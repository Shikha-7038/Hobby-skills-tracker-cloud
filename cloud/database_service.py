"""
cloud/database_service.py
=========================
PURPOSE
    One small interface for the *cloud database*, with two interchangeable
    implementations:

    * SupabaseDatabase - managed PostgreSQL (Supabase free tier). Used in the cloud.
    * LocalDatabase    - in-memory / JSON-file store. Used for local simulation and tests.

    The rest of the application only talks to ``DatabaseService`` so the same
    business logic runs unchanged on your laptop and in the cloud.

FILTER SYNTAX
    filters = {"user_id": "abc"}                     -> equality
    filters = {"post_id": ("in", ["a", "b"])}        -> IN (...)
    filters = {"created_at": ("gte", "2026-01-01")}  -> >=   (also lte, gt, lt, neq)
    filters = {"search_text": ("ilike", "%guitar%")} -> case-insensitive LIKE
"""
from __future__ import annotations

import copy
import json
import logging
import re
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# table name -> primary-key column
TABLE_PK = {
    "users": "user_id",
    "skills": "skill_id",
    "goals": "goal_id",
    "milestones": "milestone_id",
    "practice_sessions": "session_id",
    "posts": "post_id",
    "comments": "comment_id",
    "likes": "like_id",        # "<post_id>:<user_id>"  -> primary key prevents duplicate likes
    "follows": "follow_id",    # "<follower_id>:<following_id>"
    "files": "file_id",
    "reports": "report_id",    # "<post_id>:<reporter_id>"
}

# columns that must be unique (mirrors UNIQUE indexes in docs/schema.sql)
UNIQUE_COLUMNS = {"users": ("username", "email")}

Filters = dict
OrderBy = list  # [(column, descending_bool), ...]


class DuplicateError(Exception):
    """Raised when an insert violates a primary-key / unique constraint."""


class DatabaseError(Exception):
    """Raised when the cloud database is unreachable or returns an error."""


class DatabaseService(ABC):
    @abstractmethod
    def insert(self, table: str, row: dict) -> dict: ...

    @abstractmethod
    def get(self, table: str, pk: str) -> Optional[dict]: ...

    @abstractmethod
    def select(
        self,
        table: str,
        filters: Optional[Filters] = None,
        order_by: Optional[OrderBy] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[dict]: ...

    @abstractmethod
    def update(self, table: str, pk: str, changes: dict) -> Optional[dict]: ...

    @abstractmethod
    def delete(self, table: str, pk: str) -> bool: ...

    @abstractmethod
    def delete_where(self, table: str, filters: Filters) -> int: ...

    @abstractmethod
    def count(self, table: str, filters: Optional[Filters] = None) -> int: ...


# --------------------------------------------------------------------------- #
# Local implementation (simulation / tests)
# --------------------------------------------------------------------------- #
def _ilike_regex(pattern: str) -> "re.Pattern[str]":
    parts = []
    for ch in pattern:
        if ch == "%":
            parts.append(".*")
        elif ch == "_":
            parts.append(".")
        else:
            parts.append(re.escape(ch))
    return re.compile("".join(parts), re.IGNORECASE | re.DOTALL)


def _matches(row: dict, filters: Optional[Filters]) -> bool:
    for col, cond in (filters or {}).items():
        val = row.get(col)
        if isinstance(cond, tuple):
            op, arg = cond
            if op == "in":
                if val not in arg:
                    return False
            elif op == "ilike":
                if val is None or not _ilike_regex(arg).fullmatch(str(val)):
                    return False
            elif op == "gte":
                if val is None or val < arg:
                    return False
            elif op == "lte":
                if val is None or val > arg:
                    return False
            elif op == "gt":
                if val is None or val <= arg:
                    return False
            elif op == "lt":
                if val is None or val >= arg:
                    return False
            elif op == "neq":
                if val == arg:
                    return False
            else:
                raise ValueError(f"Unsupported filter operator: {op}")
        elif val != cond:
            return False
    return True


class LocalDatabase(DatabaseService):
    """Thread-safe dictionary database, optionally persisted to a JSON file."""

    def __init__(self, path: Optional[str] = None):
        self._lock = threading.RLock()
        self._path = Path(path) if path else None
        self._tables: dict[str, dict[str, dict]] = {t: {} for t in TABLE_PK}
        if self._path and self._path.exists():
            try:
                loaded = json.loads(self._path.read_text(encoding="utf-8"))
                for table, rows in loaded.items():
                    if table in self._tables:
                        self._tables[table] = rows
            except (OSError, ValueError):
                logger.warning("Could not read %s; starting with an empty database", self._path)

    def _save(self) -> None:
        if not self._path:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._tables, default=str), encoding="utf-8")
        tmp.replace(self._path)

    def insert(self, table: str, row: dict) -> dict:
        pk_col = TABLE_PK[table]
        with self._lock:
            pk = row[pk_col]
            if pk in self._tables[table]:
                raise DuplicateError(f"{table}.{pk_col}={pk} already exists")
            for col in UNIQUE_COLUMNS.get(table, ()):
                if any(
                    str(existing.get(col, "")).lower() == str(row.get(col, "")).lower()
                    for existing in self._tables[table].values()
                ):
                    raise DuplicateError(f"{table}.{col} must be unique")
            self._tables[table][pk] = copy.deepcopy(row)
            self._save()
            return copy.deepcopy(row)

    def get(self, table: str, pk: str) -> Optional[dict]:
        with self._lock:
            row = self._tables[table].get(pk)
            return copy.deepcopy(row) if row else None

    def select(self, table, filters=None, order_by=None, limit=None, offset=0):
        with self._lock:
            rows = [r for r in self._tables[table].values() if _matches(r, filters)]
            # stable multi-column sort: apply the least significant key first
            for col, desc in reversed(order_by or []):
                rows.sort(key=lambda r, c=col: (r.get(c) is None, r.get(c)), reverse=desc)
            end = None if limit is None else offset + limit
            return copy.deepcopy(rows[offset:end])

    def update(self, table, pk, changes):
        with self._lock:
            row = self._tables[table].get(pk)
            if row is None:
                return None
            row.update(copy.deepcopy(changes))
            self._save()
            return copy.deepcopy(row)

    def delete(self, table, pk):
        with self._lock:
            existed = self._tables[table].pop(pk, None) is not None
            if existed:
                self._save()
            return existed

    def delete_where(self, table, filters):
        if not filters:
            raise ValueError("delete_where requires at least one filter")
        with self._lock:
            doomed = [pk for pk, r in self._tables[table].items() if _matches(r, filters)]
            for pk in doomed:
                del self._tables[table][pk]
            if doomed:
                self._save()
            return len(doomed)

    def count(self, table, filters=None):
        with self._lock:
            return sum(1 for r in self._tables[table].values() if _matches(r, filters))


# --------------------------------------------------------------------------- #
# Supabase (managed PostgreSQL) implementation
# --------------------------------------------------------------------------- #
class SupabaseDatabase(DatabaseService):
    PAGE = 1000  # Supabase returns at most 1000 rows per request

    def __init__(self, client: Any):
        self.client = client

    # -- helpers ----------------------------------------------------------- #
    @staticmethod
    def _apply(query: Any, filters: Optional[Filters]) -> Any:
        for col, cond in (filters or {}).items():
            if isinstance(cond, tuple):
                op, arg = cond
                if op == "in":
                    query = query.in_(col, list(arg))
                elif op == "ilike":
                    query = query.ilike(col, arg)
                elif op in ("gte", "lte", "gt", "lt", "neq"):
                    query = getattr(query, op)(col, arg)
                else:
                    raise ValueError(f"Unsupported filter operator: {op}")
            else:
                query = query.eq(col, cond)
        return query

    @staticmethod
    def _has_empty_in(filters: Optional[Filters]) -> bool:
        return any(
            isinstance(c, tuple) and c[0] == "in" and len(c[1]) == 0
            for c in (filters or {}).values()
        )

    @staticmethod
    def _run(query: Any) -> Any:
        try:
            return query.execute()
        except Exception as exc:  # postgrest APIError, network errors, ...
            text = str(exc).lower()
            if getattr(exc, "code", None) == "23505" or "duplicate key" in text or "23505" in text:
                raise DuplicateError(str(exc)) from exc
            logger.error("Supabase database error: %s", exc)
            raise DatabaseError(str(exc)) from exc

    # -- interface --------------------------------------------------------- #
    def insert(self, table, row):
        res = self._run(self.client.table(table).insert(row))
        return res.data[0] if res.data else row

    def get(self, table, pk):
        res = self._run(self.client.table(table).select("*").eq(TABLE_PK[table], pk).limit(1))
        return res.data[0] if res.data else None

    def select(self, table, filters=None, order_by=None, limit=None, offset=0):
        if self._has_empty_in(filters):
            return []

        def build() -> Any:
            q = self._apply(self.client.table(table).select("*"), filters)
            for col, desc in order_by or []:
                q = q.order(col, desc=desc)
            return q

        if limit is not None:
            return self._run(build().range(offset, offset + limit - 1)).data or []

        rows: list[dict] = []
        start = offset
        while True:  # fetch everything, one page at a time
            page = self._run(build().range(start, start + self.PAGE - 1)).data or []
            rows.extend(page)
            if len(page) < self.PAGE:
                return rows
            start += self.PAGE

    def update(self, table, pk, changes):
        res = self._run(self.client.table(table).update(changes).eq(TABLE_PK[table], pk))
        return res.data[0] if res.data else None

    def delete(self, table, pk):
        res = self._run(self.client.table(table).delete().eq(TABLE_PK[table], pk))
        return bool(res.data)

    def delete_where(self, table, filters):
        if not filters:
            raise ValueError("delete_where requires at least one filter")
        if self._has_empty_in(filters):
            return 0
        res = self._run(self._apply(self.client.table(table).delete(), filters))
        return len(res.data or [])

    def count(self, table, filters=None):
        if self._has_empty_in(filters):
            return 0
        q = self._apply(self.client.table(table).select("*", count="exact"), filters).limit(1)
        res = self._run(q)
        return int(res.count or 0)
