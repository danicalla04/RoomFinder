<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from "vue";
import { MapPin, RotateCcw, ExternalLink, LoaderCircle } from "lucide-vue-next";
import L from "leaflet";
import mapWorkerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import "maplibre-gl/dist/maplibre-gl.css";
import { CALAPAN_CENTER, LOCATION_LABEL } from "../services/location";
import { money } from "../services/api";
const props = defineProps({
  hotels: { type: Array, default: () => [] },
  dates: { type: Object, default: () => ({}) },
});
const panel = ref(),
  el = ref(),
  renderer = ref("vector"),
  style = ref("streets"),
  status = ref("loading"),
  message = ref("");
let vectorMap,
  basicMap,
  gl,
  markers = [],
  observer,
  timer,
  epoch = 0,
  disposed = false;
const styles = {
  streets: "https://tiles.openfreemap.org/styles/liberty",
  light: "https://tiles.openfreemap.org/styles/positron",
};
const googleUrl = computed(() =>
  googleLink(props.hotels.length === 1 ? props.hotels[0] : null),
);
function googleLink(hotel) {
  const query = hotel ? `${hotel.latitude},${hotel.longitude}` : LOCATION_LABEL;
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}
function viewLink(hotel) {
  const params = new URLSearchParams(
    Object.entries(props.dates)
      .filter(([, v]) => v != null)
      .map(([k, v]) => [k, String(v)]),
  );
  return `/hotels/${hotel.id}${params.size ? "?" + params.toString() : ""}`;
}
function popup(hotel) {
  const card = document.createElement("article");
  card.className = "map-hotel-popup";
  if (hotel.photos?.length) {
    const img = document.createElement("img");
    img.src = hotel.photos[0].image;
    img.alt = hotel.name;
    card.appendChild(img);
  }
  const location = document.createElement("small");
  location.textContent = LOCATION_LABEL;
  card.appendChild(location);
  const title = document.createElement("h3");
  title.textContent = hotel.name;
  card.appendChild(title);
  const rate = document.createElement("p");
  rate.textContent = `From ${money(hotel.min_price)} / night`;
  card.appendChild(rate);
  const links = document.createElement("div");
  links.className = "map-popup-links";
  const view = document.createElement("a");
  view.href = viewLink(hotel);
  view.textContent = "View rooms";
  links.appendChild(view);
  const directions = document.createElement("a");
  directions.href = googleLink(hotel);
  directions.target = "_blank";
  directions.rel = "noopener noreferrer";
  directions.textContent = "Google Maps";
  links.appendChild(directions);
  card.appendChild(links);
  return card;
}
function pin(hotel) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "hotel-price-pin";
  button.textContent = money(hotel.min_price);
  button.setAttribute(
    "aria-label",
    `${hotel.name}, from ${money(hotel.min_price)} per night`,
  );
  return button;
}
function validHotels() {
  return props.hotels.filter(
    (h) =>
      Number.isFinite(Number(h.latitude)) &&
      Number.isFinite(Number(h.longitude)),
  );
}
function fitHotels() {
  const hotels = validHotels();
  if (!hotels.length) return;
  if (vectorMap) {
    const points = hotels.map((h) => [Number(h.longitude), Number(h.latitude)]);
    if (points.length === 1) vectorMap.jumpTo({ center: points[0], zoom: 15 });
    else {
      const bounds = new gl.LngLatBounds();
      points.forEach((p) => bounds.extend(p));
      vectorMap.fitBounds(bounds, { padding: 75, maxZoom: 15, duration: 0 });
    }
  }
  if (basicMap)
    basicMap.fitBounds(
      hotels.map((h) => [Number(h.latitude), Number(h.longitude)]),
      { padding: [65, 65], maxZoom: 15 },
    );
}
function renderMarkers() {
  markers.forEach((m) => m.remove());
  markers = [];
  for (const hotel of validHotels()) {
    const button = pin(hotel);
    if (vectorMap) {
      const detail = new gl.Popup({
        offset: 20,
        maxWidth: "255px",
      }).setDOMContent(popup(hotel));
      detail.on("open", () => button.classList.add("is-active"));
      detail.on("close", () => button.classList.remove("is-active"));
      markers.push(
        new gl.Marker({ element: button, anchor: "bottom" })
          .setLngLat([Number(hotel.longitude), Number(hotel.latitude)])
          .setPopup(detail)
          .addTo(vectorMap),
      );
    } else if (basicMap) {
      markers.push(
        L.marker([Number(hotel.latitude), Number(hotel.longitude)], {
          icon: L.divIcon({
            className: "hotel-pin-wrap",
            html: button,
            iconSize: [82, 32],
            iconAnchor: [41, 32],
          }),
        })
          .bindPopup(popup(hotel), { maxWidth: 255 })
          .addTo(basicMap),
      );
    }
  }
  fitHotels();
}
function startLoading() {
  status.value = "loading";
  message.value = "";
  clearTimeout(timer);
  timer = setTimeout(() => {
    if (!disposed && status.value === "loading") {
      status.value = "error";
      message.value =
        "The map is taking longer to load. Retry or use the basic map.";
    }
  }, 15000);
}
function destroyMaps() {
  clearTimeout(timer);
  markers.forEach((m) => m.remove());
  markers = [];
  vectorMap?.remove();
  vectorMap = null;
  basicMap?.remove();
  basicMap = null;
}
async function initVector() {
  const version = ++epoch;
  destroyMaps();
  renderer.value = "vector";
  startLoading();
  try {
    const module = await import("maplibre-gl");
    if (disposed || version !== epoch) return;
    gl = module.Map ? module : module.default;
    gl.setWorkerUrl(mapWorkerUrl);
    const map = new gl.Map({
      container: el.value,
      style: styles[style.value],
      center: [CALAPAN_CENTER[1], CALAPAN_CENTER[0]],
      zoom: 14,
      maxZoom: 19,
      attributionControl: { compact: true },
    });
    vectorMap = map;
    map.addControl(
      new gl.NavigationControl({ showCompass: false }),
      "bottom-right",
    );
    map.addControl(
      new gl.FullscreenControl({ container: panel.value }),
      "top-right",
    );
    map.addControl(
      new gl.ScaleControl({ maxWidth: 100, unit: "metric" }),
      "bottom-left",
    );
    map.on("load", () => {
      if (vectorMap !== map) return;
      clearTimeout(timer);
      status.value = "ready";
      message.value = "";
    });
    map.on("error", () => {
      if (vectorMap !== map || status.value === "ready") return;
      status.value = "error";
      message.value =
        "Street details could not load. Check your connection, retry, or use the basic map.";
    });
    renderMarkers();
  } catch {
    if (!disposed && version === epoch) initBasic();
  }
}
function initBasic() {
  ++epoch;
  destroyMaps();
  renderer.value = "basic";
  startLoading();
  let loaded = false;
  try {
    basicMap = L.map(el.value).setView(CALAPAN_CENTER, 14);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    })
      .on("tileload", () => {
        loaded = true;
        clearTimeout(timer);
        status.value = "ready";
        message.value = "";
      })
      .on("tileerror", () => {
        if (!loaded) {
          status.value = "error";
          message.value =
            "Map tiles could not load. Check your connection or open Google Maps.";
        }
      })
      .addTo(basicMap);
    renderMarkers();
  } catch {
    status.value = "error";
    message.value =
      "The map is unavailable in this browser. Open Google Maps to view the area.";
  }
}
function chooseStyle(value) {
  style.value = value;
  if (!vectorMap) {
    initVector();
    return;
  }
  const current = vectorMap;
  startLoading();
  current.setStyle(styles[value]);
  current.once("idle", () => {
    if (vectorMap === current) {
      clearTimeout(timer);
      status.value = "ready";
      message.value = "";
    }
  });
}
function retry() {
  if (renderer.value === "basic") initBasic();
  else initVector();
}
watch(() => props.hotels, renderMarkers);
onMounted(() => {
  observer = new ResizeObserver(() => {
    vectorMap?.resize();
    basicMap?.invalidateSize();
  });
  observer.observe(el.value);
  initVector();
});
onBeforeUnmount(() => {
  disposed = true;
  ++epoch;
  observer?.disconnect();
  destroyMaps();
});
</script>
<template>
  <section
    ref="panel"
    class="hotel-map-panel"
    aria-label="Calapan City hotel locations map"
    :data-renderer="renderer"
    :data-map-status="status"
  >
    <div class="map-toolbar">
      <div>
        <MapPin :size="17" /><strong>Explore Calapan City</strong
        ><span>{{ hotels.length }} stays</span>
      </div>
      <div class="map-style-options">
        <button
          type="button"
          :class="{ active: renderer === 'vector' && style === 'streets' }"
          :aria-pressed="renderer === 'vector' && style === 'streets'"
          @click="chooseStyle('streets')"
        >
          Streets</button
        ><button
          type="button"
          :class="{ active: renderer === 'vector' && style === 'light' }"
          :aria-pressed="renderer === 'vector' && style === 'light'"
          @click="chooseStyle('light')"
        >
          Light</button
        ><button
          type="button"
          :class="{ active: renderer === 'basic' }"
          :aria-pressed="renderer === 'basic'"
          @click="initBasic"
        >
          Basic map
        </button>
      </div>
    </div>
    <div class="map-viewport">
      <div ref="el" class="hotel-map"></div>
      <div v-if="status === 'loading'" class="map-status" role="status">
        <LoaderCircle :size="17" class="spin" />Loading streets and places...
      </div>
      <div
        v-if="status === 'error'"
        class="map-status map-load-error"
        role="status"
      >
        <span>{{ message }}</span
        ><button type="button" @click="retry">Retry</button
        ><button v-if="renderer !== 'basic'" type="button" @click="initBasic">
          Use basic map</button
        ><a :href="googleUrl" target="_blank" rel="noopener noreferrer"
          >Open Google Maps</a
        >
      </div>
      <button type="button" class="map-fit-button" @click="fitHotels">
        <RotateCcw :size="15" />Show all stays
      </button>
    </div>
    <div class="map-footer">
      <span>Tap a price to explore a stay.</span
      ><a :href="googleUrl" target="_blank" rel="noopener noreferrer"
        >Open in Google Maps <ExternalLink :size="13"
      /></a>
    </div>
  </section>
</template>
