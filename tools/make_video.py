"""Assemble the captioned demo video (1080p, H.264) from deck slides, the recorded journey and result frames."""
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECK_PDF = ROOT / "deliverables" / "HRRS_VV_Presentation_Raktim.pdf"
JOURNEY = ROOT / "reports" / "demo_recording" / "guest_journey.webm"
TERMINAL = Path(__file__).resolve().parents[1] / "docs" / "figures" / "video" / "terminal.png"
OUT = ROOT / "deliverables" / "HRRS_Demo_Video_Raktim.mp4"
FONT = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
W = Path(tempfile.mkdtemp(prefix="vid_"))

subprocess.run(["pdftoppm", "-png", "-scale-to-x", "1920", "-scale-to-y", "1080", str(DECK_PDF), str(W / "s")], check=True,
               capture_output=True)
slides = sorted(W.glob("s-*.png"))
S = lambda n: slides[n - 1]  # noqa: E731  (1-based slide numbers)

STORY = [  # (image or 'journey', seconds, caption)
    (S(1), 5, "Raktim Chandra · Software Verification & Validation · Hotel Room Reservation System"),
    (S(3), 6, "Every number in this video comes from the real, automated test run"),
    (S(7), 5, "The system is built so each layer maps onto a test level"),
    ("journey", None, None),
    (S(22), 6, "Black-box: decision table DT-1 — 8 refund rules, one executed test per rule"),
    (S(24), 5, "State transition: all 30 cells of the state table, 24 illegal moves rejected"),
    (S(28), 6, "White-box: V(G) = 8 computed three ways → 8 basis-path tests"),
    (S(31), 5, "MC/DC: every condition shown to independently change the decision"),
    (TERMINAL, 6, "pytest: 558 passed, 2 skipped, 0 failed · 100 % statement coverage"),
    (S(34), 6, "Mutation testing: 85.9 % → 100 % as surviving mutants guided new tests"),
    (S(35), 6, "Fault seeding: one missed bug exposed a weak test — fixed, now 12 / 12"),
    (S(41), 6, "Load testing found DEF-004; tuning cut booking p95 latency by 70 %"),
    (S(48), 6, "Five real defects, each found by a different technique, all regression-tested"),
    (S(50), 5, "Metrics: coverage, mutation score, defect density, DRE"),
    (S(54), 5, "Thank you — Raktim Chandra · RA2311033010038 · SRMIST"),
]
JOURNEY_CAPS = [(0, 9.5, "1 · Register — a weak password is rejected (FR-02)"), (9.5, 15.5, "2 · Account created; the guest signs in"),
                (15.5, 19, "3 · Search 2 → 5 Nov: live availability (FR-03)"), (19, 23, "4 · Price: ₹12,000 + 5 % GST = ₹12,600 (FR-06)"),
                (23, 28, "5 · Rooms held; card paid inside the 15-minute window (FR-08)"), (28, 30.5, "6 · Booking CONFIRMED (FR-09)"),
                (30.5, 40, "7 · Cancelled 25 days ahead → 100 % refund, rule R3 (FR-07)")]


def caption_filter(items):
    parts = ["drawbox=x=0:y=ih-110:w=iw:h=110:color=0x14213D@0.88:t=fill"]
    for a, b, text in items:
        tf = W / f"cap_{abs(hash(text))}.txt"
        tf.write_text(text)
        en = f":enable='between(t,{a},{b})'" if b is not None else ""
        parts.append(f"drawtext=fontfile={FONT}:textfile={tf}:expansion=none:fontsize=38:fontcolor=white:x=60:y=h-75{en}")
    return ",".join(parts)


segs = []
for k, (src, secs, cap) in enumerate(STORY):
    out = W / f"seg{k:02d}.mp4"
    if src == "journey":
        vf = ("scale=1700:-2,pad=1920:1080:(ow-iw)/2:30:color=0xF6F1E7," + caption_filter(JOURNEY_CAPS))
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(JOURNEY), "-vf", vf, "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(out)]
    else:
        vf = f"scale=1920:1080,{caption_filter([(0, None, cap)])},fade=t=in:st=0:d=0.4,fade=t=out:st={secs - 0.4}:d=0.4"
        cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-t", str(secs), "-i", str(src), "-vf", vf, "-r", "30", "-c:v", "libx264",
               "-pix_fmt", "yuv420p", "-an", str(out)]
    subprocess.run(cmd, check=True)
    segs.append(out)

lst = W / "list.txt"
lst.write_text("".join(f"file '{p}'\n" for p in segs))
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(OUT)], check=True)
dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(OUT)], capture_output=True, text=True).stdout
print(OUT, round(float(dur), 1), "s")
