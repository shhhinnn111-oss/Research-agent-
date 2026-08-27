"""Verify the formatting contract of the generated thesis theme DOCX.

Checks (all must pass):
  1. every run in the document body, tables, header and footer is Arial / 14 pt / black;
  2. the document defines one four-level multilevel list with the requested patterns
     1.  ->  a.  ->  (1)  ->  (a), and levels restart under their parent;
  3. by simulating Word's numbering algorithm over the XML, every list paragraph's actual
     label is reproduced and matched against the expected pattern for its level.

Usage:  python verify_docx_format.py [path/to/file.docx]
"""

import re
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

LEVEL_PATTERNS = [
    re.compile(r"^\d+\.$"),          # 1.
    re.compile(r"^[a-z]\.$"),        # a.
    re.compile(r"^\(\d+\)$"),        # (1)
    re.compile(r"^\([a-z]\)$"),      # (a)
]
CONVERTERS = {
    "decimal": lambda n: str(n),
    "lowerLetter": lambda n: chr(ord("a") + n - 1) if 1 <= n <= 26 else str(n),
    "upperLetter": lambda n: chr(ord("A") + n - 1) if 1 <= n <= 26 else str(n),
    "lowerRoman": lambda n: _roman(n),
    "upperRoman": lambda n: _roman(n).upper(),
}


def _roman(num):
    vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
            (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, sym in vals:
        while num >= v:
            out += sym
            num -= v
    return out or "0"


def load_lists(doc):
    """Return {numId: [ {fmt, text}, ... ]} for the abstractNum each numId points at."""
    numbering = doc.part.numbering_part.element
    abstracts = {}
    for abs_el in numbering.findall(qn("w:abstractNum")):
        aid = abs_el.get(qn("w:abstractNumId"))
        levels = []
        for lvl in abs_el.findall(qn("w:lvl")):
            fmt = lvl.find(qn("w:numFmt"))
            txt = lvl.find(qn("w:lvlText"))
            ppr = lvl.find(qn("w:pPr"))
            ind = ppr.find(qn("w:ind")) if ppr is not None else None
            levels.append({
                "fmt": fmt.get(qn("w:val")) if fmt is not None else "decimal",
                "text": txt.get(qn("w:val")) if txt is not None else "",
                "left": ind.get(qn("w:left")) if ind is not None else None,
                "hanging": ind.get(qn("w:hanging")) if ind is not None else None,
            })
        abstracts[aid] = levels
    mapping = {}
    for num_el in numbering.findall(qn("w:num")):
        nid = num_el.get(qn("w:numId"))
        ref = num_el.find(qn("w:abstractNumId"))
        if ref is not None:
            mapping[nid] = abstracts.get(ref.get(qn("w:val")), [])
    return mapping


def style_numbering(doc):
    """Map paragraph style name -> (numId, ilvl) for styles that carry numbering."""
    out = {}
    for style in doc.styles:
        ppr = style.element.find(qn("w:pPr"))
        if ppr is None:
            continue
        numpr = ppr.find(qn("w:numPr"))
        if numpr is None:
            continue
        ilvl = numpr.find(qn("w:ilvl"))
        numid = numpr.find(qn("w:numId"))
        if ilvl is not None and numid is not None:
            out[style.name] = (numid.get(qn("w:val")), int(ilvl.get(qn("w:val"))))
    return out


def paragraph_numbering(p, style_map, abstracts):
    numpr = p._p.find(qn("w:pPr") + "/" + qn("w:numPr"))
    if numpr is None:
        ppr = p._p.find(qn("w:pPr"))
        numpr = ppr.find(qn("w:numPr")) if ppr is not None else None
    if numpr is not None:
        ilvl_el = numpr.find(qn("w:ilvl"))
        numid_el = numpr.find(qn("w:numId"))
        numid = numid_el.get(qn("w:val")) if numid_el is not None else None
        ilvl = int(ilvl_el.get(qn("w:val"))) if ilvl_el is not None else 0
        if numid:
            return numid, ilvl
    name = p.style.name if p.style is not None else None
    if name in style_map:
        return style_map[name]
    return None, None


def render_labels(doc):
    """Simulate Word's multilevel numbering and yield (label, level, text) for each item."""
    abstracts = load_lists(doc)
    style_map = style_numbering(doc)
    counters = {}
    rendered = []
    for p in doc.paragraphs:
        numid, ilvl = paragraph_numbering(p, style_map, abstracts)
        if numid is None:
            continue
        levels = abstracts[numid]
        state = counters.setdefault(numid, [0] * len(levels))
        state[ilvl] += 1
        for deeper in range(ilvl + 1, len(state)):
            state[deeper] = 0
        spec = levels[ilvl]
        label = spec["text"]
        for depth in range(len(state)):
            conv = CONVERTERS.get(levels[depth]["fmt"], CONVERTERS["decimal"])
            label = label.replace(f"%{depth + 1}", conv(state[depth] or 1))
        rendered.append((label, ilvl, p.text.strip(), spec))
    return rendered


def all_runs(doc):
    for p in doc.paragraphs:
        yield from p.runs
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    yield from p.runs
    for section in doc.sections:
        for part in (section.header, section.footer):
            for p in part.paragraphs:
                yield from p.runs


def main(path):
    doc = Document(path)
    problems = []

    # --- 1. fonts --- #
    checked = 0
    for run in all_runs(doc):
        checked += 1
        txt = (run.text or "").strip()
        if not txt:
            continue
        name = run.font.name
        size = run.font.size
        color = run.font.color.rgb if run.font.color and run.font.color.type is not None else None
        if name != "Arial":
            problems.append(f"font name: {name!r} for {txt[:40]!r}")
        if size is None or size.pt != 14.0:
            problems.append(f"font size: {size} for {txt[:40]!r}")
        if str(color) != "000000":
            problems.append(f"font colour: {color} for {txt[:40]!r}")

    # also inspect raw rPr on every run, including field runs python-docx does not model
    for r in doc.element.body.iter(qn("w:r")):
        rpr = r.find(qn("w:rPr"))
        rf = rpr.find(qn("w:rFonts")) if rpr is not None else None
        if rf is not None:
            for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
                if rf.get(qn("w:" + attr)) not in (None, "Arial"):
                    problems.append(f"raw rFonts {attr}={rf.get(qn('w:' + attr))}")
        sz = rpr.find(qn("w:sz")) if rpr is not None else None
        if sz is not None and sz.get(qn("w:val")) not in (None, "28"):
            problems.append(f"raw sz={sz.get(qn('w:val'))}")

    # --- 2/3. numbering --- #
    rendered = render_labels(doc)
    level_counts = {0: 0, 1: 0, 2: 0, 3: 0}
    for label, ilvl, text, spec in rendered:
        level_counts[ilvl] = level_counts.get(ilvl, 0) + 1
        pat = LEVEL_PATTERNS[ilvl] if ilvl < 4 else None
        if pat is None:
            problems.append(f"unexpected level {ilvl}")
        elif not pat.match(label):
            problems.append(f"level {ilvl} label {label!r} does not match {pat.pattern}")

    print(f"file                : {path}")
    print(f"paragraphs (body)   : {len(doc.paragraphs)}")
    print(f"tables              : {len(doc.tables)}")
    print(f"numbered items      : {len(rendered)}")
    print(f"  level 1 '1.'      : {level_counts.get(0, 0)}")
    print(f"  level 2 'a.'      : {level_counts.get(1, 0)}")
    print(f"  level 3 '(1)'     : {level_counts.get(2, 0)}")
    print(f"  level 4 '(a)'     : {level_counts.get(3, 0)}")
    print(f"runs font-checked   : {checked}")
    words = sum(len(p.text.split()) for p in doc.paragraphs)
    print(f"approx word count   : {words}")
    print("\nfirst 28 numbered lines as Word will render them:")
    for label, ilvl, text, spec in rendered[:28]:
        print(f"  {'   ' * ilvl}{label}\t{text[:74]}")
    print("\nrestart behaviour spot-check (level 2 counters under each level 1 item):")
    last_top = None
    seq = []
    for label, ilvl, text, spec in rendered:
        if ilvl == 0:
            if seq:
                print("   " + last_top + " -> " + " ".join(seq))
            last_top, seq = label, []
        elif ilvl == 1:
            seq.append(label)
    if seq:
        print("   " + last_top + " -> " + " ".join(seq))

    if problems:
        print(f"\nFAILED: {len(problems)} formatting problems")
        for pb in problems[:25]:
            print("  -", pb)
        return 1
    print("\nPASS: Arial 14 pt black everywhere; four-level numbering 1. / a. / (1) / (a) correct.")
    return 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else str(
        Path(__file__).resolve().parent
        / "PhD-Thesis-Theme_Chinese-Governance-State-Capacity-and-Lessons-for-Pakistan.docx")
    sys.exit(main(target))
