import { test, expect } from "@playwright/test";

test("administrator can open users, property, floor, and room", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/login");
  await page.getByRole("radio", { name: "Administrator", exact: true }).check();
  await page.getByLabel("Username", { exact: true }).fill("administrator");
  await page.getByLabel("Password", { exact: true }).fill("RoomFinder!2026");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await page.getByRole("link", { name: "Users", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Hotel owners \(\d+\)/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Users \(\d+\)/ })).toBeVisible();
  await page.getByRole("link", { name: /^Open / }).first().click();
  await expect(page.getByRole("heading", { name: /Places and floors/ })).toBeVisible();
  await page.getByRole("button", { name: /View rooms/ }).first().click();
  await expect(page.getByRole("button", { name: /View room/ }).first()).toBeVisible();
  await page.getByRole("button", { name: /View room/ }).first().click();
  await expect(page.getByRole("heading", { name: /^Room \S+$/ })).toBeVisible();
  await expect(page.getByText("Price per night")).toBeVisible();
  expect(errors).toEqual([]);
});
