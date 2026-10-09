"""A-1 Plan: the owner's floor plan redrawn from plan/house.json, with the room schedule."""
from setlib import HOUSE, ROOMS, Sheet, ft_in, centroid


def build():
    sh = Sheet('A-1', 'Floor plan', 'Redrawn from the owner\'s A-1 and A-5 (Larson House, 6/11/26). Pick a room for its size and finishes.')
    sh.base(colour=True)
    picks, rows = {}, []
    meta = HOUSE['meta']
    for r in HOUSE['rooms']:
        cx, cy = centroid(r)
        if r['id'] == 'mud': cx, cy = 21.0, 33.6
        if r['id'] == 'garage': cx, cy = 15.5, 52.0
        if r['id'] == 'kitchen': cx, cy = 34.8, 20.5
        pts = ' '.join(f'{60 + x * 11:.1f},{60 + y * 11:.1f}' for x, y in r['poly'])
        sh.add(f'<g id="a1-{r["id"]}" class="sym room" data-id="{r["id"]}"><title>{r["name"]}</title><polygon points="{pts}" fill="#fff" fill-opacity="0" pointer-events="all"/></g>', 'disc')
        sh.items.append((r['id'], r['name']))
        ceiling = '4:12 vault (A-2)' if r['id'] in meta['vault']['rooms'] else '6:12 vaulted patio ceiling (A-2)' if r['id'] == 'patio' else f"{meta['ceiling_ft']:g}'-0\" flat" if r['kind'] != 'outdoor' else 'porch ceiling'
        doors = [d for d in HOUSE['doors'] if r['id'] in d['between'] and d['kind'] != 'glass']
        wins = [w for w in HOUSE['windows'] if w['room'] == r['id']]
        fx = [f for f in HOUSE['fixtures'] if f['room'] == r['id'] and f['kind'] not in ('cabinet',)]
        fields = [('A-1 size', r['label'] or '—'), ('A-1 area', f"{r['label_sf']} sq ft" if r['label_sf'] else '—'),
                  ('Measured', f"{r['area_sf']:.0f} sq ft between finished wall faces"), ('Ceiling', ceiling),
                  ('Doors', ', '.join(f"{d['id']} {d['name']}" for d in doors) or '—'), ('Windows', ', '.join(f"{w['id']} ({ft_in(w['w'])} x {ft_in(w['h'])})" for w in wins) or 'none'),
                  ('Fixtures', ', '.join(f['name'] for f in fx) or '—')]
        if r['id'] == 'living': fields.append(('Note', 'A-1 prints 17\'-4" wide; the walls measure about 20\'-5" and the printed 512 sq ft matches the wider figure.'))
        if r['id'] == 'bed3': fields.append(('Note', 'One window (W17, 4\'x4\'); check its sill for egress (≤ 44").'))
        if r['id'] == 'powder': fields.append(('Note', 'A-5 draws a toilet only; a sink is assumed on P-1.'))
        picks[r['id']] = dict(tag=r['name'], sub=r['kind'].title(), fields=fields)
        rows.append((r['id'], [r['name'], r['label'] or '—', str(r['label_sf'] or '—'), f"{r['area_sf']:.0f}", ceiling, str(len(wins)), ', '.join(d['id'] for d in doors) or '—']))
    # overall dimension strings, as A-1 prints them
    o = HOUSE['meta']['overall']
    sh.line(0, 72.3, 83.44, 72.3, '#3f3b35', 0.6); sh.text(41.7, 73.3, "83'-5 1/4\" overall", 7.5, '#3f3b35', '600', layer='base-lab')
    sh.line(85.3, 0, 85.3, 62.24, '#3f3b35', 0.6); sh.text(86.4, 31.0, "62'-2 15/16\"", 7.5, '#3f3b35', '600', rot=90, layer='base-lab')
    sh.line(-3.6, 0, -3.6, 70.09, '#3f3b35', 0.6)
    sh.text(-4.6, 52.0, "70'-1 1/16\"", 7.5, '#3f3b35', '600', rot=-90, layer='base-lab')
    t = HOUSE['totals']
    sh.title_block([f"About {t['heated_gross_sf']:,} sq ft heated (outside faces), garage {t['garage_gross_sf']:,} sq ft, porch {t['porch_sf']} sq ft, patio {t['patio_sf']} sq ft.",
                    '9\' ceilings; 4:12 vault over kitchen and living; 6:12 vaulted patio.', 'Roof: metal, 6:12 hips, 8:12 gables, 2:12 porch (A-2).',
                    'Board-and-batten siding, stone on the front garage gable.'])
    notes = [
        f"One story, {t['heated_gross_sf']:,} sq ft heated to the outside faces ({t['conditioned_room_sf']:,} sq ft of rooms between finished faces); two-car garage {t['garage_gross_sf']:,} sq ft; covered front porch {t['porch_sf']} sq ft; covered rear patio {t['patio_sf']} sq ft.",
        'Walls: 2x6 exterior, 2x4 interior, as drawn. Ceilings 9\' except the 4:12 vault over kitchen and living and the 6:12 vaulted patio ceiling (A-2).',
        'Roof: dark standing-seam metal; 6:12 main hips, 8:12 front gables, 2:12 shed over the front porch. Siding: tan vertical board-and-batten, stone veneer on the front garage gable, cedar-tone posts and an entry gable bracket (A-3).',
        'The room sizes printed on A-1 are kept in the schedule beside the measured areas; the plan\'s areas run a little larger than the measured ones, consistent with measuring to wall centers.',
        'Datum for every sheet in this app: X in feet from the outside of the garage-door wall, Y in feet from the outside of the master bedroom\'s rear wall.',
    ]
    open_items = [
        'Where the house is (address, lot, orientation): the site plan has a north arrow but no dimensions, setbacks or street.',
        'Sheet numbering: the site plan and the front/rear elevations are both A-3 on the owner\'s set.',
        'Living room width (17\'-4" printed vs. ~20\'-5" measured).',
        'Powder room sink, fireplace chimney route, bedroom 3 egress window.',
    ]
    tables = [dict(key='rooms', title='Room schedule', cols=['Room', 'A-1 size', 'A-1 sf', 'Measured sf', 'Ceiling', 'Windows', 'Doors'], rows=rows)]
    return dict(sheet=sh, picks=picks, tables=tables, notes=notes, open=open_items, summary={})
