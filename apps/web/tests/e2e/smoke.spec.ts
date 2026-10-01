import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("real API readiness, keyboard access and accessibility", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Engenharia guiada",
  );
  await expect(page.getByRole("status")).toContainText("Operacional");
  await expect(page.getByRole("status")).toContainText("Pronto");
  await page.getByRole("button", { name: "Atualizar status" }).focus();
  await expect(
    page.getByRole("button", { name: "Atualizar status" }),
  ).toBeFocused();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
});
test("API unreachable shows a recoverable error", async ({ page }) => {
  await page.route("**/api/status", (route) => route.abort());
  await page.goto("/");
  await expect(page.getByRole("status")).toContainText(
    "Não foi possível conectar",
  );
  await page.unroute("**/api/status");
  await page.getByRole("button", { name: "Atualizar status" }).click();
  await expect(page.getByRole("status")).toContainText("Operacional");
});
