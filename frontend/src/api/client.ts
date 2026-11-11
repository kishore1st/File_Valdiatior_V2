import axios from "axios";

export const api = axios.create({ baseURL: "/v1" });

api.interceptors.request.use((cfg) => {
  const token = sessionStorage.getItem("okta_token");
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});