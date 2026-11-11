import axios from "axios";
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1/",
  timeout: 20000,
});
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("rf_access");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
let refreshing;
api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    if (
      error.response?.status === 401 &&
      !original._retry &&
      !original.url.includes("auth/token") &&
      sessionStorage.getItem("rf_refresh")
    ) {
      original._retry = true;
      try {
        refreshing ||= axios
          .post(`${api.defaults.baseURL}auth/token/refresh/`, {
            refresh: sessionStorage.getItem("rf_refresh"),
          })
          .finally(() => (refreshing = null));
        const { data } = await refreshing;
        sessionStorage.setItem("rf_access", data.access);
        original.headers.Authorization = `Bearer ${data.access}`;
        return api(original);
      } catch {
        sessionStorage.removeItem("rf_access");
        sessionStorage.removeItem("rf_refresh");
        window.dispatchEvent(new Event("rf-expired"));
      }
    }
    return Promise.reject(error);
  },
);
export function errorMessage(error) {
  const d = error.response?.data;
  if (!d)
    return "Unable to reach RoomFinder. Check that the Django server is running.";
  if (typeof d === "string")
    return "The server could not complete this request.";
  return Object.entries(d)
    .map(
      ([k, v]) =>
        `${k === "detail" || k === "non_field_errors" ? "" : k + ": "}${Array.isArray(v) ? v.join(" ") : v}`,
    )
    .join(" ");
}
export const money = (value) =>
  new Intl.NumberFormat("en-PH", {
    style: "currency",
    currency: "PHP",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
export const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
export function nextDay(value, days = 1) {
  const d = new Date(value + "T12:00:00");
  d.setDate(d.getDate() + days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
