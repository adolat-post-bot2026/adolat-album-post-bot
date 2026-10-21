import os
import json
import asyncio
import requests

from telegram import (
    Update,
    InputMediaPhoto,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
TELEGRAPH_ACCESS_TOKEN = os.getenv("TELEGRAPH_ACCESS_TOKEN", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()

albums = {}
pending_drafts = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Аввал 1–10 та сурат юборинг. "
        "Кейин мақоланинг тўлиқ матнини юборинг. "
        "Тугатгач /done буйруғини беринг.\n\n"
        "AI журналист таҳрири учун матнни юбориб, /ai буйруғини беринг. "
        "Тайёрланган матн фақат тасдиқласангиз каналга чиқади."
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


def generate_ai_draft(source_text: str) -> dict:
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY созланмаган. FadeHost муҳитида ушбу ўзгарувчини текширинг."
        )

    prompt = f"""
Сиз Ўзбекистондаги маҳаллий тадбирлар ва жамоатчилик ҳаётини ёритадиган тажрибали журналист-муҳаррирсиз.
Манба матни асосида профессионал, равон ва таҳрирга тайёр журналистик материал тайёрланг. Асосий тил — ўзбек тилининг кирилл ёзуви.

МАҚОЛА ҲАЖМИ ВА ТУЗИЛИШИ:
- "article" қисми учун мақсадли ҳажм: 500–700 сўз.
- Мақолани мазмунли сарлавҳа/кириш, асосий қисм ва якунловчи абзац билан тузинг.
- Бир фикрни турли сўзлар билан такрорлаб ҳажм тўлдирманг; ҳар бир абзац мақоланинг мазмунига хизмат қилсин.
- Манбадаги маълумотларни тартибга солинг, муҳим жиҳатларни тушунарлироқ баён қилинг ва журналистик боғланишларни яхшиланг.
- Агар манба 500–700 сўзлик мақола ёзиш учун етарли факт бермаса, ҳажмни тўлдириш учун факт тўқиманг. Бундай ҳолда ҳақиқий маълумотни устун қўйиб, имкон қадар мазмунли мақола ёзинг; етишмаган маълумотларни алоҳида тўқиб чиқарманг.

ФАКТЛАР БЎЙИЧА ҚАТЪИЙ ҚОИДАЛАР:
- Манбада йўқ исмлар, саналар, манзиллар, ташкилотлар, лавозимлар, иштирокчилар, рақамлар, иқтибослар, қарорлар, натижалар ёки тадбир тафсилотларини ҚЎШМАНГ.
- Тадбир ташкилотчиси, қатнашчилар сони, ким нутқ сўзлагани ёки қандай қарор қабул қилингани берилмаган бўлса, уларни тахмин қилманг.
- Умумий ижтимоий аҳамиятни шарҳлаш мумкин, аммо умумий фикрларни тадбирда аниқ айтилган гап ёки тасдиқланган воқеа сифатида кўрсатманг.
- Манбадаги маълумотни ўзгартирманг, муболаға қилманг ва асоссиз хулоса чиқарманг.
- Агар манбада маълумот етишмаса, мақола ҳажмини сақлашдан кўра фактларнинг аниқлигини устун қўйинг.

УСЛУБ ВА ЁЗУВ:
- Матбуот учун мос, холис, расмий-журналистик услубда ёзинг.
- Ўзбек тилида табиий эшитиладиган сўз ва ибораларни танланг; сўзма-сўз таржимага ўхшаган, сунъий ёки ўзбек тилида маъно бермайдиган ифодаларни ишлатманг.
- Ҳар бир жумлани грамматик ва мантиқий жиҳатдан текширинг: эга-кесим мослиги, келишик қўшимчалари, сўз тартиби ва фикрнинг аниқлиги тўғри бўлсин.
- «фаолият тактикларида эгалик этувчи рўли», «фикрлашдилар», «бу иборатувчи тадбир» каби нотабиий бирикмаларни ишлатманг; шубҳали иборани содда ва аниқ ўзбекча жумлага айлантиринг.
- Манбада тадбирда нима муҳокама қилингани ёки ким нима дегани аниқ берилмаган бўлса, буни аниқ воқеа сифатида баён қилманг. Умумий хулосаларни ҳам тадбирда айтилган гапдек кўрсатманг.
- Имло, грамматика, услуб, жумлалар орасидаги мантиқий боғланиш ва абзацлар тузилишини яхшиланг.
- Барча ўзбекча матнни кирилл алифбосида беринг. Ўзбекча лотин ёзувини қолдирманг. Халқаро қисқартмалар ва бренд номлари зарур бўлса асл ёзувида қолиши мумкин.
- "short_post" қисми 2–3 гапдан иборат, Telegram учун қисқа ва мазмунли бўлсин.
- "headlines" қисмида 3–5 та бир-биридан фарқли, аниқ ва журналистик сарлавҳа бўлсин.
- Натижани фақат тўғри JSON объект сифатида қайтаринг; Markdown белгиси ёки қўшимча изоҳ қўшманг.
- JSON калитлари айнан қуйидагича бўлсин: "article", "short_post", "headlines". "article" ва "short_post" матн, "headlines" эса сарлавҳалар рўйхати бўлсин.

МАНБА МАТНИ:
{source_text}
""".strip()

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://t.me/Adolat_Toshvil_post_bot",
            "X-Title": "Adolat SDP Journalist Editor",
        },
        json={
            "model": OPENROUTER_MODEL or "openrouter/free",
            "messages": [
                {
                    "role": "system",
                    "content": "Фақат JSON объект қайтаринг. Манбада бўлмаган фактларни қўшманг.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        },
        timeout=90,
    )

    if not response.ok:
        try:
            detail = response.json().get("error", {}).get("message", response.text)
        except Exception:
            detail = response.text
        raise RuntimeError(f"OpenRouter хатоси ({response.status_code}): {detail[:500]}")

    payload = response.json()
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("AI жавоб қайтармади.")

    content = choices[0].get("message", {}).get("content", "")
    if isinstance(content, list):
        content = "".join(
            item.get("text", "") for item in content if isinstance(item, dict)
        )
    content = str(content).strip()
    if content.startswith("```"):
        content = content.replace("```json", "", 1).replace("```", "").strip()

    try:
        draft = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            draft = json.loads(content[start:end + 1])
        else:
            raise RuntimeError("AI жавоби JSON шаклида эмас. Қайта уриниб кўринг.")

    article = str(draft.get("article", "")).strip()
    short_post = str(draft.get("short_post", "")).strip()
    headlines = draft.get("headlines", [])
    if isinstance(headlines, str):
        headlines = [line.strip(" -*•\t") for line in headlines.splitlines() if line.strip()]
    if not isinstance(headlines, list):
        headlines = []
    headlines = [str(item).strip() for item in headlines if str(item).strip()][:5]

    if not article or not short_post:
        raise RuntimeError("AI жавобида мақола ёки қисқа пост етишмаяпти.")

    return {
        "article": article,
        "short_post": short_post,
        "headlines": headlines[:5],
    }


def proofread_ai_draft(source_text: str, draft: dict) -> dict:
    """Second editorial pass: fix language and logic without inventing facts."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY созланмаган. FadeHost муҳитида ушбу ўзгарувчини текширинг."
        )

    prompt = f"""
Сиз биринчи таҳрирдан ўтган журналистик матнни нашр олдидан текширадиган катта муҳаррирсиз.
Вазифангиз — матнни қайтадан узайтириш эмас, унинг тили ва мантиғини пухта таҳрир қилиш.

ҚАТЪИЙ ТАЛАБЛАР:
1. Фақат ўзбек кирилл алифбосида, табиий ва равон адабий тилда ёзинг.
2. Ўзбек тилида табиий ишлатиладиган сўз ва ибораларни танланг. Сўзма-сўз таржимага ўхшаган, сунъий, тушунарсиз ёки ўзбек тилида маъно бермайдиган бирикмаларни қолдирманг.
3. Имло, грамматика, келишик, сўз танлаш ва жумлалар қурилишини тузатинг. Эга-кесим мослиги, сўз тартиби ва фикрнинг мантиқий изчиллигини текширинг.
4. Маъноси ноаниқ, сунъий, таржимадан чиққанга ўхшаш ёки мантиқан нотўғри жумлаларни табиий қилиб қайта ёзинг.
5. Бир фикрни такрорлайдиган жумлалар ва мазмунсиз умумий гапларни олиб ташланг.
6. Ҳар бир абзац аниқ маълумот берсин. Мақолани ҳажм учун сунъий равишда узайтирманг.
7. Фақат МАНБА МАТНИда тасдиқланган фактларни сақланг. Қатнашчилар, ташкилотчилар, саналар, манзиллар, иқтибослар, қарорлар ва натижаларни ўйлаб топманг.
8. Биринчи лойиҳада пайдо бўлган, аммо манбада тасдиқланмаган даъво ёки тафсилотларни олиб ташланг.
9. М. Бердиқулова, Ж. Номозов каби номлар, мактаб рақами ва бошқа маълумотларни манбадаги шаклда сақланг; янги маълумот қўшманг.
10. Сарлавҳалар аниқ, табиий ва бир-биридан фарқли бўлсин. Қисқа пост 2–3 гапдан иборат бўлсин.
11. Мақола 500–700 сўз бўлиши мақсад қилинади, аммо манба маълумоти кам бўлса, такрор ёки тахмин билан ҳажмни тўлдирманг.
11. Жавобни фақат тўғри JSON шаклида қайтаринг: {{"article":"...", "short_post":"...", "headlines":["...", "..."]}}. Markdown ёки изоҳ қўшманг.

АСЛ МАНБА:
{source_text}

БИРИНЧИ ЛОЙИҲА:
{json.dumps(draft, ensure_ascii=False)}
""".strip()

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://t.me/Adolat_Toshvil_post_bot",
            "X-Title": "Adolat SDP Journalist Proofreader",
        },
        json={
            "model": OPENROUTER_MODEL or "openrouter/free",
            "messages": [
                {
                    "role": "system",
                    "content": "Сиз фактларга содиқ ўзбек тили муҳарририсиз. Фақат JSON қайтаринг.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        },
        timeout=90,
    )

    if not response.ok:
        try:
            detail = response.json().get("error", {}).get("message", response.text)
        except Exception:
            detail = response.text
        raise RuntimeError(
            f"AI иккинчи таҳрир босқичида хато ({response.status_code}): {detail[:400]}"
        )

    payload = response.json()
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("AI иккинчи таҳрир босқичида жавоб қайтармади.")

    content = choices[0].get("message", {}).get("content", "")
    if isinstance(content, list):
        content = "".join(
            item.get("text", "") for item in content if isinstance(item, dict)
        )
    content = str(content).strip()
    if content.startswith("```"):
        content = content.replace("```json", "", 1).replace("```", "").strip()

    try:
        reviewed = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("AI иккинчи таҳрир жавоби JSON шаклида эмас.")
        reviewed = json.loads(content[start:end + 1])

    article = str(reviewed.get("article", "")).strip()
    short_post = str(reviewed.get("short_post", "")).strip()
    headlines = reviewed.get("headlines", [])
    if isinstance(headlines, str):
        headlines = [
            line.strip(" -*•\t") for line in headlines.splitlines() if line.strip()
        ]
    if not isinstance(headlines, list):
        headlines = []
    headlines = [str(item).strip() for item in headlines if str(item).strip()][:5]

    if not article or not short_post:
        raise RuntimeError("AI иккинчи таҳрир натижасида мақола ёки қисқа пост йўқ.")

    return {"article": article, "short_post": short_post, "headlines": headlines}


async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id
    data = albums.get(user_id, {})
    source_text = str(data.get("text", "")).strip()

    if not source_text:
        await update.message.reply_text(
            "Аввал мақоланинг тўлиқ матнини юборинг, кейин /ai буйруғини беринг."
        )
        return

    if not OPENROUTER_API_KEY:
        await update.message.reply_text(
            "AI калити топилмади. FadeHost муҳитида OPENROUTER_API_KEY ўзгарувчиси борлигини текширинг."
        )
        return

    await update.message.reply_text("AI журналист матнни таҳрирламоқда. Бироз кутинг...")
    try:
        draft = await asyncio.to_thread(generate_ai_draft, source_text)
        # Иккинчи босқич: имло, мантиқ, такрор ва фактларга содиқликни текшириш.
        try:
            draft = await asyncio.to_thread(proofread_ai_draft, source_text, draft)
        except Exception as review_error:
            # Иккинчи босқич ишламаса ҳам биринчи лойиҳа йўқолмасин; фойдаланувчига хабар берилади.
            await update.message.reply_text(
                "Эслатма: автоматик иккинчи таҳрир босқичи ишламади; "
                f"биринчи лойиҳа текширувсиз кўрсатилади. Сабаб: {review_error}"
            )
        pending_drafts[user_id] = draft

        headlines = "\n".join(
            f"{index}. {headline}"
            for index, headline in enumerate(draft["headlines"], start=1)
        ) or "Сарлавҳа вариантлари берилмади."

        preview_header = (
            "📝 AI журналист таҳрири тайёр\n\n"
            "САРЛАВҲА ВАРИАНТЛАРИ:\n"
            f"{headlines}\n\n"
            "ҚИСҚА TELEGRAM ПОСТИ:\n"
            f"{draft['short_post']}\n\n"
            "ТЎЛИҚ МАҚОЛА (матн қуйида тўлиқ берилган):"
        )
        # Telegram хабарларининг узунлик чекловига риоя қилиб, бутун мақолани кўрсатамиз.
        full_preview = preview_header + "\n\n" + draft["article"]
        chunks = []
        while len(full_preview) > 3500:
            split_at = full_preview.rfind("\n", 0, 3500)
            if split_at < 1000:
                split_at = 3500
            chunks.append(full_preview[:split_at])
            full_preview = full_preview[split_at:].lstrip("\n")
        if full_preview:
            chunks.append(full_preview)

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "✅ Тасдиқлаш ва нашр этиш",
                    callback_data="ai_approve",
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Бекор қилиш",
                    callback_data="ai_cancel",
                )
            ],
        ])
        for index, chunk in enumerate(chunks):
            is_last = index == len(chunks) - 1
            await update.message.reply_text(
                chunk,
                reply_markup=keyboard if is_last else None,
            )
    except Exception as error:
        await update.message.reply_text(f"AI матн тайёрлай олмади: {error}")


async def ai_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.from_user:
        return

    user_id = query.from_user.id
    draft = pending_drafts.get(user_id)

    if query.data == "ai_cancel":
        pending_drafts.pop(user_id, None)
        await query.answer("Таҳрир бекор қилинди.")
        try:
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text("AI таҳрири бекор қилинди. Каналга ҳеч нарса жойланмади.")
        except Exception:
            pass
        return

    if query.data != "ai_approve":
        await query.answer()
        return

    if not draft:
        await query.answer("Тасдиқлаш учун сақланган матн топилмади.", show_alert=True)
        return

    if not CHANNEL_ID:
        await query.answer("CHANNEL_ID созламаси топилмади.", show_alert=True)
        return

    await query.answer("Нашр тайёрланмоқда...")
    data = albums.get(user_id, {"photos": []})
    photos = data.get("photos", [])

    try:
        article_url = await asyncio.to_thread(create_telegraph_page, draft["article"])
        caption = f"{draft['short_post']}\n\nТўлиқ мақола: {article_url}"

        if photos:
            media = []
            for index, photo_id in enumerate(photos[:10]):
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
