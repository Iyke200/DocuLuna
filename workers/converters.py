import logging
from pdf2docx import Converter
from PyPDF2 import PdfReader
import os

logger = logging.getLogger(__name__)

def pdf_to_docx(input_path: str, output_path: str, password: str = None):
    try:
        pdf = PdfReader(input_path)
        if pdf.is_encrypted:
            if not password:
                raise ValueError("Encrypted PDF requires a password")
            pdf.decrypt(password)
        cv = Converter(input_path)
        cv.convert(output_path)
        cv.close()
        logger.info("Converted %s to %s", input_path, output_path)
    except Exception as e:
        logger.error("Failed to convert %s: %s", input_path, e)
        raise