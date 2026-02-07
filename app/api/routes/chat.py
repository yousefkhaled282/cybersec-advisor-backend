import time
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.deepseek import deepseek_service
from app.services.firestore import firestore_service
from app.core.security import verify_app_check
from app.core.utils import validate_token_limit
from app.core.logger import logger
from pathlib import Path

router = APIRouter()

# Load Prompt
PROMPT_PATH = Path("app/resources/prompts/system_prompt.txt")
BASE_PROMPT = PROMPT_PATH.read_text() if PROMPT_PATH.exists() else "You are a cybersecurity expert."

@router.post("/ask", response_model=ChatResponse, dependencies=[Depends(verify_app_check)])
async def ask_advisor(request: ChatRequest):
    start_time = time.time()
    
    # [START] Request Logging
    logger.info(f"🚀 [START] Incoming Request | User: {request.user_id} | Chat: {request.chat_id}")
    logger.info(f"📝 Message Preview: {request.message[:50]}...") # Log first 50 chars only

    try:
        # 1. Validate
        validate_token_limit(request.message, limit=300)
        logger.info("✅ [1/6] Token validation passed.")

        # 2. Sync User Profile
        user_profile = {
            "role": request.role,
            "level": request.level,
            "stack": request.stack
        }
        firestore_service.upsert_user(request.user_id, user_profile)
        logger.info(f"✅ [2/6] User profile synced for {request.user_id}.")

        # 3. Prepare Prompt
        system_instruction = BASE_PROMPT.format(**user_profile)
        messages = [{"role": "system", "content": system_instruction}]
        logger.info("✅ [3/6] System prompt constructed with user facts.")

        # 4. Fetch Specific Chat History
        history = firestore_service.get_chat_history(request.user_id, request.chat_id)
        msg_count = len(history)
        messages.extend(history)
        
        # Add Current User Message
        messages.append({"role": "user", "content": request.message})
        logger.info(f"✅ [4/6] History Fetched. Injected {msg_count} previous messages.")

        # 5. Call DeepSeek
        logger.info(f"⏳ [5/6] Calling DeepSeek (Vertex AI)... Payload size: {len(messages)} msgs.")
        ai_start = time.time()
        ai_response = deepseek_service.generate_response(messages)
        ai_duration = round(time.time() - ai_start, 2)
        logger.info(f"✅ [5/6] DeepSeek Responded in {ai_duration}s. Response Length: {len(ai_response)} chars.")

        # 6. Save & Prune History (Rolling Window)
        new_pair = [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": ai_response}
        ]
        firestore_service.save_interaction(request.user_id, request.chat_id, new_pair)
        logger.info("✅ [6/6] Interaction saved & history pruned to last 2 pairs.")

        # [END] Completion Logging
        total_duration = round(time.time() - start_time, 2)
        logger.info(f"🏁 [COMPLETE] Request finished successfully in {total_duration}s.")

        return ChatResponse(
            response=ai_response,
            chat_id=request.chat_id,
            tokens_used=len(ai_response.split()) 
        )

    except Exception as e:
        logger.error(f"❌ [ERROR] Request Failed: {str(e)}")
        raise e