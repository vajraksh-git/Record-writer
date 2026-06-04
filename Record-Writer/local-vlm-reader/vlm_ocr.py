import torch
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info

def run_local_vlm():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[*] Loading Qwen2-VL-2B in 4-BIT MODE into {device.upper()} VRAM...")

    # 1. THE SOLID FIX: Compress the model from 4GB down to ~1.2GB
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16
    )

    model = Qwen2VLForConditionalGeneration.from_pretrained(
        "Qwen/Qwen2-VL-2B-Instruct", 
        quantization_config=quantization_config, 
        device_map="auto"
    )

    # 2. THE SAFETY NET: Cap the image resolution so it doesn't spike VRAM
    processor = AutoProcessor.from_pretrained(
        "Qwen/Qwen2-VL-2B-Instruct",
        min_pixels=256 * 28 * 28,
        max_pixels=1024 * 28 * 28  # Bumping this up so it can actually read!
    )

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "image": "test_image.png",
                },
                {
                    
                    "type": "text", 
                    "text": "Transcribe this handwritten math document exactly as written. Convert all mathematical equations and symbols into clean LaTeX. Do not add any extra formatting, just output the text and math."
                },
            ],
        }
    ]

    print("[*] Processing image and generating structured layout...")
    
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    
    inputs = processor(
        text=[text],
        images=image_inputs,
        padding=True,
        return_tensors="pt",
    ).to(device)

    # Force PyTorch to clean up any fragmented memory before the heavy math starts
    torch.cuda.empty_cache()

    generated_ids = model.generate(
        **inputs, 
        max_new_tokens=512,
        repetition_penalty=1.15,  # Stop repeating!
        temperature=0.1,          # Stop hallucinating, just read.
        do_sample=True
    )
    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    
    output_text = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )[0]

    print("\n[+] Local VLM Output:")
    print("="*40)
    print(output_text)

if __name__ == "__main__":
    run_local_vlm()