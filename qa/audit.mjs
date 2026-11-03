// Dark-theme sweep, keyboard focus, touch-target and modal checks over the fictional demo.
import { chromium } from '../apps/web/node_modules/playwright/index.mjs';
import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = fileURLToPath(new URL('../', import.meta.url));
const output = process.env.MANU_AUDIT || path.join(root, 'qa', 'audit');
mkdirSync(output, { recursive: true });
const base = 'http://127.0.0.1:8791';
try { await fetch(base + '/api/cases'); throw new Error('Port 8791 is already in use.'); } catch (e) { if (e.message.includes('in use')) throw e; }
const server = spawn('uv', ['run', 'manu', 'serve', '--demo', '--port', '8791'], { cwd: root, stdio: 'ignore' });
let browser;
const report = { dark: [], focus: [], smallTargets: [], modals: [], errors: [] };
try {
  for (let i = 0; i < 100; i++) { try { if ((await fetch(base + '/api/cases')).ok) break; } catch {} await new Promise(r => setTimeout(r, 100)); }
  browser = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox'] });
  const data = await (await fetch(base + '/api/cases')).json();
  const imran = data.cases.find(c => c.title === 'State v. Imran Sheikh');
  const p = await browser.newPage({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
  p.on('pageerror', e => report.errors.push(e.message));
  const settle = async () => { await p.waitForTimeout(250); await p.locator('.mn-faint.mn-pad').waitFor({ state: 'hidden' }).catch(() => {}); };
  const open = async route => { await p.goto(base + '/#' + route); await settle(); };
  const shot = async name => { await p.screenshot({ path: `${output}/${name}.png` }); report.dark.push(name); };
  // contrast: text colour vs effective background for every visible text node
  const contrast = () => p.evaluate(() => {
    const parse = s => (s.match(/[\d.]+/g) || []).map(Number);
    const lum = ([r, g, b]) => { const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; }; return .2126 * f(r) + .7152 * f(g) + .0722 * f(b); };
    const bg = el => { let n = el; while (n) { const c = parse(getComputedStyle(n).backgroundColor); if (c.length >= 3 && (c[3] ?? 1) > .9) return c; n = n.parentElement; } return [255, 255, 255]; };
    const out = []; const seen = new Set();
    for (const el of document.querySelectorAll('.mn *')) {
      if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
      const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
      const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || +cs.opacity === 0) continue;
      let fg = parse(cs.color); const a = fg[3] ?? 1; const b = bg(el);
      fg = fg.slice(0, 3).map((v, i) => v * a + b[i] * (1 - a));
      const L1 = lum(fg), L2 = lum(b); const ratio = (Math.max(L1, L2) + .05) / (Math.min(L1, L2) + .05);
      const size = parseFloat(cs.fontSize); const large = size >= 24 || (size >= 18.66 && +cs.fontWeight >= 700);
      if (ratio < (large ? 3 : 4.5)) { const key = el.className + '|' + cs.color; if (!seen.has(key)) { seen.add(key); out.push({ cls: String(el.className).slice(0, 40), text: el.textContent.trim().slice(0, 30), ratio: +ratio.toFixed(2), size }); } }
    }
    return out;
  });
  for (const theme of ['Light', 'Dark']) {
    if (theme === 'Dark') { await open('/'); await p.getByRole('button', { name: 'Dark', exact: true }).click(); }
    const tag = theme.toLowerCase();
    for (const [route, name] of [['/', 'today'], ['/attention', 'attention'], ['/week', 'week'], ['/changes', 'changes'], ['/c/' + imran.id, 'case']]) {
      await open(route); if (theme === 'Dark') await shot(`dark-${name}`);
      report.dark.push([tag, name, 'low-contrast', await contrast()]);
    }
    await open('/c/' + imran.id);
    for (const tab of ['Notes', 'Authorities', 'Deadline', 'Draft', 'Bail facts']) {
      await p.getByRole('tab', { name: tab, exact: true }).click(); await p.locator('.mn-bench').scrollIntoViewIfNeeded(); await settle();
      if (theme === 'Dark') await shot(`dark-tool-${tab.toLowerCase().replace(' ', '-')}`);
      report.dark.push([tag, 'tool-' + tab, 'low-contrast', await contrast()]);
    }
    await p.getByRole('button', { name: 'Show sources', exact: true }).click();
    for (const tab of ['Source', 'Papers', 'Research', 'Dates', 'Timeline']) {
      await p.getByRole('tab', { name: tab, exact: true }).click(); await settle();
      if (theme === 'Dark') await shot(`dark-panel-${tab.toLowerCase()}`);
      report.dark.push([tag, 'panel-' + tab, 'low-contrast', await contrast()]);
    }
    await p.getByRole('button', { name: 'Close panel', exact: true }).click();
    await p.getByRole('tab', { name: 'Draft', exact: true }).click();
    await p.locator('.mn-draft-buttons button').first().click(); await p.locator('.mn-questions label').first().waitFor();
    if (theme === 'Dark') await shot('dark-application');
    report.dark.push([tag, 'application', 'low-contrast', await contrast()]);
    await p.getByRole('button', { name: 'Close', exact: true }).click();
    await p.getByRole('button', { name: 'Draft a client update', exact: true }).click(); await p.locator('textarea.mn-draft').waitFor();
    await p.waitForFunction(() => document.querySelector('textarea.mn-draft')?.value.length > 0);
    if (theme === 'Dark') await shot('dark-client-draft');
    report.dark.push([tag, 'client-draft', 'low-contrast', await contrast()]);
    // modal: Escape closes, focus is inside while open
    const inside = await p.evaluate(() => !!document.activeElement?.closest('[role=dialog], .mn-sheet-modal, .mn-modal, .mn-draft-sheet'));
    await p.keyboard.press('Escape'); await p.waitForTimeout(200);
    report.modals.push({ theme: tag, focusInsideOnOpen: inside, closedByEscape: !(await p.locator('textarea.mn-draft').count()) });
    if (await p.locator('textarea.mn-draft').count()) await p.getByRole('button', { name: 'Close', exact: true }).click();
    if (theme === 'Dark') await p.getByRole('button', { name: 'Light', exact: true }).click();
  }
  // keyboard: tab through each route, every stop must show a visible focus ring
  for (const route of ['/', '/attention', '/week', '/changes', '/c/' + imran.id]) {
    await open(route); await p.evaluate(() => document.activeElement?.blur());
    let bad = [];
    for (let i = 0; i < 45; i++) {
      await p.keyboard.press('Tab');
      const r = await p.evaluate(() => { const el = document.activeElement; if (!el || el === document.body) return null; const cs = getComputedStyle(el); const w = parseFloat(cs.outlineWidth); const vis = (cs.outlineStyle !== 'none' && w > 0) || cs.boxShadow !== 'none'; return { vis, tag: el.tagName, cls: String(el.className).slice(0, 30), label: (el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 25) }; });
      if (r && !r.vis) bad.push(r);
    }
    report.focus.push({ route: route.replace(imran.id, ':case'), noVisibleFocus: bad });
  }
  // touch targets at phone width
  await p.setViewportSize({ width: 390, height: 844 });
  for (const route of ['/', '/attention', '/week', '/changes', '/c/' + imran.id]) {
    await open(route);
    const small = await p.evaluate(() => [...document.querySelectorAll('.mn button, .mn a, .mn input, .mn select, .mn summary, .mn [role=tab]')].map(el => { const r = el.getBoundingClientRect(); return { r, el }; }).filter(({ r }) => r.width && r.height && (r.height < 36 || r.width < 36)).map(({ r, el }) => ({ tag: el.tagName, cls: String(el.className).slice(0, 30), label: (el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 22), w: Math.round(r.width), h: Math.round(r.height) })));
    report.smallTargets.push({ route: route.replace(imran.id, ':case'), count: small.length, sample: small.slice(0, 12) });
  }
  writeFileSync(path.join(output, 'audit.json'), JSON.stringify(report, null, 1));
  console.log(JSON.stringify({ errors: report.errors, modals: report.modals, focus: report.focus, small: report.smallTargets.map(s => [s.route, s.count]) }));
  for (const d of report.dark.filter(Array.isArray)) if (d[3].length) console.log(d[0], d[1], JSON.stringify(d[3].slice(0, 6)));
} finally { await browser?.close(); server.kill('SIGTERM'); }
