<script setup>
import { ref, onMounted } from "vue";
import { api, errorMessage, money, today } from "../services/api";
import {
  CalendarDays,
  ArrowUpRight,
  Check,
  Download,
  Star,
} from "lucide-vue-next";
const bookings = ref([]),
  loading = ref(true),
  error = ref(""),
  filter = ref("all"),
  cancelId = ref(null),
  busy = ref(false),
  reviewId = ref(null),
  review = ref({ rating: 5, comment: "" }),
  notice = ref("");
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
    notice.value =
      "Reservation cancelled. Your simulated payment has been refunded.";
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
Simulated payment: ${b.payment.status}
No real money was charged.`,
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
onMounted(load);
</script>
<template>
  <section class="section page">
    <span class="eyebrow">YOUR TRAVEL JOURNAL</span>
    <div class="section-heading">
      <h1>Good stays ahead<span>.</span></h1>
      <RouterLink to="/" class="button small"
        >Find another stay <ArrowUpRight :size="17"
      /></RouterLink>
    </div>
    <p class="lead">All your reservations, in one comfortable place.</p>
    <div class="tabs">
      <button
        v-for="s in ['all', 'confirmed', 'cancelled']"
        :class="{ active: filter === s }"
        @click="filter = s"
      >
        {{ s }}
      </button>
    </div>
    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="loading">Loading your stays...</p>
    <div class="reservation-list">
      <article
        v-for="b in bookings.filter(
          (b) => filter === 'all' || b.status === filter,
        )"
      >
        <div class="reservation-icon"><CalendarDays :size="29" /></div>
        <div class="reservation-info">
          <span class="badge" :class="b.status">{{ b.status }}</span>
          <h3>{{ b.hotel_name }}</h3>
          <p>
            Room {{ b.room_number }} · {{ b.guests }} guests ·
            {{ b.check_in }} · {{ b.check_out }}
          </p>
          <small class="reference">{{ b.reference }}</small
          ><small
            >Simulated payment {{ b.payment?.status }} ·
            {{ money(b.total) }}</small
          >
        </div>
        <div class="reservation-actions">
          <button class="text-button" @click="download(b)">
            <Download :size="16" />Confirmation</button
          ><button
            v-if="b.status === 'confirmed' && b.check_in > today()"
            class="text-button danger"
            @click="cancelId = b.id"
          >
            Cancel reservation</button
          ><button
            v-if="
              b.status === 'confirmed' && b.check_out <= today() && !b.reviewed
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
    <div v-if="cancelId || reviewId" class="modal-backdrop">
      <section
        class="modal"
        role="dialog"
        aria-modal="true"
        :aria-label="cancelId ? 'Cancel reservation' : 'Review stay'"
      >
        <template v-if="cancelId"
          ><h2>Change of plans?</h2>
          <p>
            Your room will become available again and the simulated payment will
            be marked refunded.
          </p>
          <button class="button full" :disabled="busy" @click="cancel">
            {{ busy ? "Cancelling..." : "Confirm cancellation" }}</button
          ><button class="text-button" @click="cancelId = null">
            Keep my reservation
          </button></template
        >
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
