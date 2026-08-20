export function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "success" | "warning" | "danger" | "info" }) {
  const tones = {
    neutral: "status-neutral",
    success: "status-success",
    warning: "status-warning",
    danger: "status-danger",
    info: "status-info"
  };
  return <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold ${tones[tone]}`}>{children}</span>;
}
