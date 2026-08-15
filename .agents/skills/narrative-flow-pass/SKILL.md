---
name: narrative-flow-pass
description: Audit and optimize narrative flow, progressive concept disclosure, definition pairing, callout layout, footnote placement typography, and visual figure line routing across manuscript chapters.
---

# Narrative Flow Pass Skill

Use this skill when auditing or refining the narrative flow, pedagogical structure, callout layout, typography, or visual diagrams of manuscript chapters.

## 1. Progressive Disclosure & Definition Pairing

- **Introduce Overarching Paradigms First:** Never stack multiple definition blocks (e.g. three consecutive blockquotes) on top of each other. Introduce the primary umbrella concept or paradigm (e.g., *Architecture 2.0*) first to set the conceptual framework.
- **Pair Direct Contrasts Cleanly:** Group complementary or contrasting concepts (e.g., *Point AI assistance* vs *AI-native system and chip design*, or *AI models* vs *AI-native design systems*) together as paired bullet points or side-by-side contrasts immediately following the paradigm setup.
- **Preserve Human Narrative Transitions:** Do not strip organic, engaging transition clauses that orient human readers (e.g., "When we step back...", "As we examine the trade-offs...", "To test whether AI capabilities..."). Micro-edits must serve macro narrative continuity.

## 2. Callout & Margin Layout Rules

- **Prevent Margin & TOC Collisions:** Never let `.column-margin` or side-notes collide with or overlay the right-hand Table of Contents (`#TOC`).
- **Enforce Body Grid Scoping:** Ensure all callouts, epigraphs, and `.column-margin` blocks carry `grid-column: body !important;` in SCSS (`arch2-html.scss`) so they render as clean, full-width or side-note callout panels inside the main article column on all screen resolutions (desktop 4K, 1080p, tablet, mobile).

## 3. Footnote Typography & Placement

- **Place Footnotes Outside Trailing Punctuation:** Footnote callout markers MUST always be placed OUTSIDE (after) trailing punctuation marks (periods, commas, closing quotation marks), e.g., `sentence finish.[^fn-key]` or `clause,[^fn-key]`. Never place markers inside punctuation (`sentence finish[^fn-key].`).
- **High Technical Signal & Named Keys:** All footnotes must use reference-style named keys (`[^fn-...-cXX]`), isolate ephemeral/historical context, follow `**Term**: Definition` format, and avoid discursive bloat.

## 4. Chicago Manual of Style (CMOS) Figure and Table Prose Integration

Follow CMOS (17th/18th ed., Sections 3.9, 3.50–3.53) conventions for referencing illustrations, figures, and tables in narrative prose:

- **Pre-Briefing Requirement:** Every figure and table MUST be introduced or cited in the prose *before* or directly adjacent to its appearance in the text. Never allow a figure or table to float without prior narrative preparation.
- **Syntactic Integration vs. Parenthetical Citation:**
  - *Syntactically Integrated (Primary Object):* When the visual is the focal point of explanation, weave it directly into the sentence structure:
    - *Good:* "We trace this progression in @fig-design-method-progression, which maps each historical era..."
    - *Good:* "As @fig-moonshot-prompt illustrates, compact intent encapsulates eight coupled requirement layers..."
  - *Parenthetical (Supplementary Evidence):* When the visual confirms or illustrates an architectural fact or measurement, cite it parenthetically:
    - *Good:* "...reversing the net system efficiency through elevated interconnect traffic (@fig-waterbed-effect)."
    - *Good:* "...under strict thermal design power ceilings (@tbl-cache-run-declaration)."
  - *Avoid Awkward Meta-Narration:* Avoid clumsy formulas like "The following figure is a diagram that shows..." or "See Figure X below". State the engineering insight directly, using the cross-reference as the visual anchor.
- **Quarto Cross-Reference Syntax:** Always use `@fig-<name>` and `@tbl-<name>` so Pandoc generates hyperlinked, properly numbered cross-references. For parenthetical references, use `(@fig-<name>)` or `(@tbl-<name>)`.

## 5. Visual Figure Line & Arrow Routing Audit Loop

For every conceptual SVG figure:
1. **Render PNG:** Convert the SVG to a 1200px PNG using `rsvg-convert -w 1200 <input.svg> -o /tmp/<figure-name>.png`.
2. **Visual Inspection:** Inspect the rendered PNG using `view_file` to visually verify:
   - Zero line collisions or text clipping inside boxes.
   - Zero lines cutting through adjacent box borders.
   - Clean orthogonal path routing for all connecting arrows and feedback return loops.
3. **Tweak SVG Paths:** If any line cuts through a box or overlaps an arrow, update the SVG `<path d="..." />` coordinates to route cleanly around all elements.
4. **Re-render & Re-verify:** Re-convert SVG $\to$ PNG and inspect the final PNG to confirm 100% visual perfection.
