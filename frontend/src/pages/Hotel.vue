<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from "vue";
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
import HotelNavigation from "../components/HotelNavigation.vue";
import FloorPlanEditor from "../components/FloorPlanEditor.vue";
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
  roomView = ref("photos"),
  showMap = ref(false),
  showNavigation = ref(false),
  confirmed = ref(null),
  depositPrompt = ref(false);
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
const depositDue = computed(() => total.value * 0.5);
const gallery = computed(() =>
  [
    ...(hotel.value?.photos || []),
    ...rooms.value.flatMap((r) => r.photos),
  ].filter((p, i, a) => a.findIndex((x) => x.image === p.image) === i),
);
let availabilityTimer = null;
let availabilityRequest = 0;
async function refreshRooms() {
  if (availabilityTimer) {
    clearTimeout(availabilityTimer);
    availabilityTimer = null;
  }
  const requestId = ++availabilityRequest;
  error.value = "";
  selected.value = null;
  checkingRooms.value = true;
  const period = {
    check_in: form.value.check_in,
    check_out: form.value.check_out,
  };
  try {
    const { data } = await api.get("rooms/", {
      params: {
        hotel: route.params.id,
        ...period,
      },
    });
    if (requestId !== availabilityRequest) return;
    rooms.value = data;
    appliedDates.value = period;
  } catch (e) {
    if (requestId === availabilityRequest) error.value = errorMessage(e);
  } finally {
    if (requestId === availabilityRequest) checkingRooms.value = false;
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
function beginBooking() {
  if (!auth.user) {
    router.push({ path: "/login", query: { next: route.fullPath } });
    return;
  }
  depositPrompt.value = true;
}
async function continueBooking() {
  depositPrompt.value = false;
  await reserve();
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
  ([checkIn, checkOut]) => {
    selected.value = null;
    if (availabilityTimer) clearTimeout(availabilityTimer);
    if (!checkIn || !checkOut) return;
    if (checkOut <= checkIn) {
      form.value.check_out = nextDay(checkIn);
      return;
    }
    availabilityTimer = setTimeout(() => {
      availabilityTimer = null;
      refreshRooms();
    }, 300);
  },
);
onMounted(load);
onBeforeUnmount(() => {
  if (availabilityTimer) clearTimeout(availabilityTimer);
  availabilityRequest += 1;
});
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
        <span class="eyebrow">{{ hotel.city.toUpperCase() }}</span>
        <h1>{{ hotel.name }}</h1>
        <p>
          <MapPin :size="16" />{{ hotel.address }}, {{ hotel.city }}
          <button class="text-button" @click="showMap = !showMap">
            {{ showMap ? "Hide map" : "View map" }}
          </button>
          <button class="text-button hotel-directions-button" @click="showNavigation = !showNavigation">
            {{ showNavigation ? "Close directions" : "Follow directions" }}
          </button>
        </p>
      </div>
      <span class="rating large"
        ><Star fill="currentColor" :size="20" />{{
          hotel.rating ? Number(hotel.rating).toFixed(1) : "New"
        }}<small>{{ hotel.review_count ? `${hotel.review_count} reviews` : "No reviews yet" }}</small></span
      >
    </div>
    <HotelMap v-if="showMap" :hotels="[hotel]" />
    <HotelNavigation v-if="showNavigation" :hotel="hotel" @close="showNavigation = false" />
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
        <p class="muted">
          Availability is for {{ form.check_in }} · {{ form.check_out }}.
        </p>
        <div class="room-view-switch" role="group" aria-label="Choose how to view rooms">
          <button type="button" :class="{ active: roomView === 'photos' }" :aria-pressed="roomView === 'photos'" @click="roomView = 'photos'">Room photos</button>
          <button type="button" :class="{ active: roomView === 'layout' }" :aria-pressed="roomView === 'layout'" @click="roomView = 'layout'">Floor layout</button>
        </div>
        <div class="floor-tabs">
          <button
            v-for="f in floors"
            :class="{ active: floorId === f.id }"
            @click="floorId = f.id"
          >
            {{ f.name }} <small>Floor {{ f.number }}</small>
          </button>
        </div>
        <div v-if="datesDirty || checkingRooms" class="availability-refreshing" role="status">
          <span class="eyebrow">UPDATING ROOM AVAILABILITY</span>
          <p v-if="form.check_in && form.check_out">Checking rooms for {{ form.check_in }} · {{ form.check_out }}…</p>
          <p v-else>Choose both dates to check room availability.</p>
        </div>
        <div v-else-if="floor && roomView === 'photos'" class="room-photo-grid">
          <button
            v-for="room in floorRooms" :key="room.id" type="button"
            class="room-photo-card" :class="{ chosen: selected?.id === room.id, disabled: roomState(room) !== 'available' && roomState(room) !== 'selected' }"
            :disabled="datesDirty || checkingRooms || (roomState(room) !== 'available' && roomState(room) !== 'selected')"
            @click="selectRoom(room)"
          >
            <div class="room-photo-card-image">
              <img v-if="room.photos?.length" :src="room.photos[0].image" :alt="`Room ${room.number}`" loading="lazy" />
              <span v-else class="room-photo-placeholder"><BedDouble :size="36" />Photo coming soon</span>
              <span class="room-photo-status" :class="roomState(room)">{{ roomLabel(room) }}</span>
            </div>
            <div class="room-photo-card-body">
              <span class="eyebrow">ROOM {{ room.number }}</span>
              <h3>{{ room.kind }}</h3>
              <p>{{ room.beds }} · {{ room.capacity }} guests · {{ room.area }} m²</p>
              <strong>{{ money(room.price) }} <small>/ night</small></strong>
            </div>
          </button>
          <p v-if="!floorRooms.length" class="empty">No rooms are listed on this floor yet.</p>
        </div>
        <div v-else-if="floor" class="floor-plan">
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
          <FloorPlanEditor
            :key="floor.id" :floor="floor" :rooms="floorRooms" readonly
            :selected-room-id="selected?.id || null" :room-state="roomState" :room-label="roomLabel"
            @select-room="selectRoom"
          />
          <div class="legend">
            <span><i></i>Available</span
            ><span><i class="picked"></i>Your choice</span
            ><span><i class="booked"></i>Booked</span
            ><span><i class="taken"></i>Unavailable</span
            ><span><i class="capacity"></i>Too small</span>
          </div>
        </div>
        <p v-else class="empty">This property has no rooms listed yet.</p>
      </div>
      <aside class="reservation-panel">
        <span class="eyebrow">YOUR NEXT CHAPTER</span>
        <h3>{{ selected ? "Make it yours." : "Your room is waiting." }}</h3>
        <p v-if="!selected">
          Choose an available room from the photos or floor layout to see your reservation details.
        </p>
        <template v-else
          ><div class="reservation-room-photo">
            <img v-if="selected.photos?.length" :src="selected.photos[0].image" :alt="`Selected room ${selected.number}`" />
            <div v-else class="room-photo-placeholder"><BedDouble :size="32" />Photo coming soon</div>
            <span>ROOM {{ selected.number }} · {{ selected.kind }}</span>
          </div>
          <p class="reservation-room-description">{{ selected.description }}</p>
          <div class="room-facts">
            <span><BedDouble :size="16" />{{ selected.beds }}</span>
            <span><Users :size="16" />{{ selected.capacity }} guests</span>
            <span><Maximize :size="16" />{{ selected.area }} m²</span>
          </div>
          <div class="price-head">
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
          <button
            class="button full"
            @click="beginBooking"
            :disabled="
              busy || nights < 1 || (auth.user && auth.user.role !== 'customer')
            "
          >
            {{
              busy
                ? "Sending request..."
                : auth.user
                  ? "Request booking"
                  : "Sign in to reserve"
            }}<ArrowRight :size="17" />
          </button>
          <p v-if="auth.user && auth.user.role !== 'customer'" class="muted">
            A customer account is required to reserve.
          </p>
          <small class="muted">The owner must approve your booking. You may cancel within two hours of requesting it, before check-in day.</small></template
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
    <div v-if="depositPrompt" class="modal-backdrop">
      <section class="modal confirmation" role="dialog" aria-modal="true" aria-label="Booking deposit information">
        <span class="success-icon"><ShieldCheck :size="32" /></span>
        <span class="eyebrow">DEPOSIT INFORMATION</span>
        <h2>A 50% deposit is requested.</h2>
        <p>Deposit amount: <strong>{{ money(depositDue) }}</strong></p>
        <p>Booking total: {{ money(total) }}</p>
        <p class="muted">RoomFinder does not collect or verify payments in this app. Arrange the deposit directly with the hotel owner before proceeding. The owner handles any eligible refund under the hotel's cancellation policy.</p>
        <button class="button full" :disabled="busy" @click="continueBooking">Continue with booking request <ArrowRight :size="17" /></button>
        <button class="text-button" :disabled="busy" @click="depositPrompt = false">Go back</button>
      </section>
    </div>
    <div v-if="confirmed" class="modal-backdrop">
      <section
        class="modal confirmation"
        role="dialog"
        aria-modal="true"
        aria-label="Booking request submitted"
      >
        <span class="success-icon"><Check :size="34" /></span
        ><span class="eyebrow">YOU'RE GOING SOMEWHERE</span>
        <h2>Request sent to the owner.</h2>
        <p>Your booking is pending approval.</p>
        <p>{{ confirmed.hotel_name }} · Room {{ confirmed.room_number }}</p>
        <p>{{ confirmed.check_in }} · {{ confirmed.check_out }}</p>
        <p class="reference">{{ confirmed.reference }}</p>
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
