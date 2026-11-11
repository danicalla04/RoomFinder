import { test, expect } from "@playwright/test";
async function login(page, role, username) {
  await page.goto("/login");
  await page.getByRole("radio", { name: role, exact: true }).check();
  await page.getByLabel("Username", { exact: true }).fill(username);
  await page.getByLabel("Password", { exact: true }).fill("RoomFinder!2026");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Sign out", exact: true }),
  ).toBeVisible();
}
function dateIn(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

test("room plan visibly separates date-specific booked and unavailable rooms", async ({
  page,
}) => {
  await login(page, "Customer", "traveler");
  const list = await page.request.get("/api/v1/hotels/");
  const hotel = (await list.json()).find((h) => h.name === "The Verde House");
  await page.goto(
    `/hotels/${hotel.id}?check_in=${dateIn(0)}&check_out=${dateIn(1)}&guests=2`,
  );
  const booked = page.locator('.room-seat[data-state="booked"]'),
    unavailable = page.locator('.room-seat[data-state="unavailable"]');
  await expect(booked.first()).toBeVisible();
  await expect(booked.first()).toBeDisabled();
  await expect(booked.first()).toContainText("Booked");
  await expect(unavailable.first()).toBeVisible();
  await expect(unavailable.first()).toBeDisabled();
  await expect(unavailable.first()).toContainText("Unavailable");
  await expect(
    page.locator('.room-seat[data-state="available"]').first(),
  ).toBeEnabled();
  expect(
    await booked.first().evaluate((e) => getComputedStyle(e).backgroundColor),
  ).not.toBe(
    await page
      .locator('.room-seat[data-state="available"]')
      .first()
      .evaluate((e) => getComputedStyle(e).backgroundColor),
  );
  await expect(page.locator(".classification-note")).toContainText(
    "not official accreditation",
  );
  await page.screenshot({
    path: "../.local/screenshots/room-statuses.png",
    fullPage: true,
  });
  await page.getByLabel("Check in", { exact: true }).fill(dateIn(10));
  await page.getByLabel("Check out", { exact: true }).fill(dateIn(11));
  await expect(
    page.getByText(
      "Dates changed. Check availability to refresh the room plan.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(page.locator(".room-seat").first()).toBeDisabled();
  await page
    .getByRole("button", { name: "Check availability", exact: true })
    .click();
  await expect(page.getByRole("button", { name: /^Room 103,/ })).toBeEnabled();
  await expect(page.getByRole("button", { name: /^Room 112,/ })).toBeDisabled();
});

test("owner chart has demo activity and room deletion is visible at a narrow width", async ({
  page,
}) => {
  await login(page, "Hotel owner", "hotelowner");
  await page.goto("/dashboard");
  await expect(page.locator(".demo-activity-note")).toBeVisible();
  const token = await page.evaluate(() => sessionStorage.getItem("rf_access"));
  const headers = { Authorization: `Bearer ${token}` };
  const report = await (
    await page.request.get("/api/v1/reports/summary/", { headers })
  ).json();
  expect(report.demo_booking_count).toBeGreaterThan(0);
  expect(
    report.trend.every((d) => Number(d.revenue) > 0 && d.bookings > 0),
  ).toBeTruthy();
  await expect(
    page.getByLabel("Revenue and reservations over the last seven days"),
  ).toBeVisible();
  await page.screenshot({
    path: "../.local/screenshots/active-owner-chart.png",
    fullPage: true,
  });
  const hotels = await (
    await page.request.get("/api/v1/hotels/?mine=true", { headers })
  ).json();
  const hotel = hotels.find((h) => h.name === "The Verde House");
  const floors = await (
    await page.request.get(`/api/v1/floors/?hotel=${hotel.id}`, { headers })
  ).json();
  const floor = floors[0];
  const rooms = await (
    await page.request.get(`/api/v1/rooms/?floor=${floor.id}`, { headers })
  ).json();
  const used = new Set(rooms.map((r) => `${r.row},${r.column}`));
  let position;
  for (let row = 0; row <= 30 && !position; row++)
    for (let column = 0; column < floor.columns && !position; column++)
      if (!used.has(`${row},${column}`)) position = { row, column };
  const number = `DEL${Date.now().toString().slice(-7)}`;
  const response = await page.request.post("/api/v1/rooms/", {
    headers,
    data: { floor: floor.id, number, price: 1500, capacity: 2, ...position },
  });
  expect(response.status()).toBe(201);
  const room = await response.json();
  try {
    await page.setViewportSize({ width: 760, height: 900 });
    await page.goto("/manage");
    await page
      .getByRole("combobox", { name: "PROPERTY", exact: true })
      .selectOption(String(hotel.id));
    const card = page
      .locator(".owner-room-item")
      .filter({
        has: page.getByRole("heading", { name: `Room ${number}`, exact: true }),
      });
    await card.scrollIntoViewIfNeeded();
    await expect(
      card.getByRole("button", { name: `Delete room ${number}`, exact: true }),
    ).toBeEnabled();
    await card
      .getByRole("button", { name: "Make unavailable", exact: true })
      .click();
    await expect(card.locator(".room-status-badge")).toHaveText("Unavailable");
    await card
      .getByRole("button", { name: "Make available", exact: true })
      .click();
    await expect(card.locator(".room-status-badge")).toHaveText("Available");
    await page.screenshot({
      path: "../.local/screenshots/owner-room-actions.png",
      fullPage: true,
    });
    await card.getByRole("button", { name: "Edit room", exact: true }).click();
    await expect(
      page
        .locator(".modal")
        .getByRole("button", { name: `Delete room ${number}`, exact: true }),
    ).toBeVisible();
    await page
      .locator(".modal")
      .getByRole("button", { name: `Delete room ${number}`, exact: true })
      .click();
    await page
      .getByRole("button", { name: "Confirm delete room", exact: true })
      .click();
    await expect(card).toHaveCount(0);
  } finally {
    const result = await page.request.delete(`/api/v1/rooms/${room.id}/`, {
      headers,
    });
    expect([204, 404]).toContain(result.status());
  }
});

test("modern vector map loads streets, price pins, and Google Maps links", async ({
  page,
}) => {
  await login(page, "Customer", "traveler");
  await page.goto("/");
  await page.getByRole("button", { name: "Map", exact: true }).click();
  const panel = page.locator(".hotel-map-panel");
  await expect(panel).toHaveAttribute("data-renderer", "vector", {
    timeout: 15000,
  });
  await expect(panel).toHaveAttribute("data-map-status", "ready", {
    timeout: 45000,
  });
  await expect(page.locator(".maplibregl-canvas")).toBeVisible();
  await expect(page.locator(".hotel-price-pin")).toHaveCount(4);
  await page.locator(".hotel-price-pin").first().click();
  await expect(
    page
      .locator(".map-hotel-popup")
      .getByRole("link", { name: "View rooms", exact: true }),
  ).toBeVisible();
  await expect(
    page
      .locator(".map-hotel-popup")
      .getByRole("link", { name: "Google Maps", exact: true }),
  ).toHaveAttribute("href", /google.com\/maps\/search/);
  await page.getByRole("button", { name: "Light", exact: true }).click();
  await expect(panel).toHaveAttribute("data-map-status", "ready", {
    timeout: 30000,
  });
  await page.getByRole("button", { name: "Streets", exact: true }).click();
  await expect(panel).toHaveAttribute("data-map-status", "ready", {
    timeout: 30000,
  });
  await page.screenshot({
    path: "../.local/screenshots/modern-calapan-map.png",
    fullPage: true,
  });
});

test("map tile failure offers a usable basic-map fallback", async ({
  page,
}) => {
  await page.route("https://tiles.openfreemap.org/**", (route) =>
    route.abort(),
  );
  await login(page, "Customer", "traveler");
  await page.goto("/");
  await page.getByRole("button", { name: "Map", exact: true }).click();
  await expect(page.locator(".map-load-error")).toBeVisible({ timeout: 20000 });
  await page
    .getByRole("button", { name: "Use basic map", exact: true })
    .click();
  await expect(page.locator(".hotel-map-panel")).toHaveAttribute(
    "data-renderer",
    "basic",
  );
  await expect(page.locator(".leaflet-container")).toBeVisible();
  await expect(page.locator(".hotel-price-pin")).toHaveCount(4);
});
