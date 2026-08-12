#!/usr/bin/env node
/**
 * GOAL Step 9 — keyed identity: insert, remove, reorder with stable __koru_key.
 * Serves public/ locally and drives chromium via playwright-core (koru-libs closer dep).
 */
import http from "node:http";
import { createReadStream, promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, "..");
const PUBLIC = path.join(REPO, "public");
const require = createRequire(import.meta.url);

const PW_CANDIDATES = [
  path.join(__dirname, ".pw/node_modules/playwright-core"),
  "/mnt/w/src/koru-libs/dom/closer/node_modules/playwright-core",
  path.join(REPO, "node_modules/playwright-core"),
];

function loadPlaywright() {
  for (const c of PW_CANDIDATES) {
    try {
      return require(c);
    } catch {
      /* try next */
    }
  }
  try {
    return require("playwright-core");
  } catch {
    /* fall through */
  }
  throw new Error("playwright-core not found (use scripts/test_keyed_list.sh in Docker)");
}

const MIME = {
  ".html": "text/html",
  ".js": "text/javascript",
};

function startServer(root) {
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      const urlPath = decodeURIComponent(new URL(req.url, "http://x").pathname);
      let filePath = path.join(root, urlPath === "/" ? "enhance-demo.html" : urlPath);
      if (!filePath.startsWith(path.resolve(root))) {
        res.writeHead(403).end();
        return;
      }
      const stream = createReadStream(filePath);
      stream.on("error", () => res.writeHead(404).end("not found"));
      stream.on("open", () => {
        res.writeHead(200, {
          "content-type": MIME[path.extname(filePath)] ?? "application/octet-stream",
        });
        stream.pipe(res);
      });
    });
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => resolve(server));
  });
}

function titles(page) {
  return page.locator("#koru-list li .title").allTextContents();
}

function keys(page) {
  return page.evaluate(() =>
    [...document.querySelectorAll("#koru-list li")].map((li) => li.__koru_key)
  );
}

async function main() {
  const jsPath = path.join(PUBLIC, "koru-dom-enhance.js");
  const st = await fs.stat(jsPath);
  if (st.size < 1000) throw new Error("koru-dom-enhance.js missing or tiny — run build-browser.sh");

  const { chromium } = loadPlaywright();
  const server = await startServer(PUBLIC);
  const { port } = server.address();
  const url = `http://127.0.0.1:${port}/enhance-demo.html`;

  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.goto(url, { waitUntil: "load", timeout: 15000 });

    await page.click("#seed");
    await page.waitForFunction(() => document.querySelectorAll("#koru-list li").length === 3);
    const t1 = await titles(page);
    const k1 = await keys(page);
    if (JSON.stringify(t1) !== JSON.stringify(["demo", "empty", "onebyte"])) {
      throw new Error(`seed titles: ${JSON.stringify(t1)}`);
    }
    if (k1.length !== 3 || new Set(k1).size !== 3) {
      throw new Error(`seed keys not unique: ${JSON.stringify(k1)}`);
    }
    if (k1.some((k) => k === undefined || k === 0)) {
      throw new Error(`seed keys invalid: ${JSON.stringify(k1)}`);
    }

    // Remove middle row — remaining keys must keep identity
    await page.locator("#koru-list li").nth(1).locator("button").click();
    await page.waitForFunction(() => document.querySelectorAll("#koru-list li").length === 2);
    const t2 = await titles(page);
    const k2 = await keys(page);
    if (JSON.stringify(t2) !== JSON.stringify(["demo", "onebyte"])) {
      throw new Error(`after remove titles: ${JSON.stringify(t2)}`);
    }
    if (k2[0] !== k1[0] || k2[1] !== k1[2]) {
      throw new Error(`handles not stable after remove: before=${k1} after=${k2}`);
    }

    await page.click("#append");
    await page.waitForFunction(() => document.querySelectorAll("#koru-list li").length === 3);
    const k3 = await keys(page);
    if (k3[0] !== k2[0] || k3[1] !== k2[1]) {
      throw new Error(`handles changed on append: ${k2} -> ${k3}`);
    }

    const beforeSwapKeys = await keys(page);
    const beforeSwapTitles = await titles(page);
    await page.click("#swap");
    await page.waitForFunction(
      (expected) => {
        const t = [...document.querySelectorAll("#koru-list li .title")].map((n) => n.textContent);
        return t[0] === expected[1] && t[1] === expected[0];
      },
      beforeSwapTitles
    );
    const afterSwapTitles = await titles(page);
    const afterSwapKeys = await keys(page);
    if (
      afterSwapTitles[0] !== beforeSwapTitles[1] ||
      afterSwapTitles[1] !== beforeSwapTitles[0]
    ) {
      throw new Error(`swap titles: ${beforeSwapTitles} -> ${afterSwapTitles}`);
    }
    if (
      afterSwapKeys[0] !== beforeSwapKeys[1] ||
      afterSwapKeys[1] !== beforeSwapKeys[0]
    ) {
      throw new Error(`swap keys moved with nodes: ${beforeSwapKeys} -> ${afterSwapKeys}`);
    }
    // Same handle still on same title text (identity survives reorder)
    if (afterSwapKeys[0] !== beforeSwapKeys[1] || afterSwapKeys[1] !== beforeSwapKeys[0]) {
      throw new Error("reorder broke handle↔node coupling");
    }

    console.log("keyed identity OK (insert/remove/reorder + stable handles)");
  } finally {
    if (browser) await browser.close();
    server.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
