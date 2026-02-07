from fastapi import HTTPException

def validate_token_limit(text: str, limit: int = 300):
    """
    Estimates token count. If it exceeds the limit, raises HTTP 400.
    Rule of thumb: 1 token ~= 4 chars in English.
    """
    # Quick estimation: Character count / 4
    estimated_tokens = len(text) / 4
    
    if estimated_tokens > limit:
        raise HTTPException(
            status_code=400, 
            detail=f"Message too long! Estimated {int(estimated_tokens)} tokens. Limit is {limit}."
        )
    return True