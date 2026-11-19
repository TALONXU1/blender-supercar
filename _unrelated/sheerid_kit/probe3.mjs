import { Camoufox } from 'camoufox';
const URL = process.argv[2];
const b = await Camoufox({ headless: true, locale: 'en-US', fingerprint_preset: false, humanize: 1.5, geoip: true });
const ctx = await b.newContext({ locale: 'en-US' });
const page = await ctx.newPage();
const reqs = [];
page.on('request', r => { if (/sheerid/.test(r.url()) && !/\.(js|css|png|svg|woff2?)/.test(r.url())) reqs.push(r.method() + ' ' + r.url()); });
await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForTimeout(3500);

const c = page.locator('#sid-country');
await c.click();
await page.waitForTimeout(1200);
console.log('--- after click, expanded=', await c.getAttribute('aria-expanded'));

const dump = await page.evaluate(() => {
  const out = {};
  const ctl = document.querySelector('#sid-country')?.getAttribute('aria-controls');
  out.controls = ctl;
  if (ctl) { const m = document.getElementById(ctl); out.menuHTML = m ? m.outerHTML.slice(0, 1500) : 'null'; }
  out.options = [...document.querySelectorAll('[role="option"]')].slice(0, 12).map(e => ({ id: e.id, txt: e.innerText.trim().slice(0, 40) }));
  out.inputs = [...document.querySelectorAll('input[id]')].map(e => e.id);
  return out;
});
console.log(JSON.stringify(dump, null, 1).slice(0, 2600));

console.log('\n--- requests so far ---');
console.log([...new Set(reqs)].join('\n'));

await b.close();
