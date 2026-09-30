import { useAuth } from "./context/AuthContext";
import { useHashRoute, matchRoute } from "./utils/router";
import Sidebar from "./components/Sidebar";

import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import SkillsPage from "./pages/SkillsPage";
import SkillDetailPage from "./pages/SkillDetailPage";
import FeedPage from "./pages/FeedPage";
import ProfilePage from "./pages/ProfilePage";

export default function App() {
  const { user, loading } = useAuth();
  const [path, navigate] = useHashRoute();

  if (loading) {
    return (
      <div className="auth-screen">
        <p style={{ color: "var(--cream-600)" }}>Loading…</p>
      </div>
    );
  }

  if (!user) {
    if (path.startsWith("/register")) return <RegisterPage navigate={navigate} />;
    return <LoginPage navigate={navigate} />;
  }

  // Logged in: redirect the bare "/" and any auth screens straight to the dashboard.
  if (path === "/" || path === "" || path.startsWith("/login") || path.startsWith("/register")) {
    navigate("/dashboard");
  }

  let content;
  const skillDetailParams = matchRoute("/skills/:id", path);

  if (path.startsWith("/dashboard")) {
    content = <DashboardPage navigate={navigate} />;
  } else if (skillDetailParams) {
    content = <SkillDetailPage skillId={skillDetailParams.id} navigate={navigate} />;
  } else if (path.startsWith("/skills")) {
    content = <SkillsPage navigate={navigate} />;
  } else if (path.startsWith("/feed")) {
    content = <FeedPage navigate={navigate} />;
  } else if (path.startsWith("/profile")) {
    content = <ProfilePage navigate={navigate} />;
  } else {
    content = <DashboardPage navigate={navigate} />;
  }

  return (
    <div className="app-shell">
      <Sidebar path={path} navigate={navigate} />
      {content}
    </div>
  );
}
