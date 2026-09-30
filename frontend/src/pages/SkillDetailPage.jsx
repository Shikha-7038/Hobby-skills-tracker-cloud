import { useEffect, useState } from "react";
import { api, ApiError } from "../services/api";
import ProgressBar from "../components/ProgressBar";

const emptyGoal = { title: "", target_value: "", unit: "hours" };
const emptyLog = { duration_minutes: "", activity: "", notes: "", practiced_at: new Date().toISOString().slice(0, 10) };

export default function SkillDetailPage({ skillId, navigate }) {
  const [skill, setSkill] = useState(null);
  const [goals, setGoals] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [showGoalForm, setShowGoalForm] = useState(false);
  const [goalForm, setGoalForm] = useState(emptyGoal);
  const [logForm, setLogForm] = useState(emptyLog);
  const [celebration, setCelebration] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    const [skillData, goalData, sessionData] = await Promise.all([
      api.getSkill(skillId),
      api.getGoals(skillId),
      api.getSkillPractice(skillId),
    ]);
    setSkill(skillData);
    setGoals(goalData);
    setSessions(sessionData);
  };

  useEffect(() => {
    load();
  }, [skillId]);

  const submitGoal = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await api.createGoal({
        skill_id: skillId,
        title: goalForm.title,
        target_value: Number(goalForm.target_value),
        unit: goalForm.unit,
      });
      setGoalForm(emptyGoal);
      setShowGoalForm(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the goal.");
    }
  };

  const submitLog = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const result = await api.logPractice({
        skill_id: skillId,
        duration_minutes: Number(logForm.duration_minutes),
        activity: logForm.activity,
        notes: logForm.notes,
        practiced_at: logForm.practiced_at,
      });
      setLogForm({ ...emptyLog, practiced_at: logForm.practiced_at });
      if (result.milestones_achieved?.length) {
        setCelebration(result.milestones_achieved.map((m) => m.title).join(", "));
      }
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not log this session.");
    } finally {
      setBusy(false);
    }
  };

  const shareToFeed = async () => {
    const content = window.prompt(
      "Share an update about this hobby:",
      `Made progress on ${skill.skill_name} today!`
    );
    if (content === null) return;
    await api.createPost({ content, skill_id: skillId });
    window.alert("Shared to the community feed.");
  };

  const deleteSkill = async () => {
    if (!window.confirm(`Delete "${skill.skill_name}" and all its goals and practice history?`)) return;
    await api.deleteSkill(skillId);
    navigate("/skills");
  };

  if (!skill) {
    return (
      <div className="page">
        <p style={{ color: "var(--ink-600)" }}>Loading…</p>
      </div>
    );
  }

  return (
    <div className="page">
      <button className="btn btn-ghost btn-sm" style={{ marginBottom: 16 }} onClick={() => navigate("/skills")}>
        ← Back to hobbies
      </button>

      <div className="page-header">
        <div>
          <h1>{skill.skill_name}</h1>
          <p className="page-subtitle">
            {skill.category} · {skill.current_level.toLowerCase()} → {skill.target_level.toLowerCase()}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-ghost" onClick={shareToFeed}>
            Share update
          </button>
          <button className="btn btn-danger" onClick={deleteSkill}>
            Delete hobby
          </button>
        </div>
      </div>

      {celebration && (
        <div className="form-success">🎉 Milestone reached: {celebration}</div>
      )}
      {error && <div className="form-error">{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 0.9fr", gap: "var(--space-5)", alignItems: "start" }}>
        <div>
          <div className="entry-card" style={{ marginBottom: "var(--space-4)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h3 style={{ fontSize: 16 }}>Log a practice session</h3>
            </div>
            <form onSubmit={submitLog}>
              <div className="field-row">
                <div className="field">
                  <label htmlFor="duration">Minutes practiced</label>
                  <input
                    id="duration"
                    type="number"
                    min="1"
                    required
                    value={logForm.duration_minutes}
                    onChange={(e) => setLogForm((f) => ({ ...f, duration_minutes: e.target.value }))}
                  />
                </div>
                <div className="field">
                  <label htmlFor="practiced_at">Date</label>
                  <input
                    id="practiced_at"
                    type="date"
                    required
                    value={logForm.practiced_at}
                    onChange={(e) => setLogForm((f) => ({ ...f, practiced_at: e.target.value }))}
                  />
                </div>
              </div>
              <div className="field">
                <label htmlFor="activity">What did you work on?</label>
                <input
                  id="activity"
                  placeholder="e.g. Practiced chord transitions"
                  value={logForm.activity}
                  onChange={(e) => setLogForm((f) => ({ ...f, activity: e.target.value }))}
                />
              </div>
              <div className="field">
                <label htmlFor="notes">Notes (optional)</label>
                <textarea
                  id="notes"
                  rows={2}
                  value={logForm.notes}
                  onChange={(e) => setLogForm((f) => ({ ...f, notes: e.target.value }))}
                />
              </div>
              <button className="btn btn-primary" type="submit" disabled={busy}>
                {busy ? "Saving…" : "Log session"}
              </button>
            </form>
          </div>

          <div className="entry-card">
            <h3 style={{ fontSize: 16, marginBottom: 12 }}>Recent sessions</h3>
            {sessions.length === 0 ? (
              <p style={{ color: "var(--ink-600)", fontSize: 13.5 }}>No sessions logged yet.</p>
            ) : (
              <div className="ledger">
                {sessions.slice(0, 8).map((s) => (
                  <div className="ledger-row" key={s.session_id}>
                    <div>
                      <div style={{ fontSize: 13.5 }}>{s.activity || "Practice session"}</div>
                      <div style={{ fontSize: 12, color: "var(--ink-600)" }}>{s.practiced_at}</div>
                    </div>
                    <span className="ledger-value" style={{ fontSize: 16 }}>
                      {s.duration_minutes}m
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div>
          <div className="entry-card" style={{ marginBottom: "var(--space-4)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h3 style={{ fontSize: 16 }}>Goals</h3>
              <button className="btn btn-ghost btn-sm" onClick={() => setShowGoalForm((s) => !s)}>
                {showGoalForm ? "Cancel" : "+ Goal"}
              </button>
            </div>

            {showGoalForm && (
              <form onSubmit={submitGoal} style={{ marginBottom: 16 }}>
                <div className="field">
                  <label htmlFor="goal_title">Goal</label>
                  <input
                    id="goal_title"
                    required
                    placeholder="e.g. Practice 30 hours"
                    value={goalForm.title}
                    onChange={(e) => setGoalForm((f) => ({ ...f, title: e.target.value }))}
                  />
                </div>
                <div className="field-row">
                  <div className="field">
                    <label htmlFor="goal_target">Target</label>
                    <input
                      id="goal_target"
                      type="number"
                      min="0.5"
                      step="0.5"
                      required
                      value={goalForm.target_value}
                      onChange={(e) => setGoalForm((f) => ({ ...f, target_value: e.target.value }))}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="goal_unit">Unit</label>
                    <input
                      id="goal_unit"
                      value={goalForm.unit}
                      onChange={(e) => setGoalForm((f) => ({ ...f, unit: e.target.value }))}
                    />
                  </div>
                </div>
                <button className="btn btn-primary btn-sm" type="submit">
                  Create goal
                </button>
              </form>
            )}

            {goals.length === 0 ? (
              <p style={{ color: "var(--ink-600)", fontSize: 13.5 }}>No goals set for this hobby yet.</p>
            ) : (
              goals.map((goal) => (
                <div key={goal.goal_id} style={{ marginBottom: 18 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14, marginBottom: 6 }}>
                    <span>{goal.title}</span>
                    <span style={{ color: "var(--ink-600)" }}>
                      {goal.current_value} / {goal.target_value} {goal.unit}
                    </span>
                  </div>
                  <ProgressBar percent={goal.progress_percent} tone={goal.status === "COMPLETED" ? "gold" : "sage"} />
                  {goal.milestones?.length > 0 && (
                    <div style={{ marginTop: 8 }}>
                      {goal.milestones.map((m) => (
                        <div key={m.milestone_id} className={`milestone-row ${m.achieved ? "achieved" : ""}`}>
                          <span className={`milestone-dot ${m.achieved ? "achieved" : ""}`} />
                          {m.title}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
