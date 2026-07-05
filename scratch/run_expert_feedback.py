import os
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor
import time
from pathlib import Path

# The list of personas
PERSONAS = [
    "Dave Patterson (RISC, Architecture legend, quantitative approach)",
    "Graduate Student (Learning, clarity, getting excited about the subject)",
    "Instructor (Pedagogy, clarity, what are the insights to teach?)",
    "Mark Hill (Memory systems, gem5, simulation)",
    "David Wood (Simulation, gem5, performance evaluation)",
    "Amin Vahdat (Google systems/networking, cloud infrastructure)",
    "Jeff Dean (ML Systems, hardware-software co-design at scale)",
    "Bill Dally (NVIDIA, accelerators, architecture, GPUs)",
    "NVIDIA Chief Architect (e.g. Bruce / Stephen Keckler - industrial accelerator integration)",
    "Jason Cong (FPGA, CAD, customized computing)",
    "Deming Chen (FPGA, ML accelerators, high-level synthesis)",
    "David Brooks (Power, machine learning for architecture)",
    "Margaret Martinosi (Power, quantum, architecture, mobile systems)",
    "ML Architect (Focus on model execution, data movement for AI)",
]

BOOK_DIR = Path("/Users/VJ/GitHub/arch2/synthesis/book/chapters")

def get_book_content():
    content = []
    # Assumes chapters are numbered 01-, 02-, etc.
    chapters = sorted(BOOK_DIR.glob("*/index.qmd"))
    for chap in chapters:
        with open(chap, "r") as f:
            content.append(f"\n\n--- CHAPTER: {chap.parent.name} ---\n\n")
            content.append(f.read())
    return "".join(content)

def call_gemini_judge(prompt: str, *, timeout: int = 600) -> dict | None:
    # Use gemini-2.5-pro or gemini-3.1-pro-preview based on SKILL.md
    r = subprocess.run(
        ["gemini", "-m", "gemini-3.1-pro-preview", "-p", prompt, "--yolo", "--skip-trust"],
        capture_output=True, text=True, timeout=timeout,
        stdin=subprocess.DEVNULL,
    )
    if r.returncode != 0:
        print(f"Error from gemini: {r.returncode}\n{r.stderr}")
        return None
    s = r.stdout
    i, j = s.find("{"), s.rfind("}")
    if i == -1 or j <= i:
        print(f"Failed to find JSON in output:\n{s[:200]}...")
        return None
    try:
        return json.loads(s[i:j + 1])
    except json.JSONDecodeError:
        print("JSON Decode Error")
        return None

def get_feedback_for_persona(persona, book_text):
    print(f"Getting feedback for: {persona}", flush=True)
    prompt = f"""You are acting as the following expert persona: {persona}

We are writing a Synthesis Lecture titled "Architecture 2.0". It's aimed at graduate students, instructors, and researchers. It is about how the design loop of computer architecture is changing with AI-assisted tools, models, and generative methods. The core message is that AI does not replace the architect; it shifts their job to bounding and governing loops (intent, abstraction, constraints, evidence, rejection authority).

Read the entire book manuscript below and provide your feedback. 
Specifically look for:
1. Clarifications needed (what don't you understand or find ambiguous?)
2. Conceptual gaps or missed connections an architect/expert would appreciate.
3. Where we might need extra figures (describe what the figure should show).
4. Do we maintain a consistent engineering discipline, avoiding AI hype and reward hacking?

BOOK MANUSCRIPT:
{book_text}

Respond with a single JSON object. No prose, no code fences.
Format:
{{
  "persona": "{persona}",
  "overall_impression": "...",
  "clarifications_needed": ["...", "..."],
  "conceptual_gaps_and_connections": ["...", "..."],
  "suggested_figures": [
      {{"location": "chapter/section", "description": "..."}}
  ],
  "hype_check": "..."
}}
"""
    
    res = call_gemini_judge(prompt)
    if res:
        out_path = Path(f"/Users/VJ/GitHub/arch2/synthesis/scratch/feedback_{persona.split(' ')[0]}.json")
        with open(out_path, "w") as f:
            json.dump(res, f, indent=2)
        print(f"Saved {out_path}", flush=True)
    else:
        print(f"Failed for {persona}", flush=True)

def main():
    book_text = get_book_content()
    print(f"Loaded book manuscript, length: {len(book_text)} chars", flush=True)
    
    out_dir = Path("/Users/VJ/GitHub/arch2/synthesis/scratch")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # We will use ThreadPoolExecutor to run these in parallel (max 8)
    with ThreadPoolExecutor(max_workers=8) as executor:
        for p in PERSONAS:
            executor.submit(get_feedback_for_persona, p, book_text)

if __name__ == "__main__":
    main()
