import api from "@/lib/api";

export const estimateBuild = (payload) => {
  const body = typeof payload === "string" ? { prompt: payload } : payload;
  return api.post("/builds/estimate", body).then((r) => r.data.data);
};

export const createBuild = (payload) => {
  const body = typeof payload === "string" ? { prompt: payload } : payload;
  return api.post("/builds", body).then((r) => r.data.data);
};

export const fetchBuilds = ({ page = 1, limit = 20, status = "" } = {}) =>
  api
    .get("/builds", { params: { page, limit, ...(status !== "" ? { status } : {}) } })
    .then((r) => r.data.data);

export const fetchBuild = (id) => api.get(`/builds/${id}`).then((r) => r.data.data);

export const cancelBuild = (id) => api.post(`/builds/${id}/cancel`).then((r) => r.data.data);

export const fetchBudget = () => api.get("/builds/budget").then((r) => r.data.data);

export const fetchBlueprints = (locale = "es") =>
  api.get("/blueprints", { params: { locale } }).then((r) => r.data.data);

export const fetchBlueprint = (id, locale = "es") =>
  api.get(`/blueprints/${id}`, { params: { locale } }).then((r) => r.data.data);

export const fetchBlueprintProgress = (id, locale = "es") =>
  api.get(`/blueprints/${id}/progress`, { params: { locale } }).then((r) => r.data.data);

export const fetchLlmStatus = () => api.get("/builds/llm/status").then((r) => r.data.data);

export const saveLlmKey = ({ api_key, preferred_model = "sonnet" }) =>
  api.put("/builds/llm/key", { api_key, preferred_model }).then((r) => r.data.data);

export const deleteLlmKey = () => api.delete("/builds/llm/key").then((r) => r.data.data);

export const setLlmModel = (preferred_model) =>
  api.patch("/builds/llm/model", { preferred_model }).then((r) => r.data.data);

export const buildEventsUrl = (id) => `${process.env.REACT_APP_BACKEND_URL}/api/builds/${id}/events`;

export const buildDownloadUrl = (id) => `${process.env.REACT_APP_BACKEND_URL}/api/builds/${id}/download`;
