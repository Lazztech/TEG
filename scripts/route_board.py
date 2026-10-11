#!/usr/bin/env python3
"""Route the placed board with a 2-layer maze (Lee) router.

STATUS: experimental / unfinished. It routes ~95% of connections but does NOT yet reach
a DRC-clean board, so the routed output is not used — the shipped board is left unrouted
and clean. A routed attempt is kept in build/TEG-routed-attempt.kicad_pcb for reference.

What works: grid occupancy model, rectangular pad obstacles, per-pad fanout ("escape")
stubs for the 0.5 mm-pitch VQFN, vias, and net ordering.
What does not: clearance vs routability trade-off — a halo tight enough to route
everything leaves ~40 clearance violations, and a halo wide enough to be clean leaves
~4 connections unrouted. Resolving that needs visual iteration; routing this interactively
in KiCad is the recommended path (see README).

Writes tracks + vias into hardware/TEG.kicad_pcb.

Pipeline:  gen_schematic.py -> gen_board.py -> route_board.py -> validate.sh
(gen_board.py rewrites the board and wipes routing.)
"""
import sys
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_schematic import parse_sexpr, unq, walk  # noqa: E402

PCB = Path(__file__).resolve().parent.parent / "hardware" / "TEG.kicad_pcb"

GRID = 0.25
TRACK_W = 0.2
VIA_SIZE, VIA_DRILL = 0.6, 0.3
CLEARANCE = 0.2
PAD_MARGIN = 0.40     # pad rect margin: track half + clearance + grid slack
VIA_CLEAR = 0.5       # via centre to foreign pad edge (0.3 via half + 0.2 rule)
HALO = 2
EDGE_MARGIN = 0.8
F, B = 0, 1
VIA_COST = 40
LAYERS = ("F.Cu", "B.Cu")


def f(x):
    return f"{round(x, 4):.4f}".rstrip("0").rstrip(".")


def read_board():
    root, _ = parse_sexpr(PCB.read_text())
    pcb = root[0]
    nets = {int(n[1]): unq(n[2]) for n in walk(pcb, "net") if len(n) > 2}
    modules = []
    for m in pcb:
        if not (isinstance(m, list) and m[0] == "module"):
            continue
        at = next(c for c in m if isinstance(c, list) and c[0] == "at")
        mx, my = float(at[1]), float(at[2])
        ref = next((unq(t[2]) for t in walk(m, "fp_text") if t[1] == "reference"), "?")
        pads = []
        for pad in walk(m, "pad"):
            pat = next(c for c in pad if isinstance(c, list) and c[0] == "at")
            psz = next(c for c in pad if isinstance(c, list) and c[0] == "size")
            pnet = next((c for c in pad if isinstance(c, list) and c[0] == "net"), None)
            layers = next((c for c in pad if isinstance(c, list) and c[0] == "layers"), None)
            thru = any("*.Cu" in str(x) for x in (layers[1:] if layers else []))
            pads.append(dict(num=unq(pad[1]), x=mx + float(pat[1]), y=my + float(pat[2]),
                             w=float(psz[1]), h=float(psz[2]),
                             net=int(pnet[1]) if pnet else 0, thru=thru))
        modules.append(dict(ref=ref, pads=pads))
    xs, ys = [], []
    for gl in walk(pcb, "gr_line"):
        if any(isinstance(c, list) and c[0] == "layer" and "Edge.Cuts" in str(c[1]) for c in gl):
            st = next(c for c in gl if isinstance(c, list) and c[0] == "start")
            xs.append(float(st[1])); ys.append(float(st[2]))
    return nets, modules, (min(xs), min(ys), max(xs), max(ys))


class Grid:
    def __init__(self, x0, y0, cols, rows):
        self.x0, self.y0, self.cols, self.rows = x0, y0, cols, rows
        self.pads = []          # (x, y, w, h, net) for via clearance checks
        self.pad = [[0] * (cols * rows) for _ in (F, B)]     # -1 off-board, 0 free, else net
        self.route = [[0] * (cols * rows) for _ in (F, B)]

    def idx(self, c, r):
        return r * self.cols + c

    def cell(self, x, y):
        return round((x - self.x0) / GRID), round((y - self.y0) / GRID)

    def xy(self, c, r):
        return self.x0 + c * GRID, self.y0 + r * GRID

    def inside(self, c, r):
        return 0 <= c < self.cols and 0 <= r < self.rows

    def block_rect(self, x, y, w, h, net, margin=PAD_MARGIN):
        ci, ri = self.cell(x, y)
        nc = int((w / 2 + margin) / GRID) + 2
        nr = int((h / 2 + margin) / GRID) + 2
        for dc in range(-nc, nc + 1):
            for dr in range(-nr, nr + 1):
                c, r = ci + dc, ri + dr
                if not self.inside(c, r):
                    continue
                gx, gy = self.xy(c, r)
                if abs(gx - x) <= w / 2 + margin and abs(gy - y) <= h / 2 + margin:
                    for li in (F, B):
                        i = self.idx(c, r)
                        if self.pad[li][i] == 0:
                            self.pad[li][i] = net

    def mark_route(self, c, r, li, net, halo=HALO):
        for dc in range(-halo, halo + 1):
            for dr in range(-halo, halo + 1):
                cc, rr = c + dc, r + dr
                if self.inside(cc, rr):
                    i = self.idx(cc, rr)
                    if self.route[li][i] == 0:
                        self.route[li][i] = net

    def usable(self, c, r, li, net):
        i = self.idx(c, r)
        if self.pad[li][i] not in (0, net):     # -1 (off-board) and foreign pads block
            return False
        return self.route[li][i] in (0, net)

    def via_ok(self, c, r, net):
        if not (self.usable(c, r, F, net) and self.usable(c, r, B, net)):
            return False
        x, y = self.xy(c, r)
        for px, py, pw, ph, pnet in self.pads:
            if pnet == net and abs(VIA_SIZE) > 0 and False:
                continue
            if abs(x - px) <= pw / 2 + VIA_CLEAR and abs(y - py) <= ph / 2 + VIA_CLEAR:
                return False
        return True


def build_grid(modules, outline):
    x0, y0, x1, y1 = outline
    cols = int((x1 - x0) / GRID) + 3
    rows = int((y1 - y0) / GRID) + 3
    g = Grid(x0 - GRID, y0 - GRID, cols, rows)
    for c in range(cols):
        for r in range(rows):
            x, y = g.xy(c, r)
            if not (x0 + EDGE_MARGIN <= x <= x1 - EDGE_MARGIN and y0 + EDGE_MARGIN <= y <= y1 - EDGE_MARGIN):
                for li in (F, B):
                    g.pad[li][g.idx(c, r)] = -1
    for m in modules:
        for p in m["pads"]:
            g.block_rect(p["x"], p["y"], p["w"], p["h"], p["net"] or -2)
            g.pads.append((p["x"], p["y"], p["w"], p["h"], p["net"]))
    return g


def layers_of(p):
    return (F, B) if p["thru"] else (F,)


def escape_direction(p, centre):
    """Dominant axis pointing away from the package centre."""
    dx, dy = p["x"] - centre[0], p["y"] - centre[1]
    if abs(dx) >= abs(dy):
        return (1 if dx >= 0 else -1, 0)
    return (0, 1 if dy >= 0 else -1)


def pre_escape(g, modules):
    """Fanout: walk each pad outward and claim free cells, so fine-pitch pins have a
    reachable stub. Returns {pad id -> (c, r)} terminal cells and escape segments."""
    terms, escapes = {}, []
    for m in modules:
        if not m["pads"]:
            continue
        cx = sum(p["x"] for p in m["pads"]) / len(m["pads"])
        cy = sum(p["y"] for p in m["pads"]) / len(m["pads"])
        for p in m["pads"]:
            if not p["net"]:
                continue
            c0, r0 = g.cell(p["x"], p["y"])
            term = (c0, r0)
            dx, dy = escape_direction(p, (cx, cy))
            cur = (c0, r0)
            for _ in range(6):                       # up to 1.5 mm of fanout
                nc, nr = cur[0] + dx, cur[1] + dy
                if not g.inside(nc, nr):
                    break
                if not g.usable(nc, nr, F, p["net"]):
                    break
                g.mark_route(nc, nr, F, p["net"])
                cur = (nc, nr)
                term = cur
            terms[id(p)] = term
            x0, y0 = g.xy(c0, r0)
            x1, y1 = g.xy(term[0], term[1])
            if (x0, y0) != (x1, y1):
                escapes.append((p["x"], p["y"], x1, y1, p["net"]))
    return terms, escapes


def bfs(g, net, a, b, a_layers=(F, B), b_layers=(F, B)):
    (ac, ar), (bc, br) = a, b
    start = [(ac, ar, li) for li in a_layers if g.usable(ac, ar, li, net)]
    goals = {(bc, br, li) for li in b_layers if g.usable(bc, br, li, net)}
    if not start:
        return None
    seen, prev = {}, {}
    q = deque()
    for s in start:
        seen[s] = 0
        q.append(s)
    while q:
        cur = q.popleft()
        if cur in goals:
            path = [cur]
            while cur in prev:
                cur = prev[cur]
                path.append(cur)
            return path[::-1]
        c, r, li = cur
        d = seen[cur]
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cc, rr = c + dc, r + dr
            if g.inside(cc, rr) and g.usable(cc, rr, li, net):
                nxt = (cc, rr, li)
                if nxt not in seen or d + 1 < seen[nxt]:
                    seen[nxt] = d + 1; prev[nxt] = cur; q.append(nxt)
        other = B if li == F else F
        if g.via_ok(c, r, net) and g.usable(c, r, other, net):
            nxt = (c, r, other)
            if nxt not in seen or d + VIA_COST < seen[nxt]:
                seen[nxt] = d + VIA_COST; prev[nxt] = cur; q.append(nxt)
    return None


def path_to_geometry(path, g, net):
    """One segment per maximal straight run; a via at every layer change."""
    segs, vias = [], []
    i = 0
    n = len(path)
    while i < n - 1:
        c0, r0, l0 = path[i]
        if path[i + 1][2] != l0:                      # layer change -> via
            x, y = g.xy(c0, r0)
            vias.append((x, y, net))
            i += 1
            continue
        # extend while same layer and same direction
        dc, dr = path[i + 1][0] - c0, path[i + 1][1] - r0
        j = i
        while (j + 1 < n and path[j + 1][2] == l0 and
               path[j + 1][0] - path[j][0] == dc and path[j + 1][1] - path[j][1] == dr):
            j += 1
        x0, y0 = g.xy(c0, r0)
        x1, y1 = g.xy(path[j][0], path[j][1])
        segs.append((x0, y0, x1, y1, l0, net))
        i = j
    return segs, vias


def main():
    nets, modules, outline = read_board()
    g = build_grid(modules, outline)
    groups = {}
    for m in modules:
        for p in m["pads"]:
            if p["net"]:
                groups.setdefault(p["net"], []).append(p)

    # small nets first (local escapes made before the board fills up)
    order = sorted(groups, key=lambda n: len(groups[n]))
    print(f"outline {outline}  grid {g.cols}x{g.rows}  nets {len(order)}")

    terms_by_pad, escapes = pre_escape(g, modules)

    segs, vias, fails = [], [], []
    for net in order:
        terms = []
        for p in groups[net]:
            c, r = terms_by_pad.get(id(p)) or g.cell(p["x"], p["y"])
            c = min(max(c, 0), g.cols - 1); r = min(max(r, 0), g.rows - 1)
            terms.append((c, r, p))
        conn = [terms[0]]
        rest = terms[1:]
        while rest:
            best = None
            for t in rest:
                for cc in conn:
                    d = abs(t[0] - cc[0]) + abs(t[1] - cc[1])
                    if best is None or d < best[0]:
                        best = (d, t, cc)
            _, t, cc = best
            path = bfs(g, net, (t[0], t[1]), (cc[0], cc[1]),
                       layers_of(t[2]), layers_of(cc[2]))
            if path is None:
                fails.append((net, nets.get(net), t[2]["num"], cc[2]["num"]))
            else:
                s2, v2 = path_to_geometry(path, g, net)
                segs += s2
                vias += v2
                for (c, r, li) in path:
                    g.mark_route(c, r, li, net)
                conn.append(t)
            rest.remove(t)

    s = PCB.read_text().rstrip()
    assert s.endswith(")")
    body = [f"  (segment (start {f(a)} {f(b)}) (end {f(c)} {f(d)}) (width {TRACK_W}) "
            f"(layer {LAYERS[li]}) (net {nt}))" for a, b, c, d, li, nt in segs]
    body += [f"  (segment (start {f(a)} {f(b)}) (end {f(c)} {f(d)}) (width {TRACK_W}) "
             f"(layer F.Cu) (net {nt}))" for a, b, c, d, nt in escapes]
    body += [f"  (via (at {f(x)} {f(y)}) (size {VIA_SIZE}) (drill {VIA_DRILL}) "
             f"(layers F.Cu B.Cu) (net {nt}))" for x, y, nt in vias]
    PCB.write_text(s[:-1] + "\n" + "\n".join(body) + "\n)\n")
    print(f"segments={len(segs)} vias={len(vias)} failed_edges={len(fails)}")
    for fl in fails:
        print("   FAILED", fl)


if __name__ == "__main__":
    main()
