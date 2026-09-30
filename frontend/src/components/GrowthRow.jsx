/**
 * GrowthRow
 * =========
 * Renders the last N days as small marks; a filled (sage) mark means the
 * user logged at least one practice session that day. This replaces the
 * more obvious "flame + number" streak treatment with something specific
 * to a practice-journal metaphor: a short row of growth.
 *
 * `practicedDates` is an array of "YYYY-MM-DD" strings (any skill, any
 * session - the streak rewards showing up, not any one hobby).
 */
export default function GrowthRow({ practicedDates, days = 14 }) {
  const set = new Set(practicedDates);
  const today = new Date();
  const marks = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const iso = d.toISOString().slice(0, 10);
    marks.push({ iso, filled: set.has(iso), isToday: i === 0 });
  }

  return (
    <div className="growth-row" role="img" aria-label={`Practice activity over the last ${days} days`}>
      {marks.map((m) => (
        <div
          key={m.iso}
          className={`growth-mark ${m.filled ? "filled" : ""} ${m.isToday ? "today" : ""}`}
          title={m.iso}
        />
      ))}
    </div>
  );
}
