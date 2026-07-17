import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

export const ProtectedRoute = ({ children }) => {
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
  if (user === false) return <Navigate to="/login" replace />;
  return children;
};
