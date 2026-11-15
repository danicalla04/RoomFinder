import { defineStore } from "pinia";
import { ref } from "vue";
import { api } from "../services/api";

export const useMessages = defineStore("messages", () => {
  const unreadCount = ref(0);
  let timer;
  async function refresh() {
    if (!sessionStorage.getItem("rf_access")) { unreadCount.value = 0; return; }
    try {
      const { data } = await api.get("bookings/unread-messages/");
      unreadCount.value = data.count || 0;
    } catch { /* Keep the last count during brief network interruptions. */ }
  }
  function stop() {
    if (timer) clearInterval(timer);
    timer = undefined;
    unreadCount.value = 0;
  }
  function start() {
    if (timer) clearInterval(timer);
    refresh();
    timer = setInterval(refresh, 10000);
  }
  return { unreadCount, refresh, start, stop };
});
