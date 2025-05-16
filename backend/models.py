from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table, \
    Boolean
from sqlalchemy.orm import relationship

from datetime import datetime

from backend.database import Base

# Таблица для связи друзей
friends_table = Table(
    "friends", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("friend_id", Integer, ForeignKey("users.id"), primary_key=True)
)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    # Связь многие-ко-многим для друзей
    friends = relationship("User", secondary=friends_table,
                           primaryjoin="User.id == friends.c.user_id",
                           secondaryjoin="User.id == friends.c.friend_id")


class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, ForeignKey("users.id"))
    user2_id = Column(Integer, ForeignKey("users.id"))
    user1 = relationship("User", foreign_keys=[user1_id])
    user2 = relationship("User", foreign_keys=[user2_id])
    messages = relationship("Message", back_populates="chat")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    message_text = Column(String)
    file_path = Column(String, nullable=True)  # Путь к файлу
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User")
