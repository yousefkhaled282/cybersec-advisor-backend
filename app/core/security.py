import firebase_admin
from firebase_admin import credentials, app_check
from fastapi import Header, HTTPException
from app.core.config import settings
from app.core.logger import logger  # Assumes you have a basic logger setup
import os

# Global Flag to track status
FIREBASE_INITIALIZED = False

def initialize_firebase():
    """
    Attempts to initialize Firebase.
    If it fails, it LOGS the error but DOES NOT crash the container.
    This is critical for Cloud Run cold starts not to fail hard on transient config issues.
    """
    global FIREBASE_INITIALIZED
    try:
        if firebase_admin._apps:
            FIREBASE_INITIALIZED = True
            return

        # Use the Project ID from settings
        firebase_config = {'projectId': settings.FIREBASE_PROJECT_ID}
        
        # 1. Try Secrets Directory (Cloud Run Volume Mounts)
        cred_path = "/app/secrets/service_account.json"
        local_fallback = "secrets/service_account.json"
        
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, options=firebase_config)
            logger.info(f"Firebase initialized (MOUNTED secret) for: {settings.FIREBASE_PROJECT_ID}")
        elif os.path.exists(local_fallback):
            cred = credentials.Certificate(local_fallback)
            firebase_admin.initialize_app(cred, options=firebase_config)
            logger.info(f"Firebase initialized (LOCAL secret) for: {settings.FIREBASE_PROJECT_ID}")
        else:
            # 2. ADC Fallback (Application Default Credentials)
            # This is the preferred method for Cloud Run (Identity-based security)
            logger.info(f"Attempting ADC init for {settings.FIREBASE_PROJECT_ID}...")
            firebase_admin.initialize_app(options=firebase_config)
            logger.info(f"Firebase successfully initialized via ADC.")

        FIREBASE_INITIALIZED = True

    except Exception as e:
        # --- CRITICAL CHANGE: DO NOT EXIT ---
        logger.error(f"⚠️ FIREBASE INIT FAILED: {e}")
        logger.error("App will start in UNSECURED mode (Requests will fail auth).")
        FIREBASE_INITIALIZED = False

# Initialize on import
initialize_firebase()

async def verify_app_check(x_firebase_app_check: str = Header(None, alias="X-Firebase-AppCheck")):
    """
    Dependency to verify Firebase App Check token.
    Used to ensure requests come from your genuine App/Web client, not bots.
    """
    # 1. Check if Firebase is even running
    if not FIREBASE_INITIALIZED:
        logger.error("Rejecting request: Firebase failed to initialize on startup.")
        raise HTTPException(status_code=500, detail="Server Security Misconfigured")

    # 2. Dev Mode Bypass
    if not settings.APP_CHECK_ENFORCED:
        logger.warning("⚠️ App Check is DISABLED (Dev Mode)")
        return True

    # 3. Token Check
    if not x_firebase_app_check:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing App Check Token")

    try:
        # Verify the token with Firebase
        decoded_token = app_check.verify_token(x_firebase_app_check)
        return decoded_token
    except Exception as e:
        logger.error(f"Security Alert: {e}")
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Token")