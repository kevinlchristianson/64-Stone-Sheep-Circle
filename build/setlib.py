"""SVG sheet library for the 64 Stone Sheep Circle build set.

Datum is plan/house.json's: feet, X to the right and Y down the sheet as A-1
is drawn (front porch at the bottom, garage on the left). 11 px per foot with
60/60 px margins; every sheet has the same plan position, so they overlay.

A Sheet draws the house in grey as a base, then a trade draws its layer in
colour on top. Clickable things are <g class="sym"> or tagged circles with a
data-id; the page script reads those to show the picked item's schedule row.
"""
import json, os, html, math

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HOUSE = json.load(open(os.path.join(ROOT, 'plan', 'house.json')))
ROOMS = {r['id']: r for r in HOUSE['rooms']}

S, MX, MY = 11.0, 60, 60
PW, PH = 84.0, 71.0                     # plan extents in feet
TB = 230                                # title block width, px


def px(x): return MX + x * S
def py(y): return MY + y * S


def ft_in(v):
    """feet -> 12'-3 1/2" """
    neg = v < 0; v = abs(v)
    f = int(v + 1e-9); i = round((v - f) * 24) / 2
    if i >= 12: f, i = f + 1, i - 12
    ins = (f'{int(i)}' if i == int(i) else f'{int(i)} 1/2' if int(i) else '1/2')
    s = f"{f}'-{ins}\"" if f else f'{ins}"'
    return ('-' if neg else '') + s


def esc(t): return html.escape(str(t), quote=True)


def centroid(room):
    p = room['poly']; a = cx = cy = 0.0
    for i in range(len(p)):
        x0, y0 = p[i]; x1, y1 = p[(i + 1) % len(p)]
        c = x0 * y1 - x1 * y0; a += c; cx += (x0 + x1) * c; cy += (y0 + y1) * c
    a /= 2
    return (cx / (6 * a), cy / (6 * a))


def bbox(room):
    xs = [p[0] for p in room['poly']]; ys = [p[1] for p in room['poly']]
    return min(xs), min(ys), max(xs), max(ys)


def inside(room, x, y):
    p = room['poly']; c = False
    for i in range(len(p)):
        x0, y0 = p[i]; x1, y1 = p[(i + 1) % len(p)]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0: c = not c
    return c


def room_at(x, y):
    for r in HOUSE['rooms']:
        if inside(r, x, y): return r
    return None


ROOM_FILL = {'bed': '#f3efe6', 'bath': '#e3eef5', 'closet': '#efece6', 'hall': '#f6f4ef', 'laundry': '#e8f0f2',
             'kitchen': '#f6ede0', 'living': '#f7f1e6', 'mech': '#ece6ea', 'garage': '#ececec', 'outdoor': '#eef2e8'}

LAYERS = ['page', 'rooms', 'grid', 'walls', 'openings', 'fix', 'base-lab', 'disc', 'disc-lab', 'tags', 'title']


class Sheet:
    def __init__(self, number, title, subtitle=''):
        self.number, self.title, self.subtitle = number, title, subtitle
        self.L = {k: [] for k in LAYERS}
        self.items = []
        self.prefix = number.replace('-', '').lower() + '-'
        self.width = int(MX * 2 + PW * S + TB)
        self.height = int(MY * 2 + PH * S)

    def add(self, s, layer='disc'): self.L[layer].append(s)

    # ------------------------------------------------------------ primitives (feet in, svg out)
    def rect(self, x0, y0, x1, y1, fill='none', stroke='none', sw=1, dash=None, layer='disc', extra=''):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        self.add(f'<rect x="{px(min(x0, x1)):.1f}" y="{py(min(y0, y1)):.1f}" width="{abs(x1 - x0) * S:.1f}" height="{abs(y1 - y0) * S:.1f}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}{extra}/>', layer)

    def line(self, x0, y0, x1, y1, color='#444', w=1, dash=None, layer='disc', extra=''):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        self.add(f'<line x1="{px(x0):.1f}" y1="{py(y0):.1f}" x2="{px(x1):.1f}" y2="{py(y1):.1f}" stroke="{color}" stroke-width="{w}"{d}{extra}/>', layer)

    def path(self, pts, color='#444', w=1, dash=None, layer='disc', fill='none', close=False, extra=''):
        d = ' '.join(f'{"M" if i == 0 else "L"}{px(x):.1f},{py(y):.1f}' for i, (x, y) in enumerate(pts)) + (' Z' if close else '')
        da = f' stroke-dasharray="{dash}"' if dash else ''
        self.add(f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"{da}{extra}/>', layer)

    def circle(self, x, y, r, fill='none', stroke='#444', sw=1, layer='disc', extra=''):
        self.add(f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="{r * S:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{extra}/>', layer)

    def text(self, x, y, t, size=9, color='#333', weight='normal', anchor='middle', rot=0, layer='disc-lab', extra=''):
        tr = f' transform="rotate({rot} {px(x):.1f} {py(y):.1f})"' if rot else ''
        self.add(f'<text x="{px(x):.1f}" y="{py(y):.1f}" font-size="{size}" font-weight="{weight}" fill="{color}" '
                 f'text-anchor="{anchor}" dominant-baseline="middle"{tr}{extra}>{esc(t)}</text>', layer)

    def open_group(self, id, title, layer='disc', hit=None, cls='sym', attrs=''):
        self.add(f'<g id="{self.prefix}{esc(id)}" class="{cls}" data-id="{esc(id)}"{attrs}><title>{esc(title)}</title>', layer)
        if hit: self.add(f'<circle class="hit" cx="{px(hit[0]):.1f}" cy="{py(hit[1]):.1f}" r="{hit[2] * S:.1f}" fill="#fff" fill-opacity="0" pointer-events="all"/>', layer)
        self.items.append((id, title))

    def close_group(self, layer='disc'): self.add('</g>', layer)

    def tag(self, x, y, label, color='#b4462f', id=None, title=None, r=0.55, size=7, layer='tags'):
        ex = f' id="{self.prefix}{esc(id)}" class="tag" data-id="{esc(id)}"' if id else ''
        t = f'<title>{esc(title)}</title>' if title else ''
        hit = f'<circle class="hit" cx="{px(x):.1f}" cy="{py(y):.1f}" r="{max(r, 0.9) * S:.1f}" fill="#fff" fill-opacity="0" pointer-events="all"/>' if id else ''
        self.add(f'<g{ex}>{t}{hit}<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="{r * S:.1f}" fill="#fff" stroke="{color}" stroke-width="1"/>'
                 f'<text x="{px(x):.1f}" y="{py(y) + 0.4:.1f}" font-size="{size}" font-weight="700" fill="{color}" text-anchor="middle" dominant-baseline="middle">{esc(label)}</text></g>', layer)
        if id: self.items.append((id, title or label))

    # ------------------------------------------------------------ the house, in grey (or colour on A-1)
    def base(self, colour=False, fixtures=True, labels=True, grid=True):
        self.add('<rect width="100%" height="100%" fill="#fff"/>', 'page')
        for r in HOUSE['rooms']:
            fill = ROOM_FILL.get(r['kind'], '#fff') if colour else ('#f4f5f1' if r['kind'] == 'outdoor' else '#fbfbfa')
            pts = ' '.join(f'{px(x):.1f},{py(y):.1f}' for x, y in r['poly'])
            if r['kind'] == 'outdoor':
                self.add(f'<polygon points="{pts}" fill="{fill}" stroke="#9aa08f" stroke-width="0.8" stroke-dasharray="4,3"/>', 'rooms')
            else:
                self.add(f'<polygon points="{pts}" fill="{fill}"/>', 'rooms')
        if grid:
            for x in range(0, 85, 5):
                self.line(x, -1.2, x, 71, '#d3dbe4', 0.5, '2,3', layer='grid'); self.text(x, -2.2, str(x), 6.5, '#7b93ad', layer='grid')
            for y in range(0, 71, 5):
                self.line(-1.2, y, 84, y, '#d3dbe4', 0.5, '2,3', layer='grid'); self.text(-2.6, y, str(y), 6.5, '#7b93ad', layer='grid')
        wc = '#3f3b35' if colour else '#77726a'
        for w in HOUSE['walls']:
            fill = ('#8a9bb4' if w['kind'] == 'E' else '#d9c56a') if colour else ('#9b968d' if w['kind'] == 'E' else '#c3beb5')
            self.rect(w['x0'], w['y0'], w['x1'], w['y1'], fill, wc, 0.6, layer='walls')
        for x, y in HOUSE['posts']:
            self.rect(x - 0.33, y - 0.33, x + 0.33, y + 0.33, '#fff', wc, 0.8, layer='walls')
        self.openings(colour)
        if fixtures:
            for f in HOUSE['fixtures']:
                self.fixture(f, '#8a5a44' if colour else '#b6afa5')
        if labels:
            for r in HOUSE['rooms']:
                if r['area_sf'] < 12: continue
                cx, cy = centroid(r)
                if r['id'] == 'mud': cx, cy = 21.0, 33.6
                if r['id'] == 'garage': cx, cy = 15.5, 52.0
                if r['id'] == 'kitchen': cx, cy = 34.8, 20.5
                self.text(cx, cy - 0.5, r['name'].upper(), 7.5 if r['area_sf'] > 40 else 6, '#4d4842' if colour else '#8f897f', '600', layer='base-lab')
                if colour and r.get('label'):
                    self.text(cx, cy + 0.7, r['label'], 6.5, '#6f685d', layer='base-lab')

    def openings(self, colour):
        for w in HOUSE['windows']:
            a, (s0, s1) = w['at'], w['span']; t = 0.46
            if w['axis'] == 'y':
                self.rect(s0, a, s1, a + t, '#fff', '#3c6e9e' if colour else '#8f8a82', 0.6, layer='openings')
                self.line(s0, a + t / 2, s1, a + t / 2, '#3c6e9e' if colour else '#8f8a82', 0.8, layer='openings')
            else:
                self.rect(a, s0, a + t, s1, '#fff', '#3c6e9e' if colour else '#8f8a82', 0.6, layer='openings')
                self.line(a + t / 2, s0, a + t / 2, s1, '#3c6e9e' if colour else '#8f8a82', 0.8, layer='openings')
        for d in HOUSE['doors']:
            self.door(d, '#3f3b35' if colour else '#9a948a')

    def door(self, d, color):
        a, (s0, s1) = d['at'], d['span']; k = d['kind']
        t = 0.46 if d.get('ext') else 0.293
        if k == 'glass':
            self.line(a, s0, a, s1, '#6aa6c8', 1.4, layer='openings'); return
        # clear the wall
        if d['axis'] == 'y':
            self.rect(s0, a - 0.02, s1, a + t + 0.02, '#fff', layer='openings')
        else:
            self.rect(a - 0.02, s0, a + t + 0.02, s1, '#fff', layer='openings')
        if k in ('opening',):
            return
        if k == 'overhead':
            self.rect(a + 0.6, s0, a + 1.0, s1, 'none', color, 0.7, '3,2', layer='openings'); return
        if k in ('bypass', 'pocket'):
            if d['axis'] == 'y':
                self.line(s0, a + 0.08, (s0 + s1) / 2 + 0.2, a + 0.08, color, 1.2, layer='openings')
                self.line((s0 + s1) / 2 - 0.2, a + t - 0.08, s1, a + t - 0.08, color, 1.2, layer='openings')
            else:
                self.line(a + t / 2, s0, a + t / 2, s1, color, 1.2, '3,2', layer='openings')
            return
        # swings: hinge at the span's start, into the named room
        into = ROOMS.get(d.get('into'))
        leaves = d.get('leaves', 1)
        spans = [(s0, s1)] if leaves == 1 else [(s0, (s0 + s1) / 2), (s1, (s0 + s1) / 2)]
        for h, e in spans:
            L = abs(e - h)
            if d['axis'] == 'y':
                side = -1 if into is None or centroid(into)[1] < a else 1
                y0 = a if side < 0 else a + t
                hx, hy, ox, oy = h, y0, h, y0 + side * L
                ex, ey = e, y0
            else:
                side = -1 if into is None or centroid(into)[0] < a else 1
                x0 = a if side < 0 else a + t
                hx, hy, ox, oy = x0, h, x0 + side * L, h
                ex, ey = x0, e
            self.line(hx, hy, ox, oy, color, 1.1, layer='openings')
            sweep = 1 if ((ox - hx) * (ey - hy) - (oy - hy) * (ex - hx)) > 0 else 0
            self.add(f'<path d="M{px(ox):.1f},{py(oy):.1f} A{L * S:.1f},{L * S:.1f} 0 0 {sweep} {px(ex):.1f},{py(ey):.1f}" fill="none" stroke="{color}" stroke-width="0.6" stroke-dasharray="2,2"/>', 'openings')

    def fixture(self, f, color):
        x, y = f['at']; w, h = f['size']; k = f['kind']
        x0, y0, x1, y1 = x - w / 2, y - h / 2, x + w / 2, y + h / 2
        if k in ('wc',):
            self.rect(x0, y0, x1, y1, '#fff', color, 0.7, layer='fix')
            self.add(f'<ellipse cx="{px(x):.1f}" cy="{py(y):.1f}" rx="{min(w, h) * S * 0.33:.1f}" ry="{min(w, h) * S * 0.38:.1f}" fill="none" stroke="{color}" stroke-width="0.7"/>', 'fix')
        elif k in ('tub',):
            self.rect(x0, y0, x1, y1, '#fff', color, 0.8, layer='fix')
            self.rect(x0 + 0.25, y0 + 0.25, x1 - 0.25, y1 - 0.25, 'none', color, 0.5, layer='fix')
        elif k in ('lav', 'sink'):
            self.add(f'<ellipse cx="{px(x):.1f}" cy="{py(y):.1f}" rx="{w * S * 0.36:.1f}" ry="{h * S * 0.36:.1f}" fill="#fff" stroke="{color}" stroke-width="0.7"/>', 'fix')
        elif k == 'drain':
            self.circle(x, y, 0.25, '#fff', color, 0.7, layer='fix')
        elif k == 'shower':
            self.rect(x0, y0, x1, y1, 'none', color, 0.6, '3,2', layer='fix')
            self.line(x0, y0, x1, y1, color, 0.4, layer='fix'); self.line(x0, y1, x1, y0, color, 0.4, layer='fix')
        elif k == 'fireplace':
            self.rect(x0, y0, x1, y1, '#f1e4dc', color, 0.8, layer='fix')
        else:
            self.rect(x0, y0, x1, y1, 'none', color, 0.6, layer='fix')
            if k in ('range', 'washer', 'dryer', 'ref', 'dw'):
                self.text(x, y, {'range': 'R', 'washer': 'W', 'dryer': 'D', 'ref': 'REF', 'dw': 'DW'}[k], 5.5, color, layer='fix')

    # ------------------------------------------------------------ title block and output
    def title_block(self, notes=()):
        x = self.width - TB + 10; w = TB - 20; y = MY; h = self.height - 2 * MY
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#fff" stroke="#3f3b35" stroke-width="1"/>', 'title')
        self.add(f'<text x="{x + 10}" y="{y + 22}" font-size="10" fill="#6f685d" font-weight="600" letter-spacing="1">64 STONE SHEEP CIRCLE</text>', 'title')
        self.add(f'<text x="{x + 10}" y="{y + 40}" font-size="9" fill="#6f685d">From the owner\'s plans, Larson House 6/11/26</text>', 'title')
        self.add(f'<text x="{x + 10}" y="{y + 76}" font-size="15" fill="#221f1a" font-weight="700">{esc(self.title)}</text>', 'title')
        yy = y + 96
        for line in wrap(self.subtitle, 40):
            self.add(f'<text x="{x + 10}" y="{yy}" font-size="9" fill="#4d4842">{esc(line)}</text>', 'title'); yy += 13
        yy += 10
        for n in notes:
            for i, line in enumerate(wrap(n, 44)):
                self.add(f'<text x="{x + 10}" y="{yy}" font-size="8.5" fill="#4d4842">{esc(("• " if i == 0 else "  ") + line)}</text>', 'title'); yy += 12
            yy += 3
        # north is not given relative to the plan; show the plan's own directions
        self.add(f'<text x="{x + 10}" y="{y + h - 92}" font-size="8.5" fill="#6f685d">Top of sheet = rear (patio). Bottom = front (porch).</text>', 'title')
        self.add(f'<text x="{x + 10}" y="{y + h - 78}" font-size="8.5" fill="#6f685d">Grid: 5 ft, feet from the garage door wall (X)</text>', 'title')
        self.add(f'<text x="{x + 10}" y="{y + h - 66}" font-size="8.5" fill="#6f685d">and from the master bedroom\'s rear wall (Y).</text>', 'title')
        self.add(f'<line x1="{x}" y1="{y + h - 50}" x2="{x + w}" y2="{y + h - 50}" stroke="#3f3b35"/>', 'title')
        self.add(f'<text x="{x + 10}" y="{y + h - 30}" font-size="9" fill="#6f685d">SHEET</text>', 'title')
        self.add(f'<text x="{x + w - 10}" y="{y + h - 18}" font-size="26" fill="#b4462f" font-weight="700" text-anchor="end">{esc(self.number)}</text>', 'title')
        self.add(f'<text class="rev" x="{x + 10}" y="{y + h - 14}" font-size="9" fill="#6f685d">draft</text>', 'title')

    def svg(self):
        body = ''.join(''.join(self.L[k]) for k in LAYERS)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}" '
                f'font-family="IBM Plex Sans, Segoe UI, Helvetica, Arial, sans-serif">{body}</svg>')


def wrap(t, n):
    out, cur = [], ''
    for word in str(t).split():
        if len(cur) + len(word) + 1 > n and cur: out.append(cur); cur = word
        else: cur = (cur + ' ' + word).strip()
    if cur: out.append(cur)
    return out


def dist(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])
