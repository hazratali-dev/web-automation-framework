import { LayoutDashboard, ListChecks, Server, Settings, Target } from "lucide-react";
import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/targets", label: "Targets", icon: Target },
  { to: "/tasks", label: "Tasks", icon: ListChecks },
  { to: "/proxies", label: "Proxies", icon: Server },
  { to: "/config", label: "Config", icon: Settings },
];

export function Sidebar() {
  return (
    <aside className="flex h-screen w-60 flex-shrink-0 flex-col border-r border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-5 py-5">
        <p className="text-sm font-semibold tracking-wide text-slate-900">Web Automation</p>
        <p className="text-xs text-slate-400">Framework Dashboard</p>
      </div>
      <nav className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-blue-50 text-blue-700"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-slate-200 px-5 py-4 text-xs text-slate-400">
        Phase 5 · SQLite + asyncio
      </div>
    </aside>
  );
}
