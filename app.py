from flask import Flask, render_template, request, send_file, jsonify
import ezdxf
import numpy as np
import io

app = Flask(__name__)

# Function to create a perforation pattern and generate DXF
def create_dxf(holes, width, height, filename="output.dxf"):
    doc = ezdxf.new()
    msp = doc.modelspace()

    # Define size-based color mapping
    size_layers = {
        "small": {"range": (1, 5), "color": 1, "layer": "Small_Holes"},  # Red
        "medium": {"range": (6, 10), "color": 3, "layer": "Medium_Holes"},  # Green
        "large": {"range": (11, 50), "color": 5, "layer": "Large_Holes"}  # Blue
    }

    # Create layers
    for key, data in size_layers.items():
        doc.layers.add(name=data["layer"], color=data["color"])

    # Draw boundary
    msp.add_lwpolyline([(0, 0), (width, 0), (width, height), (0, height), (0, 0)], close=True, dxfattribs={"layer": "Boundary"})

    # Generate circles in layers
    for hole in holes:
        x, y, size = hole
        if 0 <= x <= width and 0 <= y <= height:
            for key, data in size_layers.items():
                if data["range"][0] <= size <= data["range"][1]:
                    msp.add_circle(center=(x, y), radius=size / 2, dxfattribs={"layer": data["layer"], "color": data["color"]})
                    break

    # Save DXF to memory
    buffer = io.BytesIO()
    doc.write(buffer)
    buffer.seek(0)
    return buffer

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate_dxf", methods=["POST"])
def generate_dxf():
    data = request.json
    width = float(data.get("width", 500))
    height = float(data.get("height", 500))
    num_holes = 100

    # Generate random perforation holes within bounds
    holes = np.random.uniform(0, min(width, height), (num_holes, 3))  # (x, y, size)
    holes[:, 2] = np.random.randint(3, 12, num_holes)  # Random hole sizes

    dxf_buffer = create_dxf(holes, width, height)
    return send_file(dxf_buffer, download_name="perforation.dxf", as_attachment=True)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3000, debug=True)

