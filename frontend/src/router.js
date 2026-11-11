import { createRouter, createWebHistory } from "vue-router";
import { useAuth } from "./stores/auth";
import Search from "./pages/Search.vue";
const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: "/", component: Search },
    { path: "/hotels/:id", component: () => import("./pages/Hotel.vue") },
    { path: "/compare", component: () => import("./pages/Compare.vue") },
    { path: "/login", component: () => import("./pages/Auth.vue") },
    { path: "/register", component: () => import("./pages/Auth.vue") },
    { path: "/verify-email", component: () => import("./pages/VerifyEmail.vue") },
    {
      path: "/bookings",
      component: () => import("./pages/Bookings.vue"),
      meta: { auth: true },
    },
    {
      path: "/notifications",
      component: () => import("./pages/Notifications.vue"),
      meta: { auth: true },
    },
    {
      path: "/profile",
      component: () => import("./pages/Profile.vue"),
      meta: { auth: true },
    },
    {
      path: "/dashboard",
      component: () => import("./pages/Dashboard.vue"),
      meta: { roles: ["owner", "admin"] },
    },
    {
      path: "/manage",
      component: () => import("./pages/Manage.vue"),
      meta: { roles: ["owner"] },
    },
    {
      path: "/admin/users",
      component: () => import("./pages/AdminUsers.vue"),
      meta: { roles: ["admin"] },
    },
    {
      path: "/admin/hotels/:id",
      component: () => import("./pages/AdminHotel.vue"),
      meta: { roles: ["admin"] },
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});
router.beforeEach(async (to) => {
  const auth = useAuth();
  if (!auth.ready) {
    try {
      await auth.load();
    } catch {
      auth.logout();
    }
  }
  const authPage = ["/login", "/register", "/verify-email"].includes(to.path);
  const home = auth.user?.role === "customer" ? "/" : "/dashboard";
  if (!auth.user && !authPage)
    return { path: "/login", query: { next: to.fullPath } };
  if (auth.user && authPage && to.path !== "/verify-email") return home;
  if (auth.user?.role !== "customer" && to.path === "/") return "/dashboard";
  if (to.meta.roles && !to.meta.roles.includes(auth.user.role)) return home;
});
export default router;
