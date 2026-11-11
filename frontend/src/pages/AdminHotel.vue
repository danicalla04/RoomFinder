<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, errorMessage, money } from "../services/api";

const route = useRoute();
const router = useRouter();
const overview = ref(null);
const loading = ref(true);
const error = ref("");
const deletionName = ref("");
const deleting = ref(false);
const deletionError = ref("");
const selectedFloorId = ref(null);
const selectedRoomId = ref(null);
const selectedFloor = computed(() => overview.value?.floors.find((floor) => floor.id === selectedFloorId.value));
const selectedRoom = computed(() => overview.value?.rooms.find((room) => room.id === selectedRoomId.value));
const floorRooms = computed(() => overview.value?.rooms.filter((room) => room.floor_id === selectedFloorId.value) || []);
const visibleBookings = computed(() => {
  const bookings = overview.value?.bookings || [];
  if (selectedRoomId.value) return bookings.filter((booking) => booking.room_id === selectedRoomId.value);
  if (selectedFloorId.value) {
    const roomIds = new Set(floorRooms.value.map((room) => room.id));
    return bookings.filter((booking) => roomIds.has(booking.room_id));
  }
  return bookings;
});

function openFloor(floor) {
  selectedFloorId.value = floor.id;
  selectedRoomId.value = null;
}

function backToProperty() {
  selectedFloorId.value = null;
  selectedRoomId.value = null;
}

async function load() {
  loading.value = true;
  error.value = "";
  overview.value = null;
  deletionName.value = "";
  deletionError.value = "";
  backToProperty();
  try {
    overview.value = (await api.get(`admin/hotels/${route.params.id}/`)).data;
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}

async function deleteHotel() {
  if (!overview.value || deletionName.value !== overview.value.hotel.name || deleting.value) return;
  deleting.value = true;
  deletionError.value = "";
  try {
    await api.delete(`admin/hotels/${overview.value.hotel.id}/`, {
      data: { confirm_name: deletionName.value },
    });
    sessionStorage.removeItem("rf_admin_users");
    await router.push("/admin/users");
  } catch (e) {
    deletionError.value = errorMessage(e);
  } finally {
    deleting.value = false;
  }
}

onMounted(load);
watch(() => route.params.id, load);
</script>

<template>
  <section class="section page">
    <RouterLink to="/admin/users">← Back to users</RouterLink>
    <span class="eyebrow">PROPERTY MONITORING</span>
    <p v-if="loading">Loading property...</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <template v-if="overview">
      <h1>{{ overview.hotel.name }}<span>.</span></h1>
      <p class="lead">Owned by {{ overview.hotel.owner }} · {{ overview.hotel.address }}, {{ overview.hotel.city }}</p>
      <article class="panel">
        <h2>Property information</h2>
        <p>{{ overview.hotel.description || "None yet." }}</p>
        <p>Status: {{ overview.hotel.status }} · Rating: {{ overview.hotel.stars }} stars</p>
        <p v-if="overview.hotel.verification_note">Verification note: {{ overview.hotel.verification_note }}</p>
      </article>

      <article class="panel" v-if="!selectedFloorId">
        <h2>Places and floors ({{ overview.floors.length }})</h2>
        <p class="muted">Select a floor to see its rooms.</p>
        <p v-if="!overview.floors.length" class="muted">None yet.</p>
        <div v-else class="admin-place-grid">
          <button v-for="floor in overview.floors" :key="floor.id" class="admin-place" @click="openFloor(floor)">
            <strong>{{ floor.name || `Floor ${floor.number}` }}</strong>
            <span>Floor {{ floor.number }} · {{ overview.rooms.filter((room) => room.floor_id === floor.id).length }} rooms</span>
            <small>View rooms →</small>
          </button>
        </div>
      </article>

      <article class="panel" v-if="selectedFloor && !selectedRoom">
        <button class="text-button" @click="backToProperty">← All places</button>
        <h2>{{ selectedFloor.name || `Floor ${selectedFloor.number}` }}</h2>
        <p class="muted">Floor {{ selectedFloor.number }} · {{ floorRooms.length }} rooms</p>
        <p v-if="!floorRooms.length" class="muted">None yet.</p>
        <div v-else class="admin-place-grid">
          <button v-for="room in floorRooms" :key="room.id" class="admin-place" @click="selectedRoomId = room.id">
            <strong>Room {{ room.number }}</strong>
            <span>{{ room.kind }} · {{ room.capacity }} guests · {{ money(room.price) }} per night</span>
            <small>{{ room.active ? "Active" : "Inactive" }} · View room →</small>
          </button>
        </div>
      </article>

      <article class="panel" v-if="selectedRoom">
        <button class="text-button" @click="selectedRoomId = null">← {{ selectedFloor.name || `Floor ${selectedFloor.number}` }}</button>
        <h2>Room {{ selectedRoom.number }}</h2>
        <p>{{ selectedRoom.description || "No description yet." }}</p>
        <div class="admin-room-facts">
          <p><strong>Type</strong><br>{{ selectedRoom.kind }}</p>
          <p><strong>Price per night</strong><br>{{ money(selectedRoom.price) }}</p>
          <p><strong>Capacity</strong><br>{{ selectedRoom.capacity }} guests</p>
          <p><strong>Beds</strong><br>{{ selectedRoom.beds }}</p>
          <p><strong>Area</strong><br>{{ selectedRoom.area }} m²</p>
          <p><strong>Status</strong><br>{{ selectedRoom.active ? "Active" : "Inactive" }}</p>
          <p><strong>Position</strong><br>Row {{ selectedRoom.row + 1 }}, column {{ selectedRoom.column + 1 }}</p>
        </div>
        <h3>Photos ({{ selectedRoom.photos.length }})</h3>
        <p v-if="!selectedRoom.photos.length" class="muted">None yet.</p>
        <div v-else class="admin-room-photos">
          <figure v-for="photo in selectedRoom.photos" :key="photo.image">
            <img :src="photo.image" :alt="photo.caption || `Room ${selectedRoom.number}`" />
            <figcaption v-if="photo.caption">{{ photo.caption }}</figcaption>
          </figure>
        </div>
      </article>

      <article class="panel">
        <h2>{{ selectedRoom ? `Room ${selectedRoom.number} reservations` : selectedFloor ? "Floor reservations" : "Property reservations" }} ({{ visibleBookings.length }})</h2>
        <p v-if="!visibleBookings.length" class="muted">None yet.</p>
        <div v-else class="table-scroll">
          <table>
            <thead><tr><th>Reference</th><th>Guest</th><th>Room</th><th>Check in</th><th>Check out</th><th>Guests</th><th>Total</th><th>Booking</th><th>Payment</th></tr></thead>
            <tbody>
              <tr v-for="booking in visibleBookings" :key="booking.id">
                <td>{{ booking.reference }}</td>
                <td>{{ booking.customer__username }}</td>
                <td>{{ booking.room__number }}</td>
                <td>{{ booking.check_in }}</td>
                <td>{{ booking.check_out }}</td>
                <td>{{ booking.guests }}</td>
                <td>{{ money(booking.total) }}</td>
                <td>{{ booking.status }}</td>
                <td>{{ booking.payment__status || "None" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>

      <article class="panel delete-hotel-panel" v-if="!selectedFloorId">
        <h2>Delete this hotel</h2>
        <p>This permanently removes the hotel, its floors, rooms, reservations, payments, reviews, promotions, and photos. The owner and guest accounts remain.</p>
        <p class="muted">Type <strong>{{ overview.hotel.name }}</strong> to confirm.</p>
        <form @submit.prevent="deleteHotel">
          <label for="delete-hotel-name">Hotel name</label>
          <input id="delete-hotel-name" v-model="deletionName" autocomplete="off" />
          <p v-if="deletionError" class="error" role="alert">{{ deletionError }}</p>
          <button class="button delete-hotel-button" type="submit" :disabled="deleting || deletionName !== overview.hotel.name">
            {{ deleting ? "Deleting..." : "Delete hotel and records" }}
          </button>
        </form>
      </article>
    </template>
  </section>
</template>

<style scoped>
.admin-place-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-top: 1rem; }
.admin-place { display: flex; flex-direction: column; align-items: flex-start; gap: .4rem; padding: 1rem; border: 1px solid #d6dfe5; border-radius: .75rem; background: #fff; color: inherit; text-align: left; cursor: pointer; }
.admin-place:hover, .admin-place:focus-visible { border-color: #20866a; box-shadow: 0 0 0 2px #20866a22; }
.admin-place small { color: #16785e; font-weight: 600; }
.admin-room-facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: .5rem 1rem; }
.admin-room-photos { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; }
.admin-room-photos figure { margin: 0; }
.admin-room-photos img { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; border-radius: .6rem; }
.delete-hotel-panel { border-color: #dfb6ad; margin-top: 1.5rem; }
.delete-hotel-panel form { display: grid; gap: .75rem; max-width: 26rem; }
.delete-hotel-panel input { width: 100%; }
.delete-hotel-button { background: #a93d32; border-color: #a93d32; }
.delete-hotel-button:hover { background: #842f27; }
.delete-hotel-button:disabled { opacity: .5; cursor: not-allowed; }
</style>
