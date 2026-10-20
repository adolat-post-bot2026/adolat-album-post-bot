    )
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(
            "Telegraph мақоласини яратиб бўлмади: "
            + str(result.get("error", "номаълум хато"))
        )
    return result["result"]["url"]


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id
    data = albums.get(user_id)

    if not data or (not data["text"].strip() and not data["photos"]):
        await update.message.reply_text("Аввал матн ёки сурат юборинг.")
        return

    if not BOT_TOKEN or not CHANNEL_ID:
        await update.message.reply_text(
            "Бот созламалари тўлиқ эмас. BOT_TOKEN ва CHANNEL_ID ни текширинг."
        )
        return

    text = data["text"].strip()
    photos = data["photos"]

    if not text:
        await update.message.reply_text(
            "Илтимос, аввал мақола матнини ҳам юборинг."
        )
        return

    status = await update.message.reply_text(
        "Мақола тайёрланяпти. Бироз кутинг..."
    )

    try:
        # Telegraph API синхрон бўлгани учун алоҳида оқимда ишлатамиз.
        article_url = await asyncio.to_thread(create_telegraph_page, text)

        # Альбомга тўлиқ матн эмас, мақола ҳаволаси ва қисқа сарлавҳа қўшилади.
        title = next((line.strip() for line in text.splitlines() if line.strip()), "Янги мақола")
        caption = f"{title[:700]}\n\nТўлиқ мақола: {article_url}"
        caption = caption[:1024]

        if photos:
            # Telegram media group bir yuborishda 2–10 ta surat oladi.
            # Birinchi albomga sarlavha va Telegraph havolasi biriktiriladi.
            first_batch = photos[:10]
            if len(first_batch) == 1:
                await context.bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=first_batch[0],
                    caption=caption,
                )
            else:
                media = [
                    InputMediaPhoto(
                        media=photo_id,
                        caption=caption if index == 0 else None,
                    )
                    for index, photo_id in enumerate(first_batch)
                ]
                await context.bot.send_media_group(
                    chat_id=CHANNEL_ID,
                    media=media,
                )

            # 10 tadan ortiq surat bo'lsa, qolganlarini keyingi albomlarga yuboramiz.
            remaining = photos[10:]
            while remaining:
                batch = remaining[:10]
                if len(batch) == 1:
                    await context.bot.send_photo(
                        chat_id=CHANNEL_ID,
                        photo=batch[0],
                    )
                else:
                    await context.bot.send_media_group(
                        chat_id=CHANNEL_ID,
                        media=[InputMediaPhoto(media=photo_id) for photo_id in batch],
                    )
                remaining = remaining[10:]
        else:
            # Surat bo'lmasa, kanalga maqola havolasini matn ko'rinishida yuboramiz.
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"{title[:700]}\n\nТўлиқ мақола: {article_url}",
                disable_web_page_preview=False,
            )

        albums.pop(user_id, None)
        await status.edit_text(
            "Каналга жойланди! Суратлар постда, тўлиқ матн эса Telegraph ҳаволасида."
        )

    except Exception as error:
        await status.edit_text(
            "Жойлашда хато юз берди. Қуйидаги хабарни текширинг:\n"
            f"{str(error)[:1200]}"
        )


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN муҳит ўзгарувчиси киритилмаган.")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(
        MessageHandler(
            (filters.TEXT & ~filters.COMMAND) | filters.PHOTO,
            handle_message,
        )
    )

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()


