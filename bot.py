import os
import asyncio
import html
import requests

from telegram import Update, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
TELEGRAPH_ACCESS_TOKEN = os.getenv("TELEGRAPH_ACCESS_TOKEN", "").strip()

# Har bir foydalanuvchi yuborgan matn va suratlarni vaqtincha saqlash
albums = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Аввал тўлиқ матнни юборинг, кейин 1–10 тагача сурат юборинг. "
        "Тугатгач /done буйруғини беринг. "
        "Матн Telegraph мақоласига жойланади, каналга суратлар ва мақола ҳаволаси чиқади."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id
    message = update.message

    if user_id not in albums:
        albums[user_id] = {"text": "", "photos": []}

    if message.text:
        albums[user_id]["text"] += message.text + "\n"
        await message.reply_text("Матн қабул қилинди.")
    elif message.photo:
        albums[user_id]["photos"].append(message.photo[-1].file_id)
        await message.reply_text(
            f"Сурат қабул қилинди. Жами суратлар: {len(albums[user_id]['photos'])}"
        )


def create_telegraph_page(full_text: str) -> str:
    """Telegraph API orqali to'liq matnli maqola yaratadi."""
    access_token = TELEGRAPH_ACCESS_TOKEN

    if not access_token:
        account_response = requests.post(
            "https://api.telegra.ph/createAccount",
            data={
                "short_name": "AdolatPostBot",
                "author_name": "Adolat SDP Toshkent viloyati",
            },
            timeout=30,
        )
        account_response.raise_for_status()
        account_data = account_response.json()
        if not account_data.get("ok"):
            raise RuntimeError(
                "Telegraph akkauntini yaratib bo'lmadi: "
                + str(account_data.get("error", "noma'lum xato"))
            )
        access_token = account_data["result"]["access_token"]

    # Telegraph sarlavhasi sifatida matnning birinchi qatoridan foydalanamiz.
    lines = [line.strip() for line in full_text.splitlines() if line.strip()]
    title = (lines[0] if lines else "Янги мақола")[:256]

    # Matnni abzatslarga ajratamiz; matn oddiy matn sifatida yuboriladi.
    content = []
    for paragraph in full_text.splitlines():
        paragraph = paragraph.strip()
        if paragraph:
            content.append({"tag": "p", "children": [paragraph]})

    if not content:
        content = [{"tag": "p", "children": ["Матн берилмаган."]}]

    response = requests.post(
        "https://api.telegra.ph/createPage",
        data={
            "access_token": access_token,
            "title": title,
            "author_name": "Adolat SDP Toshkent viloyati",
            "content": __import__("json").dumps(content, ensure_ascii=False),
            "return_content": "false",
        },
        timeout=30,
