"""Build the PhD thesis theme document (DOCX).

Formatting contract enforced here:
  * every character (title, body, lists, tables, footer) is Arial, 14 pt, black;
  * all list content is ONE real Word multilevel list with the four requested levels:
        1.   decimal        "%1."
        a.   lowerLetter    "%2."
        (1)  decimal        "(%3)"
        (a)  lowerLetter    "(%4)"
    so numbers update automatically and restart correctly under each parent.
"""

from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT, SIZE, BLACK = "Arial", Pt(14), RGBColor(0x00, 0x00, 0x00)
ABSTRACT_NUM_ID = 500
NUM_ID = 500

# (numFmt, lvlText, w:left indent twips, w:hanging twips)
LEVELS = [
    ("decimal", "%1.", 425, 425),
    ("lowerLetter", "%2.", 850, 425),
    ("decimal", "(%3)", 1275, 425),
    ("lowerLetter", "(%4)", 1700, 425),
]

# Canonical child order for the OOXML elements we touch (used for schema-safe inserts).
RPR_ORDER = ("w:rStyle w:rFonts w:b w:bCs w:i w:iCs w:caps w:smallCaps w:strike w:dstrike w:outline "
             "w:shadow w:emboss w:imprint w:noProof w:snapToGrid w:vanish w:webHidden w:color "
             "w:spacing w:w w:kern w:position w:sz w:szCs w:highlight w:u w:effect w:bdr w:shd "
             "w:fitText w:vertAlign w:rtl w:cs w:em w:lang").split()
PPR_ORDER = ("w:pStyle w:keepNext w:keepLines w:pageBreakBefore w:framePr w:widowControl w:numPr "
             "w:suppressLineNumbers w:pBdr w:shd w:tabs w:suppressAutoHyphens w:kinsoku w:wordWrap "
             "w:overflowPunct w:topLinePunct w:autoSpaceDE w:autoSpaceDN w:bidi w:adjustRightInd "
             "w:snapToGrid w:spacing w:ind w:contextualSpacing w:mirrorIndents w:suppressOverlap "
             "w:jc w:textDirection w:textAlignment w:textboxTightWrap w:outlineLvl w:divId "
             "w:cnfStyle w:rPr w:sectPr w:pPrChange").split()

STYLE_ORDER = ("w:name w:aliases w:basedOn w:next w:link w:autoRedefine w:hidden w:uiPriority "
               "w:semiHidden w:unhideWhenUsed w:qFormat w:locked w:personal w:personalCompose "
               "w:personalReply w:rsid w:pPr w:rPr w:tblPr w:trPr w:tcPr w:tblStylePr").split()


def sub(parent, tag, order=None, **attrs):
    """Create/replace a child element, keeping OOXML child order valid."""
    if isinstance(parent, list):  # not used; defensive
        raise TypeError
    el = OxmlElement(tag)
    for key, val in attrs.items():
        el.set(qn("w:" + key), str(val))
    if order:
        idx = order.index(tag)
        parent.insert_element_before(el, *order[idx + 1:])
    else:
        parent.append(el)
    return el


def ensure(parent, tag, order=None):
    el = parent.find(qn(tag))
    if el is None:
        el = sub(parent, tag, order=order)
    return el


def clear(parent, *tags):
    for tag in tags:
        for found in parent.findall(qn(tag)):
            parent.remove(found)


# --------------------------------------------------------------------------- #
# Font handling
# --------------------------------------------------------------------------- #
def style_font(style, bold=False, italic=False, caps=False):
    """Force Arial / 14 pt / black on a style (also drives the list-number glyph font)."""
    st = style.element
    rpr = st.get_or_add_rPr()
    clear(rpr, "w:rFonts", "w:sz", "w:szCs", "w:b", "w:bCs", "w:i", "w:iCs", "w:color",
          "w:caps", "w:smallCaps")
    rfonts = ensure(rpr, "w:rFonts", RPR_ORDER)
    for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
        rfonts.set(qn("w:" + attr), FONT)
    rfonts.set(qn("w:hint"), "default")
    if bold:
        sub(rpr, "w:b", order=RPR_ORDER)
        sub(rpr, "w:bCs", order=RPR_ORDER)
    if italic:
        sub(rpr, "w:i", order=RPR_ORDER)
        sub(rpr, "w:iCs", order=RPR_ORDER)
    if caps:
        sub(rpr, "w:smallCaps", order=RPR_ORDER)
    color = sub(rpr, "w:color", order=RPR_ORDER, val="000000")
    sub(rpr, "w:sz", order=RPR_ORDER, val="28")
    sub(rpr, "w:szCs", order=RPR_ORDER, val="28")


def apply_font(run, bold=False, italic=False):
    """Arial 14 pt black. bold/italic are only written when True, so that the formatting
    carried by the paragraph style (section bold, sub-point italic) is not cancelled."""
    run.font.name = FONT
    run.font.size = SIZE
    run.font.color.rgb = BLACK
    if bold:
        run.bold = True
    if italic:
        run.italic = True
    rpr = run._element.get_or_add_rPr()
    rfonts = ensure(rpr, "w:rFonts", RPR_ORDER)
    for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
        rfonts.set(qn("w:" + attr), FONT)
    for attr in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        if rfonts.get(qn("w:" + attr)):
            del rfonts.attrib[qn("w:" + attr)]
    ensure(rpr, "w:szCs", RPR_ORDER).set(qn("w:val"), "28")
    ensure(rpr, "w:color", RPR_ORDER).set(qn("w:val"), "000000")
    if italic:
        ensure(rpr, "w:iCs", RPR_ORDER)
    if bold:
        ensure(rpr, "w:bCs", RPR_ORDER)


# --------------------------------------------------------------------------- #
# Multilevel numbering definition
# --------------------------------------------------------------------------- #
def add_numbering_definition(doc):
    numbering = doc.part.numbering_part.element
    first_abstract = numbering.find(qn("w:abstractNum"))

    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(ABSTRACT_NUM_ID))
    if first_abstract is not None:
        first_abstract.addprevious(abstract)
    else:
        numbering.append(abstract)

    sub(abstract, "w:nsid", val="07A1B301")
    sub(abstract, "w:multiLevelType", val="multilevel")
    sub(abstract, "w:tmpl", val="07A1B301")
    sub(abstract, "w:name", val="Thesis Four Level")

    for ilvl, (fmt, text, left, hanging) in enumerate(LEVELS):
        lvl = sub(abstract, "w:lvl", ilvl=ilvl)
        sub(lvl, "w:start", val="1")
        sub(lvl, "w:numFmt", val=fmt)
        sub(lvl, "w:lvlRestart", val="1")
        sub(lvl, "w:pStyle", val=f"ThesisList{ilvl + 1}")
        sub(lvl, "w:suff", val="tab")
        sub(lvl, "w:lvlText", val=text)
        sub(lvl, "w:lvlJc", val="left")
        ppr = sub(lvl, "w:pPr")
        sub(ppr, "w:ind", left=left, hanging=hanging)
        sub(lvl, "w:rPr")

    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(NUM_ID))
    numbering.append(num)
    sub(num, "w:abstractNumId", val=ABSTRACT_NUM_ID)


def make_list_styles(doc):
    """Four paragraph styles that carry the numbering plus the Arial/14/black formatting."""
    specs = [
        ("ThesisList1", 0, True, False, 16, 5),   # 1.   major section  - bold
        ("ThesisList2", 1, True, False, 9, 4),    # a.   sub-theme       - bold
        ("ThesisList3", 2, False, True, 6, 3),    # (1)  analytic point  - italic
        ("ThesisList4", 3, False, False, 4, 3),   # (a)  detail         - plain
    ]
    base = doc.styles["Normal"]
    for name, ilvl, bold, italic, before, after in specs:
        style = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        style.base_style = base
        style.quick_style = True
        pf = style.paragraph_format
        pf.space_before = Pt(before)
        pf.space_after = Pt(after)
        pf.line_spacing = 1.2
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        pf.keep_with_next = ilvl < 2
        ppr = style.element.get_or_add_pPr()
        if ilvl < 2:
            ensure(ppr, "w:outlineLvl", PPR_ORDER).set(qn("w:val"), str(ilvl))
        numpr = ppr.get_or_add_numPr()
        numpr.get_or_add_ilvl().val = ilvl
        numpr.get_or_add_numId().val = NUM_ID
        style_font(style, bold=bold, italic=italic)
    return specs


# --------------------------------------------------------------------------- #
# Paragraph / table helpers
# --------------------------------------------------------------------------- #
def add_para(doc, text, style=None, align=None, before=0, after=6, bold=False, italic=False,
             spacing=1.2):
    p = doc.add_paragraph(style=style)
    if align is not None:
        p.alignment = align
    if style is None:
        pf = p.paragraph_format
        pf.space_before, pf.space_after, pf.line_spacing = Pt(before), Pt(after), spacing
    for idx, chunk in enumerate(text.split("**")):
        if not chunk:
            continue
        apply_font(p.add_run(chunk), bold=bold or idx % 2 == 1, italic=italic)
    if not p.runs:
        apply_font(p.add_run(""))
    return p


def set_cell(cell, text, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    pf = p.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(2), Pt(2), 1.15
    for idx, chunk in enumerate(text.split("**")):
        if chunk:
            apply_font(p.add_run(chunk), bold=bold or idx % 2 == 1)


def boxed(table):
    tbl_pr = table._tbl.tblPr
    clear(tbl_pr, "w:tblBorders")
    borders = sub(tbl_pr, "w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        sub(borders, f"w:{edge}", val="single", sz="8", space="0", color="000000")


def add_footer_page_number(doc):
    for footer in (doc.sections[0].footer, doc.sections[0].header):
        for p in footer.paragraphs:
            for r in list(p.runs):
                r._element.getparent().remove(r._element)
    footer_p = doc.sections[0].footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    label = footer_p.add_run("Page ")
    apply_font(label)
    for instr in ("PAGE", "NUMPAGES"):
        fld = OxmlElement("w:fldSimple")
        fld.set(qn("w:instr"), instr)
        run = OxmlElement("w:r")
        rpr = OxmlElement("w:rPr")
        rf = OxmlElement("w:rFonts")
        for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
            rf.set(qn("w:" + attr), FONT)
        rpr.append(rf)
        for tag in ("w:sz", "w:szCs"):
            e = OxmlElement(tag)
            e.set(qn("w:val"), "28")
            rpr.append(e)
        c = OxmlElement("w:color")
        c.set(qn("w:val"), "000000")
        rpr.append(c)
        run.append(rpr)
        t = OxmlElement("w:t")
        t.text = "1"
        run.append(t)
        fld.append(run)
        footer_p._p.append(fld)
        if instr == "PAGE":
            mid = footer_p.add_run(" of ")
            apply_font(mid)
    return


def rule(doc, after=10):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.0
    ppr = p._p.get_or_add_pPr()
    clear(ppr, "w:pBdr")
    borders = sub(ppr, "w:pBdr")
    sub(borders, "w:bottom", val="single", sz="12", space="1", color="000000")


# --------------------------------------------------------------------------- #
# Content
# --------------------------------------------------------------------------- #
# kinds: T = title (centred, bold) | C = centred plain | P = plain | 1..4 = numbering levels
#        META = metadata table | BREAK = page break | NOTE = boxed note
HEAD = [
    ("T", "RESEARCH THEME FOR DOCTORAL (PhD) THESIS"),
    ("T", "CHINESE GOVERNANCE SYSTEM, DECISION-MAKING, STATE CAPACITY, "
          "STRATEGIC GOVERNANCE AND LESSONS FOR PAKISTAN"),
    ("C", "Theme Statement and Pre-Synopsis Framework"),
    ("C", "**Proposed theme:** Four Gears of Strategic Governance — What China's Decision-Making "
          "and State-Capacity Architecture Can, and Cannot, Teach Pakistan"),
    ("C", "Discipline: Political Science / Public Administration  ·  Paradigm: comparative "
          "institutional analysis  ·  Version 1.0  ·  August 2026"),
]

META = [
    ("Candidate name", "____________________________"),
    ("Registration / roll no.", "____________________________"),
    ("Programme", "PhD (Public Administration / Political Science)"),
    ("Department / institution", "____________________________"),
    ("Proposed supervisor", "____________________________"),
    ("Proposed co-supervisor", "____________________________"),
    ("Thesis type", "Comparative, qualitative-dominant mixed methods"),
    ("Purpose of this document", "Approval of the research theme; basis for the synopsis, "
                                "coursework essay and fieldwork planning"),
]

BODY = [
    # ---------------------------------------------------------------- 1
    ("1", "Proposed Thesis Titles"),
    ("2", "Primary title recommended for the synopsis"),
    ("3", "“Four Gears of Strategic Governance: China's Decision-Making System, State Capacity, and "
          "Transferable Lessons for Pakistan's Administrative Reform”"),
    ("4", "Strengths: it names all four constructs in the approved topic (governance system, "
          "decision-making, state capacity, strategic governance) and signals mechanism-level analysis "
          "rather than praise or imitation; “transferable” commits the thesis to a conditionality test."),
    ("4", "Risk to manage: a metaphor in a title must be defined and used consistently in Chapter 3, or "
          "examiners will read it as decoration. If the supervisor objects to metaphors, use the "
          "secondary option below."),
    ("4", "Regulatory check: confirm the department's maximum title length and whether subtitles are "
          "permitted on the title page."),
    ("2", "Secondary options, each suited to a different audience"),
    ("3", "**Institutional-design option** — “From Plan to Delivery: China's Strategic Governance "
          "Architecture and Pakistan's Implementation Deficit”."),
    ("4", "Best fit if the department is Public Administration; foregrounds the puzzle rather than the "
          "country comparison."),
    ("3", "**Policy-learning option** — “Learning from an Ally: Policy Transfer, State Capacity and "
          "China's Governance Practices in Pakistan's Reform Agenda, 2013–2026”."),
    ("4", "Best fit if the supervisor works in comparative policy; makes the transfer literature, not "
          "China studies, the theoretical home."),
    ("3", "**Narrow and current option** — “Codifying the Plan: China's National Development Plans Law "
          "(2026), Strategic Governance, and Lessons for Pakistan's Planning System”."),
    ("4", "Sharpest and most publishable, but it constricts Chapter 6 and the cadre-system analysis; "
          "choose it only if the supervisor wants a tight, document-based thesis."),
    ("3", "**Developmental-state option** — “Embedded Capacity Reconsidered: Incentives, Information and "
          "Discipline in the Chinese and Pakistani Bureaucracies”."),
    ("4", "Theoretically strongest, empirically heaviest: it requires primary data from both "
          "bureaucracies and is therefore riskier inside a three-to-four-year cycle."),
    ("2", "Title hygiene the thesis will observe"),
    ("3", "No filler constructions (“A Study of…”, “An Analysis of…”, “…in Light of…”), at most one "
          "colon, and no title that promises causal estimation the design cannot deliver."),
    ("3", "Every noun in the chosen title must map onto a defined construct in Chapter 3 and onto at "
          "least one chapter of evidence; otherwise it is deleted from the title."),
    ("3", "The chosen title must survive three tests: the examiner's question “what did you actually "
          "do?”, the archivist's question “which documents?”, and the policy reader's question “what "
          "should Pakistan change on Monday morning?”"),

    # ---------------------------------------------------------------- 2
    ("1", "The Theme in One Page"),
    ("2", "Core claim"),
    ("3", "China's development outcome is not explained primarily by an economic model but by a "
          "**governance technology**: a durable, observable and partly learnable machinery that "
          "converts strategic intent into implemented policy."),
    ("3", "That machinery is analysed as four coupled gears — **Direction** (who sets binding "
          "priorities and for how long), **Delegation** (how execution is contracted to lower levels "
          "with resources and discretion), **Data** (how the centre learns what is actually happening) "
          "and **Discipline** (how performance and probity are rewarded or punished)."),
    ("3", "Pakistan's problem is not an absence of plans, councils, authorities or zones, but the "
          "absence of the **connective tissue** between them: the personnel system, fiscal incentive "
          "structure, information apparatus and accountability loop that turn an announced intention "
          "into a delivered service."),
    ("2", "The reframing that makes this a doctoral question rather than a policy essay"),
    ("3", "The question is not “should Pakistan copy China?”, which is unanswerable, but “which "
          "specific mechanisms explain China's execution capability, and under what constitutional, "
          "fiscal and bureaucratic preconditions could Pakistan reconstitute them?”"),
    ("3", "Every candidate lesson must therefore be stated as a **mechanism plus precondition plus "
          "legal instrument plus risk**; anything that cannot be stated that way is excluded from the "
          "thesis."),
    ("2", "Concepts the thesis holds constant"),
    ("3", "**Governance system** — the organisations that bear authority and the rules allocating "
          "agenda-setting, decision and implementation rights among them."),
    ("3", "**Decision-making** — the observable procedure by which an issue becomes a binding "
          "decision: who researches, who consults, who negotiates, who ratifies, how dissent is "
          "processed."),
    ("3", "**State capacity** — the effective ability to extract revenue, apply law, generate "
          "reliable information, staff and motivate a bureaucracy, and deliver services."),
    ("3", "**Strategic governance** — governing through an explicit, time-phased, publicly stated "
          "plan that binds and coordinates lower-tier actors, with periodic revision; a mode between "
          "command planning and market-steering."),
    ("3", "**Lessons** — evaluated, conditional, constitutionally admissible policy transfers, with "
          "an explicit account of what is **non-transferable**."),
    ("2", "One-line answer for the synopsis defence"),
    ("3", "Plans are cheap; the machinery that connects a plan to a person's career and a citizen's "
          "file is what China built and what Pakistan has not."),

    # ---------------------------------------------------------------- 2
    ("1", "Background and Context"),
    ("2", "The Chinese case: long-run accumulation of governance capability"),
    ("3", "Continuity of the planning instrument"),
    ("4", "Seven decades of five-year planning, from the First Five-Year Plan (1953–1957) to the "
          "Fifteenth Five-Year Plan (2026–2030), approved by the National People's Congress in March "
          "2026 together with the Outline of Long-Range Objectives to 2035."),
    ("4", "The plan's substantive content (a modern industrial system as first priority, core digital "
          "industries targeted at about 12.5 per cent of GDP, society-wide R&D growth above 7 per cent "
          "a year) is context; the **procedure** that produced it is this thesis's data."),
    ("3", "Legal codification of the planning cycle — the most current and most researchable hook"),
    ("4", "In March 2026 the NPC also adopted the **Law on National Development Plans**, the first "
          "statute to formalise the whole lifecycle: preliminary study, drafting, public "
          "participation, legislative review and approval, implementation, and oversight."),
    ("4", "It codifies the differentiated hierarchy introduced by the 2018 joint opinion of the CPC "
          "Central Committee and State Council — national development plans, special (sectoral) plans, "
          "regional plans and territorial-spatial plans, with the national plan “commanding” the rest."),
    ("4", "For this thesis, the requirement that provincial draft plans be submitted to the National "
          "Development and Reform Commission for coordination before sub-national approval is a "
          "precise, codeable variable: **engineered vertical coherence**."),
    ("3", "Governance modernisation as a declared, deadline-bound objective"),
    ("4", "“Modernising China's system and capacity for governance” was set as a total reform "
          "objective in 2013 (Third Plenum of the 18th Central Committee), elaborated in 2019 (Fourth "
          "Plenum of the 19th Central Committee), and reaffirmed in July 2024 by the Third Plenum of "
          "the 20th Central Committee, whose Decision lists about 300 reform measures with a 2029 "
          "completion deadline."),
    ("4", "The 2024 Decision explicitly pledges to improve “the national strategic planning system and "
          "policy coordination mechanisms” and to pursue coordinated fiscal, taxation and financial "
          "reform — the state openly re-engineering its own steering apparatus."),
    ("3", "Institutional surgery as routine practice"),
    ("4", "The 2023 Party and state institutional reform re-tiered apex coordination bodies (for "
          "example elevating financial authority to a Central Financial Commission, and creating a "
          "National Financial Regulatory Administration, a Central Social Work Department and a "
          "national data administration), and re-scoped ministry functions."),
    ("4", "This capacity to restructure the decision-making core in response to identified failures is "
          "treated in this thesis as an **independent variable**, not as background."),
    ("3", "The incentive and accountability layer beneath the architecture"),
    ("4", "Target responsibility contracts, promotion competition among jurisdictions, priority "
          "targets carrying veto weight, cross-jurisdictional rotation, inspection tours and audit "
          "follow-up are the mechanisms through which the centre makes local leaders care."),
    ("4", "Documented pathologies of the same layer — statistical distortion, “target-driven "
          "formalism”, local-government debt, risk aversion under intense discipline — are analysed as "
          "part of the model, not as rebuttals to it."),
    ("2", "The Pakistani case: institutional abundance, capability fragmentation"),
    ("3", "Planning interrupted, then revived without binding force"),
    ("4", "The Planning Commission was constituted in the early 1950s, abolished in 1998 and revived "
          "after the Eighteenth Amendment; the Twelfth Plan (2018–2025) and the Thirteenth Plan "
          "(2024/25–2028/29) were both late and left no binding inter-governmental implementation "
          "contract."),
    ("4", "Since 1988 the three-year IMF-centred cycle has functioned as Pakistan's de facto "
          "medium-term plan; the Fund itself has observed that the absence of a comprehensive "
          "medium-term planning document weakens the link between development ambitions and public "
          "investment."),
    ("3", "A constitutional order of divided authority, continuously re-written"),
    ("4", "The Eighteenth Amendment (2010) abolished the Concurrent List and devolved extensively; "
          "Article 140-A mandates an elected local-government tier that no province has implemented in a "
          "sustained, constitutionally compliant way — re-confirmed by the Task Force on Reforms in "
          "Local Governance in its 2026 report, which proposed giving Article 140-A the enforceability "
          "that Article 160 gives to the NFC award."),
    ("4", "The Twenty-Sixth Amendment (October 2024) and Twenty-Seventh Amendment (November 2025), "
          "which established a Federal Constitutional Court and revised judicial-appointment, "
          "command and federal–provincial provisions, together with the 2025–2026 debate over new "
          "provinces and administrative regions, show reform energy concentrated on **architecture and "
          "maps** rather than on delivery capacity."),
    ("4", "Note: every amendment section used in the thesis must be verified against the official "
          "gazette; newspaper reporting is treated as a research lead only."),
    ("3", "Coordination devices without connective machinery"),
    ("4", "The Special Investment Facilitation Council (created by Cabinet approval on 20 June 2023 as "
          "a single-window investment body chaired by the Prime Minister and including the chief "
          "ministers and service-chief representation), its overseeing Federal Cabinet Committee, the "
          "Board of Investment and the PMU CPEC–ICDP form fast-track decision-making **layered over** "
          "ordinary administration instead of integrated with it."),
    ("4", "Notified Special Economic Zones grew from seven in 2019 to roughly 44 by 2025, while "
          "commentary on CPEC's second phase keeps identifying the binding constraint as **ownership of "
          "delivery** — land, utilities, skills, permit stacking and regulatory predictability — rather "
          "than finance or approval."),
    ("3", "Personnel capacity as the openly contested variable"),
    ("4", "The Civil Service Reforms Committee (2025) proposals to move from the generalist Central "
          "Superior Services model to cluster-based, subject-specific recruitment, together with "
          "amendments to the Civil Servants Act and stronger appraisal, are direct evidence that "
          "Pakistan has itself diagnosed the cadre system as the binding constraint."),
    ("4", "The current programme's structural benchmarks (separating tax policy from collection through "
          "a Tax Policy Office, DISCO restructuring, state-enterprise governance) constitute a natural "
          "experiment window for 2024–2027 that the thesis can exploit."),
    ("2", "Bilateral and scholarly context"),
    ("3", "2026 marks the 75th anniversary of Pakistan–China diplomatic relations; CPEC has moved to a "
          "second, industry- and agriculture-centred phase, with industrial cooperation channelled "
          "through a Joint Working Group between the Board of Investment and China's NDRC."),
    ("3", "The existing literature on this partnership is dense on infrastructure, energy, debt and "
          "geopolitics, but thin on the relationship as a channel of **governance knowledge transfer** "
          "(training, secondments, planning technique, zone administration, digital-government "
          "systems) — the gap this thesis occupies."),
    ("3", "Pakistani reform debate repeatedly invokes China by name without analysing the "
          "institutions invoked; that invocation is itself a data source for the discursive analysis in "
          "Chapter 7."),
    ("2", "Why this theme is timely for a 2026–2029 doctoral cycle"),
    ("3", "China's planning system has just been codified into law, and its 2024 reform list expires "
          "in 2029 — an evaluation window opening exactly during the thesis period."),
    ("3", "Pakistan simultaneously has a live civil-service reform file, a local-government "
          "task-force report, a revived five-year plan, and post-programme reform obligations — an "
          "unusually receptive policy moment for a thesis with a practical output."),

    # ---------------------------------------------------------------- 3
    ("1", "Statement of the Problem"),
    ("2", "The problem"),
    ("3", "Pakistan has replicated the **visible forms** of strategic governance — five-year plans, "
          "apex councils, single-window facilitation, special economic zones, digital service portals, "
          "performance-reporting initiatives — while lacking the **invisible machinery** that converts "
          "form into execution."),
    ("3", "As a result, the country's reform rate is high and its delivery rate low: the gap between "
          "announced policy and delivered service is the empirical object of this thesis."),
    ("2", "Three facets of one problem"),
    ("3", "**Direction** — strategic intent is produced by short-horizon, crisis-responsive cycles "
          "(annual budgets, programme reviews, ad hoc task forces) rather than by a statutory planning "
          "cycle with binding downstream instruments."),
    ("3", "**Delegation** — sub-national execution is governed by bargaining, discretionary transfers "
          "and weak service standards, rather than by measurable, career-linked targets with resources "
          "attached."),
    ("3", "**Data and Discipline** — accountability instances (audit, accountability bureaux, "
          "accounting officers, appraisal reports) rarely terminate in career or budgetary "
          "consequences, so information about performance is neither reliable nor consequential."),
    ("2", "Why it is a research problem rather than a policy cliché"),
    ("3", "Comparative scholarship usually explains outcomes either by **regime type**, which makes "
          "China untransferable by assumption, or by **capital and geography**, which ignores "
          "implementation; the middle-level institutional mechanisms in between are under-theorised."),
    ("3", "There is no validated instrument that decomposes governance capability for China and "
          "Pakistan at comparable sub-national granularity; building and testing one is part of the "
          "contribution."),
    ("3", "Policy-transfer theory has been applied to East Asian developmental states but rarely to a "
          "South–South, asymmetric, alliance-based pair in which the receiving state is a parliamentary "
          "federation."),
    ("2", "Costs of leaving it unaddressed"),
    ("3", "Reform continues to be designed as organisations (a new authority, cell or council) rather "
          "than as systems of incentives, information and consequences — reproducing the failure it is "
          "meant to cure."),
    ("3", "The relationship with China continues to be valued only for financing and construction, "
          "leaving unused the cheapest available instrument: institutional learning from the state "
          "that has most improved execution capability in the same region and income trajectory."),

    # ---------------------------------------------------------------- 4
    ("1", "Research Questions"),
    ("2", "Primary question"),
    ("3", "Which institutional mechanisms of China's strategic governance system explain its capacity "
          "to convert strategic intentions into implemented policy, and under what constitutional, "
          "fiscal and bureaucratic preconditions could Pakistan adapt them to narrow its "
          "implementation deficit?"),
    ("2", "Secondary questions"),
    ("3", "**RQ1 (Direction).** How is China's national planning cycle organised, and which procedural "
          "rules — mandatory preliminary study, public consultation, sub-national plan coordination, "
          "legislative approval, annual reporting and oversight — give it authority over line "
          "agencies?"),
    ("4", "Evidence sought: article-level procedure in the 2026 Law on National Development Plans; the "
          "2018 joint opinion; the 2021 NPC Standing Committee oversight decision; NDRC drafting "
          "practice for the 15th Plan."),
    ("3", "**RQ2 (Delegation).** How does the centre align provincial, municipal and county "
          "incentives with national priorities through responsibility contracts, fiscal instruments "
          "and career linkage?"),
    ("4", "Disaggregate: performance-based promotion; veto-type targets; debt, environment, food and "
          "employment indicators; rotation and cross-jurisdictional transfer."),
    ("4", "Pakistani analogue to test: the link (or absence of a link) between district service-delivery "
          "metrics and the appraisal or posting of district officers."),
    ("3", "**RQ3 (Data).** What information apparatus allows the centre to observe implementation, and "
          "how is its reliability defended against manipulation by the level being measured?"),
    ("4", "Include statistical management, one-stop government services, citizen hotlines, national data "
          "governance, audit and inspection reporting; treat misreporting as a variable, not noise."),
    ("3", "**RQ4 (Discipline).** Through which accountability instruments is non-performance punished, "
          "and what are the observed trade-offs with local initiative and experimentation?"),
    ("3", "**RQ5 (Transferability).** Which mechanisms are transferable into Pakistan's constitutional "
          "order, which are transferable only with adaptation, and which are non-transferable — and by "
          "which legal instrument would each be effected?"),
    ("4", "For each candidate, identify: enabling statute or amendment, fiscal cost, veto players, "
          "distributional consequences and legitimacy argument."),
    ("4", "Apply a legitimacy filter: capacity instruments imported into a federation with strong "
          "provincial veto players must be justified democratically, not only administratively."),
    ("3", "**RQ6 (Learning channel).** How do Pakistani officials, legislators, planners and "
          "researchers actually learn about Chinese governance, and with what fidelity?"),
    ("4", "Sites: academy-to-academy training, study tours, CPEC-embedded technical cooperation, "
          "translated policy literature, consultancy and task-force evidence bases."),

    # ---------------------------------------------------------------- 5
    ("1", "Research Objectives"),
    ("2", "To reconstruct China's governance system at the level of **operating procedure** — how a "
          "strategic decision is conceived, negotiated, ratified, executed, measured and corrected."),
    ("3", "Deliverable: an annotated institutional map, one page per mechanism, published as an "
          "appendix."),
    ("2", "To conceptualise and measure “strategic governance” and “state capacity” comparably across "
          "the two cases."),
    ("3", "Deliverable: a published **Four-Gears Capability Index** — 4 dimensions × 4 indicators, "
          "each scored 0–3 against documented evidence, with a rubric and confidence flags."),
    ("2", "To explain, causally rather than descriptively, which mechanisms produced execution "
          "capability in three policy domains used as probes."),
    ("3", "Domains: industrial and zone-based development policy; poverty reduction and social "
          "protection; digital government and data administration."),
    ("4", "Selection logic: each domain exists in comparable form in both countries, isolating the "
          "implementation variable while holding the policy intent constant."),
    ("2", "To identify the preconditions — legal, fiscal, informational, human-resource — that Pakistan "
          "must satisfy before any mechanism can function."),
    ("2", "To derive a ranked, sequenced and constitutionally admissible transfer agenda, and to state "
          "explicitly what must not be transferred."),
    ("2", "To generalise the framework beyond this dyad so that it can be reused for other "
          "South–South learning pairs."),

    # ---------------------------------------------------------------- 6
    ("1", "Propositions and Hypotheses"),
    ("2", "Overarching proposition"),
    ("3", "Capability equals the **product**, not the sum, of Direction, Delegation, Data and "
          "Discipline: any gear at zero zeroes the system, and strengthening one gear in isolation "
          "produces little or negative returns."),
    ("2", "Testable hypotheses"),
    ("3", "**H1 (planning-as-authority).** Formally codified planning procedures raise the probability "
          "that a strategic priority acquires budgetary and personnel follow-through."),
    ("4", "Falsified if sub-national units meet targets with no exposure to these procedures, or comply "
          "fully with procedure yet fail to deliver."),
    ("3", "**H2 (career linkage).** The strength of the target–appraisal–career linkage is positively "
          "associated with delivery speed in prioritised domains, controlling for fiscal capacity and "
          "human capital."),
    ("3", "**H3 (informational autonomy).** Verification units staffing-independent from the government "
          "being measured (inspection teams, cross-jurisdictional audit, vertically managed statistics) "
          "reduce misreporting and improve central steering."),
    ("3", "**H4 (accountability double bind).** High-intensity discipline raises compliance but "
          "depresses experimentation; China partially offsets this through authorised pilots and "
          "tolerance-for-failure rules, which any accountability import must reproduce."),
    ("3", "**H5 (adaptation condition).** Transfers that arrive as **instruments with preconditions** "
          "outperform transfers that arrive as **organisations**; this explains Pakistan's single-window "
          "and zone outcomes."),
    ("4", "Test: process-trace the SIFC and SEZ programmes against the Chinese development-zone model "
          "on all four gears."),
    ("3", "**H6 (legitimacy filter).** In a federation with provincial veto players, compensation-linked "
          "capacity instruments are more readily adopted than command-linked ones, but deliver less per "
          "unit of authority transferred."),
    ("2", "Analytical posture"),
    ("3", "The thesis tests these propositions; it does not assume China's superiority or Pakistan's "
          "failure, and it reports disconfirming cases from both countries."),

    # ---------------------------------------------------------------- 7
    ("1", "Scope, Case Boundaries and Delimitations"),
    ("2", "Temporal scope"),
    ("3", "Principal window 2012–2026, covering the 2013 and 2024 plenum decisions, the 2019 "
          "governance-capacity decision, the 2023 institutional reform, the 14th and 15th Five-Year "
          "Plans, and Pakistan's 12th and 13th Plans and 2024–2025 amendments."),
    ("3", "Genealogical window 1978–2012 for the origin of mechanisms (fiscal contracting, the 1994 "
          "tax-sharing reform, the SEZ system, township enterprise governance) and 1953–1998 for "
          "Pakistan's planning history."),
    ("2", "Territorial scope"),
    ("3", "China: the national level plus two contrasted provinces — one high-capacity coastal "
          "province (Zhejiang or Jiangsu) and one lower-capacity inland province (Guizhou or Gansu) — "
          "varying fiscal capacity while holding the national frame constant."),
    ("3", "Pakistan: the federal level plus Punjab and Khyber Pakhtunkhwa (the most advanced "
          "local-government and digital-service experiments) with Balochistan as a hard-case contrast."),
    ("4", "Justification: most variation in implementation capacity is **within** states, not between "
          "them; national-level comparison alone would mis-attribute to “culture” what belongs to local "
          "institutional variation."),
    ("2", "Deliberate exclusions"),
    ("3", "No normative ranking of political systems; the study is an institutional-capacity analysis, "
          "not a regime debate."),
    ("3", "No assessment of military, strategic or security institutions except where they affect "
          "civilian coordination."),
    ("3", "No econometric estimate of the growth effect of governance reform; growth is context and "
          "outcome correlate only."),
    ("3", "No project-level financial appraisal of CPEC except where it evidences a governance "
          "mechanism."),
    ("2", "Boundary condition on the term “lesson”"),
    ("3", "A lesson is a **mechanism-plus-precondition pair** expressible as a rule of decision, an "
          "organisational design or an information instrument."),
    ("3", "Claims about civilisational temperament, culture, ideology or “national character” are "
          "excluded by definition, because no instrument follows from them."),

    # ---------------------------------------------------------------- 8
    ("1", "Theoretical and Conceptual Framework"),
    ("2", "Strands drawn upon"),
    ("3", "**Developmental state** (Evans's embedded autonomy; Wade's govern the market; Amsden; "
          "Woo-Cumings): the thesis extends this literature by specifying the **informational** and "
          "**personnel** micro-foundations that it tends to leave implicit."),
    ("3", "**Experimentation under hierarchy and adaptive governance** (Heilmann; Heilmann and Perry): "
          "pilots, dual-track reform, scaling by authorisation — treated as an information-processing "
          "advantage, including its distortions."),
    ("3", "**Fragmented authoritarianism and its revisions** (Lieberthal and Oksenberg; Walder; Oi; Xu "
          "Chenggang on delegation, personalisation and mobilisation structure; Hsing on land): "
          "explains both coordination success and implementation failure."),
    ("3", "**Incentive and cadre-management research** (Li and Zhou on promotion competition; Edin on "
          "cadre control; Maskin, Qian and Xu on M-form information and incentives; Ang on the "
          "co-evolution of capability and incentives and on “directed improvisation”): the causal core "
          "of H2 and H4."),
    ("3", "**State capability and problem-driven iteration in development** (Andrews, Pritchett and "
          "Woolcock; Grindle's “good enough governance” and meta-bureaucracy; Besley and Persson on "
          "fiscal and legal capacity; Mann on infrastructural power): supplies the development-side "
          "guard against copying forms and the isomorphism trap."),
    ("3", "**Authoritarian resilience and legitimacy debates** (Bell; Nathan; Pei, and their critics): "
          "used to separate regime-dependent from capability-dependent mechanisms."),
    ("3", "**Policy transfer and lesson-drawing** (Rose; Dolowitz and Marsh; Phillips and Ochs on "
          "methodological risks in borrowing research): used to structure Chapter 9."),
    ("2", "The thesis's own framework: the Four-Gears model"),
    ("3", "**Gear 1 — Direction.** Who sets the agenda, how it becomes binding, and for how long."),
    ("4", "Indicators: existence of a planning statute; hierarchy and “commanding” relation of plans; "
          "ratifying body; mandatory consultation; term of binding force; ex-ante and ex-post "
          "evaluation duties."),
    ("3", "**Gear 2 — Delegation.** How execution is contracted downward, with what resources and "
          "discretion."),
    ("4", "Indicators: own-source revenue share; predictability and rule-basedness of transfers; number "
          "and weighting of performance targets; pilot-authorisation rules; dispute-resolution forum."),
    ("3", "**Gear 3 — Data.** How the centre learns what is happening."),
    ("4", "Indicators: statistical-body independence and vertical management; digital coverage of "
          "administrative transactions; complaint resolution rates; audit follow-up; frequency of "
          "published performance data; institutional tolerance of bad news."),
    ("3", "**Gear 4 — Discipline.** How performance and probity are enforced and rewarded."),
    ("4", "Indicators: appraisal-to-consequence linkage; tenure and rotation rules; inspection coverage; "
          "case-conversion of accountability bodies; documented protection for good-faith policy "
          "failure."),
    ("3", "**The coupling clause.** The model's distinct claim: capability is conjunctural. This is what "
          "converts a descriptive comparison into an analytical one and justifies a configurational "
          "method."),
    ("4", "Formalised for fuzzy-set analysis: high execution capability = DIR*DEL*DAT*DIS; Pakistan's "
          "outcomes are then tested as “missing gear” versus “weak coupling” explanations."),
    ("2", "A priori positioning (to be tested, not asserted)"),
    ("3", "China: strong Direction and Discipline; Data capable but exposed to manipulation; "
          "Delegation context-dependent; overall capability high in prioritised domains and uneven "
          "elsewhere."),
    ("3", "Pakistan: Direction advisory; Delegation constitutionally protected but fiscally thin at "
          "district and local level; Data improving through digital identity, taxpayer portals and "
          "citizen-service channels; Discipline fragmented and rarely consequential."),
    ("3", "Consequence for design: over-sample **deviant cases** — Chinese localities with weak data, "
          "and Pakistani delivery units with strong coupling — because they discriminate between rival "
          "explanations."),
    ("2", "Working definitions of two contested terms"),
    ("3", "**Strategic governance** is defined narrowly (plan-bound coordination with revision) so that "
          "it is not confused with either “grand strategy” or “long-term planning” in the general "
          "sense."),
    ("3", "**State capacity** is defined as effective capability (what the state does), not "
          "administrative size or legal authority (what the state claims), which is the distinction "
          "Pakistan's reform debate most often collapses."),

    # ---------------------------------------------------------------- 9
    ("1", "Literature Review and Research Gap"),
    ("2", "Strand 1 — China's governance, planning and cadre systems"),
    ("3", "Strength: mechanism-level detail, excellent single-institution studies, growing use of "
          "administrative micro-data."),
    ("3", "Weakness for present purposes: written for readers inside the China field, rarely framed as "
          "**transferable design knowledge**, and seldom translated into instruments usable under a "
          "parliamentary federation's constraints."),
    ("2", "Strand 2 — State capacity and public administration reform"),
    ("3", "Strength: a mature conceptual vocabulary and strong diagnostic norms (problem-driven "
          "iteration, function over form)."),
    ("3", "Weakness: capacity is measured through aggregate or perceptual indicators (tax-to-GDP "
          "ratios, governance indices) that cannot reveal **how** coupling works; little testing of "
          "capability-building in large, federal, lower-middle-income settings."),
    ("2", "Strand 3 — Pakistan's administration and political economy"),
    ("3", "Strength: deep historical work on the generalist cadre, patronage, elite capture, fiscal "
          "federalism and the missing third tier."),
    ("3", "Weakness: predominantly normative; prescriptions default to creating new institutions; "
          "little measurement of the 2024–2026 reform files as they move; almost no systematic "
          "engagement with the functioning of Chinese counterparts."),
    ("2", "Strand 4 — China–Pakistan studies"),
    ("3", "Dominance of CPEC financing, energy, debt-sustainability and security framings; zone studies "
          "describe design and incentives but rarely the administrative capacity needed to operate a "
          "zone."),
    ("2", "Gaps this thesis fills"),
    ("3", "**Gap 1 (conceptual).** No mid-range framework links China's documented mechanisms to "
          "transferability conditions, with a legitimacy filter for federal democracies."),
    ("3", "**Gap 2 (empirical and current).** No Pakistan-facing reconstruction of China's planning "
          "cycle after the 2026 Law on National Development Plans — the single most important and least "
          "exploited institutional development for this comparison."),
    ("3", "**Gap 3 (measurement).** No validated bilateral capability index at sub-national granularity "
          "using a conjunctural rather than additive logic."),
    ("3", "**Gap 4 (learning process).** No empirical account of how Pakistani officials learn about "
          "Chinese governance, or of the accuracy of that learning — the most directly intervenable "
          "finding available."),

    # ---------------------------------------------------------------- 10
    ("1", "Proposed Chapterisation"),
    ("2", "Chapter 1 — Introduction: the capability puzzle and the case for studying machinery"),
    ("3", "Context, problem, questions, significance, definitions, structure. Target 6,000–7,000 "
          "words."),
    ("2", "Chapter 2 — Literature Review and the Research Gap (≈8,000 words)"),
    ("2", "Chapter 3 — Framework: the Four-Gears model and the coupling clause (≈6,000 words)"),
    ("3", "Derivation, definitions, hypotheses H1–H6, and what the model deliberately excludes."),
    ("2", "Chapter 4 — China's Governance System and Decision-Making Architecture (≈9,000 words)"),
    ("3", "Party–state structure; the plenum–Decision–legislation cycle; the State Council and its "
          "components; commissions and leading small groups; the 2023 institutional reform as a case of "
          "self-redesign."),
    ("2", "Chapter 5 — Strategic Governance: the Planning Machine (≈8,000 words)"),
    ("3", "Genealogy of five-year planning; the unified planning hierarchy; the 2026 planning law; "
          "long-range objectives to 2035; macro-policy coordination; a process-traced vignette of the "
          "15th Plan."),
    ("2", "Chapter 6 — State Capacity: Delegation, Incentives, Information, Discipline (≈9,000 words)"),
    ("3", "Fiscal structure and local solvency; target responsibility and cadre appraisal; statistics, "
          "digital government and hotlines; inspection, supervision and anti-corruption; the recorded "
          "dysfunctions of the same instruments."),
    ("2", "Chapter 7 — Pakistan: Architecture and the Implementation Deficit (≈9,000 words)"),
    ("3", "Federal–provincial–local tiers; Article 140-A; NFC arrangements; planning institutions since "
          "1953; cadre structure and the 2025 reform proposals; SIFC and zone administration; "
          "digital-state assets; the discourse of “learning from China” in task-force evidence."),
    ("2", "Chapter 8 — Comparison and Three Policy-Domain Probes (≈9,000 words)"),
    ("3", "Index application and pattern matching across six to eight cases; process tracing of "
          "industrial zones, poverty and social protection, and digital government."),
    ("2", "Chapter 9 — Lessons, Preconditions and Non-Transferables (≈6,000 words)"),
    ("2", "Chapter 10 — Conclusion: theory, policy, limitations and a research programme "
          "(≈3,500 words)"),
    ("2", "Provisional total ≈73,000–76,000 words, with appendices for the index, codebook, interview "
          "protocols, survey instrument and translated document extracts."),

    # ---------------------------------------------------------------- 11
    ("1", "Research Methodology"),
    ("2", "Design and logic of inference"),
    ("3", "Qualitative-dominant mixed methods: theory-guided comparative institutional analysis of a "
          "reference case (China) and a receiving case (Pakistan), with deliberate sub-national "
          "variation."),
    ("3", "Case logic: **most-similar systems** sub-nationally (shared constitutional frame, varying "
          "capacity) and **most-different systems** nationally (varying regime and scale, shared "
          "development problem)."),
    ("3", "Because the framework predicts conjunctural causation, the design combines process tracing "
          "with **fuzzy-set qualitative comparative analysis**, which can represent necessity and "
          "conjunction where additive models cannot."),
    ("3", "Ontology/epistemology: critical-realist, mechanism-oriented explanation; interpretive "
          "treatment of officials' accounts with triangulation against documentary evidence."),
    ("2", "Stages, techniques and instruments"),
    ("3", "**Stage 1 — Document and legal analysis (months 1–12).** Systematic coding of 150–200 "
          "primary documents: Party decisions and communiqués, laws and implementing regulations, "
          "planning outlines, ministry and NDRC implementation texts, white papers; and, for Pakistan, "
          "constitutional provisions, acts, ECNEC/ECC decisions, budget documents, audit reports and "
          "task-force reports."),
    ("4", "Technique: procedural process tracing — each mechanism reconstructed as a sequence of "
          "rules, actors, artefacts and sanctions; evidence graded as hoop, smoking-gun or "
          "straw-in-the-wind for H1, H2 and H5."),
    ("4", "Corpus discipline: authoritative translations used for reading, but every cited article "
          "verified in the original language; a bilingual terminology appendix maintained throughout."),
    ("3", "**Stage 2 — Elite and expert interviews (months 12–26).** 35–45 semi-structured "
          "interviews, purposive then snowball."),
    ("4", "Chinese side: serving and retired planning-commission and Development and Reform Commission "
          "officials, cadre-management researchers, party-school and administration-institute faculty, "
          "legal-drafting participants."),
    ("4", "Pakistani side: Planning Division and Commission officers, Board of Investment and SIFC "
          "Secretariat officials, chief-secretary and commissioner-level officers, district "
          "administrators, academy faculty, and CPEC-embedded technical counterparts."),
    ("4", "Two aligned guides with identical mechanism prompts, so answers map directly onto the four "
          "gears; all interviews transcribed, anonymised and coded."),
    ("3", "**Stage 3 — Practitioner survey (months 18–30).** 300–400 questionnaires to federal, "
          "provincial and district officers in Pakistan measuring target-setting, reporting burden, "
          "appraisal fairness and perceived sanctions."),
    ("4", "Analysis: descriptive statistics and exploratory factor analysis; a target Cronbach's alpha "
          "of at least 0.70; no causal claim made from survey data."),
    ("3", "**Stage 4 — Index construction and cross-case comparison (months 22–34).** Four-Gears "
          "Capability Index (4 dimensions × 4 indicators = 16 indicators), each scored 0–3 against "
          "documented evidence with a published rubric; fsQCA over 8–12 cases with alternative "
          "calibrations for robustness."),
    ("4", "Each index cell carries an evidence note and a High/Medium/Low confidence flag; "
          "non-comparability is reported as a finding, not hidden."),
    ("3", "**Stage 5 — Synthesis and transfer analysis (months 30–42).** Mechanism-based transfer "
          "assessment, an expert validation workshop, and revision of the ranked policy agenda."),
    ("2", "Quantitative support (context, not inference)"),
    ("3", "Descriptive benchmarking using World Bank (Worldwide Governance Indicators; PIMA), IMF "
          "(Article IV and programme reviews; Fiscal Monitor), UNDP capacity assessments, OECD "
          "Government at a Glance, UN e-Government Survey, Pakistan Economic Survey and budget "
          "documents, and Chinese statistical yearbooks — used to situate index scores, never to "
          "stand in for mechanism evidence."),
    ("2", "Analysis software and reliability"),
    ("3", "NVivo or Atlas.ti for coding with a published codebook; double-coding of at least 20 per "
          "cent of material, targeting Cohen's kappa ≥ 0.75; R or Stata for the survey; R (QCA "
          "package) or fsQCA 3.0 for configurational analysis."),
    ("2", "Reflexivity and ethics"),
    ("3", "Positionality statement: the researcher is a Pakistani national studying a close ally; the "
          "thesis guards against advocacy by pre-committing coding rules, requiring adverse-evidence "
          "sections, and inviting a China-studies reviewer to read the China chapters."),
    ("3", "Protection of human subjects: informed consent, anonymisation of serving officials, no "
          "solicitation of classified or non-public internal material, and review-board approval before "
          "any fieldwork."),
    ("3", "Data management: a documented audit trail for every claim and figure, version-controlled "
          "transcripts stored encrypted, and a source log recording date of access for fast-moving "
          "material."),
    ("2", "Limitations acknowledged in advance"),
    ("3", "Access asymmetry and opacity in the Chinese case; social-desirability bias in interviews in "
          "both countries; index subjectivity (mitigated, not removed); translation loss; the "
          "time-bound generalisability of reform descriptions; the impossibility of randomised "
          "counterfactuals."),

    # ---------------------------------------------------------------- 12
    ("1", "Data Sources and Indicator Matrix"),
    ("2", "Primary sources — China"),
    ("3", "Constitution and organic laws; the Law on National Development Plans (2026); plenum "
          "decisions and communiqués of 2013, 2019, 2024 and the October 2025 plenum recommendations; "
          "the 15th Five-Year Plan Outline and the 2035 long-range objectives."),
    ("3", "State Council white papers (including the 2020 poverty-alleviation white paper); NDRC, "
          "Ministry of Finance, science-and-technology and data-administration publications; NPC "
          "Standing Committee oversight decisions and annual work reports."),
    ("3", "Provincial planning and cadre-assessment documents available through public channels; "
          "Chinese-language legal and policy databases (e.g. PKULaw / Beida Fabao) where library "
          "subscription access exists."),
    ("2", "Primary sources — Pakistan"),
    ("3", "Constitution of 1973 (Articles 140-A, 153–154, 160, 25-A and related); the 18th (2010), "
          "26th (2024) and 27th (2025) amendments as gazetted; the NFC award framework; Board of "
          "Investment Act 2017; federal and provincial special-economic-zone laws; the Benazir Income "
          "Support Programme Act 2019; the Right of Access to Information Act 2017; the Civil Servants "
          "Act 1973 and its 2024–2026 amendment proposals."),
    ("3", "Planning Division documents for the 12th and 13th Plans; ECNEC and Economic Coordination "
          "Committee decisions; Public Sector Development Programme data; Economic Survey; Finance "
          "Division budget documents; Auditor General reports; SIFC releases; the 2026 local-governance "
          "task-force report and the 2025 civil-service reform committee record."),
    ("2", "Indicator matrix: the sixteen cells (draft specification)"),
    ("3", "**Direction:** statutory planning procedure; hierarchy of plans; mandatory ex-ante study; "
          "independent ex-post evaluation; consistency of the planning horizon with the electoral "
          "cycle."),
    ("3", "**Delegation:** sub-national own-source revenue; transfer predictability; expenditure "
          "autonomy; number and weighting of binding targets; institutionalised dispute resolution."),
    ("3", "**Data:** statistical independence; digital coverage of service transactions; complaint "
          "resolution performance; audit-finding follow-up rate; publication frequency of delivery "
          "data."),
    ("3", "**Discipline:** appraisal-to-consequence linkage; rotation and tenure rules; inspection "
          "coverage; accountability case conversion; formal protection for good-faith policy failure."),
    ("3", "**Outcome proxies:** project completion timeliness; zone land-transfer and utility-connection "
          "times; tax administration efficiency; learning and primary-health service delivery; "
          "provincial comparables for China."),
    ("2", "Translation and terminology protocol"),
    ("3", "Mandarin proficiency developed during years 1–2 (or a formally engaged bilingual research "
          "assistant), with back-translation of every quoted legal or policy provision."),
    ("3", "Key terms recorded in pinyin with a glossary and the Chinese characters kept in the "
          "appendix only: quan guo ren min da min zhu (whole-process people's democracy), mubiao "
          "zeren zhi (target responsibility system), du cha (verification and inspection), xun shi "
          "(inspection tours), fang guan fu (streamlining, regulation and service reform), quan guo "
          "tong yi da shi chang (national unified market), shi di (pilot points)."),
    ("2", "Note on figures and dates"),
    ("3", "Every quantitative claim in this theme document is a **research lead** current as at "
          "27 August 2026, drawn from official releases and reputable reporting; each must be "
          "re-verified against primary sources before use in the synopsis or thesis."),

    # ---------------------------------------------------------------- 13
    ("1", "Expected Original Contribution"),
    ("2", "Theoretical"),
    ("3", "A mid-range, mechanism-level framework — the Four-Gears model with a coupling clause — that "
          "reconciles developmental-state theory, policy-experimentation research and state-capability "
          "scholarship under a single conjunctural logic."),
    ("3", "A definitional refinement in policy-transfer studies: a “lesson” as a mechanism-plus-"
          "precondition pair, subject to an explicit legitimacy filter when transferring from a "
          "one-party state into a parliamentary federation."),
    ("2", "Empirical"),
    ("3", "The first Pakistan-facing reconstruction of China's planning cycle that incorporates the "
          "2026 planning law and the post-2023 institutional architecture."),
    ("3", "A replicable bilateral capability index with a published rubric and evidence notes — a "
          "research asset others can extend to other country pairs."),
    ("3", "Original interview material from both countries on how targets are set, reported and "
          "sanctioned, a scarce data type for this comparison."),
    ("2", "Methodological"),
    ("3", "A demonstration of combining procedure-level document analysis, process tracing, fsQCA and a "
          "practitioner survey inside comparative public administration, with transparent and "
          "pre-committed coding rules."),
    ("2", "Policy"),
    ("3", "A costed, sequenced, constitutionally mapped reform agenda for Pakistan, addressed to the "
          "Planning, Establishment, Finance and Investment apparatus and to provincial governments, "
          "instead of a list of aspirations."),
    ("2", "Dissemination plan"),
    ("3", "Article 1 — the 2026 planning law and the legalisation of strategic governance (Journal of "
          "Contemporary China; The China Quarterly; The China Journal)."),
    ("3", "Article 2 — the four-gears framework and index applied to two federations (Governance; "
          "Public Administration and Development; Journal of Comparative Policy Analysis)."),
    ("3", "Article 3 — zone governance and single-window reform in Pakistan (The Pakistan Development "
          "Review; World Development; Development Policy and Society)."),
    ("3", "Article 4 — a practitioner-facing policy note for an open-access outlet (PIDE, SDPI, "
          "NUST IASM, LUMS SSI), and one Chinese-language summary for a Chinese academy journal."),

    # ---------------------------------------------------------------- 14
    ("1", "Policy Relevance: Candidate Lessons to Be Tested"),
    ("2", "Structure of every candidate lesson in Chapter 9"),
    ("3", "Mechanism → precondition → Pakistani legal instrument → cost → veto players → risk → "
          "monitoring indicator. A candidate that cannot be expressed in all seven fields is "
          "disqualified from the recommendations."),
    ("2", "Eight candidates currently on the agenda"),
    ("3", "**L1 Statutory planning cycle.** Mechanism: a law fixing the planning calendar, "
          "participation, approval, reporting and oversight duties, as China's 2026 planning law does. "
          "Precondition: cross-party acceptance that planning is an obligation. Instrument: a National "
          "Development Planning Act, with provincial counterparts and an ECNEC coordination gate. Risk: "
          "read as recentralisation."),
    ("4", "Risk-reducing design: bind **procedure and reporting only**, never provincial policy "
          "content; make targets advisory and reporting duties mandatory and public."),
    ("3", "**L2 Mandatory evaluation of every plan and scheme.** Mechanism: obligatory ex-ante study "
          "plus independent ex-post evaluation feeding the next cycle. Precondition: a small, permanent, "
          "competitive-salaried evaluation secretariat. Instrument: an independent Office of Evaluation "
          "with statutory publication rights. Risk: capture by evaluated agencies."),
    ("4", "Mitigations: rotating external panel; published evaluation mandates; automatic sunset for "
          "schemes not evaluated."),
    ("3", "**L3 Coupling targets to personnel.** Mechanism: a small set of weighted, measurable targets "
          "embedded in cadre appraisal with real career consequences. Precondition: reliable "
          "district-level outcome data and protected tenure to limit gaming. Instrument: amendment of "
          "the Civil Servants Act and appraisal rules; a district performance dashboard. Risk: metric "
          "tyranny and formalistic target-chasing — the documented Chinese pathology, hence an "
          "anticipated cost."),
    ("3", "**L4 Codified experimentation with tolerance for failure.** Mechanism: authorised pilots, "
          "fixed duration, mandatory evaluation, then scale or stop, with explicit protection for "
          "officials whose authorised pilot fails. Precondition: a legal power to suspend specified "
          "rules within a named pilot area. Instrument: a Policy Experimentation and Pilot "
          "Authorisation Act. Why it fits Pakistan: it raises capability **without** centralising "
          "authority."),
    ("3", "**L5 Verified information apparatus.** Mechanism: statistical and audit functions staffed "
          "independently of the government measured, plus citizen-reporting channels with enforced "
          "resolution timelines. Precondition: consolidation of existing digital assets (national "
          "identity infrastructure, taxpayer portal, citizen complaint portals, service platforms) into "
          "one performance layer. Instrument: a Public Service Data and Performance Act with "
          "machine-readable publication standards."),
    ("3", "**L6 Zone governance as administrative technology.** Mechanism: a zone authority with a "
          "published list of delegated powers, control of land and utilities, a single accountable chief "
          "executive and revenue-linked incentives. Precondition, for the roughly 44 notified zones: "
          "clean land title, de-stacked federal/provincial permits, and grade-A infrastructure at "
          "plug-and-play cost. Risk: multiplying zone authorities without delivery powers."),
    ("4", "Comparative evidence to be assembled: the delegated-authority lists and fiscal retention "
          "rules of Chinese development-zone management committees, documented article by article."),
    ("3", "**L7 Sub-national fiscal discipline.** Mechanism: hard budget constraints, transparent local "
          "debt control and a revenue-performance link. Precondition: honest treatment of provincial "
          "reluctance to devolve (Article 140-A) and of the disincentives embedded in the NFC formula. "
          "Instrument: NFC and Article 140-A reform plus a sub-national fiscal transparency code."),
    ("3", "**L8 Institutionalised learning machinery.** Mechanism: knowledge transfer treated as a "
          "programme — curriculum co-development with schools of government, secondments, translation of "
          "Chinese laws and implementation guides, joint case-method teaching. Precondition: a named "
          "mandate and budget line. Instrument: an intergovernmental memorandum annexed to CPEC "
          "social-field cooperation, with publication requirements to preserve democratic scrutiny."),
    ("2", "Explicitly non-transferable (the thesis names these rather than eliding them)"),
    ("3", "Single-party disciplinary and ideological apparatus; appointment control through a "
          "nomenklatura logic; surveillance-capable information systems lacking independent judicial "
          "authorisation; suppression of independent reporting as a “data” fix."),
    ("3", "Reason: these are inseparable from regime logic and would fail the legitimacy filter of "
          "Pakistan's constitutional order; the capability functions they perform must be met by "
          "democratically admissible substitutes — courts, legislatures, supreme audit institutions, a "
          "free press, and public scorecards."),
    ("2", "Indicative sequencing (subject to findings, not a substitute for them)"),
    ("3", "Year 1, low-conflict credibility steps: publication standards, evaluation mandates, pilot "
          "authorisation rules."),
    ("3", "Years 2–3: planning-procedure and data legislation; appraisal linkage piloted in two "
          "provinces."),
    ("3", "Years 4–5: fiscal and local-government restructuring, conditional on pilot evidence."),

    # ---------------------------------------------------------------- 15
    ("1", "Feasibility, Work Plan and Milestones"),
    ("2", "Feasibility"),
    ("3", "Documentary: high. The Chinese planning and reform corpus and Pakistan's constitutional, "
          "budgetary and task-force documents are public, and the index requires no confidential "
          "material."),
    ("3", "Fieldwork: medium. Chinese access depends on institutional affiliation and language; the "
          "design is deliberately built so that the documentary base alone can support a defensible "
          "thesis if access is curtailed."),
    ("3", "Supervisory fit: secure a primary supervisor in comparative politics or Chinese "
          "political economy and a second reader in Pakistani public administration, or co-supervision "
          "with a China-studies centre; begin language study before synopsis defence."),
    ("3", "Cost: two field trips (10–14 weeks in China; one multi-city Pakistan round), transcription "
          "and translation, survey administration, software, and one research assistant for twelve "
          "months — an order of magnitude to be confirmed against current university rates."),
    ("3", "Funding routes: HEC indigenous PhD scholarship, university assistantships, CSC-type "
          "scholarships for the China fieldwork period, and small-grant schemes for comparative "
          "research."),
    ("2", "Forty-two-month timeline"),
    ("3", "Months 1–6: coursework; refinement of framework; systematic review protocol; codebook v1; "
          "ethics application; language study."),
    ("3", "Months 6–12: corpus assembly and coding; draft Chapter 4; index specification v1."),
    ("3", "Months 12–18: interview guide piloted in Pakistan; first fieldwork; conference paper; "
          "journal article 1 submitted."),
    ("3", "Months 18–26: China fieldwork; survey fielded and analysed; Chapters 5 and 6 drafted."),
    ("3", "Months 26–34: index scoring; fsQCA; Chapters 7 and 8."),
    ("3", "Months 34–38: Chapter 9 transfer agenda; expert validation workshop; articles 2 and 3 "
          "submitted."),
    ("3", "Months 38–42: integration, editing, pre-submission checks, viva preparation."),
    ("2", "Milestones, each with a named artefact and audience"),
    ("3", "M1 synopsis approved (this document revised per committee comments)."),
    ("3", "M2 comprehensive literature review chapter (departmental seminar)."),
    ("3", "M3 instruments approved by the review board (ethics file, codebook, index rubric)."),
    ("3", "M4 two analytical chapters plus progress report (annual review)."),
    ("3", "M5 all empirical chapters drafted (pre-submission committee)."),
    ("3", "M6 complete thesis submitted, with two journal articles accepted or under review."),
    ("2", "Monitoring"),
    ("3", "Monthly supervisor meeting with a written work log; quarterly milestone self-audit; annual "
          "revision of the risk register and of the source list."),

    # ---------------------------------------------------------------- 16
    ("1", "Risk Register and Mitigation"),
    ("2", "Access and data risks"),
    ("3", "Restricted access in China → university sponsorship; retired officials and academics as "
          "primary interviewees; a document-sufficient design."),
    ("3", "Reluctance or guarded responses in Pakistan → institutional sponsorship, anonymised "
          "protocols, third-party survey administration, and no requests for non-public documents."),
    ("3", "Rapidly changing legal landscape → a living chronology, access-date stamps on every source, "
          "and an “as at” statement opening each chapter."),
    ("3", "Paywalled or non-digitised sources → early library access requests, interlibrary loan, and "
          "use of open-access government gazettes."),
    ("2", "Analytical and reputational risks"),
    ("3", "Advocacy drift, i.e. the thesis reading as a defence of either country → mandatory "
          "adverse-evidence sections, regime-neutral framing in the introduction, and external reading "
          "by scholars from both traditions."),
    ("3", "Romanticising the model → mechanisms described together with their recorded dysfunctions: "
          "misreporting, formalism, local debt stress, innovation-suppressing accountability, and the "
          "demographic and property-sector constraints of the 2020s."),
    ("3", "Index subjectivity → published rubric, double scoring, external adjudication of divergences, "
          "and sensitivity analysis across calibrations."),
    ("3", "Citation integrity, including AI-assisted drafting errors → no citation enters the text "
          "without a located primary source; a source log for every number; institutional "
          "similarity-check standards met."),
    ("2", "Personal and administrative risks"),
    ("3", "Language-learning load, funding slippage, family and health disruption → two alternate "
          "fieldwork windows per year, a rolling twelve-month budget review, and early application for "
          "external funding."),
    ("2", "Contingency: a fallback version of the thesis"),
    ("3", "If fieldwork becomes impossible, the design collapses to a two-country documentary and "
          "index study with a Pakistani-only interview sample, retaining Chapters 4, 5, 7, 8 and 9 with "
          "revised titles and a stated limitation."),

    # ---------------------------------------------------------------- 17
    ("1", "Synopsis-Submission Checklist and Supporting Elements"),
    ("2", "Elements required by most Pakistani doctoral regulations, mapped to this document"),
    ("3", "Title and abstract; introduction and background; problem statement; research questions; "
          "objectives; hypotheses; literature review; theoretical framework; scope and limitations; "
          "research methodology; chapterisation; work plan and timeline; references; appendices."),
    ("3", "Cross-check each departmental requirement against this document at the synopsis stage and "
          "revise; where the university thesis manual mandates a different font or size for the final "
          "submission (commonly 12 pt), apply the manual to the thesis and keep 14 pt only for the "
          "synopsis and review drafts."),
    ("2", "Suggested abstract (about 210 words; refine for the synopsis)"),
    ("3", "Pakistan has not lacked development strategies; it has lacked the machinery that converts "
          "strategy into delivery. This thesis explains China's execution capability not as a product of "
          "authoritarianism, scale or capital, but as an assembled technology of strategic governance "
          "comprising four coupled mechanisms: Direction, an enforceable planning hierarchy now codified "
          "in the 2026 Law on National Development Plans; Delegation, target-linked resources and "
          "authority for lower tiers; Data, verification capacity insulated from the government being "
          "measured; and Discipline, performance-linked consequences in personnel decisions. Using "
          "comparative institutional analysis of three policy domains — industrial zones, poverty "
          "reduction and social protection, and digital government — and combining legal and document "
          "analysis, elite interviews, a practitioner survey and fuzzy-set qualitative comparative "
          "analysis, the thesis derives a ranked transfer agenda for Pakistan, specifies the "
          "precondition each transfer requires, and identifies the elements that cannot be transferred "
          "into a parliamentary federation."),
    ("2", "Suggested keywords"),
    ("3", "Strategic governance; state capacity; Chinese governance system; five-year planning; policy "
          "transfer; lesson-drawing; cadre management; administrative reform; CPEC Phase II; "
          "comparative public administration."),
    ("2", "Preliminary appendices to be prepared"),
    ("3", "A1 institutional map of China's decision-making cycle; A2 index rubric and scoring sheet; "
          "A3 interview guides (China and Pakistan versions); A4 survey instrument; A5 document corpus "
          "list with access dates; A6 glossary and translation table; A7 fieldwork ethics and consent "
          "forms."),

    # ---------------------------------------------------------------- 18
    ("1", "Indicative Core Bibliography (verify and extend)"),
    ("2", "State capacity, development management and the developmental state"),
    ("3", "Andrews, M., Pritchett, L., & Woolcock, M. (2017). *Building State Capability: Evidence, "
          "Analysis, Action.* Oxford University Press."),
    ("3", "Besley, T., & Persson, T. (2011). *Pillars of Prosperity: The Political Economics of "
          "Development Clusters.* Princeton University Press."),
    ("3", "Evans, P. B. (1995). *Embedded Autonomy: States and Industrial Transformation.* Cambridge "
          "University Press."),
    ("3", "Fukuyama, F. (2004). *State-Building: Governance and a New World Order.* Yale University "
          "Press."),
    ("3", "Grindle, M. S. (2011). Good enough governance revisited. *Development Policy Review, 29*(5), "
          "607–623."),
    ("3", "Mann, M. (1984). The autonomous power of the state: Its origins and mechanisms. *Archives "
          "Européennes de Sociologie, 25*(2), 185–213."),
    ("3", "Moore, M. (2004). Death and taxes: A threatening relationship. *Third World Quarterly, "
          "25*(5)."),
    ("3", "Woo-Cumings, M. (Ed.). (1999). *The Developmental State.* Cornell University Press."),
    ("2", "China's governance, decision-making, planning and cadre systems"),
    ("3", "Ang, Y. Y. (2016). *How China Escaped the Poverty Trap.* Cornell University Press."),
    ("3", "Ang, Y. Y. (2020). *China's Gilded Age: The Paradox of Economic Boom and Vast Corruption.* "
          "Cambridge University Press."),
    ("3", "Bell, D. A. (2015). *The China Model: Political Meritocracy and the Limits of Democracy.* "
          "Princeton University Press."),
    ("3", "Edin, M. (2003). State capacity and local agent control in China: CCP cadre management from a "
          "township perspective. *The China Quarterly, 173*, 35–52."),
    ("3", "Heilmann, S. (2008). Policy experimentation in China's economic rise. *Studies in Comparative "
          "International Development, 43*(1), 1–26."),
    ("3", "Heilmann, S., & Perry, E. J. (Eds.). (2011). *Mao's Invisible Hand: The Political "
          "Foundations of Adaptive Governance in China.* Harvard University Asia Center."),
    ("3", "Hsing, Y.-T. (2010). *The Great Urban Transformation: Politics of Land and Property in "
          "China.* Oxford University Press."),
    ("3", "Kennedy, S. (2005). Win, lose or draw: Assessing the changing role of policy in China. *The "
          "China Quarterly, 183*, 655–674."),
    ("3", "Lieberthal, K., & Oksenberg, M. (1988). *Policy Making in China: Leaders, Structures, and "
          "Processes.* Princeton University Press."),
    ("3", "Li, H., & Zhou, L.-A. (2005). Political turnover and economic performance: The incentive role "
          "of local leaders in China's economic transition. *Journal of Public Economics, 89*(9–10), "
          "1743–1762."),
    ("3", "Maskin, E., Qian, Y., & Xu, C. (2000). Incentives, information, and organizational form. "
          "*Review of Economic Studies, 67*(2), 359–378."),
    ("3", "Naughton, B. (2007). *The Chinese Economy: Transitions and Growth.* MIT Press."),
    ("3", "Nathan, A. J. (2003). Authoritarian resilience. *Journal of Democracy, 14*(1), 6–17."),
    ("3", "Oi, J. C. (1999). *Rural China Takes Off: Institutional Foundations of Economic Reform.* "
          "University of California Press."),
    ("3", "O'Brien, K. J., & Li, L. (1999). Selective policy implementation in rural China. *Comparative "
          "Politics, 31*(2), 167–186."),
    ("3", "Pei, M. (2006). *China's Trapped Transition: The Limits of Developmental Autocracy.* Harvard "
          "University Press."),
    ("3", "Walder, A. G. (1995). Local governments as industrial firms: An organizational analysis of "
          "China's transitional economy. *American Journal of Sociology, 101*(2), 263–301."),
    ("3", "Xu, C. (2011). The fundamental institutions of China's reforms and development. *Journal of "
          "Economic Literature, 49*(3), 641–689."),
    ("2", "Policy transfer, comparison and methods"),
    ("3", "Bennett, A., & Checkel, J. T. (Eds.). (2015). *Process Tracing: From Metaphor to Analytic "
          "Tool.* Cambridge University Press."),
    ("3", "Dolowitz, D. P., & Marsh, D. (2000). Learning from abroad: The role of policy transfer in "
          "contemporary policy-making. *Governance, 13*(1), 5–23."),
    ("3", "Phillips, D., & Ochs, K. (2004). Researching policy borrowing: Methodological challenges in "
          "comparative education. *Oxford Review of Education, 30*(1), 77–90."),
    ("3", "Ragin, C. C. (2008). *Redesigning Social Inquiry: Fuzzy Sets and Beyond.* University of "
          "Chicago Press."),
    ("3", "Rose, R. (1991). What is lesson-drawing? *Journal of Public Policy, 11*(1), 3–30."),
    ("2", "Pakistan: governance, administration and political economy"),
    ("3", "Cohen, S. P. (2004). *The Idea of Pakistan.* Brookings Institution Press."),
    ("3", "Lieven, A. (2012). *Pakistan: A Hard Country.* PublicAffairs."),
    ("3", "Stern, A. B., & Zia, H. J. (2017). Aid effectiveness and local institutional coordination: A "
          "review. *World Development, 99*, 304–319."),
    ("3", "World Bank. (2004). *Making Services Work for Poor People* (World Development Report 2004). "
          "Oxford University Press."),
    ("2", "Primary and official documents (core corpus)"),
    ("3", "Decision of the Central Committee of the Communist Party of China on Further Deepening "
          "Reform Comprehensively to Advance Chinese Modernization (Third Plenum of the 20th Central "
          "Committee, adopted 18 July 2024; published 21 July 2024)."),
    ("3", "Decision on Some Major Issues Concerning Comprehensively Deepening the Reform (Third Plenum "
          "of the 18th Central Committee, 12 November 2013); Decision on Upholding and Improving the "
          "System of Socialism with Chinese Characteristics and Advancing the Modernization of China's "
          "System and Capacity for Governance (Fourth Plenum of the 19th Central Committee, 31 October "
          "2019)."),
    ("3", "Law of the People's Republic of China on National Development Plans (adopted March 2026); "
          "Outline of the 15th Five-Year Plan for National Economic and Social Development and the "
          "Outline of Long-Range Objectives to 2035 (approved March 2026)."),
    ("3", "Constitution of the Islamic Republic of Pakistan, 1973, as amended; Benazir Income Support "
          "Programme Act 2019; Board of Investment Act 2017; federal and provincial Special Economic "
          "Zones Acts; Civil Servants Act 1973; Right of Access to Information Act 2017."),
    ("3", "IMF Pakistan Article IV consultation and Extended Fund Facility staff reports (2023–2026); "
          "Pakistan Economic Survey (2022–23 to 2025–26); Planning Division 12th and 13th Five-Year Plan "
          "documents; Auditor General of Pakistan reports; Task Force on Reforms in Local Governance "
          "report (2026)."),
    ("3", "Final note: this bibliography is an indicative core. Each entry, page range and document "
          "date must be confirmed against the publisher or official gazette before submission; nothing "
          "in this theme statement should be reproduced as a finished citation."),
]


def build(out_path: Path):
    doc = Document()

    # ---- global fonts -------------------------------------------------- #
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = SIZE
    normal.font.color.rgb = BLACK
    style_font(normal)

    styles_el = doc.styles.element
    doc_defaults = styles_el.find(qn("w:docDefaults"))
    if doc_defaults is None:
        doc_defaults = OxmlElement("w:docDefaults")
        styles_el.insert(0, doc_defaults)
    rpr_default = doc_defaults.find(qn("w:rPrDefault"))
    if rpr_default is None:
        rpr_default = sub(doc_defaults, "w:rPrDefault")
    rpr = rpr_default.find(qn("w:rPr"))
    if rpr is None:
        rpr = sub(rpr_default, "w:rPr")
    clear(rpr, "w:rFonts", "w:sz", "w:szCs", "w:color")
    rf = ensure(rpr, "w:rFonts", RPR_ORDER)
    for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
        rf.set(qn("w:" + attr), FONT)
    sub(rpr, "w:sz", order=RPR_ORDER, val="28")
    sub(rpr, "w:szCs", order=RPR_ORDER, val="28")
    sub(rpr, "w:color", order=RPR_ORDER, val="000000")

    touched = ["Title", "Subtitle", "Heading 1", "Heading 2", "Heading 3", "Heading 4",
               "Heading 5", "Heading 6", "Heading 7", "Heading 8", "Heading 9", "List Paragraph",
               "List Bullet", "List Number", "Quote", "Intense Quote", "Caption", "Table Caption",
               "Header", "Footer", "No List"]
    names = {s.name for s in doc.styles}
    for name in touched:
        if name in names:
            style_font(doc.styles[name], bold=name.startswith("Heading") or name in ("Title",))

    # ---- page setup ---------------------------------------------------- #
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin, sec.bottom_margin = Cm(2.5), Cm(2.5)
    sec.left_margin, sec.right_margin = Cm(2.8), Cm(2.2)
    add_footer_page_number(doc)

    # ---- numbering ----------------------------------------------------- #
    add_numbering_definition(doc)
    make_list_styles(doc)

    # ---- title block --------------------------------------------------- #
    for kind, text in HEAD:
        if kind == "T":
            add_para(doc, text, align=WD_ALIGN_PARAGRAPH.CENTER, after=6, bold=True, spacing=1.15)
        else:
            add_para(doc, text, align=WD_ALIGN_PARAGRAPH.CENTER, after=5, spacing=1.15)
    rule(doc)

    meta_table = doc.add_table(rows=0, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for label, value in META:
        row = meta_table.add_row()
        set_cell(row.cells[0], label, bold=True)
        set_cell(row.cells[1], value)
        row.cells[0].width = Cm(6.0)
        row.cells[1].width = Cm(9.5)
    boxed(meta_table)
    add_para(doc, "", after=4)
    note = ("**How to use this document:** it is a theme statement, not the synopsis itself. Fill the "
            "bracketed and blank fields, keep the four-level numbering (1. / a. / (1) / (a)) and the "
            "Arial 14 pt formatting if your department requires this style at the synopsis stage, delete "
            "any element your regulations do not ask for, and treat every date, figure and legal "
            "reference as a lead to be verified against primary sources. The final thesis will normally "
            "follow the university's own template (commonly 12 pt), so keep this file as the working "
            "outline and generate the formatted version from it.")
    add_para(doc, note, align=WD_ALIGN_PARAGRAPH.JUSTIFY, before=0, after=4)
    rule(doc, after=8)

    # ---- body ---------------------------------------------------------- #
    style_map = {"1": "ThesisList1", "2": "ThesisList2", "3": "ThesisList3", "4": "ThesisList4"}
    for kind, payload in BODY:
        if kind == "BREAK":
            doc.add_page_break()
            continue
        add_para(doc, payload, style=style_map.get(kind))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))
    return out_path


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    target = here / "PhD-Thesis-Theme_Chinese-Governance-State-Capacity-and-Lessons-for-Pakistan.docx"
    print("written:", build(target))
