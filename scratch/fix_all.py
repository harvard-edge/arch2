import glob
import re

def fix_chapter_1(content):
    content = content.replace(
        '*Why the Prompt Spans the Stack* section',
        'the @sec-why-the-prompt-spans-the-stack section'
    )
    content = content.replace(
        '*Efficiency Claims Need Rejectable Loops* section',
        'the @sec-efficiency-claims-need-rejectable-loops section'
    )
    content = content.replace(
        '*Architecture Development Spans Three Roles* section',
        'the @sec-architecture-development-spans-three-roles section'
    )
    content = content.replace(
        '*From Architecture 1.0 to Architecture 2.0* section',
        'the @sec-from-architecture-10-to-architecture-20 section'
    )
    return content

def fix_chapter_2(content):
    # Replace only the first occurrence which is around line 374
    # But to be safe we'll use a regex that matches the exact caption
    content = re.sub(
        r'\]\(images/F2-scissors-gap\)\{#fig-scissors-gap\s+width="100%"',
        r'](images/F2-scissors-gap){#fig-scissors-gap-intro width="100%"',
        content
    )
    return content

def fix_chapter_6(content):
    content = content.replace(
        'Once a loop can act and choose methods, how do we know whether its feedback is evidence? @sec-feedback-verification-trust answers that question by',
        'Once a loop can act and choose methods, it must rigorously verify whether its feedback constitutes true evidence. @sec-feedback-verification-trust addresses this by'
    )
    return content

def fix_chapter_9(content):
    content = content.replace(
        '::: {.callout-lighthouse title="The subsystem choice is an integration choice"}',
        ':::: {.callout-lighthouse title="The subsystem choice is an integration choice"}'
    )
    content = content.replace(
        '::: {.callout-architect-checkpoint title="The Cross-Layer Rejection Gate"}\nWhen an optimizer tunes a candidate architecture against a local proxy (like core area), the architect must enforce cross-layer boundaries. Does the loop environment automatically reject candidates that only win by silently pushing complexity into memory traffic, compiler support, verification, or SoC integration?\n:::\n:::',
        '::: {.callout-architect-checkpoint title="The Cross-Layer Rejection Gate"}\nWhen an optimizer tunes a candidate architecture against a local proxy (like core area), the architect must enforce cross-layer boundaries. Does the loop environment automatically reject candidates that only win by silently pushing complexity into memory traffic, compiler support, verification, or SoC integration?\n:::\n::::'
    )
    return content

def verb_to_gerund(verb):
    verb = verb.lower()
    if verb.endswith('e') and verb not in ['see', 'be']:
        return verb[:-1] + 'ing'
    elif verb.endswith('t') and verb not in ['detect', 'construct', 'extract', 'connect']:
        return verb + 'ting' # e.g., get -> getting (simple hack, may not be perfect)
    return verb + 'ing'

def fix_questions(content):
    lines = content.split('\n')
    in_questions = False
    for i, line in enumerate(lines):
        if line.strip().lower() == '## open research questions':
            lines[i] = '## Open Research Questions'
            in_questions = True
        elif in_questions and line.startswith('## '):
            in_questions = False
        
        if in_questions:
            # Match "1. **How do we construct ...?**"
            match = re.match(r'^(\d+\.) \*\*(?:How do we|How can we|How can|How do)\s+([a-zA-Z\-]+)\s+(.*?)\?\*\*(.*)$', line)
            if match:
                num = match.group(1)
                verb = match.group(2)
                rest = match.group(3)
                trailing = match.group(4)
                
                gerund = verb_to_gerund(verb).capitalize()
                
                # Reconstruct the line
                lines[i] = f"{num} **{gerund} {rest}.**{trailing}"
    return '\n'.join(lines)

def process_all():
    files = sorted(glob.glob('synthesis/book/chapters/*/index.qmd'))
    for f in files:
        with open(f, 'r') as fh:
            content = fh.read()
            
        content = fix_questions(content)
        
        if '01-moonshot' in f:
            content = fix_chapter_1(content)
        if '02-design-loop' in f:
            content = fix_chapter_2(content)
        if '06-methods' in f:
            content = fix_chapter_6(content)
        if '09-loop-patterns' in f:
            content = fix_chapter_9(content)
            
        with open(f, 'w') as fh:
            fh.write(content)

if __name__ == '__main__':
    process_all()
