<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from "vue";
import { Chart, registerables } from "chart.js";
import { api, errorMessage, money } from "../services/api";
import { LOCATION_LABEL } from "../services/location";
import { useAuth } from "../stores/auth";
import {
  Building2,
  BedDouble,
  CalendarDays,
  TrendingUp,
  Download,
  ArrowUpRight,
  Check,
  X,
} from "lucide-vue-next";
Chart.register(...registerables);
const auth = useAuth(),
  report = ref(null),
  bookings = ref([]),
  pending = ref([]),
  error = ref(""),
  loading = ref(true),
  canvas = ref(),
  busy = ref(false),
  note = ref("");
let chart;
async function load() {
  try {
    const [r, b] = await Promise.all([
      api.get("reports/summary/"),
      api.get("bookings/"),
    ]);
    report.value = r.data;
    bookings.value = b.data;
    if (auth.user.role === "admin")
      pending.value = (
        await api.get("hotels/", { params: { status: "pending" } })
      ).data;
    await nextTick();
    chart?.destroy();
    if (canvas.value)
      chart = new Chart(canvas.value, {
        type: "bar",
        data: {
          labels: r.data.trend.map((d) => d.date.slice(5)),
          datasets: [
            {
              label: "Simulated revenue (PHP)",
              data: r.data.trend.map((d) => Number(d.revenue)),
              backgroundColor: "#1f5c4d",
              borderRadius: 5,
              yAxisID: "y",
            },
            {
              type: "line",
              label: "Reservations",
              data: r.data.trend.map((d) => d.bookings),
              borderColor: "#c67145",
              backgroundColor: "#c67145",
              borderWidth: 2,
              pointRadius: 4,
              tension: 0.3,
              yAxisID: "bookings",
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: true,
              labels: { boxWidth: 10, font: { size: 10 } },
            },
          },
          scales: {
            x: { grid: { display: false } },
            y: { beginAtZero: true, grid: { color: "#eeede7" } },
            bookings: {
              position: "right",
              beginAtZero: true,
              ticks: { precision: 0 },
              grid: { drawOnChartArea: false },
            },
          },
        },
      });
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
async function verify(h, status) {
  busy.value = true;
  error.value = "";
  try {
    await api.post(`hotels/${h.id}/verify/`, { status, note: note.value });
    note.value = "";
    await load();
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    busy.value = false;
  }
}
async function download() {
  try {
    const { data } = await api.get("reports/summary/", {
      params: { format: "csv" },
      responseType: "blob",
    });
    const u = URL.createObjectURL(data),
      a = document.createElement("a");
    a.href = u;
    a.download = "roomfinder-report.csv";
    a.click();
    URL.revokeObjectURL(u);
  } catch (e) {
    error.value = errorMessage(e);
  }
}
onMounted(load);
onBeforeUnmount(() => chart?.destroy());
</script>
<template>
  <section class="section page">
    <span class="eyebrow">{{
      auth.user.role === "admin"
        ? "THE BIG PICTURE"
        : "YOUR PROPERTY, AT A GLANCE"
    }}</span>
    <div class="section-heading">
      <div>
        <h1>
          Welcome back, {{ auth.user.first_name || auth.user.username
          }}<span>.</span>
        </h1>
        <p class="lead">
          {{ LOCATION_LABEL }} properties, reservations, and reports.
        </p>
      </div>
      <button class="button small" @click="download">
        <Download :size="16" />Export report
      </button>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="loading">Gathering your latest numbers...</p>
    <template v-if="report"
      ><div class="stats-grid">
        <article>
          <Building2 :size="21" /><span>Properties</span
          ><strong>{{ report.hotel_count }}</strong
          ><small>{{ report.pending_hotels }} awaiting verification</small>
        </article>
        <article>
          <BedDouble :size="21" /><span>Active rooms</span
          ><strong>{{ report.room_count }}</strong
          ><small>{{ report.occupancy }}% occupied today</small>
        </article>
        <article>
          <CalendarDays :size="21" /><span>Reservations</span
          ><strong>{{ report.booking_count }}</strong
          ><small>{{ report.confirmed_count }} confirmed</small>
        </article>
        <article>
          <TrendingUp :size="21" /><span>Simulated revenue</span
          ><strong>{{ money(report.revenue) }}</strong
          ><small>Confirmed reservations · all time</small>
        </article>
      </div>
      <div class="dashboard-grid">
        <article class="panel">
          <div class="section-heading">
            <h3>A week in perspective</h3>
            <span class="muted">Simulated revenue</span>
          </div>
          <div class="chart-wrap">
            <canvas
              ref="canvas"
              aria-label="Revenue and reservations over the last seven days"
            ></canvas>
          </div>
        </article>
        <article class="panel">
          <span class="eyebrow">THE PLACES PEOPLE PICK</span>
          <h3>Top properties</h3>
          <div v-for="(h, i) in report.top_hotels" class="top-hotel">
            <span>0{{ i + 1 }}</span>
            <div>
              <strong>{{ h.room__floor__hotel__name }}</strong
              ><small>{{ h.bookings }} reservations</small>
            </div>
            <strong>{{ money(h.revenue) }}</strong>
          </div>
          <p v-if="!report.top_hotels.length" class="muted">
            Your first reservation will appear here.
          </p>
          <RouterLink v-if="auth.user.role === 'owner'" to="/manage" class="text-button"
            >Manage properties <ArrowUpRight :size="16"
          /></RouterLink>
        </article></div
    ></template>
    <article v-if="auth.user.role === 'admin'" class="panel verification">
      <span class="eyebrow">QUALITY STARTS HERE</span>
      <h2>Calapan property verification</h2>
      <p class="muted">
        Verify that the address and map location are in {{ LOCATION_LABEL }}.
      </p>
      <label v-if="pending.length"
        >Verification note (included in owner notification)<input
          v-model="note"
          placeholder="Review notes or reason for rejection"
          maxlength="2000"
      /></label>
      <div v-for="h in pending" class="verification-row">
        <div>
          <h3>{{ h.name }}</h3>
          <p>{{ h.city }} · {{ h.address }} · Owner: {{ h.owner_name }}</p>
          <small>{{ h.description }}</small>
        </div>
        <RouterLink :to="`/hotels/${h.id}`" class="text-button"
          >Inspect</RouterLink
        ><button
          class="button small"
          :disabled="busy"
          @click="verify(h, 'verified')"
        >
          <Check :size="15" />Verify</button
        ><button
          class="button secondary small"
          :disabled="busy"
          @click="verify(h, 'rejected')"
        >
          <X :size="15" />Reject
        </button>
      </div>
      <p v-if="!pending.length" class="muted">
        All caught up. No properties awaiting verification.
      </p>
    </article>
    <article class="panel">
      <div class="section-heading">
        <h2>Reservation activity</h2>
        <span class="muted">{{ bookings.length }} total</span>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Guest</th>
              <th>Property / room</th>
              <th>Dates</th>
              <th>Status</th>
              <th>Payment</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="b in bookings">
              <td>
                {{ b.customer_display_name || b.customer_name
                }}<small v-if="b.is_demo" class="demo-label">Demo guest</small>
              </td>
              <td>
                {{ b.hotel_name }}<small>Room {{ b.room_number }}</small>
              </td>
              <td>
                {{ b.check_in }}<small>to {{ b.check_out }}</small>
              </td>
              <td>
                <span class="badge" :class="b.status">{{ b.status }}</span>
              </td>
              <td>{{ b.payment?.status }}<small>Simulation</small></td>
              <td>{{ money(b.total) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!bookings.length" class="empty">No reservations yet.</p>
    </article>
  </section>
</template>
