import requests
import google.auth
import google.auth.transport.requests
from fastapi import HTTPException
from app.core.config import settings
from app.core.logger import logger

class DeepSeekService:
    def __init__(self):
        self.project_id = settings.VERTEX_PROJECT_ID
        self.location = settings.VERTEX_LOCATION
        self.model_name = settings.VERTEX_MODEL_NAME
        
        # Endpoint construction for Vertex AI Model Garden
        self.endpoint_url = (
            f"https://{self.location}-aiplatform.googleapis.com"
            f"/v1beta1/projects/{self.project_id}/locations/{self.location}"
            "/endpoints/openapi/chat/completions"
        )
        logger.info(f"🔹 DeepSeek Service Initialized. Target Endpoint: {self.endpoint_url}")

    def _get_access_token(self) -> str:
        """
        Dynamically generates a Google Cloud Access Token.
        Equivalent to: $(gcloud auth print-access-token)
        """
        try:
            logger.info("🔑 Attempting to generate Google Cloud Access Token...")
            credentials, project = google.auth.default()
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)
            logger.info("✅ Google Cloud Access Token generated successfully.")
            return credentials.token
        except Exception as e:
            logger.error(f"❌ Failed to generate Google Cloud Token: {e}")
            raise HTTPException(status_code=500, detail="Internal Auth Error")

    def generate_response(self, messages: list, max_tokens: int = 300, temperature: float = 0.6) -> str:
        logger.info(f"🧠 [DeepSeek] Starting generation. Context: {len(messages)} messages. Max Tokens: {max_tokens}")
        
        token = self._get_access_token()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.95,
            "stream": False 
        }

        logger.info(f"📡 Sending request to Vertex AI... Model: {self.model_name}")

        try:
            response = requests.post(
                self.endpoint_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            # Log the raw status code for debugging
            logger.info(f"⬅️ Vertex AI responded with Status Code: {response.status_code}")
            
            response.raise_for_status()
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                logger.info(f"✅ [DeepSeek] Successfully extracted content. Length: {len(content)} chars.")
                return content
            else:
                logger.error(f"⚠️ Unexpected response format: {data}")
                raise HTTPException(status_code=502, detail="Invalid AI Response")

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Vertex AI Request Failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                 logger.error(f"❌ Error Details (Response Body): {e.response.text}")
            raise HTTPException(status_code=502, detail="AI Service Unavailable")

deepseek_service = DeepSeekService()