import { Outlet, NavLink } from "react-router-dom";
import { Cube, SignOut } from "@phosphor-icons/react";
import { useAuth } from "@/features/auth/AuthContext";
import { Button } from "@/components/ui/button";
import { APP_NAME } from "@/config";

// Agrega aqui un item por cada feature nueva (icono de @phosphor-icons/react).
// "enabled: false" muestra un placeholder deshabilitado con badge "pronto".
const navItems = [
  { to: "/items", label: "Items", icon: Cube, enabled: true },
];

export const AppLayout = () => {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col border-r border-border bg-card md:flex" data-testid="app-sidebar">
        <div className="flex h-14 items-center gap-2 border-b border-border px-5">
          <Cube size={20} weight="fill" className="text-[#4D7CFF]" />
          <span className="font-heading text-base font-black tracking-tighter">{APP_NAME}</span>
        </div>
        <nav className="flex-1 space-y-px p-3">
          {navItems.map(({ to, label, icon: Icon, enabled }) =>
            enabled ? (
              <NavLink key={to} to={to} data-testid={`sidebar-link-${label.toLowerCase()}`}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 text-sm font-medium transition-colors duration-150 ${
                    isActive ? "bg-[#002FA7] text-white" : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                  }`
                }>
                <Icon size={17} /> {label}
              </NavLink>
            ) : (
              <div key={to} className="flex cursor-not-allowed items-center justify-between px-3 py-2.5 text-sm text-muted-foreground/40" data-testid={`sidebar-disabled-${label.toLowerCase()}`}>
                <span className="flex items-center gap-3"><Icon size={17} /> {label}</span>
                <span className="border border-border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest">pronto</span>
              </div>
            )
          )}
        </nav>
        <div className="border-t border-border p-4">
          <p className="truncate text-sm font-medium" data-testid="sidebar-user-name">{user?.name}</p>
          <p className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground" data-testid="sidebar-user-role">{user?.role}</p>
        </div>
      </aside>

      <div className="md:pl-60">
        <header className="sticky top-0 z-50 flex h-14 items-center justify-between border-b border-border bg-background/80 px-5 backdrop-blur-md" data-testid="app-navbar">
          <div className="flex items-center gap-2 md:hidden">
            <Cube size={18} weight="fill" className="text-[#4D7CFF]" />
            <span className="font-heading text-sm font-black tracking-tighter">{APP_NAME}</span>
          </div>
          <p className="hidden font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground md:block">
            Panel de administración
          </p>
          <Button variant="ghost" size="sm" onClick={logout} className="gap-2 text-muted-foreground hover:text-foreground" data-testid="logout-button">
            <SignOut size={16} /> Salir
          </Button>
        </header>
        <main className="p-5 sm:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
