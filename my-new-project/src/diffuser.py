from flask import Flask, request, render_template
from diffusers import StableDiffusionPipeline
import torch
from io import BytesIO
import base64
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw
import random
import os
import colorsys
import hashlib
from werkzeug.utils import secure_filename
import json
import requests

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
temp_dir = "temp"
os.makedirs(temp_dir, exist_ok=True)
output_dir = "nfts"
os.makedirs(output_dir, exist_ok=True)

# Pinata API credentials (replace with your keys)
PINATA_API_KEY = "bf0783c6c7e239baf57c"  # Replace with your Pinata API key
PINATA_SECRET_API_KEY = "88b18093b01d30c8af21be5bb6d50f6d7ce914b8f4fe463d2d22859588622340"  # Replace with your Pinata secret API key

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

# Generate distinct RGB colors (blues/neons for right image style)
def generate_unique_colors(count):
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
    
    filename = os.path.join(temp_dir, f"nft_{index:03d}.png")
    img.save(filename)
    print(f"Saved NFT {index:03d} to {filename}")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img, f"data:image/png;base64,{img_str}"

# Generate variations (NFTs) and store images in temp
def generate_nft_collection(base_image, options, prompt, num_gifs):
    total_images = num_gifs * 3  # Multiply GIF number by 3 for images
    print(f"Creating {total_images} unique variations for {num_gifs} GIFs...")
    colors = generate_unique_colors(total_images)
    variations = []
    images = []  # Store all images for GIF creation
    
    for i in range(total_images):
        img, variation = create_variation(base_image, i, colors[i], options, target_style='right')
        variations.append(variation)
        images.append(img)
    
    print(f"Generated {len(variations)} variations")
    return variations, images

## Generate GIFs from existing NFT images, with hashes as filenames, using Pinata REST API
def generate_gifs(images, options, prompt, description):
    print("Creating unique GIFs...")
    gifs = []
    gif_hashes = {}  # Store GIF paths and their hashes
    gif_ipfs_hashes = {}  # Store IPFS hashes for metadata
    
    num_gifs = len(images) // 3  # Number of GIFs based on available images
    for i in range(0, len(images), 3):  # Step by 3 to use 3 images per GIF
        if i + 2 < len(images):  # Ensure we have 3 images
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
            
            # Generate SHA-256 hash for the GIF content
            gif_binary = BytesIO()
            gif_frames[0].save(gif_binary, format="GIF", save_all=True, append_images=gif_frames[1:], duration=150, loop=0)
            gif_hash = hashlib.sha256(gif_binary.getvalue()).hexdigest()
            
            # Use hash as filename
            gif_filename = f"{gif_hash}.gif"
            gif_path = os.path.join(output_dir, gif_filename)
            gif_frames[0].save(gif_path, save_all=True, append_images=gif_frames[1:], duration=150, loop=0)
            
            # Optionally, print for debugging
            print(f"GIF {i//3} saved at {gif_path} with hash {gif_hash}")
            gifs.append(f"data:image/gif;base64,{base64.b64encode(gif_binary.getvalue()).decode('utf-8')}")
            gif_hashes[gif_path] = gif_hash
            
            # Upload GIF to Pinata via REST API
            try:
                url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
                headers = {
                    "pinata_api_key": PINATA_API_KEY,
                    "pinata_secret_api_key": PINATA_SECRET_API_KEY,
                }
                files = {"file": (gif_filename, gif_binary.getvalue(), "image/gif")}
                response = requests.post(url, headers=headers, files=files)
                response.raise_for_status()  # Raise an exception for bad status codes
                gif_ipfs_hash = response.json()["IpfsHash"]
                print(f"Uploaded {gif_path} to Pinata with hash: ipfs://{gif_ipfs_hash}")
                gif_ipfs_hashes[gif_filename] = gif_ipfs_hash
            except requests.RequestException as e:
                print(f"Failed to upload {gif_path} to Pinata: {e}")
                continue
    
    # Generate and upload metadata to Pinata via REST API
    metadata = {}
    for gif_filename, gif_ipfs_hash in gif_ipfs_hashes.items():
        gif_hash = gif_hashes[os.path.join(output_dir, gif_filename)]
        # Set name as description concatenated with hash
        name = f"{description} {gif_hash}"
        metadata[f"nft_{gif_hash}"] = {
            "name": name,
            "description": description,  # Use user-provided description
            "hash": gif_hash,
            "image": f"ipfs://{gif_ipfs_hash}",
            "attributes": [
                {"trait_type": "Effect", "value": x} for x in [k for k, v in options.items() if v]
            ]
        }
    
    # Save metadata locally with the name "metadata.json"
    metadata_file = os.path.join(output_dir, "metadata.json")
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=4)
    print(f"Generated metadata for {len(metadata)} NFTs and saved to {metadata_file}")
    
    # Upload metadata to Pinata via REST API
    try:
        url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
        headers = {
            "pinata_api_key": PINATA_API_KEY,
            "pinata_secret_api_key": PINATA_SECRET_API_KEY,
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers, json=metadata)
        response.raise_for_status()
        metadata_ipfs_hash = response.json()["IpfsHash"]
        print(f"Metadata uploaded to Pinata with hash: ipfs://{metadata_ipfs_hash}")
    except requests.RequestException as e:
        print(f"Failed to upload metadata to Pinata: {e}")
    
    return gifs

# Premium feature checker (set to True for testing)
def is_premium_user():
    # Temporarily assume premium access for testing
    return True  # Enable premium features during testing

# Generate base image with Stable Diffusion
def generate_base_image(prompt):
    generator = torch.Generator(device=device).manual_seed(random.randint(0, 1000000))
    print("Generating base image with Stable Diffusion...")
    return pipe(
        prompt,
        negative_prompt="blurry, low quality, distorted, pixelated",
        num_inference_steps=50,
        guidance_scale=7.5,
        generator=generator
    ).images[0]

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
        
        num_gifs = int(request.form.get("num_gifs", 100))  # Default to 100 if not specified
        description = request.form.get("description", "A futuristic robot GIF with flashing blue neon effects.")  # Default description
        
        if num_gifs < 1 or num_gifs > 100:
            return render_template("index.html", error="Number of GIFs must be between 1 and 100")
        
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
        
        # Generate NFTs and GIFs
        variations, images = generate_nft_collection(base_image, options, prompt, num_gifs)
        
        # Generate GIFs (premium enabled for testing)
        if is_premium_user():
            gifs = generate_gifs(images, options, prompt, description)
        else:
            print("GIF creation requires premium access")
    
    return render_template("index.html", variations=variations, gifs=gifs, prompt=prompt, total_nfts=len(variations))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)