<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { LocateFixed, MapPin, Navigation, RotateCw, X } from "lucide-vue-next";
import mapWorkerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import "maplibre-gl/dist/maplibre-gl.css";
import { Capacitor, registerPlugin } from "@capacitor/core";
import { api, errorMessage } from "../services/api";
import { useAuth } from "../stores/auth";
import { useRoute } from "vue-router";

const props = defineProps({ hotel: { type: Object, required: true } });
const emit = defineEmits(["close"]);
const GeospatialAR = registerPlugin("GeospatialAR");
const auth = useAuth();
const currentRoute = useRoute();
const mapElement = ref(null);
const state = ref("idle");
const message = ref("");
const routeInfo = ref(null);
const nextInstruction = ref("");
const arError = ref("");
const isNativeApp = Capacitor.isNativePlatform();
const destination = computed(() => [Number(props.hotel.longitude), Number(props.hotel.latitude)]);
let map;
let watchId = null;
let latestPosition;
let lastRequestedPosition;
let lastRequestAt = 0;
let routeRequest = 0;
let mounted = false;
let routeGeometry = null;
let routeOverlay = null;
let routeCasing = null;
let routeStroke = null;

function validDestination() {
  return destination.value.every(Number.isFinite) && Math.abs(destination.value[0]) <= 180 && Math.abs(destination.value[1]) <= 90;
}
function setUserPoint(position) {
  if (!map?.getSource("live-user")) return;
  map.getSource("live-user").setData({
    type: "FeatureCollection",
    features: [{ type: "Feature", geometry: { type: "Point", coordinates: [position.longitude, position.latitude] }, properties: {} }],
  });
}
function drawRoute(feature) {
  if (!map) throw new Error("The map is not ready yet. Try again shortly.");
  if (map.getLayer("road-route-line")) map.removeLayer("road-route-line");
  if (map.getLayer("road-route-casing")) map.removeLayer("road-route-casing");
  if (map.getSource("road-route")) map.removeSource("road-route");
  map.addSource("road-route", {
    type: "geojson",
    data: { type: "FeatureCollection", features: [feature] },
  });
  map.addLayer({
    id: "road-route-casing",
    type: "line",
    source: "road-route",
    paint: {
      "line-color": "#ffffff",
      "line-width": 12,
      "line-opacity": 1,
      "line-cap": "round",
      "line-join": "round",
    },
  });
  map.addLayer({
    id: "road-route-line",
    type: "line",
    source: "road-route",
    paint: {
      "line-color": "#5268df",
      "line-width": 8,
      "line-opacity": 1,
      "line-cap": "round",
      "line-join": "round",
    },
  });
  routeGeometry = feature.geometry;
  renderRouteOverlay();
}
function renderRouteOverlay() {
  if (!map || !routeOverlay || !routeGeometry) return;
  const coordinates = routeGeometry.type === "MultiLineString"
    ? routeGeometry.coordinates.flat()
    : routeGeometry.coordinates;
  if (!Array.isArray(coordinates)) return;
  const { width, height } = map.getContainer().getBoundingClientRect();
  if (!width || !height) return;
  routeOverlay.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const path = coordinates.map((coordinate, index) => {
    if (!Array.isArray(coordinate) || coordinate.length < 2) return "";
    const point = map.project([Number(coordinate[0]), Number(coordinate[1])]);
    return `${index ? "L" : "M"}${point.x.toFixed(1)},${point.y.toFixed(1)}`;
  }).filter(Boolean).join(" ");
  routeCasing?.setAttribute("d", path);
  routeStroke?.setAttribute("d", path);
}
function fitRoute(geometry) {
  if (!map || !geometry?.coordinates?.length) return;
  const bounds = new maplibre.LngLatBounds();
  geometry.coordinates.forEach((point) => bounds.extend(point));
  bounds.extend(destination.value);
  map.fitBounds(bounds, { padding: 60, maxZoom: 17, duration: 700 });
}
async function requestRoute(position, force = false) {
  if (!auth.user) {
    state.value = "error";
    message.value = "Sign in to get live directions.";
    return;
  }
  const now = Date.now();
  if (!force && lastRequestedPosition && now - lastRequestAt < 45000) return;
  if (!force && lastRequestedPosition && distanceMeters(position, lastRequestedPosition) < 80) return;
  const id = ++routeRequest;
  state.value = "routing";
  message.value = "Finding a road route…";
  try {
    const { data } = await api.post("navigation/route/", {
      origin_latitude: position.latitude,
      origin_longitude: position.longitude,
      destination_latitude: destination.value[1],
      destination_longitude: destination.value[0],
      profile: "foot-walking",
    });
    if (!mounted || id !== routeRequest) return;
    const routeFeature = data.route?.type === "FeatureCollection"
      ? data.route.features?.[0]
      : data.route;
    if (!routeFeature?.geometry?.coordinates?.length) {
      throw new Error("The route service returned directions without a map path.");
    }
    drawRoute(routeFeature);
    routeInfo.value = { ...data, route: routeFeature };
    nextInstruction.value = data.steps?.[0]?.instruction || "Follow the route shown on the map.";
    lastRequestedPosition = position;
    lastRequestAt = now;
    state.value = "ready";
    message.value = "Route updated. Keep the map open while you walk.";
    fitRoute(routeFeature.geometry);
  } catch (error) {
    if (id === routeRequest) {
      state.value = "error";
      message.value = error.response ? errorMessage(error) : (error.message || "Could not calculate a route.");
    }
  }
}
function distanceMeters(a, b) {
  const rad = (v) => (v * Math.PI) / 180;
  const dLat = rad(a.latitude - b.latitude);
  const dLon = rad(a.longitude - b.longitude);
  const value = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.latitude)) * Math.cos(rad(b.latitude)) * Math.sin(dLon / 2) ** 2;
  return 6371000 * 2 * Math.atan2(Math.sqrt(value), Math.sqrt(1 - value));
}
function onPosition(position) {
  latestPosition = { latitude: position.coords.latitude, longitude: position.coords.longitude };
  setUserPoint(latestPosition);
  if (state.value === "idle" || state.value === "locating" || (lastRequestedPosition && distanceMeters(latestPosition, lastRequestedPosition) > 80 && Date.now() - lastRequestAt > 45000)) {
    requestRoute(latestPosition);
  }
  if (map && !routeInfo.value) map.easeTo({ center: [latestPosition.longitude, latestPosition.latitude], zoom: 15, duration: 400 });
}
function onLocationError(error) {
  state.value = "error";
  message.value = error.code === 1 ? "Location permission is required for live directions." : "Could not read your location. Check that location services are enabled.";
}
function locate() {
  if (!navigator.geolocation) {
    state.value = "error";
    message.value = "This device does not provide location access in this browser.";
    return;
  }
  state.value = "locating";
  message.value = "Waiting for your current location…";
  if (watchId !== null) navigator.geolocation.clearWatch(watchId);
  watchId = navigator.geolocation.watchPosition(onPosition, onLocationError, { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 });
}
function retryRoute() {
  if (latestPosition) requestRoute(latestPosition, true);
  else locate();
}
async function openArGuidance() {
  if (!isNativeApp || !routeInfo.value?.route?.geometry?.coordinates) return;
  arError.value = "";
  try {
    await GeospatialAR.start({
      hotelName: props.hotel.name,
      coordinates: routeInfo.value.route.geometry.coordinates,
    });
  } catch {
    arError.value = "Could not open AR directions. Rebuild and install the Android app, then try again.";
  }
}
function formatDistance(value) {
  return value >= 1000 ? `${(value / 1000).toFixed(1)} km` : `${Math.round(value || 0)} m`;
}
let maplibre;
onMounted(async () => {
  mounted = true;
  if (!validDestination()) {
    state.value = "error";
    message.value = "This hotel has no valid map coordinates yet.";
    return;
  }
  try {
    const module = await import("maplibre-gl");
    maplibre = module.Map ? module : module.default;
    maplibre.setWorkerUrl(mapWorkerUrl);
    map = new maplibre.Map({ container: mapElement.value, style: "https://tiles.openfreemap.org/styles/liberty", center: destination.value, zoom: 14, attributionControl: { compact: true } });
    routeOverlay = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    routeOverlay.setAttribute("aria-hidden", "true");
    Object.assign(routeOverlay.style, { position: "absolute", inset: "0", width: "100%", height: "100%", overflow: "hidden", pointerEvents: "none", zIndex: "2" });
    routeCasing = document.createElementNS("http://www.w3.org/2000/svg", "path");
    Object.assign(routeCasing.style, { fill: "none", stroke: "#fff", strokeWidth: "12", strokeLinecap: "round", strokeLinejoin: "round" });
    routeStroke = document.createElementNS("http://www.w3.org/2000/svg", "path");
    Object.assign(routeStroke.style, { fill: "none", stroke: "#5268df", strokeWidth: "7", strokeLinecap: "round", strokeLinejoin: "round" });
    routeOverlay.append(routeCasing, routeStroke);
    map.getCanvasContainer().appendChild(routeOverlay);
    map.on("render", renderRouteOverlay);
    map.addControl(new maplibre.NavigationControl({ showCompass: false }), "bottom-right");
    map.on("load", () => {
      if (!mounted) return;
      map.addSource("live-user", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({ id: "live-user-halo", type: "circle", source: "live-user", paint: { "circle-radius": 13, "circle-color": "#ffffff" } });
      map.addLayer({ id: "live-user-dot", type: "circle", source: "live-user", paint: { "circle-radius": 8, "circle-color": "#2563eb", "circle-stroke-color": "#ffffff", "circle-stroke-width": 2 } });
      new maplibre.Marker({ color: "#e33b43" }).setLngLat(destination.value).setPopup(new maplibre.Popup({ offset: 24 }).setText(props.hotel.name)).addTo(map);
      locate();
    });
  } catch {
    state.value = "error";
    message.value = "The route map could not load. Check your internet connection and try again.";
  }
});
onBeforeUnmount(() => {
  mounted = false;
  ++routeRequest;
  if (watchId !== null && navigator.geolocation) navigator.geolocation.clearWatch(watchId);
  map?.remove();
  routeGeometry = null;
  routeOverlay = null;
  routeCasing = null;
  routeStroke = null;
});
</script>

<template>
  <section class="navigation-panel" aria-label="Live directions to hotel">
    <header class="navigation-header">
      <div><span class="eyebrow">WALKING DIRECTIONS</span><h2><Navigation :size="20" /> To {{ hotel.name }}</h2></div>
      <button class="icon-button" type="button" aria-label="Close directions" @click="emit('close')"><X :size="19" /></button>
    </header>
    <div class="navigation-map-wrap"><div ref="mapElement" class="navigation-map"></div>
      <div v-if="state === 'locating' || state === 'routing'" class="navigation-map-status" role="status">{{ message }}</div>
    </div>
    <div class="navigation-details">
      <div class="navigation-destination"><MapPin :size="18" /><span><strong>{{ hotel.name }}</strong><small>{{ hotel.address }}, {{ hotel.city }}</small></span></div>
      <p v-if="nextInstruction && state === 'ready'" class="navigation-instruction"><Navigation :size="17" />{{ nextInstruction }}</p>
      <p v-if="routeInfo && state === 'ready'" class="navigation-summary">{{ formatDistance(routeInfo.distance_meters) }} · about {{ Math.max(1, Math.round((routeInfo.duration_seconds || 0) / 60)) }} min walking</p>
      <button v-if="routeInfo && state === 'ready' && isNativeApp" type="button" class="button navigation-ar-button" @click="openArGuidance"><LocateFixed :size="17" />Open AR route arrow</button>
      <p v-if="routeInfo && state === 'ready' && !isNativeApp" class="navigation-ar-note">The AR route arrow is available in the installed Android app.</p>
      <p v-if="arError" class="error" role="alert">{{ arError }}</p>
      <p v-if="message && state === 'error'" class="error" role="alert">{{ message }}</p>
      <RouterLink v-if="!auth.user" class="button" :to="{ path: '/login', query: { next: currentRoute.fullPath } }">Sign in for live directions</RouterLink>
      <button v-else-if="state === 'idle' || state === 'error'" type="button" class="button" @click="retryRoute"><LocateFixed :size="17" />{{ state === 'error' ? 'Try again' : 'Start live directions' }}</button>
      <button v-else-if="state === 'ready'" type="button" class="text-button navigation-refresh" @click="retryRoute"><RotateCw :size="15" />Refresh route</button>
      <small class="muted">Location access is used while this screen is open. Turn on your phone’s location setting for live updates.</small>
    </div>
  </section>
</template>
