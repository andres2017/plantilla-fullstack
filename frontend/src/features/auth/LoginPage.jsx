import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { AuthShell } from "./AuthShell";
import { getApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/items");
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell title="Iniciar sesión" subtitle="Accede a tu panel.">
      <form onSubmit={handleSubmit} className="space-y-6" data-testid="login-form">
        <div className="space-y-2">
          <Label htmlFor="email" className="text-xs uppercase tracking-[0.2em]">Email</Label>
          <Input id="email" type="email" required value={email} placeholder="admin@example.com"
            onChange={(e) => setEmail(e.target.value)} data-testid="login-email-input" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password" className="text-xs uppercase tracking-[0.2em]">Contraseña</Label>
          <Input id="password" type="password" required value={password} placeholder="••••••••"
            onChange={(e) => setPassword(e.target.value)} data-testid="login-password-input" />
        </div>
        {error && (
          <p className="border border-[#FF2A2A] px-3 py-2 text-sm text-[#FF2A2A]" data-testid="login-error-message">
            {error}
          </p>
        )}
        <Button type="submit" disabled={loading} className="w-full" data-testid="login-submit-button">
          {loading ? "Verificando..." : "Entrar"}
        </Button>
        <p className="text-sm text-muted-foreground">
          ¿No tienes cuenta?{" "}
          <Link to="/register" className="text-foreground underline underline-offset-4 hover:text-[#4D7CFF]" data-testid="go-to-register-link">
            Regístrate
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}
