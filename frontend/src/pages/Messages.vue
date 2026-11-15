<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { ArrowLeft, MessageCircle, Search } from "lucide-vue-next";
import { api, errorMessage } from "../services/api";
import { useAuth } from "../stores/auth";
import { useMessages } from "../stores/messages";
import BookingChat from "../components/BookingChat.vue";

const auth = useAuth(), messagesStore = useMessages();
const threads = ref([]), activeId = ref(null), error = ref(""), loading = ref(true), search = ref("");
const activeBooking = computed(() => threads.value.find((thread) => thread.id === activeId.value));
const visibleThreads = computed(() => {
  const query = search.value.trim().toLowerCase();
  return query ? threads.value.filter((thread) => `${thread.hotel_name} ${thread.customer_display_name} ${thread.room_number}`.toLowerCase().includes(query)) : threads.value;
});
let timer;
async function load(silent = false) {
  try { threads.value = (await api.get("bookings/conversations/")).data; }
  catch (e) { if (!silent) error.value = errorMessage(e); }
  finally { loading.value = false; }
}
function otherPerson(thread) { return auth.user?.role === "owner" ? thread.customer_display_name : thread.hotel_name; }
function lastMessage(thread) { return `${thread.last_message.sender === auth.user?.id ? "You: " : ""}${thread.last_message.message}`; }
onMounted(() => { load(); messagesStore.refresh(); timer = setInterval(() => { load(true); messagesStore.refresh(); }, 10000); });
onBeforeUnmount(() => clearInterval(timer));
</script>
<template>
  <section class="section page messages-page">
    <span class="eyebrow">YOUR CONVERSATIONS</span>
    <h1>Messages<span>.</span></h1>
    <p class="lead">Talk with guests or hotel owners about a booking.</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <div class="messenger-layout">
      <aside class="messenger-sidebar">
        <label class="messenger-search"><Search :size="17" /><input v-model="search" placeholder="Search conversations" aria-label="Search conversations" /></label>
        <div v-if="loading" class="messenger-empty">Loading conversations…</div>
        <button v-for="thread in visibleThreads" :key="thread.id" class="messenger-thread" :class="{ active: activeId === thread.id }" @click="activeId = thread.id">
          <span class="messenger-avatar">{{ otherPerson(thread).slice(0, 1).toUpperCase() }}</span>
          <span class="messenger-thread-copy"><strong>{{ otherPerson(thread) }}</strong><small>{{ thread.hotel_name }} · Room {{ thread.room_number }}</small><span>{{ lastMessage(thread) }}</span></span>
          <span v-if="thread.unread_count" class="messenger-unread">{{ thread.unread_count > 99 ? '99+' : thread.unread_count }}</span>
        </button>
        <div v-if="!loading && !visibleThreads.length" class="messenger-empty"><MessageCircle :size="25" /><p>{{ threads.length ? 'No conversations match your search.' : 'Your booking conversations will appear here.' }}</p></div>
      </aside>
      <main class="messenger-conversation">
        <button v-if="activeBooking" class="messenger-mobile-back" @click="activeId = null"><ArrowLeft :size="16" />All conversations</button>
        <BookingChat v-if="activeBooking" :key="activeBooking.id" :booking="activeBooking" :embedded="true" :title="otherPerson(activeBooking)" />
        <div v-else class="messenger-placeholder"><MessageCircle :size="40" /><h2>Select a conversation</h2><p>Choose a booking chat to read or send a message.</p></div>
      </main>
    </div>
  </section>
</template>
<style scoped>
.messenger-layout{display:grid;grid-template-columns:minmax(270px,350px) minmax(0,1fr);height:min(680px,calc(100vh - 300px));min-height:440px;margin-top:26px;border:1px solid #e1e7e1;border-radius:18px;overflow:hidden;background:#fff}.messenger-sidebar{display:flex;flex-direction:column;overflow:auto;border-right:1px solid #e5eae5;background:#fff}.messenger-search{display:flex;align-items:center;gap:9px;margin:14px;padding:10px 12px;border-radius:10px;background:#f4f6f3;color:#77847c}.messenger-search input{width:100%;border:0;outline:0;background:transparent;font:inherit;font-size:13px}.messenger-thread{display:flex;align-items:center;gap:11px;width:100%;padding:13px 14px;border:0;border-top:1px solid #f0f2ef;background:#fff;text-align:left;cursor:pointer}.messenger-thread:hover,.messenger-thread.active{background:#f2f7f3}.messenger-avatar{display:grid;place-items:center;flex:0 0 42px;height:42px;border-radius:50%;background:#e5efe8;color:#235944;font-weight:700}.messenger-thread-copy{display:flex;flex-direction:column;gap:3px;min-width:0;flex:1}.messenger-thread-copy strong,.messenger-thread-copy small,.messenger-thread-copy span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.messenger-thread-copy strong{font-size:13px}.messenger-thread-copy small{color:#77847c;font-size:11px}.messenger-thread-copy span{color:#69756e;font-size:12px}.messenger-unread{display:grid;place-items:center;min-width:20px;height:20px;padding:0 5px;border-radius:99px;background:#c93636;color:#fff;font-size:10px;font-weight:700}.messenger-conversation{min-width:0;min-height:0;background:#f7f8f5}.messenger-placeholder,.messenger-empty{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:9px;color:#77847c;text-align:center;padding:20px}.messenger-placeholder{height:100%}.messenger-placeholder h2{color:#26332d;font-size:23px}.messenger-placeholder p,.messenger-empty p{font-size:13px}.messenger-mobile-back{display:none}.messages-page :deep(.booking-chat.embedded){width:100%;height:100%;max-height:none;border-radius:0;box-shadow:none}.messages-page :deep(.booking-chat.embedded .booking-chat-close){display:none}@media(max-width:760px){.messenger-layout{grid-template-columns:1fr;height:calc(100vh - 245px);min-height:500px}.messenger-conversation{display:none}.messenger-sidebar{border-right:0}.messenger-layout:has(.messenger-conversation .booking-chat){grid-template-columns:0 minmax(0,1fr)}.messenger-layout:has(.booking-chat) .messenger-sidebar{display:none}.messenger-layout:has(.booking-chat) .messenger-conversation{display:block}.messenger-mobile-back{display:inline-flex;align-items:center;gap:8px;margin:8px;padding:6px 10px;border:0;background:transparent;color:#1f5c4d}}
</style>
