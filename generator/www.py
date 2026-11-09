"""Animated energy-flow picture for the dashboard (picture-elements card).

The background (huis_Nsets.svg) is an original architectural illustration in isometric projection:
a modern house with flat roofs and solar panels, a grid connection cabinet, N SolarFlow sets on the
front wall, a garage and a car on a granny charger. Each flow is a separate transparent SVG with a
CSS-animated dashed path in the same 1000x700 coordinate system; the dashboard shows it only while that
flow is running (conditional elements on the sensor values). The SVGs are embedded in the dashboard
as data URIs.
"""
import math

W, H = 1000, 700

# ------------------------------------------------------------------ isometric projection
S = 21.0                      # px per metre
OX, OY = 452.0, 262.0         # screen position of world origin (plot corner, ground level)
C30, S30 = math.cos(math.radians(30)), 0.5


def P(x, y, z=0.0):
    """World (m) -> screen (px). x runs right-down, y runs left-down, z up."""
    return (OX + (x - y) * C30 * S, OY + (x + y) * S30 * S - z * S)


def pts(*ps):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in ps)


def poly(ps, fill, extra=""):
    return f'<polygon points="{pts(*ps)}" fill="{fill}" {extra}/>'


def box(x0, y0, z0, x1, y1, z1, top, right, left, extra=""):
    """Visible faces of a box: top (z1), +x face (right), +y face (left)."""
    o = []
    o.append(poly([P(x0, y1, z0), P(x1, y1, z0), P(x1, y1, z1), P(x0, y1, z1)], left, extra))
    o.append(poly([P(x1, y0, z0), P(x1, y1, z0), P(x1, y1, z1), P(x1, y0, z1)], right, extra))
    o.append(poly([P(x0, y0, z1), P(x1, y0, z1), P(x1, y1, z1), P(x0, y1, z1)], top, extra))
    return "".join(o)


def yface(x0, x1, y, z0, z1, fill, extra=""):
    """Rectangle on a +y facing wall (front-left)."""
    return poly([P(x0, y, z0), P(x1, y, z0), P(x1, y, z1), P(x0, y, z1)], fill, extra)


def xface(y0, y1, x, z0, z1, fill, extra=""):
    """Rectangle on a +x facing wall (front-right)."""
    return poly([P(x, y0, z0), P(x, y1, z0), P(x, y1, z1), P(x, y0, z1)], fill, extra)


def ground(x0, y0, x1, y1, fill, z=0.0, extra=""):
    return poly([P(x0, y0, z), P(x1, y0, z), P(x1, y1, z), P(x0, y1, z)], fill, extra)


def path(*ps):
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in ps)


# ------------------------------------------------------------------ key points
HUB = P(5.5, 10.0, 1.45)                 # meter / inverter box on the front wall
CAB = P(1.0, 12.4, 1.25)                 # grid connection cabinet (top)
CAB_FOOT = P(1.0, 12.0, 0.0)
PV_C = P(8.6, 5.4, 6.75)                 # middle of the solar array
INSIDE = P(9.0, 6.0, 4.4)                # inside the upper floor
BATT_TOP = P(3.95, 10.2, 1.45)
SOCKET = P(13.25, 8.0, 0.75)             # socket on the garage front wall
PORT = P(14.6, 9.45, 0.95)               # charge port on the car

LABEL_Y_TOP, LABEL_Y_BOT = 66, 628

FLOWS = {
    # pole/cabinet -> house (import)
    "net": (path((CAB[0], 128), CAB, CAB_FOOT, P(5.5, 10.0, 0.0), HUB), "#ff9f43"),
    # roof -> house
    "zon": (path((PV_C[0], 128), PV_C, HUB), "#ffd43b"),
    # house -> label
    "huis": (path(HUB, INSIDE, (880, INSIDE[1]), (880, 128)), "#4dabf7"),
    # house -> battery (charging)
    "accu": (path(HUB, P(4.95, 10.0, 1.45), BATT_TOP, P(3.95, 10.6, 0.0), (P(3.95, 10.6, 0.0)[0], 612)), "#51cf66"),
    # house -> car
    "ev": (path(HUB, P(13.0, 10.0, 1.45), P(13.25, 8.0, 0.75), SOCKET, PORT), "#b197fc"),
}

LABELS = {
    "net": (round(CAB[0]), LABEL_Y_TOP, "NET"),
    "zon": (round(PV_C[0]), LABEL_Y_TOP, "ZON"),
    "huis": (880, LABEL_Y_TOP, "HUIS"),
    "accu": (round(P(3.95, 10.6, 0.0)[0]), LABEL_Y_BOT, "ACCU'S"),
    "ev": (round(PORT[0] + 70), LABEL_Y_BOT, "AUTO"),
}
SOC_POS = (round(BATT_TOP[0] - 4), round(BATT_TOP[1] - 22))


# ------------------------------------------------------------------ drawing
DEFS = """<defs>
  <radialGradient id="sky" cx="0.5" cy="0.25" r="0.9">
    <stop offset="0" stop-color="#2a3442"/><stop offset="0.6" stop-color="#151a22"/><stop offset="1" stop-color="#0b0e13"/></radialGradient>
  <linearGradient id="lawn" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#3b4a3a"/><stop offset="1" stop-color="#2a3629"/></linearGradient>
  <linearGradient id="soilL" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#3a342e"/><stop offset="1" stop-color="#1d1a17"/></linearGradient>
  <linearGradient id="soilR" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#2b2723"/><stop offset="1" stop-color="#141210"/></linearGradient>
  <linearGradient id="paving" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#8b8a86"/><stop offset="1" stop-color="#6c6b68"/></linearGradient>
  <linearGradient id="plasterL" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#ecebe6"/><stop offset="1" stop-color="#cfcdc6"/></linearGradient>
  <linearGradient id="plasterR" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#bebcb5"/><stop offset="1" stop-color="#a5a39c"/></linearGradient>
  <linearGradient id="plasterT" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#d9d8d3"/><stop offset="1" stop-color="#c4c3be"/></linearGradient>
  <linearGradient id="darkL" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#4a4f57"/><stop offset="1" stop-color="#3a3e45"/></linearGradient>
  <linearGradient id="darkR" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#33373d"/><stop offset="1" stop-color="#282b30"/></linearGradient>
  <linearGradient id="roof" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#5a5e64"/><stop offset="1" stop-color="#474a50"/></linearGradient>
  <linearGradient id="glass" x1="0" y1="0" x2="0.3" y2="1">
    <stop offset="0" stop-color="#ffe3ad"/><stop offset="0.55" stop-color="#f3bd6c"/><stop offset="1" stop-color="#c98a3e"/></linearGradient>
  <linearGradient id="glassR" x1="0" y1="0" x2="0.3" y2="1">
    <stop offset="0" stop-color="#f0cf96"/><stop offset="1" stop-color="#b27a38"/></linearGradient>
  <linearGradient id="sheen" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#ffffff" stop-opacity="0"/><stop offset="0.5" stop-color="#ffffff" stop-opacity="0.22"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></linearGradient>
  <linearGradient id="pv" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#3f5f8c"/><stop offset="0.5" stop-color="#1c2f4d"/><stop offset="1" stop-color="#121f34"/></linearGradient>
  <linearGradient id="wood" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#a7744a"/><stop offset="1" stop-color="#7e532f"/></linearGradient>
  <linearGradient id="garageDoor" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#5b6068"/><stop offset="1" stop-color="#3f434a"/></linearGradient>
  <linearGradient id="carBody" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#9aa3ad"/><stop offset="0.5" stop-color="#6d7681"/><stop offset="1" stop-color="#3f454d"/></linearGradient>
  <linearGradient id="carSide" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#7a838e"/><stop offset="1" stop-color="#3a4048"/></linearGradient>
  <linearGradient id="carGlass" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#6f8196"/><stop offset="1" stop-color="#1f2833"/></linearGradient>
  <linearGradient id="batt" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f4f5f6"/><stop offset="1" stop-color="#cfd3d8"/></linearGradient>
  <linearGradient id="battR" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#c3c8ce"/><stop offset="1" stop-color="#9ea4ab"/></linearGradient>
  <linearGradient id="cab" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#b9bdc2"/><stop offset="1" stop-color="#8d9298"/></linearGradient>
  <radialGradient id="spill" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0" stop-color="#ffcf87" stop-opacity="0.38"/><stop offset="1" stop-color="#ffcf87" stop-opacity="0"/></radialGradient>
  <radialGradient id="canopy" cx="0.4" cy="0.35" r="0.7">
    <stop offset="0" stop-color="#5f7a55"/><stop offset="1" stop-color="#2f4430"/></radialGradient>
  <filter id="blur6" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="6"/></filter>
  <filter id="blur3" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3"/></filter>
  <filter id="grain" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="7" result="n"/>
    <feColorMatrix type="matrix" values="0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0 0.5  0 0 0 0.09 0"/>
  </filter>
</defs>"""


def _tree(x, y, h, r):
    o = []
    base = P(x, y, 0)
    o.append(f'<ellipse cx="{base[0] + 10:.1f}" cy="{base[1] + 3:.1f}" rx="{r * S * 1.0:.1f}" ry="{r * S * 0.42:.1f}" '
             f'fill="#000" opacity="0.35" filter="url(#blur3)"/>')
    top = P(x, y, h)
    o.append(f'<line x1="{base[0]:.1f}" y1="{base[1]:.1f}" x2="{top[0]:.1f}" y2="{top[1] + r * S * 0.6:.1f}" '
             f'stroke="#4a3a2c" stroke-width="3.2" stroke-linecap="round"/>')
    for dx, dy, k, op in ((-0.35, 0.2, 0.85, 0.95), (0.4, 0.35, 0.75, 0.95), (0.0, -0.45, 0.8, 0.95), (0.05, 0.05, 1.0, 0.85)):
        o.append(f'<ellipse cx="{top[0] + dx * r * S:.1f}" cy="{top[1] + dy * r * S:.1f}" rx="{k * r * S:.1f}" '
                 f'ry="{k * r * S * 0.92:.1f}" fill="url(#canopy)" opacity="{op}"/>')
    return "".join(o)


def _grasses(x, y, n=7):
    b = P(x, y, 0)
    o = []
    for k in range(n):
        a = -0.9 + 1.8 * k / (n - 1)
        o.append(f'<path d="M{b[0]:.1f},{b[1]:.1f} q{a * 6:.1f},-9 {a * 11:.1f},-17" fill="none" '
                 f'stroke="#8c9a6e" stroke-width="1.2" stroke-linecap="round" opacity="0.9"/>')
    return "".join(o)


def _pv_panel(x0, y0, w, d, z, tilt):
    """Panel tilted towards +y (front): back edge higher."""
    a, b = P(x0, y0, z + tilt), P(x0 + w, y0, z + tilt)
    c, e = P(x0 + w, y0 + d, z), P(x0, y0 + d, z)
    o = [poly([P(x0, y0 + d, z - 0.02), P(x0 + w, y0 + d, z - 0.02), P(x0 + w + 0.25, y0 + d + 0.45, z - 0.02),
               P(x0 + 0.25, y0 + d + 0.45, z - 0.02)], "#000", 'opacity="0.25"')]
    o.append(poly([a, b, c, e], "url(#pv)", 'stroke="#9fb3cc" stroke-width="0.8" stroke-linejoin="round"'))
    for t in (1 / 3, 2 / 3):
        p1 = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        p2 = (e[0] + (c[0] - e[0]) * t, e[1] + (c[1] - e[1]) * t)
        o.append(f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" stroke="#46638c" stroke-width="0.5"/>')
    m1 = ((a[0] + e[0]) / 2, (a[1] + e[1]) / 2)
    m2 = ((b[0] + c[0]) / 2, (b[1] + c[1]) / 2)
    o.append(f'<line x1="{m1[0]:.1f}" y1="{m1[1]:.1f}" x2="{m2[0]:.1f}" y2="{m2[1]:.1f}" stroke="#46638c" stroke-width="0.5"/>')
    o.append(poly([a, (a[0] + (b[0] - a[0]) * 0.45, a[1] + (b[1] - a[1]) * 0.45),
                   (e[0] + (c[0] - e[0]) * 0.25, e[1] + (c[1] - e[1]) * 0.25), e], "url(#sheen)", 'opacity="0.5"'))
    return "".join(o)


def _window_y(x0, x1, y, z0, z1, mullions=1, glass="url(#glass)"):
    o = [yface(x0 - 0.08, x1 + 0.08, y, z0 - 0.08, z1 + 0.08, "#2b2e33")]
    o.append(yface(x0, x1, y, z0, z1, glass))
    # interior depth hint and reflection
    o.append(yface(x0, x0 + (x1 - x0) * 0.3, y, z0, z1, "url(#sheen)", 'opacity="0.35"'))
    for k in range(1, mullions + 1):
        xm = x0 + (x1 - x0) * k / (mullions + 1)
        o.append(yface(xm - 0.04, xm + 0.04, y, z0, z1, "#2b2e33"))
    return "".join(o)


def _window_x(y0, y1, x, z0, z1, mullions=1):
    o = [xface(y0 - 0.08, y1 + 0.08, x, z0 - 0.08, z1 + 0.08, "#25282c")]
    o.append(xface(y0, y1, x, z0, z1, "url(#glassR)"))
    for k in range(1, mullions + 1):
        ym = y0 + (y1 - y0) * k / (mullions + 1)
        o.append(xface(ym - 0.04, ym + 0.04, x, z0, z1, "#25282c"))
    return "".join(o)


def _car():
    """Hatchback/crossover, length along x, parked on the driveway."""
    x0, x1, y0, y1 = 14.3, 18.8, 9.25, 11.1
    o = []
    # contact shadow
    sh = [P(x0 - 0.2, y0 - 0.1, 0), P(x1 + 0.3, y0 - 0.1, 0), P(x1 + 0.3, y1 + 0.35, 0), P(x0 - 0.2, y1 + 0.35, 0)]
    o.append(poly(sh, "#000", 'opacity="0.55" filter="url(#blur3)"'))
    # wheels (visible on the +y side)
    for wx in (x0 + 0.85, x1 - 0.85):
        c = P(wx, y1 + 0.02, 0.33)
        o.append(f'<ellipse cx="{c[0]:.1f}" cy="{c[1]:.1f}" rx="7.2" ry="9.4" fill="#111316" transform="rotate(-32 {c[0]:.1f} {c[1]:.1f})"/>'
                 f'<ellipse cx="{c[0]:.1f}" cy="{c[1]:.1f}" rx="4.6" ry="6.0" fill="#9aa1a8" transform="rotate(-32 {c[0]:.1f} {c[1]:.1f})"/>'
                 f'<ellipse cx="{c[0]:.1f}" cy="{c[1]:.1f}" rx="1.6" ry="2.1" fill="#3a3f45" transform="rotate(-32 {c[0]:.1f} {c[1]:.1f})"/>')
    # lower body
    zb, zt = 0.3, 0.95
    o.append(box(x0, y0, zb, x1, y1, zt, "url(#carBody)", "url(#carSide)", "url(#carSide)",
                 'stroke="#1c1f23" stroke-width="0.6" stroke-linejoin="round"'))
    # front (x1) slope / bonnet and cabin
    cx0, cx1 = x0 + 0.75, x1 - 1.55
    gy0, gy1 = y0 + 0.12, y1 - 0.12
    zc = 1.5
    # windscreen (sloped towards x1) and rear glass
    o.append(poly([P(cx1, gy0, zc), P(cx1 + 0.75, gy0, zt), P(cx1 + 0.75, gy1, zt), P(cx1, gy1, zc)], "url(#carGlass)",
                  'stroke="#1c1f23" stroke-width="0.6"'))
    # side glass (+y face of cabin)
    o.append(poly([P(cx0 - 0.55, gy1, zt), P(cx1 + 0.75, gy1, zt), P(cx1, gy1, zc), P(cx0, gy1, zc)], "url(#carGlass)",
                  'stroke="#1c1f23" stroke-width="0.6"'))
    bp = P(cx0 + (cx1 - cx0) * 0.48, gy1, zt)
    bq = P(cx0 + (cx1 - cx0) * 0.48, gy1, zc)
    o.append(f'<line x1="{bp[0]:.1f}" y1="{bp[1]:.1f}" x2="{bq[0]:.1f}" y2="{bq[1]:.1f}" stroke="#2a2f35" stroke-width="2"/>')
    # roof
    o.append(poly([P(cx0, gy0, zc), P(cx1, gy0, zc), P(cx1, gy1, zc), P(cx0, gy1, zc)], "#5d656f",
                  'stroke="#1c1f23" stroke-width="0.6"'))
    o.append(poly([P(cx0 - 0.55, gy0, zt), P(cx0, gy0, zc), P(cx0, gy1, zc), P(cx0 - 0.55, gy1, zt)], "url(#carGlass)",
                  'stroke="#1c1f23" stroke-width="0.6"'))
    # lights
    hl = [P(x1, y1 - 0.45, 0.8), P(x1, y1 - 0.12, 0.8), P(x1, y1 - 0.12, 0.68), P(x1, y1 - 0.45, 0.68)]
    o.append(poly(hl, "#fff3d6"))
    tl = [P(x0, y1 - 0.45, 0.82), P(x0 + 0.02, y1 - 0.08, 0.82), P(x0 + 0.02, y1 - 0.08, 0.72), P(x0, y1 - 0.45, 0.72)]
    o.append(poly(tl, "#c8323a"))
    # body line highlight
    a, b = P(x0 + 0.1, y1, 0.82), P(x1 - 0.1, y1, 0.82)
    o.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#c6ccd2" stroke-width="0.8" opacity="0.6"/>')
    # charge port light
    o.append(f'<circle cx="{PORT[0]:.1f}" cy="{PORT[1]:.1f}" r="2.6" fill="#b197fc"/>')
    return "".join(o)


def _tower(k: int) -> list:
    """Battery tower k (1..3) on the front wall. Fixed places, so towers 2 and 3 can be laid on top separately."""
    bw, gap = 0.72, 0.16
    span = 3 * bw + 2 * gap
    x = 3.95 - span / 2 + (k - 1) * (bw + gap)
    o = [poly([P(x, 10.0, 0), P(x + bw, 10.0, 0), P(x + bw + 0.2, 10.55, 0), P(x + 0.2, 10.55, 0)], "#000",
              'opacity="0.35" filter="url(#blur3)"'),
         box(x, 10.0, 0.05, x + bw, 10.38, 1.45, "#e7e9ec", "url(#battR)", "url(#batt)",
             'stroke="#7d848c" stroke-width="0.5" stroke-linejoin="round"')]
    for zz in (0.5, 0.95):
        a, b = P(x + 0.04, 10.38, zz), P(x + bw - 0.04, 10.38, zz)
        o.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#a8aeb5" stroke-width="0.7"/>')
    led = P(x + bw / 2, 10.38, 1.3)
    o.append(f'<rect x="{led[0] - 4:.1f}" y="{led[1] - 1.2:.1f}" width="8" height="2.4" rx="1.2" fill="#51cf66" '
             f'transform="rotate(-30 {led[0]:.1f} {led[1]:.1f})"/>')
    return o


def tower(k: int) -> str:
    """Only battery tower k, transparent around it: laid over the house when set k has an IP address."""
    return "\n".join([f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
                      """<defs>
  <linearGradient id="batt" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f4f5f6"/><stop offset="1" stop-color="#cfd3d8"/></linearGradient>
  <linearGradient id="battR" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#c3c8ce"/><stop offset="1" stop-color="#9ea4ab"/></linearGradient>
  <filter id="blur3" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="3"/></filter>
</defs>"""] + _tower(k) + ["</svg>"])


def background(n: int) -> str:
    F = "Helvetica, Arial, sans-serif"
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', DEFS,
         f'<rect width="{W}" height="{H}" rx="28" fill="url(#sky)"/>']
    # ---------------- plot: shadow, soil, lawn, paving
    X1, Y1 = 21.0, 14.0
    sh = [P(0, 0, 0), P(X1, 0, 0), P(X1, Y1, 0), P(0, Y1, 0)]
    o.append(poly([(x + 18, y + 26) for x, y in sh], "#000", 'opacity="0.6" filter="url(#blur6)"'))
    o.append(poly([P(0, Y1, 0), P(X1, Y1, 0), P(X1, Y1, -0.7), P(0, Y1, -0.7)], "url(#soilL)"))
    o.append(poly([P(X1, 0, 0), P(X1, Y1, 0), P(X1, Y1, -0.7), P(X1, 0, -0.7)], "url(#soilR)"))
    o.append(ground(0, 0, X1, Y1, "url(#lawn)"))
    # paving strip along the front of the house, path, driveway (concrete slabs)
    o.append(ground(2.4, 10.0, 12.6, 11.2, "url(#paving)"))
    o.append(ground(8.2, 11.2, 9.6, Y1, "url(#paving)"))
    for k in range(1, 5):
        a, b = P(8.2, 11.2 + k * 0.56), P(9.6, 11.2 + k * 0.56)
        o.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#5c5b58" stroke-width="0.8"/>')
    o.append(ground(13.0, 8.0, 19.8, Y1, "url(#paving)"))
    for k in range(1, 6):
        a, b = P(13.0, 8.0 + k * 1.0), P(19.8, 8.0 + k * 1.0)
        o.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#5c5b58" stroke-width="0.7" opacity="0.8"/>')
    # warm light spill from the windows onto the paving / lawn
    for (x, y) in ((6.3, 11.0), (10.6, 11.0)):
        c = P(x, y, 0)
        o.append(f'<ellipse cx="{c[0]:.1f}" cy="{c[1]:.1f}" rx="70" ry="26" fill="url(#spill)"/>')
    # faint static flow lines
    for pth, col in FLOWS.values():
        o.append(f'<path d="{pth}" fill="none" stroke="{col}" stroke-opacity="0.13" stroke-width="2.5" '
                 f'stroke-linecap="round" stroke-linejoin="round"/>')
    # back tree and grasses left of the house (behind it in this view)
    o.append(_tree(1.6, 2.2, 5.8, 1.5))
    for (x, y) in ((0.6, 7.6), (1.0, 8.6), (1.5, 6.8)):
        o.append(_grasses(x, y, 6))
    # ---------------- house: contact shadow
    o.append(poly([P(3.0, 3.0), P(12.0, 3.0), P(12.6, 10.6), P(3.0, 10.6)], "#000", 'opacity="0.35" filter="url(#blur3)"'))
    # lower volume (plaster)
    o.append(box(3.0, 3.0, 0.0, 12.0, 10.0, 3.2, "url(#roof)", "url(#plasterR)", "url(#plasterL)"))
    # parapet edge lower roof
    o.append(box(3.0, 9.8, 3.2, 5.0, 10.0, 3.4, "#d8d7d2", "#b5b3ad", "#e2e1dc"))
    o.append(box(3.0, 3.0, 3.2, 3.2, 10.0, 3.4, "#d8d7d2", "#b5b3ad", "#e2e1dc"))
    o.append(box(5.0, 9.8, 3.2, 12.0, 10.0, 3.4, "#d8d7d2", "#b5b3ad", "#e2e1dc"))
    o.append(box(11.8, 3.0, 3.2, 12.0, 10.0, 3.4, "#d8d7d2", "#b5b3ad", "#e2e1dc"))
    # lower floor glazing (front and side)
    o.append(_window_y(5.9, 7.9, 10.0, 0.15, 2.75, mullions=1))
    o.append(_window_y(9.7, 11.5, 10.0, 0.15, 2.75, mullions=1))
    o.append(_window_x(4.2, 8.6, 12.0, 0.15, 2.75, mullions=2))
    # front door (wood) with canopy
    o.append(yface(8.35, 9.35, 10.0, 0.0, 2.45, "url(#wood)"))
    o.append(yface(8.45, 8.55, 10.0, 0.25, 2.3, "#e8c99a"))
    o.append(box(8.0, 10.0, 2.6, 9.9, 10.9, 2.75, "#3c4046", "#2a2d31", "#33363b"))
    lamp = P(9.6, 10.0, 2.1)
    o.append(f'<circle cx="{lamp[0]:.1f}" cy="{lamp[1]:.1f}" r="16" fill="url(#spill)"/>'
             f'<circle cx="{lamp[0]:.1f}" cy="{lamp[1]:.1f}" r="1.6" fill="#ffe7b5"/>')
    # upper volume (anthracite cladding) with wood slat section
    o.append(poly([P(5.0, 3.0, 3.2), P(12.0, 3.0, 3.2), P(12.3, 8.4, 3.2), P(5.0, 8.4, 3.2)], "#000",
                  'opacity="0.25" filter="url(#blur3)"'))
    o.append(box(5.0, 3.0, 3.2, 12.0, 8.2, 6.3, "url(#roof)", "url(#darkR)", "url(#darkL)"))
    for k in range(29):
        xk = 5.15 + k * 0.12
        o.append(yface(xk, xk + 0.07, 8.2, 3.25, 6.25, "url(#wood)"))
    o.append(_window_y(8.9, 11.5, 8.2, 3.9, 5.7, mullions=2))
    o.append(_window_x(3.8, 6.0, 12.0, 3.9, 5.7, mullions=1))
    # upper parapet
    o.append(box(5.0, 8.0, 6.3, 12.0, 8.2, 6.45, "#5e636a", "#3b3f45", "#4d5259"))
    o.append(box(11.8, 3.0, 6.3, 12.0, 8.2, 6.45, "#5e636a", "#3b3f45", "#4d5259"))
    o.append(box(5.0, 3.0, 6.3, 5.2, 8.2, 6.45, "#5e636a", "#3b3f45", "#4d5259"))
    # solar panels on the upper roof: 2 rows x 4
    for row, y0 in enumerate((3.55, 5.55)):
        for col in range(4):
            o.append(_pv_panel(5.55 + col * 1.58, y0, 1.5, 1.45, 6.45, 0.35))
    # ---------------- batteries on the front wall + hub
    for k in range(1, n + 1):
        o.extend(_tower(k))
    o.append(box(5.15, 10.0, 1.15, 5.85, 10.18, 1.75, "#3a3f46", "#2a2e33", "#34383e",
                 'stroke="#80878f" stroke-width="0.5"'))
    o.append(f'<circle cx="{HUB[0]:.1f}" cy="{HUB[1]:.1f}" r="2.8" fill="#4dabf7"/>')
    # planter with grasses along the front
    o.append(box(9.9, 10.15, 0.0, 12.4, 10.75, 0.35, "#4a4d52", "#3a3d41", "#55595e"))
    for k in range(6):
        o.append(_grasses(10.15 + k * 0.4, 10.45))
    # ---------------- garage
    o.append(poly([P(12.6, 3.0), P(18.6, 3.0), P(19.0, 8.5), P(12.6, 8.5)], "#000", 'opacity="0.35" filter="url(#blur3)"'))
    o.append(box(12.6, 3.0, 0.0, 18.4, 8.0, 2.9, "url(#roof)", "url(#plasterR)", "url(#plasterL)"))
    o.append(box(12.6, 7.85, 2.9, 18.4, 8.0, 3.05, "#d8d7d2", "#b5b3ad", "#e2e1dc"))
    o.append(box(18.25, 3.0, 2.9, 18.4, 8.0, 3.05, "#d8d7d2", "#b5b3ad", "#e2e1dc"))
    o.append(yface(14.2, 17.9, 8.0, 0.0, 2.35, "url(#garageDoor)"))
    for k in range(1, 6):
        a, b = P(14.2, 8.0, k * 0.39), P(17.9, 8.0, k * 0.39)
        o.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#2f3237" stroke-width="0.8"/>')
    o.append(_window_x(4.0, 6.6, 18.4, 1.2, 2.3, mullions=1))
    # socket and granny charger cable to the car
    o.append(yface(13.1, 13.4, 8.0, 0.6, 0.9, "#f1f2f3", 'stroke="#8f969d" stroke-width="0.5"'))
    o.append(f'<path d="M{SOCKET[0]:.1f},{SOCKET[1]:.1f} C{SOCKET[0] + 2:.1f},{SOCKET[1] + 38:.1f} '
             f'{PORT[0] - 28:.1f},{PORT[1] + 30:.1f} {PORT[0]:.1f},{PORT[1]:.1f}" fill="none" stroke="#15171a" '
             f'stroke-width="2.6" stroke-linecap="round"/>')
    mid = (SOCKET[0] + (PORT[0] - SOCKET[0]) * 0.45, SOCKET[1] + 30)
    o.append(f'<rect x="{mid[0] - 7:.1f}" y="{mid[1] - 4:.1f}" width="14" height="8" rx="2" fill="#2a2f35" '
             f'stroke="#555c64" stroke-width="0.6"/>')
    # ---------------- grid connection cabinet
    o.append(poly([P(0.6, 11.9, 0), P(1.4, 11.9, 0), P(1.65, 12.75, 0), P(0.6, 12.75, 0)], "#000",
                  'opacity="0.35" filter="url(#blur3)"'))
    o.append(box(0.6, 11.9, 0.0, 1.4, 12.4, 1.25, "#c9ccd0", "#8f949a", "url(#cab)",
                 'stroke="#6c7177" stroke-width="0.5" stroke-linejoin="round"'))
    a, b = P(0.7, 12.4, 0.95), P(1.3, 12.4, 0.95)
    o.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#f0b400" stroke-width="2.2"/>')
    # ---------------- car, front tree, garden lights
    o.append(_car())
    o.append(_tree(20.0, 2.6, 5.0, 1.3))
    for (x, y) in ((7.9, 12.5), (10.0, 12.5), (13.0, 13.4)):
        c = P(x, y, 0.45)
        b0 = P(x, y, 0)
        o.append(f'<line x1="{b0[0]:.1f}" y1="{b0[1]:.1f}" x2="{c[0]:.1f}" y2="{c[1]:.1f}" stroke="#2c2f33" stroke-width="2"/>'
                 f'<ellipse cx="{b0[0]:.1f}" cy="{b0[1]:.1f}" rx="16" ry="7" fill="url(#spill)"/>'
                 f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="1.8" fill="#ffe2a8"/>')
    for (x, y) in ((6.0, 13.0), (12.0, 12.8)):
        o.append(_grasses(x, y, 6))
    # ---------------- film grain for a less flat look
    o.append(f'<rect width="{W}" height="{H}" rx="28" filter="url(#grain)" opacity="0.6"/>')
    # captions under the values
    for key, (x, y, cap) in LABELS.items():
        o.append(f'<text x="{x}" y="{y + 40}" text-anchor="middle" font-family="{F}" font-weight="700" '
                 f'font-size="26" letter-spacing="3" fill="#c9d2dd" stroke="#0b0e13" stroke-width="4" '
                 f'paint-order="stroke">{cap}</text>')
    o.append("</svg>")
    return "\n".join(o)


def flow(key: str, reverse: bool = False) -> str:
    pth, col = FLOWS[key]
    direction = "reverse" if reverse else "normal"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>
  @keyframes f {{ from {{ stroke-dashoffset: 0; }} to {{ stroke-dashoffset: -60; }} }}
  .g {{ fill: none; stroke: {col}; stroke-width: 9; stroke-opacity: 0.4; stroke-linecap: round; stroke-linejoin: round; filter: url(#b); }}
  .c {{ fill: none; stroke: {col}; stroke-width: 1.6; stroke-opacity: 0.55; stroke-linecap: round; stroke-linejoin: round; }}
  .l {{ fill: none; stroke: {col}; stroke-width: 3.4; stroke-linecap: round; stroke-linejoin: round;
        stroke-dasharray: 12 18; animation: f 1.2s linear infinite; animation-direction: {direction}; }}
</style>
<defs><filter id="b" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="4"/></filter></defs>
<path class="g" d="{pth}"/>
<path class="c" d="{pth}"/>
<path class="l" d="{pth}"/>
</svg>
"""


def files(n_values=(1, 2, 3)) -> dict:
    out = {f"huis_{n}sets.svg": background(n) for n in n_values}
    out.update({f"toren_{k}.svg": tower(k) for k in (2, 3)})
    out["flow_net_afname.svg"] = flow("net")
    out["flow_net_teruglevering.svg"] = flow("net", reverse=True)
    out["flow_zon.svg"] = flow("zon")
    out["flow_huis.svg"] = flow("huis")
    out["flow_accu_laden.svg"] = flow("accu")
    out["flow_accu_ontladen.svg"] = flow("accu", reverse=True)
    out["flow_ev.svg"] = flow("ev")
    return out
