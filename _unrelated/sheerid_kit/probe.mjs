import { Camoufox } from 'camoufox';

const URL = process.argv[2];
const QUERY = process.argv[3] || 'Community College';

const b = await Camoufox({ headless: true, locale: 'en-US', fingerprint_preset: false, humanize: 1.5, geoip: true });
const ctx = await b.newContext({ locale: 'en-US' });
const page = await ctx.newPage();

const hits = [];
page.on('response', async res => {
  const u = res.url();
  if (!/sheerid\.com/.test(u)) return;
  if (!/organization|school|search|program/i.test(u)) return;
  let body = '';
  try { body = (await res.text()).slice(0, 4000); } catch {}
  hits.push({ url: u, status: res.status(), body });
});

console.log('→ goto');
await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
await page.waitForTimeout(4000);

const title = await page.title();
console.log('title:', title);
console.log('url  :', page.url());

// 页面可见文本前 600 字
const txt = (await page.locator('body').innerText().catch(() => '')).replace(/\n{2,}/g, '\n').slice(0, 700);
console.log('--- body text ---\n' + txt + '\n---');

// 找 select / input
const fields = await page.evaluate(() => {
  const out = [];
  document.querySelectorAll('select,input,button').forEach(el => {
    out.push({
      tag: el.tagName, type: el.type || '', id: el.id || '', name: el.name || '',
      ph: el.placeholder || '', aria: el.getAttribute('aria-label') || '',
      opts: el.tagName === 'SELECT' ? [...el.options].slice(0, 6).map(o => o.text.trim()) : undefined,
    });
  });
  return out.slice(0, 40);
});
console.log('--- fields ---');
for (const f of fields) console.log(JSON.stringify(f));

// 选国家
try {
  const sel = page.locator('select').first();
  if (await sel.count()) {
    const vals = await sel.locator('option').evaluateAll(os => os.map(o => ({ v: o.value, t: o.textContent.trim() })));
    console.log('--- country options (前15) ---');
    console.log(vals.slice(0, 15).map(o => `${o.v}=${o.t}`).join(' | '));
    const us = vals.find(o => /^US$|United States/i.test(o.t) || o.v === 'US');
    if (us) {
      await sel.selectOption(us.v);
      console.log('selected country:', us.t);
      await page.waitForTimeout(1500);
    }
  }
} catch (e) { console.log('country err', e.message); }

// 学校搜索
try {
  const cands = ['#sid-organization-search', 'input[name="organizationSearch"]', 'input[placeholder*="school" i]', 'input[placeholder*="School" i]'];
  let el = null;
  for (const c of cands) { const l = page.locator(c).first(); if (await l.count()) { el = l; console.log('school input:', c); break; } }
  if (el) {
    await el.click();
    await el.type(QUERY, { delay: 60 });
    await page.waitForTimeout(4000);
    const optTxt = await page.evaluate(() => {
      const out = [];
      document.querySelectorAll('[role="option"],[class*="option"],[class*="Option"]').forEach(e => {
        const t = e.innerText?.trim(); if (t && t.length < 120) out.push(t);
      });
      return [...new Set(out)].slice(0, 40);
    });
    console.log('--- school options ---');
    console.log(optTxt.join('\n') || '(none)');
  } else {
    console.log('school input not found');
  }
} catch (e) { console.log('school err', e.message); }

await page.waitForTimeout(2000);

console.log('\n=== captured API ===');
for (const h of hits) {
  console.log(`\n[${h.status}] ${h.url}`);
  console.log(h.body.slice(0, 1200));
}

await b.close();
