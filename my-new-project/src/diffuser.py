from flask import Flask, request, render_template
from diffusers import StableDiffusionPipeline
import torch
from io import BytesIO
import base64
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw
import random
import os
import colorsys
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
output_dir = "nfts"
os.makedirs(output_dir, exist_ok=True)

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

# Generate 300 distinct RGB colors (blues/neons for right image style)
def generate_unique_colors(count=300):
    colors = []
    for i in range(count):
        hue = (i / count) * 0.7  # Focus on blue/neon hues (0.5-0.7 range)
        rgb = colorsys.hsv_to_rgb(hue, 0.9, 0.9)  # High saturation/value for neon
        colors.append(tuple(int(x * 255) for x in rgb))
    return colors

# Apply drastic effects to match the right image (futuristic, blue-lit robot)
def create_variation(base_image, index, bg_color, options, target_style='right'):
    img = base_image.copy().convert("RGB")
    
    # Apply background color (blue/neon for right style)
    img_with_bg = Image.new("RGB", img.size, bg_color)
    img_with_bg.paste(img, (0, 0), img.split()[3] if img.mode == "RGBA" else None)
    img = img_with_bg
    
    # Test and apply selected effects (debug prints for verification)
    if 'hue' in options:
        img = ImageEnhance.Color(img).enhance(random.uniform(0.0, 2.0))
        print(f"NFT {index}: Applied drastic hue shift (blue/neon)")
    if 'brightness' in options:
        img = ImageEnhance.Brightness(img).enhance(random.uniform(0.2, 1.8))
        print(f"NFT {index}: Applied drastic brightness")
    if 'contrast' in options:
        img = ImageEnhance.Contrast(img).enhance(random.uniform(0.5, 2.5))
        print(f"NFT {index}: Applied drastic contrast")
    if 'posterize' in options:
        img = ImageOps.posterize(img, random.randint(2, 4))
        print(f"NFT {index}: Applied posterization")
    if 'neon' in options:
        draw = ImageDraw.Draw(img)
        neon_color = (0, 0, random.randint(200, 255))  # Blue/neon for right style
        draw.rectangle([0, 0, img.width, img.height], outline=neon_color, width=15)
        print(f"NFT {index}: Applied neon border (blue)")
    
    filename = f"{output_dir}/nft_{index:03d}.png"
    img.save(filename)
    print(f"Saved NFT {index:03d} to {filename}")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img, f"data:image/png;base64,{img_str}"

# Generate 300 variations and prepare for 100 GIFs
def generate_nft_collection(base_image, options, prompt):
    print("Creating 300 unique variations...")
    colors = generate_unique_colors(300)
    variations = []
    images = []  # Store all images for GIF creation
    
    for i in range(300):
        img, variation = create_variation(base_image, i, colors[i], options, target_style='right')
        variations.append(variation)
        images.append(img)
    
    # Generate 100 unique GIFs from the 300 images (3 frames each, non-overlapping)
    gifs = []
    for i in range(0, 300, 3):  # Step by 3 to use 3 images per GIF
        if i + 2 < 300:  # Ensure we have 3 images
            gif_frames = [images[i], images[i + 1], images[i + 2]]
            
            # Apply drastic changes for flashing effect
            for j, frame in enumerate(gif_frames):
                if 'hue' in options:
                    frame = ImageEnhance.Color(frame).enhance((j + 1) * 0.8)
                if 'brightness' in options:
                    frame = ImageEnhance.Brightness(frame).enhance(0.3 + j * 0.7)
                if 'contrast' in options:
                    frame = ImageEnhance.Contrast(frame).enhance(1.5 + j * 0.5)
                gif_frames[j] = frame
            
            gif_path = os.path.join(output_dir, f"gif_{prompt[:10] if prompt else 'uploaded'}_{i//3:03d}_{random.randint(0, 9999)}.gif")
            gif_frames[0].save(gif_path, save_all=True, append_images=gif_frames[1:], duration=150, loop=0)
            with open(gif_path, "rb") as gif_file:
                gif_str = base64.b64encode(gif_file.read()).decode("utf-8")
            gifs.append(gif_str)
    
    print(f"Generated {len(variations)} variations and {len(gifs)} GIFs")
    return variations, gifs

# Premium feature checker (set to True for testing)
def is_premium_user():
    # Temporarily assume premium access for testing
    return True  # Enable premium features during testing

@app.route("/", methods=["GET", "POST"])
def home():
    variations = []
    gifs = []
    prompt = None
    
    if request.method == "POST":
        options = {
            'hue': 'hue' in request.form,
            'brightness': 'brightness' in request.form,
            'contrast': 'contrast' in request.form,
            'posterize': 'posterize' in request.form,
            'neon': 'neon' in request.form
        }
        
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            base_image = Image.open(file_path).convert("RGBA")
            print("Using uploaded image as base...")
            prompt = "Uploaded Image"
        else:
            prompt = request.form.get("prompt", "")
            if not prompt:
                return render_template("index.html", error="Please provide a prompt or upload an image")
            base_image = generate_base_image(prompt)
        
        # Generate NFTs
        variations, _ = generate_nft_collection(base_image, options, prompt)
        
        # Generate GIFs (premium enabled for testing)
        if is_premium_user():
            _, gifs = generate_nft_collection(base_image, options, prompt)
        else:
            print("GIF creation requires premium access")
    
    return render_template("index.html", variations=variations, gifs=gifs, prompt=prompt, total_nfts=len(variations))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)