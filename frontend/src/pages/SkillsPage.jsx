import { useEffect, useState } from "react";
import { api, ApiError } from "../services/api";
import SkillCard from "../components/SkillCard";

const CATEGORIES = ["Music", "Coding", "Art", "Fitness", "Language", "Writing", "Cooking", "Chess", "Other"];

const emptyForm = {
  skill_name: "",
  category: "Music",
  current_level: "BEGINNER",
  target_level: "ADVANCED",
  start_date: new Date().toISOString().slice(0, 10),
  description: "",
};

export default function SkillsPage({ navigate }) {
  const [skills, setSkills] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => api.getSkills().then(setSkills);

  useEffect(() => {
    load();
  }, []);

  const update = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api.createSkill(form);
      setForm(emptyForm);
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not add this hobby.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>My hobbies</h1>
          <p className="page-subtitle">Everything you're learning, in one place.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "+ Add a hobby"}
        </button>
      </div>

      {showForm && (
        <div className="entry-card" style={{ marginBottom: "var(--space-5)" }}>
          {error && <div className="form-error">{error}</div>}
          <form onSubmit={submit}>
            <div className="field-row">
              <div className="field">
                <label htmlFor="skill_name">Hobby or skill name</label>
                <input
                  id="skill_name"
                  required
                  placeholder="e.g. Guitar"
                  value={form.skill_name}
                  onChange={update("skill_name")}
                />
              </div>
              <div className="field">
                <label htmlFor="category">Category</label>
                <select id="category" value={form.category} onChange={update("category")}>
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="field-row">
              <div className="field">
                <label htmlFor="current_level">Current level</label>
                <select id="current_level" value={form.current_level} onChange={update("current_level")}>
                  <option value="BEGINNER">Beginner</option>
                  <option value="INTERMEDIATE">Intermediate</option>
                  <option value="ADVANCED">Advanced</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="target_level">Target level</label>
                <select id="target_level" value={form.target_level} onChange={update("target_level")}>
                  <option value="BEGINNER">Beginner</option>
                  <option value="INTERMEDIATE">Intermediate</option>
                  <option value="ADVANCED">Advanced</option>
                </select>
              </div>
            </div>
            <div className="field">
              <label htmlFor="description">Notes (optional)</label>
              <textarea
                id="description"
                rows={2}
                placeholder="What do you want to get out of this?"
                value={form.description}
                onChange={update("description")}
              />
            </div>
            <button className="btn btn-primary" type="submit" disabled={busy}>
              {busy ? "Adding…" : "Add hobby"}
            </button>
          </form>
        </div>
      )}

      {skills === null ? (
        <p style={{ color: "var(--ink-600)" }}>Loading…</p>
      ) : skills.length === 0 ? (
        <div className="empty-state">
          <h3>No hobbies yet</h3>
          <p>Add the first one you want to practice consistently.</p>
        </div>
      ) : (
        <div className="skill-grid">
          {skills.map((skill) => (
            <SkillCard key={skill.skill_id} skill={skill} onOpen={(id) => navigate(`/skills/${id}`)} />
          ))}
        </div>
      )}
    </div>
  );
}
