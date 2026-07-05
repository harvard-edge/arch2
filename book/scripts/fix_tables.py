import os
import re

def process_file(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()
        
    changed = False
    new_lines = []
    
    # A markdown table header is a line followed by a separator line
    separator_pattern = re.compile(r'^\s*\|(?:\s*-+\s*\|)+\s*$')
    
    for i in range(len(lines)):
        # If the current line is a separator and the previous line exists and is a table row
        if separator_pattern.match(lines[i]) and i > 0 and lines[i-1].strip().startswith('|'):
            # The previous line is a header. Let's process it.
            header_line = lines[i-1]
            # Split by |
            parts = header_line.split('|')
            new_parts = []
            
            # We don't process the first and last empty strings usually resulting from leading/trailing |
            for j, part in enumerate(parts):
                if (j == 0 or j == len(parts) - 1) and part.strip() == '':
                    new_parts.append(part)
                else:
                    stripped = part.strip()
                    if stripped == '':
                        new_parts.append(part)
                    else:
                        # Check if it's already bold
                        if stripped.startswith('**') and stripped.endswith('**'):
                            new_parts.append(part)
                        else:
                            # It might have bold inside but not wrap the whole thing, or it might just not be bold
                            # Let's strip any existing bold at the edges just in case to avoid ** ** nested
                            stripped = stripped.strip('*')
                            # Retain original leading/trailing whitespace if possible, or just space it nicely
                            new_part = f" **{stripped}** "
                            new_parts.append(new_part)
            
            new_header_line = "|".join(new_parts)
            if new_header_line != header_line:
                # Replace the previous line in new_lines
                new_lines[-1] = new_header_line
                changed = True
                print(f"Fixed header in {filepath}:\n- {header_line.strip()}\n+ {new_header_line.strip()}")
                
        new_lines.append(lines[i])
        
    if changed:
        with open(filepath, 'w') as f:
            f.writelines(new_lines)

def main():
    chapters_dir = '/Users/VJ/GitHub/arch2/synthesis/book/chapters'
    for root, dirs, files in os.walk(chapters_dir):
        for file in files:
            if file.endswith('.qmd'):
                process_file(os.path.join(root, file))

if __name__ == '__main__':
    main()
