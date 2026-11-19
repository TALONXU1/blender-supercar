import { Camoufox } from 'camoufox';
const URL = process.argv[2];
const COUNTRY = process.argv[3] || '美国';
const QUERY = process.argv[4] || 'College';

const b = await Camoufox({ headless: true, locale: 'en-US', fingerprint_preset: false, humanize: 1.5, geoip: true });
const ctx = await b.newContext({ locale: 'en-US' });
const page = await ctx.newPage();
const api = [];
page.on('response', async r => {
  const u = r.url();
  if (!/sheerid\.(com|net)/.test(u)) return;
  if (/\.(js|css|png|svg|woff2?)($|\?)/.test(u)) return;
  let body = '';
  try { body = (await r.text()).slice(0, 5000); } catch {}
  api.push({ u, s: r.status(), body });
});

await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForTimeout(3500);

// 1) 国家
await page.locator('#sid-country').click();
await page.waitForTimeout(600);
await page.locator('#sid-country').type(COUNTRY, { delay: 90 });
await page.waitForTimeout(1500);
const filtered = await page.evaluate(() => [...document.querySelectorAll('#sid-country-menu [role="option"]')]
  .map(e => ({ id: e.id, txt: e.innerText.trim() })));
console.log('filtered countries:', filtered.map(o => o.txt).join(' | ') || '(none)');
const exact = filtered.find(o => o.txt === COUNTRY) || filtered[0];
if (!exact) { await b.close(); process.exit(1); }
await page.locator('#' + exact.id).click();
await page.waitForTimeout(2500);
console.log('selected:', exact.txt);

// 2) 学校
const school = page.locator('#sid-college-name');
console.log('school enabled:', await school.isEnabled().catch(() => false));
if (await school.isEnabled().catch(() => false)) {
  await school.click();
  await page.waitForTimeout(400);
  await school.type(QUERY, { delay: 90 });
  await page.waitForTimeout(4500);
  const opts = await page.evaluate(() => [...document.querySelectorAll('#sid-org-list-menu [role="option"], [role="option"]')]
    .map(e => e.innerText.trim()).filter(t => t && t.length > 2).slice(0, 60));
  console.log('--- school options ---');
  console.log(opts.join('\n') || '(none)');
}

await page.waitForTimeout(1500);
console.log('\n=== API ===');
for (const h of api) {
  
  console.log(`\n[${h.s}] ${h.u.slice(0, 200)}`);
  console.log(h.body.slice(0, 2500));
}
await b.close();
