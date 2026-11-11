<script setup>
import { ref, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  ArrowUpRight,
  BedDouble,
  UserRound,
  Building2,
  ShieldCheck,
} from "lucide-vue-next";
import { api, errorMessage } from "../services/api";
import { useAuth } from "../stores/auth";
const route = useRoute(),
  router = useRouter(),
  auth = useAuth(),
  register = computed(() => route.path === "/register"),
  busy = ref(false),
  error = ref(""),
  form = ref({
    username: "",
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    phone: "",
    role:
      ["customer", "owner", "admin"].includes(route.query.role) &&
      !(register.value && route.query.role === "admin")
        ? route.query.role
        : "customer",
  });
const loginRoles = [
  {
    value: "customer",
    label: "Customer",
    detail: "Find and book stays",
    icon: UserRound,
    demo: "traveler",
  },
  {
    value: "owner",
    label: "Hotel owner",
    detail: "Manage your properties",
    icon: Building2,
    demo: "hotelowner",
  },
  {
    value: "admin",
    label: "Administrator",
    detail: "Oversee RoomFinder",
    icon: ShieldCheck,
    demo: "administrator",
  },
];
const selectedRole = computed(() =>
  loginRoles.find((role) => role.value === form.value.role),
);
watch(register, (value) => {
  error.value = "";
  if (value && form.value.role === "admin") form.value.role = "customer";
});
watch(
  () => form.value.role,
  () => {
    error.value = "";
  },
);
async function submit() {
  busy.value = true;
  error.value = "";
  try {
    if (register.value) {
      await api.post("auth/register/", form.value, { timeout: 120000 });
      sessionStorage.setItem("rf_pending_email", form.value.email);
      sessionStorage.setItem("rf_verify_resend_at", String(Date.now() + 60000));
      await router.push("/verify-email");
      return;
    }
    await auth.login({
      username: form.value.username,
      password: form.value.password,
      role: form.value.role,
    });
    const next =
      typeof route.query.next === "string" &&
      route.query.next.startsWith("/") &&
      !route.query.next.startsWith("//")
        ? route.query.next
        : null;
    const home = auth.user.role === "customer" ? "/" : "/dashboard";
    const destination = next ? router.resolve(next) : null;
    const allowedNext =
      destination &&
      destination.matched.length &&
      !["/login", "/register"].includes(destination.path) &&
      !(destination.path === "/" && auth.user.role !== "customer") &&
      (!destination.meta.roles ||
        destination.meta.roles.includes(auth.user.role));
    await router.push(allowedNext ? next : home);
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <section class="auth-page section">
    <div class="auth-story">
      <span class="eyebrow">STAY CURIOUS. STAY SOMEWHERE GOOD.</span>
      <h1>Your next chapter<br />starts <em>here.</em></h1>
      <img src="/hero.jpg" alt="A tropical hotel pool" />
      <p>
        Thoughtful places in Calapan City, Oriental Mindoro. Your exact room.
      </p>
    </div>
    <div class="auth-form">
      <BedDouble :size="32" />
      <h2>{{ register ? "Make room for more." : "Log in to RoomFinder." }}</h2>
      <p class="muted">
        {{
          register
            ? "Create an account for your next great stay."
            : "Choose your role, then enter your account details."
        }}
      </p>
      <form @submit.prevent="submit">
        <fieldset v-if="!register" class="login-roles" :disabled="busy">
          <legend>Log in as</legend>
          <div class="role-options">
            <label
              v-for="role in loginRoles"
              :key="role.value"
              class="role-option"
              :class="{ selected: form.role === role.value }"
            >
              <input
                v-model="form.role"
                type="radio"
                name="login-role"
                :value="role.value"
                :aria-label="role.label"
              />
              <component :is="role.icon" :size="22" aria-hidden="true" />
              <strong>{{ role.label }}</strong>
              <small>{{ role.detail }}</small>
            </label>
          </div>
        </fieldset>
        <div v-if="register" class="segmented">
          <label
            ><input type="radio" value="customer" v-model="form.role" />I'm a
            traveler</label
          ><label
            ><input type="radio" value="owner" v-model="form.role" />I'm a hotel
            owner</label
          >
        </div>
        <div v-if="register" class="form-row">
          <label
            >First name<input
              v-model="form.first_name"
              required
              autocomplete="given-name"
              maxlength="150" /></label
          ><label
            >Last name<input
              v-model="form.last_name"
              required
              autocomplete="family-name"
              maxlength="150"
          /></label>
        </div>
        <label
          >Username<input
            v-model="form.username"
            required
            autocomplete="username"
            maxlength="150" /></label
        ><label v-if="register"
          >Email<input
            v-model="form.email"
            type="email"
            required
            autocomplete="email" /></label
        ><label v-if="register"
          >Phone (optional)<input
            v-model="form.phone"
            type="tel"
            autocomplete="tel"
            maxlength="30" /></label
        ><label
          >Password<input
            v-model="form.password"
            type="password"
            :autocomplete="register ? 'new-password' : 'current-password'"
            :minlength="register ? 8 : 1"
            required
        /></label>
        <p v-if="register" class="muted">
          Use at least 8 characters and a password that is not common or
          entirely numeric.
        </p>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button class="button full" :disabled="busy">
          {{ busy ? "One moment..." : register ? "Create account" : "Log in"
          }}<ArrowUpRight :size="18" />
        </button>
      </form>
      <p class="auth-switch">
        {{ register ? "Already have an account?" : "New to RoomFinder?" }}
        <RouterLink
          :to="{ path: register ? '/login' : '/register', query: route.query }"
          >{{ register ? "Log in" : "Create an account" }}</RouterLink
        >
      </p>
      <p class="auth-switch"><RouterLink to="/verify-email">Have a verification code? Enter it here</RouterLink></p>
      <p class="demo-note">
        {{ selectedRole.label }} demo: <strong>{{ selectedRole.demo }}</strong
        ><br />
        Password: RoomFinder!2026
      </p>
    </div>
  </section>
</template>
