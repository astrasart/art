from flask import Flask, request, render_template, send_file, session
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
import math

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
temp_dir = "temp"
os.makedirs(temp_dir, exist_ok=True)
output_dir = "nfts"
os.makedirs(output_dir, exist_ok=True)

pinata_api_key = os.getenv("pinata_api_key", "default_key_if_not_found")
pinata_secret_api_key = os.getenv("pinata_secret_api_key", "default_secret_if_not_found")

print("Torch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
device = "mps" if torch.backends.mps.is_available() else "cpu"
model_id = "runwayml/stable-diffusion-v1-5"
print("Loading model...")
pipe = StableDiffusionPipeline.from_pretrained(model_id)
pipe = pipe.to(device)
pipe.enable_attention_slicing()
print(f"Model loaded on {device}")

def generate_unique_colors(count):
    colors = []
    for i in range(count):
        hue = (i / count) * 0.7
        rgb = colorsys.hsv_to_rgb(hue, random.uniform(0.7, 1.0), random.uniform(0.7, 1.0))
        colors.append(tuple(int(x * 255) for x in rgb))
    return colors

def create_variation(base_image, index, bg_color, options, target_style='right'):
    img = base_image.copy().convert("RGB")
    img_with_bg = Image.new("RGB", img.size, bg_color)
    img_with_bg.paste(img, (0, 0), img.split()[3] if img.mode == "RGBA" else None)
    img = img_with_bg
    
    if options.get('hue', False):
        img = ImageEnhance.Color(img).enhance(random.uniform(0.5, 2.5))
        print(f"NFT {index}: Applied drastic hue shift (blue/neon)")
    if options.get('brightness', False):
        img = ImageEnhance.Brightness(img).enhance(random.uniform(0.1, 2.0))
        print(f"NFT {index}: Applied drastic brightness")
    if options.get('contrast', False):
        img = ImageEnhance.Contrast(img).enhance(random.uniform(0.3, 2.7))
        print(f"NFT {index}: Applied drastic contrast")
    if options.get('posterize', False):
        img = ImageOps.posterize(img, random.randint(1, 5))
        print(f"NFT {index}: Applied posterization")
    if options.get('neon', False):
        draw = ImageDraw.Draw(img)
        neon_color = (random.randint(0, 50), random.randint(0, 50), random.randint(150, 255))
        width = random.randint(10, 20)
        draw.rectangle([0, 0, img.width, img.height], outline=neon_color, width=width)
        print(f"NFT {index}: Applied neon border (varied)")
    if options.get('pixelate', False):
        scale = random.randint(5, 15)
        small = img.resize((img.width // scale, img.height // scale), Image.Resampling.NEAREST)
        img = small.resize(img.size, Image.Resampling.NEAREST)
        print(f"NFT {index}: Applied pixelation (scale {scale})")
    if options.get('invert', False):
        img = ImageOps.invert(img)
        if random.random() > 0.5:
            img = Image.blend(img, img_with_bg, 0.5)
        print(f"NFT {index}: Applied color inversion")
    if options.get('blur', False):
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(1, 5)))
        print(f"NFT {index}: Applied blur")
    if options.get('sharpen', False):
        img = ImageEnhance.Sharpness(img).enhance(random.uniform(2.0, 5.0))
        print(f"NFT {index}: Applied extra sharpening")
    if options.get('emboss', False):
        img = img.filter(ImageFilter.EMBOSS)
        if random.random() > 0.5:
            img = Image.blend(img, img_with_bg, 0.7)
        print(f"NFT {index}: Applied emboss effect")
    if options.get('edge', False):
        img = img.filter(ImageFilter.FIND_EDGES)
        img = ImageEnhance.Contrast(img).enhance(random.uniform(1.5, 3.0))
        print(f"NFT {index}: Applied edge detection")
    
    img = img.filter(ImageFilter.SHARPEN)
    img = ImageEnhance.Sharpness(img).enhance(random.uniform(1.2, 1.8))
    img = ImageEnhance.Contrast(img).enhance(random.uniform(1.0, 1.4))
    target_size = (1028, 1028)
    img = img.resize(target_size, Image.Resampling.LANCZOS)
    
    filename = os.path.join(temp_dir, f"nft_{index:03d}.png")
    img.save(filename)
    print(f"Saved NFT {index:03d} to {filename}")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img, f"data:image/png;base64,{img_str}", filename

def generate_nft_collection(base_image, options, prompt, num_gifs):
    total_images = num_gifs * 4
    print(f"Creating {total_images} unique variations for {num_gifs} GIFs...")
    colors = generate_unique_colors(total_images)
    variations, images, filenames = [], [], []
    
    for i in range(total_images):
        img, variation, filename = create_variation(base_image, i, colors[i], options)
        variations.append(variation)
        images.append(img)
        filenames.append(filename)
    
    print(f"Generated {len(variations)} variations")
    return variations, images, filenames

def upload_to_pinata(file_path, file_type="image/png"):
    try:
        url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
        headers = {
            "pinata_api_key": pinata_api_key,
            "pinata_secret_api_key": pinata_secret_api_key,
        }
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, file_type)}
            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()
            ipfs_hash = response.json()["IpfsHash"]
            print(f"Uploaded {file_path} to Pinata with hash: ipfs://{ipfs_hash}")
            return ipfs_hash
    except requests.RequestException as e:
        print(f"Failed to upload {file_path} to Pinata: {e}")
        return None

def generate_nfts_and_gifs(images, filenames, options, prompt, description, base_image, base_image_path, collect_name, artist_name):
    print("Processing NFTs and GIFs with IPFS upload...")
    gifs, nft_hashes, nft_ipfs_hashes = [], {}, {}
    
    base_filename = os.path.join(temp_dir, "base_image.png")
    base_image.save(base_filename)
    base_hash = hashlib.sha256(open(base_filename, "rb").read()).hexdigest()
    base_ipfs_hash = upload_to_pinata(base_filename)
    if base_ipfs_hash:
        nft_hashes[base_filename] = base_hash
        nft_ipfs_hashes["base_image.png"] = base_ipfs_hash

    for filename in filenames:
        nft_hash = hashlib.sha256(open(filename, "rb").read()).hexdigest()
        ipfs_hash = upload_to_pinata(filename)
        if ipfs_hash:
            nft_hashes[filename] = nft_hash
            nft_ipfs_hashes[os.path.basename(filename)] = ipfs_hash
    
    num_gifs = len(images) // 4
    for i in range(0, len(images), 4):
        if i + 2 < len(images):
            gif_frames = [base_image.copy()] + [images[i], images[i + 1], images[i + 2]]
            for j, frame in enumerate(gif_frames[1:], 1):
                if options.get('hue', False):
                    frame = ImageEnhance.Color(frame).enhance((j) * random.uniform(0.5, 2.0))
                if options.get('brightness', False):
                    frame = ImageEnhance.Brightness(frame).enhance(0.3 + (j-1) * random.uniform(0.5, 1.5))
                if options.get('contrast', False):
                    frame = ImageEnhance.Contrast(frame).enhance(1.5 + (j-1) * random.uniform(0.3, 1.0))
                if options.get('pixelate', False):
                    scale = random.randint(5, 15)
                    small = frame.resize((frame.width // scale, frame.height // scale), Image.Resampling.NEAREST)
                    frame = small.resize(frame.size, Image.Resampling.NEAREST)
                if options.get('invert', False):
                    frame = ImageOps.invert(frame)
                if options.get('blur', False):
                    frame = frame.filter(ImageFilter.GaussianBlur(radius=random.uniform(1, 5)))
                if options.get('sharpen', False):
                    frame = ImageEnhance.Sharpness(frame).enhance(random.uniform(2.0, 5.0))
                if options.get('emboss', False):
                    frame = frame.filter(ImageFilter.EMBOSS)
                if options.get('edge', False):
                    frame = frame.filter(ImageFilter.FIND_EDGES)
                gif_frames[j] = frame
            
            gif_binary = BytesIO()
            gif_frames[0].save(gif_binary, format="GIF", save_all=True, append_images=gif_frames[1:], duration=150, loop=0)
            gif_hash = hashlib.sha256(gif_binary.getvalue()).hexdigest()
            
            gif_filename = f"{gif_hash}.gif"
            gif_path = os.path.join(output_dir, gif_filename)
            gif_frames[0].save(gif_path, save_all=True, append_images=gif_frames[1:], duration=150, loop=0)
            
            print(f"GIF {i//3} saved at {gif_path} with hash {gif_hash}")
            gifs.append(f"data:image/gif;base64,{base64.b64encode(gif_binary.getvalue()).decode('utf-8')}")
            nft_hashes[gif_path] = gif_hash
            
            ipfs_hash = upload_to_pinata(gif_path, "image/gif")
            if ipfs_hash:
                nft_ipfs_hashes[gif_filename] = ipfs_hash
    
    metadata = {}
    for file_path, ipfs_hash in nft_ipfs_hashes.items():
        full_path = os.path.join(output_dir if file_path.endswith('.gif') else temp_dir, file_path)
        if full_path in nft_hashes:
            nft_hash = nft_hashes[full_path]
            name_suffix = f" {nft_hash}" if file_path != "base_image.png" else " (Rare)"
            metadata[f"nft_{nft_hash}"] = {
                "name": f"{collect_name}{name_suffix}",
                "description": description if description else prompt,
                "hash": nft_hash,
                "image": f"ipfs://{ipfs_hash}",
                "creator": artist_name if artist_name else "Unknown",
                "attributes": [{"trait_type": "Type", "value": "Base" if file_path == "base_image.png" else "Variation" if file_path.endswith('.png') else "GIF"}] + 
                              [{"trait_type": "Effect", "value": x} for x in [k for k, v in options.items() if v]]
            }
    
    metadata_file = os.path.join(output_dir, "metadata.json")
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=4)
    print(f"Generated metadata for {len(metadata)} NFTs and saved to {metadata_file}")
    
    try:
        url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
        headers = {"pinata_api_key": pinata_api_key, "pinata_secret_api_key": pinata_secret_api_key, "Content-Type": "application/json"}
        response = requests.post(url, headers=headers, json=metadata)
        response.raise_for_status()
        metadata_ipfs_hash = response.json()["IpfsHash"]
        print(f"Metadata uploaded to Pinata with hash: ipfs://{metadata_ipfs_hash}")
    except requests.RequestException as e:
        print(f"Failed to upload metadata to Pinata: {e}")
    
    return gifs

def is_premium_user():
    return True  # For testing

def generate_base_image(prompt):
    generator = torch.Generator(device=device).manual_seed(random.randint(0, 1000000))
    print("Generating base image with Stable Diffusion...")
    return pipe(
        prompt,
        negative_prompt="Blurry, low quality, distorted, pixelated, low resolution, artifacts, compression noise, washed out colors, overexposed, underexposed, unrealistic lighting, unnatural reflections, jagged edges, aliasing, chromatic aberration, out of focus, poor_depth_of_field, oversaturated, desaturated, unnatural_shadows, unrealistic_fabric_texture, flat_shading, low_detail, lack_of_sharpness, warped_structure, unrealistic_motion_blur, artificial_appearance, messy_details, deformed_flag, asymmetry, poor_composition",
        num_inference_steps=70,
        guidance_scale=7.5,
        generator=generator
    ).images[0]

@app.route('/download_original')
def download_original():
    file_path = session.get('original_image_path')
    if file_path and os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name='original_image.png')
    return "Original image not found", 404

@app.route("/", methods=["GET", "POST"])
def home():
    variations, gifs, prompt, original_image_data = [], [], None, None
    collect_name, artist_name = None, None
    
    if request.method == "POST":
        options = {key: True for key in ['hue', 'brightness', 'contrast', 'posterize', 'neon', 'pixelate', 'invert', 'blur', 'sharpen', 'emboss', 'edge'] if key in request.form}
        
        num_gifs = int(request.form.get("num_gifs", 100))
        total_images = num_gifs * 4
        min_effects = math.ceil(math.log(total_images, 20))  # Required effects based on num_gifs
        min_effects = min(min_effects, 11)  # Cap at total available effects (11)
        
        # Enforce minimum number of effects
        selected_effects = sum(options.values())
        if selected_effects < min_effects:
            return render_template("index.html", 
                                 error=f"Please select at least {min_effects} post-processing effect(s) for {num_gifs} GIFs ({total_images} total images) to ensure uniqueness.")
        
        collect_name = request.form.get("collect_name", "")
        artist_name = request.form.get("artist_name", "")
        description = request.form.get("description", "")
        
        if num_gifs < 1 or num_gifs > 20000:
            return render_template("index.html", error="Number of GIFs must be between 1 and 100")
        
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            base_image = Image.open(file_path).convert("RGBA")
            print("Using uploaded image as base...")
            prompt = "Uploaded Image"
            session['original_image_path'] = file_path
        else:
            prompt = request.form.get("prompt", "")
            if not prompt:
                return render_template("index.html", error="Please provide a prompt or upload an image")
            base_image = generate_base_image(prompt)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'generated_original.png')
            base_image.save(file_path)
            session['original_image_path'] = file_path
        
        buffered = BytesIO()
        base_image.save(buffered, format="PNG")
        original_image_data = f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"
        
        variations, images, filenames = generate_nft_collection(base_image, options, prompt, num_gifs)
        if is_premium_user():
            gifs = generate_nfts_and_gifs(images, filenames, options, prompt, description, base_image, file_path, collect_name, artist_name)
        else:
            print("GIF creation requires premium access")
    
    return render_template("index.html", 
                         variations=variations, 
                         gifs=gifs, 
                         prompt=prompt, 
                         total_nfts=len(variations), 
                         original_image=original_image_data,
                         collect_name=collect_name,
                         artist_name=artist_name)

if __name__ == "__main__":
    app.secret_key = os.getenv("PRIVATE_KEY")
    app.run(debug=True, host="0.0.0.0", port=5000)