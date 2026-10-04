#!/usr/bin/env python3
"""Build a print-ready, vector infographic atlas from the KPK study's 46-item matrix.

Usage: /tmp/pdfenv/bin/python build_infographics.py
The source recommendation text, leads, cost notes and KPIs are parsed directly from
research/chapters/18_statistical_annex.md so the action cards stay tied to the study.
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parent
ANNEX = ROOT / "research" / "chapters" / "18_statistical_annex.md"
OUTDIR = ROOT / "research" / "deliverables"
OUTFILE = OUTDIR / "KPK_Security_Recommendations_Infographics.pdf"
PAGE_W, PAGE_H = landscape(A4)

# A restrained editorial palette: ink/navy for authority, teal for institutions,
# gold for investment, and coral for urgent/early-phase actions.
NAVY = HexColor("#0B3558")
INK = HexColor("#172A3A")
TEAL = HexColor("#167D80")
TEAL_LIGHT = HexColor("#E4F2F1")
BLUE = HexColor("#357FA3")
BLUE_LIGHT = HexColor("#E8F1F6")
GOLD = HexColor("#D6A23A")
GOLD_LIGHT = HexColor("#FBF3DE")
CORAL = HexColor("#C85D4B")
CORAL_LIGHT = HexColor("#F9E9E5")
GREEN = HexColor("#4C8A6A")
GREEN_LIGHT = HexColor("#EAF3ED")
PAPER = HexColor("#F4F7F8")
WHITE = colors.white
LINE = HexColor("#D7E1E5")
MUTED = HexColor("#607384")
PALE = HexColor("#ECF1F3")

PHASE_COLORS = {"I": CORAL, "II": TEAL, "III": GOLD, "C": BLUE}
PHASE_LIGHTS = {"I": CORAL_LIGHT, "II": TEAL_LIGHT, "III": GOLD_LIGHT, "C": BLUE_LIGHT}

FONT_REG = "DV"
FONT_BOLD = "DV-Bold"
font_reg_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
font_bold_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
if font_reg_path.exists() and font_bold_path.exists():
    pdfmetrics.registerFont(TTFont(FONT_REG, str(font_reg_path)))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(font_bold_path)))
else:  # portable fallback; reportlab's built-in fonts are always available
    FONT_REG, FONT_BOLD = "Helvetica", "Helvetica-Bold"


def clean(s: str) -> str:
    """Remove lightweight Markdown while preserving the underlying wording."""
    s = s.replace("**", "").replace("`", "")
    s = re.sub(r"(?<!\w)\*(.*?)\*(?!\w)", r"\1", s)
    return s.strip()


def markup(s: str) -> str:
    """Escape source wording and convert plain newlines to Paragraph line breaks."""
    s = str(s).replace("**", "").replace("`", "")
    s = escape(s)
    s = s.replace("\n", "<br/>")
    # Escape already protects any embedded source text from being interpreted as HTML.
    return s


def parse_recommendations() -> list[dict[str, str]]:
    if not ANNEX.exists():
        raise FileNotFoundError(f"Recommendation source not found: {ANNEX}")
    text = ANNEX.read_text(encoding="utf-8")
    if "# RECOMMENDATIONS MATRIX" not in text:
        raise ValueError("Could not locate RECOMMENDATIONS MATRIX in statistical annex")
    matrix = text.split("# RECOMMENDATIONS MATRIX", 1)[1]
    result: list[dict[str, str]] = []
    for line in matrix.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 7 or not cells[0].isdigit():
            continue
        result.append({
            "id": cells[0],
            "text": clean(cells[1]),
            "source": clean(cells[2]),
            "phase": clean(cells[3]),
            "lead": clean(cells[4]),
            "cost": clean(cells[5]),
            "kpi": clean(cells[6]).replace("casuatly", "casualty"),
        })
    ids = [int(r["id"]) for r in result]
    if ids != list(range(1, 47)):
        raise ValueError(f"Expected exactly recommendations 1–46 in order; got {ids}")
    return result


RECS = parse_recommendations()
REC_BY_ID = {int(r["id"]): r for r in RECS}

PILLARS = [
    {
        "name": "Fiscal federalism & accountable state",
        "color": NAVY,
        "light": BLUE_LIGHT,
        "ids": [1, 2, 25, 26, 31, 38, 39],
        "copy": "Make the merger's fiscal promise rule-based, transparent and answerable.",
    },
    {
        "name": "Police protection & capable security",
        "color": CORAL,
        "light": CORAL_LIGHT,
        "ids": [3, 4, 8, 10, 11, 12, 13, 14, 30, 37, 40, 43, 44],
        "copy": "Protect frontline personnel and build civilian-led, accountable capability.",
    },
    {
        "name": "Justice, rights & public voice",
        "color": TEAL,
        "light": TEAL_LIGHT,
        "ids": [5, 7, 15, 16, 18, 24, 32, 33],
        "copy": "Make due process, courts, local voice and redress visible in daily life.",
    },
    {
        "name": "Border management & peace transition",
        "color": BLUE,
        "light": BLUE_LIGHT,
        "ids": [6, 9, 17, 34, 35, 41, 42],
        "copy": "Manage cross-border risk through verification, mediation and safe recovery.",
    },
    {
        "name": "Prevention & reintegration",
        "color": GOLD,
        "light": GOLD_LIGHT,
        "ids": [19, 20, 21, 22, 23],
        "copy": "Make rehabilitation lawful, independently tested and connected to aftercare.",
    },
    {
        "name": "Human development & resilience",
        "color": GREEN,
        "light": GREEN_LIGHT,
        "ids": [27, 28, 29, 36, 45, 46],
        "copy": "Invest in education, livelihoods, climate resilience and community benefit.",
    },
]

# Assert the thematic navigation is an exact, non-overlapping cover of all actions.
_pillar_ids = [n for p in PILLARS for n in p["ids"]]
if sorted(_pillar_ids) != list(range(1, 47)) or len(_pillar_ids) != len(set(_pillar_ids)):
    raise ValueError("Pillar map must assign each recommendation exactly once")


def phase_tokens(phase: str) -> set[str]:
    out = set(re.findall(r"(?<![A-Z])I{1,3}(?![A-Z])", phase.upper()))
    if re.search(r"(?<![A-Z])C(?![A-Z])", phase.upper()):
        out.add("C")
    return out


def register_page(c: "NumberedCanvas", section: str, title: str) -> None:
    key = f"page-{len(c._page_keys) + 1}"
    c._page_keys.append(key)
    c.bookmarkPage(key)
    c.addOutlineEntry(f"{section}: {title}", key, level=0, closed=False)


def para(c, text: str, x: float, top: float, width: float, *, size=9.5,
         leading=None, color=INK, bold=False, max_h=None, align=0,
         font=None, min_size=7.2) -> float:
    """Draw a wrapping text block from its top edge; shrink gently if necessary."""
    face = font or (FONT_BOLD if bold else FONT_REG)
    leading = leading or size * 1.28
    cur = size
    while True:
        style = ParagraphStyle(
            name=f"p_{cur}_{face}_{align}", fontName=face, fontSize=cur,
            leading=leading * (cur / size), textColor=color,
            alignment=align, spaceBefore=0, spaceAfter=0,
            splitLongWords=1, allowWidows=0, allowOrphans=0,
        )
        p = Paragraph(markup(text), style)
        _, h = p.wrap(width, 2000)
        if max_h is None or h <= max_h or cur <= min_size:
            p.drawOn(c, x, top - h)
            return h
        cur = max(min_size, cur - 0.35)


def draw_chip(c, label: str, x: float, y: float, *, fill=PALE, ink=NAVY,
              size=7.3, height=17, pad=7, stroke=None, bold=True) -> float:
    face = FONT_BOLD if bold else FONT_REG
    width = pdfmetrics.stringWidth(label, face, size) + 2 * pad
    c.setFillColor(fill)
    c.setStrokeColor(stroke or fill)
    c.roundRect(x, y, width, height, 7, fill=1, stroke=1 if stroke else 0)
    c.setFillColor(ink)
    c.setFont(face, size)
    c.drawCentredString(x + width / 2, y + (height - size) / 2 + 1.2, label)
    return width


def draw_id_cloud(c, ids, x, top, width, *, chip_h=17, gap_x=5, gap_y=5,
                  fill=BLUE_LIGHT, ink=NAVY, cols=None, font_size=7.2):
    x0 = x
    y = top - chip_h
    row = 0
    if cols is None:
        cols = max(1, int((width + gap_x) // (36 + gap_x)))
    for idx, n in enumerate(ids):
        if idx and idx % cols == 0:
            row += 1
            x0 = x
            y -= chip_h + gap_y
        w = draw_chip(c, f"#{n:02d}", x0, y, fill=fill, ink=ink,
                      size=font_size, height=chip_h, pad=6)
        x0 += w + gap_x
    return y - 2


def draw_card(c, x, y, w, h, *, fill=WHITE, stroke=LINE, radius=13,
              accent=None, shadow=False):
    if shadow:
        c.setFillColor(HexColor("#E6ECEF"))
        c.roundRect(x + 2, y - 2, w, h, radius, fill=1, stroke=0)
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(0.8)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)
    if accent:
        c.setFillColor(accent)
        c.roundRect(x, y, 6, h, radius, fill=1, stroke=0)
        c.rect(x + 3, y, 3, h, fill=1, stroke=0)


def start_page(c: "NumberedCanvas", section: str, title: str, subtitle: str = "",
               *, accent=TEAL, title_size=22) -> float:
    c.setFillColor(PAPER)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.rect(0, PAGE_H - 7, PAGE_W, 7, fill=1, stroke=0)
    c.setFillColor(MUTED)
    c.setFont(FONT_BOLD, 7.1)
    c.drawString(40, PAGE_H - 25, "KPK NORMALIZATION  /  VISUAL IMPLEMENTATION ATLAS")
    c.setFont(FONT_REG, 7.1)
    c.drawRightString(PAGE_W - 40, PAGE_H - 25, "46 ACTIONS  ·  6 WORKSTREAMS  ·  3 PHASES")
    c.setStrokeColor(LINE)
    c.setLineWidth(0.65)
    c.line(40, PAGE_H - 36, PAGE_W - 40, PAGE_H - 36)
    c.setFillColor(accent)
    c.setFont(FONT_BOLD, 8)
    c.drawString(40, PAGE_H - 57, section.upper())
    c.setFillColor(INK)
    c.setFont(FONT_BOLD, title_size)
    c.drawString(40, PAGE_H - 84, title)
    if subtitle:
        para(c, subtitle, 40, PAGE_H - 96, PAGE_W - 80,
             size=8.7, leading=11.1, color=MUTED, max_h=24)
    register_page(c, section, title)
    return PAGE_H - 130


class NumberedCanvas(rl_canvas.Canvas):
    """Canvas that adds a consistent, total-page footer and preserves bookmarks."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self._page_keys = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.setStrokeColor(LINE)
            self.setLineWidth(0.55)
            self.line(40, 31, PAGE_W - 40, 31)
            self.setFillColor(MUTED)
            self.setFont(FONT_REG, 6.8)
            self.drawString(40, 18, "POLICY VISUALS  ·  STUDY CUT-OFF 04 OCT 2026  ·  PKR COSTS ARE INDICATIVE")
            self.setFont(FONT_BOLD, 6.8)
            self.drawRightString(PAGE_W - 40, 18, f"{self._pageNumber} / {total}")
            rl_canvas.Canvas.showPage(self)
        rl_canvas.Canvas.save(self)


def draw_cover(c):
    c.setFillColor(NAVY)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # Abstract linked rings signal the three interlocking systems; no geographic
    # boundary is implied by the graphic.
    c.saveState()
    c.setStrokeColor(HexColor("#1D5273"))
    c.setLineWidth(1.0)
    for r in (72, 112, 153):
        c.circle(PAGE_W - 112, PAGE_H - 136, r, fill=0, stroke=1)
    c.setStrokeColor(HexColor("#28647F"))
    c.circle(PAGE_W - 112, PAGE_H - 136, 192, fill=0, stroke=1)
    c.restoreState()
    c.setFillColor(TEAL)
    c.rect(40, PAGE_H - 43, 48, 5, fill=1, stroke=0)
    c.setFillColor(HexColor("#DDE8ED"))
    c.setFont(FONT_BOLD, 8.3)
    c.drawString(40, PAGE_H - 65, "KPK SECURITY NORMALIZATION  /  IMPLEMENTATION ATLAS")
    title = "46 actions.\nOne sequenced pathway\nto durable peace."
    para(c, title, 40, PAGE_H - 112, 505, size=29, leading=35,
         color=WHITE, bold=True, max_h=138, min_size=25)
    para(c, "Visualising the recommendations for Normalizing the Security Situation of Khyber Pakhtunkhwa",
         42, PAGE_H - 254, 470, size=12.4, leading=17.4,
         color=HexColor("#D7E5EB"), max_h=40)
    # Action-count medallion.
    c.setFillColor(TEAL)
    c.circle(PAGE_W - 116, PAGE_H - 142, 49, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 31)
    c.drawCentredString(PAGE_W - 116, PAGE_H - 151, "46")
    c.setFont(FONT_BOLD, 7)
    c.drawCentredString(PAGE_W - 116, PAGE_H - 166, "RECOMMENDATIONS")
    # Three implementation horizons.
    labels = [("I", "0–2 YEARS", CORAL), ("II", "2–5 YEARS", TEAL), ("III", "5–15 YEARS", GOLD)]
    x = 42
    y = 141
    for roman, label, col in labels:
        c.setFillColor(col)
        c.roundRect(x, y, 226, 43, 10, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 10)
        c.drawString(x + 15, y + 25, f"PHASE {roman}")
        c.setFont(FONT_REG, 9)
        c.drawString(x + 15, y + 10, label)
        x += 244
    c.setFillColor(HexColor("#D7E5EB"))
    c.setFont(FONT_REG, 8.3)
    c.drawString(42, 101, "Six workstreams  ·  Cost and KPI on every action card  ·  Vector artwork for sharp printing")
    c.setFillColor(HexColor("#AFC5D0"))
    c.setFont(FONT_REG, 7.4)
    c.drawString(42, 74, "Study data cut-off: 4 October 2026  |  Visual pack prepared: 5 October 2026")
    register_page(c, "START HERE", "46 actions. One sequenced pathway to durable peace.")
    c.showPage()


def page_system_logic(c):
    start_page(c, "01  /  THE STUDY'S CENTRAL FRAME", "Normalization is a three-part system",
               "The monograph's core claim: force is necessary, but durable security depends on enforceable rights and a credible fiscal settlement too.",
               accent=TEAL)
    blocks = [
        ("01", "Organized\nviolence", "The state's capacity to protect people and prevent armed groups from governing by force.", "Recommendations 03–14, 30, 37, 40, 43–44", CORAL, CORAL_LIGHT),
        ("02", "Justice &\ngovernance", "The citizen's enforceable claim on the state: lawful process, functioning courts and local voice.", "Recommendations 05, 07, 15–18, 24, 32–33", TEAL, TEAL_LIGHT),
        ("03", "Fiscal\nfederalism", "The province's claim on national resources: timely, rule-based transfers that can build institutions.", "Recommendations 01–02, 25–26, 31, 38–39", GOLD, GOLD_LIGHT),
    ]
    x_positions = [44, 306, 568]
    y, h, w = 201, 241, 229
    for (num, title, body, refs, col, light), x in zip(blocks, x_positions):
        draw_card(c, x, y, w, h, fill=WHITE, accent=col, shadow=True)
        c.setFillColor(light)
        c.circle(x + 39, y + h - 39, 21, fill=1, stroke=0)
        c.setFillColor(col)
        c.setFont(FONT_BOLD, 11)
        c.drawCentredString(x + 39, y + h - 43, num)
        c.setFillColor(MUTED)
        c.setFont(FONT_BOLD, 7.1)
        c.drawString(x + 71, y + h - 36, "INTERLOCKING MONOPOLY")
        para(c, title, x + 18, y + h - 77, w - 36,
             size=17, leading=20, color=col, bold=True, max_h=47)
        c.setStrokeColor(LINE)
        c.line(x + 18, y + 101, x + w - 18, y + 101)
        para(c, body, x + 18, y + 88, w - 36, size=9.2, leading=12.5,
             color=INK, max_h=58)
        para(c, refs, x + 18, y + 33, w - 36, size=7.2, leading=9,
             color=MUTED, max_h=24)
    # Connectors across the model.
    c.setStrokeColor(HexColor("#A7B9C2"))
    c.setLineWidth(2)
    for x in (275, 537):
        c.line(x, 318, x + 26, 318)
        c.line(x + 21, 323, x + 26, 318)
        c.line(x + 21, 313, x + 26, 318)
    c.setFillColor(NAVY)
    c.roundRect(44, 101, PAGE_W - 88, 76, 12, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 10.4)
    c.drawString(62, 154, "THE NORMALIZATION TEST")
    para(c, "Repair all three together: security without rights loses cooperation; rights without security are unenforceable; transfers without accountability do not become services.",
         62, 141, PAGE_W - 124, size=9.4, leading=12, color=WHITE, max_h=28)
    c.showPage()


def page_pillars(c):
    start_page(c, "02  /  PORTFOLIO MAP", "Six workstreams carry the 46 actions",
               "The themes are a navigation aid: cross-cutting actions remain numbered and fully detailed in the recommendation cards.",
               accent=BLUE)
    left, gap, card_w, card_h = 40, 14, (PAGE_W - 80 - 2 * 14) / 3, 157
    top = 451
    row_gap = 13
    for idx, pillar in enumerate(PILLARS):
        row, col = divmod(idx, 3)
        x = left + col * (card_w + gap)
        y = top - card_h - row * (card_h + row_gap)
        draw_card(c, x, y, card_w, card_h, fill=WHITE, accent=pillar["color"])
        c.setFillColor(pillar["light"])
        c.circle(x + card_w - 30, y + card_h - 28, 17, fill=1, stroke=0)
        c.setFillColor(pillar["color"])
        c.setFont(FONT_BOLD, 10)
        c.drawCentredString(x + card_w - 30, y + card_h - 31.5, str(len(pillar["ids"])))
        para(c, pillar["name"], x + 17, y + card_h - 18, card_w - 63,
             size=11.4, leading=13.7, color=INK, bold=True, max_h=31)
        para(c, pillar["copy"], x + 17, y + card_h - 56, card_w - 34,
             size=8.1, leading=10.3, color=MUTED, max_h=31)
        c.setFillColor(MUTED)
        c.setFont(FONT_BOLD, 6.7)
        c.drawString(x + 17, y + 55, "ACTION IDS")
        draw_id_cloud(c, pillar["ids"], x + 17, y + 51, card_w - 34,
                      chip_h=14, gap_x=4, gap_y=2, fill=pillar["light"],
                      ink=pillar["color"], font_size=6.5, cols=6)
    # legend strip
    c.setFillColor(NAVY)
    c.roundRect(40, 58, PAGE_W - 80, 34, 9, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 7.4)
    c.drawString(55, 71, "46 / 46 ACTIONS MAPPED")
    c.setFont(FONT_REG, 7.1)
    c.drawString(190, 71, "Each matrix action belongs to one primary visual workstream; multiple agencies and dependencies may cross themes.")
    c.showPage()


def page_phase_map(c):
    start_page(c, "03  /  DELIVERY HORIZONS", "The portfolio moves from credibility to capacity",
               "Phase is taken from the matrix. A recommendation tagged across phases appears in each applicable window; continuous actions are called out separately.",
               accent=CORAL)
    phase_data = [
        ("I", "0–2 YEARS", "Secure credibility", CORAL, CORAL_LIGHT,
         "Pay, protect, restore lawful channels, and establish the implementation machinery."),
        ("II", "2–5 YEARS", "Build institutions", TEAL, TEAL_LIGHT,
         "Expand police, courts, local government, prevention and basic services."),
        ("III", "5–15 YEARS", "Consolidate peace", GOLD, GOLD_LIGHT,
         "Lock in community security, truth, economic transformation and regional normalization."),
    ]
    phase_ids = {}
    for roman, *_ in phase_data:
        phase_ids[roman] = [int(r["id"]) for r in RECS if roman in phase_tokens(r["phase"])]
    continuous = [int(r["id"]) for r in RECS if "C" in phase_tokens(r["phase"])]
    left, gap = 40, 14
    col_w = (PAGE_W - 80 - 2 * gap) / 3
    y, h = 113, 329
    for idx, (roman, years, label, col, light, copy) in enumerate(phase_data):
        x = left + idx * (col_w + gap)
        draw_card(c, x, y, col_w, h, fill=WHITE, accent=col)
        c.setFillColor(light)
        c.roundRect(x + 15, y + h - 59, col_w - 30, 42, 9, fill=1, stroke=0)
        c.setFillColor(col)
        c.setFont(FONT_BOLD, 8)
        c.drawString(x + 27, y + h - 35, f"PHASE {roman}  ·  {years}")
        c.setFillColor(INK)
        c.setFont(FONT_BOLD, 13.2)
        c.drawString(x + 17, y + h - 82, label)
        para(c, copy, x + 17, y + h - 94, col_w - 34, size=8.5,
             leading=10.7, color=MUTED, max_h=35)
        c.setFillColor(MUTED)
        c.setFont(FONT_BOLD, 7)
        c.drawString(x + 17, y + h - 144, f"ACTIONS IN THIS WINDOW  ·  {len(phase_ids[roman])}")
        draw_id_cloud(c, phase_ids[roman], x + 17, y + h - 153, col_w - 34,
                      chip_h=16, gap_x=5, gap_y=5, fill=light, ink=col,
                      font_size=6.9, cols=6)
        c.setStrokeColor(LINE)
        c.line(x + 17, y + 49, x + col_w - 17, y + 49)
        c.setFillColor(col)
        c.setFont(FONT_BOLD, 7.2)
        c.drawString(x + 17, y + 34, "CHECKPOINT")
        c.setFillColor(INK)
        outcome = {"I": "Credible commitments and protected frontline institutions",
                   "II": "Courts, police, councils and services functioning",
                   "III": "Local security, accountability and economic resilience"}[roman]
        para(c, outcome, x + 17, y + 23, col_w - 34, size=7.8,
             leading=9.5, color=INK, max_h=22)
    # Continuous actions ribbon below the columns.
    c.setFillColor(BLUE_LIGHT)
    c.roundRect(40, 57, PAGE_W - 80, 42, 10, fill=1, stroke=0)
    c.setFillColor(BLUE)
    c.setFont(FONT_BOLD, 7.2)
    c.drawString(54, 82, "CONTINUOUS / RECURRING")
    para(c, "These actions should not stop at a phase boundary:", 54, 70,
         194, size=7.2, leading=9, color=INK, max_h=14)
    draw_id_cloud(c, continuous, 256, 82, PAGE_W - 315, chip_h=17,
                  gap_x=7, fill=WHITE, ink=BLUE, font_size=7.2, cols=10)
    c.showPage()


def page_critical_path(c):
    start_page(c, "04  /  SEQUENCING LOGIC", "Follow the credibility chain—and keep safeguards parallel",
               "Chapter 15's critical path links fiscal delivery to durable security. It is not a reason to postpone rights or civilian protection.",
               accent=GOLD)
    steps = [
        ("01", "Fiscal\nrescue", "#01–02", NAVY),
        ("02", "Police\nprotection", "#03–04", CORAL),
        ("03", "Justice\ndelivery", "#15", TEAL),
        ("04", "Local\ngovernment", "#24", BLUE),
        ("05", "Reintegration\nat scale", "#19–23", GOLD),
        ("06", "Political\ninclusion", "#05", GREEN),
        ("07", "Regional\nnormalization", "#06, 34–35, 42", NAVY),
    ]
    x0, x1, y = 68, PAGE_W - 68, 352
    step = (x1 - x0) / 6
    c.setStrokeColor(HexColor("#B8C7CE"))
    c.setLineWidth(3)
    c.line(x0, y, x1, y)
    for i, (num, title, refs, col) in enumerate(steps):
        x = x0 + i * step
        c.setFillColor(WHITE)
        c.setStrokeColor(col)
        c.setLineWidth(3)
        c.circle(x, y, 18, fill=1, stroke=1)
        c.setFillColor(col)
        c.setFont(FONT_BOLD, 9.1)
        c.drawCentredString(x, y - 3.2, num)
        if i < len(steps) - 1:
            c.setFillColor(HexColor("#B8C7CE"))
            c.setFont(FONT_BOLD, 12)
            c.drawCentredString(x + step / 2, y + 7, "›")
        para(c, title, x - 48, y - 34, 96,
             size=9.2, leading=11, color=INK, bold=True, align=1, max_h=32)
        c.setFillColor(MUTED)
        c.setFont(FONT_BOLD, 6.8)
        c.drawCentredString(x, y - 72, refs)
    # Dependency band.
    c.setFillColor(NAVY)
    c.roundRect(41, 201, PAGE_W - 82, 68, 11, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont(FONT_BOLD, 8)
    c.drawString(57, 241, "THE SEQUENCING RULE")
    para(c, "Parallel action is possible, but credibility is cumulative: a roadmap that begins with reconciliation while officers lack protection will not be believed; services without fiscal delivery remain promises.",
         57, 228, PAGE_W - 114, size=8.9, leading=11.3, color=WHITE, max_h=28)
    c.setFillColor(INK)
    c.setFont(FONT_BOLD, 8.2)
    c.drawString(43, 183, "RUN THESE SAFEGUARDS IN PARALLEL")
    gates = [
        ("Verification before claims of settlement", "#06 · #34 · #42", BLUE, BLUE_LIGHT),
        ("Due process and political space", "#05 · #07 · #15", TEAL, TEAL_LIGHT),
        ("Independent data and oversight", "#20 · #30 · #31", GOLD, GOLD_LIGHT),
        ("Return, repair and compensation", "#09 · #16 · #41", CORAL, CORAL_LIGHT),
    ]
    gx, gap, gw = 41, 12, (PAGE_W - 82 - 3 * 12) / 4
    for i, (label, refs, col, light) in enumerate(gates):
        x = gx + i * (gw + gap)
        draw_card(c, x, 104, gw, 59, fill=light, stroke=light)
        c.setFillColor(col)
        c.setFont(FONT_BOLD, 7.2)
        c.drawString(x + 12, 143, refs)
        para(c, label, x + 12, 132, gw - 24, size=7.5, leading=9.2,
             color=INK, max_h=23)
    c.showPage()


def page_six_commitments(c):
    start_page(c, "05  /  THE FIRST SIX COMMITMENTS", "Seven matrix actions. Six public commitments.",
               "The study groups the statutory transfer and arrears payment together; all priority IDs are shown, including the annual public report.",
               accent=TEAL)
    commitments = [
        ("01", "Pay—and lock in—the transfer", "#01 + #02", "Enact a protected formula, publish a schedule and clear the Rs 568 bn arrears.", "Statute + audited quarterly releases", NAVY, BLUE_LIGHT),
        ("02", "Protect and compensate police", "#03 + #04", "Fund protected mobility, equipment, insurance and family support as one package.", "Compensation paid within 90 days", CORAL, CORAL_LIGHT),
        ("03", "Staff the courts", "#15", "Make the justice system present in merged districts and measure time to disposition.", "≥75% of ATC cases closed within 24 months", TEAL, TEAL_LIGHT),
        ("04", "Elect councils with budgets", "#24", "Complete local elections and devolve resources so residents have a lawful local interface.", "Councils in all 7 merged districts", BLUE, BLUE_LIGHT),
        ("05", "Fund girls' education", "#27", "Secure schools, recruit female teachers and use stipends to close the enrolment gap.", "Girls' secondary enrolment within 10 pp of provincial average", GOLD, GOLD_LIGHT),
        ("06", "Publish the scorecard", "#31", "Table an independent annual Normalization Report and name non-compliance.", "Report within 180 days of each fiscal year", GREEN, GREEN_LIGHT),
    ]
    left, gap_x, card_w, card_h = 40, 13, (PAGE_W - 80 - 2 * 13) / 3, 149
    top, gap_y = 445, 13
    for idx, row in enumerate(commitments):
        num, title, refs, body, measure, col, light = row
        r, cc = divmod(idx, 3)
        x = left + cc * (card_w + gap_x)
        y = top - card_h - r * (card_h + gap_y)
        draw_card(c, x, y, card_w, card_h, fill=WHITE, accent=col)
        c.setFillColor(light)
        c.circle(x + 31, y + card_h - 29, 17, fill=1, stroke=0)
        c.setFillColor(col)
        c.setFont(FONT_BOLD, 8.5)
        c.drawCentredString(x + 31, y + card_h - 32, num)
        c.setFillColor(col)
        c.setFont(FONT_BOLD, 7.4)
        c.drawRightString(x + card_w - 15, y + card_h - 32, refs)
        para(c, title, x + 17, y + card_h - 53, card_w - 34,
             size=11, leading=13.4, color=INK, bold=True, max_h=29)
        para(c, body, x + 17, y + card_h - 86, card_w - 34,
             size=8.1, leading=10.4, color=MUTED, max_h=33)
        c.setFillColor(light)
        c.roundRect(x + 13, y + 12, card_w - 26, 29, 7, fill=1, stroke=0)
        para(c, measure, x + 22, y + 34, card_w - 44,
             size=7.5, leading=9, color=col, bold=True, max_h=20)
    c.setFillColor(MUTED)
    c.setFont(FONT_REG, 7.2)
    c.drawString(42, 63, "A priority set—not the full programme. The cards that follow retain all 46 recommendations.")
    c.showPage()


def page_first_90_days(c):
    start_page(c, "06  /  IMMEDIATE IMPLEMENTATION", "First 90 days: make the state measurable and responsive",
               "The policy brief identifies three no-regret measures that can begin without waiting for the full legislative package.",
               accent=CORAL)
    actions = [
        ("01", "Publish the data", "QUARTERLY + MONTHLY", "Direct Home, Police and Finance to publish district-wise attacks, casualties and compensation each quarter, and merged-district releases each month.", "LEAD  Home Department · KP Police · Finance Department", "LINK  #01 · #31", "A public baseline replaces fragmented claims.", CORAL, CORAL_LIGHT),
        ("02", "Audit the pipeline", "RECONCILE SINCE 2019", "Bring federal, provincial, district and audit authorities together to reconcile every rupee committed against every rupee delivered; publish the table.", "LEAD  Federal + KP Finance · Auditor-General", "LINK  #01 · #02 · #26", "A visible ledger turns fiscal grievance into an accountable process.", TEAL, TEAL_LIGHT),
        ("03", "Respond to each police fatality", "14 / 30 / 45-DAY CLOCK", "Within 14 days: documented review. Within 30 days: begin automatic family-compensation processing. Within 45 days: equipment-needs assessment for the unit.", "LEAD  KP Police · Home Department", "LINK  #03 · #04 · #10", "A repeatable protocol supports families and frontline confidence.", GOLD, GOLD_LIGHT),
    ]
    left, gap, w = 40, 16, (PAGE_W - 80 - 2 * 16) / 3
    y, h = 131, 304
    for idx, a in enumerate(actions):
        num, title, timing, body, lead, refs, closing, col, light = a
        x = left + idx * (w + gap)
        draw_card(c, x, y, w, h, fill=WHITE, accent=col, shadow=True)
        c.setFillColor(light)
        c.roundRect(x + 16, y + h - 54, w - 32, 34, 8, fill=1, stroke=0)
        c.setFillColor(col)
        c.setFont(FONT_BOLD, 7.2)
        c.drawString(x + 27, y + h - 41, f"MOVE {num}  ·  {timing}")
        para(c, title, x + 18, y + h - 73, w - 36,
             size=15, leading=18, color=INK, bold=True, max_h=43)
        c.setStrokeColor(LINE)
        c.line(x + 18, y + h - 126, x + w - 18, y + h - 126)
        para(c, body, x + 18, y + h - 142, w - 36,
             size=9.2, leading=12.1, color=INK, max_h=100)
        c.setFillColor(MUTED)
        c.setFont(FONT_BOLD, 6.8)
        c.drawString(x + 18, y + 93, "ACCOUNTABILITY")
        para(c, lead, x + 18, y + 82, w - 36, size=7.7,
             leading=9.6, color=MUTED, max_h=29)
        c.setFillColor(col)
        c.setFont(FONT_BOLD, 7.1)
        c.drawString(x + 18, y + 44, refs)
        para(c, closing, x + 18, y + 31, w - 36, size=7.5,
             leading=9.3, color=col, bold=True, max_h=22)
    c.setFillColor(NAVY)
    c.roundRect(40, 71, PAGE_W - 80, 42, 9, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 8.4)
    c.drawCentredString(PAGE_W / 2, 87, "90-DAY TEST: CAN PEOPLE SEE THE MONEY, THE RESPONSE AND THE RESULT?")
    c.showPage()


def page_financing(c):
    start_page(c, "07  /  FINANCING THE ROADMAP", "Fund prevention and institutions before the conflict bills grow",
               "All amounts are the study's indicative planning estimates. Annual programme costs and one-time arrears are shown separately.",
               accent=GOLD)
    # Left: visually scaled ranges in PKR bn / year.
    draw_card(c, 40, 172, 432, 278, fill=WHITE, accent=GOLD)
    c.setFillColor(INK)
    c.setFont(FONT_BOLD, 11)
    c.drawString(58, 426, "ANNUAL FLOW: INVESTMENT VS ESTIMATED LOSS")
    c.setFillColor(MUTED)
    c.setFont(FONT_REG, 7.2)
    c.drawString(58, 410, "PKR billion / year  ·  scale 0–800")
    x0, x1 = 185, 443
    bar_w = x1 - x0
    # Axis
    c.setStrokeColor(LINE)
    c.setLineWidth(0.7)
    for val in range(0, 801, 200):
        xx = x0 + bar_w * val / 800
        c.line(xx, 214, xx, 382)
        c.setFillColor(MUTED)
        c.setFont(FONT_REG, 6.5)
        c.drawCentredString(xx, 199, str(val))
    rows = [
        ("Roadmap\n(at maturity)", 150, 250, TEAL, "150–250"),
        ("Conflict loss\n(estimate)", 400, 800, CORAL, "400–800"),
    ]
    for idx, (lab, lo, hi, col, txt) in enumerate(rows):
        yy = 345 - idx * 77
        para(c, lab, 58, yy + 15, 111,
             size=8.4, leading=10.5, color=INK, bold=True, max_h=27)
        a = x0 + bar_w * lo / 800
        b = x0 + bar_w * hi / 800
        c.setFillColor(HexColor("#E9EEF0"))
        c.roundRect(x0, yy - 5, bar_w, 21, 8, fill=1, stroke=0)
        c.setFillColor(col)
        c.roundRect(a, yy - 5, b - a, 21, 8, fill=1, stroke=0)
        c.setFillColor(col)
        c.setFont(FONT_BOLD, 8.5)
        c.drawRightString(min(b + 1, x1), yy + 24, txt)
    c.setFillColor(GREEN_LIGHT)
    c.roundRect(58, 230, 376, 29, 8, fill=1, stroke=0)
    c.setFillColor(GREEN)
    c.setFont(FONT_BOLD, 7.5)
    c.drawCentredString(246, 241, "Study's broad comparison: annual roadmap cost ≈ ¼–½ of estimated annual loss")
    c.setFillColor(MUTED)
    c.setFont(FONT_REG, 6.5)
    c.drawString(58, 184, "Ranges are estimates, not audited budget figures; the comparison is not a guaranteed saving.")

    # Right: recurring/one-time cost cards.
    draw_card(c, 489, 172, PAGE_W - 529, 278, fill=WHITE, accent=TEAL)
    c.setFillColor(INK)
    c.setFont(FONT_BOLD, 11)
    c.drawString(507, 426, "WHAT THE PLAN MUST FINANCE")
    items = [
        ("Police protection", "Rs 30–50 bn/yr", CORAL),
        ("NMD education", "Rs 40–60 bn/yr", GOLD),
        ("Reintegration", "Rs 10–20 bn/yr", TEAL),
        ("Justice expansion", "Rs 5–10 bn/yr", BLUE),
        ("Local government + M&E", "Rs 5–10 bn/yr", GREEN),
        ("3% transfer framework", "~Rs 192 bn/yr", NAVY),
    ]
    yy = 393
    for name, val, col in items:
        c.setFillColor(col)
        c.circle(513, yy - 2, 4, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont(FONT_REG, 7.7)
        c.drawString(526, yy - 5, name)
        c.setFillColor(col)
        c.setFont(FONT_BOLD, 7.5)
        c.drawRightString(PAGE_W - 58, yy - 5, val)
        c.setStrokeColor(PALE)
        c.line(507, yy - 14, PAGE_W - 57, yy - 14)
        yy -= 30
    c.setFillColor(CORAL_LIGHT)
    c.roundRect(507, 194, PAGE_W - 566, 31, 7, fill=1, stroke=0)
    c.setFillColor(CORAL)
    c.setFont(FONT_BOLD, 7.2)
    c.drawCentredString(507 + (PAGE_W - 566) / 2, 206, "Rs 568 bn arrears = one-time stock, not an annual flow")

    # Fiscal rules below both panels.
    c.setFillColor(NAVY)
    c.roundRect(40, 91, PAGE_W - 80, 59, 10, fill=1, stroke=0)
    rules = [("RING-FENCE", "Protect the transfer in law and budget"),
             ("PUBLISH", "Show district releases and audit follow-up"),
             ("FUND PEOPLE", "Pay recurrent costs, not only construction"),
             ("VERIFY", "Report delivery and non-compliance annually")]
    rw = (PAGE_W - 100) / 4
    for i, (head, body) in enumerate(rules):
        xx = 50 + i * rw
        c.setFillColor(GOLD if i == 0 else TEAL_LIGHT)
        c.setFont(FONT_BOLD, 7.1)
        c.drawString(xx + 12, 127, head)
        para(c, body, xx + 12, 115, rw - 22, size=7.2, leading=9,
             color=WHITE, max_h=20)
    c.setFont(FONT_REG, 6.7)
    c.setFillColor(MUTED)
    c.drawString(42, 72, "Stock: Rs 568 bn arrears. Annual flows: itemised estimates and aggregate maturity requirement (Rs 150–250 bn/yr). Do not sum categories mechanically.")
    c.showPage()


def page_responsibilities(c):
    start_page(c, "08  /  IMPLEMENTATION ARCHITECTURE", "Assign each function across four levels",
               "A whole-of-government compact: federal financing and diplomacy; provincial delivery; district-facing services; independent and international partners.",
               accent=BLUE)
    cols = ["FUNCTION", "FEDERAL", "PROVINCIAL", "DISTRICT / LOCAL", "PARTNERS"]
    rows = [
        ["Merged-district fund + audit", "Finance · NFC · PMO", "KP Finance", "Community committees", "Auditor-General"],
        ["Police protection + compensation", "Interior (supplementary)", "Home · Police", "DPOs", "Donors (equipment)"],
        ["CTD · fusion · CFT", "Interior · NACTA", "Home · CTD", "—", "FATF-consistent partners"],
        ["Border + mediation", "MOFA · Security Divisions", "Border districts", "Levies · police", "China · Qatar · Türkiye · Saudi Arabia"],
        ["Refugee processing", "SAFRON · Interior", "KP administration", "Transit centres", "UNHCR · IOM"],
        ["Deradicalization + reintegration", "NACTA · Interior", "Home · CTD", "DRCs", "Universities · NGOs"],
        ["Courts + ATCs", "Law · Supreme Court", "Prosecution · PHC", "District judiciary", "UNODC · partners"],
        ["Local government", "ECP · Law", "Local Government", "Councils", "UNDP · donors"],
        ["Education · health · jobs", "Federal schemes", "Line departments", "DEOs · facilities", "UNICEF · WFP · World Bank"],
        ["Monitoring + annual report", "Planning", "P&D cell", "District statistics", "Independent panel"],
    ]
    x0, top = 40, 440
    widths = [143, 146, 150, 148, PAGE_W - 80 - 587]
    row_h = 31
    x = x0
    for label, w in zip(cols, widths):
        c.setFillColor(NAVY)
        c.roundRect(x, top, w - 2, 29, 5, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 6.8)
        c.drawCentredString(x + (w - 2) / 2, top + 10, label)
        x += w
    for r_i, row in enumerate(rows):
        yy = top - 7 - (r_i + 1) * row_h
        fill = WHITE if r_i % 2 == 0 else HexColor("#EEF3F5")
        x = x0
        for c_i, (text, w) in enumerate(zip(row, widths)):
            c.setFillColor(fill)
            c.setStrokeColor(LINE)
            c.rect(x, yy, w - 2, row_h, fill=1, stroke=1)
            col = NAVY if c_i == 0 else INK
            para(c, text, x + 6, yy + row_h - 5, w - 14,
                 size=7.0 if c_i else 7.1, leading=8.6, color=col,
                 bold=(c_i == 0), max_h=row_h - 6, min_size=6.2)
            x += w
    c.setFillColor(TEAL_LIGHT)
    c.roundRect(40, 75, PAGE_W - 80, 37, 8, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.setFont(FONT_BOLD, 7.5)
    c.drawString(55, 97, "ACCOUNTABILITY RULE")
    para(c, "Every function needs one lead, a public delivery indicator, and an escalation path when federal and provincial responsibilities collide.",
         171, 99, PAGE_W - 220, size=7.7, leading=9.6, color=INK, max_h=20)
    c.showPage()


def page_outcomes(c):
    start_page(c, "09  /  MONITORING & EVALUATION", "A public 2035 dashboard turns promises into tests",
               "Targets below are the study's end-state measures. Disaggregate by district and publish definitions, denominators and audit notes.",
               accent=GREEN)
    metrics = [
        ("VIOLENCE", "≤400 / yr", "Conflict fatalities across KP", CORAL),
        ("PARALLEL GOVERNANCE", "0 districts", "TTP taxation / justice for 4 consecutive quarters", NAVY),
        ("POLICE SAFETY", "≤50 / yr", "Police personnel killed", CORAL),
        ("PROTECTION", "≥80%", "Attacks survived without loss; responders equipped", TEAL),
        ("JUSTICE", "≥75%", "ATC cases concluded within 24 months", BLUE),
        ("DETENTION", "Publish count", "Statutory limits enforced; public reporting", GOLD),
        ("FISCAL DELIVERY", "≥95%", "Merged-district transfer released within fiscal year; audited", NAVY),
        ("LOCAL VOICE", "7 / 7", "NMD councils elected with budgets", TEAL),
        ("GIRLS' EDUCATION", "≤10 pp gap", "NMD secondary enrolment vs provincial average", GOLD),
        ("ECONOMIC GAP", "≤10 pp", "Merged-district poverty gap vs provincial average", GREEN),
        ("POLITICAL SPACE", "0 bans", "Proscriptions of non-violent parties", BLUE),
        ("PUBLIC REPORTING", "≤180 days", "Annual Normalization Report tabled after fiscal year", NAVY),
    ]
    left, gx, gy = 40, 11, 10
    cw = (PAGE_W - 80 - 3 * gx) / 4
    ch = 105
    top = 448
    for idx, (domain, target, descr, col) in enumerate(metrics):
        row, cl = divmod(idx, 4)
        x = left + cl * (cw + gx)
        y = top - ch - row * (ch + gy)
        draw_card(c, x, y, cw, ch, fill=WHITE, accent=col)
        c.setFillColor(MUTED)
        c.setFont(FONT_BOLD, 6.6)
        c.drawString(x + 14, y + ch - 19, domain)
        c.setFillColor(col)
        c.setFont(FONT_BOLD, 16.4 if len(target) <= 10 else 13.2)
        c.drawString(x + 14, y + ch - 47, target)
        c.setStrokeColor(LINE)
        c.line(x + 14, y + ch - 56, x + cw - 14, y + ch - 56)
        para(c, descr, x + 14, y + ch - 65, cw - 28,
             size=7.4, leading=9.2, color=INK, max_h=31)
    c.setFillColor(NAVY)
    c.roundRect(40, 63, PAGE_W - 80, 30, 8, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 7.4)
    c.drawCentredString(PAGE_W / 2, 74, "MEASURE WHAT RESIDENTS EXPERIENCE—NOT ONLY WHAT INSTITUTIONS SPEND OR ANNOUNCE")
    c.showPage()


def page_districts(c):
    start_page(c, "10  /  DISTRICT PRIORITISATION", "Target the package to place and exposure",
               "The source describes a tiered prioritisation aid—not a rendered geographic map. The tier lists below follow Appendix H; see the classification note.",
               accent=CORAL)
    tiers = [
        ("TIER 1", "SEVERE · SUSTAINED", "North Waziristan · South Waziristan (Upper / Lower) · Bannu · Lakki Marwat",
         "Protect police mobility; fuse military–police intelligence; finish return and compensation; restore schools, health and district courts.", CORAL, CORAL_LIGHT),
        ("TIER 2", "HIGH · EPISODIC", "Khyber / Tirah · Bajaur · Mohmand · Kurram · Orakzai · D.I. Khan · Tank · Karak · Hangu",
         "Complete NMD policing; enforce Kurram accords; support Tirah and Sarbakaf return; protect roads and de-escalate sectarian risk.", GOLD, GOLD_LIGHT),
        ("TIER 3", "URBAN / SOFT-TARGET", "Peshawar · Mardan · Charsadda · Nowshera · Swat · Shangla · Malakand / Dir cluster",
         "Strengthen CT policing; protect markets, mosques, schools and transport; support Swat re-entry with rights-safe public safety.", BLUE, BLUE_LIGHT),
        ("TIER 4", "STRATEGIC EXPOSURE", "Abbottabad · Mansehra · Haripur · Chitral · Upper / Lower Dir · Hazara districts",
         "Protect infrastructure, tourism routes and corridors; integrate climate and GLOF resilience; monitor border-adjacent exposure.", TEAL, TEAL_LIGHT),
    ]
    left, gap, cw, ch = 40, 14, (PAGE_W - 80 - 14) / 2, 166
    top = 444
    for idx, row in enumerate(tiers):
        name, sub, districts, actions, col, light = row
        r, cl = divmod(idx, 2)
        x = left + cl * (cw + gap)
        y = top - ch - r * (ch + 13)
        draw_card(c, x, y, cw, ch, fill=WHITE, accent=col)
        c.setFillColor(light)
        c.roundRect(x + 15, y + ch - 41, 79, 25, 7, fill=1, stroke=0)
        c.setFillColor(col)
        c.setFont(FONT_BOLD, 8)
        c.drawCentredString(x + 54.5, y + ch - 33, name)
        c.setFillColor(MUTED)
        c.setFont(FONT_BOLD, 7.1)
        c.drawString(x + 105, y + ch - 33, sub)
        para(c, districts, x + 17, y + ch - 54, cw - 34,
             size=8.2, leading=10.5, color=INK, bold=True, max_h=42)
        c.setStrokeColor(LINE)
        c.line(x + 17, y + 71, x + cw - 17, y + 71)
        c.setFillColor(col)
        c.setFont(FONT_BOLD, 6.8)
        c.drawString(x + 17, y + 56, "PRIORITY PACKAGE")
        para(c, actions, x + 17, y + 47, cw - 34,
             size=7.7, leading=9.5, color=MUTED, max_h=37)
    c.setFillColor(HexColor("#FFF4DD"))
    c.roundRect(40, 44, PAGE_W - 80, 44, 8, fill=1, stroke=0)
    c.setFillColor(HexColor("#8A6414"))
    c.setFont(FONT_BOLD, 7)
    c.drawString(54, 70, "CLASSIFICATION CAVEAT")
    para(c, "Appendix H lists Upper / Lower Dir in both its Tier 3 cluster and Tier 4 exposure group, and refers generally to “Hazara districts.” The study does not supply a GIS-ready, exhaustive district map; reconcile the overlap and validate local data before operational allocation.",
         177, 72, PAGE_W - 230, size=7.1, leading=8.8, color=INK, max_h=28)
    c.showPage()


def page_risks(c):
    start_page(c, "11  /  RISK, RIGHTS & SAFEGUARDS", "Build the safeguards into the delivery plan",
               "The roadmap identifies seven political and operational risks. Mitigation is an implementation task, not a footnote.",
               accent=CORAL)
    risks = [
        ("Fiscal promises deferred past 2028", "Legislate the transfer; publish audited releases; make non-compliance visible."),
        ("Elite capture of merged-district funds", "Community monitoring, public beneficiary lists, audits and elected councils."),
        ("Spoilers target visible progress", "Protect schools, markets and routes; rapid compensation; plan continuity."),
        ("Police losses erode recruitment and morale", "Protection-first sequencing, insurance, family support and equipment reviews."),
        ("Political instability interrupts reform", "Multi-year budgets, a cross-party provincial charter and independent reporting."),
        ("Escalation with Afghanistan", "Standing mediation, verified commitments and trade / mobility contingencies."),
        ("Surveillance growth erodes rights", "Enact data-protection rules and parliamentary oversight before Safe City expansion."),
    ]
    x, w, row_h, gap = 40, PAGE_W - 80, 39, 6
    top = 446
    for i, (risk, mitigation) in enumerate(risks):
        y = top - (i + 1) * row_h - i * gap
        c.setFillColor(WHITE if i % 2 == 0 else HexColor("#EDF2F4"))
        c.setStrokeColor(LINE)
        c.roundRect(x, y, w, row_h, 6, fill=1, stroke=1)
        c.setFillColor(CORAL if i in (0, 2, 3, 5, 6) else GOLD)
        c.circle(x + 17, y + row_h / 2, 4, fill=1, stroke=0)
        para(c, risk, x + 30, y + row_h - 8, 237,
             size=7.7, leading=9.2, color=INK, bold=True, max_h=row_h - 8)
        c.setStrokeColor(LINE)
        c.line(x + 278, y + 6, x + 278, y + row_h - 6)
        para(c, mitigation, x + 292, y + row_h - 8, w - 306,
             size=7.6, leading=9.2, color=MUTED, max_h=row_h - 8)
    # safeguards strip
    c.setFillColor(NAVY)
    c.roundRect(40, 73, PAGE_W - 80, 65, 10, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont(FONT_BOLD, 7.5)
    c.drawString(56, 119, "NON-NEGOTIABLE DELIVERY GUARDRAILS")
    guardrails = ["Lawful, individual refugee processing", "Collateral-harm review + rapid compensation",
                  "Independent programme evaluation", "Privacy rules before expanded surveillance"]
    gx, gap, gw = 55, 13, (PAGE_W - 110 - 3 * 13) / 4
    for i, text in enumerate(guardrails):
        xx = gx + i * (gw + gap)
        c.setFillColor(TEAL if i % 2 == 0 else GOLD)
        c.circle(xx + 4, 96, 3, fill=1, stroke=0)
        para(c, text, xx + 12, 103, gw - 15,
             size=7.1, leading=8.6, color=WHITE, max_h=20)
    c.showPage()


def phase_label(phase: str) -> tuple[str, colors.Color, colors.Color]:
    tokens = phase_tokens(phase)
    if "I" in tokens:
        key = "I"
    elif "II" in tokens:
        key = "II"
    elif "III" in tokens:
        key = "III"
    else:
        key = "C"
    return phase.upper().replace("–", "–"), PHASE_COLORS[key], PHASE_LIGHTS[key]


def draw_recommendation_card(c, x, y, w, h, rec):
    phase_txt, accent, light = phase_label(rec["phase"])
    draw_card(c, x, y, w, h, fill=WHITE, accent=accent, shadow=True)
    # number and phase ribbon
    c.setFillColor(light)
    c.circle(x + 27, y + h - 26, 14, fill=1, stroke=0)
    c.setFillColor(accent)
    c.setFont(FONT_BOLD, 7.6)
    c.drawCentredString(x + 27, y + h - 29, f"{int(rec['id']):02d}")
    c.setFillColor(MUTED)
    c.setFont(FONT_BOLD, 6.5)
    c.drawString(x + 48, y + h - 23, "RECOMMENDATION")
    c.setFillColor(accent)
    c.setFont(FONT_BOLD, 6.0)
    c.drawRightString(x + w - 13, y + h - 23, f"PHASE {phase_txt}  ·  {rec['source']}")
    # full recommendation wording
    body_top = y + h - 43
    desc_h = para(c, rec["text"], x + 14, body_top, w - 28,
                  size=9.5, leading=12.0, color=INK, bold=True,
                  max_h=47, min_size=8.3)
    meta_top = body_top - desc_h - 6
    c.setFillColor(light)
    c.roundRect(x + 11, meta_top - 42, w - 22, 42, 7, fill=1, stroke=0)
    mid = x + w * 0.53
    c.setFillColor(accent)
    c.setFont(FONT_BOLD, 6.1)
    c.drawString(x + 19, meta_top - 12, "LEAD")
    c.drawString(mid + 4, meta_top - 12, "INDICATIVE COST")
    lead_w = mid - (x + 23)
    cost_w = x + w - 19 - (mid + 4)
    para(c, rec["lead"], x + 19, meta_top - 16, lead_w,
         size=7.2, leading=8.6, color=INK, max_h=26, min_size=6.4)
    para(c, rec["cost"] if rec["cost"] not in ("—", "–", "-") else "Not quantified",
         mid + 4, meta_top - 16, cost_w,
         size=7.2, leading=8.6, color=INK, max_h=26, min_size=6.4)
    kpi_top = meta_top - 50
    c.setFillColor(MUTED)
    c.setFont(FONT_BOLD, 6.2)
    c.drawString(x + 14, kpi_top, "MEASURE OF PROGRESS")
    para(c, rec["kpi"], x + 14, kpi_top - 6, w - 28,
         size=7.6, leading=9.1, color=INK, max_h=30, min_size=6.6)
    # Source chapters are carried in the header beside the exact phase label.


def page_recommendation_cards(c, group, page_index):
    first = int(group[0]["id"])
    last = int(group[-1]["id"])
    start_page(c, "12  /  COMPLETE ACTION REGISTER",
               f"Recommendations {first:02d}–{last:02d}",
               "Every card carries the matrix wording, lead responsibility, indicative cost and KPI. Phase labels follow the study's matrix.",
               accent=TEAL,
               title_size=21)
    left, gap_x = 40, 14
    card_w = (PAGE_W - 80 - gap_x) / 2
    card_h, gap_y = 190, 12
    top = 451
    for i, rec in enumerate(group):
        row, col = divmod(i, 2)
        x = left + col * (card_w + gap_x)
        y = top - card_h - row * (card_h + gap_y)
        draw_recommendation_card(c, x, y, card_w, card_h, rec)
    # On the final two-card page, use the remaining space for a concise legend.
    if len(group) == 2:
        c.setFillColor(BLUE_LIGHT)
        c.roundRect(40, 67, PAGE_W - 80, 60, 10, fill=1, stroke=0)
        c.setFillColor(NAVY)
        c.setFont(FONT_BOLD, 7.6)
        c.drawString(56, 105, "THE ACTION REGISTER IS COMPLETE")
        para(c, "The 46 recommendations are the implementation layer of the monograph's 16-chapter analysis. The following source note records how to interpret cost ranges, data gaps and the district classification.",
             56, 92, PAGE_W - 112, size=8, leading=10.2, color=INK, max_h=27)
    c.showPage()


def page_sources(c):
    start_page(c, "13  /  SOURCE & USE NOTES", "Read the figures as a decision aid—not a forecast",
               "This atlas makes the source study's recommendations easier to compare, sequence and assign. It does not add new evidence or change the underlying claims.",
               accent=NAVY)
    boxes = [
        ("PRIMARY BASIS", "Research-agent monograph, Chapter 15 (Phased Normalization Roadmap) and the 46-item Recommendations Matrix in Chapter 18 / Statistical Annex. Policy-brief financing, governance and monitoring tables supplement the action cards.", NAVY, BLUE_LIGHT),
        ("COSTS", "All costs are indicative planning ranges in Pakistani rupees. Costs are annual unless stated; Rs 568 bn is an arrears stock, not an annual amount. The study's Rs 150–250 bn/yr maturity estimate excludes arrears and one-off costs. Do not add every row mechanically.", TEAL, TEAL_LIGHT),
        ("EVIDENCE LIMITS", "The monograph flags data gaps in public audited time series, operation-related civilian harm, case outcomes, fiscal absorption and rehabilitation results. Contested claims are attributed, not reconciled; programme figures are not presented as independent evaluations.", GOLD, GOLD_LIGHT),
        ("DISTRICT TIERS", "Appendix H describes tiers rather than supplying a GIS-ready basemap. Its Upper / Lower Dir listing overlaps between tiers, and “Hazara districts” is not enumerated. Validate this classification against current, district-level evidence before allocating operational resources.", CORAL, CORAL_LIGHT),
    ]
    x, top, w, h, gap = 40, 446, 366, 142, 15
    for idx, (head, body, col, light) in enumerate(boxes):
        row, cc = divmod(idx, 2)
        xx = x + cc * (w + gap)
        yy = top - h - row * (h + 14)
        draw_card(c, xx, yy, w, h, fill=WHITE, accent=col)
        c.setFillColor(light)
        c.roundRect(xx + 16, yy + h - 43, w - 32, 26, 7, fill=1, stroke=0)
        c.setFillColor(col)
        c.setFont(FONT_BOLD, 7.5)
        c.drawString(xx + 27, yy + h - 34, head)
        para(c, body, xx + 17, yy + h - 59, w - 34,
             size=8.2, leading=10.6, color=INK, max_h=81)
    c.setFillColor(NAVY)
    c.roundRect(40, 63, PAGE_W - 80, 38, 9, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 7.7)
    c.drawCentredString(PAGE_W / 2, 78, "SOURCE TEXT: research/chapters/18_statistical_annex.md  ·  DATA CUT-OFF: 04 OCT 2026")
    c.showPage()


def build_pdf():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    c = NumberedCanvas(str(OUTFILE), pagesize=(PAGE_W, PAGE_H), pageCompression=1,
                       invariant=1)
    c.setTitle("KPK Security Normalization — Recommendations Infographics Atlas")
    c.setAuthor("Research Agent")
    c.setSubject("Visual implementation guide to the 46 recommendations in the KPK security normalization monograph")
    c.setKeywords("Khyber Pakhtunkhwa, recommendations, normalization, implementation, policy infographic")
    draw_cover(c)
    page_system_logic(c)
    page_pillars(c)
    page_phase_map(c)
    page_critical_path(c)
    page_six_commitments(c)
    page_first_90_days(c)
    page_financing(c)
    page_responsibilities(c)
    page_outcomes(c)
    page_districts(c)
    page_risks(c)
    for start in range(0, len(RECS), 4):
        page_recommendation_cards(c, RECS[start:start + 4], start // 4)
    page_sources(c)
    c.save()
    return OUTFILE


if __name__ == "__main__":
    path = build_pdf()
    print(f"Wrote {path}")
    print(f"Recommendations parsed: {len(RECS)}; pillars: {len(PILLARS)}; page size: A4 landscape vector PDF")
