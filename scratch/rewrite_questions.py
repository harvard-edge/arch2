import glob
import subprocess
import json
import os

prompt = """
You are a technical editor. The following text is the "Open research questions" section from a chapter in an advanced computer architecture textbook.
The user's rule states: "Avoid the explicitly patterned 'Question: [What can the...]' or similar Q&A structural styles in written prose. We use this style very sparingly and only when it absolutely makes sense, because it reads as distinctly LLM-generated. Integrate questions and answers naturally into the narrative flow instead of forcing a rigid structural pattern."

Currently, the text uses a rigid Q&A pattern like:
1. **How do we do X?**
   Explanation of why we need to do X.

Rewrite the list to use declarative bullet points or a natural narrative flow. For example:
1. **Doing X.** Explanation of why doing X is needed.
OR
1. **The challenge of X.** Explanation of why X is needed.

Keep the exact same meaning, paragraph structure, and markdown references (e.g. @sec-something), but remove the rigid "How do we...?" question pattern. 
Also, the user noted that using "we" (e.g. "we must explore") is OK, as long as it fits naturally. Just remove the rigid Q&A formatting.

Return ONLY the rewritten markdown text. Do not include markdown code fences (like ```markdown) in your output, just the raw text.
"""

files = sorted(glob.glob("synthesis/book/chapters/*/index.qmd"))
for fpath in files:
    with open(fpath, "r") as f:
        content = f.read()
    
    if "## Open research questions" not in content:
        continue
        
    parts = content.split("## Open research questions\n")
    before = parts[0] + "## Open research questions\n"
    after_heading = parts[1]
    
    # find the end of the section
    end_marker = "::: {.callout-carry-forward"
    if end_marker in after_heading:
        questions_text = after_heading.split(end_marker)[0]
        remainder = end_marker + after_heading.split(end_marker, 1)[1]
    else:
        # Chapter 10 has tables and stuff. Let's just find the next ## or end of file
        subparts = after_heading.split("\n## ")
        questions_text = subparts[0]
        remainder = "\n## " + "\n## ".join(subparts[1:]) if len(subparts) > 1 else ""

    print(f"Rewriting {fpath}...")
    
    # Call gemini
    full_prompt = prompt + "\n\nTEXT TO REWRITE:\n" + questions_text
    
    result = subprocess.run(
        ["gemini", "-m", "gemini-2.5-pro", "-p", full_prompt, "--yolo"],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL
    )
    
    if result.returncode != 0:
        print(f"Error calling gemini: {result.stderr}")
        continue
        
    rewritten_text = result.stdout.strip()
    
    # Remove markdown block if gemini added it despite instructions
    if rewritten_text.startswith("```markdown"):
        rewritten_text = rewritten_text[len("```markdown"):].strip()
    if rewritten_text.endswith("```"):
        rewritten_text = rewritten_text[:-3].strip()
        
    new_content = before + rewritten_text + "\n\n" + remainder
    
    with open(fpath, "w") as f:
        f.write(new_content)
    
    print(f"Done {fpath}")

