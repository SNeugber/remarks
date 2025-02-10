import base64
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image


SCREEN_DPI = 226
SCALE = 72.0 / SCREEN_DPI


def render_template(
    template_svg_path: Path, target_width: int, target_height: int
) -> Image.Image:
    tree = ET.parse(str(template_svg_path))
    root = tree.getroot()

    is_fixed_size = False  # I.e. doesn't keep repeating when scrolling down/sideways
    for child in root.iter():
        if "clip-path" in child.attrib:
            is_fixed_size = True
            break

    template_width = int(float(root.get("width").replace("pt", "")))
    template_height = int(float(root.get("height").replace("pt", "")))

    num_repetitions_vertical = (target_height + template_height - 1) // template_height
    num_repetitions_horizontal = (target_width + template_width - 1) // template_width

    combined_root = ET.Element("svg")
    combined_root.set("xmlns", "http://www.w3.org/2000/svg")
    combined_root.set("xmlns:xlink", "http://www.w3.org/1999/xlink")
    combined_root.set("width", str(target_width))
    combined_root.set("height", str(target_height))
    combined_root.set("viewBox", f"0 0 {target_width} {target_height}")

    # Try to tile the template (or a white background) to match target SVG
    for i in range(int(num_repetitions_vertical)):
        for j in range(int(num_repetitions_horizontal)):
            group = ET.SubElement(combined_root, "g")
            group.set(
                "transform",
                f"translate({j * template_width}, {i * template_height})",
            )
            if is_fixed_size and (i > 0 or j > 0):
                # Tile with white background, except for very first element, which should be the template
                rect = ET.SubElement(group, "rect")
                rect.set("x", "0")
                rect.set("y", "0")
                rect.set("width", f"{template_width}")
                rect.set("height", f"{template_height}")
                rect.set(
                    "style", "fill:rgb(100%,100%,100%);fill-opacity:1;stroke:none;"
                )
            else:
                # Deep copy the template's content into the group
                for child in root:
                    group.append(ET.fromstring(ET.tostring(child)))

    combined_svg_string = ET.tostring(combined_root, encoding="utf-8")
    svg_bytes = BytesIO(combined_svg_string)
    png_bytes = cairosvg.svg2png(
        file_obj=svg_bytes, output_width=target_width, output_height=target_height
    )
    return Image.open(BytesIO(png_bytes))


def add_template_to_svg(svg: Path, template_path: Path):
    tree = ET.parse(svg)
    root = tree.getroot()
    root.set("xmlns", "http://www.w3.org/2000/svg")
    root.set("xmlns:xlink", "http://www.w3.org/1999/xlink")

    width_pt = float(root.get("width"))
    width = unscale(width_pt)
    height_pt = float(root.get("height"))
    height = unscale(height_pt)
    x, y, _, _ = root.get("viewBox").split(" ")
    x = float(x)
    y = float(y)

    template_png = render_template(template_path, width, height)
    template_resized = template_png.resize((int(width_pt), int(height_pt)))
    buff = BytesIO()
    template_resized.save(buff, format="png")
    template_bytes = base64.b64encode(buff.getvalue()).decode("utf-8")

    image = ET.Element("image")
    image.set("x", f"{x}")
    image.set("y", f"{y}")
    image.set("width", f"{width_pt}")
    image.set("height", f"{height_pt}")
    image.set("xlink:href", f"data:image/png;base64,{template_bytes}")
    root.insert(0, image)

    with open(svg, "wb") as f:
        tree.write(f)


def unscale(size_pt):
    return size_pt / SCALE
