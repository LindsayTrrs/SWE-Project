from flask import Flask, render_template, request, send_file
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def process_files(file1_path, file2_path, output_filename):
    """Read two files, compare their lines, and generate XML mapping"""
    
    # Read both files
    with open(file1_path, 'r') as f1:
        lines1 = [line.rstrip('\n') for line in f1.readlines()]
    
    with open(file2_path, 'r') as f2:
        lines2 = [line.rstrip('\n') for line in f2.readlines()]
    
    # Create XML structure
    root = ET.Element("line_mapping")
    
    # Add file information
    files_elem = ET.SubElement(root, "files")
    
    file1_elem = ET.SubElement(files_elem, "file")
    file1_elem.set("name", os.path.basename(file1_path))
    file1_elem.set("line_count", str(len(lines1)))
    
    file2_elem = ET.SubElement(files_elem, "file")
    file2_elem.set("name", os.path.basename(file2_path))
    file2_elem.set("line_count", str(len(lines2)))
    
    # Create line mappings
    mappings_elem = ET.SubElement(root, "mappings")
    
    # Determine maximum number of lines to process
    max_lines = max(len(lines1), len(lines2))
    
    for i in range(max_lines):
        mapping_elem = ET.SubElement(mappings_elem, "mapping")
        mapping_elem.set("index", str(i + 1))
        
        # File 1 line (if exists)
        line1_elem = ET.SubElement(mapping_elem, "line")
        line1_elem.set("file", os.path.basename(file1_path))
        line1_elem.set("number", str(i + 1) if i < len(lines1) else "N/A")
        if i < len(lines1):
            line1_elem.text = lines1[i]
        else:
            line1_elem.text = "[No corresponding line]"
        
        # File 2 line (if exists)
        line2_elem = ET.SubElement(mapping_elem, "line")
        line2_elem.set("file", os.path.basename(file2_path))
        line2_elem.set("number", str(i + 1) if i < len(lines2) else "N/A")
        if i < len(lines2):
            line2_elem.text = lines2[i]
        else:
            line2_elem.text = "[No corresponding line]"
        
        # Add comparison result
        if i < len(lines1) and i < len(lines2):
            if lines1[i] == lines2[i]:
                mapping_elem.set("match", "exact")
            elif lines1[i].strip() == lines2[i].strip():
                mapping_elem.set("match", "similar")
            else:
                mapping_elem.set("match", "different")
        else:
            mapping_elem.set("match", "missing")
    
    # Create pretty XML
    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ")
    
    # Write to output file
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    with open(output_path, 'w') as f:
        f.write(pretty_xml)
    
    return output_path


@app.route("/", methods=["GET", "POST"])
def index():
    output_file = None
    message = None
    message_type = "error"

    if request.method == "POST":
        uploaded_files = request.files.getlist("file")
        
        # Check if exactly 2 files are uploaded
        if len(uploaded_files) != 2:
            message = "Please upload exactly two files."
        elif any(f.filename == "" for f in uploaded_files):
            message = "Both files must be selected."
        else:
            # Save uploaded files
            file_paths = []
            for uploaded_file in uploaded_files:
                input_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
                uploaded_file.save(input_path)
                file_paths.append(input_path)
            
            # Generate output filename from first file's name
            first_filename = uploaded_files[0].filename
            name_without_ext = os.path.splitext(first_filename)[0]
            output_filename = f"{name_without_ext}.xml"
            
            # Process files and generate XML
            output_path = process_files(file_paths[0], file_paths[1], output_filename)
            output_file = output_filename
            
            message = f"Successfully processed {uploaded_files[0].filename} and {uploaded_files[1].filename}"
            message_type = "success"

    return render_template(
        "index.html",
        output_file=output_file,
        message=message,
        message_type=message_type
    )

@app.route("/download/<filename>")
def download(filename):
    return send_file(
        os.path.join(OUTPUT_FOLDER, filename),
        as_attachment=True
    )

if __name__ == "__main__":
    app.run(debug=True)