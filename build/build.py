"""Builds the 64 Stone Sheep Circle Contractor App and the Property App's house data.

    python3 plan/house.py      # only when the plan data changes
    python3 build/build.py     # sheets, schedules, packets, contractor/index.html, property/data/

Reads plan/house.json; writes
  contractor/index.html            the app (3D, A-1, S-1, E-1, P-1, M-1, R-1, the owner's plans, crew chat)
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
VERSION = 'v10'

import plan, framing, electrical, plumbing, hvac, radiant   # noqa: E402
import structure3d                                  # noqa: E402
from setlib import HOUSE, ft_in                     # noqa: E402
from climate import CLIMATE, ENVELOPE               # noqa: E402

SHEETS = [('a1', 'A-1', 'Plan', plan), ('s1', 'S-1', 'Framing', framing), ('e1', 'E-1', 'Electrical', electrical),
          ('p1', 'P-1', 'Plumbing', plumbing), ('m1', 'M-1', 'HVAC', hvac), ('r1', 'R-1', 'Radiant', radiant)]
esc = lambda t: html.escape(str(t), quote=True)


NUM = re.compile(r'^-?[\d$][\d,.\'"\- /x×]*( ?[A-Za-z/%]{1,6})?$')   # a number or measurement: set in mono, as on Zero Rd


def table_html(t, key):
    # Zero Rd schedule markup: a wide section per table, rows keyed by tag and focusable; the page script turns each
    # section into a tab of the schedule bar, adds search and one-tap type filters
    heads = ''.join(f'<th scope="col">{esc(c)}</th>' for c in t['cols'])
    body = []
    for rid, cells in t['rows']:
        tds = ''.join(f'<td class="{"num" if i and NUM.match(str(c).strip()) else ""}">{esc(c)}</td>' for i, c in enumerate(cells))
        body.append(f'<tr data-id="{esc(rid)}" tabindex="0">{tds}</tr>' if rid else f'<tr>{tds}</tr>')
    lede = f'<p class="lede">{esc(t["lede"])}</p>' if t.get('lede') else ''
    if t.get('feed'): lede += f'<p class="feed">{esc(t["feed"])}</p>'   # E-1: the panel's feed line above the circuit schedule
    return f'<section class="wide"><h3>{esc(t["title"])}</h3>{lede}<div class="tbl"><table><thead><tr>{heads}</tr></thead><tbody>{"".join(body)}</tbody></table></div></section>'


def summary_html(key, s):
    if not s: return ''
    labels = {
        's1': [('runs', 'wall runs'), ('ext_lf', 'lf exterior wall'), ('int_lf', 'lf interior wall'), ('studs', 'studs'), ('wall_board', 'sf wall board'), ('ceiling_board', 'sf ceiling board'), ('trusses', 'roof trusses')],
        'e1': [('devices', 'devices'), ('receptacles', 'receptacles'), ('lights', 'lights'), ('switches', 'switches'), ('circuits', 'circuits'), ('amps', 'A calculated load')],
        'p1': [('fixtures', 'fixtures'), ('dfu', 'DFU'), ('wsfu', 'WSFU'), ('stacks', 'stacks')],
        'r1': [('loops', 'loops'), ('tube_ft', 'ft of 1/2" PEX'), ('manifolds', 'manifolds'), ('house_heat', 'Btu/h house'), ('heat', 'Btu/h with the garage'), ('supply_f', '°F supply at design')],
        'm1': [('heat', 'Btu/h heating'), ('cool', 'Btu/h cooling'), ('units', 'outdoor units'), ('tons', 'tons of mini-split'), ('heads', 'wall heads')],
    }.get(key, [])
    items = ''.join(f'<li><b>{s[k]:,}</b> {esc(v)}</li>' if isinstance(s[k], int) else f'<li><b>{s[k]:g}</b> {esc(v)}</li>' for k, v in labels if k in s)
    return f'<ul class="summary">{items}</ul>'


PDF_ICON = ('<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true"><path d="M4 1.5h5.5L13 5v9.5H4z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/>'
            '<path d="M9.5 1.5V5H13M8.5 7.5v4.5M6.5 10l2 2 2-2" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>')
HINT = 'These zoom buttons are your friend.\nEverything you see is clickable.'


def sheet_section(key, no, name, b):
    # the Zero Rd sheet: toolbar (zoom, packet PDF, selection line), optional sub-tabs (E-1 circuit sheets), the drawing,
    # then Notes / Open items / schedules, which the page script turns into one pane at a time
    sh = b['sheet']
    notes = ''.join(f'<li>{esc(n)}</li>' for n in b['notes'])
    opens = ''.join(f'<li>{esc(n)}</li>' for n in b['open'])
    tables = ''.join(table_html(t, key) for t in b['tables'])
    legend = ''.join(f'<li><span class="sw" style="background:{esc(c)}"></span>{esc(t)}</li>' for c, t in b.get('legend', []))
    legend = f'<ul class="legend">{legend}</ul>' if legend else ''
    subtabs = b.get('subtabs_html', '')
    return f'''    <!-- ================================================================ {no} -->
    <div class="sheet sheet2d" id="sheet-{key}" data-key="{key}" role="tabpanel" aria-labelledby="tab-{key}" hidden>
      <div class="tools"><div class="zoom" role="group" aria-label="Zoom"><button type="button" data-zoom="1" aria-pressed="true">Fit</button><button type="button" data-zoom="2" aria-pressed="false">2×</button><button type="button" data-zoom="4" aria-pressed="false">4×</button></div><a class="packet" href="packets/{no}-{name.lower()}-packet.pdf" target="_blank" rel="noopener">{PDF_ICON}<span class="pk-name">{esc(name)} packet </span>PDF</a><p class="sel" data-hint="{esc(HINT)}">{esc(HINT)}</p></div>{subtabs}
      <div class="drawing"><div class="scroller"><div class="paper">{sh.svg()}</div></div></div>
      <div class="below">
        <section><h2>{no} {esc(sh.title)}</h2><p class="lede">{esc(sh.subtitle)}</p>{summary_html(key, b.get('summary'))}{legend}
          <h3>Notes</h3><ol>{notes}</ol></section>
        <section><h2>Open items</h2><p class="lede">The particulars to settle on this sheet.</p><div class="open"><ul>{opens}</ul></div></section>
        {tables}
      </div>
    </div>
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
    # E-1 devices are built by the model script's buildElectrical() from DATA.elec3d, P-1 pipes by buildPlumbing() from DATA.plumb3d
    return [], []


def radiant3d(r):
    # PEX loops, leaders and feed pairs at the slab, coloured by zone; manifolds and the heat source as markers
    return r['items'], r['lines']


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
    ri, rl = radiant3d(built['r1'][2]); items += ri; lines += rl
    house_lite = {k: HOUSE[k] for k in ('meta', 'rooms', 'windows', 'doors', 'fixtures', 'posts', 'walls', 'totals')}
    data = dict(house=house_lite, picks=picks, trade3d=items, lines3d=lines, struct3d=structure3d.build(built['s1'][2]), elec3d=built['e1'][2]['devices'], plumb3d=built['p1'][2]['plumb3d'], footprint=plumbing.OUTLINE, hvac3d=built['m1'][2]['hvac3d'])
    floor = plan.build()['sheet']
    floor.L['grid'] = []; floor.L['title'] = []; floor.L['tags'] = []
    floor_svg = base64.b64encode(floor.svg().encode()).decode()
    t = HOUSE['totals']; hv = built['m1'][2]['summary']; el = built['e1'][2]['summary']
    facts = [('Heated', f"{t['heated_gross_sf']:,} sq ft"), ('Garage', f"{t['garage_gross_sf']:,} sq ft"), ('Porch / patio', f"{t['porch_sf']} / {t['patio_sf']} sq ft"),
             ('Bedrooms', '3 + office'), ('Baths', '2 full + master + powder'), ('Ceilings', "9' · 4:12 vault"), ('Cooling', f"{hv['units']} mini-splits, {hv['heads']} heads"), ('Service', f"200 A ({el['amps']} A calc.)")]
    plans_html = []
    captions = [('A-1', 'First floor plan with room sizes and dimensions'), ('A-2', 'Roof plan over the floor plan: pitches, vaulted ceiling notes'), ('A-3', 'Site plan with the north arrow'),
                ('A-3', 'Front and rear elevations'), ('A-4', 'Left and right elevations'), ('A-5', 'Floor plan with fixtures, cabinets and appliances')]
    for i, (no, cap) in enumerate(captions, 1):
        plans_html.append(f'        <figure><a href="plans/sheet-{i}.jpg" target="_blank" rel="noopener"><img src="plans/sheet-{i}.jpg" alt="Owner\'s sheet {no}: {esc(cap)}" loading="lazy" width="2592" height="1728"></a><figcaption><b>{no}</b>{esc(cap)}</figcaption></figure>')
    sm = {k: (b.get('summary') or {}) for k, (no, name, b) in built.items()}
    counts = ' · '.join(f'{v:,} {label}' for v, label in [(len(HOUSE['walls']), 'wall segments'), (len(HOUSE['doors']), 'doors'), (len(HOUSE['windows']), 'windows'),
                                                          (sm['e1'].get('devices', 0), 'electrical devices'), (sm['p1'].get('fixtures', 0), 'plumbing fixtures')] if v)
    tpl = open(os.path.join(HERE, 'app_template.html')).read()
    page = (tpl.replace('{{VERSION}}', VERSION).replace('{{TABS}}', '\n'.join(tabs)).replace('{{SHEETS}}', ''.join(sections))
            .replace('{{PLANS}}', '\n'.join(plans_html)).replace('{{FACTS}}', ''.join(f'<dt>{esc(k)}</dt><dd>{esc(v)}</dd>' for k, v in facts))
            .replace('{{COUNTS}}', esc(counts)).replace('{{CUTMAX}}', f"{HOUSE['meta']['ceiling_ft'] + 0.5:g}")
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
