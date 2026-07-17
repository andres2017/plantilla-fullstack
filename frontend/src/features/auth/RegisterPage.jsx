import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { AuthShell } from "./AuthShell";
import { getApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(name, email, password);
      navigate("/items");
    } catch (err) {
      setError(getApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell title="Crear cuenta" subtitle="Regístrate para empezar.">
      <form onSubmit={handleSubmit} className="space-y-6" data-testid="register-form">
        <div className="space-y-2">
          <Label htmlFor="name" className="text-xs uppercase tracking-[0.2em]">Nombre</Label>
          <Input id="name" required minLength={2} value={name} placeholder="Tu nombre"
            onChange={(e) => setName(e.target.value)} data-testid="register-name-input" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="email" className="text-xs uppercase tracking-[0.2em]">Email</Label>
          <Input id="email" type="email" required value={email} placeholder="tu@email.com"
            onChange={(e) => setEmail(e.target.value)} data-testid="register-email-input" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password" className="text-xs uppercase tracking-[0.2em]">Contraseña</Label>
          <Input id="password" type="password" required minLength={6} value={password} placeholder="Mínimo 6 caracteres"
            onChange={(e) => setPassword(e.target.value)} data-testid="register-password-input" />
        </div>
        {error && (
          <p className="border border-[#FF2A2A] px-3 py-2 text-sm text-[#FF2A2A]" data-testid="register-error-message">
            {error}
          </p>
        )}
        <Button type="submit" disabled={loading} className="w-full" data-testid="register-submit-button">
          {loading ? "Creando cuenta..." : "Crear cuenta"}
        </Button>
        <p className="text-sm text-muted-foreground">
          ¿Ya tienes cuenta?{" "}
          <Link to="/login" className="text-foreground underline underline-offset-4 hover:text-[#4D7CFF]" data-testid="go-to-login-link">
            Inicia sesión
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}
