export default function ProgressBar({ percent, tone = "sage" }) {
  const clamped = Math.max(0, Math.min(100, percent));
  return (
    <div
      className="progress-track"
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className={`progress-fill ${tone === "gold" ? "gold" : ""}`} style={{ width: `${clamped}%` }} />
    </div>
  );
}
