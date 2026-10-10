import { chromium } from "@playwright/test";
import { writeFile } from "node:fs/promises";
import assert from "node:assert/strict";

const base = "http://127.0.0.1:4173";
const browser = await chromium.launch({ channel: "msedge" });
try {
  const page = await browser.newPage({
    viewport: { width: 1920, height: 1080 },
  });
  const errors = [],
    externalRequests = [],
    failures = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => {
    if (new URL(r.url()).origin !== base) externalRequests.push(r.url());
  });
  page.on("response", (r) => {
    if (r.status() >= 400) failures.push(`${r.status()} ${r.url()}`);
  });
  await page.goto(base, { waitUntil: "networkidle" });
  assert.equal(await page.locator(".shot-card").count(), 3);
  await page.getByRole("button", { name: "角色资产", exact: true }).click();
  assert.equal(await page.locator(".asset-card").count(), 2);
  await page.getByRole("button", { name: "分镜工作区", exact: true }).click();
  await page.screenshot({ path: "docs/screenshots/production-1920.png" });
  assert.deepEqual(errors, []);
  assert.deepEqual(externalRequests, []);
  assert.deepEqual(failures, []);
  const report = {
    date: new Date().toISOString(),
    browser: browser.version(),
    builtApp: base,
    shotCount: 3,
    assetCount: 2,
    pageErrors: errors,
    externalRequests,
    failedResponses: failures,
    result: "passed",
  };
  await writeFile(
    "docs/production-validation.json",
    JSON.stringify(report, null, 2),
  );
  console.log(JSON.stringify(report, null, 2));
} finally {
  await browser.close();
}
