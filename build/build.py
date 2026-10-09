"""Builds the 64 Stone Sheep Circle Contractor App and the Property App's house data.

    python3 plan/house.py      # only when the plan data changes
    python3 build/build.py     # sheets, schedules, packets, contractor/index.html, property/data/

Reads plan/house.json; writes
  contractor/index.html            the app (3D, A-1, S-1, E-1, P-1, M-1, the owner's plans, crew chat)
  contractor/sheets/*.svg          each sheet on its own
  contractor/packets/*.html        printable trade packets (node build/render_packets.mjs prints the PDFs)
  build/schedules.md               every schedule and note as Markdown
  property/data/house-data.json    rooms, envelope areas, loads and take-offs for the Property App
  property/data/budget-seed.json   starting construction budget (quantities from the plans, placeholder prices)
Bump VERSION below (and in contractor/sw.js) whenever the app changes so phones pick up the new copy.
Python 3.8+, standard library only.
"""
import base64, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
VERSION = 'v2'

import plan, framing, electrical, plumbing, hvac   # noqa: E402
from setlib import HOUSE, ft_in                     # noqa: E402
from climate import CLIMATE, ENVELOPE               # noqa: E402

SHEETS = [('a1', 'A-1', 'Plan', plan), ('s1', 'S-1', 'Framing', framing), ('e1', 'E-1', 'Electrical', electrical),
          ('p1', 'P-1', 'Plumbing', plumbing), ('m1', 'M-1', 'HVAC', hvac)]
esc = lambda t: html.escape(str(t), quote=True)


def table_html(t, key):
    heads = ''.join(f'<th scope="col">{esc(c)}</th>' for c in t['cols'])
    body = []
    for rid, cells in t['rows']:
        tds = ''.join(f'<td data-label="{esc(t["cols"][i])}">{esc(c)}</td>' for i, c in enumerate(cells))
        body.append(f'<tr data-id="{esc(rid)}">{tds}</tr>' if rid else f'<tr>{tds}</tr>')
    search = f'<div class="tsearch"><input type="search" placeholder="Search {esc(t["title"].lower())}" aria-label="Search {esc(t["title"])}"><span class="cnt"></span></div>' if len(t['rows']) > 12 else ''
    lede = f'<p class="lede">{esc(t["lede"])}</p>' if t.get('lede') else ''
    return f'<section class="wide"><h3>{esc(t["title"])}</h3>{lede}{search}<div class="tbl"><table><thead><tr>{heads}</tr></thead><tbody>{"".join(body)}</tbody></table></div></section>'


def summary_html(key, s):
    if not s: return ''
    labels = {
        's1': [('runs', 'wall runs'), ('ext_lf', 'lf exterior wall'), ('int_lf', 'lf interior wall'), ('studs', 'studs'), ('wall_board', 'sf wall board'), ('ceiling_board', 'sf ceiling board')],
        'e1': [('devices', 'devices'), ('receptacles', 'receptacles'), ('lights', 'lights'), ('switches', 'switches'), ('circuits', 'circuits'), ('amps', 'A calculated load')],
        'p1': [('fixtures', 'fixtures'), ('dfu', 'DFU'), ('wsfu', 'WSFU'), ('stacks', 'stacks')],
        'm1': [('heat', 'Btu/h heating'), ('cool', 'Btu/h cooling'), ('tons', 'ton heat pump'), ('cfm', 'CFM'), ('registers', 'supply registers'), ('backup_kw', 'kW backup heat')],
    }.get(key, [])
    items = ''.join(f'<li><b>{s[k]:,}</b> {esc(v)}</li>' if isinstance(s[k], int) else f'<li><b>{s[k]:g}</b> {esc(v)}</li>' for k, v in labels if k in s)
    return f'<ul class="summary">{items}</ul>'


def sheet_section(key, no, name, b):
    sh = b['sheet']
    notes = ''.join(f'<li>{esc(n)}</li>' for n in b['notes'])
    opens = ''.join(f'<li>{esc(n)}</li>' for n in b['open'])
    tables = ''.join(table_html(t, key) for t in b['tables'])
    return f'''    <section class="sheet sheet2d" id="sheet-{key}" data-key="{key}" role="tabpanel" aria-labelledby="tab-{key}" hidden>
      <div class="tools">
        <div class="zoom" role="group" aria-label="Zoom"><button type="button" data-zoom="1">Fit</button><button type="button" data-zoom="2">2×</button><button type="button" data-zoom="4">4×</button></div>
        <p class="sel">Tap a tag on the drawing or a row in a schedule.</p>
        <a class="packet" href="packets/{no}-{name.lower()}-packet.pdf" target="_blank" rel="noopener">⎙ <span class="pk-name">{no} packet</span></a>
      </div>
      <div class="drawing"><div class="scroller"><div class="paper">{sh.svg()}</div></div></div>
      <div class="picked" hidden><div class="pk-card" role="region" aria-live="polite" aria-label="Selected item"><div class="pk-head"><span class="pk-tag"></span><span class="pk-sub"></span><button type="button" class="pk-x">Clear</button></div><dl class="pk-dl"></dl></div></div>
      <div class="below">
        <section><h2>{no} {esc(sh.title)}</h2><p class="lede">{esc(sh.subtitle)}</p>{summary_html(key, b.get('summary'))}<h3>Notes</h3><ol>{notes}</ol></section>
        <section><h2>Open items</h2><p class="lede">The particulars to settle on this sheet.</p><ul class="open">{opens}</ul></section>
        {tables}
      </div>
    </section>
'''


def packet_html(no, name, b):
    sh = b['sheet']
    notes = ''.join(f'<li>{esc(n)}</li>' for n in b['notes'])
    opens = ''.join(f'<li>{esc(n)}</li>' for n in b['open'])
    tables = ''
    for t in b['tables']:
        heads = ''.join(f'<th>{esc(c)}</th>' for c in t['cols'])
        rows = ''.join('<tr>' + ''.join(f'<td>{esc(c)}</td>' for c in cells) + '</tr>' for _, cells in t['rows'])
        tables += f'<h2>{esc(t["title"])}</h2>' + (f'<p class="lede">{esc(t["lede"])}</p>' if t.get('lede') else '') + f'<table><thead><tr>{heads}</tr></thead><tbody>{rows}</tbody></table>'
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{no} {esc(name)} packet · 64 Stone Sheep Circle</title>
<style>
@page {{ size: letter landscape; margin: 0.4in; }}
body {{ font: 10pt/1.35 "IBM Plex Sans", "Segoe UI", Helvetica, Arial, sans-serif; color: #221f1a; margin: 0; }}
.sheet svg {{ width: 100%; height: auto; max-height: 7.4in; display: block; }}
.page {{ page-break-after: always; }}
h1 {{ font: 700 18pt "Barlow Condensed", "Arial Narrow", sans-serif; margin: 0 0 4px; }}
h2 {{ font: 600 13pt "Barlow Condensed", "Arial Narrow", sans-serif; margin: 14px 0 4px; page-break-after: avoid; }}
.lede {{ color: #6f685d; margin: 0 0 6px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 8.5pt; }}
th, td {{ border: 1px solid #d6cfc3; padding: 3px 6px; text-align: left; vertical-align: top; }}
th {{ background: #eeeae2; }}
tr {{ page-break-inside: avoid; }}
.cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
li {{ margin: 0 0 4px; }}
</style></head><body>
<div class="page sheet">{sh.svg()}</div>
<h1>{no} {esc(name)} · 64 Stone Sheep Circle</h1>
<p class="lede">{esc(sh.subtitle)} App version {VERSION}. From the owner's plans (Larson House, 6/11/26).</p>
<div class="cols"><div><h2>Notes</h2><ol>{notes}</ol></div><div><h2>Open items</h2><ul>{opens}</ul></div></div>
{tables}
</body></html>
'''


def trade3d(e, p, m):
    items = []
    names = {'rec': 'Receptacle', 'rec-gfci': 'GFCI receptacle', 'rec-20': 'Washer receptacle', 'rec-240': 'Dryer receptacle', 'rec-wr': 'Exterior receptacle', 'switch': 'Switch',
             'light': 'Light', 'can': 'Recessed light', 'pend': 'Pendant', 'strip': 'Under-cabinet light', 'wall-light': 'Wall light', 'fan': 'Fan', 'appl': 'Appliance circuit', 'smoke': 'Smoke alarm', 'smoke-co': 'Smoke/CO alarm'}
    for d in e['devices']:
        h = d['h'] if d['h'] is not None else 1.0
        if d['kind'] in ('light', 'can', 'pend', 'fan', 'smoke', 'smoke-co') and d['h'] is None: h = 8.85
        items.append(dict(layer='elec', x=d['at'][0], y=d['at'][1], h=min(h, 8.85), size=0.45, name=f"{d['id']} · {names[d['kind']]}", text=d['desc']))
    for f in HOUSE['fixtures']:
        if f['kind'] in plumbing.TABLE:
            items.append(dict(layer='plumb', x=f['at'][0], y=f['at'][1], h=0.3, size=0.35, name=f"{f['id']} · {f['name']}", text='drain and supply, see P-1'))
    for s in p['stacks']:
        items.append(dict(layer='plumb', x=s['at'][0], y=s['at'][1], h=5.0, size=0.3, name=f"{s['id']} · {s['name']} stack", text='3" stack to the roof'))
        items.append(dict(layer='plumb', x=s['at'][0], y=s['at'][1], h=9.5, size=0.3, name=f"{s['id']} · vent", text='vent through the roof'))
    for h in p['hose']:
        items.append(dict(layer='plumb', x=h['at'][0], y=h['at'][1], h=1.5, size=0.35, cold=True, name=h['id'], text=h['name']))
    for r in m['regs']:
        items.append(dict(layer='hvac', x=r['at'][0], y=r['at'][1], h=8.9, size=0.9, name=r['id'], text=r['name']))
    # stacks drawn as tall thin boxes: give them height via two points (bottom and top)
    lines = [dict(layer='plumb', name=l['name'], pts=l['pts'], h=0.15, r=l['r']) for l in p['lines']]
    lines += [dict(layer='hvac', name='Supply trunk (attic)', pts=t, h=9.8, r=0.45) for t in m['trunks']]
    return items, lines


def main():
    out_c = os.path.join(ROOT, 'contractor')
    os.makedirs(os.path.join(out_c, 'sheets'), exist_ok=True)
    os.makedirs(os.path.join(out_c, 'packets'), exist_ok=True)
    built = {key: (no, name, mod.build()) for key, no, name, mod in SHEETS}
    tabs, sections, picks, md = [], [], {}, ['# 64 Stone Sheep Circle: schedules and notes', '',
                                              f'Generated by build/build.py ({VERSION}) from plan/house.json. Every number here is also on the sheets in the Contractor App.', '']
    for key, (no, name, b) in built.items():
        tabs.append(f'      <button type="button" role="tab" id="tab-{key}" aria-selected="false" aria-controls="sheet-{key}" data-sheet="{key}"><span class="no">{no}</span>{name}</button>')
        sections.append(sheet_section(key, no, name, b))
        picks[key] = b['picks']
        with open(os.path.join(out_c, 'sheets', f'{no}-{name.lower()}.svg'), 'w') as f: f.write(b['sheet'].svg())
        with open(os.path.join(out_c, 'packets', f'{no}-{name.lower()}-packet.html'), 'w') as f: f.write(packet_html(no, name, b))
        md += [f'## {no} {b["sheet"].title}', '', b['sheet'].subtitle, '', '### Notes', ''] + [f'{i}. {n}' for i, n in enumerate(b['notes'], 1)] + ['', '### Open items', ''] + [f'- {n}' for n in b['open']] + ['']
        for t in b['tables']:
            md += [f'### {t["title"]}', '']
            if t.get('lede'): md += [t['lede'], '']
            md += ['| ' + ' | '.join(t['cols']) + ' |', '|' + '---|' * len(t['cols'])]
            md += ['| ' + ' | '.join(str(c).replace('|', '/') for c in cells) + ' |' for _, cells in t['rows']] + ['']
    with open(os.path.join(HERE, 'schedules.md'), 'w') as f: f.write('\n'.join(md))

    items, lines = trade3d(built['e1'][2], built['p1'][2], built['m1'][2])
    house_lite = {k: HOUSE[k] for k in ('meta', 'rooms', 'windows', 'doors', 'fixtures', 'posts', 'walls', 'totals')}
    data = dict(house=house_lite, picks=picks, trade3d=items, lines3d=lines)
    floor = plan.build()['sheet']
    floor.L['grid'] = []; floor.L['title'] = []; floor.L['tags'] = []
    floor_svg = base64.b64encode(floor.svg().encode()).decode()
    t = HOUSE['totals']; hv = built['m1'][2]['summary']; el = built['e1'][2]['summary']
    facts = [('Heated', f"{t['heated_gross_sf']:,} sq ft"), ('Garage', f"{t['garage_gross_sf']:,} sq ft"), ('Porch / patio', f"{t['porch_sf']} / {t['patio_sf']} sq ft"),
             ('Bedrooms', '3 + office'), ('Baths', '2 full + master + powder'), ('Ceilings', "9' · 4:12 vault"), ('Heat pump', f"{hv['tons']:g} tons (draft)"), ('Service', f"200 A ({el['amps']} A calc.)")]
    plans_html = []
    captions = [('A-1', 'First floor plan with room sizes and dimensions'), ('A-2', 'Roof plan over the floor plan: pitches, vaulted ceiling notes'), ('A-3', 'Site plan with the north arrow'),
                ('A-3', 'Front and rear elevations'), ('A-4', 'Left and right elevations'), ('A-5', 'Floor plan with fixtures, cabinets and appliances')]
    for i, (no, cap) in enumerate(captions, 1):
        plans_html.append(f'        <figure><a href="plans/sheet-{i}.jpg" target="_blank" rel="noopener"><img src="plans/sheet-{i}.jpg" alt="Owner\'s sheet {no}: {esc(cap)}" loading="lazy" width="2592" height="1728"></a><figcaption><b>{no}</b>{esc(cap)}</figcaption></figure>')
    tpl = open(os.path.join(HERE, 'app_template.html')).read()
    page = (tpl.replace('{{VERSION}}', VERSION).replace('{{TABS}}', '\n'.join(tabs)).replace('{{SHEETS}}', ''.join(sections))
            .replace('{{PLANS}}', '\n'.join(plans_html)).replace('{{FACTS}}', ''.join(f'<dt>{esc(k)}</dt><dd>{esc(v)}</dd>' for k, v in facts))
            .replace('{{DATA}}', json.dumps(data, separators=(',', ':')).replace('</', '<\\/')).replace('{{FLOORSVG}}', floor_svg))
    with open(os.path.join(out_c, 'index.html'), 'w') as f: f.write(page)

    # the Property App's copy of the house: rooms, envelope areas and the trade summaries
    os.makedirs(os.path.join(ROOT, 'property', 'data'), exist_ok=True)
    loads = built['m1'][2]['loads']
    env = dict(walls=0.0, windows=0.0, doors=0.0, ceiling=0.0, vault=0.0, slab_ft=0.0, garage_wall=0.0, volume=0.0)
    for l in loads:
        r = next(r for r in HOUSE['rooms'] if r['id'] == l['id'])
        for e in l['exposures']:
            ops = hvac.openings_on(r, e)
            g = sum(o['w'] * o['h'] for o in ops if 'head' in o)
            d = sum(o['w'] * o['h'] for o in ops if 'head' not in o and o['kind'] != 'overhead')
            if e['kind'] == 'garage': env['garage_wall'] += e['len'] * 9 - d; env['doors'] += d
            else: env['walls'] += e['len'] * 9 - g - d; env['windows'] += g; env['doors'] += d; env['slab_ft'] += e['len']
        if l['id'] in hvac.VAULT: env['vault'] += r['area_sf'] * 1.054
        else: env['ceiling'] += r['area_sf']
        env['volume'] += l['vol']
    prop = dict(version=VERSION, meta=HOUSE['meta'], totals=t, climate=CLIMATE, envelope_defaults=ENVELOPE,
                envelope={k: round(v, 1) for k, v in env.items()},
                rooms=[dict(id=r['id'], name=r['name'], kind=r['kind'], label=r['label'], label_sf=r['label_sf'], area_sf=r['area_sf']) for r in HOUSE['rooms']],
                windows=len(HOUSE['windows']), doors=len(HOUSE['doors']),
                # conditioned glazing by side of the house, for the Property App's solar gains;
                # windows under the rear patio roof are counted as shaded
                glazing=[dict(id=w['id'], room=w['room'], side=('right' if w['axis'] == 'x' and w['at'] > 40 else 'left') if w['axis'] == 'x' else ('rear' if w['at'] < 30 else 'front'),
                              sf=round(w['w'] * w['h'], 1), shaded=w['wall'] == 'patio') for w in HOUSE['windows'] if w['room'] != 'garage'],
                loads=[dict(name=l['name'], heat=round(l['heat']), cool=round(l['cool']), cfm=round(l['cfm'])) for l in loads],
                trades={k: b['summary'] for k, (no, name, b) in built.items() if b.get('summary')},
                open_items={no: b['open'] for k, (no, name, b) in built.items()})
    with open(os.path.join(ROOT, 'property', 'data', 'house-data.json'), 'w') as f: json.dump(prop, f, indent=1)
    import budget_seed
    with open(os.path.join(ROOT, 'property', 'data', 'budget-seed.json'), 'w') as f: json.dump(budget_seed.build(prop), f, indent=1)
    print(f"contractor/index.html {len(page) / 1024:,.0f} KB · {sum(len(p) for p in picks.values())} pickable items · {len(items)} 3D markers")
    for k, (no, name, b) in built.items(): print(no, b.get('summary'))


if __name__ == '__main__':
    main()
