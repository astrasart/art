from flask import Flask, request, render_template
from diffusers import StableDiffusionPipeline
import torch
from io import BytesIO
import base64

# Initialize Flask app
app = Flask(__name__)

# Load Stable Diffusion model (once at startup)
print("Torch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
device = "mps" if torch.backends.mps.is_available() else "cpu"  # Use MPS on M1/M2 Macs if available
model_id = "runwayml/stable-diffusion-v1-5"
print("Loading model...")
pipe = StableDiffusionPipeline.from_pretrained(model_id)
pipe = pipe.to(device)
print(f"Model loaded on {device}")

# Home route with form and image display
@app.route("/", methods=["GET", "POST"])
def home():
    image_data = None
    prompt = None
    
    if request.method == "POST":
        prompt = request.form.get("prompt")
        if prompt:
            print(f"Generating image for: {prompt}")
            image = pipe(prompt).images[0]
            
            # Convert image to base64 for display
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            image_data = f"data:image/png;base64,{img_str}"
    
    return render_template("index.html", image_data=image_data, prompt=prompt)

# Run the app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)