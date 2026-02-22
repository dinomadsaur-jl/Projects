import json
import base64
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

def select_svg_files():
    """Open a file dialog to select multiple SVG files."""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    file_paths = filedialog.askopenfilenames(
        title="Select SVG Files",
        filetypes=[("SVG files", "*.svg")],
        initialdir=Path.home()
    )
    return list(file_paths) if file_paths else []

def create_drawio_library(svg_paths: list[str], output_file: str = "selected_svgs_library.drawio"):
    """Generate a draw.io library from selected SVGs."""
    entries = []
    
    for file_path in svg_paths:
        p = Path(file_path)
        if p.suffix.lower() != '.svg':
            continue
        
        with open(p, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode('ascii')
        
        title = p.stem.replace("_", " ").title()
        
        entry = {
            "data": f"data:image/svg+xml;base64,{b64}",
            "title": title,
            "aspect": "fixed",
            "w": 100, "h": 100,
            "style": "image;imageAspect=1;aspect=fixed;"
        }
        entries.append(entry)
    
    if not entries:
        print("No SVGs selected. Library not created.")
        return
    
    library = {
        "title": "Selected SVGs Library",
        "items": entries
    }
    
    # Wrap in mxlibrary XML
    xml_content = f'<mxlibrary>{json.dumps(library, indent=2)}</mxlibrary>'
    
    Path(output_file).write_text(xml_content, encoding="utf-8")
    print(f"Created library with {len(entries)} SVGs → {output_file}")

def create_a4_report_drawio(output_file: str = "a4_report.drawio", num_pages: int = 3, side_by_side: bool = True):
    """Generate a draw.io file simulating an A4 report with multiple 'pages' side by side.
    
    - A4 size: approx 827x1169 units (8.27in x 11.69in at 100ppi).
    - Each 'page' is a rectangle with a textbox inside, fitting with 20-unit margins.
    - If side_by_side=True, arranges horizontally on a large canvas (instead of vertically).
    """
    a4_width = 827
    a4_height = 1169
    margin = 20  # Inner margin for textbox
    spacing = 50  # Space between pages
    
    if side_by_side:
        total_width = num_pages * a4_width + (num_pages - 1) * spacing
        total_height = a4_height
        page_scale = 1  # No scaling needed
    else:
        total_width = a4_width
        total_height = num_pages * a4_height + (num_pages - 1) * spacing
        page_scale = 1
    
    # mxGraphModel settings for A4 (but custom total size)
    model_attrs = f'page="1" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" pageWidth="{total_width}" pageHeight="{total_height}" math="0" shadow="0"'
    
    cells = []
    x, y = 0, 0
    
    for i in range(num_pages):
        # Page border (rectangle simulating A4 page)
        border_style = "rounded=0;whiteSpace=wrap;html=1;strokeColor=#000000;strokeWidth=1;fillColor=none;"
        border_cell = f'''
        <mxCell id="{2 + i*2}" value="" style="{border_style}"
         vertex="1" parent="1">
          <mxGeometry x="{x}" y="{y}" width="{a4_width}" height="{a4_height}" as="geometry"/>
        </mxCell>'''
        
        # Textbox inside with margins (fits A4 minus margins)
        textbox_style = "text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=top;whiteSpace=wrap;overflow=hidden;"
        textbox_cell = f'''
        <mxCell id="{3 + i*2}" value="Your report text here...&#xa;&#xa;Add more content as needed."
         style="{textbox_style}"
         vertex="1" parent="1">
          <mxGeometry x="{x + margin}" y="{y + margin}" width="{a4_width - 2*margin}" height="{a4_height - 2*margin}" as="geometry"/>
        </mxCell>'''
        
        cells.extend([border_cell, textbox_cell])
        
        if side_by_side:
            x += a4_width + spacing
        else:
            y += a4_height + spacing
    
    xml = f'''<mxfile host="app.diagrams.net" modified="2023-01-01T00:00:00.000Z" agent="Mozilla/5.0" etag="abc" version="20.0.0" type="device">
  <diagram id="diagram1" name="Page-1">
    <mxGraphModel {model_attrs}>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        {''.join(cells)}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''
    
    Path(output_file).write_text(xml, encoding="utf-8")
    print(f"Created A4 report diagram → {output_file}")
    print("Note: Open in draw.io. The 'pages' are arranged side by side on a large canvas.")
    print("To print as separate A4 pages, you may need to export or adjust print settings.")

# Main execution
svg_files = select_svg_files()
if svg_files:
    create_drawio_library(svg_files)

create_a4_report_drawio(side_by_side=True)  # Generate the A4 report separately