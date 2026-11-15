<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import L from "leaflet";
import { CALAPAN_CENTER } from "../services/location";

const props = defineProps({
  latitude: { type: [Number, String], default: null },
  longitude: { type: [Number, String], default: null },
});
const emit = defineEmits(["choose"]);
const mapElement = ref(null);
let map;
let marker;

const pinIcon = L.divIcon({
  className: "property-location-pin",
  html: '<span aria-hidden="true"></span>',
  iconSize: [24, 32],
  iconAnchor: [12, 32],
});

function selectedPoint() {
  if (props.latitude == null || props.longitude == null) return null;
  const latitude = Number(props.latitude);
  const longitude = Number(props.longitude);
  return Number.isFinite(latitude) && Number.isFinite(longitude)
    ? [latitude, longitude]
    : null;
}

function placePin(point) {
  if (!map) return;
  if (!marker) {
    marker = L.marker(point, { icon: pinIcon, draggable: true }).addTo(map);
    marker.on("dragend", () => select(marker.getLatLng()));
  } else {
    marker.setLatLng(point);
  }
}

function select(point) {
  const latitude = Number(point.lat.toFixed(6));
  const longitude = Number(point.lng.toFixed(6));
  placePin([latitude, longitude]);
  emit("choose", { latitude, longitude });
}

function selectCenter() {
  if (map) select(map.getCenter());
}

onMounted(async () => {
  const point = selectedPoint();
  map = L.map(mapElement.value).setView(point || CALAPAN_CENTER, point ? 16 : 13);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(map);
  map.on("click", (event) => select(event.latlng));
  if (point) placePin(point);
  await nextTick();
  map.invalidateSize();
});

watch(() => [props.latitude, props.longitude], () => {
  const point = selectedPoint();
  if (point) placePin(point);
});

onBeforeUnmount(() => {
  map?.remove();
  map = null;
  marker = null;
});
</script>

<template>
  <div class="property-map-picker">
    <div ref="mapElement" class="property-map" aria-label="Choose your property's location on the map"></div>
    <button type="button" class="button secondary small" @click="selectCenter">Place pin at map center</button>
  </div>
</template>

<style scoped>
.property-map { height: 320px; width: 100%; border-radius: .6rem; }
.property-map-picker { display: grid; gap: .6rem; }
.property-map-picker button { justify-self: start; }
:deep(.property-location-pin span) { display: block; width: 24px; height: 24px; border: 3px solid #fff; border-radius: 50% 50% 50% 0; background: #c83d31; box-shadow: 0 2px 8px #0008; transform: rotate(-45deg); }
</style>
