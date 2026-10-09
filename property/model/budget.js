// Construction budget and spending ledger for 64 Stone Sheep Circle.
// State lives in this browser (localStorage); export/import moves it between devices.

export const KEY = 'ssp-budget-v1';

export function fresh(seed) {
  return { v: 1, contingency: seed.contingency_pct, lines: seed.lines.map(l => ({ ...l })), payments: [] };
}

export function load(seed) {
  try {
    const s = JSON.parse(localStorage.getItem(KEY) || 'null');
    if (s && Array.isArray(s.lines) && Array.isArray(s.payments)) return s;
  } catch {}
  return fresh(seed);
}

export function save(state) {
  try { localStorage.setItem(KEY, JSON.stringify(state)); return true; } catch { return false; }
}

export const lineBudget = l => (Number(l.qty) || 0) * (Number(l.price) || 0);

export function summarize(state) {
  const spent = {};
  for (const p of state.payments) spent[p.line] = (spent[p.line] || 0) + (Number(p.amount) || 0);
  const groups = new Map();
  for (const l of state.lines) {
    const g = groups.get(l.group) || { name: l.group, budget: 0, spent: 0, lines: [] };
    const b = lineBudget(l), s = spent[l.id] || 0;
    g.lines.push({ ...l, budget: b, spent: s, left: b - s });
    g.budget += b; g.spent += s; groups.set(l.group, g);
  }
  const base = [...groups.values()].reduce((a, g) => a + g.budget, 0);
  const contingency = base * (Number(state.contingency) || 0) / 100;
  const paid = state.payments.reduce((a, p) => a + (Number(p.amount) || 0), 0);
  const unassigned = state.payments.filter(p => !state.lines.some(l => l.id === p.line)).reduce((a, p) => a + (Number(p.amount) || 0), 0);
  return { groups: [...groups.values()], base, contingency, total: base + contingency, paid, left: base + contingency - paid, unassigned };
}

export function newId(prefix, list) {
  let n = list.length + 1;
  while (list.some(x => x.id === prefix + n)) n++;
  return prefix + n;
}

export function toCsv(state) {
  const q = v => /[",\n]/.test(String(v)) ? '"' + String(v).replace(/"/g, '""') + '"' : String(v);
  const name = Object.fromEntries(state.lines.map(l => [l.id, l.group + ' / ' + l.name]));
  const rows = [['Date', 'Budget line', 'Paid to', 'Amount', 'Note']].concat(
    [...state.payments].sort((a, b) => a.date.localeCompare(b.date)).map(p => [p.date, name[p.line] || '(removed line)', p.vendor, p.amount, p.note || '']));
  return rows.map(r => r.map(q).join(',')).join('\n');
}

// The shared copy kept by the Cloudflare Worker (/api/doc/budget), when the app is
// opened through it and signed in. Resolves to null anywhere else (GitHub Pages,
// opened from disk, offline), and the budget then stays in this browser only.
// The newer copy wins, by `updatedAt`, which every saved change stamps.
export async function cloudStore() {
  if (!/^https?:$/.test(location.protocol)) return null;
  const api = new URL('../api/', location.href);
  try {
    const r = await fetch(new URL('ping', api), { cache: 'no-store', credentials: 'same-origin' });
    if (!r.ok || !(await r.json()).ok) return null;
  } catch { return null; }
  const doc = new URL('doc/budget', api);
  return {
    async get() {
      const r = await fetch(doc, { cache: 'no-store', credentials: 'same-origin' });
      if (!r.ok) throw new Error('sync read ' + r.status);
      const j = await r.json();
      return j.exists ? j.data : null;
    },
    async put(state) {
      const r = await fetch(doc, { method: 'PUT', cache: 'no-store', credentials: 'same-origin', headers: { 'content-type': 'application/json' }, body: JSON.stringify(state) });
      if (!r.ok) throw new Error('sync write ' + r.status);
    },
  };
}
