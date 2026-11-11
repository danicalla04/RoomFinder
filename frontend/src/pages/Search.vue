<script setup>
import { ref, computed, onMounted } from "vue";
import {
  Search,
  MapPin,
  CalendarDays,
  Users,
  ArrowUpRight,
  SlidersHorizontal,
  Map,
  LayoutGrid,
  ArrowRight,
  ShieldCheck,
  BedDouble,
  Sparkles,
} from "lucide-vue-next";
import { api, errorMessage, today, nextDay } from "../services/api";
import { CITY_NAME, LOCATION_LABEL } from "../services/location";
import HotelCard from "../components/HotelCard.vue";
import HotelMap from "../components/HotelMap.vue";
const hotels = ref([]),
  loading = ref(true),
  error = ref(""),
  showMap = ref(false),
  filters = ref(false);
const form = ref({
  search: "",
  check_in: today(),
  check_out: nextDay(today()),
  guests: 2,
  min_price: "",
  max_price: "",
  stars: "",
  rating: "",
  sort: "newest",
  amenities: [],
});
const dates = computed(() => ({
  check_in: form.value.check_in,
  check_out: form.value.check_out,
  guests: form.value.guests,
}));
async function load() {
  loading.value = true;
  error.value = "";
  try {
    const p = {
      ...form.value,
      amenities: form.value.amenities.join(","),
      city: CITY_NAME,
    };
    hotels.value = (await api.get("hotels/", { params: p })).data;
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
function showCalapanMap() {
  showMap.value = true;
  document.getElementById("stays")?.scrollIntoView({ behavior: "smooth" });
}
onMounted(() => load());
</script>
<template>
  <section class="hero section">
    <div class="hero-copy">
      <span class="eyebrow"
        ><span class="tiny-line"></span>GOOD PLACES. GREAT POSSIBILITIES.</span
      >
      <h1>Somewhere new.<br />Something <em>you.</em></h1>
      <p>
        Find your next stay in Calapan City, Oriental Mindoro.<br
          class="desktop"
        />
        Find your stay. Choose your room. Make it yours.
      </p>
      <div class="hero-proof">
        <span class="proof-icon"><BedDouble :size="20" /></span
        ><span
          >Your room, your choice.<small
            >See the floor. Pick the perfect spot.</small
          ></span
        ><ArrowUpRight :size="21" />
      </div>
    </div>
    <div class="hero-visual">
      <img
        src="/hero.jpg"
        alt="Illustrative sample hotel for Calapan stays"
      /><span class="hero-coordinate"
        >13.4000&deg; N &nbsp; 121.1833&deg; E</span
      >
      <div class="hero-label">
        <span>A change of scenery</span><strong>Closer than you think.</strong
        ><a href="#stays" aria-label="Explore available stays"
          ><ArrowUpRight :size="23"
        /></a>
      </div>
      <span class="vertical-note">CURATED STAYS, CONSIDERED DETAILS</span>
    </div>
  </section>
  <section class="search-section section">
    <form class="search-bar" @submit.prevent="load()">
      <label class="destination"
        ><span><MapPin :size="15" /> LOCATION</span
        ><input
          :value="LOCATION_LABEL"
          readonly
          aria-label="Destination" /></label
      ><label
        ><span><CalendarDays :size="15" /> CHECK IN</span
        ><input
          type="date"
          v-model="form.check_in"
          :min="today()"
          required
          @change="
            form.check_out <= form.check_in &&
            (form.check_out = nextDay(form.check_in))
          " /></label
      ><label
        ><span><CalendarDays :size="15" /> CHECK OUT</span
        ><input
          type="date"
          v-model="form.check_out"
          :min="nextDay(form.check_in)"
          required /></label
      ><label class="guests"
        ><span><Users :size="15" /> GUESTS</span
        ><select v-model="form.guests">
          <option v-for="n in 8" :value="n">
            {{ n }} {{ n === 1 ? "guest" : "guests" }}
          </option>
        </select></label
      ><button class="button search-submit" :disabled="loading">
        <Search :size="19" /><span>Find a stay</span>
      </button>
    </form>
    <div class="search-foot">
      <span
        ><ShieldCheck :size="14" /> Verified properties. Clear prices. A better
        way to stay.</span
      ><button class="text-button" @click="showCalapanMap">
        <MapPin :size="14" /> Explore Calapan map
      </button>
    </div>
  </section>
  <section id="stays" class="discovery section">
    <div class="section-heading">
      <div>
        <span class="eyebrow">YOUR NEXT CHECK-IN</span>
        <h2>Find your stay in Calapan City<span>.</span></h2>
      </div>
      <button class="text-button" @click="filters = !filters">
        <SlidersHorizontal :size="17" />{{ filters ? "Hide" : "Refine" }} search
      </button>
    </div>
    <div class="discovery-controls">
      <div class="tabs">
        <button class="active" @click="load()">{{ CITY_NAME }}</button>
        <span class="service-province">Oriental Mindoro</span>
      </div>
      <div class="view-switch">
        <button :class="{ active: !showMap }" @click="showMap = false">
          <LayoutGrid :size="15" />Grid</button
        ><button :class="{ active: showMap }" @click="showMap = true">
          <Map :size="15" />Map
        </button>
      </div>
    </div>
    <form v-if="filters" class="filter-panel" @submit.prevent="load()">
      <label
        >Hotel or area in Calapan<input
          v-model="form.search"
          placeholder="Hotel name, street, or barangay"
      /></label>
      <label
        >Min price (PHP)<input
          type="number"
          min="0"
          v-model="form.min_price"
          placeholder="Any" /></label
      ><label
        >Max price (PHP)<input
          type="number"
          min="0"
          v-model="form.max_price"
          placeholder="Any" /></label
      ><label
        >Property category<select v-model="form.stars">
          <option value="">Any stars</option>
          <option v-for="n in [3, 4, 5]" :value="n">{{ n }}+ stars</option>
        </select></label
      ><label
        >Guest rating<select v-model="form.rating">
          <option value="">Any rating</option>
          <option value="4">4+ stars</option>
          <option value="5">5 stars</option>
        </select></label
      ><label
        >Sort by<select v-model="form.sort">
          <option value="newest">Recently added</option>
          <option value="price">Price: low to high</option>
          <option value="rating">Top rated</option>
        </select></label
      >
      <div class="checks">
        <label v-for="a in ['Wi-Fi', 'Pool', 'Breakfast', 'Parking', 'Gym']"
          ><input type="checkbox" :value="a" v-model="form.amenities" />{{
            a
          }}</label
        >
      </div>
      <button class="button small">Apply filters</button>
    </form>
    <details v-if="filters" class="classification-help">
      <summary>What do property stars mean?</summary>
      <p>
        Stars (1-5) are the owner's property category. They are separate from
        guest review scores and do not certify official accreditation. Sample
        hotel categories are demonstration data.
      </p>
    </details>
    <p class="error" v-if="error" role="alert">{{ error }}</p>
    <div class="results-caption">
      <span>{{
        loading
          ? "Finding your next favorite place..."
          : `${hotels.length} stays in Calapan City`
      }}</span
      ><span>PHP · per room, per night</span>
    </div>
    <div v-if="loading" class="hotel-grid">
      <div v-for="n in 4" class="skeleton"></div>
    </div>
    <HotelMap v-else-if="showMap" :hotels="hotels" :dates="dates" />
    <div v-else-if="hotels.length" class="hotel-grid">
      <HotelCard
        v-for="hotel in hotels"
        :key="hotel.id"
        :hotel="hotel"
        :dates="dates"
      />
    </div>
    <div v-else class="empty">
      <Search :size="32" />
      <h3>No stays found this time.</h3>
      <p>Try another hotel name, date, or a wider price range.</p>
    </div>
  </section>
  <section class="difference section">
    <div>
      <span class="eyebrow">A BETTER WAY TO BOOK</span>
      <h2>Don't just book a room.<br />Choose <em>your</em> room.</h2>
      <p>
        Near the lift or at the quiet end of the hall? Our interactive floor
        plans put the choice in your hands.
      </p>
      <a href="#how-it-works" class="text-button"
        >A little more control. A lot more comfort. <ArrowRight :size="18"
      /></a>
    </div>
    <div id="how-it-works" class="steps">
      <div
        v-for="(step, i) in [
          [
            'Find your place',
            'Explore verified Calapan stays by budget and the things you love.',
          ],
          [
            'Pick your perfect room',
            'See the layout, compare rooms, and select your exact spot.',
          ],
          [
            'Make yourself at home',
            'Reserve in a few clicks. Your confirmation is ready right away.',
          ],
        ]"
      >
        <span>0{{ i + 1 }}</span>
        <div>
          <h3>{{ step[0] }}</h3>
          <p>{{ step[1] }}</p>
        </div>
      </div>
    </div>
  </section>
</template>
