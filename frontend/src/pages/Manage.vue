<script setup>
import { ref, computed, onMounted } from "vue";
import { api, errorMessage, money, today, nextDay } from "../services/api";
import {
  CITY_NAME,
  PROVINCE_NAME,
  LOCATION_LABEL,
} from "../services/location";
import { useAuth } from "../stores/auth";
import PropertyLocationPicker from "../components/PropertyLocationPicker.vue";
import FloorPlanEditor from "../components/FloorPlanEditor.vue";
import {
  Plus,
  Save,
  Trash2,
  Upload,
  Building2,
  ArrowUpRight,
  Pencil,
  Check,
  X,
} from "lucide-vue-next";
const auth = useAuth(),
  hotels = ref([]),
  hotelId = ref(null),
  floors = ref([]),
  rooms = ref([]),
  promos = ref([]),
  tab = ref("Rooms & layout"),
  error = ref(""),
  notice = ref(""),
  busy = ref(false),
  loading = ref(true),
  hotelModal = ref(false),
  showLocationPicker = ref(false),
  propertyPhotos = ref([]),
  propertyPhotoInput = ref(null),
  roomPhoto = ref(null),
  roomPhotoInput = ref(null),
  roomModal = ref(false),
  floorModal = ref(false),
  promoModal = ref(false),
  deleteTarget = ref(null);
const hotel = computed(() => hotels.value.find((h) => h.id === hotelId.value)),
  floorId = ref(null),
  floor = computed(() => floors.value.find((f) => f.id === floorId.value)),
  floorRooms = computed(() =>
    rooms.value.filter((r) => r.floor === floorId.value),
  );
const hasPropertyLocation = computed(() =>
  hf.value.latitude != null && hf.value.longitude != null &&
  Number.isFinite(Number(hf.value.latitude)) && Number.isFinite(Number(hf.value.longitude)),
);
const hf = ref({}),
  rf = ref({}),
  ff = ref({}),
  pf = ref({}),
  uploadKind = ref("hotel"),
  uploadRoom = ref(null),
  uploadFile = ref(null),
  caption = ref(""),
  fileInput = ref(),
  amenitiesText = ref("");
function failure(e) {
  error.value = errorMessage(e);
}
async function load() {
  loading.value = true;
  try {
    hotels.value = (
      await api.get("hotels/", {
        params: auth.user.role === "admin" ? {} : { mine: true },
      })
    ).data;
    if (!hotelId.value || !hotels.value.some((h) => h.id === hotelId.value))
      hotelId.value = hotels.value[0]?.id;
    await details();
  } catch (e) {
    failure(e);
  } finally {
    loading.value = false;
  }
}
async function details() {
  if (!hotelId.value) {
    floors.value = [];
    rooms.value = [];
    promos.value = [];
    return;
  }
  try {
    const [f, r, p] = await Promise.all([
      api.get("floors/", { params: { hotel: hotelId.value } }),
      api.get("rooms/", { params: { hotel: hotelId.value } }),
      api.get("promotions/", { params: { hotel: hotelId.value } }),
    ]);
    floors.value = f.data;
    rooms.value = r.data;
    promos.value = p.data;
    if (!floors.value.some((f) => f.id === floorId.value))
      floorId.value = floors.value[0]?.id;
  } catch (e) {
    failure(e);
  }
}
function editHotel(h) {
  hf.value = h
    ? { ...h, city: CITY_NAME }
    : {
        name: "",
        city: CITY_NAME,
        address: "",
        description: "",
        latitude: null,
        longitude: null,
      };
  amenitiesText.value = h?.amenities.join(", ") || "Wi-Fi, Parking";
  showLocationPicker.value = false;
  propertyPhotos.value = [];
  hotelModal.value = true;
  error.value = "";
}
function choosePropertyLocation(point) {
  hf.value.latitude = point.latitude;
  hf.value.longitude = point.longitude;
}
function selectPropertyPhotos(event) {
  const files = Array.from(event.target.files || []);
  const invalid = files.find((file) =>
    !["image/jpeg", "image/png", "image/webp"].includes(file.type) || file.size > 5 * 1024 * 1024,
  );
  if (invalid) {
    error.value = "Choose JPG, PNG, or WebP photos up to 5 MB each.";
    propertyPhotos.value = [];
    event.target.value = "";
    return;
  }
  error.value = "";
  propertyPhotos.value = files;
}
function editFloor(f) {
  ff.value = f
    ? { ...f }
    : {
        hotel: hotelId.value,
        number: floors.value.length + 1,
        name: "",
        columns: 6,
        plan_width_m: 30,
        plan_height_m: 20,
      };
  floorModal.value = true;
  error.value = "";
}
function roomPlan(room) {
  return room.plan || { x: room.column * 5, y: room.row * 5, width: 5, height: 5, zones: [] };
}
function firstFreePlan() {
  const size = 4;
  for (let y = 0; y <= Number(floor.value.plan_height_m) - size; y += 1) {
    for (let x = 0; x <= Number(floor.value.plan_width_m) - size; x += 1) {
      const candidate = { x, y, width: size, height: size, zones: [] };
      const occupied = floorRooms.value.some((room) => {
        const other = roomPlan(room);
        return x < other.x + other.width && other.x < x + size &&
          y < other.y + other.height && other.y < y + size;
      });
      if (!occupied) return candidate;
    }
  }
  return { x: 0, y: 0, width: size, height: size, zones: [] };
}
function editRoom(room, drawnPlan = null) {
  const taken = new Set(floorRooms.value.map((item) => `${item.row},${item.column}`));
  let slot = 0;
  while (taken.has(`${Math.floor(slot / floor.value.columns)},${slot % floor.value.columns}`)) slot += 1;
  rf.value = room
    ? { ...room, plan: { ...roomPlan(room), zones: [...(room.plan?.zones || [])] } }
    : {
        floor: floorId.value,
        number: "",
        kind: "Deluxe",
        description: "",
        price: 2500,
        capacity: 2,
        beds: "1 queen bed",
        row: Math.floor(slot / floor.value.columns),
        column: slot % floor.value.columns,
        plan: drawnPlan || firstFreePlan(),
        active: true,
      };
  roomPhoto.value = null;
  if (roomPhotoInput.value) roomPhotoInput.value.value = "";
  roomModal.value = true;
  error.value = "";
}
function selectRoomPhoto(event) {
  const file = event.target.files?.[0] || null;
  if (file && (!["image/jpeg", "image/png", "image/webp"].includes(file.type) || file.size > 5 * 1024 * 1024)) {
    roomPhoto.value = null;
    event.target.value = "";
    error.value = "Choose a JPG, PNG, or WebP room photo up to 5 MB.";
    return;
  }
  roomPhoto.value = file;
  error.value = "";
}
async function changeRoomPlan(room, plan) {
  if (busy.value) return;
  if (floor.value?.areas === undefined) {
    error.value = "Restart the local Django server to enable named plan areas.";
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    await api.patch(`rooms/${room.id}/`, { plan });
    await details();
    notice.value = `Room ${room.number} layout saved.`;
  } catch (e) {
    failure(e);
  } finally {
    busy.value = false;
  }
}
async function changeFloorAreas(areas) {
  if (busy.value || !floor.value) return;
  if (floor.value.areas === undefined) {
    error.value = "Restart the local Django server to enable named plan areas.";
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    await api.patch(`floors/${floor.value.id}/`, { areas });
    await details();
    notice.value = "Floor area saved.";
  } catch (e) {
    failure(e);
  } finally {
    busy.value = false;
  }
}
function editPromo(p) {
  pf.value = p
    ? { ...p }
    : {
        hotel: hotelId.value,
        code: "",
        percent: 10,
        starts_on: today(),
        ends_on: nextDay(today(), 30),
        active: true,
      };
  promoModal.value = true;
  error.value = "";
}
async function save(kind) {
  busy.value = true;
  error.value = "";
  notice.value = "";
  try {
    if (kind === "rooms" && !roomPhoto.value && !rf.value.photos?.length) {
      error.value = "Add a room photo before saving this room.";
      return;
    }
    if ((kind === "rooms" || kind === "floors") && floor.value && floor.value.areas === undefined) {
      error.value = "Restart the local Django server to enable named plan areas.";
      return;
    }
    if (kind === "hotels" && !hasPropertyLocation.value) {
      error.value = "Choose the property's location on the map before saving.";
      showLocationPicker.value = true;
      return;
    }
    const source =
      kind === "hotels"
        ? hf.value
        : kind === "rooms"
          ? rf.value
          : kind === "floors"
            ? ff.value
            : pf.value;
    let fields =
      kind === "hotels"
        ? [
            "name",
            "city",
            "address",
            "description",
            "latitude",
            "longitude",
          ]
        : kind === "rooms"
          ? [
              "floor",
              "number",
              "kind",
              "description",
              "price",
              "capacity",
              "beds",
              "plan",
              "row",
              "column",
              "active",
            ]
          : kind === "floors"
            ? ["hotel", "number", "name", "columns", "plan_width_m", "plan_height_m"]
            : ["hotel", "code", "percent", "starts_on", "ends_on", "active"];
    const payload = Object.fromEntries(fields.map((k) => [k, source[k]]));
    if (kind === "hotels")
      payload.amenities = amenitiesText.value
        .split(",")
        .map((a) => a.trim())
        .filter(Boolean);
    const { data } = source.id
      ? await api.patch(`${kind}/${source.id}/`, payload)
      : await api.post(`${kind}/`, payload);
    if (kind === "rooms" && roomPhoto.value) {
      const photo = new FormData();
      photo.append("room", data.id);
      photo.append("image", roomPhoto.value);
      try {
        await api.post("room-photos/", photo);
      } catch (uploadError) {
        if (!source.id) {
          try {
            await api.delete(`rooms/${data.id}/`);
          } catch {
            error.value = `Photo upload failed. Room ${data.number} was created; open it and retry the photo. ${errorMessage(uploadError)}`;
            await details();
            return;
          }
        }
        error.value = `Room photo could not upload. Please try again. ${errorMessage(uploadError)}`;
        return;
      }
      roomPhoto.value = null;
      if (roomPhotoInput.value) roomPhotoInput.value.value = "";
    }
    if (kind === "hotels") {
      hotelId.value = data.id;
      hf.value.id = data.id;
      const failedPhotos = [];
      let uploadError = "";
      for (const file of propertyPhotos.value) {
        const photo = new FormData();
        photo.append("hotel", data.id);
        photo.append("image", file);
        try {
          await api.post("hotel-photos/", photo);
        } catch (e) {
          failedPhotos.push(file);
          uploadError ||= errorMessage(e);
        }
      }
      propertyPhotos.value = failedPhotos;
      if (failedPhotos.length) {
        error.value = `Property saved, but ${failedPhotos.length} photo(s) could not upload. Try saving again. ${uploadError}`;
        await load();
        return;
      }
      if (propertyPhotoInput.value) propertyPhotoInput.value.value = "";
    }
    hotelModal.value =
      roomModal.value =
      floorModal.value =
      promoModal.value =
        false;
    notice.value =
      kind === "hotels"
        ? "Property saved and submitted for administrator verification."
        : "Changes saved.";
    await load();
  } catch (e) {
    failure(e);
  } finally {
    busy.value = false;
  }
}
function requestRoomDelete(room) {
  roomModal.value = false;
  error.value = "";
  deleteTarget.value = { kind: "rooms", id: room.id, number: room.number };
}
function roomStatus(room) {
  return room.availability_status === "booked"
    ? "Booked today"
    : room.active
      ? "Available"
      : "Unavailable";
}
async function toggleAvailability(room) {
  busy.value = true;
  error.value = "";
  try {
    await api.patch(`rooms/${room.id}/`, { active: !room.active });
    notice.value = `Room ${room.number} is now ${room.active ? "unavailable" : "available for reservations"}.`;
    await details();
  } catch (e) {
    failure(e);
  } finally {
    busy.value = false;
  }
}
async function remove() {
  busy.value = true;
  error.value = "";
  try {
    await api.delete(`${deleteTarget.value.kind}/${deleteTarget.value.id}/`);
    deleteTarget.value = null;
    notice.value = "Record removed.";
    await load();
  } catch (e) {
    failure(e);
  } finally {
    busy.value = false;
  }
}
async function upload() {
  if (!uploadFile.value) {
    error.value = "Choose an image first.";
    return;
  }
  if (uploadKind.value === "room" && !uploadRoom.value) {
    error.value = "Select a room first.";
    return;
  }
  busy.value = true;
  error.value = "";
  try {
    const data = new FormData();
    data.append(
      uploadKind.value,
      uploadKind.value === "hotel" ? hotelId.value : uploadRoom.value,
    );
    data.append("image", uploadFile.value);
    data.append("caption", caption.value);
    await api.post(
      uploadKind.value === "hotel" ? "hotel-photos/" : "room-photos/",
      data,
    );
    notice.value = "Photo uploaded.";
    uploadFile.value = null;
    caption.value = "";
    if (fileInput.value) fileInput.value.value = "";
    await load();
  } catch (e) {
    failure(e);
  } finally {
    busy.value = false;
  }
}
const photos = computed(() => [
  ...(hotel.value?.photos || []).map((p) => ({ ...p, kind: "hotel-photos" })),
  ...rooms.value.flatMap((r) =>
    r.photos.map((p) => ({ ...p, kind: "room-photos", room: r.number })),
  ),
]);
onMounted(load);
</script>
<template>
  <section class="section page">
    <span class="eyebrow">MAKE EVERY STAY A GOOD ONE</span>
    <div class="section-heading">
      <div>
        <h1>Your places, your way<span>.</span></h1>
        <p class="lead">Manage your properties in {{ LOCATION_LABEL }}.</p>
      </div>
      <button class="button small" @click="editHotel()">
        <Plus :size="17" />Add property
      </button>
    </div>
    <p class="success" v-if="notice" role="status">{{ notice }}</p>
    <p
      class="error"
      v-if="
        error &&
        !hotelModal &&
        !roomModal &&
        !floorModal &&
        !promoModal &&
        !deleteTarget
      "
      role="alert"
    >
      {{ error }}
    </p>
    <p v-if="loading">Loading properties...</p>
    <template v-if="hotels.length"
      ><div class="property-bar">
        <label
          >PROPERTY<select v-model="hotelId" @change="details">
            <option v-for="h in hotels" :value="h.id">
              {{ h.name }} · {{ h.city }}
            </option>
          </select></label
        ><span class="badge" :class="hotel?.status">{{ hotel?.status }}</span
        ><button class="text-button" @click="editHotel(hotel)">
          <Pencil :size="15" />Edit property</button
        ><RouterLink :to="`/hotels/${hotelId}`" class="text-button"
          >Preview <ArrowUpRight :size="16"
        /></RouterLink>
      </div>
      <p v-if="hotel?.verification_note" class="muted">
        Administrator note: {{ hotel.verification_note }}
      </p>
      <p v-if="hotel?.status !== 'verified'" class="info-note">
        This property is hidden from customers until an administrator verifies
        it.
      </p>
      <div class="tabs">
        <button
          v-for="t in ['Rooms & layout', 'Promotions', 'Photos']"
          :class="{ active: tab === t }"
          @click="tab = t"
        >
          {{ t }}
        </button>
      </div>
      <template v-if="tab === 'Rooms & layout'"
        ><div class="section-heading">
          <div class="floor-tabs">
            <button
              v-for="f in floors"
              :class="{ active: floorId === f.id }"
              @click="floorId = f.id"
            >
              {{ f.name }} <small>Floor {{ f.number }}</small>
            </button>
          </div>
          <button class="button secondary small" @click="editFloor()">
            <Plus :size="15" />Add floor
          </button>
        </div>
        <template v-if="floor"
          ><div class="section-heading">
            <p class="muted">
              {{ floor.plan_width_m }} m × {{ floor.plan_height_m }} m · {{ floorRooms.length }} rooms
            </p>
            <div class="inline-actions">
              <button class="text-button" @click="editFloor(floor)">
                Edit floor</button
              ><button
                class="text-button danger"
                @click="deleteTarget = { kind: 'floors', id: floor.id }"
              >
                Delete floor</button
              ><button class="button small" @click="editRoom()">
                <Plus :size="16" />Add room
              </button>
            </div>
          </div>
          <FloorPlanEditor
            v-if="floor.plan_width_m != null && floor.plan_height_m != null && floor.areas !== undefined"
            :key="floor.id" :floor="floor" :rooms="floorRooms" :busy="busy"
            @draw-room="editRoom(null, $event)" @change-room="changeRoomPlan"
            @change-floor="changeFloorAreas" @edit-room="editRoom"
          />
          <p v-else class="error" role="alert">Restart the local Django server to enable named plan areas.</p>
          <h3 class="room-inventory-title">Rooms on this floor</h3>
          <p class="muted">
            Draw rooms and named areas anywhere on the plan. Drag a box or its corner to adjust it.
            Rooms with booking history can be made unavailable instead of
            deleted.
          </p>
          <div class="room-inventory">
            <article
              v-for="r in floorRooms"
              :key="r.id"
              class="owner-room-item"
            >
              <div class="room-inventory-heading">
                <h3>Room {{ r.number }}</h3>
                <span
                  class="room-status-badge"
                  :class="r.availability_status"
                  >{{ roomStatus(r) }}</span
                >
              </div>
              <p>
                {{ r.kind }} &middot; {{ r.capacity }} guests &middot;
                {{ money(r.price) }} / night
              </p>
              <div class="room-item-actions">
                <button class="button secondary small" @click="editRoom(r)">
                  <Pencil :size="14" />Edit room</button
                ><button
                  class="button secondary small"
                  :disabled="busy"
                  @click="toggleAvailability(r)"
                >
                  {{ r.active ? "Make unavailable" : "Make available" }}</button
                ><button
                  class="delete-room-button"
                  :aria-label="`Delete room ${r.number}`"
                  :disabled="busy || r.can_delete === false"
                  :title="
                    r.can_delete === false
                      ? 'This room has reservation history. Make it unavailable instead.'
                      : `Delete room ${r.number}`
                  "
                  @click="requestRoomDelete(r)"
                >
                  <Trash2 :size="15" />Delete room
                </button>
              </div>
              <small v-if="r.can_delete === false" class="muted"
                >Booking history is protected. Use Make unavailable to stop new
                reservations.</small
              >
            </article>
          </div></template
        >
        <div v-else class="empty">
          Add a floor, then add rooms to its layout.
        </div></template
      >
      <template v-if="tab === 'Promotions'"
        ><div class="section-heading">
          <h2>A reason to stay a little longer.</h2>
          <button class="button small" @click="editPromo()">
            <Plus :size="16" />New promotion
          </button>
        </div>
        <div class="promotion-grid">
          <article v-for="p in promos" class="panel">
            <span class="eyebrow">{{ p.active ? "ACTIVE" : "INACTIVE" }}</span>
            <h2>{{ p.percent }}% off</h2>
            <strong class="promo-code">{{ p.code }}</strong>
            <p>{{ p.starts_on }} · {{ p.ends_on }}</p>
            <div class="inline-actions">
              <button class="text-button" @click="editPromo(p)">Edit</button
              ><button
                class="text-button danger"
                @click="deleteTarget = { kind: 'promotions', id: p.id }"
              >
                Remove
              </button>
            </div>
          </article>
        </div>
        <p v-if="!promos.length" class="empty">
          Create your first promotion.
        </p></template
      >
      <template v-if="tab === 'Photos'"
        ><form class="panel upload-form" @submit.prevent="upload">
          <h2>Show your best side.</h2>
          <div class="form-row">
            <label
              >Photo for<select v-model="uploadKind">
                <option value="hotel">Property</option>
                <option value="room">Room</option>
              </select></label
            ><label v-if="uploadKind === 'room'"
              >Room<select v-model="uploadRoom" required>
                <option :value="null" disabled>Select a room</option>
                <option v-for="r in rooms" :value="r.id">
                  Room {{ r.number }} · Floor {{ r.floor_number }}
                </option>
              </select></label
            >
          </div>
          <label
            >Image (up to 5 MB)<input
              ref="fileInput"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              @change="uploadFile = $event.target.files[0]"
              required /></label
          ><label>Caption<input v-model="caption" maxlength="160" /></label
          ><button class="button" :disabled="busy">
            <Upload :size="16" />{{ busy ? "Uploading..." : "Upload photo" }}
          </button>
        </form>
        <div class="photo-grid">
          <article v-for="p in photos">
            <img :src="p.image" :alt="p.caption || 'Property photo'" />
            <p>{{ p.caption }} {{ p.room ? "? Room " + p.room : "" }}</p>
            <button
              class="text-button danger"
              @click="deleteTarget = { kind: p.kind, id: p.id }"
            >
              <Trash2 :size="14" />Remove
            </button>
          </article>
        </div></template
      >
    </template>
    <div v-else-if="!loading" class="empty">
      <Building2 :size="40" />
      <h2>Make room for your first guests.</h2>
      <p>
        Add your Calapan property, create its floors and rooms, then submit it
        for verification.
      </p>
      <button class="button" @click="editHotel()">Add your property</button>
    </div>
    <div
      v-if="hotelModal || floorModal || roomModal || promoModal || deleteTarget"
      class="modal-backdrop"
    >
      <section
        class="modal wide"
        role="dialog"
        aria-modal="true"
        aria-label="Manage property details"
      >
        <form v-if="hotelModal" @submit.prevent="save('hotels')">
          <h2>{{ hf.id ? "Edit" : "Add" }} property</h2>
          <p class="muted">
            Saving property details submits it for administrator verification.
          </p>
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <label
            >Property name<input v-model="hf.name" required maxlength="160"
          /></label>
          <div class="form-row">
            <label>City<input :value="CITY_NAME" readonly /></label
            ><label>Province<input :value="PROVINCE_NAME" readonly /></label>
          </div>
          <label
            >Street / barangay in Calapan<input
              v-model="hf.address"
              required
              maxlength="255"
              placeholder="Street, building, or barangay in Calapan City" /></label
          ><label
            >Description<textarea
              v-model="hf.description"
              required
              rows="3"
            ></textarea>
          </label>
          <div class="property-location-field">
            <strong>Property location</strong>
            <p class="muted">Choose your hotel's exact location in {{ LOCATION_LABEL }}. Tap the map or drag the pin.</p>
            <button class="button secondary small" type="button" @click="showLocationPicker = !showLocationPicker">
              {{ showLocationPicker ? "Hide map" : hasPropertyLocation ? "Change map pin" : "Choose on map" }}
            </button>
            <PropertyLocationPicker
              v-if="showLocationPicker"
              :latitude="hf.latitude"
              :longitude="hf.longitude"
              @choose="choosePropertyLocation"
            />
            <p v-if="hasPropertyLocation" class="muted">Pin selected: {{ Number(hf.latitude).toFixed(6) }}, {{ Number(hf.longitude).toFixed(6) }}</p>
            <p v-else class="muted">No location selected yet.</p>
          </div>
          <label
            >Amenities (comma-separated)<input
              v-model="amenitiesText"
              placeholder="Wi-Fi, Pool, Breakfast" /></label
          >
          <label>Hotel photos (optional, up to 5 MB each)
            <input ref="propertyPhotoInput" type="file" accept="image/jpeg,image/png,image/webp" multiple @change="selectPropertyPhotos" />
          </label>
          <p v-if="propertyPhotos.length" class="muted">{{ propertyPhotos.length }} photo(s) selected: {{ propertyPhotos.map((file) => file.name).join(", ") }}</p>
          <button class="button full" :disabled="busy">{{ busy ? "Saving..." : "Save property" }}</button>
        </form>
        <form v-else-if="floorModal" @submit.prevent="save('floors')">
          <h2>{{ ff.id ? "Edit" : "Add" }} floor</h2>
          <p class="muted">Enter the floor's measured width and length. Existing rooms use approximate boxes until you set their sizes.</p>
          <label
            >Floor name<input v-model="ff.name" required maxlength="80"
          /></label>
          <div class="form-row">
            <label
              >Floor number<input
                type="number"
                v-model.number="ff.number"
                min="0"
                max="100"
                required /></label
            ><label
              >Floor width (m)<input
                type="number"
                v-model.number="ff.plan_width_m"
                min="5"
                max="200"
                step="0.01"
                required
            /></label>
          </div>
          <label>Floor length (m)<input type="number" v-model.number="ff.plan_height_m" min="5" max="200" step="0.01" required /></label>
          <button class="button full" :disabled="busy">Save floor</button>
        </form>
        <form v-else-if="roomModal" @submit.prevent="save('rooms')">
          <h2>{{ rf.id ? "Edit" : "Add" }} room</h2>
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <div class="form-row">
            <label
              >Room number<input
                v-model="rf.number"
                maxlength="12"
                required /></label
            ><label
              >Room type<select v-model="rf.kind">
                <option>Deluxe</option>
                <option>Standard</option>
                <option>Suite</option>
                <option>Family</option>
              </select></label
            >
          </div>
          <label
            >Description<textarea v-model="rf.description" rows="2"></textarea>
          </label>
          <div class="form-row">
            <label
              >Price per night (PHP)<input
                type="number"
                step="0.01"
                min="1"
                max="99999999"
                v-model.number="rf.price"
                required /></label
            ><label
              >Capacity<input
                type="number"
                min="1"
                max="20"
                v-model.number="rf.capacity"
                required
            /></label>
          </div>
          <label>Beds<input v-model="rf.beds" maxlength="80" required /></label>
          <div class="room-photo-field">
            <div>
              <strong>Room photo <span v-if="!rf.photos?.length">required</span></strong>
              <p>Show guests the room they will book. JPG, PNG, or WebP, up to 5 MB.</p>
            </div>
            <img v-if="rf.photos?.length" :src="rf.photos[0].image" :alt="`Current photo of room ${rf.number}`" />
            <label>
              {{ rf.photos?.length ? "Add another photo" : "Choose a room photo" }}
              <input ref="roomPhotoInput" type="file" accept="image/jpeg,image/png,image/webp" :required="!rf.photos?.length && !roomPhoto" @change="selectRoomPhoto" />
            </label>
            <small v-if="roomPhoto">Ready to upload: {{ roomPhoto.name }}</small>
          </div>
          <div class="form-row">
            <label>Room width (m)<input type="number" min="1" step="0.01" v-model.number="rf.plan.width" required /></label>
            <label>Room length (m)<input type="number" min="1" step="0.01" v-model.number="rf.plan.height" required /></label>
          </div>
          <p class="muted">Measured area: {{ Number((rf.plan?.width || 0) * (rf.plan?.height || 0)).toFixed(2) }} m²</p>
          <div class="form-row">
            <label>From left (m)<input type="number" min="0" step="0.01" v-model.number="rf.plan.x" required /></label>
            <label>From top (m)<input type="number" min="0" step="0.01" v-model.number="rf.plan.y" required /></label>
          </div>
          <label class="checkbox-label"
            ><input type="checkbox" v-model="rf.active" />Room is active and
            accepts reservations (turn off for maintenance)</label
          ><button class="button full" :disabled="busy">Save room</button>
          <p v-if="rf.id && rf.can_delete === false" class="muted">
            This room has reservation history. Turn off availability and save to
            stop new bookings.
          </p>
          <button
            v-if="rf.id"
            type="button"
            class="delete-room-button full"
            :disabled="busy || rf.can_delete === false"
            @click="requestRoomDelete(rf)"
          >
            <Trash2 :size="16" />Delete room {{ rf.number }}
          </button>
        </form>
        <form v-else-if="promoModal" @submit.prevent="save('promotions')">
          <h2>{{ pf.id ? "Edit" : "Create" }} promotion</h2>
          <label
            >Code<input
              v-model="pf.code"
              required
              maxlength="32"
              pattern="[A-Za-z0-9_-]+" /></label
          ><label
            >Discount percent<input
              type="number"
              min="1"
              max="80"
              v-model.number="pf.percent"
              required
          /></label>
          <div class="form-row">
            <label
              >Starts on<input
                type="date"
                v-model="pf.starts_on"
                required /></label
            ><label
              >Ends on<input
                type="date"
                v-model="pf.ends_on"
                :min="pf.starts_on"
                required
            /></label>
          </div>
          <label class="checkbox-label"
            ><input type="checkbox" v-model="pf.active" />Active</label
          ><button class="button full" :disabled="busy">Save promotion</button>
        </form>
        <template v-else-if="deleteTarget"
          ><h2>
            {{
              deleteTarget.kind === "rooms"
                ? `Delete room ${deleteTarget.number}?`
                : "Remove this record?"
            }}
          </h2>
          <p>
            Records used by reservations are protected. Deactivate rooms to
            preserve booking history.
          </p>
          <button class="button full" :disabled="busy" @click="remove">
            {{
              deleteTarget.kind === "rooms"
                ? "Confirm delete room"
                : "Remove record"
            }}
          </button></template
        >
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button
          class="text-button modal-close"
          :disabled="busy"
          @click="
            hotelModal = roomModal = floorModal = promoModal = false;
            deleteTarget = null;
            error = '';
          "
        >
          Close
        </button>
      </section>
    </div>
  </section>
</template>

<style scoped>
.property-location-field { display: grid; gap: .6rem; margin: 1rem 0; }
.property-location-field p { margin: 0; }
.property-location-field > button { justify-self: start; }
</style>
