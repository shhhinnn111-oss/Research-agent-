#!/usr/bin/env python3
"""
render_study.py — long-form markdown -> PDF / DOCX renderer for the
KPK Security Normalization monograph and its derived deliverables.

Usage:
    /tmp/pdfenv/bin/python render_study.py monograph
    /tmp/pdfenv/bin/python render_study.py exec
    /tmp/pdfenv/bin/python render_study.py brief

Markdown subset supported: #, ##, ### headings; paragraphs; - and * bullets;
numbered lists; pipe tables; horizontal rules (---); **bold**, *italic*;
image placeholders: [[FIG:file.png|Caption text]]

Outputs go to research/build/.
"""
import os, re, sys, glob

BASE = os.path.dirname(os.path.abspath(__file__))
CH = os.path.join(BASE, "research", "chapters")
BUILD = os.path.join(BASE, "research", "deliverables")
FIGDIR = os.path.join(BUILD, "figures")
os.makedirs(BUILD, exist_ok=True)

TITLE = "NORMALIZING THE SECURITY SITUATION OF KHYBER PAKHTUNKHWA"
SUBTITLE = "Conflict Evolution, Threat Dynamics, and Pathways to Sustainable Peace"
SHORT = "Normalizing the Security Situation of KPK"

# ----------------------------------------------------------------------------
# Markdown parsing
# ----------------------------------------------------------------------------

def split_row(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]

def is_sep_row(line):
    return bool(re.match(r"^\s*\|?[\s:\-|]+\|?\s*$", line)) and "-" in line

def parse_md(text):
    """Return list of blocks: ('h',level,txt) ('p',txt) ('ul',[items])
    ('ol',[items]) ('table',rows) ('hr',) ('fig',path,caption)"""
    lines = text.replace("\r\n", "\n").split("\n")
    blocks, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1; continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            blocks.append(("h", len(m.group(1)), m.group(2).strip()))
            i += 1; continue
        if re.match(r"^---+$", s):
            blocks.append(("hr",)); i += 1; continue
        fm = re.match(r"^\[\[FIG:([^|\]]+)\|(.*)\]\]$", s)
        if fm:
            blocks.append(("fig", fm.group(1).strip(), fm.group(2).strip()))
            i += 1; continue
        if s.startswith("|"):
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                if not is_sep_row(lines[i]):
                    rows.append(split_row(lines[i]))
                i += 1
            if rows:
                blocks.append(("table", rows))
            continue
        if re.match(r"^\s*[-*]\s+", line):
            items = []
            while i < n and re.match(r"^\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i]).strip())
                i += 1
            blocks.append(("ul", items)); continue
        if re.match(r"^\s*\d+[.)]\s+", line):
            items = []
            while i < n and re.match(r"^\s*\d+[.)]\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+[.)]\s+", "", lines[i]).strip())
                i += 1
            blocks.append(("ol", items)); continue
        # paragraph
        para = [s]
        i += 1
        while i < n:
            t = lines[i].strip()
            if (not t or t.startswith("#") or t.startswith("|")
                    or re.match(r"^\s*[-*]\s+", lines[i])
                    or re.match(r"^\s*\d+[.)]\s+", lines[i])
                    or re.match(r"^---+$", t) or t.startswith("[[FIG:")):
                break
            para.append(t); i += 1
        blocks.append(("p", " ".join(para)))
    return blocks

def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def inline(t):
    """Escape then convert **bold**, *italic*, `code`. Preserves existing tags."""
    t = t.replace("&", "\x00AMP\x00").replace("<", "\x00LT\x00").replace(">", "\x00GT\x00")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\s)([^*]+?)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"`([^`]+)`", r'<font face="Courier">\1</font>', t)
    t = t.replace("\x00AMP\x00", "&amp;").replace("\x00LT\x00", "&lt;").replace("\x00GT\x00", "&gt;")
    return t

# ----------------------------------------------------------------------------
# Figures
# ----------------------------------------------------------------------------

def make_figures():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(FIGDIR, exist_ok=True)
    NAVY = "#0B3A5D"; RED = "#B03A2E"; GREY = "#5D6D7E"; GOLD = "#B7950B"

    # Fig 1 — KP and national violence-linked fatalities
    fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=200)
    yrs = ["2023*", "2024", "2025"]
    natl = [1530, 2555, 3417]; kp = [1026, 1620, 2331]
    x = range(len(yrs)); w = 0.38
    ax.bar([i - w/2 for i in x], natl, w, label="Pakistan (national)", color=NAVY)
    ax.bar([i + w/2 for i in x], kp, w, label="Khyber Pakhtunkhwa", color=RED)
    for i, v in enumerate(natl): ax.text(i - w/2, v + 40, f"{v:,}", ha="center", fontsize=7.5, color=NAVY)
    for i, v in enumerate(kp): ax.text(i + w/2, v + 40, f"{v:,}", ha="center", fontsize=7.5, color=RED)
    ax.set_xticks(list(x)); ax.set_xticklabels(yrs, fontsize=8)
    ax.set_ylabel("Violence-linked fatalities", fontsize=8)
    ax.set_title("Figure 1. Violence-linked fatalities, national and KP, 2023–2025 (CRSS)", fontsize=8.5, color=NAVY)
    ax.legend(fontsize=7.5, frameon=False); ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=7.5)
    fig.text(0.01, 0.005, "*2023 national figure derived from reported annual percentage change; KP 2023 estimate.", fontsize=6, color=GREY)
    fig.tight_layout(); fig.savefig(os.path.join(FIGDIR, "fig1_violence_trend.png")); plt.close(fig)

    # Fig 2 — KP vs Balochistan, 2026 quarters
    fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=200)
    q = ["Q1 2026", "Q2 2026", "Q3 2026"]; k = [311, 475, 556]; b = [114, 265, 829]
    ax.plot(q, k, "o-", color=NAVY, label="Khyber Pakhtunkhwa", linewidth=2)
    ax.plot(q, b, "s--", color=RED, label="Balochistan", linewidth=2)
    for xx, yy in zip(q, k): ax.annotate(f"{yy}", (xx, yy), textcoords="offset points", xytext=(0, 7), fontsize=7.5, color=NAVY, ha="center")
    for xx, yy in zip(q, b): ax.annotate(f"{yy}", (xx, yy), textcoords="offset points", xytext=(0, -13), fontsize=7.5, color=RED, ha="center")
    ax.set_ylabel("Violence-linked fatalities", fontsize=8)
    ax.set_title("Figure 2. Provincial fatalities by quarter, 2026: Balochistan overtakes KP in Q3 (CRSS)", fontsize=8.5, color=NAVY)
    ax.legend(fontsize=7.5, frameon=False); ax.spines[["top", "right"]].set_visible(False); ax.tick_params(labelsize=7.5)
    ax.grid(axis="y", color="#EEEEEE")
    fig.tight_layout(); fig.savefig(os.path.join(FIGDIR, "fig2_2026_quarters.png")); plt.close(fig)

    # Fig 3 — KP police killed and attacks
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1), dpi=200)
    yrs = ["2023", "2024", "2025", "H1 2026"]
    killed = [186, 153, 159, 122]
    axes[0].bar(yrs, killed, color=NAVY, width=0.55)
    for i, v in enumerate(killed): axes[0].text(i, v + 3, str(v), ha="center", fontsize=8, color=NAVY)
    axes[0].set_title("Police personnel killed", fontsize=8.5, color=NAVY)
    axes[0].tick_params(labelsize=7.5); axes[0].spines[["top", "right"]].set_visible(False)
    ay = ["2024*", "2025", "Jan–Sep 2026"]; attacks = [362, 536, 680]
    axes[1].bar(ay, attacks, color=RED, width=0.55)
    for i, v in enumerate(attacks): axes[1].text(i, v + 10, str(v), ha="center", fontsize=8, color=RED)
    axes[1].set_title("Attacks on police", fontsize=8.5, color=NAVY)
    axes[1].tick_params(labelsize=7.5); axes[1].spines[["top", "right"]].set_visible(False)
    fig.suptitle("Figure 3. KP police: casualties and attacks, 2023–2026 (official KP data)", fontsize=9, color=NAVY)
    fig.text(0.01, 0.005, "*2024 attacks derived from reported +48% change; SATP/CRSS counts differ in scope.", fontsize=6, color=GREY)
    fig.tight_layout(rect=[0, 0.03, 1, 0.94]); fig.savefig(os.path.join(FIGDIR, "fig3_police.png")); plt.close(fig)

    # Fig 4 — fiscal delivery vs conflict loss
    fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=200)
    labels = ["Promised to merged\ndistricts (10 yrs)", "Delivered by\nmid-2026", "Annual conflict loss\n(low)", "Annual conflict loss\n(high)"]
    vals = [700, 132, 400, 800]; cols = [NAVY, RED, GOLD, GOLD]
    bars = ax.bar(labels, vals, color=cols, width=0.55)
    for b, v in zip(bars, vals): ax.text(b.get_x() + b.get_width()/2, v + 18, f"Rs {v} bn", ha="center", fontsize=8)
    ax.set_ylabel("PKR billion", fontsize=8)
    ax.set_title("Figure 4. The merger's fiscal shortfall (Rs 568 bn) against annual conflict losses (Rs 400–800 bn)", fontsize=8.5, color=NAVY)
    ax.tick_params(labelsize=7); ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(os.path.join(FIGDIR, "fig4_fiscal.png")); plt.close(fig)

    # Fig 5 — scenarios
    fig, ax = plt.subplots(figsize=(7.2, 2.9), dpi=200)
    names = ["Scenario 1\nSustained normalization", "Scenario 2\nFragile equilibrium", "Scenario 3\nDeterioration"]
    lo = [15, 50, 25]; hi = [20, 60, 30]; mid = [(a+b)/2 for a, b in zip(lo, hi)]
    colors = ["#1E8449", GOLD, RED]
    ax.barh(names, mid, color=colors, height=0.5)
    for i, (a, b) in enumerate(zip(lo, hi)):
        ax.text(b + 1, i, f"{a}–{b}%", va="center", fontsize=8)
    ax.set_xlim(0, 75); ax.set_xlabel("Subjective probability to 2035 (per cent)", fontsize=8)
    ax.set_title("Figure 5. KP security scenarios to 2035 (Chapter 14 assessments)", fontsize=8.5, color=NAVY)
    ax.tick_params(labelsize=7.5); ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(os.path.join(FIGDIR, "fig5_scenarios.png")); plt.close(fig)

    print("Figures written to", FIGDIR)

# ----------------------------------------------------------------------------
# PDF rendering
# ----------------------------------------------------------------------------

def build_pdf(md_files, out_pdf, cover_title, cover_subtitle, cover_note,
              cover=True, toc=True, toc_levels=(1, 2)):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
    from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                    Spacer, Table, TableStyle, PageBreak, KeepTogether,
                                    HRFlowable, NextPageTemplate, Image)
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.pdfgen import canvas as pdfcanvas

    NAVY = colors.HexColor("#0B3A5D")
    GREY = colors.HexColor("#5D6D7E")
    LIGHT = colors.HexColor("#F2F5F7")
    LINE = colors.HexColor("#C9D4DA")

    styles = {
        "body": ParagraphStyle("body", fontName="Times-Roman", fontSize=9.4, leading=12.6,
                               alignment=TA_JUSTIFY, spaceAfter=5.5, textColor=colors.HexColor("#1A1A1A")),
        "h1": ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=15, leading=19,
                             textColor=NAVY, spaceBefore=0, spaceAfter=12),
        "h2": ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=11, leading=14,
                             textColor=NAVY, spaceBefore=11, spaceAfter=5),
        "h3": ParagraphStyle("H3", fontName="Helvetica-BoldOblique", fontSize=9.6, leading=12.5,
                             textColor=GREY, spaceBefore=9, spaceAfter=4),
        "bullet": ParagraphStyle("bullet", fontName="Times-Roman", fontSize=9.4, leading=12.4,
                                 leftIndent=14, bulletIndent=4, spaceAfter=3, alignment=TA_JUSTIFY),
        "caption": ParagraphStyle("caption", fontName="Helvetica", fontSize=7.6, leading=9.6,
                                  textColor=GREY, spaceBefore=4, spaceAfter=8),
        "cover_t": ParagraphStyle("cover_t", fontName="Helvetica-Bold", fontSize=25, leading=30,
                                  textColor=NAVY, alignment=TA_CENTER),
        "cover_s": ParagraphStyle("cover_s", fontName="Helvetica", fontSize=12.5, leading=17,
                                  textColor=GREY, alignment=TA_CENTER),
        "cover_m": ParagraphStyle("cover_m", fontName="Helvetica", fontSize=9.5, leading=14,
                                  textColor=colors.HexColor("#333333"), alignment=TA_CENTER),
        "toc_h": ParagraphStyle("toc_h", fontName="Helvetica-Bold", fontSize=9.6, leading=13,
                                textColor=NAVY),
        "toc_e": ParagraphStyle("toc_e", fontName="Times-Roman", fontSize=8.6, leading=11.6),
    }

    def tbl_style(ncols):
        return TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.2),
            ("LEADING", (0, 0), (-1, -1), 8.8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.4, LINE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
            ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ])

    class Doc(BaseDocTemplate):
        def afterFlowable(self, flowable):
            if isinstance(flowable, Paragraph):
                name = flowable.style.name
                if name == "H1" and 1 in toc_levels:
                    key = "sec-h1-" + str(self.seq.nextf("h1key"))
                    self.canv.bookmarkPage(key)
                    self.notify("TOCEntry", (0, flowable.getPlainText(), self.page, key))
                elif name == "H2" and 2 in toc_levels:
                    key = "sec-h2-" + str(self.seq.nextf("h2key"))
                    self.canv.bookmarkPage(key)
                    self.notify("TOCEntry", (1, flowable.getPlainText(), self.page, key))

    class NumCanvas(pdfcanvas.Canvas):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self._saved = []
        def showPage(self):
            self._saved.append(dict(self.__dict__)); self._startPage()
        def save(self):
            total = len(self._saved)
            for idx, state in enumerate(self._saved):
                self.__dict__.update(state)
                if idx > 0:
                    self.setFont("Helvetica", 7)
                    self.setFillColor(GREY)
                    self.drawString(20 * mm, A4[1] - 12 * mm, SHORT)
                    self.setStrokeColor(LINE); self.setLineWidth(0.4)
                    self.line(20 * mm, A4[1] - 14 * mm, A4[0] - 20 * mm, A4[1] - 14 * mm)
                    self.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Page {idx + 1} of {total}")
                    self.drawString(20 * mm, 12 * mm, "Research Monograph — October 2026")
                super().showPage()
            super().save()

    frame = Frame(20 * mm, 18 * mm, A4[0] - 40 * mm, A4[1] - 36 * mm, id="body")

    def on_cover(c, d):
        pass

    doc = Doc(out_pdf, pagesize=A4, title=cover_title, author="Independent policy research monograph",
              subject=cover_subtitle, leftMargin=20 * mm, rightMargin=20 * mm,
              topMargin=18 * mm, bottomMargin=18 * mm)
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[frame], onPage=on_cover),
        PageTemplate(id="body", frames=[frame]),
    ])

    story = []
    if cover:
        story += [Spacer(1, 34 * mm),
                  Paragraph(cover_title, styles["cover_t"]),
                  Spacer(1, 7 * mm),
                  HRFlowable(width="45%", thickness=1.1, color=NAVY, hAlign="CENTER"),
                  Spacer(1, 7 * mm),
                  Paragraph(cover_subtitle, styles["cover_s"]),
                  Spacer(1, 14 * mm),
                  Paragraph(cover_note, styles["cover_m"]),
                  NextPageTemplate("body"), PageBreak()]

    if toc:
        contents_style = ParagraphStyle("contents_head", parent=styles["h1"])
        story += [Paragraph("CONTENTS", contents_style)]
        toc_flow = TableOfContents()
        toc_flow.levelStyles = [styles["toc_h"], styles["toc_e"]]
        toc_flow.dotsMinLevel = 0
        story += [toc_flow, PageBreak()]

    first_h1 = True
    for fi, path in enumerate(md_files):
        text = open(path, encoding="utf-8").read()
        blocks = parse_md(text)
        if cover and fi == 0 and blocks and blocks[0][0] == "h" and blocks[0][1] == 1:
            blocks = blocks[1:]  # drop duplicate of cover title
            if blocks and blocks[0][0] == "h" and blocks[0][1] == 2:
                blocks = blocks[1:]  # drop duplicate of cover subtitle
        for b in blocks:
            if fi == 0 and b[0] == "h" and b[1] == 2 and b[2].strip().upper().startswith("CONTENTS"):
                break  # auto-generated TOC supersedes the manual contents list
            if b[0] == "h":
                lvl, txt = b[1], b[2]
                if lvl == 1:
                    if first_h1:
                        first_h1 = False
                    else:
                        story.append(PageBreak())
                    story.append(Paragraph(inline(txt), styles["h1"]))
                    story.append(HRFlowable(width="100%", thickness=0.8, color=NAVY, spaceAfter=8))
                elif lvl == 2:
                    story.append(Paragraph(inline(txt), styles["h2"]))
                else:
                    story.append(Paragraph(inline(txt), styles["h3"]))
            elif b[0] == "p":
                story.append(Paragraph(inline(b[1]), styles["body"]))
            elif b[0] == "ul":
                for it in b[1]:
                    story.append(Paragraph(inline(it), styles["bullet"], bulletText="•"))
                story.append(Spacer(1, 3))
            elif b[0] == "ol":
                for n, it in enumerate(b[1], 1):
                    story.append(Paragraph(inline(it), styles["bullet"], bulletText=f"{n}."))
                story.append(Spacer(1, 3))
            elif b[0] == "hr":
                story.append(HRFlowable(width="60%", thickness=0.5, color=LINE, spaceBefore=4, spaceAfter=6))
            elif b[0] == "fig":
                fpath = os.path.join(FIGDIR, b[1])
                if os.path.exists(fpath):
                    from reportlab.lib.utils import ImageReader
                    iw, ih = ImageReader(fpath).getSize()
                    w = A4[0] - 40 * mm
                    h = ih * w / iw
                    story.append(KeepTogether([Spacer(1, 4), Image(fpath, width=w, height=h),
                                               Paragraph(inline(b[2]), styles["caption"])]))
            elif b[0] == "table":
                rows = b[1]
                ncols = max(len(r) for r in rows)
                rows = [r + [""] * (ncols - len(r)) for r in rows]
                # column widths proportional to content length
                lens = []
                for ci in range(ncols):
                    cl = max(len(rows[ri][ci]) for ri in range(min(len(rows), 12)))
                    lens.append(max(cl, 6))
                total = sum(lens)
                avail = A4[0] - 40 * mm
                widths = [max(avail * l / total, 14 * mm) for l in lens]
                scale = avail / sum(widths)
                widths = [w * scale for w in widths]
                data = [[Paragraph(inline(c), ParagraphStyle("cell", fontName="Helvetica-Bold" if ri == 0 else "Times-Roman",
                                                            fontSize=7.2, leading=8.8, textColor=colors.white if ri == 0 else colors.HexColor("#1A1A1A")))
                         for c in row] for ri, row in enumerate(rows)]
                t = Table(data, colWidths=widths, repeatRows=1)
                t.setStyle(tbl_style(ncols))
                story.append(Spacer(1, 3)); story.append(t); story.append(Spacer(1, 7))

    doc.multiBuild(story, canvasmaker=NumCanvas)
    print("Wrote", out_pdf)

# ----------------------------------------------------------------------------
# DOCX rendering
# ----------------------------------------------------------------------------

def build_docx(md_files, out_docx, cover_title, cover_subtitle, cover_note):
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    NAVY = RGBColor(0x0B, 0x3A, 0x5D)
    doc = Document()
    st = doc.styles["Normal"]; st.font.name = "Cambria"; st.font.size = Pt(10.5)
    for sec in doc.sections:
        sec.left_margin = sec.right_margin = Inches(0.9)
        sec.top_margin = sec.bottom_margin = Inches(0.85)
    t = doc.add_paragraph(); r = t.add_run(cover_title); r.bold = True; r.font.size = Pt(20); r.font.color.rgb = NAVY
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    s = doc.add_paragraph(); r = s.add_run(cover_subtitle); r.font.size = Pt(12); r.italic = True
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    m = doc.add_paragraph(); r = m.add_run(cover_note); r.font.size = Pt(9); m.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def add_runs(p, text):
        # split on bold/italic markers
        parts = re.split(r"(\*\*.+?\*\*|\*[^*]+?\*)", text)
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                r = p.add_run(part[2:-2]); r.bold = True
            elif part.startswith("*") and part.endswith("*") and len(part) > 2:
                r = p.add_run(part[1:-1]); r.italic = True
            else:
                p.add_run(part)

    first_h1 = True
    for fi, path in enumerate(md_files):
        text = open(path, encoding="utf-8").read()
        blocks = parse_md(text)
        if fi == 0 and blocks and blocks[0][0] == "h" and blocks[0][1] == 1:
            blocks = blocks[1:]
        for b in blocks:
            if fi == 0 and b[0] == "h" and b[1] == 2 and b[2].strip().upper().startswith("CONTENTS"):
                break
            if b[0] == "h":
                lvl, txt = b[1], b[2]
                if lvl == 1:
                    if first_h1:
                        first_h1 = False
                    else:
                        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
                    h = doc.add_heading(level=1); r = h.add_run(txt); r.font.color.rgb = NAVY
                elif lvl == 2:
                    h = doc.add_heading(level=2); r = h.add_run(txt); r.font.color.rgb = NAVY
                else:
                    h = doc.add_heading(level=3); r = h.add_run(txt)
            elif b[0] == "p":
                p = doc.add_paragraph(); add_runs(p, b[1]); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            elif b[0] == "ul":
                for it in b[1]:
                    p = doc.add_paragraph(style="List Bullet"); add_runs(p, it)
            elif b[0] == "ol":
                for it in b[1]:
                    p = doc.add_paragraph(style="List Number"); add_runs(p, it)
            elif b[0] == "table":
                rows = b[1]
                ncols = max(len(r) for r in rows)
                tb = doc.add_table(rows=0, cols=ncols); tb.style = "Table Grid"
                for ri, row in enumerate(rows):
                    cells = tb.add_row().cells
                    for ci in range(ncols):
                        cell = cells[ci]
                        cell.text = ""
                        p = cell.paragraphs[0]; add_runs(p, row[ci] if ci < len(row) else "")
                        for run in p.runs:
                            run.font.size = Pt(8)
                            if ri == 0: run.bold = True
                doc.add_paragraph()
            elif b[0] == "fig":
                fpath = os.path.join(FIGDIR, b[1])
                if os.path.exists(fpath):
                    doc.add_picture(fpath, width=Inches(6.4))
                    cap = doc.add_paragraph(); r = cap.add_run(b[2]); r.italic = True; r.font.size = Pt(8.5)
                    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.save(out_docx)
    print("Wrote", out_docx)

# ----------------------------------------------------------------------------
# Build targets
# ----------------------------------------------------------------------------

def monograph_files():
    order = ["00_front_matter.md", "ch01_introduction.md", "ch02_history.md",
             "ch03_threat_landscape.md", "ch04_root_causes.md", "ch05_fata_merger.md",
             "ch06_military_operations.md", "ch07_law_enforcement.md",
             "ch08_deradicalization.md", "ch09_geopolitics.md", "ch10_socioeconomic.md",
             "11_governance_policy.md", "ch12_civil_society.md", "ch13_comparative.md",
             "14_scenarios_risk.md", "ch15_roadmap.md", "ch16_conclusion.md",
             "17_bibliography.md", "18_statistical_annex.md", "19_appendices.md"]
    return [os.path.join(CH, f) for f in order]

def write_combined():
    out = os.path.join(BUILD, "KPK_Security_Normalization_Full_Study.md")
    parts = []
    for f in monograph_files():
        txt = open(f, encoding="utf-8").read().strip()
        parts.append(txt)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n\n\n".join(parts) + "\n")
    words = sum(len(p.split()) for p in parts)
    print("Wrote", out, f"({words:,} words)")

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "monograph"
    make_figures()
    if cmd == "monograph":
        write_combined()
        build_pdf(monograph_files(), os.path.join(BUILD, "KPK_Security_Normalization_Monograph.pdf"),
                  TITLE, SUBTITLE,
                  "A Mixed-Methods Policy Research Monograph<br/>Data cut-off: 4 October 2026<br/>"
                  "Sixteen chapters · Statistical annex · 46-item recommendations matrix · Eight appendices")
        build_docx(monograph_files(), os.path.join(BUILD, "KPK_Security_Normalization_Monograph.docx"),
                   TITLE, SUBTITLE, "Data cut-off: 4 October 2026")
    elif cmd == "exec":
        files = [os.path.join(CH, "exec_summary.md")]
        build_pdf(files, os.path.join(BUILD, "KPK_Security_Executive_Summary.pdf"),
                  "EXECUTIVE SUMMARY", "Normalizing the Security Situation of Khyber Pakhtunkhwa",
                  "Companion to the full research monograph · Data cut-off: 4 October 2026",
                  cover=True, toc=False)
        build_docx(files, os.path.join(BUILD, "KPK_Security_Executive_Summary.docx"),
                   "EXECUTIVE SUMMARY", "Normalizing the Security Situation of Khyber Pakhtunkhwa",
                   "Companion to the full research monograph · Data cut-off: 4 October 2026")
    elif cmd == "brief":
        files = [os.path.join(CH, "policy_brief.md")]
        build_pdf(files, os.path.join(BUILD, "KPK_Security_Policy_Brief.pdf"),
                  "POLICY BRIEF", "Normalizing Security in Khyber Pakhtunkhwa: A 15-Year Roadmap",
                  "For federal and provincial decision-makers · Data cut-off: 4 October 2026",
                  cover=True, toc=False)
        build_docx(files, os.path.join(BUILD, "KPK_Security_Policy_Brief.docx"),
                   "POLICY BRIEF", "Normalizing Security in Khyber Pakhtunkhwa: A 15-Year Roadmap",
                   "For federal and provincial decision-makers · Data cut-off: 4 October 2026")
    else:
        print("Unknown target:", cmd); sys.exit(1)

if __name__ == "__main__":
    main()
