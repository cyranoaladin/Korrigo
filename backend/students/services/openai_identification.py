import base64
import json
import logging
import os
import time
from typing import List, Dict, Optional
from django.conf import settings
import requests

logger = logging.getLogger(__name__)

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_STUDENTS_PER_CALL = 500
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1.0


class OpenAIService:
    """
    Service to identify students from header images using OpenAI GPT-4o.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, 'OPENAI_API_KEY', None)
        if not self.api_key:
            logger.warning("OpenAI API Key not configured.")

    def identify_student(self, header_image_path: str, student_list: List[Dict]) -> Dict:
        """
        Identify a student from a header image.

        Args:
            header_image_path: Path to the header image file.
            student_list: List of dictionaries containing student info (name, first_name, dob).

        Returns:
            Dict containing identification result:
            {
                "student_id": int or None,
                "confidence": float,
                "reasoning": str
            }
        """
        if not self.api_key:
            return {"error": "OpenAI API Key missing"}

        try:
            # Validate image size before encoding
            file_size = os.path.getsize(header_image_path)
            if file_size > MAX_IMAGE_SIZE_BYTES:
                return {"error": f"Image too large ({file_size} bytes), max {MAX_IMAGE_SIZE_BYTES}"}

            with open(header_image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')

            # Data minimization: only send name fields, not full records
            minimized_list = [
                {"id": s.get("id"), "name": s.get("full_name") or s.get("name", ""), "dob": s.get("date_of_birth", "")}
                for s in student_list[:MAX_STUDENTS_PER_CALL]
            ]

            system_prompt = (
                "You are an expert OCR and data matching assistant. "
                "Your task is to identify a student from a handwritten or printed exam header image. "
                "You will be provided with an image and a list of valid students. "
                "Output ONLY valid JSON."
            )

            user_prompt = f"""
            Here is the list of valid students enrolled in this exam:
            {json.dumps(minimized_list, ensure_ascii=False)}

            Analyze the attached image. It contains the student's name and possibly date of birth.
            1. Transcribe the handwritten name and date of birth.
            2. Match it against the provided list.
            3. Return the ID of the matching student, your confidence score (0.0 to 1.0), and a brief reasoning.

            If no match is found or confidence is low, set student_id to null.

            Response format:
            {{
                "student_id": <int or null>,
                "confidence": <float>,
                "reasoning": "<string>"
            }}
            """

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }

            payload = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}",
                                    "detail": "low"
                                }
                            }
                        ]
                    }
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
                "max_tokens": 300
            }

            # Retry with exponential backoff
            last_error = None
            for attempt in range(MAX_RETRIES):
                try:
                    response = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=30
                    )

                    if response.status_code == 200:
                        result_json = response.json()
                        content = result_json['choices'][0]['message']['content']
                        return json.loads(content)

                    if response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', BACKOFF_BASE_SECONDS * (2 ** attempt)))
                        logger.warning(f"OpenAI rate limited, retrying in {retry_after}s (attempt {attempt + 1})")
                        time.sleep(retry_after)
                        continue

                    if response.status_code >= 500:
                        logger.warning(f"OpenAI server error {response.status_code}, retrying (attempt {attempt + 1})")
                        time.sleep(BACKOFF_BASE_SECONDS * (2 ** attempt))
                        continue

                    # Client errors (400, 401, 403) - don't retry
                    logger.error(f"OpenAI API Error: {response.status_code} - {response.text[:500]}")
                    return {"error": f"OpenAI Error: {response.status_code}"}

                except requests.exceptions.Timeout:
                    last_error = "Request timeout"
                    logger.warning(f"OpenAI timeout (attempt {attempt + 1})")
                    time.sleep(BACKOFF_BASE_SECONDS * (2 ** attempt))
                except requests.exceptions.ConnectionError as e:
                    last_error = str(e)
                    logger.warning(f"OpenAI connection error (attempt {attempt + 1}): {e}")
                    time.sleep(BACKOFF_BASE_SECONDS * (2 ** attempt))

            return {"error": f"OpenAI failed after {MAX_RETRIES} retries: {last_error}"}

        except Exception as e:
            logger.error(f"OpenAI Identification failed: {str(e)}")
            return {"error": str(e)}
