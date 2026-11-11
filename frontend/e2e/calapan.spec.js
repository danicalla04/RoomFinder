import { test, expect } from "@playwright/test";
async function login(page, label, username) {
  await page.goto("/login");
  await page.getByRole("radio", { name: label, exact: true }).check();
  await page.getByLabel("Username", { exact: true }).fill(username);
  await page.getByLabel("Password", { exact: true }).fill("RoomFinder!2026");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Sign out", exact: true }),
  ).toBeVisible();
}

test("customer destination and all displayed places are fixed to Calapan", async ({
  page,
}) => {
  await login(page, "Customer", "traveler");
  await page.goto("/");
  const destination = page.getByRole("textbox", {
    name: "Destination",
    exact: true,
  });
  await expect(destination).toHaveValue("Calapan City, Oriental Mindoro");
  await expect(destination).toHaveJSProperty("readOnly", true);
  await expect(
    page.getByRole("button", { name: "Calapan City", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", {
      name: /^(Tagaytay|Batangas|Manila|Los Banos)$/,
    }),
  ).toHaveCount(0);
  await expect(page.locator(".hotel-card")).toHaveCount(4);
  await expect
    .poll(() =>
      page
        .locator(".hotel-card img")
        .evaluateAll((images) =>
          images.every((i) => i.complete && i.naturalWidth > 0),
        ),
    )
    .toBeTruthy();
  for (const card of await page.locator(".hotel-card").all())
    await expect(card.locator(".card-meta")).toContainText("Calapan City");
  await page.screenshot({
    path: "../.local/screenshots/calapan-discovery-desktop.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Explore Calapan map", exact: true })
    .click();
  await expect(
    page.getByLabel("Calapan City hotel locations map"),
  ).toBeVisible();
  await expect(page.locator(".hotel-price-pin")).toHaveCount(4);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(destination).toHaveValue("Calapan City, Oriental Mindoro");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "../.local/screenshots/calapan-discovery-mobile.png",
    fullPage: true,
  });
});

for (const [label, username] of [
  ["Hotel owner", "hotelowner"],
  ["Administrator", "administrator"],
]) {
  test(`${label} forms and reports stay inside Calapan`, async ({ page }) => {
    await login(page, label, username);
    await page.goto("/dashboard");
    await expect(page.locator(".lead")).toContainText(
      "Calapan City, Oriental Mindoro",
    );
    await page.goto("/manage");
    await page
      .getByRole("button", { name: "Add property", exact: true })
      .click();
    const city = page.getByLabel("City", { exact: true }),
      province = page.getByLabel("Province", { exact: true });
    await expect(city).toHaveValue("Calapan City");
    await expect(city).toHaveJSProperty("readOnly", true);
    await expect(province).toHaveValue("Oriental Mindoro");
    await expect(province).toHaveJSProperty("readOnly", true);
    await expect(page.getByLabel("Latitude", { exact: true })).toHaveValue(
      "13.4",
    );
    await page.screenshot({
      path: `../.local/screenshots/calapan-${username}-form.png`,
      fullPage: true,
    });
    const token = await page.evaluate(() =>
      sessionStorage.getItem("rf_access"),
    );
    const headers = { Authorization: `Bearer ${token}` };
    const response = await page.request.post("/api/v1/hotels/", {
      headers,
      data: {
        name: "Outside city should fail",
        city: "Manila",
        description: "Test scope validation.",
        address: "Test Street",
        latitude: 14.6,
        longitude: 121,
      },
    });
    expect(response.status()).toBe(400);
    expect(await response.json()).toHaveProperty("city");
    const report = await page.request.get("/api/v1/reports/summary/", {
      headers,
    });
    expect((await report.json()).location).toBe(
      "Calapan City, Oriental Mindoro",
    );
  });
}
