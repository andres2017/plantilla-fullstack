// Cliente de la entidad "items" — duplica este archivo para cada entidad nueva.
import api from "@/lib/api";

export const fetchItems = ({ page = 1, limit = 10, active = "" }) =>
  api.get("/items", { params: { page, limit, ...(active !== "" ? { active } : {}) } }).then((r) => r.data.data);

export const createItem = (payload) => api.post("/items", payload).then((r) => r.data.data);

export const updateItem = (id, payload) => api.patch(`/items/${id}`, payload).then((r) => r.data.data);

export const deleteItem = (id) => api.delete(`/items/${id}`).then((r) => r.data.data);
