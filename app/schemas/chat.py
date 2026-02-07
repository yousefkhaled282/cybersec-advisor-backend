from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    chat_id: str = Field(..., description="Unique conversation identifier (e.g. session-123)")
    message: str = Field(..., description="The query for the advisor")
    
    # Profile Data (Sent with every request)
    role: str = Field("Developer", description="Job title")
    level: str = Field("Mid-Level", description="Experience level")
    stack: str = Field("General", description="Tech stack")

class ChatResponse(BaseModel):
    response: str
    chat_id: str
    tokens_used: int

# 3. NEW: Standard Envelope (Generic)
class APIResponse(BaseModel):
    status: int
    msg: str 
    data: Optional[ChatResponse] = None  