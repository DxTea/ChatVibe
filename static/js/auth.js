console.log("auth.js loaded"); // Для отладки

window.login = async function () {
    console.log("login function called"); // Для отладки
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    if (!username || !password) {
        alert("Пожалуйста, заполните все поля");
        return;
    }
    try {
        const response = await fetch("/login", {
            method: "POST",
            headers: {"Content-Type": "application/x-www-form-urlencoded"},
            body: new URLSearchParams({username, password})
        });
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem("token", data.access_token);
            window.location.href = "/main";
        } else {
            alert("Ошибка входа в ChatVibe: " + (await response.text()));
        }
    } catch (error) {
        console.error("Login error:", error);
        alert("Ошибка входа в ChatVibe: Не удалось подключиться к серверу");
    }
}

window.register = async function () {
    console.log("register function called"); // Для отладки
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    if (!username || !password) {
        alert("Пожалуйста, заполните все поля");
        return;
    }
    try {
        const response = await fetch("/register", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({username, password})
        });
        if (response.ok) {
            alert("Регистрация в ChatVibe прошла успешно! Пожалуйста, войдите.");
            document.getElementById("username").value = "";
            document.getElementById("password").value = "";
        } else {
            alert("Ошибка регистрации в ChatVibe: " + (await response.text()));
        }
    } catch (error) {
        console.error("Register error:", error);
        alert("Ошибка регистрации в ChatVibe: Не удалось подключиться к серверу");
    }
}