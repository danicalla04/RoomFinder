<script setup>
import { ref, nextTick, onMounted, onBeforeUnmount } from "vue";
import { MessageCircle, Send, X } from "lucide-vue-next";
import { api, errorMessage } from "../services/api";
import { useAuth } from "../stores/auth";
import { useMessages } from "../stores/messages";

const props = defineProps({ booking: { type: Object, required: true }, embedded: { type: Boolean, default: false }, title: { type: String, default: "" } });
const emit = defineEmits(["close"]);
const auth = useAuth();
const messagesStore = useMessages();
const messages = ref([]), draft = ref(""), error = ref(""), loading = ref(true), sending = ref(false);
const list = ref(null);
let refreshTimer;
async function load(silent = false) {
  try {
    const { data } = await api.get(`bookings/${props.booking.id}/messages/`);
    messages.value = data;
    messagesStore.refresh();
    await nextTick();
    if (list.value) list.value.scrollTop = list.value.scrollHeight;
  } catch (e) {
    if (!silent) error.value = errorMessage(e);
  } finally { loading.value = false; }
}
async function send() {
  const message = draft.value.trim();
  if (!message || sending.value) return;
  sending.value = true; error.value = "";
  try { await api.post(`bookings/${props.booking.id}/messages/`, { message }); draft.value = ""; await load(); }
  catch (e) { error.value = errorMessage(e); }
  finally { sending.value = false; }
}
function formatDate(value) { return new Date(value).toLocaleString([], { dateStyle: "short", timeStyle: "short" }); }
onMounted(() => { load(); refreshTimer = setInterval(() => load(true), 5000); });
onBeforeUnmount(() => clearInterval(refreshTimer));
</script>
<template>
  <section class="booking-chat" :class="{ embedded }" :role="embedded ? 'region' : 'dialog'" :aria-modal="embedded ? undefined : 'true'" aria-label="Booking conversation">
    <header class="booking-chat-head">
      <div class="booking-chat-title-icon"><MessageCircle :size="19" /></div>
      <div class="booking-chat-title"><strong>{{ title || booking.hotel_name }}</strong><small>{{ booking.hotel_name }} · Room {{ booking.room_number }} · {{ booking.check_in }} to {{ booking.check_out }}</small></div>
      <button class="booking-chat-close" aria-label="Close conversation" @click="emit('close')"><X :size="20" /></button>
    </header>
    <div ref="list" class="booking-chat-messages" aria-live="polite">
      <p v-if="loading" class="booking-chat-empty">Loading conversation…</p>
      <p v-else-if="!messages.length" class="booking-chat-empty">Ask the hotel owner a question about this booking.</p>
      <article v-for="m in messages" :key="m.id" class="booking-chat-bubble" :class="{ mine: m.sender === auth.user?.id }"><small>{{ m.sender_name }} · {{ formatDate(m.created_at) }}</small><p>{{ m.message }}</p></article>
    </div>
    <p v-if="error" class="error booking-chat-error" role="alert">{{ error }}</p>
    <form class="booking-chat-compose" @submit.prevent="send"><textarea v-model="draft" maxlength="2000" rows="2" placeholder="Write a message…" aria-label="Message" required></textarea><button class="button" :disabled="sending || !draft.trim()"><Send :size="16" />{{ sending ? 'Sending…' : 'Send' }}</button></form>
    <small class="booking-chat-private">Only you and the hotel owner can see this conversation.</small>
  </section>
</template>
<style scoped>
.booking-chat.embedded{width:100%;height:100%;max-height:none;border-radius:0;box-shadow:none}.booking-chat.embedded .booking-chat-close{display:none}
.booking-chat{width:min(560px,calc(100vw - 32px));height:min(680px,calc(100vh - 40px));display:flex;flex-direction:column;background:#fff;border-radius:20px;box-shadow:0 24px 80px #17211c40;overflow:hidden;color:#26332d}.booking-chat-head{display:flex;align-items:center;gap:12px;padding:18px 20px;border-bottom:1px solid #e8ece8}.booking-chat-title-icon{width:40px;height:40px;border-radius:50%;display:grid;place-items:center;background:#e8f2ed;color:#1f5c4d}.booking-chat-title{flex:1;min-width:0;display:flex;flex-direction:column;gap:4px}.booking-chat-title small,.booking-chat-bubble small{color:#738078;font-size:12px}.booking-chat-close{border:0;background:transparent;color:#59665f;padding:8px;cursor:pointer}.booking-chat-messages{flex:1;overflow:auto;padding:20px;display:flex;flex-direction:column;gap:12px;background:#f7f8f5}.booking-chat-empty{margin:auto;color:#77837b;text-align:center;max-width:260px}.booking-chat-bubble{align-self:flex-start;max-width:82%;padding:10px 13px;border-radius:15px 15px 15px 4px;background:#fff;box-shadow:0 1px 3px #17211c12;overflow-wrap:anywhere}.booking-chat-bubble.mine{align-self:flex-end;background:#1f5c4d;color:#fff;border-radius:15px 15px 4px 15px}.booking-chat-bubble.mine small{color:#d2e3db}.booking-chat-bubble p{white-space:pre-wrap;margin:5px 0 0}.booking-chat-compose{display:flex;align-items:flex-end;gap:10px;padding:14px 18px 8px}.booking-chat-compose textarea{flex:1;resize:vertical;min-height:46px;max-height:120px;border:1px solid #d9e0da;border-radius:12px;padding:11px;font:inherit}.booking-chat-compose .button{white-space:nowrap}.booking-chat-private{padding:0 20px 15px;color:#7a857e}.booking-chat-error{margin:0 18px}.booking-chat-compose .button:disabled{opacity:.55;cursor:not-allowed}@media(max-width:520px){.booking-chat-compose{align-items:stretch;flex-direction:column}.booking-chat-compose .button{align-self:flex-end}}
</style>
