import { test, expect } from "@playwright/test";
import fs from "node:fs";
let temporaryHotel = null;
test.afterEach(async ({ page }) => {
  if (!temporaryHotel) return;
  const response = await page.request.post("/api/v1/auth/token/", {
    data: { username: "administrator", password: "RoomFinder!2026" },
  });
  const { access } = await response.json();
  const headers = { Authorization: `Bearer ${access}` };
  for (const type of ["rooms", "floors"]) {
    const response = await page.request.get(
      `/api/v1/${type}/?hotel=${temporaryHotel}`,
      { headers },
    );
    for (const record of await response.json())
      await page.request.delete(`/api/v1/${type}/${record.id}/`, { headers });
  }
  await page.request.delete(`/api/v1/hotels/${temporaryHotel}/`, { headers });
  temporaryHotel = null;
});
const output = "../.local/screenshots";
fs.mkdirSync(output, { recursive: true });
async function login(page, username) {
  await page.goto("/login");
  const role =
    username === "hotelowner"
      ? "Hotel owner"
      : username === "administrator"
        ? "Administrator"
        : "Customer";
  await page.getByRole("radio", { name: role, exact: true }).check();
  await page.getByLabel("Username", { exact: true }).fill(username);
  await page.getByLabel("Password", { exact: true }).fill("RoomFinder!2026");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
  await page.waitForURL((url) => !url.pathname.includes("/login"), {
    timeout: 20000,
  });
}
function dateIn(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
test("discover, filter, compare, mobile, and map", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await login(page, "traveler");
  await page.goto("/");
  await expect(page.locator(".hotel-card")).toHaveCount(4);
  await page.locator(".hotel-card img").first().waitFor();
  await expect
    .poll(() =>
      page
        .locator(".hotel-card img")
        .evaluateAll((images) =>
          images.every((i) => i.complete && i.naturalWidth > 0),
        ),
    )
    .toBeTruthy();
  await page.screenshot({ path: `${output}/home-desktop.png`, fullPage: true });
  await expect(
    page.getByRole("textbox", { name: "Destination", exact: true }),
  ).toHaveValue("Calapan City, Oriental Mindoro");
  await page
    .getByRole("button", { name: "Refine search", exact: true })
    .click();
  await page
    .getByLabel("Hotel or area in Calapan", { exact: true })
    .fill("The Verde House");
  await page
    .getByRole("button", { name: "Apply filters", exact: true })
    .click();
  await expect(page.locator(".hotel-card")).toHaveCount(1);
  await page.locator(".compare-button").click();
  await page.getByLabel("Hotel or area in Calapan", { exact: true }).fill("");
  await page
    .getByRole("button", { name: "Apply filters", exact: true })
    .click();
  await expect(page.locator(".hotel-card")).toHaveCount(4);
  await page.locator(".compare-button:not(.selected)").first().click();
  await page.getByRole("link", { name: "Compare stays" }).click();
  await expect(page.locator(".compare-grid article")).toHaveCount(2);
  await page.goto("/");
  await page.getByRole("button", { name: "Map", exact: true }).click();
  await expect(page.locator(".hotel-map-panel")).toBeVisible();
  await expect(page.locator(".hotel-price-pin")).toHaveCount(4);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator(".hotel-card")).toHaveCount(4);
  await page.screenshot({ path: `${output}/home-mobile.png`, fullPage: true });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});
test("customer chooses a room, confirms simulated payment, and cancels", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await login(page, "traveler");
  const list = await page.request.get("/api/v1/hotels/");
  const hotel = (await list.json()).find((h) => h.name === "The Verde House");
  await page.goto(
    `/hotels/${hotel.id}?check_in=${dateIn(20)}&check_out=${dateIn(22)}&guests=2`,
  );
  await expect(page.locator(".room-seat")).toHaveCount(12);
  await page.locator(".room-seat:not([disabled])").first().click();
  await expect(page.locator(".selected-room")).toBeVisible();
  await page.screenshot({
    path: `${output}/room-selection.png`,
    fullPage: true,
  });
  const responsePromise = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/v1/bookings/") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Reserve & simulate payment" })
    .click();
  const response = await responsePromise;
  expect(response.status()).toBe(201);
  const booking = await response.json();
  await expect(
    page.getByRole("heading", { name: "Your stay is confirmed." }),
  ).toBeVisible();
  await page.getByRole("link", { name: "View my reservation" }).click();
  const card = page
    .locator(".reservation-list>article")
    .filter({ hasText: booking.reference });
  await expect(card).toContainText("approved");
  await card.getByRole("button", { name: "Cancel reservation" }).click();
  await page.getByRole("button", { name: "Confirm cancellation" }).click();
  await expect(card).toContainText("cancelled");
  await expect(card).toContainText("refunded");
  await page.goto("/notifications");
  await expect(
    page
      .getByRole("heading", { name: "Reservation cancelled", exact: true })
      .first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Mark all read" }).click();
  await expect(page.locator(".notification.unread")).toHaveCount(0);
  expect(errors).toEqual([]);
});
test("owner creates layout and admin verifies the property", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const name = `Browser Test Stay ${Date.now()}`;
  await login(page, "hotelowner");
  await expect(page.locator(".stats-grid")).toBeVisible();
  await page.screenshot({
    path: `${output}/owner-dashboard.png`,
    fullPage: true,
  });
  await page.goto("/manage");
  await page.getByRole("button", { name: "Add property", exact: true }).click();
  await page.getByLabel("Property name", { exact: true }).fill(name);
  await expect(page.getByLabel("City", { exact: true })).toHaveValue(
    "Calapan City",
  );
  await expect(page.getByLabel("Province", { exact: true })).toHaveValue(
    "Oriental Mindoro",
  );
  await page
    .getByLabel("Street / barangay in Calapan", { exact: true })
    .fill("1 Browser Test Road");
  await page
    .getByLabel("Description", { exact: true })
    .fill(
      "A property created through the RoomFinder browser integration test.",
    );
  const hp = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/v1/hotels/") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Save property", exact: true })
    .click();
  const hr = await hp;
  expect(hr.status()).toBe(201);
  const hotel = await hr.json();
  temporaryHotel = hotel.id;
  await expect(page.locator(".modal")).toHaveCount(0);
  await page.getByRole("button", { name: "Add floor", exact: true }).click();
  await page.getByLabel("Floor name", { exact: true }).fill("Test Garden");
  const fp = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/v1/floors/") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Save floor", exact: true }).click();
  const fr = await fp;
  expect(fr.status()).toBe(201);
  const floor = await fr.json();
  await expect(page.locator(".modal")).toHaveCount(0);
  await page.getByRole("button", { name: "Add room", exact: true }).click();
  await page.getByLabel("Room number", { exact: true }).fill("T101");
  const rp = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/v1/rooms/") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Save room", exact: true }).click();
  const rr = await rp;
  expect(rr.status()).toBe(201);
  const room = await rr.json();
  await expect(page.locator(".owner-grid")).toContainText("T101");
  await page.getByRole("button", { name: "Promotions", exact: true }).click();
  await page
    .getByRole("button", { name: "New promotion", exact: true })
    .click();
  const code = `UITEST${Date.now()}`;
  await page.getByLabel("Code", { exact: true }).fill(code);
  await page
    .getByRole("button", { name: "Save promotion", exact: true })
    .click();
  await expect(page.locator(".promo-code")).toContainText(code);
  await page.getByRole("button", { name: "Photos", exact: true }).click();
  await page
    .getByLabel("Image (up to 5 MB)", { exact: true })
    .setInputFiles("../database/sample_images/verde.jpg");
  await page
    .getByLabel("Caption", { exact: true })
    .fill("Browser property photo");
  await page.getByRole("button", { name: "Upload photo", exact: true }).click();
  await expect(page.locator(".photo-grid img")).toHaveCount(1);
  await page
    .getByRole("combobox", { name: "Photo for", exact: true })
    .selectOption("room");
  await page
    .getByRole("combobox", { name: "Room", exact: true })
    .selectOption(String(room.id));
  await page
    .getByLabel("Image (up to 5 MB)", { exact: true })
    .setInputFiles("../database/sample_images/room.jpg");
  await page.getByLabel("Caption", { exact: true }).fill("Browser room photo");
  await page.getByRole("button", { name: "Upload photo", exact: true }).click();
  await expect(page.locator(".photo-grid img")).toHaveCount(2);

  await page.getByRole("button", { name: "Sign out" }).click();
  await login(page, "administrator");
  const verification = page
    .locator(".verification-row")
    .filter({ hasText: name });
  await expect(verification).toBeVisible();
  await verification
    .getByRole("button", { name: "Verify", exact: true })
    .click();
  await expect(verification).toHaveCount(0);
  await page.screenshot({
    path: `${output}/admin-dashboard.png`,
    fullPage: true,
  });
  const dp = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Export report", exact: true })
    .click();
  expect((await dp).suggestedFilename()).toBe("roomfinder-report.csv");
  const token = await page.evaluate(() => sessionStorage.getItem("rf_access"));
  const headers = { Authorization: `Bearer ${token}` };
  const verified = await page.request.get(`/api/v1/hotels/${hotel.id}/`);
  expect((await verified.json()).status).toBe("verified");
  for (const path of [
    `rooms/${room.id}/`,
    `floors/${floor.id}/`,
    `hotels/${hotel.id}/`,
  ]) {
    const response = await page.request.delete(`/api/v1/${path}`, { headers });
    expect(response.status()).toBe(204);
  }
  expect(errors).toEqual([]);
});
