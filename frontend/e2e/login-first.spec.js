import { test, expect } from "@playwright/test";

test("guests start at role login and app links require sign-in", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login\?next=/);
  await expect(
    page.getByRole("heading", { name: "Log in to RoomFinder." }),
  ).toBeVisible();
  for (const role of ["Customer", "Hotel owner", "Administrator"])
    await expect(
      page.getByRole("radio", { name: role, exact: true }),
    ).toBeVisible();
  await page.screenshot({
    path: "../.local/screenshots/login-roles-desktop.png",
    fullPage: true,
  });
  await page.goto("/manage");
  await expect(page).toHaveURL(/\/login\?next=/);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("radio", { name: "Administrator", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "../.local/screenshots/login-roles-mobile.png",
    fullPage: true,
  });
  await page.goto("/register");
  await expect(
    page.getByRole("button", { name: "Create account", exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("radio")).toHaveCount(2);
});

for (const [label, username, target] of [
  ["Customer", "traveler", "/"],
  ["Hotel owner", "hotelowner", "/dashboard"],
  ["Administrator", "administrator", "/dashboard"],
]) {
  test(`${label} login opens the correct landing page and sign-out returns to login`, async ({
    page,
  }) => {
    await page.goto("/");
    await page.getByRole("radio", { name: label, exact: true }).check();
    await page.getByLabel("Username", { exact: true }).fill(username);
    await page.getByLabel("Password", { exact: true }).fill("RoomFinder!2026");
    await page.getByRole("button", { name: "Log in", exact: true }).click();
    await expect(page).toHaveURL(
      new RegExp(target === "/" ? "5173/$" : "/dashboard$"),
    );
    await expect(
      page.locator(target === "/" ? ".hotel-grid" : ".stats-grid"),
    ).toBeVisible();
    await page.getByRole("button", { name: "Sign out", exact: true }).click();
    await expect(page).toHaveURL(/\/login$/);
    expect(
      await page.evaluate(() => sessionStorage.getItem("rf_access")),
    ).toBeNull();
  });
}

test("wrong role is rejected without signing in", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("radio", { name: "Administrator", exact: true }).check();
  await page.getByLabel("Username", { exact: true }).fill("traveler");
  await page.getByLabel("Password", { exact: true }).fill("RoomFinder!2026");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    "selected role does not match",
  );
  expect(
    await page.evaluate(() => sessionStorage.getItem("rf_access")),
  ).toBeNull();
  await page.getByRole("radio", { name: "Customer", exact: true }).check();
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(page).toHaveURL(/5173\/$/);
});

test("customer is redirected safely after requesting an owner-only page", async ({
  page,
}) => {
  await page.goto("/manage");
  await page.getByLabel("Username", { exact: true }).fill("traveler");
  await page.getByLabel("Password", { exact: true }).fill("RoomFinder!2026");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(page).toHaveURL(/5173\/$/);
  await expect(page.locator(".hotel-grid")).toBeVisible();
});
