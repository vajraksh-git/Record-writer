import modal

# Create a persistent cloud drive to store downloaded Hugging Face models permanently
hf_cache_volume = modal.Volume.from_name("hf-cache-vol", create_if_missing=True)

app = modal.App("record-writer-vlm")

# 1. Install the tool libraries into the cloud image
vlm_image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install(
        "torch==2.1.2",
        "numpy<2",  # 👈 LOCK THIS DOWN IN THE CLOUD TOO!
        "transformers==4.45.0",
        "torchvision",
        "accelerate==0.34.2",
        "qwen-vl-utils==0.0.8",
        "Pillow==10.4.0",
    )
)

# 2. Tell the cloud GPU to read/write to our persistent hard drive
@app.cls(
    gpu="A10G", 
    image=vlm_image, 
    volumes={"/root/.cache/huggingface": hf_cache_volume}, # Mount the cache drive here
    timeout=600
)
class QwenModel:
    @modal.enter()
    def load_model(self):
        import torch
        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

        print("[*] Cloud GPU Initializing... checking Hugging Face cache mount...")
        
        # This streams from Hugging Face on run #1, then reads instantly from the Volume on run #2
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            "Qwen/Qwen2-VL-2B-Instruct", 
            torch_dtype=torch.float16, 
            device_map="auto"
        )
        self.processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-2B-Instruct")

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
                        "text": "Transcribe this handwritten math document exactly as written. Convert all mathematical equations and symbols into clean LaTeX formulas."
                    },
                ],
            }
        ]

        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, _ = process_vision_info(messages)
        inputs = self.processor(text=[text], images=image_inputs, padding=True, return_tensors="pt").to("cuda")
        
        generated_ids = self.model.generate(**inputs, max_new_tokens=512)
        generated_ids_trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
        return self.processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True)[0]

@app.local_entrypoint()
def main():
    import os
    image_path = "test_image.png"
    
    if not os.path.exists(image_path):
        print(f"[-] Place your layout image at '{image_path}' first!")
        return

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    print("[*] Streaming job to Modal infrastructure...")
    vlm_runner = QwenModel()
    result = vlm_runner.transcribe_image.remote(image_bytes)
    
    print("\n[+] Output:")
    print(result)