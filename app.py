import ezdxf
import svgwrite
import cv2
import numpy as np
import random
from flask import Flask, request, send_file, render_template, jsonify
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

DEFAULT_WIDTH = 1000  
DEFAULT_HEIGHT = 2000  

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate_dxf", methods=["POST"])
def generate_dxf():
    if "image" not in request.files:
        return "No file uploaded", 400

    file = request.files["image"]
    pattern_type = request.form.get("pattern_type", "staggered")
    spacing = int(request.form.get("spacing", 50))  
    enable_colors = request.form.get("enable_colors") == "on"  

    img_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(img_path)

    dxf_filename = "perforation.dxf"
    dxf_path = os.path.join(OUTPUT_FOLDER, dxf_filename)

    process_image_and_generate_dxf(img_path, dxf_path, pattern_type, spacing, enable_colors)

    svg_filename = "perforation.svg"
    svg_path = os.path.join(OUTPUT_FOLDER, svg_filename)
    convert_dxf_to_svg(dxf_path, svg_path, enable_colors)

    return jsonify({
        "dxf": f"/download/{dxf_filename}",
        "svg": f"/preview_svg/{svg_filename}"
    })

def process_image_and_generate_dxf(img_path, dxf_path, pattern_type, spacing, enable_colors):
    image = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    image = cv2.resize(image, (DEFAULT_WIDTH // spacing, DEFAULT_HEIGHT // spacing))

    unique_sizes = list(range(2, 11))  
    colors = {size: (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)) for size in unique_sizes}

    doc = ezdxf.new()
    msp = doc.modelspace()

    if enable_colors:
        for size in unique_sizes:
            doc.layers.add(name=f"HOLE_{size}", color=random.randint(1, 255))  

    for row in range(image.shape[0]):
        for col in range(image.shape[1]):
            hole_size = np.interp(image[row, col], [0, 255], [10, 2])  
            hole_size = int(round(hole_size))  
            hole_radius = hole_size / 2

            x = col * spacing
            y = row * spacing

            if pattern_type == "staggered" and row % 2 == 1:
                x += spacing // 2  

            layer_name = f"HOLE_{hole_size}" if enable_colors else "DEFAULT"
            msp.add_circle((x, -y), hole_radius, dxfattribs={"layer": layer_name})

    doc.saveas(dxf_path)

def convert_dxf_to_svg(dxf_path, svg_path, enable_colors):
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    min_x, min_y, max_x, max_y = float("inf"), float("inf"), float("-inf"), float("-inf")

    for entity in msp.query("CIRCLE"):
        center = entity.dxf.center
        radius = entity.dxf.radius
        min_x = min(min_x, center.x - radius)
        min_y = min(min_y, center.y - radius)
        max_x = max(max_x, center.x + radius)
        max_y = max(max_y, center.y + radius)

    width = max_x - min_x
    height = max_y - min_y

    dwg = svgwrite.Drawing(svg_path, profile='tiny', size=(width, height), viewBox=f"{min_x} {min_y} {width} {height}")

    for entity in msp.query("CIRCLE"):
        center = entity.dxf.center
        radius = entity.dxf.radius
        color = f"rgb({random.randint(0,255)},{random.randint(0,255)},{random.randint(0,255)})" if enable_colors else "black"
        dwg.add(dwg.circle(center=(center.x, -center.y), r=radius, stroke=color, fill="none"))

    dwg.save()

@app.route("/preview_svg/<filename>")
def preview_svg(filename):
    return send_file(os.path.join(OUTPUT_FOLDER, filename), mimetype="image/svg+xml")

@app.route("/download/<filename>")
def download_file(filename):
    return send_file(os.path.join(OUTPUT_FOLDER, filename), as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
