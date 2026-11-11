<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  MapPin,
  Star,
  ArrowLeft,
  Check,
  ShieldCheck,
  BedDouble,
  Users,
  Maximize,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  X,
  ArrowRight,
} from "lucide-vue-next";
import { api, errorMessage, money, today, nextDay } from "../services/api";
import { useAuth } from "../stores/auth";
import HotelMap from "../components/HotelMap.vue";
const route = useRoute(),
  router = useRouter(),
  auth = useAuth(),
  hotel = ref(null),
  floors = ref([]),
  rooms = ref([]),
  reviews = ref([]),
  promos = ref([]),
  floorId = ref(null),
  selected = ref(null),
  error = ref(""),
  busy = ref(false),
  loading = ref(true),
  photoIndex = ref(0),
  showMap = ref(false),
  confirmed = ref(null);
const form = ref({
  check_in: route.query.check_in || today(),
  check_out: route.query.check_out || nextDay(today()),
  guests: Number(route.query.guests) || 2,
  promotion_code: "",
  special_requests: "",
});
const appliedDates = ref(null),
  checkingRooms = ref(false);
const datesDirty = computed(
  () =>
    !!appliedDates.value &&
    (appliedDates.value.check_in !== form.value.check_in ||
      appliedDates.value.check_out !== form.value.check_out),
);
function roomState(room) {
  const state =
    room.availability_status ||
    (!room.active ? "unavailable" : room.available ? "available" : "booked");
  if (state !== "available") return state;
  if (room.capacity < form.value.guests) return "capacity";
  return selected.value?.id === room.id ? "selected" : "available";
}
function roomLabel(room) {
  return {
    available: "Available",
    booked: "Booked",
    unavailable: "Unavailable",
    capacity: "Too small",
    selected: "Selected",
  }[roomState(room)];
}
const floor = computed(() => floors.value.find((f) => f.id === floorId.value)),
  floorRooms = computed(() =>
    rooms.value.filter((r) => r.floor === floorId.value),
  ),
  nights = computed(() =>
    Math.max(
      0,
      Math.round(
        (new Date(form.value.check_out) - new Date(form.value.check_in)) /
          86400000,
      ),
    ),
  ),
  promo = computed(() =>
    promos.value.find(
      (p) => p.code === form.value.promotion_code.trim().toUpperCase(),
    ),
  ),
  subtotal = computed(() => Number(selected.value?.price || 0) * nights.value),
  total = computed(
    () => subtotal.value * (1 - (promo.value?.percent || 0) / 100),
  );
const gallery = computed(() =>
  [
    ...(hotel.value?.photos || []),
    ...rooms.value.flatMap((r) => r.photos),
  ].filter((p, i, a) => a.findIndex((x) => x.image === p.image) === i),
);
const gridSlots = computed(() => {
  if (!floor.value) return [];
  const count =
    Math.max(2, ...floorRooms.value.map((r) => r.row + 1)) *
    floor.value.columns;
  return Array.from({ length: count }, (_, i) =>
    floorRooms.value.find(
      (r) =>
        r.row === Math.floor(i / floor.value.columns) &&
        r.column === i % floor.value.columns,
    ),
  );
});
async function refreshRooms() {
  error.value = "";
  selected.value = null;
  checkingRooms.value = true;
  const period = {
    check_in: form.value.check_in,
    check_out: form.value.check_out,
  };
  try {
    rooms.value = (
      await api.get("rooms/", {
        params: {
          hotel: route.params.id,
          ...period,
        },
      })
    ).data;
    appliedDates.value = period;
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    checkingRooms.value = false;
  }
}
async function load() {
  try {
    const [h, f, r, p] = await Promise.all([
      api.get(`hotels/${route.params.id}/`),
      api.get("floors/", { params: { hotel: route.params.id } }),
      api.get("reviews/", { params: { hotel: route.params.id } }),
      api.get("promotions/", { params: { hotel: route.params.id } }),
    ]);
    hotel.value = h.data;
    floors.value = f.data;
    floorId.value = f.data[0]?.id;
    reviews.value = r.data;
    promos.value = p.data;
    await refreshRooms();
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
function selectRoom(room) {
  if (
    !datesDirty.value &&
    !checkingRooms.value &&
    room.available &&
    room.capacity >= form.value.guests
  )
    selected.value = room;
}
async function reserve() {
  if (!auth.user) {
    router.push({ path: "/login", query: { next: route.fullPath } });
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    const { data } = await api.post("bookings/", {
      ...form.value,
      room: selected.value.id,
    });
    confirmed.value = data;
    await refreshRooms();
  } catch (e) {
    error.value = errorMessage(e);
    await refreshRoomsKeepError();
  } finally {
    busy.value = false;
  }
}
async function refreshRoomsKeepError() {
  const previous = error.value;
  await refreshRooms();
  error.value = previous;
}
watch(
  () => form.value.guests,
  () => {
    if (selected.value?.capacity < form.value.guests) selected.value = null;
  },
);
watch(
  () => [form.value.check_in, form.value.check_out],
  () => {
    selected.value = null;
  },
);
onMounted(load);
</script>
<template>
  <section class="section page" v-if="loading">
    <div class="skeleton"></div>
  </section>
  <section class="section page" v-else-if="hotel">
    <RouterLink to="/" class="back-link"
      ><ArrowLeft :size="16" />Back to stays</RouterLink
    >
    <div class="hotel-title">
      <div>
        <span class="eyebrow"
          >{{ hotel.stars }}-STAR CATEGORY ·
          {{ hotel.city.toUpperCase() }}</span
        >
        <h1>{{ hotel.name }}</h1>
        <p>
          <MapPin :size="16" />{{ hotel.address }}, {{ hotel.city }}
          <button class="text-button" @click="showMap = !showMap">
            {{ showMap ? "Hide map" : "View map" }}
          </button>
        </p>
      </div>
      <span class="rating large"
        ><Star fill="currentColor" :size="20" />{{
          hotel.rating ? Number(hotel.rating).toFixed(1) : "New"
        }}<small>{{ hotel.review_count }} reviews</small></span
      >
    </div>
    <p class="classification-note">
      Property stars are an owner-provided category, not official accreditation.
      Guest ratings come from completed-stay reviews.
    </p>
    <HotelMap v-if="showMap" :hotels="[hotel]" />
    <div v-if="gallery.length" class="gallery">
      <img
        :src="gallery[photoIndex % gallery.length].image"
        :alt="gallery[photoIndex % gallery.length].caption || hotel.name"
      />
      <div class="gallery-controls">
        <button
          aria-label="Previous image"
          @click="
            photoIndex = (photoIndex - 1 + gallery.length) % gallery.length
          "
        >
          <ChevronLeft /></button
        ><span
          >{{ (photoIndex % gallery.length) + 1 }} / {{ gallery.length }}</span
        ><button aria-label="Next image" @click="photoIndex++">
          <ChevronRight />
        </button>
      </div>
      <span class="gallery-badge"
        ><ShieldCheck :size="16" />Verified RoomFinder property</span
      >
    </div>
    <div class="hotel-intro">
      <div>
        <h2>A little about your stay</h2>
        <p>{{ hotel.description }}</p>
      </div>
      <div class="amenities">
        <span v-for="a in hotel.amenities"><Check :size="16" />{{ a }}</span>
      </div>
    </div>
    <div class="booking-layout">
      <div>
        <div class="section-heading">
          <div>
            <span class="eyebrow">THE CHOICE IS YOURS</span>
            <h2>Pick your perfect room<span>.</span></h2>
          </div>
          <BedDouble :size="28" />
        </div>
        <form class="date-panel" @submit.prevent="refreshRooms">
          <label
            >Check in<input
              type="date"
              v-model="form.check_in"
              :min="today()"
              required /></label
          ><label
            >Check out<input
              type="date"
              v-model="form.check_out"
              :min="nextDay(form.check_in)"
              required /></label
          ><label
            >Guests<input
              type="number"
              min="1"
              max="12"
              v-model.number="form.guests"
              required /></label
          ><button class="button small">Check availability</button>
        </form>
        <p v-if="datesDirty" class="info-note">
          Dates changed. Check availability to refresh the room plan.
        </p>
        <p class="muted">
          Availability is for {{ appliedDates?.check_in || form.check_in }} ·
          {{ appliedDates?.check_out || form.check_out }}. Update dates, then
          check availability.
        </p>
        <div class="floor-tabs">
          <button
            v-for="f in floors"
            :class="{ active: floorId === f.id }"
            @click="floorId = f.id"
          >
            {{ f.name }} <small>Floor {{ f.number }}</small>
          </button>
        </div>
        <div v-if="floor" class="floor-plan">
          <div class="room-status-summary">
            <span
              >{{
                floorRooms.filter((r) => r.availability_status === "available")
                  .length
              }}
              available</span
            ><span
              >{{
                floorRooms.filter((r) => r.availability_status === "booked")
                  .length
              }}
              booked</span
            ><span
              >{{
                floorRooms.filter(
                  (r) => r.availability_status === "unavailable",
                ).length
              }}
              unavailable</span
            >
          </div>
          <div class="floor-screen">
            {{ hotel.name }} · {{ floor.name }} · Windows & view
          </div>
          <div class="room-grid" :style="{ '--columns': floor.columns }">
            <template v-for="(room, i) in gridSlots" :key="i"
              ><button
                v-if="room"
                :class="['room-seat', roomState(room)]"
                :data-state="roomState(room)"
                :disabled="
                  !room.available ||
                  room.capacity < form.guests ||
                  checkingRooms ||
                  datesDirty
                "
                @click="selectRoom(room)"
                :aria-label="`Room ${room.number}, ${room.kind}, ${money(room.price)} per night, ${roomLabel(room)}`"
                :title="`${roomLabel(room)} for the displayed dates`"
              >
                <BedDouble :size="21" /><strong>{{ room.number }}</strong
                ><small>{{ money(room.price) }}</small
                ><span class="room-state-text">{{ roomLabel(room) }}</span>
              </button>
              <div v-else class="room-gap"></div
            ></template>
          </div>
          <div class="hallway">HALLWAY &nbsp; · &nbsp; LIFT / STAIRS</div>
          <div class="legend">
            <span><i></i>Available</span
            ><span><i class="picked"></i>Your choice</span
            ><span><i class="booked"></i>Booked</span
            ><span><i class="taken"></i>Unavailable</span
            ><span><i class="capacity"></i>Too small</span>
          </div>
        </div>
        <p v-else class="empty">This property has no rooms listed yet.</p>
        <article v-if="selected" class="selected-room">
          <img
            v-if="selected.photos.length"
            :src="selected.photos[0].image"
            :alt="`Room ${selected.number}`"
          />
          <div>
            <span class="eyebrow">YOUR SELECTED ROOM</span>
            <h3>{{ selected.kind }} · Room {{ selected.number }}</h3>
            <p>{{ selected.description }}</p>
            <div class="room-facts">
              <span><BedDouble :size="16" />{{ selected.beds }}</span
              ><span><Users :size="16" />{{ selected.capacity }} guests</span
              ><span><Maximize :size="16" />{{ selected.area }} m²</span>
            </div>
          </div>
        </article>
      </div>
      <aside class="reservation-panel">
        <span class="eyebrow">YOUR NEXT CHAPTER</span>
        <h3>{{ selected ? "Make it yours." : "Your room is waiting." }}</h3>
        <p v-if="!selected">
          Choose an available room on the floor plan to see your reservation
          details.
        </p>
        <template v-else
          ><div class="price-head">
            {{ money(selected.price) }}<small> / night</small>
          </div>
          <div class="receipt-line">
            <span
              >{{ nights }} night{{ nights === 1 ? "" : "s" }} ·
              {{ form.guests }} guest{{ form.guests === 1 ? "" : "s" }}</span
            ><strong>Room {{ selected.number }}</strong>
          </div>
          <div class="receipt-line">
            <span>Room subtotal</span><span>{{ money(subtotal) }}</span>
          </div>
          <label
            >Promotion code<input
              v-model="form.promotion_code"
              placeholder="Have a code?"
              maxlength="32"
          /></label>
          <p v-if="promos.length" class="promo-hint">
            Available:
            {{ promos.map((p) => `${p.code} (${p.percent}% off)`).join(", ") }}
          </p>
          <div v-if="promo" class="receipt-line">
            <span>{{ promo.percent }}% saving</span
            ><span>? {{ money(subtotal - total) }}</span>
          </div>
          <div class="receipt-line total">
            <strong>Total</strong><strong>{{ money(total) }}</strong>
          </div>
          <label
            >Special requests<textarea
              v-model="form.special_requests"
              rows="2"
              maxlength="2000"
              placeholder="Anything we should know?"
            ></textarea>
          </label>
          <div class="simulation-note">
            <ShieldCheck :size="18" /><span
              >Simulated payment only.<small
                >No card details. No real charges.</small
              ></span
            >
          </div>
          <button
            class="button full"
            @click="reserve"
            :disabled="
              busy || nights < 1 || (auth.user && auth.user.role !== 'customer')
            "
          >
            {{
              busy
                ? "Confirming..."
                : auth.user
                  ? "Reserve & simulate payment"
                  : "Sign in to reserve"
            }}<ArrowRight :size="17" />
          </button>
          <p v-if="auth.user && auth.user.role !== 'customer'" class="muted">
            A customer account is required to reserve.
          </p>
          <small class="muted"
            >Free cancellation before check-in day.</small
          ></template
        >
        <p v-if="error" role="alert" class="error">{{ error }}</p>
      </aside>
    </div>
    <div class="reviews-section">
      <span class="eyebrow">FROM OUR GUESTS</span>
      <h2>A few words, a lot of good stays.</h2>
      <div class="review-grid">
        <article v-for="r in reviews">
          <span class="rating"
            ><Star :size="15" fill="currentColor" />{{ r.rating }} / 5</span
          >
          <p>&ldquo;{{ r.comment }}&rdquo;</p>
          <strong>{{ r.author || "RoomFinder guest" }}</strong
          ><small
            >Verified stay ·
            {{ new Date(r.created_at).toLocaleDateString() }}</small
          >
        </article>
        <p v-if="!reviews.length" class="muted">
          Be the first to review after your stay.
        </p>
      </div>
    </div>
    <div v-if="confirmed" class="modal-backdrop">
      <section
        class="modal confirmation"
        role="dialog"
        aria-modal="true"
        aria-label="Reservation confirmed"
      >
        <span class="success-icon"><Check :size="34" /></span
        ><span class="eyebrow">YOU'RE GOING SOMEWHERE</span>
        <h2>Your stay is confirmed.</h2>
        <p>{{ confirmed.hotel_name }} · Room {{ confirmed.room_number }}</p>
        <p>{{ confirmed.check_in }} · {{ confirmed.check_out }}</p>
        <p class="reference">{{ confirmed.reference }}</p>
        <div class="receipt-line">
          <span>Simulated payment approved</span
          ><strong>{{ money(confirmed.total) }}</strong>
        </div>
        <RouterLink to="/bookings" class="button full"
          >View my reservation <ArrowRight :size="17" /></RouterLink
        ><button class="text-button" @click="confirmed = null">
          Keep exploring
        </button>
      </section>
    </div>
  </section>
  <section v-else class="section page">
    <p class="error">{{ error || "Property not found." }}</p>
    <RouterLink to="/">Back to stays</RouterLink>
  </section>
</template>
