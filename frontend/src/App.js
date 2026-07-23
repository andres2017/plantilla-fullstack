import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/features/auth/AuthContext";
import { ProtectedRoute } from "@/features/auth/ProtectedRoute";
import { AdminRoute } from "@/features/auth/AdminRoute";
import { AppLayout } from "@/components/layout/AppLayout";
import LoginPage from "@/features/auth/LoginPage";
import RegisterPage from "@/features/auth/RegisterPage";
import ItemsPage from "@/features/items/ItemsPage";
import BuildsPage from "@/features/builds/BuildsPage";

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            {/* Entidad de referencia. Agrega aqui una <Route> por cada feature nueva. */}
            <Route path="/" element={<Navigate to="/items" replace />} />
            <Route path="/items" element={<ItemsPage />} />
            {/* MISION 14 — admin-only, AdminRoute redirige si el rol no es "admin". */}
            <Route
              path="/builds"
              element={
                <AdminRoute>
                  <BuildsPage />
                </AdminRoute>
              }
            />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Toaster position="bottom-right" theme="dark" />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
