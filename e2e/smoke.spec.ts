import { test, expect } from "@playwright/test";

test.describe("DMV App — core journey smoke test", () => {
  test("home page loads and shows heading", async ({ page }) => {
    await page.goto("http://localhost:5173/");
    await expect(page.getByRole("heading", { name: /prepare for your dmv visit/i })).toBeVisible();
  });

  test("disclaimer banner is visible", async ({ page }) => {
    await page.goto("http://localhost:5173/");
    await expect(page.getByRole("status")).toContainText("Educational prototype");
  });

  test("login page shows form", async ({ page }) => {
    await page.goto("http://localhost:5173/login");
    await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
  });

  test("register page shows form", async ({ page }) => {
    await page.goto("http://localhost:5173/register");
    await expect(page.getByRole("heading", { name: /create account/i })).toBeVisible();
  });
});
