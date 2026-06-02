import os
import matplotlib.pyplot as plt

def render_latex_to_geometry():
    # The complex equation from your Gemini JSON output
    latex_equation = r"$\langle f, g \rangle = \frac{1}{T} \int_0^T \left[ \sum_{n \in \mathbb{Z}} a_n e^{j \frac{2\pi}{T} n t} \right] \left[ \sum_{m \in \mathbb{Z}} b_m e^{\frac{j 2\pi}{T} m t^\ast} \right] dt$"

    print("[*] Initializing Matplotlib MathTex Engine...")
    
    # Create the figure and force a solid white background color
    fig, ax = plt.subplots(figsize=(12, 3), facecolor='white')
    ax.axis('off') # Hide graph axis markers

    # Set the background of the drawing zone to solid white too
    ax.set_facecolor('white')

    # Render the text explicitly in black
    ax.text(0.5, 0.5, latex_equation, size=14, color='black',
            horizontalalignment='center', verticalalignment='center')

    output_svg = "equation_geometry.svg"
    
    # CRITICAL FIX: Removed transparent=True, added facecolor='white' to force the background plate
    print(f"[*] Extracting geometric line paths to: {output_svg}")
    plt.savefig(output_svg, format='svg', bbox_inches='tight', transparent=False, facecolor='white')
    plt.close()
    
    print("[+] Success! Clear black-on-white SVG generated.")

if __name__ == "__main__":
    render_latex_to_geometry()