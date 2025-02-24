from flask import Flask, request, render_template
from diffusers import StableDiffusionPipeline
import torch
from io import BytesIO
import base64
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import random
import os

# Initialize Flask app
app = Flask(__name__)

# Load Stable Diffusion model
print("Torch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
device = "mps" if torch.backends.mps.is_available() else "cpu"
model_id = "runwayml/stable-diffusion-v1-5"
print("Loading model...")
pipe = StableDiffusionPipeline.from_pretrained(model_id)
pipe = pipe.to(device)
pipe.enable_attention_slicing()
print(f"Model loaded on {device}")

# Ensure output directory exists
output_dir = "nfts"
os.makedirs(output_dir, exist_ok=True)

# Function to generate a single base image
def generate_base_image(prompt):
    generator = torch.Generator(device=device).manual_seed(random.randint(0, 1000000))
    return pipe(
        prompt,
        negative_prompt="blurry, low quality, distorted, pixelated",
        num_inference_steps=50,
        guidance_scale=7.5,
        generator=generator
    ).images[0]

# Function to apply unique effects
def create_variation(base_image, index):
    img = base_image.copy()
    
    # Random effects for uniqueness (more variety)
    effect_combo = random.randint(1, 31)  # 2^5 - 1 for 32 possible combos
    if effect_combo & 1:
        img = ImageEnhance.Color(img).enhance(random.uniform(0.5, 1.5))  # Hue shift
    if effect_combo & 2:
        img = ImageEnhance.Brightness(img).enhance(random.uniform(0.6, 1.4))
    if effect_combo & 4:
        img = ImageEnhance.Contrast(img).enhance(random.uniform(0.7, 1.3))
    if effect_combo & 8:
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.1, 0.5)))
    if effect_combo & 16:
        img = ImageEnhance.Sharpness(img).enhance(random.uniform(0.5, 2.0))  # Sharpen or soften
    
    # Additional random effects
    if random.random() > 0.5:
        tint = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        img = ImageOps.colorize(img.convert("L"), black=(0, 0, 0), white=tint)
    if random.random() > 0.6:
        img = ImageOps.mirror(img)
    if random.random() > 0.6:
        img = ImageOps.flip(img)  # Vertical flip
    if random.random() > 0.5:
        img = img.rotate(random.randint(-20, 20))
    if random.random() > 0.7:
        img = img.filter(ImageFilter.EDGE_ENHANCE)  # Edge enhancement
    
    # Save to file
    filename = f"{output_dir}/nft_{index:03d}.png"
    img.save(filename)
    
    # Return base64 for display
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"

# Generate 100 unique variations from one base image
def generate_nft_collection(prompt):
    print("Generating base image...")
    base_image = generate_base_image(prompt)
    
    print("Creating 100 unique variations...")
    variations = [create_variation(base_image, i) for i in range(100)]
    
    return variations

# Home route
@app.route("/", methods=["GET", "POST"])
def home():
    variations = []
    prompt = None
    
    if request.method == "POST":
        prompt = request.form.get("prompt")
        if prompt:
            print(f"Generating NFT collection for: {prompt}")
            variations = generate_nft_collection(prompt)
    
    return render_template("index.html", variations=variations, prompt=prompt, total_nfts=len(variations))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)