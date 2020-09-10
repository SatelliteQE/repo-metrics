# module to handle file IO functions, to keep them out of the click command module
from config import METRICS_OUTPUT


def write_to_output(output_filename, content):
    """output_filename should be a pathlib Path object"""
    METRICS_OUTPUT.mkdir(parents=True, exist_ok=True)
    output_filename.write_text(content)
