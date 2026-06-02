import torch
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

def run_local_vlm():
    # Force the model into 16-bit precision so it easily fits inside your 6GB VRAM limit
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[*] Loading Qwen2-VL-2B into {device.upper()} VRAM...")

    model = Qwen2VLForConditionalGeneration.from_pretrained(
        "Qwen/Qwen2-VL-2B-Instruct", 
        torch_dtype=torch.float16, 
        device_map="auto"
    )
    processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-2B-Instruct")

    # Format the prompt exactly like we did for Gemini
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
                    "text": 'Analyze this handwritten document. Extract headings, paragraphs, and convert all math into clean LaTeX. Output the result as a JSON list of blocks with "type" and "content".'
                },
            ],
        }
    ]

    print("[*] Processing image and generating structured layout...")
    # Prepare the inputs for the model
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    
    inputs = processor(
        text=[text],
        images=image_inputs,
        padding=True,
        return_tensors="pt",
    ).to(device)

    # Run the inference engine
    generated_ids = model.generate(**inputs, max_new_tokens=512)
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