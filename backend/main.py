from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, \
    WebSocketDisconnect, Form
from fastapi import UploadFile, File
from typing import List
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import or_
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from backend import database, models, schemas, auth
from typing import List, Dict
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import os
import json

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, chat_id: int):
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = []
        self.active_connections[chat_id].append(websocket)

    def disconnect(self, websocket: WebSocket, chat_id: int):
        if chat_id in self.active_connections:
            self.active_connections[chat_id].remove(websocket)
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]

    async def broadcast(self, message: dict, chat_id: int,
                        sender_ws: WebSocket = None):
        if chat_id in self.active_connections:
            for ws in self.active_connections[chat_id]:
                if ws != sender_ws:
                    await ws.send_json(message)


manager = ConnectionManager()


@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(),
                            media_type="text/html; charset=utf-8")


@app.get("/auth", response_class=HTMLResponse)
async def read_auth():
    with open("static/auth.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(),
                            media_type="text/html; charset=utf-8")


@app.get("/main", response_class=HTMLResponse)
async def read_main():
    with open("static/main.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(),
                            media_type="text/html; charset=utf-8")


@app.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    db_user = db.query(models.User).filter(
        models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400,
                            detail="Имя пользователя уже занято")
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(username=user.username,
                          password_hash=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(
        models.User.username == form_data.username).first()
    if not user or not pwd_context.verify(form_data.password,
                                          user.password_hash):
        raise HTTPException(status_code=401,
                            detail="Неверное имя пользователя или пароль")
    access_token = auth.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@app.get("/friends", response_model=List[schemas.UserOut])
def get_friends(current_user: models.User = Depends(auth.get_current_user),
                db: Session = Depends(database.get_db)):
    friends = db.query(models.User).join(models.friends_table,
                                         or_(models.friends_table.c.friend_id == models.User.id,
                                             models.friends_table.c.user_id == models.User.id)).filter(
        or_(models.friends_table.c.user_id == current_user.id,
            models.friends_table.c.friend_id == current_user.id)).distinct().all()
    return [schemas.UserOut(id=f.id, username=f.username) for f in friends if
            f.id != current_user.id]


@app.post("/friends", response_model=schemas.ChatOut)
async def add_friend(friend: schemas.FriendCreate,
                     current_user: models.User = Depends(
                         auth.get_current_user),
                     db: Session = Depends(database.get_db)):
    friend_user = None
    if friend.friend_id is not None:
        friend_user = db.query(models.User).filter(
            models.User.id == friend.friend_id).first()
    elif friend.username:
        friend_user = db.query(models.User).filter(
            models.User.username == friend.username).first()
    if not friend_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if friend_user.id == current_user.id:
        raise HTTPException(status_code=400,
                            detail="Нельзя добавить самого себя в друзья")
    existing_friendship = db.query(models.friends_table).filter(
        or_((models.friends_table.c.user_id == current_user.id) & (
                models.friends_table.c.friend_id == friend_user.id),
            (models.friends_table.c.user_id == friend_user.id) & (
                    models.friends_table.c.friend_id == current_user.id))).first()
    if not existing_friendship:
        db.execute(
            models.friends_table.insert().values(user_id=current_user.id,
                                                 friend_id=friend_user.id))
        db.execute(models.friends_table.insert().values(user_id=friend_user.id,
                                                        friend_id=current_user.id))
    existing_chat = db.query(models.Chat).filter(
        or_((models.Chat.user1_id == current_user.id) & (
                models.Chat.user2_id == friend_user.id),
            (models.Chat.user1_id == friend_user.id) & (
                    models.Chat.user2_id == current_user.id))).first()
    if existing_chat:
        return schemas.ChatOut(id=existing_chat.id,
                               other_user=schemas.UserOut(id=friend_user.id,
                                                          username=friend_user.username))
    new_chat = models.Chat(user1_id=current_user.id, user2_id=friend_user.id)
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return schemas.ChatOut(id=new_chat.id,
                           other_user=schemas.UserOut(id=friend_user.id,
                                                      username=friend_user.username))


@app.get("/chats", response_model=List[schemas.ChatOut])
def get_chats(current_user: models.User = Depends(auth.get_current_user),
              db: Session = Depends(database.get_db)):
    chats = db.query(models.Chat).filter(
        or_(models.Chat.user1_id == current_user.id,
            models.Chat.user2_id == current_user.id)).all()
    chat_list = []
    for chat in chats:
        other_user = chat.user2 if chat.user1_id == current_user.id else chat.user1
        chat_list.append(schemas.ChatOut(id=chat.id,
                                         other_user=schemas.UserOut(
                                             id=other_user.id,
                                             username=other_user.username)))
    return chat_list


@app.post("/chats", response_model=schemas.ChatOut)
def create_chat(friend_id: int,
                current_user: models.User = Depends(auth.get_current_user),
                db: Session = Depends(database.get_db)):
    friend = db.query(models.User).filter(models.User.id == friend_id).first()
    if not friend:
        raise HTTPException(status_code=404, detail="Друг не найден")
    if friend_id not in [f.id for f in current_user.friends]:
        raise HTTPException(status_code=400, detail="Вы не друзья")
    existing_chat = db.query(models.Chat).filter(
        or_((models.Chat.user1_id == current_user.id) & (
                models.Chat.user2_id == friend_id),
            (models.Chat.user1_id == friend_id) & (
                    models.Chat.user2_id == current_user.id))).first()
    if existing_chat:
        return schemas.ChatOut(id=existing_chat.id,
                               other_user=schemas.UserOut(id=friend.id,
                                                          username=friend.username))
    new_chat = models.Chat(user1_id=current_user.id, user2_id=friend_id)
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return schemas.ChatOut(id=new_chat.id,
                           other_user=schemas.UserOut(id=friend.id,
                                                      username=friend.username))


@app.get("/chats/{chat_id}/messages", response_model=List[schemas.MessageOut])
def get_messages(chat_id: int,
                 current_user: models.User = Depends(auth.get_current_user),
                 db: Session = Depends(database.get_db)):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    if not chat or (
            chat.user1_id != current_user.id and chat.user2_id != current_user.id):
        raise HTTPException(status_code=403, detail="Нет доступа")
    other_user_id = chat.user2_id if chat.user1_id == current_user.id else chat.user1_id
    db.query(models.Message).filter(models.Message.chat_id == chat_id,
                                    models.Message.sender_id == other_user_id,
                                    models.Message.is_read == False).update(
        {"is_read": True})
    db.commit()
    messages = db.query(models.Message).filter(
        models.Message.chat_id == chat_id).order_by(
        models.Message.timestamp).all()
    return [schemas.MessageOut(id=m.id, sender=schemas.UserOut(id=m.sender.id,
                                                               username=m.sender.username),
                               message_text=m.message_text,
                               file_path=m.file_path, timestamp=m.timestamp,
                               is_read=m.is_read) for m in messages]


@app.post("/chats/{chat_id}/messages", response_model=List[schemas.MessageOut])
async def send_message(chat_id: int, message_text: str = Form(""),
                       files: List[UploadFile] = File(default=[]),
                       current_user: models.User = Depends(
                           auth.get_current_user),
                       db: Session = Depends(database.get_db)):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    if not chat or (
            chat.user1_id != current_user.id and chat.user2_id != current_user.id):
        raise HTTPException(status_code=403, detail="Нет доступа")

    messages = []
    timestamp = datetime.utcnow()

    if message_text:
        text_message = models.Message(
            chat_id=chat_id,
            sender_id=current_user.id,
            message_text=message_text,
            file_path=None,
            timestamp=timestamp,
            is_read=False
        )
        db.add(text_message)
        messages.append(text_message)

    if files:
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file = files[0]
        file_path = f"{upload_dir}/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())
        file_message = models.Message(
            chat_id=chat_id,
            sender_id=current_user.id,
            message_text="",
            file_path=file_path,
            timestamp=timestamp,
            is_read=False
        )
        db.add(file_message)
        messages.append(file_message)

    if not messages:
        raise HTTPException(status_code=400,
                            detail="Сообщение или файл обязательны")

    db.commit()

    for msg in messages:
        db.refresh(msg)
        message_data = {
            "id": msg.id,
            "sender": {"username": current_user.username},
            "message_text": msg.message_text,
            "file_path": msg.file_path,
            "timestamp": msg.timestamp.isoformat(),
            "is_read": msg.is_read
        }
        await manager.broadcast(message_data, chat_id)

    return [schemas.MessageOut(id=m.id,
                               sender=schemas.UserOut(id=current_user.id,
                                                      username=current_user.username),
                               message_text=m.message_text,
                               file_path=m.file_path, timestamp=m.timestamp,
                               is_read=m.is_read) for m in messages]


@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: int,
                current_user: models.User = Depends(auth.get_current_user),
                db: Session = Depends(database.get_db)):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
    if not chat or (
            chat.user1_id != current_user.id and chat.user2_id != current_user.id):
        raise HTTPException(status_code=403, detail="Нет доступа")
    db.query(models.Message).filter(models.Message.chat_id == chat_id).delete()
    db.delete(chat)
    db.commit()
    return {"message": "Чат успешно удален"}


@app.get("/chats/unread", response_model=List[int])
def get_unread_chats(
        current_user: models.User = Depends(auth.get_current_user),
        db: Session = Depends(database.get_db)):
    unread_chats = db.query(models.Message.chat_id).filter(
        models.Message.is_read == False,
        models.Message.sender_id != current_user.id,
        models.Message.chat_id.in_(db.query(models.Chat.id).filter(
            or_(models.Chat.user1_id == current_user.id,
                models.Chat.user2_id == current_user.id)))).distinct().all()
    return [chat_id for (chat_id,) in unread_chats]


@app.websocket("/chats/{chat_id}/ws")
async def websocket_endpoint(websocket: WebSocket, chat_id: int, token: str,
                             db: Session = Depends(database.get_db)):
    try:
        current_user = auth.get_current_user_from_token(token, db)
        chat = db.query(models.Chat).filter(models.Chat.id == chat_id).first()
        if not chat or (
                chat.user1_id != current_user.id and chat.user2_id != current_user.id):
            await websocket.close(code=1008)
            return
        await manager.connect(websocket, chat_id)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(websocket, chat_id)
    except JWTError:
        await websocket.close(code=1008)
