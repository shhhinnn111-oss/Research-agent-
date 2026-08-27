# PhD Thesis Theme — China Governance / State Capacity / Lessons for Pakistan

Working files for the doctoral thesis theme on **Chinese governance system, decision-making, state
capacity, strategic governance and lessons for Pakistan**.

| File | What it is |
| --- | --- |
| `PhD-Thesis-Theme_Chinese-Governance-State-Capacity-and-Lessons-for-Pakistan.docx` | The deliverable: theme statement / pre-synopsis framework, 19 numbered sections, ~8,100 words. |
| `build_thesis_theme_docx.py` | Generator script (python-docx). Editing the content lists `HEAD`, `META`, `BODY` and re-running regenerates the DOCX, so formatting stays consistent. |
| `verify_docx_format.py` | Formats-and-numbering checker (see below). |

## Formatting contract

* Every character — body text, headings, the metadata table and the footer — is **Arial, 14 pt, black**.
* All list content is a single real Word multilevel list with exactly four levels, auto-numbered:

  ```text
  1.     decimal        "1."
    a.   lower letter   "a."
      (1)  decimal in parentheses
        (a)  lower letter in parentheses
  ```

  Sub-level counters restart automatically under each parent, so inserting or deleting a bullet
  renumbers the document without manual editing.

## Rebuild and check

```bash
python -m venv .venv && .venv/bin/pip install python-docx      # one time
.venv/bin/python thesis/build_thesis_theme_docx.py             # regenerate the DOCX
.venv/bin/python thesis/verify_docx_format.py                  # assert Arial 14 black + 1./a./(1)/(a)
```

`verify_docx_format.py` also replays Word's numbering algorithm over the raw XML, so the labels it
prints are what Word will display. An independent round-trip (`pandoc file.docx -t markdown`)
reproduces the same four-level list structure.

## Note on sources

Facts and dates in the theme statement (China's 15th Five-Year Plan and the 2026 Law on National
Development Plans; the 2013/2019/2024 plenum decisions; Pakistan's 18th, 26th and 27th constitutional
amendments, Article 140-A, the SIFC, SEZ counts, IMF programme structure; the bibliography) are
**research leads compiled on 27 August 2026**, not verified citations. Confirm each against the
official gazette, Xinhua/NPC/NDRC releases and IMF publications before submitting a synopsis, and
replace the indicative bibliography with sources actually read.
