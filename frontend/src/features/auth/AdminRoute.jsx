import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

// Gate adicional de ROL para rutas admin-only (ej. /builds). ProtectedRoute ya
// garantiza que exista sesion; este wrapper ademas exige role === "admin".
// El backend es la barrera real (403 sin excepcion en cada endpoint) — esto es
// solo UX: evita que un usuario no-admin vea un dashboard roto lleno de toasts
// de error 403 antes de ser redirigido.
export const AdminRoute = ({ children }) => {
  const { user } = useAuth();

  if (user === null) {
    return (
      <div className="flex h-screen items-center justify-center bg-background" data-testid="auth-loading">
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-muted-foreground animate-pulse">
          [ verificando sesión... ]
        </p>
      </div>
    );
  }

  if (user?.role !== "admin") return <Navigate to="/items" replace />;

  return children;
};
