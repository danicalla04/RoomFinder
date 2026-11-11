<script setup>
import { computed, onMounted, ref } from "vue";
import { api, errorMessage } from "../services/api";

let cachedUsers = [];
try {
  const parsed = JSON.parse(sessionStorage.getItem("rf_admin_users") || "[]");
  cachedUsers = Array.isArray(parsed) ? parsed : [];
} catch { cachedUsers = []; }
const users = ref(cachedUsers);
const loading = ref(!sessionStorage.getItem("rf_admin_users"));
const busyId = ref(null);
const error = ref("");
const notice = ref("");
const owners = computed(() => users.value.filter((user) => user.role === "owner"));
const customers = computed(() => users.value.filter((user) => user.role === "customer"));
const administrators = computed(() => users.value.filter((user) => user.role === "admin"));
const pendingOwners = computed(() => owners.value.filter(
  (user) => user.owner_approval_status === "pending",
));

async function load() {
  error.value = "";
  try {
    users.value = (await api.get("admin/users/")).data;
    sessionStorage.setItem("rf_admin_users", JSON.stringify(users.value));
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}

async function review(user, decision) {
  busyId.value = user.id;
  error.value = "";
  notice.value = "";
  try {
    await api.post(`admin/users/${user.id}/review/`, { decision });
    notice.value = `${user.username} ${decision === "approved" ? "approved" : "declined"}.`;
    await load();
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    busyId.value = null;
  }
}
onMounted(load);
</script>

<template>
  <section class="section page">
    <span class="eyebrow">ROOMFINDER ADMINISTRATION</span>
    <h1>Users<span>.</span></h1>
    <p class="lead">Review hotel-owner applications and see who can use RoomFinder.</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <p v-if="loading">Connecting to the user database...</p>
    <button v-if="!loading" class="button secondary small" @click="load">Refresh users</button>

    <article class="panel" v-if="!loading">
      <h2>Hotel owners ({{ owners.length }})</h2>
      <p class="muted">Review requests and open each property to monitor rooms and reservations.</p>
      <h3>Approval requests ({{ pendingOwners.length }})</h3>
      <p v-if="!pendingOwners.length" class="muted">None pending.</p>
      <div v-for="user in pendingOwners" :key="user.id" class="verification-row">
        <div>
          <strong>{{ user.display_name || user.username }}</strong>
          <p>{{ user.email }}</p>
          <small>{{ user.email_verified ? "Email verified" : "Waiting for email verification" }}</small>
          <p class="muted">{{ user.hotels.length ? `${user.hotels.length} hotel(s) already linked` : "No hotels yet. Approval is required before creating one." }}</p>
        </div>
        <button class="button small" :disabled="busyId !== null || !user.email_verified" @click="review(user, 'approved')">Approve owner</button>
        <button class="button secondary small" :disabled="busyId !== null" @click="review(user, 'rejected')">Decline</button>
      </div>
      <h3>All owners</h3>
      <p v-if="!owners.length" class="muted">None yet.</p>
      <div v-for="user in owners" :key="user.id" class="verification-row">
        <div>
          <strong>{{ user.display_name || user.username }}</strong>
          <p>{{ user.email }}</p>
          <small>{{ user.email_verified || user.is_active ? "Email confirmed or existing account" : "Email not verified" }} · {{ user.owner_approval_status }}</small>
          <div v-if="user.hotels.length">
            <p v-for="hotel in user.hotels" :key="hotel.id">
              <RouterLink class="button secondary small" :to="`/admin/hotels/${hotel.id}`">Open {{ hotel.name }}</RouterLink>
              · {{ hotel.address }}, {{ hotel.city }} · {{ hotel.status }}
              <small>{{ hotel.description }}</small>
            </p>
          </div>
          <p v-else class="muted">No hotels yet.</p>
        </div>
        <button v-if="user.owner_approval_status === 'rejected' && user.email_verified" class="button small" :disabled="busyId !== null" @click="review(user, 'approved')">Approve owner</button>
      </div>
    </article>

    <article class="panel" v-if="!loading">
      <h2>Users ({{ customers.length }})</h2>
      <p v-if="!customers.length" class="muted">None yet.</p>
      <div v-else class="table-scroll">
        <table>
          <thead><tr><th>Username</th><th>Email</th><th>Status</th></tr></thead>
          <tbody>
            <tr v-for="user in customers" :key="user.id">
              <td>{{ user.display_name || user.username }}</td>
              <td>{{ user.email }}</td>
              <td>{{ user.is_active ? "active" : "unverified" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <h3>Administrators ({{ administrators.length }})</h3>
      <p v-if="!administrators.length" class="muted">None yet.</p>
      <p v-for="user in administrators" :key="user.id">{{ user.username }} · {{ user.email }}</p>
    </article>
  </section>
</template>
