import { defineStore } from "pinia";
import { ref } from "vue";
import { api } from "../services/api";

export const useNotifications = defineStore("notifications", () => {
  const unreadCount = ref(0);
  let timer;

  async function refresh() {
    if (!sessionStorage.getItem("rf_access")) {
      unreadCount.value = 0;
      return;
    }
    try {
      const { data } = await api.get("notifications/unread-count/");
      unreadCount.value = data.count || 0;
    } catch {
      // Keep the last known badge count if the server is briefly unavailable.
    }
  }

  function stop() {
    if (timer) clearInterval(timer);
    timer = undefined;
    unreadCount.value = 0;
  }

  function start() {
    if (timer) clearInterval(timer);
    refresh();
    timer = setInterval(refresh, 15000);
  }

  return { unreadCount, refresh, start, stop };
});
