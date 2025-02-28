import ezdxf
import cv2
import numpy as np
from flask import Flask, request, send_file, render_template, jsonify
import os
import threading
import logging
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Shared variable to track progress
progress = {"value": 0, "error": None}
lock = threading.Lock()  # Prevent conflicts when updating progress

def process_image_and_generate_dxf(img_path, dxf_path, pattern_type, hole_sizes, horizontal_spacing, vertical_spacing, enable_color):
    try:
        # Read and process the image
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)  # Read image in grayscale
        if img is None:
            raise ValueError("Failed to load image")

        # Normalize image intensity to range [0, 1]
        img_normalized = cv2.normalize(img.astype('float'), None, 0.0, 1.0, cv2.NORM_MINMAX)

        # Create a new DXF document
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()

        # Create layers for each hole size if enable_color is True
        if enable_color:
            layers = {}
            colors = [1, 2, 3, 4, 5, 6, 7]  # DXF color codes (1=red, 2=yellow, 3=green, etc.)
            for i, size in enumerate(hole_sizes):
                layer_name = f"HOLE_SIZE_{size}"
                doc.layers.new(name=layer_name, dxfattribs={"color": colors[i % len(colors)]})
                layers[size] = layer_name

        # Get image dimensions
        height, width = img.shape[:2]

        # Calculate total rows for progress tracking
        total_rows = height // vertical_spacing

        # Generate holes uniformly across the image
        for row in range(total_rows):
            if pattern_type == "staggered":
                offset = (row % 2) * horizontal_spacing // 2  # Staggered offset
            else:
                offset = 0  # No offset for non-staggered

            for x in range(offset, width, horizontal_spacing):
                # Get the intensity at the hole location
                y = row * vertical_spacing
                intensity = img_normalized[y, x]

                # Select hole size based on intensity (darker = larger holes)
                hole_size = hole_sizes[int(intensity * (len(hole_sizes) - 1))]  # Map intensity to hole size

                # Place a hole at every location (flip y-coordinate to fix upside-down issue)
                if enable_color:
                    # Add the hole to the corresponding layer
                    msp.add_circle((x, height - y), radius=hole_size / 2, dxfattribs={"layer": layers[hole_size]})
                else:
                    # Add the hole without layer/color
                    msp.add_circle((x, height - y), radius=hole_size / 2)

            # Update progress after each row
            with lock:
                progress["value"] = int((row + 1) / total_rows * 100)

        # Save the DXF file
        doc.saveas(dxf_path)

        # Clean up uploaded image file
        os.remove(img_path)

    except Exception as e:
        logger.error(f"Error in process_image_and_generate_dxf: {str(e)}")
        with lock:
            progress["error"] = str(e)
        raise

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/progress")
def get_progress():
    try:
        with lock:
            return jsonify(progress)
    except Exception as e:
        logger.error(f"Error fetching progress: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/generate_dxf", methods=["POST"])
def generate_dxf():
    try:
        if "image" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["image"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        # Validate file extension
        allowed_extensions = {"jpg", "jpeg", "png"}
        if not file.filename.lower().endswith(tuple(allowed_extensions)):
            return jsonify({"error": "Invalid file type. Only JPG, JPEG, and PNG files are allowed."}), 400

        # Secure filename to prevent path traversal attacks
        filename = secure_filename(file.filename)
        img_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(img_path)

        # Generate DXF filename based on uploaded image name
        dxf_filename = os.path.splitext(filename)[0] + ".dxf"
        dxf_path = os.path.join(OUTPUT_FOLDER, dxf_filename)

        # Validate hole sizes
        hole_sizes = request.form.getlist("hole_sizes[]")
        hole_sizes = [int(size) for size in hole_sizes if size.isdigit() and int(size) > 0]
        if not hole_sizes:
            return jsonify({"error": "No valid hole sizes provided"}), 400
        if len(hole_sizes) > 10:
            return jsonify({"error": "You can enter up to 10 hole sizes"}), 400

        # Get pattern type
        pattern_type = request.form.get("pattern_type")

        # Validate spacing based on pattern type
        if pattern_type == "staggered":
            stagger_pitch = int(request.form.get("stagger_pitch", 50))
            gauge_distance = int(request.form.get("gauge_distance", 50))
            if stagger_pitch <= 0 or gauge_distance <= 0:
                return jsonify({"error": "Stagger pitch and gauge distance must be positive numbers"}), 400
            horizontal_spacing = stagger_pitch * 2
            vertical_spacing = gauge_distance
        else:
            horizontal_spacing = int(request.form.get("horizontal_spacing", 50))
            vertical_spacing = int(request.form.get("vertical_spacing", 50))
            if horizontal_spacing <= 0 or vertical_spacing <= 0:
                return jsonify({"error": "Horizontal and vertical spacing must be positive numbers"}), 400

        enable_color = request.form.get("enable_color") == "on"

        # Reset progress
        with lock:
            progress["value"] = 0
            progress["error"] = None

        # Generate DXF in a separate thread
        threading.Thread(target=process_image_and_generate_dxf, args=(
            img_path, dxf_path, pattern_type, hole_sizes, horizontal_spacing, vertical_spacing, enable_color
        )).start()

        return jsonify({
            "dxf": f"/download/{dxf_filename}"
        })
    except Exception as e:
        logger.error(f"Error generating DXF: {str(e)}")
        return jsonify({"error": f"An error occurred while generating the DXF file: {str(e)}"}), 500

@app.route("/download/<filename>")
def download_file(filename):
    return send_file(os.path.join(OUTPUT_FOLDER, filename), as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)