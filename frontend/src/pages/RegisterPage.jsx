import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../services/api";

export default function RegisterPage({ navigate }) {
  const { register } = useAuth();
  const [form, setForm] = useState({ name: "", username: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await register(form);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create your account. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="auth-mark">
          Practice<span>Log</span>
        </div>
        <p className="auth-tagline">Start a log for the hobby you keep meaning to get back to.</p>

        {error && <div className="form-error">{error}</div>}

        <form onSubmit={submit}>
          <div className="field">
            <label htmlFor="name">Full name</label>
            <input id="name" required value={form.name} onChange={update("name")} />
          </div>
          <div className="field">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              required
              pattern="[a-zA-Z0-9_]{3,20}"
              title="3-20 characters: letters, numbers, underscore"
              value={form.username}
              onChange={update("username")}
            />
          </div>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" type="email" required value={form.email} onChange={update("email")} />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              title="At least 8 characters, with letters and numbers"
              value={form.password}
              onChange={update("password")}
            />
          </div>
          <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
            {busy ? "Creating account…" : "Create account"}
          </button>
        </form>

        <div className="auth-switch">
          Already keeping a log? <button onClick={() => navigate("/login")}>Log in</button>
        </div>
      </div>
    </div>
  );
}
