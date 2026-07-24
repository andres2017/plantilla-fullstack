// Cliente de la "fabrica Cyberandres" (MISION 14) — dashboard admin-only para
// disparar builds guiados por prompt via Claude Agent SDK. Sigue el mismo
// patron delgado que features/items/api.js: funciones que llaman a `api` y
// devuelven r.data.data (respuesta uniforme { success, data, error }).
import api from "@/lib/api";

export const estimateBuild = (prompt, { templateType = "full_stack", model = "sonnet" } = {}) =>
  api
    .post("/builds/estimate", { prompt, template_type: templateType, model })
    .then((r) => r.data.data);

export const createBuild = (
  prompt,
  { templateType = "full_stack", agent = "implementer", model = "sonnet" } = {}
) =>
  api
    .post("/builds", { prompt, template_type: templateType, agent, model })
    .then((r) => r.data.data);

export const fetchBuilds = ({ page = 1, limit = 20, status = "" } = {}) =>
  api
    .get("/builds", { params: { page, limit, ...(status !== "" ? { status } : {}) } })
    .then((r) => r.data.data);

export const fetchBuild = (id) => api.get(`/builds/${id}`).then((r) => r.data.data);

export const cancelBuild = (id) => api.post(`/builds/${id}/cancel`).then((r) => r.data.data);

export const fetchBudget = () => api.get("/builds/budget").then((r) => r.data.data);

// EventSource no usa la instancia de axios (no manda withCredentials via config
// ni headers custom) — hay que armar la URL completa a mano. Cookies httpOnly
// via { withCredentials: true } del propio EventSource.
export const buildEventsUrl = (id) => `${process.env.REACT_APP_BACKEND_URL}/api/builds/${id}/events`;

// Descarga por navegacion directa (<a href download>), no por axios/fetch+blob,
// para reutilizar las cookies httpOnly de sesion sin reinventar el manejo de
// streaming binario en el cliente.
export const buildDownloadUrl = (id) => `${process.env.REACT_APP_BACKEND_URL}/api/builds/${id}/download`;
