import time
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.chat import ChatRequest, ChatData, APIResponse
from app.services.deepseek import deepseek_service
from app.services.firestore import firestore_service
from app.core.security import verify_app_check
from app.core.utils import validate_token_limit
from app.core.logger import logger
from pathlib import Path

router = APIRouter()

PROMPT_PATH = Path("app/resources/prompts/system_prompt.txt")
BASE_PROMPT = PROMPT_PATH.read_text() if PROMPT_PATH.exists() else "You are a cybersecurity expert."

# Ensure the response model matches the Generic definition
@router.post("/ask", response_model=APIResponse[ChatData], dependencies=[Depends(verify_app_check)])
async def ask_advisor(request: ChatRequest):
    start_time = time.time()
    
    logger.info(f"🚀 [START] Incoming Request | User: {request.user_id} | Chat: {request.chat_id}")

    try:
        # 1. Validate
        validate_token_limit(request.message, limit=300)

        # 2. Sync User Profile
        user_profile = {
            "role": request.role,
            "level": request.level,
            "stack": request.stack
        }
        firestore_service.upsert_user(request.user_id, user_profile)

        # 3. Prepare Prompt
        system_instruction = BASE_PROMPT.format(**user_profile)
        messages = [{"role": "system", "content": system_instruction}]

        # 4. Fetch & Sandwich History
        history = firestore_service.get_chat_history(request.user_id, request.chat_id)
        if history:
            messages.append({"role": "system", "content": "--- PREVIOUS CONVERSATION HISTORY START ---"})
            messages.extend(history)
            messages.append({"role": "system", "content": "--- PREVIOUS CONVERSATION HISTORY END ---"})

        # Add Current User Message
        messages.append({"role": "user", "content": request.message})

        # 5. Call DeepSeek
        ai_response = deepseek_service.generate_response(messages)

        # 6. Save (Append to Full History)
        new_pair = [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": ai_response}
        ]
        firestore_service.save_interaction(request.user_id, request.chat_id, new_pair)

        # [END] Success Response
        logger.info(f"🏁 [COMPLETE] Request finished in {round(time.time() - start_time, 2)}s.")

        # --- NEW RETURN FORMAT ---
        # Note: We are using ChatData here to match the response_model
        return APIResponse(
            status=200,
            msg="Success",
            data=ChatData(
                response=ai_response,
                chat_id=request.chat_id,
                tokens_used=len(ai_response.split())
            )
        )

    except HTTPException as http_exc:
        logger.warning(f"⚠️ Handled Error: {http_exc.detail}")
        return APIResponse(
            status=http_exc.status_code,
            msg=str(http_exc.detail),
            data=None
        )

    except Exception as e:
        logger.error(f"❌ Critical Error: {str(e)}")
        # Raise 500 so FastAPI knows it's a server error
        raise HTTPException(status_code=500, detail="Internal Server Error")