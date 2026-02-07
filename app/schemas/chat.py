from pydantic import BaseModel, Field
from typing import Optional, Generic, TypeVar

# Define a Type Variable for the Generic Envelope
T = TypeVar('T')

class ChatRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    chat_id: str = Field(..., description="Unique conversation identifier")
    message: str = Field(..., description="The query for the advisor")
    
    # Profile Data
    role: str = Field("Developer", description="Job title")
    level: str = Field("Mid-Level", description="Experience level")
    stack: str = Field("General", description="Tech stack")

# This is the "Data" payload inside the envelope
class ChatData(BaseModel):
    response: str
    chat_id: str
    tokens_used: int

# This is the Generic Envelope
# It inherits from Generic[T] so you can use APIResponse[ChatData]
class APIResponse(BaseModel, Generic[T]):
    status: int
    msg: str 
    data: Optional[T] = None