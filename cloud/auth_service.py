"""
cloud/auth_service.py
=====================
PURPOSE
    Managed *authentication* abstraction.

    * SupabaseAuth - Supabase Auth (GoTrue). Passwords are hashed and stored by
      the provider (never by our code); sessions are signed JWTs.
    * LocalAuth    - PBKDF2-hashed passwords + HS256 JWTs for offline simulation.

    Authentication answers "WHO are you?". Authorization ("what may you do?")
    is enforced later in the service layer with ownership checks.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import threading
import time
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class AuthService(ABC):
    @abstractmethod
    def register(self, email: str, password: str) -> str:
        """Create credentials. Returns the new user id."""

    @abstractmethod
    def login(self, email: str, password: str) -> dict:
        """Returns {access_token, refresh_token, expires_in, user_id}."""

    @abstractmethod
    def refresh(self, refresh_token: str) -> dict: ...

    @abstractmethod
    def verify_token(self, token: str) -> str:
        """Returns the user id or raises AuthError(401)."""

    @abstractmethod
    def logout(self, token: str) -> None: ...

    @abstractmethod
    def delete_user(self, user_id: str) -> None: ...


# --------------------------------------------------------------------------- #
class LocalAuth(AuthService):
    ITERATIONS = 120_000

    def __init__(self, secret: str, path: Optional[str] = None, token_ttl: int = 3600):
        import jwt  # PyJWT

        self._jwt = jwt
        self._secret = secret
        self._ttl = token_ttl
        self._lock = threading.RLock()
        self._path = Path(path) if path else None
        self._users: dict[str, dict] = {}       # email -> {user_id, salt, hash}
        self._refresh: dict[str, str] = {}      # refresh_token -> user_id
        self._revoked: set[str] = set()         # revoked token ids (jti)
        if self._path and self._path.exists():
            try:
                self._users = json.loads(self._path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                logger.warning("Could not read %s", self._path)

    def _save(self):
        if self._path:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._users), encoding="utf-8")

    def _hash(self, password: str, salt: bytes) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, self.ITERATIONS).hex()

    def make_token(self, user_id: str, ttl: Optional[int] = None) -> str:
        now = int(time.time())
        payload = {"sub": user_id, "iat": now, "exp": now + (self._ttl if ttl is None else ttl),
                   "jti": uuid.uuid4().hex}
        return self._jwt.encode(payload, self._secret, algorithm="HS256")

    def register(self, email, password):
        email = email.lower()
        with self._lock:
            if email in self._users:
                raise AuthError("Email already registered", 409)
            salt = secrets.token_bytes(16)
            user_id = str(uuid.uuid4())
            self._users[email] = {"user_id": user_id, "salt": salt.hex(), "hash": self._hash(password, salt)}
            self._save()
            return user_id

    def _session(self, user_id: str) -> dict:
        refresh = secrets.token_urlsafe(32)
        self._refresh[refresh] = user_id
        return {"access_token": self.make_token(user_id), "refresh_token": refresh,
                "expires_in": self._ttl, "user_id": user_id}

    def login(self, email, password):
        rec = self._users.get(email.lower())
        # Always hash, even for unknown emails, so timing does not reveal which emails exist.
        salt = bytes.fromhex(rec["salt"]) if rec else b"\x00" * 16
        candidate = self._hash(password, salt)
        if not rec or not hmac.compare_digest(candidate, rec["hash"]):
            raise AuthError("Invalid email or password", 401)
        return self._session(rec["user_id"])

    def refresh(self, refresh_token):
        user_id = self._refresh.pop(refresh_token, None)  # single-use rotation
        if not user_id:
            raise AuthError("Invalid refresh token", 401)
        return self._session(user_id)

    def verify_token(self, token):
        try:
            claims = self._jwt.decode(token, self._secret, algorithms=["HS256"])
        except self._jwt.ExpiredSignatureError:
            raise AuthError("Token expired. Please log in again.", 401)
        except self._jwt.InvalidTokenError:
            raise AuthError("Invalid token", 401)
        if claims.get("jti") in self._revoked:
            raise AuthError("Token has been revoked", 401)
        return claims["sub"]

    def logout(self, token):
        try:
            claims = self._jwt.decode(token, self._secret, algorithms=["HS256"],
                                      options={"verify_exp": False})
            self._revoked.add(claims.get("jti"))
        except self._jwt.InvalidTokenError:
            pass

    def delete_user(self, user_id):
        with self._lock:
            for email in [e for e, r in self._users.items() if r["user_id"] == user_id]:
                del self._users[email]
            self._save()


# --------------------------------------------------------------------------- #
class SupabaseAuth(AuthService):
    CACHE_SECONDS = 30

    def __init__(self, url: str, anon_key: str, service_key: str):
        from supabase import create_client

        self._create = create_client
        self._url = url
        self._anon = anon_key
        # admin client: create/delete users. Service-role key stays server-side ONLY.
        self._admin = create_client(url, service_key)
        # verifier client: validates access tokens (get_user takes the token explicitly).
        self._verifier = create_client(url, anon_key)
        self._cache: dict[str, tuple[str, float]] = {}

    def register(self, email, password):
        try:
            res = self._admin.auth.admin.create_user(
                {"email": email, "password": password, "email_confirm": True}
            )
            return res.user.id
        except Exception as exc:
            text = str(exc)
            if any(w in text.lower() for w in ("already", "registered", "exists")):
                raise AuthError("Email already registered", 409)
            raise AuthError(text or "Could not create account", 400)

    @staticmethod
    def _to_session(res: Any) -> dict:
        s = res.session
        return {"access_token": s.access_token, "refresh_token": s.refresh_token,
                "expires_in": s.expires_in, "user_id": res.user.id if res.user else s.user.id}

    def login(self, email, password):
        # A fresh client per login: sign-in mutates the client's auth state, which
        # must never leak into the shared admin client.
        try:
            client = self._create(self._url, self._anon)
            res = client.auth.sign_in_with_password({"email": email, "password": password})
            return self._to_session(res)
        except Exception:
            raise AuthError("Invalid email or password", 401)

    def refresh(self, refresh_token):
        try:
            client = self._create(self._url, self._anon)
            res = client.auth.refresh_session(refresh_token)
            return self._to_session(res)
        except Exception:
            raise AuthError("Invalid refresh token", 401)

    def verify_token(self, token):
        hit = self._cache.get(token)
        if hit and hit[1] > time.time():
            return hit[0]
        try:
            res = self._verifier.auth.get_user(token)
            user = getattr(res, "user", None)
            if not user:
                raise AuthError("Invalid token", 401)
        except AuthError:
            raise
        except Exception:
            raise AuthError("Invalid or expired token. Please log in again.", 401)
        self._cache[token] = (user.id, time.time() + self.CACHE_SECONDS)
        return user.id

    def logout(self, token):
        self._cache.pop(token, None)
        try:
            self._admin.auth.admin.sign_out(token)
        except Exception as exc:  # token already expired etc. - logout is best-effort
            logger.info("Supabase sign_out ignored: %s", exc)

    def delete_user(self, user_id):
        try:
            self._admin.auth.admin.delete_user(user_id)
        except Exception as exc:
            logger.error("Could not delete auth user %s: %s", user_id, exc)
            raise AuthError("Could not delete account", 500)
