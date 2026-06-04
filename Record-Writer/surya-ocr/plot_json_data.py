import json
import os
import matplotlib.pyplot as plt

# 🛠️ FIX: Force Matplotlib to use internal fallback configuration for unknown glyphs safely
# Or parse strings cleanly without breaking the drawing matrix layout
def plot_structured_json():
    json_path = "math_results.json"
    output_img_path = "digital_reconstruction.png"

    if not os.path.exists(json_path):
        print(f"[-] Error: '{json_path}' not found.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        blocks = json.load(f)

    print("[*] Initializing rendering canvas...")
    fig, ax = plt.subplots(figsize=(12, 8), facecolor='white')
    ax.axis('off')

    current_y = 0.92
    left_x = 0.05

    print("[*] Parsing segments onto digital page layout...")
    
    for block in blocks:
        block_type = block.get("type")
        content = block.get("content")

        if block_type == "text":
            # 🛠️ FIX: Matplotlib chokes on \stackrel inside text tags. 
            # We strip the dollar signs and convert it to plain text view for simple layout verification.
            text_to_render = content.replace(r"\stackrel{FS}{\longleftrightarrow}", "-->")
            text_to_render = text_to_render.replace("$", "") # Remove math indicators for standard display strings
            font_size = 12
            font_weight = 'normal'
            color = '#1a1a1a'
            y_drop = 0.06
            
        elif block_type == "equation":
            # Pure equations remain untouched since they are standard math syntax
            if not content.startswith("$"):
                text_to_render = f"${content}$"
            else:
                text_to_render = content
                
            font_size = 13
            font_weight = 'bold'
            color = '#003366'
            y_drop = 0.12

        current_y -= y_drop

        try:
            ax.text(left_x, current_y, text_to_render, 
                    fontsize=font_size, 
                    color=color,
                    weight=font_weight,
                    va='center', 
                    ha='left')
        except Exception as e:
            # Safe boundary handler so a parsing error never crashes your entire runtime loop
            print(f"[-] Warning: Skipping formatting issues on block: {content[:20]}...")
            continue

    print(f"[*] Exporting finished layout to: {output_img_path}")
    plt.savefig(output_img_path, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"\n[+] Success! Open '{output_img_path}' to view the formatted readout sequence.")

if __name__ == "__main__":
    plot_structured_json()