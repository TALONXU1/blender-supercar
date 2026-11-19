import { Camoufox } from 'camoufox';
const URL = process.argv[2];
const Q = process.argv[3] || 'College of the Desert';

const b = await Camoufox({ headless: true, locale: 'en-US', fingerprint_preset: false, humanize: 1.5, geoip: true });
const ctx = await b.newContext({ locale: 'en-US' });
const page = await ctx.newPage();
await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForTimeout(3000);

const out = await page.evaluate(async (q) => {
  const cfg = await fetch('https://my.sheerid.com/rest/v2-beta/programs/67c8c14f5f17a83b745e3f82/configuration', { headers: { origin: 'https://services.sheerid.com' } }).then(r => r.json());
  const res = await fetch(cfg.orgSearchUrl + encodeURIComponent(q), { headers: { origin: 'https://services.sheerid.com', referer: location.href, accept: 'application/json' } });
  const txt = await res.text();
  return { status: res.status, url: cfg.orgSearchUrl.slice(-80), body: txt.slice(0, 4000) };
}, Q);

console.log('status', out.status, '| url tail', out.url);
console.log(out.body);

await b.close();
