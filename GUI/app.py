from flask import Flask, render_template, request, send_file
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def remove_trailing_numbers(filename):
    """Remove trailing numbers from filename before extension."""
    # Split into name and extension
    name, ext = os.path.splitext(filename)
    
    # Remove trailing digits from the name
    # This regex removes numbers at the end of the string
    name_without_numbers = re.sub(r'\d+$', '', name)
    
    # If removing numbers results in empty string, use original name
    if name_without_numbers == '':
        name_without_numbers = name
    
    return name_without_numbers + ext


def process_files(file1_path, file2_path):
    """Read two files, compare their lines, and generate XML mapping"""
    
    # Read both files
    with open(file1_path, 'r') as f1:
        lines1 = [line.rstrip('\n') for line in f1.readlines()]
    
    with open(file2_path, 'r') as f2:
        lines2 = [line.rstrip('\n') for line in f2.readlines()]
    
    # Create XML structure
    root = ET.Element("line_mapping")
    
    # Add metadata
    metadata = ET.SubElement(root, "metadata")
    ET.SubElement(metadata, "timestamp").text = "2024-01-01 12:00:00"
    ET.SubElement(metadata, "tool").text = "File Line Mapper"
    
    # Add file information
    files_elem = ET.SubElement(root, "files")
    
    file1_elem = ET.SubElement(files_elem, "file")
    file1_elem.set("id", "1")
    file1_elem.set("name", os.path.basename(file1_path))
    file1_elem.set("path", file1_path)
    file1_elem.set("line_count", str(len(lines1)))
    
    file2_elem = ET.SubElement(files_elem, "file")
    file2_elem.set("id", "2")
    file2_elem.set("name", os.path.basename(file2_path))
    file2_elem.set("path", file2_path)
    file2_elem.set("line_count", str(len(lines2)))
    
    # Create line mappings
    mappings_elem = ET.SubElement(root, "mappings")
    
    # Determine maximum number of lines to process
    max_lines = max(len(lines1), len(lines2))
    
    for i in range(max_lines):
        mapping_elem = ET.SubElement(mappings_elem, "mapping")
        mapping_elem.set("index", str(i + 1))
        
        # File 1 line (if exists)
        line1_elem = ET.SubElement(mapping_elem, "source_line")
        line1_elem.set("file_id", "1")
        line1_elem.set("file_name", os.path.basename(file1_path))
        line1_elem.set("line_number", str(i + 1) if i < len(lines1) else "0")
        if i < len(lines1):
            line1_elem.text = lines1[i]
        else:
            line1_elem.set("status", "missing")
            line1_elem.text = ""
        
        # File 2 line (if exists)
        line2_elem = ET.SubElement(mapping_elem, "target_line")
        line2_elem.set("file_id", "2")
        line2_elem.set("file_name", os.path.basename(file2_path))
        line2_elem.set("line_number", str(i + 1) if i < len(lines2) else "0")
        if i < len(lines2):
            line2_elem.text = lines2[i]
        else:
            line2_elem.set("status", "missing")
            line2_elem.text = ""
        
        # Add comparison result
        comparison = ET.SubElement(mapping_elem, "comparison")
        if i < len(lines1) and i < len(lines2):
            if lines1[i] == lines2[i]:
                comparison.set("result", "exact_match")
                comparison.set("confidence", "100")
                comparison.text = "Lines are identical"
            elif lines1[i].strip() == lines2[i].strip():
                comparison.set("result", "similar")
                comparison.set("confidence", "90")
                comparison.text = "Lines differ only in whitespace"
            else:
                comparison.set("result", "different")
                comparison.set("confidence", "0")
                comparison.text = "Lines have different content"
        else:
            comparison.set("result", "unpaired")
            comparison.set("confidence", "0")
            comparison.text = "No corresponding line in other file"
    
    # Add summary statistics
    summary = ET.SubElement(root, "summary")
    
    exact_count = sum(1 for i in range(min(len(lines1), len(lines2))) 
                     if i < len(lines1) and i < len(lines2) and lines1[i] == lines2[i])
    similar_count = sum(1 for i in range(min(len(lines1), len(lines2))) 
                       if i < len(lines1) and i < len(lines2) and 
                       lines1[i].strip() == lines2[i].strip() and lines1[i] != lines2[i])
    different_count = sum(1 for i in range(min(len(lines1), len(lines2))) 
                         if i < len(lines1) and i < len(lines2) and 
                         lines1[i].strip() != lines2[i].strip())
    
    ET.SubElement(summary, "total_lines_compared").text = str(max_lines)
    ET.SubElement(summary, "exact_matches").text = str(exact_count)
    ET.SubElement(summary, "similar_matches").text = str(similar_count)
    ET.SubElement(summary, "differences").text = str(different_count)
    ET.SubElement(summary, "unpaired_lines").text = str(abs(len(lines1) - len(lines2)))
    
    if max_lines > 0:
        similarity_score = ((exact_count + similar_count * 0.9) / max_lines) * 100
        ET.SubElement(summary, "similarity_score").text = f"{similarity_score:.1f}%"
    else:
        ET.SubElement(summary, "similarity_score").text = "0%"
    
    # Create pretty XML
    xml_str = ET.tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ")
    
    return pretty_xml


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
            
            # Generate output filename from first file's name WITHOUT trailing numbers
            first_filename = uploaded_files[0].filename
            name_without_ext = os.path.splitext(first_filename)[0]
            
            # Remove any trailing numbers from the name
            name_without_numbers = re.sub(r'\d+$', '', name_without_ext)
            
            # If removing numbers results in empty string, use original name
            if name_without_numbers == '':
                name_without_numbers = name_without_ext
            
            # Generate XML content
            xml_content = process_files(file_paths[0], file_paths[1])
            
            # Save XML file
            output_filename = f"{name_without_numbers}.xml"
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)
            
            with open(output_path, 'w') as f:
                f.write(xml_content)
            
            output_file = output_filename
            
            # Clean up uploaded files
            for file_path in file_paths:
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            message = f"Successfully compared '{uploaded_files[0].filename}' and '{uploaded_files[1].filename}'"
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
        as_attachment=True,
        mimetype='application/xml'
    )


@app.route("/view/<filename>")
def view_xml(filename):
    """Route to view XML content in browser"""
    filepath = os.path.join(OUTPUT_FOLDER, filename)
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            xml_content = f.read()
        return f'<pre>{xml_content}</pre>'
    return "File not found"


if __name__ == "__main__":
    app.run(debug=True)