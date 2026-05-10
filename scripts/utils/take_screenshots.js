const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const BASE = process.argv[2] || "http://localhost:3456";
const OUT_DIR = path.join(__dirname, "..", "docs", "screenshots");

const SCREENSHOTS = [
  // Public pages (redirect to login is fine for demo)
  { name: "home", path: "/", desc: "Landing / Login" },
  { name: "login", path: "/en/auth/login", desc: "Login form" },
  { name: "register", path: "/en/auth/register", desc: "Registration" },
  // After login, these would be the main features:
  { name: "search", path: "/en/search", desc: "Property search" },
  { name: "chat", path: "/en/chat", desc: "AI chat" },
  { name: "analytics", path: "/en/analytics", desc: "Analytics tools" },
  { name: "agents", path: "/en/agents", desc: "Agent directory" },
  { name: "market-trends", path: "/en/market-trends", desc: "Market trends" },
  { name: "cma", path: "/en/cma", desc: "CMA tool" },
  { name: "city-overview", path: "/en/city-overview", desc: "City overview" },
];

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    locale: "en-US",
  });
  const page = await context.newPage();

  for (const shot of SCREENSHOTS) {
    const url = `${BASE}${shot.path}`;
    console.log(`Capturing ${shot.name} (${shot.desc})...`);
    try {
      await page.goto(url, { waitUntil: "networkidle", timeout: 15000 });
      await page.waitForTimeout(1500);

      // Dismiss any cookie banners
      try {
        const btn = page.locator("button:has-text('Accept'), button:has-text('Close')");
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

  await browser.close();
  console.log("\nDone! Screenshots saved to docs/screenshots/");
}

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});
