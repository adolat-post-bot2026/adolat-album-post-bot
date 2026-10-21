                if index == 0:
                    media.append(
                        InputMediaPhoto(
                            media=photo_id,
                            caption=caption[:1024],
                        )
                    )
                else:
                    media.append(InputMediaPhoto(media=photo_id))
            await context.bot.send_media_group(chat_id=CHANNEL_ID, media=media)
        else:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=caption[:4096])

        pending_drafts.pop(user_id, None)
        albums.pop(user_id, None)
        try:
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text("✅ Тасдиқланди ва каналга нашр этилди!")
        except Exception:
            pass
    except Exception as error:
        await query.message.reply_text(
            f"Нашр қилишда хатолик юз берди: {error}\n"
            "Матн тасдиқланган ҳолда сақланди; хатони тузатиб, яна уриниб кўриш мумкин."
        )


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    data = albums.get(user_id)

    if not data:
        await update.message.reply_text("Аввал матн ёки сурат юборинг.")
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
            article_url = await asyncio.to_thread(create_telegraph_page, text)

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
        await update.message.reply_text(f"Хатолик юз берди: {error}")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN созламаси топилмади.")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("ai", ai_command))
    app.add_handler(CallbackQueryHandler(ai_callback, pattern=r"^ai_(approve|cancel)$"))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
