import re
import os

def clean_text_for_vpype(raw_text):
    text = re.sub(r'\\(?:sub)?section\*?\{(.*?)\}', r'\1', raw_text, flags=re.DOTALL)
    text = re.sub(r'\\begin\{.*?\}(?:\[.*?\])?(?:\{.*?\})?', '', text)
    text = re.sub(r'\\end\{.*?\}', '', text)
    text = re.sub(r'\\hline', '', text)
    text = re.sub(r'\\centering', '', text)
    text = re.sub(r'\\caption\{(.*?)\}', r'\1', text)
    
    # --- FIX 1: Wipe out any orphaned or headless image brackets ---
    text = re.sub(r'\[width=.*?\]\{.*?\}', '', text)
    text = re.sub(r'\\includegraphics(?:\[.*?\])?\{.*?\}', '', text)
    # NEW: Translate LaTeX symbols into English for the physical pen
    replacements = {
        '\\Delta': 'Delta',
        '\\Rightarrow': '=>',
        '\\rightarrow': '->',
        '\\to': '->',
        '\\lim': 'lim ',
        '\\infty': 'infinity',
        '\\text{': '', 
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
        
    text = text.replace('\\(', '').replace('\\)', '').replace('$', '')
    text = text.replace('\\', '')
    text = text.replace('&', '        ')
    text = text.replace('{', '').replace('}', '')
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text

def parse_latex_document(file_path):
    if not os.path.exists(file_path):
        print(f"[-] Error: Could not find {file_path}")
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        body = content.split(r"\begin{document}")[1].split(r"\end{document}")[0]
    except IndexError:
        body = content 

    pages = body.split(r"\newpage")
    
    math_regex = r'(\\\[.*?\\\]|\$\$.*?\$\$|\\begin\{(?:align|equation|eqnarray)\*?\}.*?\\end\{(?:align|equation|eqnarray)\*?\})'
    space_regex = r'(\\vspace\{([\d.]+)cm\}|\\includegraphics(?:\[.*?\])?\{.*?\}|\[width=.*?\]\{.*?\})'
    block_pattern = re.compile(f'{math_regex}|{space_regex}', re.DOTALL)

    all_pages_data = []

    for page_num, page_text in enumerate(pages):
        if not page_text.strip():
            continue
            
        page_blocks = []
        cursor = 0
        
        for match in block_pattern.finditer(page_text):
            text_block = page_text[cursor:match.start()].strip()
            text_block = re.sub(r"% --- PAGE \d+ ---", "", text_block)
            clean_text = clean_text_for_vpype(text_block)
            if clean_text:
                page_blocks.append({"type": "TEXT", "content": clean_text})
            
            if match.group(1): 
                raw_math = match.group(1).strip()
                clean_math = re.sub(r'\\begin\{(?:align|equation|eqnarray)\*?\}', '', raw_math)
                clean_math = re.sub(r'\\end\{(?:align|equation|eqnarray)\*?\}', '', clean_math)
                clean_math = clean_math.replace('\\[', '').replace('\\]', '').replace('$$', '').strip()
                clean_math = clean_math.replace('\\\\', '\n')
                math_lines = [line.strip() for line in clean_math.split('\n') if line.strip()]
                
                for line in math_lines:
                    line = line.replace('&', '')
                    if line:
                        page_blocks.append({"type": "MATH", "content": line})
                
            elif match.group(2): 
                height_cm = match.group(3) if "vspace" in match.group(2) and match.group(3) else "4.0"
                page_blocks.append({"type": "SPACE", "content": height_cm})
            
            cursor = match.end()
            
        final_text = page_text[cursor:].strip()
        final_text = re.sub(r"% --- PAGE \d+ ---", "", final_text)
        clean_final = clean_text_for_vpype(final_text)
        
        if clean_final:
            page_blocks.append({"type": "TEXT", "content": clean_final})

        all_pages_data.append(page_blocks)

    return all_pages_data