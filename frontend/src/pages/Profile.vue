<script setup>
import { ref } from "vue";
import { useAuth } from "../stores/auth";
import { api, errorMessage } from "../services/api";
const auth = useAuth(),
  form = ref({ ...auth.user }),
  error = ref(""),
  saved = ref(false),
  busy = ref(false);
async function save() {
  busy.value = true;
  error.value = "";
  saved.value = false;
  try {
    auth.user = (
      await api.patch("auth/me/", {
        first_name: form.value.first_name,
        last_name: form.value.last_name,
        phone: form.value.phone,
      })
    ).data;
    saved.value = true;
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <section class="section page narrow">
    <span class="eyebrow">A LITTLE ABOUT YOU</span>
    <h1>Your profile<span>.</span></h1>
    <p class="lead">{{ auth.user.username }} · {{ auth.user.role }}</p>
    <form class="panel profile-form" @submit.prevent="save">
      <div class="form-row">
        <label
          >First name<input v-model="form.first_name" maxlength="150" /></label
        ><label
          >Last name<input v-model="form.last_name" maxlength="150"
        /></label>
      </div>
      <label>Email<input type="email" v-model="form.email" readonly /></label
      ><label
        >Phone<input type="tel" v-model="form.phone" maxlength="30"
      /></label>
      <p v-if="saved" class="success">Profile saved.</p>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="button" :disabled="busy">
        {{ busy ? "Saving..." : "Save changes" }}
      </button>
    </form>
  </section>
</template>
