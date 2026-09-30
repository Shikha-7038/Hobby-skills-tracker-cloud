import { useEffect, useState } from "react";
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { api } from "../services/api";
import GrowthRow from "../components/GrowthRow";

const CHART_COLORS = ["#c99a3c", "#6f9a78", "#ae5a45", "#52604f", "#a87f2e", "#4f7a58"];

export default function DashboardPage({ navigate }) {
  const [dashboard, setDashboard] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getDashboard()
      .then(setDashboard)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    // Pull every skill's sessions just to build the growth-row (last 14 days of activity).
    api.getSkills().then(async (skills) => {
      const allSessions = [];
      for (const skill of skills) {
        const rows = await api.getSkillPractice(skill.skill_id);
        allSessions.push(...rows);
      }
      setSessions(allSessions);
    });
  }, []);

  if (loading || !dashboard) {
    return (
      <div className="page">
        <p style={{ color: "var(--ink-600)" }}>Loading your dashboard…</p>
      </div>
    );
  }

  const skillMinutesData = Object.entries(dashboard.charts.practice_minutes_by_skill).map(([name, minutes]) => ({
    name,
    hours: Math.round((minutes / 60) * 10) / 10,
  }));

  const weeklyTrendData = Object.entries(dashboard.charts.weekly_practice_trend).map(([week, minutes]) => ({
    week: week.split("-W")[1] ? `W${week.split("-W")[1]}` : week,
    hours: Math.round((minutes / 60) * 10) / 10,
  }));

  const goalCompletionData = Object.entries(dashboard.charts.goal_completion)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }));

  const hasNoActivity = dashboard.total_practice_minutes === 0;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Welcome back</h1>
          <p className="page-subtitle">Here's how your practice has been going.</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate("/skills")}>
          + Log a practice session
        </button>
      </div>

      <div style={{ marginBottom: "var(--space-5)" }}>
        <div className="ledger-label" style={{ marginBottom: 6 }}>
          Last 14 days
        </div>
        <GrowthRow practicedDates={sessions.map((s) => s.practiced_at)} />
      </div>

      <div className="stat-grid">
        <div className="stat-cell accent">
          <span className="stat-cell-value">{dashboard.current_streak}</span>
          <span className="stat-cell-label">day streak</span>
        </div>
        <div className="stat-cell">
          <span className="stat-cell-value">{dashboard.longest_streak}</span>
          <span className="stat-cell-label">longest streak</span>
        </div>
        <div className="stat-cell">
          <span className="stat-cell-value">{dashboard.total_practice_hours}h</span>
          <span className="stat-cell-label">total practice</span>
        </div>
        <div className="stat-cell">
          <span className="stat-cell-value">{dashboard.active_skills}</span>
          <span className="stat-cell-label">active hobbies</span>
        </div>
        <div className="stat-cell">
          <span className="stat-cell-value">{dashboard.goals_completed}</span>
          <span className="stat-cell-label">goals completed</span>
        </div>
        <div className="stat-cell">
          <span className="stat-cell-value">{dashboard.milestones_achieved}</span>
          <span className="stat-cell-label">milestones hit</span>
        </div>
      </div>

      {hasNoActivity ? (
        <div className="empty-state">
          <h3>No practice logged yet</h3>
          <p>Add a hobby and log your first session to see your charts fill in here.</p>
          <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate("/skills")}>
            Go to my hobbies
          </button>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-5)" }}>
          <div className="entry-card">
            <h3 style={{ fontSize: 16, marginBottom: 16 }}>Practice hours by hobby</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={skillMinutesData}>
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#52604f" }} />
                <YAxis tick={{ fontSize: 12, fill: "#52604f" }} />
                <Tooltip />
                <Bar dataKey="hours" fill="#c99a3c" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="entry-card">
            <h3 style={{ fontSize: 16, marginBottom: 16 }}>Weekly practice trend</h3>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={weeklyTrendData}>
                <XAxis dataKey="week" tick={{ fontSize: 12, fill: "#52604f" }} />
                <YAxis tick={{ fontSize: 12, fill: "#52604f" }} />
                <Tooltip />
                <Line type="monotone" dataKey="hours" stroke="#6f9a78" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {goalCompletionData.length > 0 && (
            <div className="entry-card">
              <h3 style={{ fontSize: 16, marginBottom: 16 }}>Goal completion</h3>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={goalCompletionData} dataKey="value" nameKey="name" outerRadius={80}>
                    {goalCompletionData.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="entry-card">
            <h3 style={{ fontSize: 16, marginBottom: 8 }}>Community engagement</h3>
            <div className="ledger">
              <div className="ledger-row">
                <span className="ledger-label">Posts shared</span>
                <span className="ledger-value">{dashboard.posts_count}</span>
              </div>
              <div className="ledger-row">
                <span className="ledger-label">Likes received</span>
                <span className="ledger-value">{dashboard.likes_received}</span>
              </div>
              <div className="ledger-row">
                <span className="ledger-label">Comments received</span>
                <span className="ledger-value">{dashboard.comments_received}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
