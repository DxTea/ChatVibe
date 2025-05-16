let currentChatId = null;
let ws = null;
let currentUser = null;
let selectedFiles = [];

function attachFile() {
    document.getElementById("file-input").click();
}

document.getElementById("file-input").addEventListener("change", (event) => {
    selectedFiles = Array.from(event.target.files);
    updateFileList();
});

function updateFileList() {
    const fileList = document.getElementById("file-list");
    fileList.innerHTML = "";
    selectedFiles.forEach((file, index) => {
        const div = document.createElement("div");
        div.className = "file-item";
        div.innerHTML = `
            <span>${file.name}</span>
            <button onclick="removeFile(${index})" class="bg-red-500 text-white px-1 py-0.5 rounded hover:bg-red-600">✖</button>
        `;
        fileList.appendChild(div);
    });
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    updateFileList();
}

async function fetchUserInfo() {
    const response = await fetch("/users/me", {headers: {"Authorization": `Bearer ${localStorage.getItem("token")}`}});
    if (response.ok) {
        currentUser = await response.json();
        document.getElementById("user-info").textContent = `Пользователь: ${currentUser.username} (ID: ${currentUser.id})`;
    } else {
        alert("Ошибка загрузки данных пользователя");
    }
}

async function fetchChats() {
    const [chatsResponse, unreadResponse] = await Promise.all([
        fetch("/chats", {headers: {"Authorization": `Bearer ${localStorage.getItem("token")}`}}),
        fetch("/chats/unread", {headers: {"Authorization": `Bearer ${localStorage.getItem("token")}`}})
    ]);
    if (!chatsResponse.ok) return;
    const chats = await chatsResponse.json();
    const unreadChats = unreadResponse.ok ? await unreadResponse.json() : [];
    const chatList = document.getElementById("chat-list");
    chatList.innerHTML = "";
    chats.forEach(chat => {
        const div = document.createElement("div");
        div.className = `p-2 hover:bg-gray-200 dark:hover:bg-gray-700 cursor-pointer flex justify-between items-center ${unreadChats.includes(chat.id) ? 'unread' : ''}`;
        div.innerHTML = `
            <span class="flex-1"><span class="unread-indicator"></span>${chat.other_user.username}</span>
            <button onclick="deleteChat(${chat.id}); event.stopPropagation();" class="bg-red-500 text-white px-2 py-1 rounded hover:bg-red-600">Удалить</button>
        `;
        div.onclick = () => loadChat(chat.id, chat.other_user.username);
        chatList.appendChild(div);
    });
    if (!currentChatId) {
        showChatPlaceholder();
    }
}

function showChatPlaceholder() {
    const chatHeader = document.getElementById("chat-header");
    const chatArea = document.getElementById("chat-area");
    const messageInput = document.getElementById("message-input");
    chatHeader.innerHTML = "";
    chatArea.innerHTML = `<div class="chat-placeholder">Чат не выбран</div>`;
    messageInput.style.display = "none";
}

async function loadChat(chatId, username) {
    currentChatId = chatId;
    const chatHeader = document.getElementById("chat-header");
    const chatArea = document.getElementById("chat-area");
    const messageInput = document.getElementById("message-input");
    chatHeader.innerHTML = `<h2 class="text-xl font-bold mb-4">Чат с ${username}</h2>`;
    chatArea.innerHTML = "";
    messageInput.style.display = "flex";

    const response = await fetch(`/chats/${chatId}/messages`, {headers: {"Authorization": `Bearer ${localStorage.getItem("token")}`}});
    if (response.ok) {
        const messages = await response.json();
        let firstUnreadMessageId = null;

        // Отображаем сообщения и ищем первое непрочитанное
        messages.forEach((message, index) => {
            const isUnread = !message.is_read && message.sender.username !== currentUser.username;
            if (isUnread && firstUnreadMessageId === null) {
                firstUnreadMessageId = `message-${index}`;
            }
            const messageDiv = document.createElement("div");
            messageDiv.id = `message-${index}`;
            chatArea.appendChild(messageDiv);
            displayMessage(message, messageDiv);
        });

        // Скролл к нужному сообщению
        if (firstUnreadMessageId) {
            const firstUnreadElement = document.getElementById(firstUnreadMessageId);
            if (firstUnreadElement) {
                firstUnreadElement.scrollIntoView({behavior: 'smooth', block: 'start'});
            }
        } else {
            chatArea.scrollTop = chatArea.scrollHeight;
        }
    }

    if (ws) ws.close();
    ws = new WebSocket(`ws://localhost:8000/chats/${chatId}/ws?token=${localStorage.getItem("token")}`);
    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        displayMessage(message);
        if (message.sender.username !== currentUser.username) {
            fetchChats();
        }
    };
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = String(date.getFullYear()).slice(2);
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${day}.${month}.${year} ${hours}:${minutes}`;
}

function displayMessage(message, targetDiv = null) {
    const chatArea = document.getElementById("chat-area");
    const div = targetDiv || document.createElement("div");
    const isOwnMessage = currentUser && message.sender.username === currentUser.username;
    div.className = `message ${isOwnMessage ? 'ml-auto bg-blue-100 text-right' : 'mr-auto bg-gray-100 text-left'}`;

    let content = `<div class="message-content"><span class="message-text">${message.message_text || ''}</span>`;
    if (message.file_path) {
        const isImage = /\.(jpg|jpeg|png|gif)$/i.test(message.file_path);
        if (isImage) {
            content += `<br><a href="${message.file_path}" download><img src="${message.file_path}" alt="Image" /></a>`;
        } else {
            content += `<br><a href="${message.file_path}" download class="text-blue-500 underline">Скачать файл: ${message.file_path.split('/').pop()}</a>`;
        }
    }
    content += `<span class="message-time">${formatTimestamp(message.timestamp)}</span></div>`;

    div.innerHTML = content;
    if (!targetDiv) {
        chatArea.appendChild(div);
        chatArea.scrollTop = chatArea.scrollHeight;
    }
}

function openAddFriendModal() {
    const modal = document.getElementById("add-friend-modal");
    modal.classList.remove("hidden");
}

function closeAddFriendModal() {
    const modal = document.getElementById("add-friend-modal");
    modal.classList.add("hidden");
    document.getElementById("friend-username").value = "";
}

async function sendFriendRequest() {
    const friendInput = document.getElementById("friend-username").value.trim();
    if (!friendInput) {
        alert("Введите имя пользователя или ID");
        return;
    }
    const body = isNaN(friendInput) ? {username: friendInput} : {friend_id: parseInt(friendInput)};
    const response = await fetch("/friends", {
        method: "POST",
        headers: {"Authorization": `Bearer ${localStorage.getItem("token")}`, "Content-Type": "application/json"},
        body: JSON.stringify(body)
    });
    if (response.ok) {
        const chat = await response.json();
        alert("Чат создан!");
        await fetchChats();
        loadChat(chat.id, chat.other_user.username);
        closeAddFriendModal();
    } else {
        alert("Ошибка: " + (await response.text()));
    }
}

async function searchChat(event) {
    if (event.key !== "Enter") return;
    const searchInput = document.getElementById("chat-search").value.trim().toLowerCase();
    if (!searchInput) {
        fetchChats();
        return;
    }
    const response = await fetch("/chats", {headers: {"Authorization": `Bearer ${localStorage.getItem("token")}`}});
    if (!response.ok) return;
    const chats = await response.json();
    const matchingChat = chats.find(chat => chat.other_user.username.toLowerCase() === searchInput);
    if (matchingChat) {
        loadChat(matchingChat.id, matchingChat.other_user.username);
    } else {
        alert("Такого чата нет");
        document.getElementById("chat-search").value = "";
        fetchChats();
    }
}

async function sendMessage() {
    const messageText = document.getElementById("message").value.trim();
    if (!currentChatId || (!messageText && selectedFiles.length === 0)) return;

    const formData = new FormData();
    formData.append("message_text", messageText);
    selectedFiles.forEach((file) => {
        formData.append("files", file);
    });

    const response = await fetch(`/chats/${currentChatId}/messages`, {
        method: "POST",
        headers: {"Authorization": `Bearer ${localStorage.getItem("token")}`},
        body: formData
    });

    if (response.ok) {
        document.getElementById("message").value = "";
        selectedFiles = [];
        updateFileList();
        await fetchChats();
    } else {
        alert("Ошибка отправки сообщения: " + (await response.text()));
    }
}

async function deleteChat(chatId) {
    if (!confirm("Вы уверены, что хотите удалить этот чат?")) return;
    const response = await fetch(`/chats/${chatId}`, {
        method: "DELETE",
        headers: {"Authorization": `Bearer ${localStorage.getItem("token")}`}
    });
    if (response.ok) {
        alert("Чат удален!");
        if (currentChatId === chatId) {
            currentChatId = null;
            showChatPlaceholder();
            if (ws) ws.close();
        }
        await fetchChats();
    } else {
        alert("Ошибка: " + (await response.text()));
    }
}

function logout() {
    localStorage.removeItem("token");
    window.location.href = "/";
}

window.onload = () => {
    fetchUserInfo();
    fetchChats();
    document.getElementById("message").addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            sendMessage();
        }
    });
    document.getElementById("add-chat-btn").addEventListener("click", openAddFriendModal);
    document.getElementById("chat-search").addEventListener("keydown", searchChat);
    document.getElementById("add-friend-modal").addEventListener("click", (event) => {
        if (event.target === document.getElementById("add-friend-modal")) {
            closeAddFriendModal();
        }
    });
};