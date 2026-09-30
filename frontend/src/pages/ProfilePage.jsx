import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { api, ApiError } from "../services/api";

export default function ProfilePage({ navigate }) {
  const { user, refreshProfile, logout } = useAuth();
  const [bio, setBio] = useState(user?.bio || "");
  const [interests, setInterests] = useState((user?.interests || []).join(", "));
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setBusy(true);
    try {
      await api.updateProfile({
        bio,
        interests: interests
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      await refreshProfile();
      setSuccess("Profile updated.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not update your profile.");
    } finally {
      setBusy(false);
    }
  };

  const uploadPicture = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await api.uploadFile(file, "PROFILE_IMAGE");
      await refreshProfile();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not upload that image.");
    }
  };

  const deleteAccount = async () => {
    const confirmed = window.confirm(
      "This permanently deletes your profile, hobbies, goals, practice history, and posts. This cannot be undone. Continue?"
    );
    if (!confirmed) return;
    await api.deleteAccount();
    await logout();
    navigate("/login");
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Profile</h1>
          <p className="page-subtitle">This is what other members see when they visit your page.</p>
        </div>
      </div>

      <div style={{ maxWidth: 480 }}>
        <div className="entry-card" style={{ marginBottom: "var(--space-4)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 8 }}>
            <div className="avatar" style={{ width: 56, height: 56, fontSize: 20 }}>
              {user?.profile_picture ? (
                <img src={user.profile_picture} alt="" />
              ) : (
                (user?.name || "?").charAt(0).toUpperCase()
              )}
            </div>
            <div>
              <div style={{ fontWeight: 600 }}>{user?.name}</div>
              <div style={{ fontSize: 13, color: "var(--ink-600)" }}>@{user?.username}</div>
            </div>
          </div>
          <label className="btn btn-ghost btn-sm" style={{ display: "inline-block" }}>
            Change photo
            <input type="file" accept="image/*" onChange={uploadPicture} style={{ display: "none" }} />
          </label>
        </div>

        <div className="entry-card">
          {error && <div className="form-error">{error}</div>}
          {success && <div className="form-success">{success}</div>}
          <form onSubmit={submit}>
            <div className="field">
              <label htmlFor="bio">Bio</label>
              <textarea id="bio" rows={3} maxLength={500} value={bio} onChange={(e) => setBio(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="interests">Interests (comma-separated)</label>
              <input
                id="interests"
                placeholder="guitar, chess, watercolor"
                value={interests}
                onChange={(e) => setInterests(e.target.value)}
              />
            </div>
            <button className="btn btn-primary" type="submit" disabled={busy}>
              {busy ? "Saving…" : "Save changes"}
            </button>
          </form>
        </div>

        <div className="entry-card" style={{ marginTop: "var(--space-4)", borderColor: "var(--brick)" }}>
          <h3 style={{ fontSize: 15, marginBottom: 6 }}>Danger zone</h3>
          <p style={{ fontSize: 13, color: "var(--ink-600)", marginBottom: 12 }}>
            Permanently delete your account and everything in it.
          </p>
          <button className="btn btn-danger" onClick={deleteAccount}>
            Delete my account
          </button>
        </div>
      </div>
    </div>
  );
}
