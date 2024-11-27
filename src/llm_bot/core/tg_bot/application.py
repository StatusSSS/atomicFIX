from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Optional
from venv import logger

from llm_bot.api.routes import router as routes

from fastapi import Depends, FastAPI
from loguru import logger
from pydantic import BaseModel
from starlette import status
from starlette.exceptions import HTTPException
from starlette.requests import Request
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from telegram.ext import (
    MessageHandler,
    filters,
)

from llm_bot.core.tg_bot.commands import start, user_message, callback_query_handler, new_chat_command, enable_chat_command
from llm_bot.api.core.tg_bot.kv_config import kv_settings
from llm_bot.api.core.tg_bot.model_config import model_settings
from llm_bot.api.core.tg_bot.telegram_bot_config import telegram_bot_config
from llm_bot.api.security.security import get_admin_username
from llm_bot.core.db.database import init_db, AsyncSession
from llm_bot.core.db.repository import set_value, get_value, get_keys, bulk_set_if_not_exists
from llm_bot.core.db.utils import get_session


@lru_cache
def get_telegram_application() -> Application:
    application = Application.builder().token(telegram_bot_config.TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("new_chat", new_chat_command))
    # application.add_handler(CommandHandler("chats", chat_command))
    application.add_handler(CommandHandler("chat", enable_chat_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_message))
    application.add_handler(CallbackQueryHandler(callback_query_handler))

    return application


async def set_webhook(url: Optional[str] = None):
    if url is None:
        url = telegram_bot_config.WEBHOOK_URL
    application = get_telegram_application()
    status = await application.bot.set_webhook(url=url)
    if not status:
        logger.error(f"Failed to set webhook with URL: {url}")
        return False
    logger.info(f"Webhook set successfully with URL: {url}")
    return True


async def set_commands(application: Application):
    await application.bot.set_my_commands(
        [
            BotCommand('start', 'Start the bot'),
            BotCommand('new_chat', 'Create a new chat'),
            BotCommand('chat', 'Enable or disable a chat menu'),
            # BotCommand('chats', 'Manage your chats'),

        ],
    )
    logger.info("Commands set successfully")


@asynccontextmanager
async def telegram_application_lifespan(app):
    application = get_telegram_application()
    async with application:
        await set_commands(application)
        await init_db()

        await application.start()

        await set_webhook()

        async with AsyncSession() as session:
            await bulk_set_if_not_exists(
                session,
                {
                    kv_settings.ai_model_promt_key: model_settings.promt,
                    kv_settings.ai_model_base_url_key: model_settings.base_url,
                    kv_settings.ai_model_openai_api_key_key: model_settings.openai_api_key,
                    kv_settings.ai_model_temperature_key: model_settings.temperature,
                    kv_settings.ai_model_max_tokens_key: model_settings.max_tokens,
                    kv_settings.ai_model_openai_default_model_key: model_settings.openai_default_model,
                    kv_settings.ai_model_edit_interval_key: model_settings.edit_interval,
                    kv_settings.ai_model_initial_token_threshold_key: model_settings.initial_token_threshold,
                    kv_settings.ai_model_typing_interval_key: model_settings.typing_interval,
                }
            )

        yield
        await application.stop()
        # await database.teardown()


app = FastAPI(
    lifespan=telegram_application_lifespan
)

app.include_router(routes)