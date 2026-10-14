"""Tube layout on 3" nub boards: every run of PEX sits on the boards' 3" grid, so the whole slab is a lattice of
nodes 3" apart and a tube is a walk from node to node. Fields are laid as a tube pair snaking together (supply and
return side by side, 6" apart, bending as a nested pair at each end) so a loop's two ends sit together at one edge of
its panel; leaders are then routed node by node from those ends to a manifold port through the free nodes around
the panels, under cabinets, through doorways and under the walls where a gate allows it. A node holds one tube, so
nothing can cross. `verify()` re-checks that at the end.

Coordinates are plan feet; node (i, j) is at (i * P, j * P) from the datum (every sheet's 0,0).
"""
import heapq
import math

P = 0.25                  # lattice pitch, ft: the boards' 3" nub grid
CLR = 0.30                # tube to a wall face or a fixed thing, ft
JAMB = 0.10               # tube to a door jamb, ft


def node(x, y): return (int(round(x / P)), int(round(y / P)))


def ft(n): return (n[0] * P, n[1] * P)


def inside_poly(poly, x, y):
    n = len(poly); c = False; j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: c = not c
        j = i
    return c


class Grid:
    """The slab as lattice nodes. `room` says which room a node is in (door openings and gates carry the room they
    lead into), `blocked` holds every node a tube may not use (walls and their clearance, fixtures, drains, outside),
    `used` the nodes tubes have taken."""

    def __init__(self, house, gates=(), no_tube=(), drains=(), skip_rooms=()):
        self.house = house
        xs = [p[0] for r in house['rooms'] for p in r['poly']]; ys = [p[1] for r in house['rooms'] for p in r['poly']]
        self.ni = int(max(xs) / P) + 2; self.nj = int(max(ys) / P) + 2
        self.room = {}
        self.blocked = set()
        self.field = set()         # nodes inside a panel's rectangle: no leader goes there
        self.used = {}             # node -> tube tag
        self.hug = set()           # nodes next to a wall, a fixture or the riser line: cheap for leaders
        self.hugt = set()          # nodes next to a tube already laid: nearly as cheap
        self.hugp = set()          # nodes next to a manifold's ports: the cheapest, so the first pair in takes the inside
        self.keep_out = set()      # nodes closed to the pair being routed now (per-loop hints from the layout)
        self.ports = {}            # station -> port nodes (reserved until a leader lands on one)
        self.gate_axis = {}        # node inside a gated wall -> the axis a tube may cross it along ('x' or 'y')
        pass_nodes = set()         # doorway and gate nodes: the wall clearance leaves them alone
        rooms = [r for r in house['rooms'] if r['kind'] != 'outdoor' and r['id'] not in skip_rooms]
        for r in rooms:
            px = [p[0] for p in r['poly']]; py = [p[1] for p in r['poly']]
            for i in range(int(min(px) / P), int(max(px) / P) + 2):
                for j in range(int(min(py) / P), int(max(py) / P) + 2):
                    if inside_poly(r['poly'], i * P, j * P): self.room[(i, j)] = r['id']
        # doorways: the gap in the wall, less the jambs, belongs to the room the door opens into
        for d in house['doors']:
            if d['kind'] in ('overhead', 'glass') or d.get('ext'): continue
            t = d.get('t', 0.29)
            s0, s1 = d['span'][0] + JAMB, d['span'][1] - JAMB
            into = d['between'][1] if d['between'][1] in {r['id'] for r in rooms} else d['between'][0]
            if d['axis'] == 'y':
                for i in range(int(s0 / P), int(s1 / P) + 1):
                    for j in range(int((d['at'] - t - CLR - 0.01) / P), int((d['at'] + t + CLR + 0.01) / P) + 2):
                        if s0 <= i * P <= s1 and d['at'] - t - CLR - 0.01 <= j * P <= d['at'] + t + CLR + 0.01: self.room[(i, j)] = into; pass_nodes.add((i, j))
            else:
                for j in range(int(s0 / P), int(s1 / P) + 1):
                    for i in range(int((d['at'] - t - CLR - 0.01) / P), int((d['at'] + t + CLR + 0.01) / P) + 2):
                        if s0 <= j * P <= s1 and d['at'] - t - CLR - 0.01 <= i * P <= d['at'] + t + CLR + 0.01: self.room[(i, j)] = into; pass_nodes.add((i, j))
        # gates: a stretch of wall tubes may pass under (the rect is the wall itself; the strip reaches CLR into both rooms)
        for x0, y0, x1, y1, into in gates:
            along_x = (x1 - x0) >= (y1 - y0)
            ex, ey = (0.0, CLR + 0.01) if along_x else (CLR + 0.01, 0.0)
            for i in range(int((x0 - ex) / P), int((x1 + ex) / P) + 2):
                for j in range(int((y0 - ey) / P), int((y1 + ey) / P) + 2):
                    if x0 - ex - 1e-6 <= i * P <= x1 + ex + 1e-6 and y0 - ey - 1e-6 <= j * P <= y1 + ey + 1e-6:
                        self.room[(i, j)] = into; pass_nodes.add((i, j))
                        if (y0 - 0.1 <= j * P <= y1 + 0.1) if along_x else (x0 - 0.1 <= i * P <= x1 + 0.1):
                            self.gate_axis[(i, j)] = 'y' if along_x else 'x'
        # walls and their clearance block everything that is not a doorway or a gate
        door_nodes = pass_nodes
        self.pass_nodes = pass_nodes
        for w in house['walls']:
            along_x = (w['x1'] - w['x0']) >= (w['y1'] - w['y0'])
            ex, ey = (JAMB, CLR) if along_x else (CLR, JAMB)
            for i in range(int((w['x0'] - ex) / P), int((w['x1'] + ex) / P) + 2):
                for j in range(int((w['y0'] - ey) / P), int((w['y1'] + ey) / P) + 2):
                    x, y = i * P, j * P
                    if w['x0'] - ex - 1e-6 <= x <= w['x1'] + ex + 1e-6 and w['y0'] - ey - 1e-6 <= y <= w['y1'] + ey + 1e-6:
                        n = (i, j)
                        if n in door_nodes: continue
                        self.blocked.add(n)
        for x, y in house['posts']:
            for i in range(int((x - 0.6) / P), int((x + 0.6) / P) + 2):
                for j in range(int((y - 0.6) / P), int((y + 0.6) / P) + 2):
                    if abs(i * P - x) <= 0.33 + CLR and abs(j * P - y) <= 0.33 + CLR: self.blocked.add((i, j))
        for x0, y0, x1, y1 in no_tube:
            for i in range(int(x0 / P) - 1, int(x1 / P) + 2):
                for j in range(int(y0 / P) - 1, int(y1 / P) + 2):
                    if x0 - 1e-6 <= i * P <= x1 + 1e-6 and y0 - 1e-6 <= j * P <= y1 + 1e-6: self.blocked.add((i, j))
        for x, y, r in drains:
            for i in range(int((x - r) / P) - 1, int((x + r) / P) + 2):
                for j in range(int((y - r) / P) - 1, int((y + r) / P) + 2):
                    if math.hypot(i * P - x, j * P - y) <= r + 1e-6: self.blocked.add((i, j))
        for n in list(self.room):
            if n in self.blocked: continue
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                m = (n[0] + di, n[1] + dj)
                if m not in self.room or m in self.blocked: self.hug.add(n); break

    def _in_room_poly(self, n):
        x, y = ft(n)
        for r in self.house['rooms']:
            if r['kind'] == 'outdoor': continue
            px = [p[0] for p in r['poly']]
            if min(px) <= x <= max(px) and inside_poly(r['poly'], x, y): return True
        return False

    def add_ports(self, station, nodes, room):
        """Where a station's loop ends rise out of the slab: one node per tube end, in a row along the wall. They sit inside
        the wall clearance, so they are unblocked here, and reserved so no leader passes through one. The rest of that
        line along the wall (up to the next doorway or corner) stays clear, so leaders run one row out from it and
        turn in, and the row in front of it is a wall row for the cost."""
        nodes = list(nodes)
        self.ports[station] = nodes
        for n in nodes:
            self.blocked.discard(n); self.room[n] = room; self.used[n] = 'port'
        a, b = nodes[0], nodes[-1]
        d = (0, 1) if a[0] == b[0] else (1, 0)
        # which side of the port row the wall is on: the perpendicular neighbour that is not free floor
        perp = (d[1], d[0])
        wall = perp if (_add(a, perp) not in self.room or _add(a, perp) in self.blocked) else (-perp[0], -perp[1])
        for start, sign in ((a, -1), (b, 1)):
            k = 1
            while True:
                m = (start[0] + sign * k * d[0], start[1] + sign * k * d[1])
                if m not in self.room or m in self.blocked or m in self.used or m in self.pass_nodes or m in self.field: break
                w = _add(m, wall)
                if w in self.room and w not in self.blocked: break        # the wall has ended (a corner, the room opens out)
                self.blocked.add(m); k += 1
                away = (m[0] - wall[0], m[1] - wall[1])                  # the row in front of the reserved line is a wall row
                if away in self.room and away not in self.blocked: self.hug.add(away)
        for n in nodes:
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                m = (n[0] + di, n[1] + dj)
                if m in self.room and m not in self.blocked: self.hug.add(m); self.hugp.add(m)

    def free_ports(self, station):
        return [n for n in self.ports[station] if self.used.get(n) == 'port']

    def free(self, n):
        return n in self.room and n not in self.blocked and n not in self.field and n not in self.used and n not in self.keep_out

    def take(self, path, tag):
        for n in path:
            if n in self.used and self.used[n] not in (tag, 'port'): raise ValueError(f'{tag} crosses {self.used[n]} at {ft(n)}')
            self.used[n] = tag
        for n in path:
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                m = (n[0] + di, n[1] + dj)
                if m in self.room: self.hugt.add(m)

    def hug_cost(self, m, fin, open_cost):
        if m in self.hugp or fin in self.hugp: return 0.0
        if m in self.hug or fin in self.hug: return 0.1
        if m in self.hugt or fin in self.hugt: return 0.15
        return open_cost


# ---------------------------------------------------------------- fields
def pair_serpentine(m, n, s=2, join=True):
    """A tube pair snaking through a band: m columns and n rows (n even) of tube `s` lattice steps apart (2 = 6").
    Local lattice units: columns 0..s(m-1) along u, rows 0..s(n-1) along v. Supply enters at (0, 0), goes out with
    the return beside it, turns with it as a nested pair at each end, and comes back to leave at (0, s); so both ends
    sit at the u = 0 edge, one tube apart, and no tube crosses another. Returns the loop's corner points."""
    assert n % 2 == 0 and n >= 2 and m >= 2
    uL, uR = 0, s * (m - 1)
    A = [(uL, 0)]; B = [(uL, s)]
    rowA, rowB = 0, s
    for k in range(n // 2):
        d = 1 if k % 2 == 0 else -1
        far = uR if d > 0 else uL
        if k == n // 2 - 1:
            A.append((far, rowA)); B.append((far, rowB)); break
        # the tube on the upper row is the outer one at this bend: it drops three rows; the lower one drops one,
        # turning one notch (s/2 nodes) inside it
        outer_is_A = rowA < rowB
        inset = max(1, s // 2)
        for tube in ('A', 'B'):
            pts = A if tube == 'A' else B
            row = rowA if tube == 'A' else rowB
            if (tube == 'A') == outer_is_A:
                pts.append((far, row)); pts.append((far, row + 3 * s)); row += 3 * s
            else:
                pts.append((far - d * inset, row)); pts.append((far - d * inset, row + s)); row += s
            if tube == 'A': rowA = row
            else: rowB = row
    if not join: return A, B
    return A + B[::-1]


def pair_open(panel, v0, n):
    """One band of a panel as an open pair: the two tubes' node lists (A from the supply inlet, B from the return
    outlet, both at the entry edge) ending side by side where the loop goes on to its next panel, plus the lead-in and
    lead-out nodes outside the entry edge and the two nodes just beyond the open ends."""
    m, _ = panel.local()
    A, B = pair_serpentine(m, n, panel.s, join=False)
    na = rasterize([panel.to_node(u, v0 + v) for u, v in A]); nb = rasterize([panel.to_node(u, v0 + v) for u, v in B])
    ea, eb = A[-1], B[-1]
    out = 1 if ea[0] > 0 else -1
    ends = (panel.to_node(ea[0] + out, v0 + ea[1]), panel.to_node(eb[0] + out, v0 + eb[1]))
    return na, nb, panel.to_node(-1, v0), panel.to_node(-1, v0 + panel.s), ends


def rasterize(corners):
    """Every lattice node along a corner list (the tube itself, 3" by 3")."""
    out = [corners[0]]
    for (a, b), (c, d) in zip(corners, corners[1:]):
        if a == c:
            step = 1 if d > b else -1
            out += [(a, v) for v in range(b + step, d + step, step)]
        elif b == d:
            step = 1 if c > a else -1
            out += [(u, b) for u in range(a + step, c + step, step)]
        else:
            raise ValueError('diagonal')
    return out


def plen_nodes(path): return (len(path) - 1) * P


class Panel:
    """A rectangle of floor to tube, in plan feet (x0, y0, x1, y1), with the edge its loop ends sit on ('W', 'E',
    'N' or 'S'; add 'r' to start the bands from the other end of that edge) and the tube spacing in inches."""

    def __init__(self, room, x0, y0, x1, y1, entry='W', spacing=6):
        self.room = room; self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.entry = entry[0]; self.rev = entry.endswith('r'); self.s = spacing * 4 // 12   # lattice steps per tube
        if self.s < 1: raise ValueError('spacing')
        # snap the field to the 6" (or 12") lines inside the rectangle
        s = self.s
        self.i0 = -(-int(math.ceil(x0 / P - 1e-9)) // s) * s; self.i1 = (int(math.floor(x1 / P + 1e-9)) // s) * s
        self.j0 = -(-int(math.ceil(y0 / P - 1e-9)) // s) * s; self.j1 = (int(math.floor(y1 / P + 1e-9)) // s) * s
        self.cols = (self.i1 - self.i0) // s + 1; self.rows = (self.j1 - self.j0) // s + 1

    def local(self):
        """Columns (along the tube runs) and rows (across them) as the serpentine sees them."""
        if self.entry in 'WE': return self.cols, self.rows
        return self.rows, self.cols

    def to_node(self, u, v):
        """Local (u along the runs from the entry edge, v across from the first band) to a lattice node."""
        if self.entry == 'W': i, j = self.i0 + u, (self.j1 - v if self.rev else self.j0 + v)
        elif self.entry == 'E': i, j = self.i1 - u, (self.j1 - v if self.rev else self.j0 + v)
        elif self.entry == 'N': j, i = self.j0 + u, (self.i1 - v if self.rev else self.i0 + v)
        else: j, i = self.j1 - u, (self.i1 - v if self.rev else self.i0 + v)
        return (i, j)

    def bbox_nodes(self):
        return [(i, j) for i in range(self.i0, self.i1 + 1) for j in range(self.j0, self.j1 + 1)]

    def rect_ft(self): return (self.i0 * P, self.j0 * P, self.i1 * P, self.j1 * P)


def band_loops(panel, n_rows_max):
    """Split a panel across its rows into bands of at most n_rows_max rows (even counts), as evenly as possible.
    Returns a list of (v0, n) in local lattice rows."""
    m, R = panel.local()
    s = panel.s
    R2 = R - (R % 2)
    if R2 < 2: return []
    nb = max(1, math.ceil(R2 / max(2, n_rows_max - n_rows_max % 2)))
    base = (R2 // nb) - ((R2 // nb) % 2)
    sizes = [base] * nb
    left = R2 - base * nb
    k = 0
    while left >= 2:
        sizes[k % nb] += 2; left -= 2; k += 1
    out = []; v = 0
    for n in sizes:
        if n >= 2: out.append((v, n))
        v += n * s
    return out


def band_path(panel, v0, n):
    """The loop in one band of a panel: lattice nodes from the supply inlet to the return outlet, both on the entry
    edge, plus the two nodes just outside the edge where the leaders start."""
    m, _ = panel.local()
    pts = pair_serpentine(m, n, panel.s)
    corners = [panel.to_node(u, v0 + v) for u, v in pts]
    nodes = rasterize(corners)
    lead_in = panel.to_node(-1, v0); lead_out = panel.to_node(-1, v0 + panel.s)
    return nodes, corners, lead_in, lead_out


# ---------------------------------------------------------------- leaders
def astar(grid, start, goals, allow=(), open_cost=0.4, limit=400000):
    """Shortest cheap walk from `start` to any node in `goals` over free nodes (plus `allow`), hugging walls and
    other leaders. Returns the node list or None."""
    goals = set(goals); allow = set(allow)
    gx = [g[0] for g in goals]; gy = [g[1] for g in goals]
    def h(n): return min(abs(n[0] - x) + abs(n[1] - y) for x, y in zip(gx, gy))
    best = {start: 0.0}; came = {}
    heap = [(h(start), 0.0, start)]
    seen = 0
    while heap:
        f, g, n = heapq.heappop(heap)
        if g > best.get(n, 1e18) + 1e-9: continue
        if n in goals:
            path = [n]
            while path[-1] in came: path.append(came[path[-1]])
            return path[::-1]
        seen += 1
        if seen > limit: return None
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            m = (n[0] + di, n[1] + dj)
            if not (m in goals or m in allow or grid.free(m)): continue
            ax = grid.gate_axis.get(m) or grid.gate_axis.get(n)
            if ax == 'y' and di != 0 or ax == 'x' and dj != 0: continue      # under a wall only straight across
            c = 1.0 + (0.0 if (m in grid.hug or m in grid.hugt or m in goals) else open_cost)
            # a corner costs a little, so runs stay straight
            if n in came and (n[0] - came[n][0], n[1] - came[n][1]) != (di, dj): c += 0.3
            ng = g + c
            if ng < best.get(m, 1e18) - 1e-9:
                best[m] = ng; came[m] = n
                heapq.heappush(heap, (ng + h(m), ng, m))
    return None


def L(d): return (-d[1], d[0])


def _add(a, b): return (a[0] + b[0], a[1] + b[1])


def _clean(path):
    """Drop repeated nodes and dead-end spurs (a, b, a) from a claimed-node sequence."""
    out = []
    for n in path:
        if not out or out[-1] != n: out.append(n)
    changed = True
    while changed:
        changed = False; i = 0
        while i + 2 < len(out):
            if out[i] == out[i + 2]: del out[i + 1:i + 3]; changed = True
            else: i += 1
    return out


def _valid(*paths):
    seen = set()
    for p in paths:
        for a, b in zip(p, p[1:]):
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1: return False
        for n in p:
            if n in seen: return False
            seen.add(n)
    return True


def _corridor(grid, n0, nb, d0, ports, leads, open_cost, limit, trace=None):
    """A* over (node, heading) for a tube pair: the main tube walks the lattice, its partner rides one node to its
    side (s * L(heading)); at a turn toward the partner the partner waits for it, at a turn away it goes round the
    outside. Returns (cost, main path, partner path) or None."""
    v = ((nb[0] - n0[0]) // 2, (nb[1] - n0[1]) // 2)
    if _add(n0, (2 * v[0], 2 * v[1])) != nb or abs(v[0]) + abs(v[1]) != 1: raise ValueError('lead nodes')
    if L(d0) == v: s = 1
    elif L(d0) == (-v[0], -v[1]): s = -1
    else: raise ValueError('lead heading')
    def sL(d): return (-s * d[1], s * d[0])
    own = {n0, nb}
    mid = None
    if leads: mid = ((leads[0][0] + leads[1][0]) // 2, (leads[0][1] + leads[1][1]) // 2)
    goals = set(ports or ()) | (set(leads) if leads else set())
    gx = [g[0] for g in goals]; gy = [g[1] for g in goals]
    def h(n): return min(abs(n[0] - x) + abs(n[1] - y) for x, y in zip(gx, gy))
    # a pair may take two adjacent free ports as long as every stretch of free ports left between used ones stays
    # even, so no single port is stranded between pairs
    okpair = set()
    if ports:
        free = [grid.used.get(n) == 'port' for n in ports]
        for i in range(len(ports) - 1):
            if not (free[i] and free[i + 1]): continue
            f = free[:]; f[i] = f[i + 1] = False
            runs = []; k = 0
            while k < len(f):
                if f[k]:
                    j = k
                    while j < len(f) and f[j]: j += 1
                    runs.append((k, j)); k = j
                else: k += 1
            if all((a == 0 or b == len(f)) or (b - a) % 2 == 0 for a, b in runs):
                okpair.add((ports[i], ports[i + 1])); okpair.add((ports[i + 1], ports[i]))
    def is_port(n): return ports is not None and grid.used.get(n) == 'port' and n in ports
    def along(n, d):
        ax = grid.gate_axis.get(n)
        return not ax or (ax == 'y' and d[0] == 0) or (ax == 'x' and d[1] == 0)
    def claims(n, d, dout):
        p = _add(n, sL(d))
        if dout == d: return [p]
        if dout == sL(d): return []
        return [p, _add(p, d), _add(n, d)]
    best = {(n0, d0, False): 0.0}; came = {}
    heap = [(h(n0), 0.0, n0, d0, False)]
    seen = 0
    while heap:
        f, g, n, d, ll = heapq.heappop(heap)
        if g > best.get((n, d, ll), 1e18) + 1e-9: continue
        if ll == 'G':
            # unwind
            steps = []; key = (n, d, ll)
            while key in came:
                prev = came[key]; steps.append((prev[0], prev[1], key[1])); key = prev
            steps.reverse()
            main = [n0] + [_add(a, dout) for a, _, dout in steps]
            part = [nb]
            for a, din, dout in steps: part += claims(a, din, dout)
            part.append(_add(n, sL(d)))
            if leads: part.append(leads[1] if n == leads[0] else leads[0])
            part = _clean(part)
            return (g, main, part) if _valid(main, part) else None
        seen += 1
        if seen > limit: return None
        for dout in (d, sL(d), (-sL(d)[0], -sL(d)[1])):
            if n == n0 and dout == v: continue                 # the partner stands there
            if ll and dout == sL(d): continue                   # two turns toward the partner would wrap it
            if not along(n, dout): continue
            m = _add(n, dout)
            fin = _add(m, sL(dout))
            goal = ((m, fin) in okpair) or (leads is not None and fin == mid and m in leads and grid.free(mid))
            if not goal and not grid.free(m): continue
            if not along(m, dout): continue
            cl = claims(n, d, dout)
            if any(not (grid.free(c) or c in own) or not along(c, dout) for c in cl): continue
            if not goal and not along(fin, dout): continue
            c = 1.0 + grid.hug_cost(m, fin, open_cost) + (0.3 if dout != d else 0.0)
            ng = g + c
            key = (m, dout, 'G' if goal else dout == sL(d))
            if ng < best.get(key, 1e18) - 1e-9:
                best[key] = ng; came[key] = (n, d, ll)
                if trace is not None: trace.add(m)
                heapq.heappush(heap, (ng + (0.0 if goal else h(m)), ng, m, dout, key[2]))
    return None


def pair_route(grid, lead_a, lead_b, d0, ports=None, leads=None, open_cost=0.4, limit=400000):
    """Route a supply and return side by side (one node apart) from their lead nodes (two nodes apart just outside a
    field's entry edge, heading d0 away from it) to two adjacent free ports of `ports`, or to a second panel's lead pair
    `leads`. Either tube may ride on the outside; the cheaper way wins. Returns (path from lead_a, path from lead_b)
    ending on the ports (or the far leads), or None."""
    best = None
    for main, other in ((lead_a, lead_b), (lead_b, lead_a)):
        r = _corridor(grid, main, other, d0, ports, leads, open_cost, limit)
        if r and (best is None or r[0] < best[0]): best = (r[0], r[1], r[2], main is lead_a)
    if not best: return None
    _, pm, pp, a_main = best
    return (pm, pp) if a_main else (pp, pm)


def verify(grid, tubes):
    """Every node used once, every step a lattice step: no crossings, no diagonals."""
    seen = {}
    for tag, nodes in tubes:
        for a, b in zip(nodes, nodes[1:]):
            if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1: raise ValueError(f'{tag}: not a lattice step at {ft(a)}')
        for n in nodes:
            if n in seen and seen[n] != tag: raise ValueError(f'{tag} crosses {seen[n]} at {ft(n)}')
            seen[n] = tag
    return len(seen)


def corners_ft(nodes):
    """Collapse a node walk to its corner points, in feet."""
    if not nodes: return []
    out = [nodes[0]]
    for a, b, c in zip(nodes, nodes[1:], nodes[2:]):
        if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]): out.append(b)
    if len(nodes) > 1: out.append(nodes[-1])
    return [ft(n) for n in out]
