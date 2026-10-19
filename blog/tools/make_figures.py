#!/usr/bin/env python3
"""Generate the four data figures for the blog entry as standalone SVGs.

Palette taken from blog/static/style.css (verified reference tokens):
  ink #222629  muted #677179  line #dce1e4  tint #f4f7f8
  accent #28627b  accent-light #bccdd5  orange #ac6538
"""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "figures")
SERIF = "Georgia, 'Source Serif 4', 'Times New Roman', serif"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif"
MONO = "ui-monospace, Menlo, Consolas, monospace"
INK, MUTED, LINE, TINT = "#222629", "#677179", "#dce1e4", "#f4f7f8"
ACCENT, ACCENT_L, ORANGE = "#28627b", "#bccdd5", "#ac6538"

os.makedirs(OUT, exist_ok=True)


def write(name, body):
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        f.write(body)
    print("wrote", path, len(body), "bytes")


def text(x, y, s, size=12, fill=MUTED, anchor="start", family=SANS, weight="400", style=""):
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" '
        f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}" {style}>{s}</text>'
    )


# ---------------------------------------------------------------- figure 1
# Scan entry with a warm camera, emulator: tap -> first picture on screen.
def hero():
    W, H = 720, 214
    x0, x1 = 150.0, 660.0
    ms0, ms1 = 0.0, 560.0
    sc = (x1 - x0) / (ms1 - ms0)

    def X(ms):
        return x0 + ms * sc

    rows = [
        # (label, y, kind, data)
        ("A1 mobile_scanner", 52, "band", (88, 228, "device open 88–228 ms")),
        ("P2 camera2-direct", 96, "dot", (179, 75, 204, "live frame 179 ms")),
        ("P4 camera2 + ML Kit", 140, "dot", (153, 108, 255, "live 153 ms")),
        ("P1 prewarm (CameraX)", 184, "split", None),
    ]
    p = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
             f'role="img" aria-labelledby="f1t f1d" width="{W}" height="{H}">')
    p.append('<title id="f1t">Time from tapping Scan to a live camera frame on the emulator</title>')
    p.append('<desc id="f1d">A1 opens the device at 88 to 228 milliseconds and never reports frames. '
             'P2 shows a live frame at 179 ms, P4 at 153 ms. P1 paints a frozen frame at 12 ms and live '
             'frames at 206 to 524 ms.</desc>')

    for ms in range(0, 501, 100):
        gx = X(ms)
        p.append(f'<line x1="{gx:.1f}" y1="30" x2="{gx:.1f}" y2="200" stroke="{LINE}" stroke-width="1"/>')
        p.append(text(gx, 212, f"{ms}", 10, MUTED, "middle", MONO))
    p.append(text(X(520), 212, "ms", 10, MUTED, "start", MONO))

    for label, y, kind, data in rows:
        p.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{LINE}" stroke-width="1"/>')
        p.append(text(x0 - 12, y + 4, label, 12, INK, "end"))

    # A1: device-open band
    y = 52
    a, b, note = 88, 228, "device open 88–228 ms"
    p.append(f'<rect x="{X(a):.1f}" y="{y-9}" width="{X(b)-X(a):.1f}" height="18" rx="4" '
             f'fill="{TINT}" stroke="{MUTED}" stroke-width="1" stroke-dasharray="3 2"/>')
    p.append(text((X(a) + X(b)) / 2, y - 16, note, 11, MUTED, "middle"))
    p.append(text(X(b) + 10, y + 4, "live frame not instrumented", 11, MUTED, "start", SANS, "400", 'font-style="italic"'))

    for y, med, a, b, note in [
        (96, 179, 75, 204, "live frame 179 (75–204)"),
        (140, 153, 108, 255, "live frame 153 (108–255)"),
    ]:
        p.append(f'<line x1="{X(a):.1f}" y1="{y}" x2="{X(b):.1f}" y2="{y}" stroke="{ACCENT}" stroke-width="6" '
                 f'stroke-linecap="round" opacity="0.35"/>')
        p.append(f'<circle cx="{X(med):.1f}" cy="{y}" r="5" fill="{ACCENT}"/>')
        p.append(text(X(b) + 10, y + 4, note, 11, ACCENT, "start"))

    # P1: frozen-frame dot + live band
    y = 184
    p.append(f'<circle cx="{X(12):.1f}" cy="{y}" r="5" fill="{ORANGE}"/>')
    p.append(text(X(12) + 9, y + 4, "frozen frame 12 ms", 11, ORANGE, "start"))
    p.append(f'<line x1="{X(206):.1f}" y1="{y}" x2="{X(524):.1f}" y2="{y}" stroke="{ACCENT}" stroke-width="6" '
             f'stroke-linecap="round" opacity="0.35"/>')
    p.append(f'<circle cx="{X(487):.1f}" cy="{y}" r="5" fill="{ACCENT}"/>')
    p.append(text(712, y + 4, "live 206–524 ms", 11, ACCENT, "end"))

    p.append("</svg>")
    write("scan-entry.svg", "\n".join(p))


# ---------------------------------------------------------------- figure 2
# Cold first scan entry, emulator: where the 5.76 s went.
def decomposition():
    W, H = 720, 168
    x0 = 150.0
    bar_end = 680.0
    px_total = bar_end - x0
    total = 5.76
    sc = px_total / total
    p = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
             f'role="img" aria-labelledby="f2t f2d" width="{W}" height="{H}">')
    p.append('<title id="f2t">Where the cold 5.76 second bind went</title>')
    p.append('<desc id="f2d">The cold mobile_scanner bind takes 5.76 seconds: about 0.43 seconds of camera '
             'work and about 5.33 seconds of CameraX and scanner overhead. The direct camera2 path opens and '
             'delivers a first frame in 0.43 seconds cold.</desc>')

    cam = 0.43 * sc
    y1, y2, h = 46, 108, 26

    p.append(text(8, y1 + 17, "A1 cold, mobile_scanner", 11, INK, "start"))
    p.append(f'<rect x="{x0}" y="{y1}" width="{cam:.1f}" height="{h}" fill="{ACCENT}"/>')
    p.append(f'<rect x="{x0+cam:.1f}" y="{y1}" width="{px_total-cam:.1f}" height="{h}" fill="{ORANGE}"/>')
    p.append(f'<line x1="{x0+cam/2:.1f}" y1="{y1}" x2="{x0+12:.1f}" y2="{y1-22}" stroke="{LINE}" stroke-width="1"/>')
    p.append(text(x0 + 14, y1 - 26, "camera 0.43 s", 11, ACCENT))
    p.append(text(x0 + cam + 14, y1 + 17, "CameraX + mobile_scanner \u2248 5.33 s", 11, "#ffffff", "start", SANS, "600"))
    p.append(text(714, y1 + 17, "5.76 s", 12, INK, "end", MONO))

    p.append(text(8, y2 + 17, "P1 prewarm, camera2", 11, INK, "start"))
    p.append(f'<rect x="{x0}" y="{y2}" width="{cam:.1f}" height="{h}" fill="{ACCENT}"/>')
    p.append(text(x0 + cam + 10, y2 + 17, "0.43 s total", 12, ACCENT, "start", MONO))

    p.append("</svg>")
    write("cold-decomposition.svg", "\n".join(p))


# ---------------------------------------------------------------- figure 3
# First live frame after returning from RFID: emulator vs S24 FE (medians).
def inversion():
    W, H = 720, 292
    groups = [
        ("P1 prewarm", 368, 685),
        ("P2 camera2", 179, 916),
        ("P3 CameraX + ML Kit", 368, 834),
        ("P4 camera2 + ML Kit", 153, 1426),
    ]
    base_y = 232.0
    scale = 168.0 / 1500.0  # px per ms
    x0 = 96.0
    gw = (700.0 - x0) / len(groups)
    bw = 22.0
    p = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
             f'role="img" aria-labelledby="f3t f3d" width="{W}" height="{H}">')
    p.append('<title id="f3t">First live frame after an RFID detour</title>')
    p.append('<desc id="f3d">On the emulator P4 is fastest at 153 milliseconds; on the S24 FE P1 is fastest '
             'at 685 milliseconds and P4 is slowest at 1426 milliseconds.</desc>')

    # legend
    p.append(f'<rect x="{x0}" y="24" width="12" height="12" fill="{ACCENT_L}"/>')
    p.append(text(x0 + 18, 34, "emulator (pixel_bench)", 11, MUTED))
    p.append(f'<rect x="{x0 + 178}" y="24" width="12" height="12" fill="{ACCENT}"/>')
    p.append(text(x0 + 196, 34, "Galaxy S24 FE", 11, MUTED))

    for ms in (0, 500, 1000, 1500):
        gy = base_y - ms * scale
        p.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="700" y2="{gy:.1f}" stroke="{LINE}" stroke-width="1" '
                 + ('stroke-dasharray="3 3"' if ms else "") + '/>')
        p.append(text(x0 - 10, gy + 4, f"{ms}", 10, MUTED, "end", MONO))
    p.append(text(x0 - 10, 46, "ms", 10, MUTED, "end", MONO))

    for i, (label, emu, phone) in enumerate(groups):
        cx = x0 + gw * i + gw / 2
        for j, (val, color, sw) in enumerate([(emu, ACCENT_L, 0), (phone, ACCENT, 1)]):
            bx = cx - bw - 2 + j * (bw + 4)
            by = base_y - val * scale
            p.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw}" height="{val*scale:.1f}" fill="{color}"/>')
            p.append(text(bx + bw / 2, by - 6, f"{val}", 10, INK, "middle", MONO))
        p.append(text(cx, base_y + 22, label, 11, INK, "middle"))

    p.append("</svg>")
    write("ranking-inversion.svg", "\n".join(p))


# ---------------------------------------------------------------- figure 4
# Leaving Scan for RFID: when the camera is really free, when the card is read.
def arbiter():
    W, H = 720, 176
    x0, x1 = 132.0, 680.0
    t0, t1 = 0.0, 1.6
    sc = (x1 - x0) / (t1 - t0)

    def X(s):
        return x0 + s * sc

    p = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
             f'role="img" aria-labelledby="f4t f4d" width="{W}" height="{H}">')
    p.append('<title id="f4t">Camera release and RFID start after leaving the scan tab</title>')
    p.append('<desc id="f4d">The mobile_scanner apps release the camera 1.29 seconds after the tap and start '
             'RFID at 1.48 seconds; the plugin apps release at 0.19 seconds and start RFID at 0.38 seconds.</desc>')

    rows = [
        ("A1 / A2 mobile_scanner", 58, 1287, 1477),
        ("P1–P4 plugin", 124, 188, 384),
    ]

    for label, y, rel, rfd in rows:
        p.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" stroke="{LINE}" stroke-width="1"/>')
        p.append(text(8, y + 4, label, 11, INK, "start"))
        p.append(f'<circle cx="{X(0.005):.1f}" cy="{y}" r="3" fill="none" stroke="{MUTED}" stroke-width="1" stroke-dasharray="2 2"/>')
        p.append(f'<circle cx="{X(rel/1000.0):.1f}" cy="{y}" r="5.5" fill="{ORANGE}"/>')
        p.append(f'<circle cx="{X(rfd/1000.0):.1f}" cy="{y}" r="5.5" fill="{ACCENT}"/>')

    p.append(text(X(0.005) + 8, 58 - 12, "stop() ack \u2248 5 ms", 10, MUTED))
    p.append(text(X(1.287), 58 - 12, "camera really free 1.29 s", 11, ORANGE, "middle"))
    p.append(text(X(1.477), 58 + 20, "RFID ok 1.48 s", 11, ACCENT, "middle"))
    p.append(text(X(0.188) + 10, 124 - 12, "free 0.19 s", 11, ORANGE))
    p.append(text(X(0.384) + 10, 124 - 12, "RFID ok 0.38 s", 11, ACCENT))

    # dead-time arrow between the two release points
    ya = 91
    p.append(f'<line x1="{X(0.188):.1f}" y1="{ya}" x2="{X(1.287):.1f}" y2="{ya}" stroke="{ORANGE}" '
             f'stroke-width="1.5"/>')
    p.append(f'<path d="M {X(0.188):.1f} {ya} l 7 -4 v 8 z" fill="{ORANGE}"/>')
    p.append(f'<path d="M {X(1.287):.1f} {ya} l -7 -4 v 8 z" fill="{ORANGE}"/>')
    p.append(text((X(0.188) + X(1.287)) / 2, ya - 5, "\u2248 1.1 s of dead time, every card tap", 11, ORANGE, "middle"))

    for s in (0.0, 0.5, 1.0, 1.5):
        p.append(f'<line x1="{X(s):.1f}" y1="146" x2="{X(s):.1f}" y2="151" stroke="{MUTED}" stroke-width="1"/>')
        p.append(text(X(s), 164, f"{s:.1f}", 10, MUTED, "middle", MONO))
    p.append(text(X(1.6) + 6, 164, "s", 10, MUTED, "start", MONO))

    p.append("</svg>")
    write("arbiter-handoff.svg", "\n".join(p))


hero()
decomposition()
inversion()
arbiter()
