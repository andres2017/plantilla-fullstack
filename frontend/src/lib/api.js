import axios from "axios";

const api = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL}/api`,
  withCredentials: true,
});

let refreshPromise = null;

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const isAuthCall = original?.url?.includes("/auth/");
    if (error.response?.status === 401 && !original._retry && !isAuthCall) {
      original._retry = true;
      try {
        refreshPromise = refreshPromise || api.post("/auth/refresh");
        await refreshPromise;
        refreshPromise = null;
        return api(original);
      } catch {
        refreshPromise = null;
      }
    }
    return Promise.reject(error);
  }
);

export const getApiError = (e) => {
  const data = e?.response?.data;
  // Formato heredado del resto del proyecto: { error: "mensaje plano" }.
  if (typeof data?.error === "string") return data.error;
  // Formato con taxonomia de codigos ({ error: { code, message } }), usado por
  // modulos opcionales como payments/builds (ver docs/DECISIONS.md). El codigo
  // (ej. "BUILD_002_COSTO_EXCEDIDO") queda disponible para quien necesite
  // distinguir programaticamente, pero getApiError siempre devuelve texto legible.
  if (data?.error && typeof data.error === "object" && typeof data.error.message === "string") {
    return data.error.message;
  }
  if (typeof data?.detail === "string") return data.detail;
  return e?.message || "Error inesperado. Intenta de nuevo.";
};

export default api;
