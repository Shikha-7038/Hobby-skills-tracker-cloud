import { useAuth } from "../context/AuthContext";

const LINKS = [
  { to: "/dashboard", label: "Dashboard", icon: "◧" },
  { to: "/skills", label: "My hobbies", icon: "✦" },
  { to: "/feed", label: "Community", icon: "◐" },
  { to: "/profile", label: "Profile", icon: "▢" },
];

export default function Sidebar({ path, navigate }) {
  const { user, logout } = useAuth();

  return (
    <nav className="spine" aria-label="Main navigation">
      <div className="spine-mark">
        Practice<span>Log</span>
      </div>

      <div className="spine-nav">
        {LINKS.map((link) => (
          <button
            key={link.to}
            className={`spine-link ${path.startsWith(link.to) ? "active" : ""}`}
            onClick={() => navigate(link.to)}
          >
            <span aria-hidden="true">{link.icon}</span>
            {link.label}
          </button>
        ))}
      </div>

      <div className="spine-footer">
        <div className="spine-user">
          <div className="avatar">
            {user?.profile_picture ? (
              <img src={user.profile_picture} alt="" />
            ) : (
              (user?.name || "?").charAt(0).toUpperCase()
            )}
          </div>
          <div>
            <div className="spine-user-name">{user?.name}</div>
            <div className="spine-user-handle">@{user?.username}</div>
          </div>
        </div>
        <button className="spine-link" onClick={logout}>
          <span aria-hidden="true">⏻</span> Log out
        </button>
      </div>
    </nav>
  );
}
