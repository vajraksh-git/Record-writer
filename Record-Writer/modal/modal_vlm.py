# requirements.txt constraint: Keep local repo clean
import modal
import io

hf_cache_volume = modal.Volume.from_name("hf-cache-vol-7b-bnb", create_if_missing=True)
app = modal.App("record-writer-pdf-vlm")

# --- GLOBAL CONFIGURATION ---
INPUT_PDF_PATH = "../pdfs/ambarish.pdf"  
OUTPUT_LATEX_PATH = "../latex/ambarish.tex"
# You can change this to standard sizes like 'a4paper', 'letterpaper', 
# or custom dimensions like 'paperwidth=150mm, paperheight=150mm'
PAGE_FORMAT = "a4paper" 
# ----------------------------

vlm_image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install(
        "torch==2.6.0",           
        "torchvision==0.21.0",    
        "numpy==1.26.4",
        "transformers==4.51.3",   
        "accelerate==0.34.2",
        "qwen-vl-utils==0.0.8",
        "Pillow==10.4.0",
        "bitsandbytes==0.45.1",
        "pymupdf==1.24.2"
    )
)

@app.cls(
    gpu="A100", 
    image=vlm_image, 
    volumes={"/root/.cache/huggingface": hf_cache_volume},
    timeout=600 
)
class PDFVlmModel:
    @modal.enter()
    def load_model(self):
        import torch
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig

        print("[*] Loading Qwen2.5-VL-7B with stable BitsAndBytes 4-bit compression...")
        
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16
        )

        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            "Qwen/Qwen2.5-VL-7B-Instruct", 
            quantization_config=quant_config,
            device_map="auto"
        )
        self.processor = AutoProcessor.from_pretrained("Qwen/Qwen2.5-VL-7B-Instruct")

    @modal.method()
    def transcribe_pdf(self, pdf_bytes: bytes, target_pages: list[int] = None, skip_pages: list[int] = None, page_format: str = "a4paper"):
        import fitz  
        from PIL import Image
        from qwen_vl_utils import process_vision_info
        import torch 

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        combined_latex_body = ""
        
        print(f"[*] Found {len(doc)} pages. Beginning extraction loop...")

        for page_num in range(len(doc)):
            actual_page = page_num + 1

            if target_pages and actual_page not in target_pages:
                continue
            if skip_pages and actual_page in skip_pages:
                print(f"    -> Skipping Page {actual_page} (User requested)")
                continue

            print(f"    -> Processing Page {actual_page}/{len(doc)}")
            
            # --- THE ONLY CHANGE: DPI raised from 100 to 200 ---
            pix = doc[page_num].get_pixmap(dpi=200)
            img_data = pix.tobytes("ppm")
            pil_image = Image.open(io.BytesIO(img_data))
            
            # --- THE FIXED PROMPT ---
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert OCR engine converting handwritten lab notes to LaTeX. "
                        "CRITICAL RULES:\n"
                        "1. Output ONLY the valid LaTeX body content. DO NOT repeat these instructions. DO NOT output conversational filler.\n"
                        "2. Do not output \\documentclass or \\begin{document} tags.\n"
                        "3. Format main headings as \\section*{TEXT} and subheadings as \\subsection*{TEXT}.\n"
                        "4. NEVER output raw Unicode symbols like Ω or θ in plaintext. Wrap all resistances in math mode (e.g., $10\\text{ k}\\Omega$) and all phase angles/variables in math mode (e.g., $\\theta$).\n"
                        "5. DIAGRAMS: Do NOT use \\includegraphics. Estimate the vertical height of the diagram/graph in centimeters and output EXACTLY: \\vspace{Xcm} \\begin{center} [Diagram Placeholder] \\end{center} (Replace X with your estimated number).\n"
                        "6. MATH MODE IS MANDATORY: You MUST wrap ALL equations, variables, numbers with exponents, and algebraic expressions in $ ... $. Do not leave terms like 4.9t^2 or f(t) in plain text. Example: Write $4.9t^2$ not 4.9t^2. Furthermore, interpret triangle symbols as \Delta.\n"
                        "7. ANTI-HALLUCINATION: DO NOT solve math problems or auto-complete theorems. Transcribe the EXACT characters you see, even if they are mathematically wrong. Trust your eyes, not your training data."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image", 
                            "image": pil_image,
                            # --- THE ONLY CHANGE: Max pixels raised from 313600 to 2.5 million ---
                            "min_pixels": 256 * 256,
                            "max_pixels": 1600 * 1600 
                        },
                        {
                            "type": "text", 
                            "text": "Transcribe this page exactly, following all system rules. Output ONLY the LaTeX code."
                        },
                    ],
                }
            ]

            text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            image_inputs, _ = process_vision_info(messages)
            inputs = self.processor(text=[text], images=image_inputs, padding=True, return_tensors="pt").to("cuda")
            
            generated_ids = self.model.generate(**inputs, max_new_tokens=1500)
            generated_ids_trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
            page_text = self.processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True)[0]
            
            combined_latex_body += f"\n% --- PAGE {actual_page} ---\n"
            combined_latex_body += page_text.strip()
            
            # Force a hard page break after every physical page to maintain 1:1 mapping
            combined_latex_body += "\n\\newpage\n\n"

            torch.cuda.empty_cache()

        # Inject the requested page formatting into the LaTeX wrapper
        final_document = f"""\\documentclass[12pt]{{article}}
\\usepackage{{amsmath}}
\\usepackage{{amssymb}}
\\usepackage{{mathtools}}
\\usepackage[{page_format}, margin=0.25in]{{geometry}}

\\begin{{document}}
{combined_latex_body}
\\end{{document}}"""

        return final_document

# Removed the duplicate decorator!
def parse_page_string(page_str: str):
    """
    Converts a string like "1,3,5-7" into a clean list of integers: [1, 3, 5, 6, 7]
    """
    if not page_str:
        return None
        
    pages = []
    for part in page_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            pages.extend(range(start, end + 1))
        else:
            pages.append(int(part))
            
    return list(set(pages)) # Removes any accidental duplicates

@app.local_entrypoint()
def main(target: str = None, skip: str = None):
    """
    Modal automatically turns 'target' and 'skip' into --target and --skip CLI flags!
    """
    import os
    
    if not os.path.exists(INPUT_PDF_PATH):
        print(f"[-] Error: Target PDF '{INPUT_PDF_PATH}' not found.")
        return

    # 1. Parse the strings from the terminal into Python lists
    target_list = parse_page_string(target)
    skip_list = parse_page_string(skip)

    if target_list: print(f"[*] Target Pages: {target_list}")
    if skip_list: print(f"[*] Skipping Pages: {skip_list}")

    with open(INPUT_PDF_PATH, "rb") as f:
        pdf_bytes = f.read()

    print(f"[*] Booting PDF cluster...")
    vlm_runner = PDFVlmModel()
    
    # 2. Pass the dynamic lists into your VLM
    result = vlm_runner.transcribe_pdf.remote(
        pdf_bytes, 
        target_pages=target_list, 
        skip_pages=skip_list, 
        page_format=PAGE_FORMAT
    )
    
    clean_result = result.replace("```latex", "").replace("```", "").strip()
    
    os.makedirs(os.path.dirname(OUTPUT_LATEX_PATH) or '.', exist_ok=True)
    with open(OUTPUT_LATEX_PATH, "w") as f:
        f.write(clean_result)
        
    print(f"[+] Complete! Output saved to '{OUTPUT_LATEX_PATH}'.")

    #RUN modal run modal_vlm.py --target "1-2,4" --skip "3" to test with specific pages!
    #modal run modal_vlm.py --target "1-10" --skip "3"