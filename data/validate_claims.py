#!/usr/bin/env python3
"""Check the claim ledger: every supported claim names its evidence and its label.

Ledgers live at data/claims/<chapter>.yml, one per chapter, in the same shape as
the MLPerf Nature claim file, with a label and an origin added. For each claim
this checks the fields, that the quoted text still appears in the chapter, that
each evidence file exists with the recorded hash, that a citation resolves, and
that a stated formula reproduces the stated value.

Coverage: every inline computed value in a chapter must belong to a claim, and
every quantitative sentence must be claimed or listed under not_claims with a
reason. A ledger cannot show that a claim is true or that its evidence was read
correctly. It shows what each claim rests on, and it makes a gap visible.

    python3 data/validate_claims.py                (check existing ledgers)
    python3 data/validate_claims.py --require      (fail on a chapter with no ledger)
    python3 data/validate_claims.py --candidates 02-pressures   (list quantitative sentences)
    python3 data/validate_claims.py --hash <path>  (print the sha256 to record)
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import operator
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENTS = ROOT / "book/contents"
LEDGERS = ROOT / "data/claims"
BIB = ROOT / "book/references/references.bib"
LABELS = {"measured", "modeled", "assumed", "constructed"}
ORIGINS = {"own-run", "third-party-reported", "transcribed", "chart-read", "author-model", "author-example"}
REQUIRED = ("claim_id", "description", "verbatim_quote", "label", "origin", "headline")
INLINE = re.compile(r"`\{python\}\s+([^`]+?)`")
QUANTITY = re.compile(
    r"(`\{python\}|\d(?:[\d,.]*\d)?\\?\s?(?:×|x\b|%|percent|-fold|fold\b|times\b|ms\b|ns\b|µs\b|us\b|GHz|MHz|mW\b|W\b|kW\b|MW\b|nm\b|mm|GB\b|MB\b|TB\b|hours?\b|days?\b|weeks?\b|months?\b|cycles\b)|\$\s?\d)"
)
OPERATORS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
             ast.Pow: operator.pow, ast.USub: operator.neg}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\\ ", " ")).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(node: ast.AST, names: dict[str, float]) -> float:
    if isinstance(node, ast.Expression):
        return evaluate(node.body, names)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Name):
        return float(names[node.id])
    if isinstance(node, ast.BinOp):
        return OPERATORS[type(node.op)](evaluate(node.left, names), evaluate(node.right, names))
    if isinstance(node, ast.UnaryOp):
        return OPERATORS[type(node.op)](evaluate(node.operand, names))
    raise ValueError(f"unsupported expression {ast.dump(node)}")


def chapter_file(name: str) -> Path | None:
    return next(iter(sorted(CONTENTS.rglob(f"{name}.qmd"))), None)


def ledger_scopes() -> list[str]:
    skip = {"about-the-author", "acknowledgments"}
    return sorted(p.stem for p in CONTENTS.rglob("*.qmd") if p.stem not in skip and not p.stem.startswith("_"))


def prose(text: str) -> str:
    return re.sub(r"^```.*?^```", "", text, flags=re.S | re.M)


def sentences(text: str) -> list[str]:
    body = re.sub(r"^(#|:::).*$", "", prose(text), flags=re.M)
    return [s.strip() for s in re.split(r"(?<=[.?!])\s+|\n\s*\n|\n(?=\|)", body) if s.strip()]


def check_claim(claim: dict, chapter: str, keys: set[str], errors: list[str], where: str) -> None:
    for field in REQUIRED:
        if field not in claim:
            errors.append(f"{where}: missing {field}")
            return
    if claim["label"] not in LABELS:
        errors.append(f"{where}: label {claim['label']!r} not in {sorted(LABELS)}")
    if claim["origin"] not in ORIGINS:
        errors.append(f"{where}: origin {claim['origin']!r} not in {sorted(ORIGINS)}")
    if normalize(claim["verbatim_quote"]) not in chapter:
        errors.append(f"{where}: quote no longer appears in the chapter")
    evidence = claim.get("source_files") or []
    citations = claim.get("citations") or []
    constructed = claim["label"] == "constructed" and claim.get("assumptions")
    if not evidence and not citations and not constructed:
        errors.append(f"{where}: no evidence; a claim without evidence stays out of the book")
    for item in evidence:
        path = ROOT / item["path"]
        if not path.is_file():
            errors.append(f"{where}: evidence file {item['path']} is missing")
        elif sha256(path) != item.get("sha256"):
            errors.append(f"{where}: evidence file {item['path']} changed since the claim was recorded")
    for key in citations:
        if key not in keys:
            errors.append(f"{where}: citation {key} is not in references.bib")
    if claim["origin"] == "own-run" and not evidence:
        errors.append(f"{where}: an own-run claim needs a retained results file")
    if claim["label"] in {"modeled", "assumed", "constructed"} and not claim.get("assumptions"):
        errors.append(f"{where}: a {claim['label']} claim must state its assumptions")
    if claim.get("formula"):
        try:
            value = evaluate(ast.parse(claim["formula"], mode="eval"), claim.get("raw_inputs") or {})
            if abs(value - float(claim["stated_value"])) > float(claim.get("tolerance", 0)):
                errors.append(f"{where}: formula gives {value}, stated {claim['stated_value']}")
        except (KeyError, ValueError, ZeroDivisionError, SyntaxError) as error:
            errors.append(f"{where}: formula failed: {error}")


def check_ledger(path: Path, keys: set[str], errors: list[str], seen: set[str]) -> dict:
    ledger = yaml.safe_load(path.read_text(encoding="utf-8"))
    source = chapter_file(path.stem)
    if source is None:
        errors.append(f"{path.name}: no chapter of that name")
        return {}
    text = source.read_text(encoding="utf-8")
    flat = normalize(text)
    claims = ledger.get("claims") or []
    for claim in claims:
        where = f"{path.stem}/{claim.get('claim_id', '?')}"
        if claim.get("claim_id") in seen:
            errors.append(f"{where}: duplicate claim id")
        seen.add(claim.get("claim_id"))
        check_claim(claim, flat, keys, errors, where)
    claimed_inline = {v for c in claims for v in (c.get("inline_values") or [])}
    for value in sorted(set(INLINE.findall(prose(text))) - claimed_inline):
        errors.append(f"{path.stem}: inline value {value} belongs to no claim")
    quotes = [normalize(c.get("verbatim_quote", "")) for c in claims]
    exempt = [normalize(row["quote"]) for row in ledger.get("not_claims") or [] if row.get("reason")]
    for sentence in sentences(text):
        flat_sentence = normalize(sentence)
        if QUANTITY.search(sentence) and not any(q and (q in flat_sentence or flat_sentence in q) for q in quotes + exempt):
            errors.append(f"{path.stem}: quantitative sentence is unclaimed: {flat_sentence[:100]}")
    return {"claims": len(claims), "headline": sum(1 for c in claims if c.get("headline"))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--require", action="store_true")
    parser.add_argument("--candidates")
    parser.add_argument("--hash")
    args = parser.parse_args()
    if args.hash:
        print(sha256(ROOT / args.hash))
        return 0
    if args.candidates:
        source = chapter_file(args.candidates)
        for sentence in sentences(source.read_text(encoding="utf-8")):
            if QUANTITY.search(sentence):
                print(normalize(sentence))
        return 0
    keys = set(re.findall(r"^@\w+\{\s*([^,\s]+)", BIB.read_text(encoding="utf-8"), flags=re.M))
    errors: list[str] = []
    seen: set[str] = set()
    for scope in ledger_scopes():
        ledger = LEDGERS / f"{scope}.yml"
        if ledger.is_file():
            print(scope, check_ledger(ledger, keys, errors, seen))
        else:
            print(scope, "no ledger")
            if args.require:
                errors.append(f"{scope}: no ledger")
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
