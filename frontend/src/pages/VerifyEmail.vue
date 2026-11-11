<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { api, errorMessage } from "../services/api";

const email = ref(sessionStorage.getItem("rf_pending_email") || "");
const code = ref("");
const message = ref("Enter the six-digit code from your email. It expires after 3 minutes.");
const error = ref("");
const verified = ref(false);
const canSignIn = ref(false);
const busy = ref(false);
const seconds = ref(0);
let timer;

function tick() {
  const resendAt = Number(sessionStorage.getItem("rf_verify_resend_at") || 0);
  seconds.value = Math.max(0, Math.ceil((resendAt - Date.now()) / 1000));
}

async function resend() {
  if (!email.value || seconds.value || busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    await api.post("auth/resend-verification/", { email: email.value }, { timeout: 120000 });
    sessionStorage.setItem("rf_pending_email", email.value);
    sessionStorage.setItem("rf_verify_resend_at", String(Date.now() + 60000));
    tick();
    message.value = "If this account needs verification, a new email has been sent.";
  } catch (e) {
    if (e.response?.data?.retry_after) {
      sessionStorage.setItem("rf_verify_resend_at", String(Date.now() + e.response.data.retry_after * 1000));
      tick();
    }
    error.value = errorMessage(e);
  } finally {
    busy.value = false;
  }
}

async function verify() {
  if (!email.value || !/^\d{6}$/.test(code.value) || busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    const { data } = await api.post("auth/verify-email/", { email: email.value, code: code.value });
    verified.value = true;
    canSignIn.value = data.can_sign_in;
    message.value = data.detail;
    sessionStorage.removeItem("rf_pending_email");
    sessionStorage.removeItem("rf_verify_resend_at");
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    busy.value = false;
  }
}

onMounted(() => {
  tick();
  timer = setInterval(tick, 1000);
});
onUnmounted(() => clearInterval(timer));
</script>

<template>
  <section class="auth-page section">
    <div class="auth-story">
      <span class="eyebrow">ROOMFINDER</span>
      <h1>One more<br /><em>step.</em></h1>
      <p>Verify your email before signing in to your new account.</p>
    </div>
    <div class="auth-form">
      <h2>{{ verified ? "Email verified" : "Check your email" }}</h2>
      <p class="muted">{{ message }}</p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <RouterLink v-if="verified && canSignIn" class="button full" to="/login">Go to login</RouterLink>
      <form v-else @submit.prevent="verify">
        <label>Email<input v-model="email" type="email" autocomplete="email" required /></label>
        <label>Verification code<input v-model="code" type="text" inputmode="numeric" autocomplete="one-time-code" maxlength="6" pattern="[0-9]{6}" required /></label>
        <button class="button full" :disabled="busy || code.length !== 6">
          {{ busy ? "Checking..." : "Verify account" }}
        </button>
      </form>
      <button v-if="!verified" type="button" class="button full" :disabled="busy || seconds > 0 || !email" @click="resend">
        {{ busy ? "One moment..." : seconds ? `Resend in ${seconds}s` : "Send another code" }}
      </button>
    </div>
  </section>
</template>
