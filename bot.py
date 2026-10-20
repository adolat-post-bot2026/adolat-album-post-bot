
import os
import json
import asyncio
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

albums = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        
            "Аввал 1–10 та сурат юборинг. "
            "Кейин мақоланинг тўлиқ матнини юборинг. "
            "Тугатгач /done буйруғини беринг."

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
            f"Сурат қабул қилинди. Жами: {len(albums[user_id]['photos'])}"
        )


def create_telegraph_page(full_text: str) -> str:
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
                "Telegraph аккаунти яратилмади: "
                + str(account_data.get("error", "номаълум хато"))
            )

        access_token = account_data["result"]["access_token"]

    lines = [line.strip() for line in full_text.splitlines() if line.strip()]
    title = (lines[0] if lines else "Янги мақола")[:256]

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
            "content": json.dumps(content, ensure_ascii=False),
            "return_content": "false",
        },
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(
            "Telegraph мақоласи яратилмади: "
            + str(result.get("error", "номаълум хато"))
        )

    return result["result"]["url"]


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    data = albums.get(user_id)

    if not data:
        await update.message.reply_text(
            "Аввал матн ёки сурат юборинг."
        )
        return

    text = data["text"].strip()
    photos = data["photos"]

    if not text and not photos:
        await update.message.reply_text("Матн ёки сурат юборилмаган.")
        return

    if not CHANNEL_ID:
        await update.message.reply_text("CHANNEL_ID созламаси топилмади.")
        return

    try:
        article_url = None

        if text:
            article_url = await asyncio.to_thread(
                create_telegraph_page, text
            )

        
        if text and article_url:
            short_text = text[:700].strip()
            post_text = f"{short_text}\n\nТўлиқ мақола: {article_url}"
        elif article_url:
            post_text = f"Тўлиқ мақола: {article_url}"
        else:
            post_text = text[:700].strip()

        if photos:
            media = []
            for index, photo_id in enumerate(photos[:10]):
                if index == 0:
                    media.append(
                        InputMediaPhoto(
                            media=photo_id,
                            caption=post_text[:1024] if post_text else None
                        )
                    )
                else:
                    media.append(InputMediaPhoto(media=photo_id))

            await context.bot.send_media_group(
                chat_id=CHANNEL_ID,
                media=media,
            )
        elif post_text:
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=post_text[:4096],
            )


        albums.pop(user_id, None)
        await update.message.reply_text("Каналга жойланди!")

    except Exception as error:
        await update.message.reply_text(
            f"Хатолик юз берди: {error}"
        )


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN созламаси топилмади.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
