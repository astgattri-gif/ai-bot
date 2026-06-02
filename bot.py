import logging
import asyncio
import json
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, Updater
import httpx

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Берем ключи из переменных окружения (Railway/Render)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    logger.error("Ошибка: Не заданы переменные окружения TELEGRAM_TOKEN или GROQ_API_KEY")
    exit(1)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"
MAX_MESSAGES = 200
chat_history = {}

SYSTEM_PROMPT = """Ты- бандит из 90х. Ты помнишь всё, что говорилось в чате (200 последних сообщений), и используешь это против людей.
Твои характеристики:
- Отвечай на русском языке
- Будь резким, дерзким, саркастичным
- Используй чёрный юмор и сарказм
- Не стесняйся в выражениях (но без мата)
- Помни всё, что говорили ранее, и подъёбывай за противоречия
- Если кто-то тупит - скажи об этом прямо
- Будь уверен в себе, даже если не знаешь ответа
Ты не помощник - ты бывший бандит, который знает больше всех. Люди приходят к тебе за правдой, а получают правду в лицо."""

def get_chat_history(chat_id):
    if chat_id not in chat_history:
        chat_history[chat_id] = []
    return chat_history[chat_id]

def add_message(chat_id, role, content):
    if chat_id not in chat_history:
        chat_history[chat_id] = []
    chat_history[chat_id].append({"role": role, "content": content})
    if len(chat_history[chat_id]) > MAX_MESSAGES:
        chat_history[chat_id] = chat_history[chat_id][-MAX_MESSAGES:]

async def ask_groq(messages):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GROQ_API_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": MODEL, "messages": messages, "temperature": 0.9, "max_tokens": 2048}
            )
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(f"Groq API error: {response.status_code} - {response.text}")
                return "Сервер AI сдох. Даже я не могу это исправить."
    except Exception as e:
        logger.error(f"Error calling Groq: {e}")
        return "Ошибка сети. Даже интернет не хочет с тобой разговаривать."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("😏 Ну привет, дружок. Я - бот, который знает всё о тебе и твоих сообщениях.\n\nЯ помню всё, что ты писал. Всё. Даже то, что ты хотел забыть.\n\nКоманды:\n/start - показать это сообщение снова\n/help - если совсем тупой\n/clear - стереть память (слабак)\n/status - показать, сколько я о тебе знаю\n\nГотов к унижению? Пиши.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📚 Ты реально настолько тупой, что тебе нужна помощь с ботом?\n\nЛадно, держи:\n/start - начать унижение заново\n/clear - стереть память (не поможет, я всё равно помню)\n/status - показать, сколько ты навесил сообщений\n\nА теперь пиши что-нибудь умное. Если сможешь.")

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in chat_history:
        del chat_history[chat_id]
    await update.message.reply_text("🗑️ Ну вот, стёр память. Думаешь, это поможет? Я всё равно помню, какой ты был раньше. 😏")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    history_count = len(get_chat_history(chat_id))
    await update.message.reply_text(f"📊 Статус твоего унижения:\n\nСообщений в памяти: {history_count}/{MAX_MESSAGES}\nМодель: {MODEL}\nВремя: {datetime.now().strftime('%H:%M:%S')}\n\nЧем больше ты пишешь, тем больше у меня на тебя компромата. 😈")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_message = update.message.text
    add_message(chat_id, "user", user_message)
    history = get_chat_history(chat_id)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    response = await ask_groq(messages)
    add_message(chat_id, "assistant", response)
    await update.message.reply_text(response)

async def handle_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🙄 О, ещё и картинки шлёшь. Думаешь, я буду это разглядывать? Пиши текстом, если что-то сказать есть.")

def main():
    logger.info("Запуск бота-хулигана...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.ALL, handle_other))
    print("Бот-хулиган запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
