<script setup>
import { ref, onMounted } from "vue";
import { api, errorMessage } from "../services/api";
import { Bell, Check, MessageCircle } from "lucide-vue-next";
import BookingChat from "../components/BookingChat.vue";
import { useNotifications } from "../stores/notifications";
const items = ref([]),
  error = ref(""),
  loading = ref(true),
  chatBooking = ref(null),
  busyBooking = ref(false);
const notifications = useNotifications();
async function load() {
  try {
    items.value = (await api.get("notifications/")).data;
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
async function read(n) {
  try {
    await api.patch(`notifications/${n.id}/`, { read: true });
    n.read = true;
    notifications.refresh();
  } catch (e) {
    error.value = errorMessage(e);
  }
}
async function all() {
  try {
    await api.post("notifications/read_all/");
    items.value.forEach((n) => (n.read = true));
    notifications.refresh();
  } catch (e) {
    error.value = errorMessage(e);
  }
}
async function openConversation(n) {
  if (!n.booking || busyBooking.value) return;
  busyBooking.value = true;
  error.value = "";
  try {
    const { data } = await api.get(`bookings/${n.booking}/`);
    chatBooking.value = data;
    if (!n.read) await read(n);
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    busyBooking.value = false;
  }
}
onMounted(load);
</script>
<template>
  <section class="section page narrow">
    <span class="eyebrow">A LITTLE UPDATE</span>
    <div class="section-heading">
      <h1>Your notifications<span>.</span></h1>
      <button class="text-button" @click="all">
        <Check :size="16" />Mark all read
      </button>
    </div>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="loading">Loading updates...</p>
    <article
      class="notification"
      v-for="n in items"
      :class="{ unread: !n.read }"
    >
      <Bell :size="22" />
      <div>
        <h3>{{ n.title }}</h3>
        <p>{{ n.message }}</p>
        <small>{{ new Date(n.created_at).toLocaleString() }}</small
        ><button v-if="n.booking" class="text-button" :disabled="busyBooking" @click="openConversation(n)">
          <MessageCircle :size="15" />Open conversation
        </button><button v-if="!n.read" class="text-button" @click="read(n)">
          Mark as read
        </button>
      </div>
    </article>
    <p v-if="!loading && !items.length" class="empty">You're all caught up.</p>
    <div v-if="chatBooking" class="modal-backdrop" @click.self="chatBooking = null">
      <BookingChat :booking="chatBooking" @close="chatBooking = null" />
    </div>
  </section>
</template>
