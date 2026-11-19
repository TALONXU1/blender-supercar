#!/usr/bin/env node
/**
 * SheerID 一键执行器
 *
 *   把验证链接粘到 sheerid_kit/url.txt，然后：
 *     node pass.mjs status      只查状态，不改远端
 *     node pass.mjs submit      填表 + 提交材料 + 轮询到出结果
 *
 * 也可直接传参：
 *     node pass.mjs submit --url=https://services.sheerid.com/verify/xxx/?verificationId=yyy
 *
 * 其余字段默认取 fields.json，可用 --first/--last/--dob/--email/--school/--option 覆盖。
 */
import { readFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { dirname, join, resolve, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';

const BASE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(BASE, '..', '_ref', 'sheeridVerify');
const CFG = join(REPO, 'config', 'sheerid.local.json');
const MODE = (process.argv[2] || '').toLowerCase();

function arg(name, fallback) {
  const hit = process.argv.slice(3).find(a => a === `--${name}` || a.startsWith(`--${name}=`));
  if (!hit) return fallback;
  if (hit.includes('=')) return hit.slice(hit.indexOf('=') + 1);
  const i = process.argv.indexOf(hit);
  return process.argv[i + 1];
}

function die(msg) {
  console.error(`\n[X] ${msg}\n`);
  process.exit(1);
}

if (!['status', 'submit', 'ip'].includes(MODE)) {
  console.log(`
用法:
  node pass.mjs ip          查出口 IP 归属地(SheerID 风控看到的就是这个)
  node pass.mjs status      只读查询, 打印当前步骤/错误码
  node pass.mjs submit      自动填写并提交材料

准备:
  1. 浏览器打开商户的学生认证页, 走到底, 复制地址栏里
     https://services.sheerid.com/verify/.../?verificationId=...
  2. 粘到 sheerid_kit/url.txt (或 --url=...)
  3. node pass.mjs status   确认状态正常后再 submit
`);
  process.exit(0);
}

// ---- 出口 IP 诊断：浏览器固定声称 America/Los_Angeles + en-US，
//      出口 IP 不在美国时 TZ/IP 打架，直接触发 fraudRulesReject
if (MODE === 'ip') {
  async function probe(host) {
    try {
      const t = await fetch(`https://${host}/cdn-cgi/trace`).then(x => x.text());
      const kv = Object.fromEntries(t.trim().split('\n').map(l => l.split('=')).filter(a => a.length === 2));
      return { ip: kv.ip, country: kv.loc, colo: kv.colo };
    } catch { return null; }
  }
  const r = await probe('cloudflare.com') || await probe('www.cloudflare.com') || { ip: '?', country: '?' };
  console.log('\n  出口 IP   ', r.ip);
  console.log('  归属      ', r.country, r.colo ? `(CF ${r.colo})` : '');
  const ok = r.country === 'US';
  console.log(`  判定      ${ok ? 'OK — 与美国时区一致' : '风险 — 浏览器声称 America/Los_Angeles，出口不匹配会挂 fraudRulesReject'}`);
  if (!ok) console.log('  建议      node pass.mjs submit --proxy=http://user:pass@us-host:port\n');
  process.exit(0);
}

// ---- URL ----
let url = arg('url', process.env.SHEERID_URL || '');
if (!url) {
  const f = join(BASE, 'url.txt');
  if (existsSync(f)) url = (await readFile(f, 'utf8')).split(/\s+/).find(t => t.startsWith('http')) || '';
}
if (!url && process.platform === 'win32') {
  // 直接吃剪贴板：浏览器里 Ctrl+C 复制验证链接，这里自动接管
  try {
    const clip = execFileSync('powershell', ['-NoProfile', '-Command', 'Get-Clipboard'],
      { encoding: 'utf8', windowsHide: true }).trim();
    if (/sheerid\.com/.test(clip)) {
      url = clip.split(/\s+/).find(t => t.startsWith('http')) || '';
      if (url) console.log('  [i] 已从剪贴板读取验证链接');
    }
  } catch { /* 剪贴板不可用时忽略 */ }
}
if (!url) die('缺验证链接。把地址栏 URL 粘进 sheerid_kit/url.txt，或用 --url=...');
if (!/sheerid\.com/.test(url)) die(`不是 SheerID 链接: ${url.slice(0, 80)}`);
const m = url.match(/[a-f\d]{24}/i);
if (!m) die('链接里找不到 24 位 verificationId');

// ---- 身份字段 ----
const fieldsPath = join(BASE, 'fields.json');
const fields = existsSync(fieldsPath) ? JSON.parse(await readFile(fieldsPath, 'utf8')) : {};
const parts = (fields.student_name || 'Alex R. Morgan').replace(/\s+/g, ' ').trim().split(' ');
const first = arg('first', parts[0]);
const last = arg('last', parts.length > 1 ? parts[parts.length - 1] : 'Morgan');
const school = arg('school', fields.school_name || 'Northgate Community College');
const domain = arg('domain', (fields.school_email || 'northgate.edu').split('@').pop());

const docArg = arg('doc', '');
let doc = docArg || join(BASE, 'out', 'enrollment_letter.jpg');
if (!isAbsolute(doc)) doc = resolve(BASE, doc);
if (!existsSync(doc)) die(`材料文件不存在: ${doc}\n先跑 python build_kit.py 生成`);

const config = {
  app: 'sheerid',
  url,
  proxy: arg('proxy', 'direct'),
  browser: {
    headless: String(arg('headless', 'false')) === 'true',
    locale: 'en-US',
    keepOpen: true,
    autoFill: true,
  },
  document: { path: doc.replace(/\\/g, '/') },
  timeouts: {
    apiMs: 20000, downloadMs: 120000, uploadMs: 120000,
    actionMs: 15000, navigationMs: 60000,
    readyMs: Number(arg('ready', 180000)),
    humanMs: Number(arg('human', 240000)),
    resultMs: 45000,
  },
  interaction: {
    keyDelayMs: { min: 40, max: 120 },
    fieldDelayMs: { min: 500, max: 1200 },
    submitDelayMs: { min: 1000, max: 2000 },
  },
  polling: { intervalMs: 5000 },
  artifactsDir: '.runs',
  data: {
    country: arg('country', 'United States'),
    firstName: first,
    lastName: last,
    email: arg('email', `${first.toLowerCase()}.${last.toLowerCase()}@${domain}`),
    birthDate: arg('dob', '2004-03-14'),
    consent: arg('consent', '') === '1' ? true : undefined,
    organization: {
      name: school,
      optionText: arg('option', school),
      emailDomain: domain,
    },
  },
};

// 固定设备指纹：存在 config/fingerprint.json 就复用，避免每次运行都换一台"新电脑"
const fpPath = join(REPO, 'config', 'fingerprint.json');
if (existsSync(fpPath)) {
  config.browser.fingerprint = JSON.parse(await readFile(fpPath, 'utf8'));
  console.log('  [i] 已装载固定指纹 config/fingerprint.json');
}

await writeFile(CFG, JSON.stringify(config, null, 2), 'utf8');

console.log(`\n  模式    ${MODE}`);
console.log(`  链接    ${url.slice(0, 72)}${url.length > 72 ? '…' : ''}`);
console.log(`  姓名    ${first} ${last}   ${config.data.birthDate}`);
console.log(`  邮箱    ${config.data.email}`);
console.log(`  学校    ${school}  (option: ${config.data.organization.optionText})`);
console.log(`  材料    ${doc}`);
console.log(`  配置    ${CFG}\n`);

const args = ['src/cli.js', MODE === 'submit' ? '--submit' : '--status', '--config', CFG];
if (MODE === 'submit') args.push('--file', doc);

// submit 模式：一旦确认材料进入审核队列，立即终止子进程。
// 原因：服务端退回 docUpload 时脚本会自动重传，而每个 verification 只有 3 次材料审核额度，
// 自动重传会在 10 秒内把额度烧光（实测：docReviewLimitExceeded）。这里保证只上传一次。
if (MODE === 'status') {
  try { execFileSync(process.execPath, args, { cwd: REPO, stdio: 'inherit' }); }
  catch (e) { process.exit(e.status ?? 1); }
} else {
  const { spawn } = await import('node:child_process');
  const child = spawn(process.execPath, args, { cwd: REPO, stdio: ['ignore', 'pipe', 'inherit'] });
  let buf = '', done = false;
  child.stdout.on('data', chunk => {
    const s = chunk.toString();
    process.stdout.write(s);
    buf += s;
    if (!done && /"code":"AWAITING_REVIEW"|"currentStep":"pending"/.test(buf)) {
      done = true;
      console.log('\n\n[✓] 材料已进入审核队列，主动终止 — 防止自动重传烧光审核额度。');
      console.log('[i] 后续用 node pass.mjs status 查看结果即可。\n');
      setTimeout(() => child.kill('SIGINT'), 400);
    }
  });
  const code = await new Promise(res => child.on('exit', c => res(c ?? 0)));
  process.exit(done ? 0 : (code || 0));
}
