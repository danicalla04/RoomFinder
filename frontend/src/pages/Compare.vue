<script setup>
import { ref, onMounted } from "vue";
import { useCompare } from "../stores/compare";
import { api, money, errorMessage } from "../services/api";
import { X, ArrowRight, Star } from "lucide-vue-next";
const compare = useCompare(),
  hotels = ref([]),
  error = ref("");
onMounted(async () => {
  try {
    hotels.value = (
      await Promise.all(compare.ids.map((id) => api.get(`hotels/${id}/`)))
    ).map((r) => r.data);
  } catch (e) {
    error.value = errorMessage(e);
  }
});
</script>
<template>
  <section class="section page">
    <span class="eyebrow">SIDE BY SIDE</span>
    <h1>Find your kind of stay.</h1>
    <p class="lead">A little comparison makes the choice a little easier.</p>
    <p class="error" v-if="error">{{ error }}</p>
    <div
      v-if="hotels.filter((h) => compare.ids.includes(h.id)).length"
      class="compare-grid"
    >
      <article v-for="h in hotels.filter((h) => compare.ids.includes(h.id))">
        <img
          v-if="h.photos.length"
          :src="h.photos[0].image"
          :alt="h.name"
        /><button class="text-button" @click="compare.toggle(h.id)">
          <X :size="16" />Remove
        </button>
        <h2>{{ h.name }}</h2>
        <dl>
          <dt>Location</dt>
          <dd>{{ h.city }}</dd>
          <dt>From / night</dt>
          <dd>{{ money(h.min_price) }}</dd>
          <dt>Guest rating</dt>
          <dd>
            {{ h.rating ? Number(h.rating).toFixed(1) : "New" }} ·
            {{ h.review_count }} reviews
          </dd>
          <dt>Property class</dt>
          <dd>{{ h.stars }} stars</dd>
          <dt>Amenities</dt>
          <dd>{{ h.amenities.join(" · ") }}</dd>
          <dt>The feeling</dt>
          <dd>{{ h.description }}</dd>
        </dl>
        <RouterLink :to="`/hotels/${h.id}`" class="button"
          >Choose a room <ArrowRight :size="17"
        /></RouterLink>
      </article>
    </div>
    <div v-else class="empty">
      <h3>Your shortlist starts here.</h3>
      <p>Select up to three stays using the + button on a property card.</p>
      <RouterLink to="/" class="button">Explore stays</RouterLink>
    </div>
  </section>
</template>
