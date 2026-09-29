#!/usr/bin/env python3
"""Mine every erratum from 19 Intel and AMD processor errata documents.

Study: data/studies/01-silicon-errata-archaeology/

Stages (all run by default):

1. fetch    Download each document listed in families.csv into the study's
            .cache/pdf/ directory (git-ignored; vendor PDFs are not
            redistributed). Record URL, document number, revision, date,
            page count and SHA-256 in sources.csv.
2. extract  Convert each PDF to text with poppler's pdftotext (layout mode for
            the summary tables, reading-order mode for AMD entries) and
            PyMuPDF (font-aware spans, for Intel entries), and extract every
            erratum: id, title, and fix status. Description text goes to
            .cache/errata_text.jsonl for classification and audit; it is
            not committed.
3. check    Per document, compare the ids found in the detailed errata
            section with the ids in the document's own summary table
            (Intel "Summary Tables of Changes", AMD "Cross-Reference of
            Processor Revision to Errata"). Removed errata must be marked
            removed in both places, Intel numbering must have no unexplained
            gap, and each detailed title must contain the title fragment the
            summary table prints on the same row. Any difference, any missing
            or truncated title, or any missing status raises and stops the run.

Usage:
    python3 data/scrapers/mine_cpu_errata.py            # fetch + extract + check
    python3 data/scrapers/mine_cpu_errata.py --offline  # reuse cached PDFs
    python3 data/scrapers/mine_cpu_errata.py --verify-hashes
        # refuse to proceed if a cached PDF's SHA-256 differs from sources.csv

Requires poppler (pdftotext, pdfinfo) and curl on PATH, and PyMuPDF (pip install
pymupdf==1.27.2.2), which reads font weight to find Intel erratum headings.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "data" / "studies" / "01-silicon-errata-archaeology"
CACHE = STUDY / ".cache"
FAMILIES = STUDY / "families.csv"
SOURCES = STUDY / "sources.csv"
ERRATA = STUDY / "errata.csv"
TEXT = CACHE / "errata_text.jsonl"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

INTEL_LABELS = ["Problem", "Implication", "Workaround", "Status"]
AMD_LABELS = [
    "Description",
    "Potential Effect on System",
    "Suggested Workaround",
    "Fix Planned",
]

# Page furniture that pdftotext interleaves with erratum text.
BOILERPLATE = re.compile(
    r"(Specification Update|Revision Guide for AMD|Errata Details|^\[Public\]$|"
    r"^\d{1,3}$|^Publication|Revision:\s*\d|^(January|February|March|April|May|June|"
    r"July|August|September|October|November|December)\s+\d{4}$|Doc\. No\.|"
    r"Document Number|Reference Number|Order Number|^Product Errata$|^§+$|"
    r"Intel Confidential|^\d{5}\s+Rev|^Send Feedback$)",
    re.I,
)


class CompletenessError(RuntimeError):
    pass


def key_of(family: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", family)


def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url: str, dest: Path) -> None:
    """Download with curl when present (it uses the system trust store), else urllib."""
    if shutil.which("curl"):
        subprocess.run(
            ["curl", "-sSL", "--fail", "--retry", "3", "-A", UA, "-o", str(dest), url],
            check=True,
        )
        data = dest.read_bytes()
    else:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
        dest.write_bytes(data)
    if not data.startswith(b"%PDF"):
        raise RuntimeError(f"{url} did not return a PDF")


def norm(s: str) -> str:
    s = s.replace("®", "").replace("™", "").replace(" ", " ")
    s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace("ﬁ", "fi")
    s = re.sub(r"(?<=\w)\*", "", s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------------------
# Document identity (number, revision, date) read from the document itself.
# ---------------------------------------------------------------------------


def identity(vendor: str, layout: str) -> dict[str, str]:
    head = layout[:6000]
    months = (
        r"(January|February|March|April|May|June|July|August|September|October|"
        r"November|December)\s+(\d{4})"
    )
    date = re.search(months, head)
    out = {"date": f"{date.group(1)} {date.group(2)}" if date else ""}
    if vendor == "AMD":
        m = re.search(r"Publication\s*(?:#|Number:)\s*(\d{5})", head)
        r = re.search(r"Revision:\s*([\d.]+)", head)
        out["doc_number"] = m.group(1) if m else ""
        out["revision"] = r.group(1) if r else ""
        d = re.search(r"(?:Issue )?Date:\s*" + months, head)
        if d:
            out["date"] = f"{d.group(1)} {d.group(2)}"
    else:
        m = re.search(
            r"(?:Reference Number|Order Number|Document Number):\s*(\d{6})(?:-(\d{3})(US)?)?",
            head,
        )
        m2 = re.search(r"Doc\. No\.:\s*(\d{6}),\s*Rev\.:\s*(\d{3}US)", head)
        rv = re.search(r"Revision\s+(\d{3})\b", head)
        if m2:
            out["doc_number"], out["revision"] = m2.group(1), m2.group(2)
        elif m:
            out["doc_number"] = m.group(1)
            out["revision"] = (m.group(2) or (rv.group(1) if rv else "")) + (
                m.group(3) or ""
            )
        else:
            bare = re.search(r"^\s*(\d{6})-(\d{3}(?:US)?)\s*$", head, re.M)
            out["doc_number"], out["revision"] = (
                (bare.group(1), bare.group(2)) if bare else ("", "")
            )
    if not all(out.get(k) for k in ("doc_number", "revision", "date")):
        raise CompletenessError(
            f"could not read document identity from the title page: {out}"
        )
    return out


# ---------------------------------------------------------------------------
# Detailed errata sections (reading-order text).
# ---------------------------------------------------------------------------


def split_fields(lines: list[str], labels: list[str]) -> dict[str, str]:
    pat = re.compile(r"^(" + "|".join(re.escape(l) for l in labels) + r")\s*:?\s*(.*)$")
    fields: dict[str, list[str]] = {l: [] for l in labels}
    cur = None
    for ln in lines:
        s = ln.strip()
        if not s or BOILERPLATE.search(s):
            continue
        m = pat.match(s)
        if m:
            cur = m.group(1)
            if m.group(2):
                fields[cur].append(m.group(2))
            continue
        if cur:
            fields[cur].append(s)
    return {k: norm(" ".join(v)) for k, v in fields.items()}


LABEL = re.compile(r"^(Problem|Implication|Workaround|Status)\s*:?\s*(.*)$", re.S)
REMOVED = re.compile(
    r"(\bRemoved\b|has been removed|ID updated to|Moved to|Replaced by|Duplicate of)",
    re.I,
)


def spans_of(pdf: Path) -> list[dict]:
    """Every text span in reading order, with bold flag, via PyMuPDF."""
    import fitz  # PyMuPDF

    out = []
    with fitz.open(pdf) as doc:
        for pno, page in enumerate(doc):
            for b in page.get_text("dict")["blocks"]:
                for line in b.get("lines", []):
                    for s in line["spans"]:
                        t = s["text"].strip()
                        if not t:
                            continue
                        bold = bool(s["flags"] & 16) or "bold" in s["font"].lower()
                        out.append({"t": t, "bold": bold, "page": pno})
    return out


def detail_intel(pdf: Path, prefix: str) -> tuple[dict[str, dict], set[str]]:
    """Detailed Intel entries: a bold id span, bold title spans, then Problem."""
    spans = spans_of(pdf)
    idre = re.compile(rf"^({prefix})\s?(\d+)(?![0-9A-Za-z])\s*\.?\s*(.*)$")
    heads: list[tuple[int, str, str]] = []  # (span index where body starts, id, title)
    removed: set[str] = set()
    i = 0
    while i < len(spans):
        s = spans[i]
        m = idre.match(s["t"]) if s["bold"] else None
        if not m:
            i += 1
            continue
        eid = m.group(1) + m.group(2)
        title = [m.group(3)] if m.group(3) else []
        j = i + 1
        kind = None
        while j < len(spans) and j < i + 40:
            t = spans[j]["t"]
            if LABEL.match(t):
                kind = LABEL.match(t).group(1)
                nxt = spans[j + 1]["t"] if j + 1 < len(spans) else ""
                # A title can end in a label word ("... Hardware Status");
                # it is title text when the Problem label follows directly.
                if (
                    kind != "Problem"
                    and spans[j]["bold"]
                    and re.match(r"^Problem\b", nxt)
                ):
                    title.append(t)
                    j += 1
                    continue
                break
            if REMOVED.search(t) and not title:
                kind = "removed"
                break
            if idre.match(t):
                break
            if not spans[j]["bold"]:
                # A symbol or a glyph set in another font (for example a
                # non-breaking hyphen) can interrupt a bold title; keep going
                # only when the title resumes in bold on the next span.
                nxt = spans[j + 1] if j + 1 < len(spans) else None
                if len(t) <= 2:
                    j += 1
                    continue
                if not (nxt and nxt["bold"] and not LABEL.match(nxt["t"])):
                    break
            if not BOILERPLATE.search(t):
                title.append(t)
            j += 1
        tt = norm(" ".join(title))
        if kind == "Problem":
            heads.append((j, eid, tt))
        elif kind == "removed" or REMOVED.search(tt):
            removed.add(eid)
        i = j if j > i else i + 1

    out: dict[str, dict] = {}
    for n, (j, eid, title) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(spans)
        fields: dict[str, list[str]] = {k: [] for k in INTEL_LABELS}
        cur = None
        for s in spans[j:end]:
            t = s["t"]
            m = LABEL.match(t)
            if m:
                cur = m.group(1)
                if m.group(2):
                    fields[cur].append(m.group(2))
                continue
            if cur and not BOILERPLATE.search(t) and not idre.match(t):
                fields[cur].append(t)
        if eid in out:
            raise CompletenessError(f"{eid}: detailed section appears twice")
        out[eid] = {
            "title": title,
            "description": norm(" ".join(fields["Problem"])).lstrip(": "),
            "implication": norm(" ".join(fields["Implication"])).lstrip(": "),
            "workaround": norm(" ".join(fields["Workaround"])).lstrip(": "),
        }
    return out, removed


def detail_amd(raw: str) -> dict[str, dict]:
    lines = raw.splitlines()
    head = re.compile(r"^(\d{3,4})\s+(\S.*)$")
    starts: list[tuple[int, str, str]] = []
    for i, ln in enumerate(lines):
        m = head.match(ln.strip())
        if not m:
            continue
        title_parts = [m.group(2)]
        ok = False
        for j in range(i + 1, min(i + 12, len(lines))):
            s = lines[j].strip()
            if not s:
                continue
            if s == "Description":
                ok = True
                break
            if head.match(s):  # running header repeats the heading; keep the later one
                break
            title_parts.append(s)
        if ok:
            t = norm(" ".join(title_parts))
            # A running header that repeats "<id> <title>" can merge into the
            # heading; keep the text after the last repetition of the id.
            t = [x for x in re.split(rf"\b{m.group(1)}\b", t) if x.strip()][-1].strip()
            starts.append((i, m.group(1), t))
    out: dict[str, dict] = {}
    for n, (i, eid, title) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        block = lines[i + 1 : end]
        # Drop a trailing running header that repeats the next erratum's heading.
        f = split_fields(block, AMD_LABELS)
        if eid in out:
            raise CompletenessError(f"{eid}: detailed section appears twice")
        out[eid] = {
            "title": title,
            "description": f["Description"],
            "implication": f["Potential Effect on System"],
            "workaround": f["Suggested Workaround"],
            # The field is one short phrase; anything after it is page furniture.
            "fix_planned": (
                re.match(r"^(No fix planned|Yes|No)\b", f["Fix Planned"], re.I) or [""]
            )[0],
        }
    return out


# ---------------------------------------------------------------------------
# Summary tables (layout text).
# ---------------------------------------------------------------------------

STATUS = re.compile(r"\b(No\s+Fix|Plan(?:ned)?\s+Fix|Fixed|Doc)\b")


def summary_intel(layout: str, prefix: str) -> tuple[dict[str, str], set[str]]:
    """Ids, fix status, and removal markers from the Summary Tables of Changes.

    A row may carry one status per stepping. The row status is the least
    resolved one: No Fix, else Plan Fix, else Fixed, else Doc.
    """
    lines = layout.splitlines()
    idl = re.compile(rf"^\s*({prefix})\s?(\d+)(?![0-9A-Za-z])\s*\.?")
    # The summary region ends at the first id line that heads a detail entry.
    end = len(lines)
    for i, ln in enumerate(lines):
        if idl.match(ln) and not STATUS.search(ln) and not REMOVED.search(ln):
            window = " ".join(lines[i : i + 8])
            if re.search(r"\bProblem\b", window):
                end = i
                break
    rank = ["No Fix", "Plan Fix", "Fixed", "Doc"]
    out: dict[str, str] = {}
    removed: set[str] = set()
    for i in range(end):
        m = idl.match(lines[i])
        if not m:
            continue
        eid = m.group(1) + m.group(2)
        row = [lines[i]]
        if not STATUS.search(lines[i]) and not REMOVED.search(lines[i]):
            # Status sits on a wrapped line next to the id; search neighbours
            # that carry no other id.
            for j in (i - 1, i + 1, i - 2, i + 2):
                if (
                    0 <= j < end
                    and not idl.match(lines[j])
                    and (STATUS.search(lines[j]) or REMOVED.search(lines[j]))
                ):
                    row = [lines[j]]
                    break
        text = " ".join(row)
        if REMOVED.search(text):
            removed.add(eid)
            continue
        found = {
            re.sub(r"\s+", " ", x).replace("Planned", "Plan")
            for x in STATUS.findall(text)
        }
        status = next((r for r in rank if r in found), "")
        out[eid] = out.get(eid) or status
    return out, removed


def summary_amd(layout: str) -> set[str]:
    lines = layout.splitlines()
    ids: set[str] = set()
    inside = False
    for ln in lines:
        s = ln.strip()
        if re.match(
            r"^Table\s+\d+[.:]\s+Cross-Reference of Processor Revision to Errata", s
        ):
            inside = True
            continue
        if re.match(r"^Table\s+\d+[.:]\s+Cross-Reference of Errata to Package", s):
            inside = False
            continue
        if inside:
            m = re.match(r"^\s{0,8}(\d{3,4})(\s|$)", ln)
            if m:
                ids.add(m.group(1))
    return ids


# ---------------------------------------------------------------------------


def title_crosscheck(layout: str, prefix: str, eid: str, title: str) -> bool | None:
    """Check a detailed-section title against the summary-table row.

    The summary table prints each title a second time. Where the id's own
    layout line carries a title fragment, that fragment must occur inside the
    detailed title. Returns None when no fragment sits on the id line.
    """
    num = int(re.sub(r"\D", "", eid))
    if prefix:
        pat = re.compile(rf"^\s*{prefix}\s?0*{num}(?!\d)\.?\s+(.*)$")
    else:
        pat = re.compile(rf"^\s{{0,8}}0*{num}\s+(.*)$")
    alnum = lambda x: re.sub(r"[^a-z0-9]", "", x.lower())
    frags = []
    for ln in layout.splitlines():
        m = pat.match(ln)
        if m:
            t = re.sub(
                r"^(\s*(No\s+Fix|Plan(?:ned)?\s+Fix|Fixed|Doc|X|N/A)\b)+",
                "",
                m.group(1),
            )
            t = re.sub(r"(\s+X)+\s*$", "", t)
            t = alnum(t)
            if len(t) >= 6:
                frags.append(t)
    if not frags:
        return None
    return any(f in alnum(title) for f in frags)


def status_amd(fix: str) -> str:
    f = fix.lower()
    if not f:
        return ""
    if f.startswith("no fix"):
        return "No Fix"
    if f.startswith("yes") or "fixed in" in f or "will be fixed" in f:
        return "Plan Fix" if "yes" in f else "Fixed"
    return fix


def sortkey(eid: str) -> tuple[str, int]:
    m = re.match(r"([A-Z]*)(\d+)", eid)
    return (m.group(1), int(m.group(2))) if m else (eid, 0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--verify-hashes", action="store_true")
    a = ap.parse_args()

    for tool in ("pdftotext", "pdfinfo"):
        if not shutil.which(tool):
            sys.exit(f"{tool} (poppler) is required")
    poppler = (
        run(["pdftotext", "-v"])
        or subprocess.run(["pdftotext", "-v"], capture_output=True, text=True).stderr
    )
    poppler = poppler.splitlines()[0].strip() if poppler else "pdftotext"

    (CACHE / "pdf").mkdir(parents=True, exist_ok=True)
    (CACHE / "txt").mkdir(parents=True, exist_ok=True)
    fams = list(csv.DictReader(FAMILIES.open()))
    prior = {}
    if SOURCES.exists():
        prior = {
            r["family"]: r
            for r in csv.DictReader(l for l in SOURCES.open() if not l.startswith("#"))
        }

    today = dt.date.today().isoformat()
    sources, errata, texts, report = [], [], [], []
    for fam in fams:
        k = key_of(fam["family"])
        pdf = CACHE / "pdf" / f"{k}.pdf"
        retrieved = prior.get(fam["family"], {}).get("retrieved", today)
        if not a.offline or not pdf.exists():
            fetch(fam["url"], pdf)
            retrieved = today
        digest = sha256(pdf)
        if (
            a.verify_hashes
            and fam["family"] in prior
            and prior[fam["family"]]["sha256"] != digest
        ):
            raise CompletenessError(
                f"{fam['family']}: cached PDF hash {digest[:12]} differs from sources.csv "
                f"{prior[fam['family']]['sha256'][:12]}; the vendor has revised the document"
            )
        layout = run(["pdftotext", "-layout", str(pdf), "-"])
        raw = run(["pdftotext", str(pdf), "-"])
        (CACHE / "txt" / f"{k}.layout.txt").write_text(layout)
        (CACHE / "txt" / f"{k}.raw.txt").write_text(raw)
        pages = re.search(r"Pages:\s+(\d+)", run(["pdfinfo", str(pdf)])).group(1)
        ident = identity(fam["vendor"], layout)

        if fam["vendor"] == "Intel":
            detail, removed_detail = detail_intel(pdf, fam["id_prefix"])
            summ, removed = summary_intel(layout, fam["id_prefix"])
            table_ids = set(summ)
        else:
            detail = detail_amd(raw)
            table_ids = summary_amd(layout)
            summ = {e: status_amd(d.get("fix_planned", "")) for e, d in detail.items()}
            removed, removed_detail = set(), set()

        missing_detail = sorted(table_ids - set(detail), key=sortkey)
        missing_table = sorted(set(detail) - table_ids, key=sortkey)
        problems = []
        if removed != removed_detail:
            problems.append(
                f"removal markers disagree: summary {sorted(removed, key=sortkey)} "
                f"vs detail {sorted(removed_detail, key=sortkey)}"
            )
        if removed & set(detail):
            problems.append(
                f"removed but also detailed: {sorted(removed & set(detail))}"
            )
        if fam["vendor"] == "Intel":
            # Intel numbers errata sequentially; every number up to the highest
            # must be either extracted or explicitly marked removed.
            main = {
                int(re.sub(r"\D", "", e))
                for e in set(detail) | removed
                if not re.search(r"LCC", e)
            }
            gaps = sorted(set(range(1, max(main) + 1)) - main)
            if gaps:
                problems.append(f"unexplained gaps in erratum numbering: {gaps}")
        if missing_detail:
            problems.append(f"in summary table but no detailed entry: {missing_detail}")
        if missing_table:
            problems.append(f"detailed entry but not in summary table: {missing_table}")
        xchecked = 0
        for eid, d in detail.items():
            xc = title_crosscheck(layout, fam["id_prefix"], eid, d["title"])
            if xc is False:
                problems.append(
                    f"{eid}: detailed title disagrees with summary table: {d['title']!r}"
                )
            xchecked += xc is True
            if (
                len(d["title"]) < 8
                or len(d["title"]) > 250
                or LABEL.match(d["title"])
                or re.search(r"steppings affected|Summary Table", d["title"], re.I)
            ):
                problems.append(f"{eid}: title missing or truncated ({d['title']!r})")
            if not summ.get(eid):
                problems.append(f"{eid}: no fix status")
            if not d["description"]:
                problems.append(f"{eid}: no description text")
        report.append(
            (fam["family"], len(table_ids), len(detail), problems, len(removed))
        )
        if problems:
            continue

        sources.append(
            {
                "family": fam["family"],
                "vendor": fam["vendor"],
                "segment": fam["segment"],
                "document": fam["document_kind"],
                "doc_number": ident["doc_number"],
                "revision": ident["revision"],
                "doc_date": ident["date"],
                "pages": pages,
                "url": fam["url"],
                "sha256": digest,
                "retrieved": retrieved,
                "summary_table_count": len(table_ids) + len(removed),
                "removed_in_document": len(removed),
                "extracted_count": len(detail),
                "titles_crosschecked": xchecked,
            }
        )
        for eid in sorted(detail, key=sortkey):
            d = detail[eid]
            errata.append(
                {
                    "family": fam["family"],
                    "vendor": fam["vendor"],
                    "erratum_id": eid,
                    "title": d["title"],
                    "status": summ[eid],
                    "doc_number": ident["doc_number"],
                    "revision": ident["revision"],
                }
            )
            texts.append({"family": fam["family"], "erratum_id": eid, **d})

    bad = [r for r in report if r[3]]
    for fam, nt, nd, probs, nr in report:
        flag = "OK  " if not probs else "FAIL"
        print(
            f"{flag} {fam:22s} summary table {nt + nr:4d} (removed {nr:2d})  extracted {nd:4d}"
        )
        for p in probs[:12]:
            print(f"       {p}")
        if len(probs) > 12:
            print(f"       ... {len(probs) - 12} more")
    if bad:
        raise CompletenessError(f"{len(bad)} document(s) failed the completeness check")

    with SOURCES.open("w", newline="") as f:
        import fitz

        pymupdf = fitz.__doc__.split(":")[0].strip()
        f.write(
            f"# Extracted with {poppler} and {pymupdf}; see README.md. One row per source document.\n"
        )
        w = csv.DictWriter(f, fieldnames=list(sources[0]))
        w.writeheader()
        w.writerows(sources)
    with ERRATA.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(errata[0]))
        w.writeheader()
        w.writerows(errata)
    with TEXT.open("w") as f:
        for t in texts:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(
        f"\n{len(errata)} errata from {len(sources)} documents -> {ERRATA.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
