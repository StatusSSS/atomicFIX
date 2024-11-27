from fastapi import APIRouter, Depends, HTTPException, status
from telegram import Update, BotCommand
from telegram.ext import Application
from llm_bot.core.tg_bot.commands import start, user_message, callback_query_handler, new_chat_command, enable_chat_command
from llm_bot.core.config.telegram_bot_config import telegram_bot_config
from llm_bot.core.config.kv_config import kv_settings

from llm_bot.core.tg_bot.application import get_telegram_application, set_webhook
from llm_bot.core.db.repository import set_value, get_value, get_keys
from llm_bot.core.db.utils import get_session
from llm_bot.api.security.security import get_admin_username
from pydantic import BaseModel
from starlette.requests import Request

router = APIRouter()

class WebhookRequest(BaseModel):
    url: str

class KVRequest(BaseModel):
    key: str
    value: str

@router.post("/webhook")
async def webhook_handler(
    request: Request,
    application: Application = Depends(get_telegram_application),
):
    data = await request.json()
    await application.process_update(Update.de_json(data=data, bot=application.bot))

@router.post("/set-webhook")
async def set_webhook_endpoint(
    webhook_request: WebhookRequest,
    username: str = Depends(get_admin_username),
):
    success = await set_webhook(webhook_request.url)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to set webhook")
    return {"message": "Webhook set successfully", "url": webhook_request.url}

@router.post("/set-value")
async def set_value_endpoint(
    kv_request: KVRequest,
    username: str = Depends(get_admin_username),
    session=Depends(get_session),
):
    await set_value(session, key=kv_request.key, value=kv_request.value)
    return {"message": "Value set successfully", "key": kv_request.key, "value": kv_request.value}

@router.get("/get-value")
async def get_value_endpoint(
    key: str,
    username: str = Depends(get_admin_username),
    session=Depends(get_session),
):
    value = await get_value(session, key)
    return {"key": key, "value": value}

@router.get("/get-keys")
async def get_keys_endpoint(
    username: str = Depends(get_admin_username),
    session=Depends(get_session),
):
    keys = await get_keys(session)
    return {"keys": keys}
