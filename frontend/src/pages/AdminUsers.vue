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
const deleteTarget = ref(null);
const deleteUsername = ref("");
const deleting = ref(false);
const manageTab = ref("owners");
const accountSearch = ref("");
const editTarget = ref(null);
const editForm = ref({});
const ownerTab = ref("all");
const showCreateForm = ref(false);
const creating = ref(false);
const createForm = ref({
  role: "customer",
  first_name: "",
  last_name: "",
  username: "",
  email: "",
  phone: "",
  password: "",
});
const customerPage = ref(1);
const customersPerPage = 5;
const owners = computed(() => users.value.filter((user) => user.role === "owner"));
const customers = computed(() => users.value.filter((user) => user.role === "customer"));
const administrators = computed(() => users.value.filter((user) => user.role === "admin"));
const ownerStatuses = ["all", "pending", "approved", "rejected"];
const ownerCount = (status) => status === "all" ? owners.value.length : owners.value.filter((user) => user.owner_approval_status === status).length;
const visibleOwners = computed(() => ownerTab.value === "all" ? owners.value : owners.value.filter(
  (user) => user.owner_approval_status === ownerTab.value,
));
const customerPageCount = computed(() => Math.max(1, Math.ceil(customers.value.length / customersPerPage)));
const currentCustomerPage = computed(() => Math.min(customerPage.value, customerPageCount.value));
const visibleCustomers = computed(() => customers.value.slice(
  (currentCustomerPage.value - 1) * customersPerPage,
  currentCustomerPage.value * customersPerPage,
));
const managedAccounts = computed(() => {
  const source = manageTab.value === "owners" ? owners.value : customers.value;
  const term = accountSearch.value.trim().toLowerCase();
  return source.filter((user) => !term || [user.username, user.display_name, user.email].some((value) => (value || "").toLowerCase().includes(term)));
});

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

async function createAccount() {
  creating.value = true;
  error.value = "";
  notice.value = "";
  try {
    const created = (await api.post("admin/users/", createForm.value)).data;
    showCreateForm.value = false;
    createForm.value = { role: "customer", first_name: "", last_name: "", username: "", email: "", phone: "", password: "" };
    sessionStorage.removeItem("rf_admin_users");
    customerPage.value = 1;
    notice.value = `${created.role === "owner" ? "Hotel owner" : "User"} ${created.username} created. The account is active and no verification email was sent.`;
    await load();
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    creating.value = false;
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
function startDelete(user) {
  deleteTarget.value = user.id;
  editTarget.value = null;
  deleteUsername.value = "";
  error.value = "";
  notice.value = "";
}

function cancelDelete() {
  deleteTarget.value = null;
  deleteUsername.value = "";
}

function startEdit(user) {
  editTarget.value = user.id;
  editForm.value = {
    first_name: user.first_name || "",
    last_name: user.last_name || "",
    phone: user.phone || "",
  };
  deleteTarget.value = null;
  error.value = "";
}

async function saveEdit(user) {
  busyId.value = user.id;
  error.value = "";
  notice.value = "";
  try {
    await api.patch(`admin/users/${user.id}/`, editForm.value);
    editTarget.value = null;
    sessionStorage.removeItem("rf_admin_users");
    notice.value = `${user.username}'s account details were updated.`;
    await load();
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    busyId.value = null;
  }
}

async function deleteAccount(user) {
  if (deleteUsername.value !== user.username || deleting.value) return;
  deleting.value = true;
  error.value = "";
  notice.value = "";
  try {
    await api.delete(`admin/users/${user.id}/`, { data: { confirm_username: deleteUsername.value } });
    cancelDelete();
    sessionStorage.removeItem("rf_admin_users");
    notice.value = `${user.username} and their related records were deleted.`;
    await load();
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    deleting.value = false;
  }
}

onMounted(load);
</script>

<template>
  <section class="section page">
    <span class="eyebrow">ROOMFINDER ADMINISTRATION</span>
    <h1>Users<span>.</span></h1>
    <p class="lead">View account lists here, then make changes in the separate management panel.</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="notice" class="success" role="status">{{ notice }}</p>
    <p v-if="loading">Connecting to the user database...</p>
    <button v-if="!loading" class="button secondary small" @click="load">Refresh users</button>

    <article class="panel" v-if="!loading">
      <h2>All owners ({{ owners.length }})</h2>
      <p class="muted">View owner details and their properties. This section has no account actions.</p>
      <div class="tabs owner-tabs" aria-label="Hotel owner approval status">
        <button
          v-for="status in ownerStatuses"
          :key="status"
          type="button"
          :class="{ active: ownerTab === status }"
          :aria-pressed="ownerTab === status"
          @click="ownerTab = status"
        >{{ status === "all" ? "All owners" : status }} ({{ ownerCount(status) }})</button>
      </div>
      <p v-if="!visibleOwners.length" class="muted owner-empty">{{ ownerTab === "all" ? "No hotel owners yet." : `No ${ownerTab} hotel owners.` }}</p>
      <div v-for="user in visibleOwners" :key="user.id" class="verification-row">
        <div>
          <strong>{{ user.display_name || user.username }}</strong>
          <span class="badge owner-status" :class="user.owner_approval_status">{{ user.owner_approval_status }}</span>
          <p>{{ user.email }}</p>
          <small>{{ user.email_verified ? "Email verified" : "Waiting for email verification" }}</small>
          <div v-if="user.hotels.length">
            <p v-for="hotel in user.hotels" :key="hotel.id">
              <RouterLink class="button secondary small" :to="`/admin/hotels/${hotel.id}`">Open {{ hotel.name }}</RouterLink>
              · {{ hotel.address }}, {{ hotel.city }} · {{ hotel.status }}
              <small>{{ hotel.description }}</small>
            </p>
          </div>
          <p v-else class="muted">No hotels yet.</p>
        </div>
      </div>
    </article>

    <article class="panel" v-if="!loading">
      <h2>Customers ({{ customers.length }})</h2>
      <p class="muted">Read-only customer list.</p>
      <p v-if="!customers.length" class="muted">None yet.</p>
      <div v-else class="table-scroll">
        <table>
          <thead><tr><th>Username</th><th>Email</th><th>Status</th></tr></thead>
          <tbody>
            <tr v-for="user in visibleCustomers" :key="user.id">
                <td>{{ user.display_name || user.username }}</td>
                <td>{{ user.email }}</td>
                <td>{{ user.is_active ? "active" : "unverified" }}</td>
              </tr>
          </tbody>
        </table>
      </div>
      <div v-if="customers.length > customersPerPage" class="customer-pagination">
        <span>Showing {{ (currentCustomerPage - 1) * customersPerPage + 1 }}–{{ Math.min(currentCustomerPage * customersPerPage, customers.length) }} of {{ customers.length }}</span>
        <div class="pagination-actions">
          <button class="button secondary small" type="button" :disabled="currentCustomerPage === 1" @click="customerPage = currentCustomerPage - 1">Previous</button>
          <span>Page {{ currentCustomerPage }} of {{ customerPageCount }}</span>
          <button class="button secondary small" type="button" :disabled="currentCustomerPage === customerPageCount" @click="customerPage = currentCustomerPage + 1">Next</button>
        </div>
      </div>
      <h3>Administrators ({{ administrators.length }})</h3>
      <p v-if="!administrators.length" class="muted">None yet.</p>
      <p v-for="user in administrators" :key="user.id">{{ user.username }} · {{ user.email }}</p>
    </article>

    <article class="panel account-management" v-if="!loading">
      <h2>Manage owners & users</h2>
      <p class="muted">Edit account details, review owner access, or delete accounts here. These actions are separate from the read-only lists above.</p>
      <button class="button small" type="button" @click="showCreateForm = !showCreateForm">{{ showCreateForm ? "Close form" : "Create account" }}</button>
      <form v-if="showCreateForm" class="account-create-form" @submit.prevent="createAccount">
        <h3>Create an account without email verification</h3>
        <p class="muted">The account will be active immediately. No verification email is sent. Share the temporary password with the person privately.</p>
        <label>Account type
          <select v-model="createForm.role">
            <option value="customer">Traveler / user</option>
            <option value="owner">Hotel owner (approved)</option>
          </select>
        </label>
        <div class="form-row"><label>First name<input v-model.trim="createForm.first_name" maxlength="150" required /></label><label>Last name<input v-model.trim="createForm.last_name" maxlength="150" required /></label></div>
        <div class="form-row"><label>Username<input v-model.trim="createForm.username" autocomplete="off" maxlength="150" required /></label><label>Email<input v-model.trim="createForm.email" type="email" autocomplete="off" required /></label></div>
        <label>Phone (optional)<input v-model.trim="createForm.phone" maxlength="30" /></label>
        <label>Temporary password<input v-model="createForm.password" type="password" autocomplete="new-password" minlength="8" required /><small>At least 8 characters and must pass the site’s password rules.</small></label>
        <button class="button small" type="submit" :disabled="creating">{{ creating ? "Creating account..." : "Create account" }}</button>
      </form>
      <div class="tabs owner-tabs" aria-label="Choose accounts to manage">
        <button type="button" :class="{ active: manageTab === 'owners' }" @click="manageTab = 'owners'; accountSearch = ''">Manage owners ({{ owners.length }})</button>
        <button type="button" :class="{ active: manageTab === 'users' }" @click="manageTab = 'users'; accountSearch = ''">Manage users ({{ customers.length }})</button>
      </div>
      <label class="account-search">Search {{ manageTab }}<input v-model="accountSearch" placeholder="Name, username, or email" /></label>
      <p v-if="!managedAccounts.length" class="muted">No matching {{ manageTab }}.</p>
      <div v-for="user in managedAccounts" :key="user.id" class="manage-account-row">
        <div class="manage-account-summary">
          <div><strong>{{ user.display_name || user.username }}</strong><span class="badge owner-status" :class="user.owner_approval_status" v-if="manageTab === 'owners'">{{ user.owner_approval_status }}</span><p>{{ user.username }} · {{ user.email }}<small v-if="user.phone"> · {{ user.phone }}</small></p></div>
          <div class="account-actions">
            <button class="button secondary small" type="button" :disabled="deleting || busyId !== null" @click="startEdit(user)">Edit details</button>
            <template v-if="manageTab === 'owners'">
              <button v-if="user.owner_approval_status !== 'approved'" class="button small" type="button" :disabled="busyId !== null || !user.email_verified" @click="review(user, 'approved')">Approve owner</button>
              <button v-if="user.owner_approval_status === 'pending'" class="button secondary small" type="button" :disabled="busyId !== null" @click="review(user, 'rejected')">Reject owner</button>
            </template>
            <button class="button secondary small delete-link" type="button" :disabled="deleting || busyId !== null" @click="startDelete(user)">Delete</button>
          </div>
        </div>
        <form v-if="editTarget === user.id" class="account-edit-form" @submit.prevent="saveEdit(user)">
          <div class="form-row"><label>First name<input v-model="editForm.first_name" maxlength="150" /></label><label>Last name<input v-model="editForm.last_name" maxlength="150" /></label></div>
          <p class="muted">Email: {{ user.email }} (managed separately to preserve verification)</p>
          <label>Phone<input v-model="editForm.phone" maxlength="30" /></label>
          <div class="delete-actions"><button class="button small" type="submit" :disabled="busyId !== null">Save account details</button><button class="button secondary small" type="button" @click="editTarget = null">Cancel</button></div>
        </form>
        <form v-if="deleteTarget === user.id" class="delete-account-form" @submit.prevent="deleteAccount(user)">
          <p>{{ manageTab === 'owners' ? 'Delete this owner and their hotels, rooms, bookings, reviews, and photos?' : 'Delete this user and their bookings and reviews?' }}</p>
          <label :for="`manage-delete-${user.id}`">Type <strong>{{ user.username }}</strong> to confirm</label>
          <input :id="`manage-delete-${user.id}`" v-model="deleteUsername" autocomplete="off" />
          <div class="delete-actions"><button class="button delete-account-button small" type="submit" :disabled="deleting || deleteUsername !== user.username">{{ deleting ? 'Deleting...' : 'Confirm delete' }}</button><button class="button secondary small" type="button" :disabled="deleting" @click="cancelDelete">Cancel</button></div>
        </form>
      </div>
    </article>
  </section>
</template>

<style scoped>
.owner-tabs { margin: 1rem 0; }
.owner-tabs button { cursor: pointer; }
.owner-empty { margin: 1.5rem 0; }
.owner-status { margin-left: .6rem; }
.owner-status.approved { background: #e9f3e0; color: #688c46; }
.customer-pagination { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: .75rem; margin: 1rem 0 1.5rem; font-size: 12px; }
.pagination-actions { display: flex; align-items: center; gap: .75rem; }
.pagination-actions button:disabled { opacity: .5; cursor: not-allowed; }
.delete-link { color: #a93d32; border-color: #dfb6ad; }
.delete-account-form { display: grid; gap: .65rem; max-width: 28rem; margin-top: 1rem; padding: 1rem; border: 1px solid #dfb6ad; border-radius: .5rem; white-space: normal; }
.delete-account-form p { margin: 0; }
.delete-account-form input { width: 100%; }
.delete-actions { display: flex; flex-wrap: wrap; gap: .5rem; }
.delete-account-button { background: #a93d32; border-color: #a93d32; }
.delete-account-button:hover { background: #842f27; }
.delete-account-button:disabled { opacity: .5; cursor: not-allowed; }
.account-management { margin-top: 1.5rem; }
.account-create-form { display: grid; gap: .8rem; max-width: 42rem; margin: 1rem 0 1.5rem; padding: 1rem; border: 1px solid #d8e1d1; border-radius: .5rem; }
.account-create-form h3, .account-create-form p { margin: 0; }
.account-create-form label { display: grid; gap: .35rem; }
.account-create-form small { color: #75816f; }
.account-search { display: block; max-width: 28rem; margin: 1rem 0; }
.manage-account-row { padding: 1rem 0; border-top: 1px solid #e1e5d9; }
.manage-account-summary, .account-actions { display: flex; align-items: center; justify-content: space-between; gap: .75rem; }
.manage-account-summary p { margin: .4rem 0 0; font-size: 12px; color: #75816f; }
.account-actions { flex-wrap: wrap; justify-content: flex-end; }
.account-edit-form { display: grid; gap: .75rem; max-width: 42rem; margin-top: 1rem; padding: 1rem; border: 1px solid #d8e1d1; border-radius: .5rem; }
@media (max-width: 700px) { .manage-account-summary { align-items: flex-start; flex-direction: column; } .account-actions { justify-content: flex-start; } }
</style>
