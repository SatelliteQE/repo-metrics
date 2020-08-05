# module to handle file IO functions, to keep them out of the click command module
import json


def write_to_output(output_filename, content):
    with open(output_filename, "w") as output_file:
        json.dump(content, output_file, indent=2)
