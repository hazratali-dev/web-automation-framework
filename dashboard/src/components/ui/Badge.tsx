const VARIANTS = {
  ok: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200",
  muted: "bg-slate-100 text-slate-600 ring-1 ring-slate-200",
  danger: "bg-red-50 text-red-700 ring-1 ring-red-200",
  warning: "bg-amber-50 text-amber-700 ring-1 ring-amber-200",
  info: "bg-blue-50 text-blue-700 ring-1 ring-blue-200",
};

export function Badge({
  children,
  variant = "muted",
}: {
  children: React.ReactNode;
  variant?: keyof typeof VARIANTS;
}) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${VARIANTS[variant]}`}>
      {children}
    </span>
  );
}

export function statusVariant(status: string): keyof typeof VARIANTS {
  switch (status) {
    case "success":
    case "active":
      return "ok";
    case "failed":
    case "archived":
      return "danger";
    case "running":
    case "queued":
    case "paused":
      return "warning";
    default:
      return "muted";
  }
}
