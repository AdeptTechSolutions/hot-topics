import asyncio
import base64
import os
import re
from io import BytesIO
from typing import Optional

from google import genai
from PIL import Image

from config import Config

os.makedirs("images", exist_ok=True)


class ImageGenerator:
    """Generates images for ad campaigns using the Gemini API."""

    def __init__(self, config: Config):
        self.api_key = config.GEMINI_API_KEY
        self.model_name = config.GEMINI_IMAGE_MODEL
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Error initializing Gemini Image client: {e}")

    def is_available(self) -> bool:
        """Check if the image generation client is available."""
        return self.client is not None

    def _sanitize_filename(self, text: str) -> str:
        """Sanitizes a string to be used as a valid filename."""
        text = re.sub(r"[^\w\s-]", "", text).strip().lower()
        text = re.sub(r"[-\s]+", "-", text)
        return text[:50]

    async def generate_image(self, prompt: str, filename_prefix: str) -> Optional[str]:
        """
        Generates an image based on a prompt and saves it.

        Args:
            prompt: The text prompt for image generation.
            filename_prefix: A string to use for the output filename.

        Returns:
            The file path of the generated image, or None on failure.
        """
        if not self.is_available():
            print("Image generator is not available.")
            return None

        print(f"🎨 Generating image for prompt: '{prompt[:50]}...'")

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"]
                ),
            )

            image_part = None
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image_part = part
                    break

            if not image_part:
                print("Gemini API did not return an image.")
                if response.candidates and response.candidates[0].content.parts:
                    text_part = response.candidates[0].content.parts[0].text
                    print(f"Gemini Response Text: {text_part}")
                return None

            image_data = image_part.inline_data.data
            image = Image.open(BytesIO(image_data))

            sanitized_prefix = self._sanitize_filename(filename_prefix)
            random_suffix = base64.b16encode(os.urandom(4)).decode().lower()
            filename = f"{sanitized_prefix}-{random_suffix}.png"
            filepath = os.path.join("images", filename)

            image.save(filepath)
            print(f"Image saved to {filepath}")
            return filepath

        except Exception as e:
            print(f"An error occurred during image generation: {e}")
            return None
