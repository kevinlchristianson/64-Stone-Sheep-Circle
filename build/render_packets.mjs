// Prints contractor/packets/*.html to PDF (letter landscape) with Playwright's Chromium.
//   npm install --no-save playwright && npx playwright install chromium   (once)
//   node build/render_packets.mjs
// Run after build/build.py whenever a sheet changes; the app's packet buttons open these PDFs.
import { readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const dir = join(here, '..', 'contractor', 'packets');
let chromium;
try { ({ chromium } = await import('playwright')); }
catch { ({ chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')); }
const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
const page = await browser.newPage();
for (const f of readdirSync(dir).filter(f => f.endsWith('.html'))) {
  await page.goto(pathToFileURL(join(dir, f)).href, { waitUntil: 'load' });
  await page.pdf({ path: join(dir, f.replace(/\.html$/, '.pdf')), format: 'Letter', landscape: true, printBackground: true, margin: { top: '0.4in', bottom: '0.4in', left: '0.4in', right: '0.4in' } });
  console.log('printed', f.replace(/\.html$/, '.pdf'));
}
await browser.close();
