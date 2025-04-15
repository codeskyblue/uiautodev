#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Created on Thu May 09 2024 11:33:17 by codeskyblue
"""


import io
import locale
import logging
from typing import List

from PIL import Image

from uiautodev.model import Node, OCRNode

logger = logging.getLogger(__name__)

def is_chinese_language() -> bool:
    language_code, _ = locale.getdefaultlocale()
    
    # Check if the language code starts with 'zh' (Chinese)
    if language_code and language_code.startswith('zh'):
        return True
    else:
        return False
    
    
def get_webpage_url() -> str:
    web_url = "https://uiauto.dev"
    if is_chinese_language():
        web_url = "https://uiauto.devsleep.com"
    return web_url


def convert_bytes_to_image(byte_data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(byte_data))


def ocr_image(image: Image.Image) -> List[OCRNode]:
    # Placeholder for OCR implementation
    w, h = image.size
    try:
        from ocrmac import ocrmac
    except ImportError:
        logger.error("OCR is not supported on this platform")
        return []
    result = ocrmac.OCR(image).recognize()
    nodes = []
    for index, (text, confidence, pbounds) in enumerate(result):
        print(f"OCR result: {text}, confidence: {confidence}, bounds: {pbounds}")
        # bounds = int(pbounds[0]*w), int(pbounds[1]*h), int(pbounds[2]*w), int(pbounds[3]*h)
        nodes.append(OCRNode(key=str(index), name=text, bounds=pbounds, confidence=confidence))
    return nodes