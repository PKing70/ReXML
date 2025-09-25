import sys              # system functions for arguments from command line
import re               # regular expressions to detect conf headers
import os               # os for file path processing
from lxml import etree  # xml element tree with which to build dita file

def parse_splunk_conf_spec(input_path, output_path):
    # Translates the file at input_path (must be a .conf.spec)
    # Writes the file at output_path, which should be XML with .xml extension instead of .spec
    # Conforms to an example Heretto topic: spexml_test_1.dita on splunk-dev.heretto
    # concept id is not dynamic yet (eg id="concept-5110"); using base file prefix as id (eg app.conf for app.conf.spec)
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()   # load the lines of the conf.spec file
    file_prefix = os.path.splitext(os.path.basename(input_path))[0]

    # Build the Heretto concept elements
    concept = etree.Element("concept", id=file_prefix) # use conf.spec name as id; see dita_tree below for attrib={"xml:lang": "en-us"}
    title = etree.SubElement(concept, "title")
    title.text = f"{file_prefix} (SpeXML)" 
    shortdesc = etree.SubElement(concept, "shortdesc")
    shortdesc.text = f"The following are the spec and example files for {file_prefix}."
    prolog = etree.SubElement(concept, "prolog")
    author = etree.SubElement(prolog, "author", attrib={"translate": "no", "type": "creator"})
    author.text = "SpeXML did this"
    metadata = etree.SubElement(prolog, "metadata")
    keywords = etree.SubElement(metadata, "keywords")
    conbody = etree.SubElement(concept, "conbody")
    
    section = etree.SubElement(conbody, "section")
    title_section = etree.SubElement(section, "title", attrib={"outputclass": "h2"})
    title_section.text = file_prefix + ".spec"    
    
    # Build the conf.spec sections
    current_section = None
    codeblock = None

    for line in lines:
        line = line.strip()
        
        # Detect stanza headers
        if re.match(r"^\[.*\]$", line):
            current_section = etree.SubElement(conbody, "section")
            section_title = etree.SubElement(current_section, "title")
            section_title.text = line.strip("[]")

            # Create a new <codeblock> for this section
            codeblock = etree.SubElement(current_section, "codeblock")
            # Placeholder for TBD outputclass
            # codeblock.set("outputclass", "good-output")

        # Add settings and comment lines inside the <codeblock>
        if current_section is not None and codeblock is not None:
            if line:
                codeblock.text = (codeblock.text or "") + line + "\n"

    # Save as DITA XML
    dita_tree = etree.ElementTree(concept)

    # xml:lang is special; see http://ditanauts.org/2012/05/04/python-lxml-and-setting-xmllang/
    root = dita_tree.getroot()
    attr = root.attrib
    attr['{http://www.w3.org/XML/1998/namespace}lang'] = "en-us"

    dita_tree.write(output_path, pretty_print=True, xml_declaration=True, encoding="UTF-8")
    print(f"Translated: {input_path} -> {output_path}")

def process_directory(directory):
    # Processes all .conf.spec files in the specified directory
    for filename in os.listdir(directory):
        if filename.endswith(".conf.spec"):
            input_path = os.path.join(directory, filename)
            output_path = os.path.join(directory, f"{os.path.splitext(filename)[0]}.xml")
            parse_splunk_conf_spec(input_path, output_path)

def main():
    # Processes command line args, requires:
    # spexml.py <input_file>
    # or
    # spexml.py -batch <directory>
    # Outputs translation to output_file
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python spexml.py <file.conf.spec>   # Translate a single file from the current directory")
        print("  python spexml.py -batch <directory> # Translate all .conf.spec files in a directory")
        sys.exit(1)        

    if sys.argv[1] == "-batch":
        if len(sys.argv) < 3:
            print("Error: Missing directory path for batch mode.")
            sys.exit(1)
        directory = sys.argv[2]
        process_directory(directory)
    else:
        input_file = sys.argv[1]
        output_file = f"{os.path.splitext(input_file)[0]}.xml"
        parse_splunk_conf_spec(input_file, output_file)

main()