import { defineStore } from "pinia";
import { ref } from "vue";
import { api } from "../services/api";
export const useAuth = defineStore("auth", () => {
  const user = ref(null),
    ready = ref(false);
  async function load() {
    const token = sessionStorage.getItem("rf_access");
    if (!token) {
      ready.value = true;
      return;
    }
    const cached = sessionStorage.getItem("rf_user");
    if (cached) {
      try {
        user.value = JSON.parse(cached);
        ready.value = true;
      } catch {
        sessionStorage.removeItem("rf_user");
      }
    }
    const refresh = async () => {
      const profile = (await api.get("auth/me/")).data;
      if (sessionStorage.getItem("rf_access")) {
        user.value = profile;
        sessionStorage.setItem("rf_user", JSON.stringify(profile));
      }
    };
    try {
      if (ready.value) {
        refresh().catch(() => logout());
      } else {
        await refresh();
      }
    } finally {
      ready.value = true;
    }
  }
  async function login(credentials) {
    const { data } = await api.post("auth/token/", credentials);
    sessionStorage.removeItem("rf_user");
    sessionStorage.removeItem("rf_admin_users");
    sessionStorage.setItem("rf_access", data.access);
    sessionStorage.setItem("rf_refresh", data.refresh);
    const profile = (await api.get("auth/me/")).data;
    user.value = profile;
    sessionStorage.setItem("rf_user", JSON.stringify(profile));
    ready.value = true;
  }
  function logout() {
    sessionStorage.removeItem("rf_access");
    sessionStorage.removeItem("rf_refresh");
    sessionStorage.removeItem("rf_user");
    sessionStorage.removeItem("rf_admin_users");
    user.value = null;
  }
  window.addEventListener("rf-expired", logout);
  return { user, ready, load, login, logout };
});
