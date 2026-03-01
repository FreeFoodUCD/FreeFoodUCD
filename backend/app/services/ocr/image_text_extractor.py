"""
OCR utility for extracting text from Instagram post images.
Uses pytesseract for text extraction.
"""

import logging
from typing import Optional
import requests
from PIL import Image, ImageFilter
from io import BytesIO
import pytesseract

logger = logging.getLogger(__name__)


class ImageTextExtractor:
    """Extract text from images using OCR."""
    
    def __init__(self):
        """Initialize the OCR extractor."""
        pass
    
    def extract_text_from_url(self, image_url: str) -> Optional[str]:
        """
        Download image from URL and extract text using OCR.
        
        Args:
            image_url: URL of the image to process
            
        Returns:
            Extracted text or None if extraction fails
        """
        try:
            # Download image
            logger.info(f"Downloading image from {image_url}")
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            # Open image
            image = Image.open(BytesIO(response.content))

            # Preprocess for better tesseract accuracy on colourful/stylised images
            w, h = image.size
            image = image.resize((w * 2, h * 2), Image.LANCZOS)  # 2× upscale
            image = image.convert('L')                             # grayscale
            image = image.filter(ImageFilter.SHARPEN)              # sharpen edges

            # Extract text using pytesseract
            text = pytesseract.image_to_string(image, config='--psm 11')

            # Clean up text
            text = text.strip()

            # Discard short noise (stray letters/punctuation from OCR artefacts)
            if len(text) < 8:
                logger.warning("No text extracted from image")
                return None

            logger.info(f"Extracted {len(text)} characters from image")
            logger.debug(f"OCR text: {text[:200]}...")
            return text
                
        except requests.RequestException as e:
            logger.error(f"Failed to download image: {e}")
            return None
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return None
    
    def extract_text_from_urls(self, image_urls: list[str]) -> tuple[str, bool]:
        """
        Extract text from multiple images and combine.

        Returns:
            (combined_text, low_yield) where low_yield=True if Tesseract returned
            fewer than 20 characters total — a signal that a vision LLM should be tried.
        """
        all_text = []

        for url in image_urls:
            text = self.extract_text_from_url(url)
            if text:
                all_text.append(text)

        combined = "\n\n".join(all_text)
        low_yield = len(combined.strip()) < 20
        return combined, low_yield


# Made with Bob