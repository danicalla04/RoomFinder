<script setup>
import { MapPin, Star, ArrowUpRight, Check, Plus } from "lucide-vue-next";
import { useCompare } from "../stores/compare";
import { money } from "../services/api";
defineProps({ hotel: Object, dates: Object });
const compare = useCompare();
</script>
<template>
  <article class="hotel-card">
    <RouterLink
      :to="{ path: `/hotels/${hotel.id}`, query: dates }"
      class="card-image"
      ><img
        v-if="hotel.photos?.length"
        :src="hotel.photos[0].image"
        :alt="hotel.name"
        loading="lazy"
      />
      <div v-else class="image-fallback">{{ hotel.name.slice(0, 1) }}</div>
      <span
        class="image-tag"
        title="Owner-provided property category, not guest review score or official accreditation."
        >{{ hotel.stars }}-star category</span
      ></RouterLink
    ><button
      class="compare-button"
      :class="{ selected: compare.ids.includes(hotel.id) }"
      :disabled="!compare.ids.includes(hotel.id) && compare.ids.length >= 3"
      @click="compare.toggle(hotel.id)"
      :aria-label="`Compare ${hotel.name}`"
    >
      <Check v-if="compare.ids.includes(hotel.id)" :size="17" /><Plus
        v-else
        :size="17"
      />
    </button>
    <div class="card-meta">
      <span><MapPin :size="13" />{{ hotel.city }}</span
      ><span class="rating"
        ><Star :size="13" fill="currentColor" />{{
          hotel.rating ? Number(hotel.rating).toFixed(1) : "New"
        }}
        <small v-if="hotel.review_count"
          >({{ hotel.review_count }})</small
        ></span
      >
    </div>
    <RouterLink :to="{ path: `/hotels/${hotel.id}`, query: dates }"
      ><h3>{{ hotel.name }}</h3></RouterLink
    >
    <p class="amenity-line">{{ hotel.amenities.slice(0, 3).join(" · ") }}</p>
    <div class="card-bottom">
      <span
        ><strong>{{ money(hotel.min_price) }}</strong
        ><small> / night</small></span
      ><RouterLink
        :to="{ path: `/hotels/${hotel.id}`, query: dates }"
        class="round-link"
        :aria-label="`View ${hotel.name}`"
        ><ArrowUpRight :size="20"
      /></RouterLink>
    </div>
  </article>
</template>
