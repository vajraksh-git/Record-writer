import modal

# Create a persistent cloud volume for the 7B model weights
hf_cache_volume = modal.Volume.from_name("hf-cache-vol-7b", create_if_missing=True)

app = modal.App("record-writer-super-vlm")

# Upgraded image configuration matching PyTorch and Transformers requirements
vlm_image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install(
        "torch==2.4.0",
        "torchvision==0.19.0",
        "numpy==1.26.4",        # Strictly locked below 2.0
        "transformers==4.49.0", # Exact version for Qwen2.5-VL
        "accelerate==0.34.2",
        "qwen-vl-utils==0.0.8",
        "Pillow==10.4.0",
    )
)

# Provision a premium enterprise A100 GPU to host the uncompressed 7B parameters
@app.cls(
    gpu="A100", 
    image=vlm_image, 
    volumes={"/root/.cache/huggingface": hf_cache_volume},
    timeout=800
)
class SuperVlmModel:
    @modal.enter()
    def load_model(self):
        import torch
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor

        print("[*] Cloud Infrastructure Initialized.")
        print("[*] Loading Qwen2.5-VL-7B-Instruct weights in half-precision (bfloat16)...")
        
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            "Qwen/Qwen2.5-VL-7B-Instruct", 
            torch_dtype=torch.bfloat16,
            device_map="auto"
        )
        self.processor = AutoProcessor.from_pretrained("Qwen/Qwen2.5-VL-7B-Instruct")

    @modal.method()
    def transcribe_image(self, image_bytes: bytes):
        import torch
        from io import BytesIO
        from PIL import Image
        from qwen_vl_utils import process_vision_info

        pil_image = Image.open(BytesIO(image_bytes))
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": pil_image},
                    {
                        "type": "text", 
                        "text": (
                            "You are an expert OCR transcription engine specializing in advanced mathematics.\n"
                            "Transcribe this handwritten document exactly as written.\n\n"
                            "CRITICAL OUTPUT FORMAT RULES:\n"
                            "1. You MUST wrap your entire output in a valid, compiling standalone LaTeX document structure.\n"
                            "2. Your output MUST explicitly start with \\documentclass{article} and include the following packages in the preamble:\n"
                            "   \\usepackage{amsmath}\n"
                            "   \\usepackage{amssymb}\n"
                            "   \\usepackage{mathtools}\n"
                            "3. Your text content MUST sit cleanly between \\begin{document} and \\end{document}.\n"
                            "4. Use standard base symbols like \\stackrel{\\mathrm{FS}}{\\longleftrightarrow} for transform relations to ensure compatibility.\n"
                            "5. Output ONLY the raw LaTeX string. Do not wrap it in markdown code blocks like ```latex, and do not add any conversational introduction or conclusion fluff."
                        )
                    },
                ],
            }
        ]
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, _ = process_vision_info(messages)
        inputs = self.processor(text=[text], images=image_inputs, padding=True, return_tensors="pt").to("cuda")
        
        print("[*] Executing inference matrix across A100 cores...")
        generated_ids = self.model.generate(**inputs, max_new_tokens=1024)
        generated_ids_trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
        
        return self.processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True)[0]

@app.local_entrypoint()
def main():
    import os
    image_path = "test_image.png"
    
    if not os.path.exists(image_path):
        print(f"[-] Error: Target image path '{image_path}' not found.")
        return

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    print(f"[*] Packaging context. Streaming payload data to A100 cluster environment...")
    vlm_runner = SuperVlmModel()
    result = vlm_runner.transcribe_image.remote(image_bytes)
    
    print("\n[+] SOTA Cloud VLM Transcription Output:")
    print("=" * 60)
    print(result)
    print("=" * 60)