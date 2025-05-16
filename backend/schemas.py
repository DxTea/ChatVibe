from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class FriendCreate(BaseModel):
    friend_id: Optional[int] = None
    username: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class ChatOut(BaseModel):
    id: int
    other_user: UserOut

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    message_text: str


class MessageOut(BaseModel):
    id: int
    sender: UserOut
    message_text: str
    file_path: Optional[str] = None
    timestamp: datetime
    is_read: bool

    class Config:
        from_attributes = True
