// Regenerate the 5 byte-identical dark-theme placeholder files in
// assets/screenshots/ (md5 159c54ac...) by capturing them with the
// running Docker demo (NEXT_PUBLIC_DEMO_MODE=true). Reads from the
// SCREENSHOTS array used by take_screenshots.js but writes to
// assets/screenshots/ with the same names.
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const BASE = process.argv[2] || "http://localhost:3082";
const OUT_DIR = path.join(__dirname, "..", "..", "assets", "screenshots");

// The 5 placeholder routes (same routes as their light counterparts
// in docs/screenshots/, but with -dark suffix in the filename).
const SCREENSHOTS = [
  { name: "agents-dark", path: "/en/agents" },
  { name: "city-overview-dark", path: "/en/city-overview" },
  { name: "documents-dark", path: "/en/documents" },
  { name: "favorites-dark", path: "/en/favorites" },
  { name: "settings-dark", path: "/en/settings" },
];

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    locale: "en-US",
    colorScheme: "dark",
  });
  // Apply dark theme before any page renders
  await context.addInitScript(() => {
    localStorage.setItem("theme", "dark");
    document.documentElement.classList.add("dark");
  });
  const page = await context.newPage();

  for (const shot of SCREENSHOTS) {
    const url = `${BASE}${shot.path}`;
    console.log(`Capturing ${shot.name}...`);
    try {
      await page.goto(url, { waitUntil: "load", timeout: 30000 });
      // City-overview fires 5+ parallel search queries; give them time.
      const wait = shot.name === "city-overview-dark" ? 12000 : 5000;
      await page.waitForTimeout(wait);

      const btn = page.locator("button:has-text('Accept'), button:has-text('Close')");
      try {
        if (await btn.isVisible({ timeout: 1000 })) await btn.click();
      } catch {}

      const outPath = path.join(OUT_DIR, `${shot.name}.png`);
      await page.screenshot({ path: outPath, fullPage: false });
      const size = fs.statSync(outPath).size;
      console.log(`  Saved: ${outPath} (${(size / 1024).toFixed(1)} KB)`);
    } catch (err) {
      console.error(`  Failed: ${err.message}`);
    }
  }

  await context.close();
  await browser.close();
  console.log("\nDone! Dark-theme placeholders regenerated.");
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});