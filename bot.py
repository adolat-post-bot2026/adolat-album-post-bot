
import os
import asyncio
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

albums = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Матнни юборинг, кейин фотоларни юборинг. "
        "Тугатгач /done буйруғини беринг."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message

    if user_id not in albums:
        albums[user_id] = {"text": "", "photos": []}

    if message.text:
        albums[user_id]["text"] += message.text + "\n"
    elif message.photo:
        albums[user_id]["photos"].append(message.photo[-1].file_id)

    await message.reply_text("Қабул қилинди.")

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = albums.get(user_id)

    if not data:
        await update.message.reply_text("Аввал матн ёки фото юборинг.")
        return

    if not BOT_TOKEN or not CHANNEL_ID:
        await update.message.reply_text("Бот созламалари тўлиқ эмас.")
                  return 
        try:
            text = data["text"].strip()
            photos = data["photos"]

            if text:
                text_message = await context.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=text
                )
            else:
                text_message = None

            if photos:
                media = [
                    InputMediaPhoto(media=photo_id)
                    for photo_id in photos[:10]
                ]

              
                sent_album = await context.bot.send_media_group(
                    chat_id=CHANNEL_ID,
                    media=media,
                    reply_to_message_id=(
                        text_message.message_id
                        if text_message else None
                    )
                )


           
            albums.pop(user_id, None)
            await update.message.reply_text("Каналга жойланди!")

        except Exception as error:
            await update.message.reply_text(
                f"Жойлашда хато юз берди: {error}"
            )


async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND | filters.PHOTO,
        handle_message
    ))
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
