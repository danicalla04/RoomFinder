<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { api, errorMessage, money, today } from "../services/api";
import BookingChat from "../components/BookingChat.vue";
import {
  CalendarDays,
  ArrowUpRight,
  Check,
  Download,
  Star,
  MessageCircle,
} from "lucide-vue-next";
const bookings = ref([]),
  loading = ref(true),
  error = ref(""),
  filter = ref("current"),
  cancelId = ref(null),
  requestCancelId = ref(null),
  checkoutId = ref(null),
  now = ref(Date.now()),
  busy = ref(false),
  reviewId = ref(null),
  review = ref({ rating: 5, comment: "" }),
  notice = ref("");
const chatBooking = ref(null);
let timer;
const isHistory = (b) => ["cancelled", "rejected"].includes(b.status) || !!b.checked_out_at || b.check_out < today();
const visibleBookings = computed(() => bookings.value.filter((b) => filter.value === "history" ? isHistory(b) : !isHistory(b)));
const canRequestCancellation = (b) => b.can_request_cancellation;
const canCancel = (b) => b.can_cancel && now.value < new Date(b.cancel_deadline).getTime();
async function load() {
  try {
    bookings.value = (await api.get("bookings/")).data;
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
async function cancel() {
  busy.value = true;
  error.value = "";
  try {
    await api.post(`bookings/${cancelId.value}/cancel/`);
    cancelId.value = null;
    notice.value = "Booking cancelled. The room is available again.";
    await load();
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    busy.value = false;
  }
}
async function requestCancellation() {
  busy.value = true;
  error.value = "";
  try {
    await api.post(`bookings/${requestCancelId.value}/request_cancel/`);
    requestCancelId.value = null;
    notice.value = "Cancellation request sent to the hotel owner. Contact them about your refund.";
    await load();
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    busy.value = false;
  }
}
async function checkout() {
  busy.value = true;
  error.value = "";
  try {
    await api.post(`bookings/${checkoutId.value}/checkout/`);
    checkoutId.value = null;
    notice.value = "Check-out recorded. Thank you for staying with us.";
    await load();
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    busy.value = false;
  }
}
async function saveReview() {
  busy.value = true;
  error.value = "";
  try {
    await api.post("reviews/", { ...review.value, booking: reviewId.value });
    reviewId.value = null;
    review.value = { rating: 5, comment: "" };
    notice.value = "Thank you. Your review is published.";
    await load();
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    busy.value = false;
  }
}
function download(b) {
  const blob = new Blob(
    [
      `ROOMFINDER RESERVATION
Reference: ${b.reference}
${b.hotel_name} - Room ${b.room_number}
${b.check_in} to ${b.check_out}
Guests: ${b.guests}
Total: ${money(b.total)}
Status: ${b.status}
`,
    ],
    { type: "text/plain" },
  );
  const u = URL.createObjectURL(blob),
    a = document.createElement("a");
  a.href = u;
  a.download = `roomfinder-${b.reference}.txt`;
  a.click();
  URL.revokeObjectURL(u);
}
onMounted(() => { load(); timer = setInterval(() => { now.value = Date.now(); }, 15000); });
onBeforeUnmount(() => clearInterval(timer));
</script>
<template>
  <section class="section page">
    <span class="eyebrow">MY BOOKINGS</span>
    <div class="section-heading">
      <h1>My bookings<span>.</span></h1>
      <RouterLink to="/" class="button small"
        >Find another stay <ArrowUpRight :size="17"
      /></RouterLink>
    </div>
    <p class="lead">All your reservations, in one comfortable place.</p>
    <div class="tabs">
      <button
        v-for="s in ['current', 'history']"
        :class="{ active: filter === s }"
        @click="filter = s"
      >
        {{ s === 'current' ? 'Current & upcoming' : 'History' }}
      </button>
    </div>
    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="loading">Loading your stays...</p>
    <div class="reservation-list">
      <article
        v-for="b in visibleBookings" :key="b.id"
      >
        <div class="reservation-icon"><CalendarDays :size="29" /></div>
        <div class="reservation-info">
          <span class="badge" :class="b.status">{{ b.checked_out_at ? 'checked out' : b.status === 'pending' ? 'Awaiting owner approval' : b.status }}</span>
          <h3>{{ b.hotel_name }}</h3>
          <p>
            Room {{ b.room_number }} · {{ b.guests }} guests ·
            {{ b.check_in }} · {{ b.check_out }}
          </p>
          <small class="reference">{{ b.reference }}</small
          ><small
            >Total {{ money(b.total) }}</small
          >
          <small v-if="b.status === 'pending'">You may cancel directly within two hours of requesting, before check-in day.</small>
          <small v-if="b.status === 'confirmed'">Cancellation requests go to the owner for approval.</small>
        </div>
        <div class="reservation-actions">
          <button class="text-button" @click="chatBooking = b"><MessageCircle :size="16" />Message hotel</button>
          <button class="text-button" @click="download(b)">
            <Download :size="16" />Booking details</button
          ><button
            v-if="canRequestCancellation(b)"
            class="text-button danger"
            @click="requestCancelId = b.id"
          >
            Request cancellation</button
          ><span v-if="b.cancellation_requested" class="muted">Cancellation request waiting for owner</span
          ><button
            v-if="b.status === 'pending' && canCancel(b)"
            class="text-button danger"
            @click="cancelId = b.id"
          >
            Cancel booking</button
          ><small v-if="b.status === 'pending' && !canCancel(b)" class="muted">Cancellation window closed</small
          ><button
            v-if="b.status === 'confirmed' && !b.checked_out_at && b.check_in <= today()"
            class="text-button"
            @click="checkoutId = b.id"
          >Check out</button
          ><button
            v-if="
              b.status === 'confirmed' && (b.checked_out_at || b.check_out <= today()) && !b.reviewed
            "
            class="text-button"
            @click="reviewId = b.id"
          >
            <Star :size="16" />Write a review</button
          ><span v-if="b.reviewed" class="muted"
            ><Check :size="14" />Reviewed</span
          >
        </div>
      </article>
    </div>
    <div v-if="!loading && !bookings.length" class="empty">
      <CalendarDays :size="36" />
      <h3>Your next adventure is waiting.</h3>
      <p>Find a place you love and choose your room.</p>
    </div>
    <p v-else-if="!loading && !visibleBookings.length" class="empty">No bookings in this section yet.</p>
    <div v-if="chatBooking" class="modal-backdrop" @click.self="chatBooking = null">
      <BookingChat :booking="chatBooking" @close="chatBooking = null" />
    </div>
    <div v-if="cancelId || requestCancelId || checkoutId || reviewId" class="modal-backdrop">
      <section
        class="modal"
        role="dialog"
        aria-modal="true"
        :aria-label="cancelId ? 'Cancel booking' : requestCancelId ? 'Request cancellation' : checkoutId ? 'Check out' : 'Review stay'"
      >
        <template v-if="cancelId"
          ><h2>Change of plans?</h2>
          <p>
            Your booking will be cancelled and the room will become available again.
          </p>
          <p class="muted">RoomFinder is not currently processing payments or issuing refunds. If you paid the property directly, contact the owner to discuss a refund.</p>
          <button class="button full" :disabled="busy" @click="cancel">
            {{ busy ? "Cancelling..." : "Confirm cancellation" }}</button
          ><button class="text-button" @click="cancelId = null">
            Keep my reservation
          </button></template
        >
        <template v-else-if="requestCancelId"><h2>Request to cancel?</h2><p>The hotel owner must approve your request before the booking is cancelled.</p><p class="muted">For your refund, contact the hotel owner. RoomFinder does not send refunds.</p><button class="button full" :disabled="busy" @click="requestCancellation">{{ busy ? 'Sending...' : 'Send cancellation request' }}</button><button class="text-button" :disabled="busy" @click="requestCancelId = null">Keep my booking</button></template>
        <template v-else-if="checkoutId"><h2>Check out now?</h2><p>This records that you have finished your stay.</p><button class="button full" :disabled="busy" @click="checkout">{{ busy ? 'Saving...' : 'Confirm check-out' }}</button><button class="text-button" @click="checkoutId = null">Stay on this page</button></template>
        <form v-else @submit.prevent="saveReview">
          <h2>How was your stay?</h2>
          <label
            >Rating<select v-model.number="review.rating">
              <option v-for="n in 5" :value="n">{{ n }} stars</option>
            </select></label
          ><label
            >Your review<textarea
              v-model="review.comment"
              required
              minlength="5"
              maxlength="2000"
              rows="4"
            ></textarea></label
          ><button class="button full" :disabled="busy">Publish review</button
          ><button type="button" class="text-button" @click="reviewId = null">
            Close
          </button>
        </form>
        <p v-if="error" class="error">{{ error }}</p>
      </section>
    </div>
  </section>
</template>
