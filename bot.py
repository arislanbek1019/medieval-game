import logging
import os
from collections import defaultdict

from openai import OpenAI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# --- Настройки ---
TELEGRAM_TOKEN = "8789203612:AAHb39qBp03lDJ8RDm1U1LbmeKTTigidXl8"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "ВАШ_OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"  # можно заменить на другую модель
SYSTEM_PROMPT = "Ты дружелюбный и полезный ассистент."
MAX_HISTORY_MESSAGES = 20  # сколько последних сообщений хранить на пользователя

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Память диалогов: user_id -> список сообщений [{"role": ..., "content": ...}]
user_histories: dict[int, list[dict]] = defaultdict(list)


def trim_history(history: list[dict]) -> list[dict]:
    """Оставляем только последние N сообщений, чтобы не раздувать запросы."""
    if len(history) > MAX_HISTORY_MESSAGES:
        return history[-MAX_HISTORY_MESSAGES:]
    return history


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text(
        "Привет! Я бот с искусственным интеллектом. Просто напиши мне сообщение, "
        "и я отвечу. Используй /reset, чтобы очистить историю диалога."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text("История диалога очищена.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_text = update.message.text

    history = user_histories[user_id]
    history.append({"role": "user", "content": user_text})
    history = trim_history(history)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
        )
        reply_text = response.choices[0].message.content
    except Exception as e:
        logger.error(f"Ошибка при обращении к OpenAI: {e}")
        reply_text = "Извини, произошла ошибка при обработке запроса. Попробуй позже."
        await update.message.reply_text(reply_text)
        return

    history.append({"role": "assistant", "content": reply_text})
    user_histories[user_id] = trim_history(history)

    await update.message.reply_text(reply_text)


def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
