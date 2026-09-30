const PILL_CLASS = { ACTIVE: "pill-active", PAUSED: "pill-paused", COMPLETED: "pill-completed" };

export default function SkillCard({ skill, onOpen }) {
  return (
    <a
      className="skill-card"
      href={`#/skills/${skill.skill_id}`}
      onClick={(e) => {
        e.preventDefault();
        onOpen(skill.skill_id);
      }}
    >
      <div className="skill-card-top">
        <h3>{skill.skill_name}</h3>
        <span className={`pill ${PILL_CLASS[skill.status] || "pill-active"}`}>{skill.status.toLowerCase()}</span>
      </div>
      <div className="skill-card-category">{skill.category}</div>
      <div style={{ fontSize: 13, color: "var(--ink-600)" }}>
        {skill.current_level.toLowerCase()} → {skill.target_level.toLowerCase()}
      </div>
    </a>
  );
}
