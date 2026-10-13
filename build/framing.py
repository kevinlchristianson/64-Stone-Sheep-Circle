"""S-1 Framing: wall types, door and window rough openings, headers, blocking, the roof truss layout and the
lumber, sheathing and drywall take-offs.

Walls come from plan/house.json (the A-1 drawing's own wall rectangles), merged into runs across the door and
window gaps. Exterior walls are 2x6, interior 2x4, and the walls around the laundry are 2x6 plates with
staggered 2x4 studs (owner, 2026-10-13). Roof trusses (build/roof.py) bear on the exterior walls and a girder
truss, so every interior wall is a non-bearing partition.

Tags follow the Zero Rd S-1: walls are numbered red circles ("wall 12"), doors tan boxes (D#), windows blue
boxes (W#). Tags are placed clear of each other and of the room names.
"""
import math
from setlib import HOUSE, ROOMS, Sheet, ft_in, centroid, room_at, esc, px, py, S as SC
import roof

CEIL = HOUSE['meta']['ceiling_ft']
WET = {'wc', 'lav', 'tub', 'shower', 'washer', 'sink', 'dw'}
OPENINGS = [dict(o, otype='window') for o in HOUSE['windows']] + [dict(d, otype='door') for d in HOUSE['doors'] if d['kind'] != 'glass']
TYPES = {'E': '2x6 exterior', 'I': '2x4 partition', 'S': '2x6 plate, staggered 2x4 studs'}
COL = {'2x6 exterior': '#7a4f1d', '2x4 partition': '#b8762a', '2x6 plate, staggered 2x4 studs': '#3f8a45'}
WALL_TAG, DOOR_TAG, WIN_TAG, BLOCK = '#b4462f', '#b8762a', '#2c6aa0', '#c2369a'


def ftype(w):
    return 'S' if w.get('frame') == 'S' else w['kind']


def runs():
    """Merge the drawing's wall rectangles into runs along one line, across opening gaps."""
    groups = {}
    for w in HOUSE['walls']:
        horiz = (w['x1'] - w['x0']) >= (w['y1'] - w['y0'])
        s = dict(w, horiz=horiz)
        key = (ftype(w), horiz, round(s['y0'], 2), round(s['y1'], 2)) if horiz else (ftype(w), horiz, round(s['x0'], 2), round(s['x1'], 2))
        groups.setdefault(key, []).append(s)
    out = []
    for key, ss in groups.items():
        kind, horiz = key[0], key[1]
        ss.sort(key=lambda s: s['x0'] if horiz else s['y0'])
        cur = None
        for s in ss:
            a0, a1 = (s['x0'], s['x1']) if horiz else (s['y0'], s['y1'])
            if cur is not None:
                gap = (cur['a1'], a0)
                line = (key[2] + key[3]) / 2
                bridged = gap[1] - gap[0] < 0.1 or any(
                    o['axis'] == ('y' if horiz else 'x') and abs(o['at'] + o.get('t', 0) / 2 - line) < 0.6 and abs(o['span'][0] - gap[0]) < 0.4 and abs(o['span'][1] - gap[1]) < 0.4
                    for o in OPENINGS)
                if bridged:
                    cur['a1'] = max(cur['a1'], a1); continue
                out.append(cur)
            cur = dict(kind=kind, horiz=horiz, c0=key[2], c1=key[3], a0=a0, a1=a1)
        out.append(cur)
    for r in out:
        r['len'] = r['a1'] - r['a0']
        r['t'] = r['c1'] - r['c0']
        r['line'] = (r['c0'] + r['c1']) / 2
    out = [r for r in out if r['len'] > 0.4]
    # exterior first, then interior; each by position, rear to front, left to right
    out.sort(key=lambda r: (r['kind'] != 'E', round(r['line'] if r['horiz'] else r['a0'], 1), r['a0'] if r['horiz'] else r['line']))
    for i, r in enumerate(out, 1):
        r['n'] = i
        r['id'] = f'wall{i}'
        r['openings'] = [o for o in OPENINGS if o['axis'] == ('y' if r['horiz'] else 'x') and abs(o['at'] - r['line']) < 0.6
                         and o['span'][0] >= r['a0'] - 0.3 and o['span'][1] <= r['a1'] + 0.3]
        r['rooms'] = sides(r)
        r['wet'] = r['kind'] != 'E' and any(f['kind'] in WET and near(r, f) for f in HOUSE['fixtures'])
        r['type'] = TYPES[r['kind']]
        r['garage'] = 'garage' in r['rooms'] and any(n not in ('garage', 'outside', 'porch') for n in r['rooms'])
    return out


def near(r, f):
    x, y = f['at']; w, h = f['size']
    if r['horiz']:
        return r['a0'] - 0.2 <= x <= r['a1'] + 0.2 and min(abs(y - h / 2 - r['c1']), abs(y + h / 2 - r['c0'])) < 0.9
    return r['a0'] - 0.2 <= y <= r['a1'] + 0.2 and min(abs(x - w / 2 - r['c1']), abs(x + w / 2 - r['c0'])) < 0.9


def sides(r):
    names = []
    for frac in (0.25, 0.5, 0.75):
        a = r['a0'] + r['len'] * frac
        for off in (-0.4, r['t'] + 0.4):
            x, y = (a, r['c0'] + off) if r['horiz'] else (r['c0'] + off, a)
            rm = room_at(x, y)
            if not rm and r['kind'] != 'E': continue
            n = rm['id'] if rm else 'outside'
            if n not in names: names.append(n)
    return names


def ro_width(o):
    if o['otype'] == 'window': return o['w'] + 0.5 / 12
    if o['kind'] in ('overhead', 'opening'): return o['w']
    if o['kind'] == 'pocket': return 2 * o['w'] + 1 / 12
    if o['kind'] in ('french', 'double', 'bypass'): return o['w'] + 2 / 12
    return o['w'] + 2 / 12


def ro_head(o):
    """Top of the rough opening above the slab."""
    if o['otype'] == 'window': return o['head'] + 0.25 / 12
    if o['kind'] in ('overhead', 'opening'): return o['h']
    return o['h'] + 2.5 / 12


def header(o, ext):
    """Header by rough-opening width, and its depth in feet. With 8' heads under a 9'-1 1/8" plate there is 7-5/8"
    between the rough opening and the top plates, so exterior headers are 7-1/4" deep: 2-2x8 or LVL. Interior walls
    carry nothing (IRC R602.7.4): a flat 2x4."""
    ro = ro_width(o)
    if not ext: return 'flat 2x4, cripples at 16" (non-bearing)', 1.5 / 12, 1
    if ro <= 4.0: return '2-2x8 + 1/2" ply, 1 jack each end', 7.25 / 12, 1
    if ro <= 6.5: return '3-1/2" x 7-1/4" LVL (2-ply 1-3/4"), 2 jacks each end', 7.25 / 12, 2
    return '5-1/4" x 7-1/4" LVL (3-ply), 2 jacks each end; engineer to confirm', 7.25 / 12, 2


def rough(o):
    w, h = ro_width(o), ro_head(o) - (o.get('sill', 0) - 0.25 / 12 if o['otype'] == 'window' else 0)
    if o['otype'] == 'door':
        if o['kind'] == 'overhead': return f"{ft_in(w)} x {ft_in(h)} (door maker's RO)"
        if o['kind'] == 'opening': return f"{ft_in(w)} x {ft_in(h)} cased"
        if o['kind'] == 'pocket': return f"{ft_in(w)} x {ft_in(h)} (pocket frame)"
    return f"{ft_in(w)} x {ft_in(h)}"


def studs(r):
    """Stud count for a run: 16" o.c. (staggered: 12" o.c., alternating faces), +2 at each end for corners and T's,
    kings and jacks at each opening, less the studs the opening removes."""
    oc = 12 if r['kind'] == 'S' else 16
    n = math.ceil(r['len'] * 12 / oc) + 1 + 4
    for o in r['openings']:
        jacks = 2 * header(o, r['kind'] == 'E')[2]
        n += 2 + jacks - max(0, math.floor(ro_width(o) * 12 / oc) - 1)
    return max(n, 3)


# ---------------------------------------------------------------- tag placement: first free spot from a list of candidates
class Placer:
    def __init__(self):
        self.boxes = []

    def block(self, x0, y0, x1, y1): self.boxes.append((x0, y0, x1, y1))

    def place(self, cands, w, h, gap=0.25):
        for x, y in cands:
            b = (x - w / 2 - gap, y - h / 2 - gap, x + w / 2 + gap, y + h / 2 + gap)
            if all(b[2] <= c[0] or b[0] >= c[2] or b[3] <= c[1] or b[1] >= c[3] for c in self.boxes):
                self.boxes.append(b); return x, y
        x, y = cands[0]; self.boxes.append((x - w / 2, y - h / 2, x + w / 2, y + h / 2)); return x, y


def box_tag(sh, x, y, label, color, id, title, h=1.05, size=6):
    w = 0.42 * len(label) + 0.5
    sh.add(f'<g id="{sh.prefix}{esc(id)}" class="tag" data-id="{esc(id)}"><title>{esc(title)}</title>'
           f'<rect class="hit" x="{px(x - w / 2 - 0.3):.1f}" y="{py(y - h / 2 - 0.3):.1f}" width="{(w + 0.6) * SC:.1f}" height="{(h + 0.6) * SC:.1f}" fill="#fff" fill-opacity="0" pointer-events="all"/>'
           f'<rect x="{px(x - w / 2):.1f}" y="{py(y - h / 2):.1f}" width="{w * SC:.1f}" height="{h * SC:.1f}" rx="{2 if color == WIN_TAG else 0}" fill="#fff" stroke="{color}" stroke-width="1"/>'
           f'<text x="{px(x):.1f}" y="{py(y) + 0.4:.1f}" font-size="{size}" font-weight="700" fill="{color}" text-anchor="middle" dominant-baseline="middle">{esc(label)}</text></g>', 'tags')
    sh.items.append((id, title))
    return w


def blocking(R):
    """Blocking bands: grab bars at the toilets, tubs and showers; vanity tops and mirrors; the washer box; the TV
    at the fireplace. Each is a band on the wall face the fixture backs onto."""
    want = {'wc': ('Grab bars and paper holder', '2x8 flat between studs, 33"-36" AFF, plus 2x6 at 24" for the paper holder'),
            'shower': ('Grab bars, valve and bench', '2x8 at 33"-36" and 2x6 at 48" AFF on every wet wall; valve blocking per the valve'),
            'tub': ('Grab bars and valve', '2x8 at 33"-36" AFF along the tub and at the valve end'),
            'cabinet': ('Cabinets and vanity top', '2x6 at 34" AFF for the top or counter, 2x6 at 84" for wall cabinets or a mirror'),
            'washer': ('Washer box', '2x6 at 36"-48" AFF for the recessed washer box'),
            'fireplace': ('TV above the fireplace', '2x10 flat, 48"-72" AFF, centred on the insert')}
    out = []
    for f in HOUSE['fixtures']:
        if f['kind'] not in want or (f['kind'] == 'tub' and f['room'] == 'master_bath'): continue   # pedestal tub: none
        if f['kind'] == 'cabinet' and f['room'] not in ('master_bath', 'bath2', 'laundry', 'kitchen'): continue
        x, y = f['at']; w, h = f['size']
        fx0, fy0, fx1, fy1 = x - w / 2, y - h / 2, x + w / 2, y + h / 2
        for r in R:
            if r['horiz']:
                lo, hi = max(fx0, r['a0']), min(fx1, r['a1'])
                if hi - lo < 0.5: continue
                if abs(fy0 - r['c1']) < 0.6: face = r['c1']
                elif abs(fy1 - r['c0']) < 0.6: face = r['c0']
                else: continue
                band = (lo - 0.25, face, hi + 0.25, face)
            else:
                lo, hi = max(fy0, r['a0']), min(fy1, r['a1'])
                if hi - lo < 0.5: continue
                if abs(fx0 - r['c1']) < 0.6: face = r['c1']
                elif abs(fx1 - r['c0']) < 0.6: face = r['c0']
                else: continue
                band = (face, lo - 0.25, face, hi + 0.25)
            if f['kind'] in ('wc', 'cabinet', 'washer', 'fireplace') and any(b['fixture'] == f['id'] for b in out): continue
            what, how = want[f['kind']]
            out.append(dict(fixture=f['id'], name=f['name'], room=f['room'], wall=r['n'], band=band, what=what, how=how, len=hi - lo + 0.5))
    return out


def build():
    R = runs()
    T = roof.build()
    sh = Sheet('S-1', 'Framing', 'Wall types, rough openings, headers, blocking and the roof truss layout. Walls numbered from 1, exterior first.')
    sh.base()
    picks, wall_rows, door_rows, win_rows = {}, [], [], []
    pl = Placer()
    # keep tags off the room names
    for r in HOUSE['rooms']:
        if r['area_sf'] < 12: continue
        cx, cy = centroid(r)
        cx, cy = {'mud': (21.0, 33.6), 'garage': (15.5, 52.0), 'kitchen': (34.8, 20.5)}.get(r['id'], (cx, cy))
        w = len(r['name']) * 0.5
        pl.block(cx - w / 2, cy - 1.0, cx + w / 2, cy + 0.1)
    BL = blocking(R)
    for b in BL:
        x0, y0, x1, y1 = b['band']
        sh.line(x0, y0, x1, y1, BLOCK, 2.2, '4,2', layer='disc-lab')
    for r in R:
        x0, y0, x1, y1 = (r['a0'], r['c0'], r['a1'], r['c1']) if r['horiz'] else (r['c0'], r['a0'], r['c1'], r['a1'])
        st = studs(r)
        rooms = ', '.join(ROOMS[n]['name'] if n in ROOMS else 'outside' for n in r['rooms'])
        ops = ', '.join(o['id'] for o in r['openings'])
        notes = []
        if r['garage']: notes.append('garage separation: 5/8" Type X on the garage side, seal penetrations')
        if r['kind'] == 'S': notes.append('sound wall: 2x6 plates, 2x4 studs alternating faces at 12" o.c. (24" o.c. each face), R-15 batt woven between, no stud touches both faces; grown 2" into the laundry')
        if r['kind'] == 'S' and any(o['kind'] == 'pocket' for o in r['openings']): notes.append('the pocket door D11 needs a 2x6 pocket frame here')
        if r['wet'] and r['kind'] == 'I': notes.append('plumbing wall, 2x4 (owner): 3" drains and vents bored through plates get a steel strap across the cut (IRC R602.6.1)')
        if r['kind'] == 'E': notes.append('PT bottom plate on the slab, sill gasket, 1/2" anchor bolts at 6\' o.c. and 12" from ends')
        bl = [b for b in BL if b['wall'] == r['n']]
        if bl: notes.append('blocking: ' + ', '.join(f"{b['what'].lower()} ({b['name']})" for b in bl))
        title = f"Wall {r['n']} · {r['type']} · {ft_in(r['len'])}"
        oc_txt = '12" o.c. staggered' if r['kind'] == 'S' else '16" o.c.'
        sh.open_group(r['id'], title)
        sh.rect(x0, y0, x1, y1, COL[r['type']], 'none', 0, layer='disc', extra=' fill-opacity="0.9"')
        sh.close_group()
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        # candidates: on the wall line at its middle, then along it, then just off either face
        cands = []
        for f in (0.5, 0.35, 0.65, 0.2, 0.8):
            a = r['a0'] + r['len'] * f
            cands.append((a, r['line']) if r['horiz'] else (r['line'], a))
        for f in (0.5, 0.3, 0.7):
            a = r['a0'] + r['len'] * f
            for off in (-0.95, 0.95):
                cands.append((a, r['line'] + off) if r['horiz'] else (r['line'] + off, a))
        if r['len'] < 1.5: cands = cands[5:] + cands[:5]
        tx, ty = pl.place(cands, 1.2, 1.2, 0.15)
        sh.tag(tx, ty, str(r['n']), WALL_TAG, r=0.6, size=6.5)
        picks[r['id']] = dict(tag=f"Wall {r['n']}", sub=r['type'], fields=[('Length', ft_in(r['len'])), ('Height', f"9'-1 1/8\" plate: PT plate, 104-5/8\" precut studs, double top plate (9' ceilings; the vault is in the trusses)"),
                                                                       ('Between', rooms), ('Openings', ops or 'none'), ('Studs', f"{st} ({oc_txt})"), ('Notes', '; '.join(notes) or '—')])
        wall_rows.append((r['id'], [str(r['n']), r['type'], ft_in(r['len']), rooms, ops or '—', str(st), '; '.join(notes) or '—']))
    for o in OPENINGS:
        a, (s0, s1) = o['at'], o['span']
        host = next((r for r in R if o in r['openings']), None)
        ext = bool(host and host['kind'] == 'E') or o.get('ext', False) or o['otype'] == 'window'
        hd = header(o, ext)[0]
        t = (host['t'] if host else 0.3)
        line = host['line'] if host else a + t / 2
        mid = (s0 + s1) / 2
        if o['otype'] == 'window':
            rm = ROOMS[o['room']]['name']
            title = f"{o['id']} · window {ft_in(o['w'])} x {ft_in(o['h'])} · {rm}"
            egress = ''
            if ROOMS[o['room']]['kind'] == 'bed' and o['room'] != 'office':
                egress = f"Bedroom: needs 5.7 sf net opening, 20\" clear width, 24\" clear height, sill ≤ 44\" (sill here {ft_in(o['sill'])}{' — too high' if o['sill'] > 44 / 12 else ''})"
            # outside the exterior wall
            probe = room_at(mid, line - 1.0) if o['axis'] == 'y' else room_at(line - 1.0, mid)
            out_dir = -1 if probe is None or probe['kind'] == 'outdoor' else 1
            cands = []
            for d in (1.3, 2.4):
                for sh_ in (0, -1.2, 1.2):
                    cands.append((mid + sh_, line + out_dir * d) if o['axis'] == 'y' else (line + out_dir * d, mid + sh_))
            tx, ty = pl.place(cands, 0.42 * len(o['id']) + 0.5, 1.05)
            box_tag(sh, tx, ty, o['id'], WIN_TAG, o['id'], title)
            fields = [('Room', rm), ('Unit', f"{ft_in(o['w'])} wide x {ft_in(o['h'])} tall (scaled from the elevations)"), ('Rough opening', rough(o)),
                      ('Head / sill', f"{ft_in(o['head'])} / {ft_in(o['sill'])} above slab"), ('Header', hd), ('Wall', f"wall {host['n']}" if host else '—')]
            if egress: fields.append(('Egress', egress))
            picks[o['id']] = dict(tag=o['id'], sub='Window · ' + rm, fields=fields)
            win_rows.append((o['id'], [o['id'], rm, f"{ft_in(o['w'])} x {ft_in(o['h'])}", rough(o), f"{ft_in(o['head'])} / {ft_in(o['sill'])}", hd, egress or '—']))
        else:
            kinds = {'entry': 'exterior entry door', 'french': 'French door pair', 'exterior': 'exterior door', 'overhead': 'overhead garage door', 'fire': '20-min fire-rated, self-closing', 'double': 'door pair',
                     'swing': 'swing door', 'opening': 'cased opening', 'pocket': 'pocket door', 'bypass': 'bypass (sliding) pair'}
            between = ' / '.join(ROOMS[b]['name'] if b in ROOMS else 'outside' for b in o['between'])
            title = f"{o['id']} · {o['name']} · {kinds[o['kind']]} {ft_in(o['w'])}"
            cands = []
            for d in (1.05, -1.05, 1.9, -1.9):
                for sh_ in (0, -0.9, 0.9):
                    cands.append((mid + sh_, line + d) if o['axis'] == 'y' else (line + d, mid + sh_))
            tx, ty = pl.place(cands, 0.42 * len(o['id']) + 0.5, 1.05)
            box_tag(sh, tx, ty, o['id'], DOOR_TAG, o['id'], title)
            fields = [('Door', f"{o['name']} ({kinds[o['kind']]})"), ('Between', between), ('Leaf', f"{ft_in(o['w'])} x {ft_in(o['h'])}" + (f", {o.get('leaves')} leaves" if o.get('leaves') else '')),
                      ('Rough opening', rough(o)), ('Header', hd), ('Wall', f"wall {host['n']}" if host else '—')]
            if o['kind'] == 'fire': fields.append(('Code', 'Garage to house: solid wood or steel ≥ 1-3/8", or 20-minute rated, self-closing and self-latching (IRC R302.5.1)'))
            if o['id'] == 'D7': fields.append(('Code', 'Opens from the garage: rate like D6 if the closet counts as part of the house; combustion air per the appliance that goes in'))
            picks[o['id']] = dict(tag=o['id'], sub=o['name'], fields=fields)
            door_rows.append((o['id'], [o['id'], o['name'], kinds[o['kind']], f"{ft_in(o['w'])} x {ft_in(o['h'])}", rough(o), hd, between]))
    # legend, in the strip under the plan (as the Zero Rd S-1)
    bar = lambda c: f'<rect x="-9" y="-3" width="18" height="6" fill="{c}"/>'
    sh.legend([(bar(COL['2x6 exterior']), '2x6 exterior @ 16"'), (bar(COL['2x4 partition']), '2x4 partition @ 16"'),
               (bar(COL['2x6 plate, staggered 2x4 studs']), '2x6 plate, staggered 2x4 studs'),
               (f'<line x1="-9" y1="0" x2="9" y2="0" stroke="{BLOCK}" stroke-width="2.2" stroke-dasharray="4,2"/>', 'blocking band'),
               (f'<circle r="6" fill="#fff" stroke="{WALL_TAG}"/>', 'wall #'), (f'<rect x="-7" y="-5" width="14" height="10" fill="#fff" stroke="{DOOR_TAG}"/>', 'D# door, rough opening'),
               (f'<rect x="-7" y="-5" width="14" height="10" rx="2" fill="#fff" stroke="{WIN_TAG}"/>', 'W# window'),
               ('<circle r="6" fill="#fff" stroke="#2c6aa0" stroke-width="1.1"/><path d="M-6,0 a6,6 0 0 1 6,-6 v6 z M6,0 a6,6 0 0 1 -6,6 v-6 z" fill="#2c6aa0"/>', '0,0 datum, grid 5\'')])

    # take-offs
    ext = [r for r in R if r['kind'] == 'E']; inte = [r for r in R if r['kind'] != 'E']
    lf = lambda rs: sum(r['len'] for r in rs)
    op_area = lambda rs: sum(o['w'] * o['h'] for r in rs for o in r['openings'] if o.get('kind') != 'overhead')
    ext_lf, int_lf, stag_lf = lf(ext), lf([r for r in inte if r['kind'] == 'I']), lf([r for r in inte if r['kind'] == 'S'])
    house_ext = [r for r in ext if 'garage' not in r['rooms']]
    wall_board = lf(house_ext) * CEIL - op_area(house_ext) + 2 * (lf(inte) * CEIL) - 2 * op_area(inte)
    heated = [r for r in HOUSE['rooms'] if r['kind'] not in ('garage', 'outdoor')]
    vault = [r for r in heated if r['id'] in HOUSE['meta']['vault']['rooms']]
    ceil_flat = sum(r['area_sf'] for r in heated if r not in vault)
    ceil_vault = sum(r['area_sf'] for r in vault) * math.hypot(12, 4) / 12
    tub_shower_backer = (4 + 6 + 6) * 8 + (5.1 + 3.37 * 2) * 8 + (5.5 + 2.73) * 6   # shower walls to 8', tub surround to 6'
    garage_x = lf([r for r in R if r['garage']]) * CEIL + HOUSE['totals']['garage_sf']
    studs_total = sum(studs(r) for r in R)
    plates = {'2x6': 3 * (ext_lf + stag_lf), '2x4': 3 * int_lf}
    takeoff_rows = [
        (None, ['Exterior wall, 2x6', f'{ext_lf:,.0f} lf', f'{sum(studs(r) for r in ext)} studs 2x6 104-5/8" precut (9\'-1 1/8" plate)', 'PT 2x6 bottom plate + double top plate']),
        (None, ['Partitions, 2x4', f'{int_lf:,.0f} lf', f'{sum(studs(r) for r in inte if r["kind"] == "I")} studs 2x4 precut', 'PT bottom plate on slab']),
        (None, ['Laundry sound walls', f'{stag_lf:,.0f} lf', f'{sum(studs(r) for r in inte if r["kind"] == "S")} studs 2x4 precut on 2x6 plates', 'R-15 batt woven between the faces']),
        (None, ['Plates', f"2x6: {plates['2x6']:,.0f} lf · 2x4: {plates['2x4']:,.0f} lf", 'one bottom, two top', 'buy 16\' lengths: ' + f"{math.ceil(plates['2x6'] / 16 * 1.1)} x 2x6, {math.ceil(plates['2x4'] / 16 * 1.1)} x 2x4 (10% waste)"]),
        (None, ['Wall sheathing', f'{(lf(ext) * (CEIL + 1) - op_area(ext)) / 32 * 1.1:,.0f} sheets 7/16" OSB 4x8', 'exterior walls incl. garage, rim to top plate, 10% waste', 'plus housewrap']),
        (None, ['Blocking', f"{sum(b['len'] for b in BL):,.0f} lf of bands", f"{len(BL)} bands (blocking schedule)", '2x6 to 2x10 offcuts']),
        (None, ['Roof trusses', f"{T['summary']['trusses']} trusses", 'roof framing schedule below', 'priced by the truss maker from their layout']),
        (None, ['Patio and porch rafters', f"{T['summary']['rafters']} rafters", '2x10 patio, 2x8 porch, at 24" o.c.', 'plus beams, ledger and hangers']),
        (None, ['Drywall, walls', f'{wall_board:,.0f} sf · {math.ceil(wall_board / 48 * 1.1)} sheets 1/2" 4x12', 'house walls, both faces of partitions, less openings', '']),
        (None, ['Drywall, ceilings', f'{ceil_flat + ceil_vault:,.0f} sf · {math.ceil((ceil_flat + ceil_vault) / 48 * 1.1)} sheets 5/8" ceiling board 4x12', f'flat {ceil_flat:,.0f} sf + vault {ceil_vault:,.0f} sf (4:12)', 'trusses at 24" o.c.: 5/8" board']),
        (None, ['Drywall, garage', f'{garage_x:,.0f} sf · {math.ceil(garage_x / 48 * 1.1)} sheets 5/8" Type X 4x12', 'walls to the house and the ceiling', 'tape and seal for the house separation']),
        (None, ['Tile backer', f'{tub_shower_backer:,.0f} sf cement board', 'two showers to 8\', tub surround to 6\'', 'pedestal tub needs none']),
        (None, ['Studs, total', f'{studs_total:,} pcs', 'kings, jacks and corners included', 'add 10% for blocking and waste']),
    ]
    block_rows = [(None, [f"wall {b['wall']}", ROOMS[b['room']]['name'], b['name'], b['what'], b['how']]) for b in sorted(BL, key=lambda b: b['wall'])]
    notes = [
        'Datum 0,0 (blue target, top left of the drawing): where the outside face of the garage-door wall (X = 0) meets the line of the outside face of the master bedroom\'s rear wall (Y = 0). It is the rear-left corner of the layout string lines, not a wall corner: set it from those two lines. The grid is 5\'-0" each way from it; X runs to the right (toward the bedroom wing), Y toward the front (the porch). Every sheet uses it.',
        'Walls: 2x6 exterior, 2x4 interior (owner, 2026-10-13), drawn at stud depth (5-1/2" and 3-1/2"). Plumbing walls are 2x4 like the rest; where a 3" drain or vent goes through a plate, strap it (IRC R602.6.1).',
        'Laundry sound walls (green, owner 2026-10-13): 2x6 plates with 2x4 studs alternating faces at 12" o.c. (24" o.c. on each face), R-15 batt woven between, no stud touching both faces. They grow 2" into the laundry, so the master bedroom, master closet, mud room, master hall and powder room keep their A-1 sizes; the laundry is 2" smaller each way. D11 needs a 2x6 pocket frame.',
        'Plate height 9\'-1 1/8" (PT plate, 104-5/8" precut studs, double top plate) for 9\'-0" ceilings. The kitchen and living vault is in the trusses (4:12 scissor bottom chords); no wall runs past the plate.',
        'Headers: with 8\' heads there is 7-5/8" between the rough opening and the top plates, so exterior headers are 7-1/4" deep: 2-2x8 up to a 4\' opening, LVL above that (the two 9\' garage doors and the 8\' patio French doors: engineer to confirm, or raise the plate). Interior walls carry no roof: a flat 2x4 header with cripples (IRC R602.7.4).',
        'Roof: trusses at 24" o.c. bearing on the exterior walls (roof framing schedule). The main trusses span front to rear on the A-2 ridge line; a 2-ply girder truss (G1) on the master-wing/kitchen line carries the master wing and garage trusses, so the wall under it is a partition. Hang every partition top plate with slip clips (no nails into the bottom chords) so truss uplift doesn\'t crack the ceilings.',
        'Door rough openings: leaf + 2" wide, + 2-1/2" tall; pockets 2 x leaf + 1". Window rough openings: unit + 1/2" each way (confirm with the window maker).',
        'Garage separation: 5/8" Type X on the garage side of the walls to the house and on the garage ceiling; D6 is a 20-minute self-closing door.',
        'Blocking (magenta): the bands on the drawing and the blocking schedule; grab-bar blocking at every toilet, tub and shower; vanity tops and mirrors, the washer box, the TV over the fireplace.',
    ]
    open_items = [
        'Datum: confirm the 0,0 layout corner with the surveyor\'s pins before the forms go in.',
        'Window sizes and heights are scaled from the elevations; confirm the window schedule with the supplier before framing.',
        f"Bedroom 3's only window (W17, 4'x4') scales with a {ft_in(4.0)} sill: above the 44\" egress limit. Lower it or use a casement sized for egress.",
        'Interior door heights are not on the plans (8\'-0" assumed to match the exterior doors on the elevations).',
        'Roof trusses: the layout here is a draft from A-2. The truss maker designs the trusses, the hip and valley sets, the G1 girder and its end posts, and the over-framed 8:12 gables at the entry and office.',
        'Heel: 12" energy heel assumed (full R-49 to the wall line); it sets the eave height on the elevations.',
        'Fireplace insert: chimney chase framing through the vaulted living ceiling and roof; clearances per the insert\'s manual.',
        'Living room label on A-1 says 17\'-4" wide; the walls measure about 20\'-5". Framing follows the walls.',
        'Foundation (slab assumed: the garage and mechanical floor drains, the radiant slab), thickened footings under G1\'s end posts and the patio and porch posts, anchor schedule.',
    ]
    sh.title_block(['Exterior 2x6 (brown), partitions 2x4 (tan), laundry sound walls 2x6 plate with staggered 2x4 studs (green).',
                    'Tags: wall numbers in red circles, doors in tan boxes, windows in blue.', 'Roof trusses bear on the exterior walls and girder G1; every interior wall is non-bearing.'])
    tables = [
        dict(key='walls', title='Wall schedule', cols=['Wall', 'Type', 'Length', 'Between', 'Openings', 'Studs', 'Notes'], rows=wall_rows),
        dict(key='doors', title='Door schedule', cols=['Door', 'Name', 'Type', 'Leaf', 'Rough opening', 'Header', 'Between'], rows=door_rows),
        dict(key='windows', title='Window schedule', cols=['Window', 'Room', 'Unit', 'Rough opening', 'Head / sill', 'Header', 'Egress'], rows=win_rows),
        dict(key='roof', title='Roof framing schedule', lede='Draft truss layout from A-2 (see the 3D model\'s roof trusses layer). Stations are feet from the datum. The truss maker designs the final layout.',
             cols=['Mark', 'Roof', 'Type', 'Span', 'Pitch', 'Peak above slab', 'Count', 'Where'], rows=T['rows']),
        dict(key='blocking', title='Blocking schedule', cols=['Wall', 'Room', 'Fixture', 'For', 'Blocking'], rows=block_rows),
        dict(key='takeoff', title='Lumber, sheathing and drywall', lede='Rough-order quantities from the wall data, for pricing. The framer takes off the final list.', cols=['Item', 'Quantity', 'Basis', 'Notes'], rows=takeoff_rows),
    ]
    summary = dict(ext_lf=round(ext_lf), int_lf=round(int_lf + stag_lf), studs=studs_total, wall_board=round(wall_board), ceiling_board=round(ceil_flat + ceil_vault), runs=len(R),
                   trusses=T['summary']['trusses'])
    legend = [(COL['2x6 exterior'], '2x6 exterior @ 16"'), (COL['2x4 partition'], '2x4 partition @ 16"'), (COL['2x6 plate, staggered 2x4 studs'], '2x6 plate, staggered 2x4 studs (laundry)'), (BLOCK, 'blocking')]
    return dict(sheet=sh, legend=legend, picks=picks, tables=tables, notes=notes, open=open_items, summary=summary, runs=R, roof=T, blocking=BL)


if __name__ == '__main__':
    b = build()
    print(b['summary'])
    for r in b['runs']:
        print(r['n'], r['type'], round(r['len'], 2), r['rooms'], [o['id'] for o in r['openings']])
