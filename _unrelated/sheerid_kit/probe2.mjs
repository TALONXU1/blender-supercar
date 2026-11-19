import { Camoufox } from 'camoufox';

const URL = process.argv[2];
const COUNTRY = process.argv[3] || 'United States';
const QUERY = process.argv[4] || 'College';

const b = await Camoufox({ headless: true, locale: 'en-US', fingerprint_preset: false, humanize: 1.5, geoip: true });
const ctx = await b.newContext({ locale: 'en-US' });
const page = await ctx.newPage();

const hits = [];
page.on('response', async res => {
  const u = res.url();
  if (!/sheerid\.com/.test(u)) return;
  if (!/organization|org|school|college|lookup|search/i.test(u)) return;
  let body = '';
  try { body = (await res.text()).slice(0, 6000); } catch {}
  hits.push({ url: u, status: res.status(), body });
});

await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForTimeout(3500);

// --- 国家 ---
const country = page.locator('#sid-country').first();
await country.click();
await page.waitForTimeout(400);
await country.type(COUNTRY, { delay: 70 });
await page.waitForTimeout(2200);
const opts = await page.evaluate(() => {
  const out = [];
  document.querySelectorAll('[role="option"], li[id*="option"], [class*="option"]').forEach(e => {
    const t = e.innerText?.trim(); if (t && t.length < 60) out.push(t);
  });
  return [...new Set(out)].slice(0, 30);
});
console.log('country candidates:', opts.join(' | ') || '(none)');
const pick = opts.find(t => t.includes('United States') || t.includes('美国')) || opts[0];
if (pick) {
  await page.getByText(pick, { exact: true }).first().click().catch(async () => {
    await page.locator('[role="option"]').first().click();
  });
  console.log('picked country:', pick);
  await page.waitForTimeout(2500);
}

// --- 学校 ---
const school = page.locator('#sid-college-name').first();
console.log('school input count:', await school.count(), 'enabled:', await school.isEnabled().catch(() => false));
await school.click();
await page.waitForTimeout(300);
await school.type(QUERY, { delay: 80 });
await page.waitForTimeout(4000);

const schools = await page.evaluate(() => {
  const out = [];
  document.querySelectorAll('[role="option"], li[id*="option"], [class*="option"], [class*="menu"] li').forEach(e => {
    const t = e.innerText?.trim(); if (t && t.length > 2 && t.length < 120) out.push(t);
  });
  return [...new Set(out)].slice(0, 50);
});
console.log('--- school options ---');
console.log(schools.join('\n') || '(none)');

await page.waitForTimeout(1500);
console.log('\n=== captured org API ===');
for (const h of hits) {
  console.log(`\n[${h.status}] ${h.url.slice(0, 160)}`);
  console.log(h.body.slice(0, 1500));
}

await b.close();
