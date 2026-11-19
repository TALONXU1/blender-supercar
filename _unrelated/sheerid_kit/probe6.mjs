import { Camoufox } from 'camoufox';
const URL = process.argv[2];
const Q = process.argv[3] || 'College of the Desert';

const b = await Camoufox({ headless: true, locale: 'en-US', fingerprint_preset: false, humanize: 1.5, geoip: true });
const ctx = await b.newContext({ locale: 'en-US' });
const page = await ctx.newPage();

let capture = false;
const seen = [];
page.on('request', r => {
  if (!capture) return;
  if (!/sheerid\.(com|net)/.test(r.url())) return;
  if (/\.(js|css|png|svg|woff2?|ico)($|\?)/.test(r.url())) return;
  seen.push({ m: r.method(), u: r.url(), h: r.headers() });
});
const bodies = new Map();
page.on('response', async r => {
  if (!capture) return;
  if (!/sheerid\.(com|net)/.test(r.url())) return;
  try { bodies.set(r.url(), (await r.text()).slice(0, 1500)); } catch {}
});

await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForTimeout(3000);

await page.locator('#sid-country').click();
await page.waitForTimeout(500);
await page.locator('#sid-country').type('美国', { delay: 90 });
await page.waitForTimeout(1500);
const items = await page.evaluate(() => [...document.querySelectorAll('#sid-country-menu [role="option"]')].map(e => ({ id: e.id, t: e.innerText.trim() })));
const us = items.find(o => o.t === '美国');
await page.locator('#' + us.id).click();
await page.waitForTimeout(2500);

capture = true;
seen.length = 0; bodies.clear();
const school = page.locator('#sid-college-name');
await school.click();
await school.type(Q, { delay: 90 });
await page.waitForTimeout(5000);
capture = false;

console.log('=== requests ===');
for (const s of seen) console.log(`\n${s.m} ${s.u}`);
console.log('\n=== bodies ===');
for (const [u, body] of bodies) { console.log('\n' + u.slice(0, 150)); console.log(body.slice(0, 900)); }
await b.close();
