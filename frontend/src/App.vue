<script setup>
import { computed, watch, onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";
import {
  BedDouble,
  ArrowUpRight,
  Bell,
  UserRound,
  ArrowRight,
  Menu,
  X,
  MessageCircle,
} from "lucide-vue-next";
import { useAuth } from "./stores/auth";
import { useCompare } from "./stores/compare";
import { useNotifications } from "./stores/notifications";
import { useMessages } from "./stores/messages";
import { ref } from "vue";
const auth = useAuth(),
  compare = useCompare(),
  notifications = useNotifications(),
  messages = useMessages(),
  router = useRouter(),
  open = ref(false);
const staff = computed(() => auth.user && auth.user.role !== "customer");
const homePath = computed(() => staff.value ? "/dashboard" : "/");
watch(() => auth.user?.id, (id) => {
  if (id) { notifications.start(); messages.start(); }
  else { notifications.stop(); messages.stop(); }
}, { immediate: true });
onBeforeUnmount(() => { notifications.stop(); messages.stop(); });
function logout() {
  auth.logout();
  router.push("/login");
  open.value = false;
}
</script>
<template>
  <header class="header">
    <RouterLink :to="homePath" class="brand"
      ><span class="brand-icon"><BedDouble :size="23" /></span>roomfinder<span
        class="brand-dot"
        >.</span
      ></RouterLink
    ><button
      v-if="auth.user"
      class="mobile-menu icon-button"
      aria-label="Toggle navigation"
      @click="open = !open"
    >
      <Menu />
    </button>
    <nav v-if="auth.user" :class="{ open }">
      <RouterLink v-if="auth.user.role === 'customer'" to="/" @click="open = false">Find a stay</RouterLink
      ><RouterLink
        v-if="auth.user?.role === 'customer'"
        to="/bookings"
        @click="open = false"
        >My bookings</RouterLink
      ><RouterLink v-if="staff" to="/dashboard" @click="open = false"
        >Dashboard</RouterLink
      ><RouterLink v-if="auth.user.role === 'admin'" to="/admin/users" @click="open = false"
        >Users</RouterLink
      ><RouterLink v-if="auth.user.role === 'owner'" to="/manage" @click="open = false"
        >Manage properties</RouterLink
      ><RouterLink
        v-if="!auth.user"
        to="/register?role=owner"
        @click="open = false"
        >List your property <ArrowUpRight :size="14"
      /></RouterLink>
    </nav>
    <div class="header-actions">
      <template v-if="auth.user"
        ><RouterLink
          to="/notifications"
          class="icon-button notification-link"
          :aria-label="notifications.unreadCount ? `Notifications, ${notifications.unreadCount} unread` : 'Notifications'"
          ><Bell :size="20" /><span v-if="notifications.unreadCount" class="notification-count">{{ notifications.unreadCount > 99 ? '99+' : notifications.unreadCount }}</span></RouterLink
        ><RouterLink
          v-if="auth.user.role !== 'admin'"
          to="/messages"
          class="icon-button notification-link"
          :aria-label="messages.unreadCount ? `Messages, ${messages.unreadCount} unread` : 'Messages'"
          ><MessageCircle :size="20" /><span v-if="messages.unreadCount" class="notification-count">{{ messages.unreadCount > 99 ? '99+' : messages.unreadCount }}</span></RouterLink
        ><RouterLink to="/profile" class="profile-link"
          ><UserRound :size="17" /><span>{{
            auth.user.first_name || auth.user.username
          }}</span></RouterLink
        ><button class="text-button" @click="logout">Sign out</button></template
      ><template v-else
        ><RouterLink to="/login" class="text-button">Log in</RouterLink
        ><RouterLink to="/register" class="button small"
          >Get started <ArrowUpRight :size="16" /></RouterLink
      ></template>
    </div>
  </header>
  <main><RouterView /></main>
  <aside v-if="auth.user && compare.ids.length" class="compare-tray">
    <span>{{ compare.ids.length }} of 3 stays selected</span
    ><RouterLink to="/compare"
      >Compare stays <ArrowRight :size="17" /></RouterLink
    ><button
      aria-label="Clear comparison"
      @click="compare.ids.slice().forEach(compare.toggle)"
    >
      <X :size="16" />
    </button>
  </aside>
  <footer>
    <RouterLink :to="homePath" class="brand"
      ><BedDouble :size="22" />roomfinder.</RouterLink
    >
    <p>A little less searching. A little more staying.</p>
    <span>Made for your next chapter · Calapan City, Oriental Mindoro</span>
  </footer>
</template>
