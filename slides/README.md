# Architecture 2.0 Presentation System

This directory contains the Beamer presentation decks and slide design system for *Architecture 2.0: Principles of AI-Native System and Chip Design*.

## Quickstart

Build all decks or individual targets using `make`:

```sh
make                     # Builds architecture-2.0.pdf, workshop-slides.pdf, and catalog.pdf
make architecture-2.0.pdf # The canonical 48-slide keynote and lecture deck
make catalog.pdf         # The slide layout archetype reference catalog
make workshop-slides.pdf # Workshop seminar slide deck
make clean               # Remove auxiliary build artifacts
```

## Presentation Architecture and Narrative Flow

The main presentation (`architecture-2.0.tex`) delivers a cumulative, 60-minute narrative structured across eleven core sections rather than a chapter-by-chapter book summary:

1. **Moonshot (Slides 1--6):** Establishes the Moonshot target (from high-level intent to signed-off silicon), defines the **Three Operational Layers of AI Integration** (Layer 1: AI-Assisted, Layer 2: AI-Driven, Layer 3: AI-Native), separates four distinct success claims, and poses the core Architecture 2.0 bet.
2. **Why Assistance (Slides 7--12):** Diagnoses modern hardware pressures. Demonstrates that efficiency levers add cross-layer obligations, data movement dwarfs arithmetic, and design cost has migrated to verification and physical signoff (71% of 2 nm IBS estimates). Introduces the scissors gap where candidate generation outpaces examination.
3. **Lifecycle (Slides 13--17):** Distinguishes the complete system, bounded architecture study, and iterative loop. Establishes the six lifecycle stages and insists that repairs target the layer that failed rather than regenerating raw RTL blindly.
4. **Data and Representation (Slides 18--22):** Distinguishes general model weights from live project state and historical logs. Shows why observation sources are not interchangeable and how representational choices bound reachable designs.
5. **Methods (Slides 23--30):** Enforces that engineering role precedes method selection. Contrasts the three method families (generation, prediction, optimization) and shows how generation expands the candidate space while verification narrows it.
6. **Environments (Slides 31--33):** Explains why execution environments require more than simulators. Focuses on toolchain identity preservation and distinguishing raw tool returns from calibrated measurements.
7. **Verification, Feedback, and Learning (Slides 34--36):** Contrasts formal proofs with simulation. Demands independent observation paths over recursive model prompting and details how feedback updates architectural state.
8. **Running the Design Loop (Slides 37--39):** Presents the SCALE-Sim systolic array study, walking through four distinct judgments (outcome, contribution, mechanism, stopping) and demonstrating that a failed explanation remains a valuable technical result.
9. **Patterns and Transfer (Slides 40--42):** Examines knowledge transfer across architecture generations and highlights four recurring design patterns across the stack.
10. **Evaluation (Slides 43--45):** Establishes rigorous benchmarking standards: matched system comparisons, total accounting (tokens, license queue time, human triage), and red-team robustness stress-tests.
11. **The Architect (Slides 46--48):** Clarifies the architect's enduring role (framing, representation, method selection, interpretation, recommendation), articulates a five-part research agenda, and concludes with the separation between technical recommendation and commitment authority.

---

## Slide Layout Catalog

To maintain audience engagement and prevent cognitive fatigue, presentations follow a deliberate mix of visual and typographic archetypes. In a 16:9 Beamer frame (`aspectratio=169`), the vertical budget below `\frametitle` and `\claim` is approximately 5.10 cm.

### Archetype 1: A Plot Only (Hero Visual)

Use when a graphic is dense, self-contained, and visually rich. The speaker unpacks details orally without competing text columns.

- **Canvas allocation:** Full horizontal width (`width=0.96\linewidth`), vertical height capped at `4.50cm` to leave space for `\source`.
- **LaTeX Template:**

```latex
\begin{frame}{Slide title here}
  \claim{One declarative sentence stating the primary claim of this slide.}
  \begin{center}
    \includegraphics[width=0.96\linewidth,height=4.50cm,keepaspectratio]{path/to/figure.pdf}
  \end{center}
  \source{Authoritative citation or chapter section.}
\end{frame}
```

### Archetype 2: Plot with Text on the Side (Asymmetric Split)

Use when a complex diagram requires immediate domain contextualization, takeaway badges, or explicit constraint items alongside the graphic.

- **Canvas allocation:** 64% graphic column on the left (`height=4.65cm`), 33% text column on the right with color-coded `\tagbox` labels.
- **LaTeX Template:**

```latex
\begin{frame}{Slide title here}
  \claim{One declarative sentence stating the primary claim of this slide.}
  \begin{columns}[c,onlytextwidth]
    \column{0.64\textwidth}
      \includegraphics[width=\linewidth,height=4.65cm,keepaspectratio]{path/to/figure.pdf}
    \column{0.33\textwidth}
      \tagbox{ArchBlueLight}{ArchBlue}{Category 1}
      \vspace{0.08cm}
      \begin{itemize}\setlength{\itemsep}{1pt}\small
        \item First concise observation
        \item Second concise observation
      \end{itemize}
      \vspace{0.14cm}
      \tagbox{ArchGoldLight}{ArchGold}{Category 2}
      \vspace{0.08cm}
      \begin{itemize}\setlength{\itemsep}{1pt}\small
        \item Key operational constraint
      \end{itemize}
  \end{columns}
  \source{Authoritative citation or chapter section.}
\end{frame}
```

### Archetype 3: Just Text (Structured Typography)

Use when defining taxonomies, sequential decision gates, or overarching principles. Never present an unstructured wall of bullet points; select one of three typographic variants:

#### 3a. Comparative Card Grid
Groups criteria, tradeoffs, or metrics into balanced, color-coded columns:

```latex
\begin{frame}{Slide title here}
  \claim{One declarative sentence stating the primary claim of this slide.}
  \vspace{0.15cm}
  \begin{columns}[T,onlytextwidth]
    \column{0.31\textwidth}
      \tagbox{ArchBlueLight}{ArchBlue}{Column 1 Title}
      \vspace{0.15cm}
      \begin{itemize}\setlength{\itemsep}{3pt}
        \item Item A
        \item Item B
      \end{itemize}
    \column{0.31\textwidth}
      \tagbox{ArchGreenLight}{ArchGreen}{Column 2 Title}
      \vspace{0.15cm}
      \begin{itemize}\setlength{\itemsep}{3pt}
        \item Item C
        \item Item D
      \end{itemize}
    \column{0.31\textwidth}
      \tagbox{ArchRedLight}{ArchRed}{Column 3 Title}
      \vspace{0.15cm}
      \begin{itemize}\setlength{\itemsep}{3pt}
        \item Item E
        \item Item F
      \end{itemize}
  \end{columns}
  \source{Authoritative citation.}
\end{frame}
```

#### 3b. Decision Flow and Alerts
Establishes sequential evaluation gates, formal handoffs, or boundary conditions with an alert callout below:

```latex
\begin{frame}{Slide title here}
  \claim{One declarative sentence stating the primary claim of this slide.}
  \vspace{0.25cm}
  \begin{center}
  \begin{tikzpicture}[node distance=0.22cm]
    \tikzset{claimstep/.style={rounded corners=3pt,draw=ArchLine,fill=ArchPanel,
      text width=3.05cm,minimum height=1.45cm,align=center,inner sep=4pt}}
    \node[claimstep] (a) {{\small\bfseries Gate 1}\\[2pt]{\footnotesize Description of condition}};
    \node[claimstep,right=of a] (b) {{\small\bfseries Gate 2}\\[2pt]{\footnotesize Description of condition}};
    \node[claimstep,right=of b] (c) {{\small\bfseries Gate 3}\\[2pt]{\footnotesize Description of condition}};
    \node[claimstep,right=of c] (d) {{\small\bfseries Gate 4}\\[2pt]{\footnotesize Description of condition}};
    \node[below=0.45cm of $(b.south)!0.5!(c.south)$,align=center,text=ArchRed,font=\small\bfseries]
      {Crucial constraint or alert message positioned underneath.};
  \end{tikzpicture}
  \end{center}
  \source{Authoritative citation.}
\end{frame}
```

#### 3c. Big Thesis Banner and Contrast Columns
Delivers an authoritative axiom or keynote turning point using `\bigsep`, followed by two contrasting columns:

```latex
\begin{frame}{Slide title here}
  \claim{One declarative sentence stating the primary claim of this slide.}
  \vspace{0.25cm}
  \bigsep{A single, authoritative axiom banner spanning two lines\\without awkward mid-word hyphenation.}
  \vspace{0.25cm}
  \begin{columns}[T,onlytextwidth]
    \column{0.46\textwidth}
      \tagbox{ArchRedLight}{ArchRed}{The Common Assumption}
      \vspace{0.15cm}
      \begin{itemize}
        \item Flawed or oversimplified perspective.
      \end{itemize}
    \column{0.46\textwidth}
      \tagbox{ArchGreenLight}{ArchGreen}{The Architectural Reality}
      \vspace{0.15cm}
      \begin{itemize}
        \item Physically grounded insight.
      \end{itemize}
  \end{columns}
  \source{Authoritative citation.}
\end{frame}
```

---

## Design and Quality Invariants

- **American English:** Use American spelling exclusively (modeling, colored, synthesis).
- **Punctuation:** Zero em-dashes (`—`), zero colon tics, zero `By <gerund>`.
- **Canvas Budget:** In 16:9 Beamer, content below `\claim` must stay within 5.10 cm vertical height to prevent overfull vbox warnings.
- **Mandatory Visual Inspection:** After modifying any slide, render the target pages to PNG using `pdftoppm -png -r 150 <deck>.pdf /tmp/slide-test` and inspect with `view_file` to confirm zero text-border collisions, zero awkward word breaks, and proper margins.
