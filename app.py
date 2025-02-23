from flask import Flask, request, send_file, render_template
import cv2
import numpy as np
import ezdxf
import os

app = Flask(__name__)

# Ensure upload folder exists
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate_dxf", methods=["POST"])
def generate_dxf():
    if "image" not in request.files:
        return "No file uploaded", 400

    file = request.files["image"]
    pattern_type = request.form.get("pattern_type", "staggered")

    # Save the image
    img_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(img_path)

    # Process image for perforation
    dxf_path = process_image_to_dxf(img_path, pattern_type)

    # Send DXF file to user
    return send_file(dxf_path, as_attachment=True)

def process_image_to_dxf(image_path, pattern_type):
    # Load image in grayscale
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    height, width = img.shape

    # Create a DXF file
    doc = ezdxf.new()
    msp = doc.modelspace()

    # Define perforation parameters
    hole_size_min = 2
    hole_size_max = 10

    # Loop through pixels to generate perforation pattern
    for y in range(0, height, 20):
        for x in range(0, width, 20):
            brightness = img[y, x]
            hole_size = np.interp(brightness, [0, 255], [hole_size_max, hole_size_min])

            if pattern_type == "staggered" and (y // 20) % 2 == 1:
                x += 10  # Offset for staggered pattern

            msp.add_circle((x, -y), hole_size / 2)

    # Save DXF file
    dxf_path = "perforation.dxf"
    doc.saveas(dxf_path)
    return dxf_path

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
