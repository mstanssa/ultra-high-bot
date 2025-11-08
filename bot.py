#!/usr/bin/env python3
import os
import asyncio
import logging
import tempfile

from yt_dlp import YoutubeDL
from telegram import InputFile, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# نقرأ التوكن من متغير البيئة
BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ultra_high_bot")

YTDL_OPTS = {
    "format": "mp4[height<=720]/mp4/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "merge_output_format": "mp4",
}

MAX_TELEGRAM_MB = 48


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔥 أهلاً بك في Ultra High تحميل فيديوهات\n\n"
        "أرسل رابط من TikTok / YouTube / X / Facebook / Instagram.\n"
        "أنا أحمّل لك الفيديو وأرسله جاهز للحفظ 📥"
    )
    await update.message.reply_text(text)


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = (update.message.text or "").strip()

    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("🚫 أرسل رابط فيديو صحيح.")
        return

    waiting = await update.message.reply_text("⏳ جاري التحميل...")

    loop = asyncio.get_running_loop()
    ok, msg = await loop.run_in_executor(
        None, download_and_send, url, update.effective_chat.id, context
    )

    if ok:
        await waiting.edit_text("✅ تم التحميل والإرسال.")
    else:
        await waiting.edit_text(f"⚠️ {msg}")


def download_and_send(url: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            opts = YTDL_OPTS.copy()
            opts["outtmpl"] = os.path.join(tmpdir, "%(id)s.%(ext)s")

            ydl = YoutubeDL(opts)
            info = ydl.extract_info(url, download=True)

            files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir)]
            if not files:
                return False, "ما قدرت أطلع ملف من الرابط."

            files.sort(key=lambda p: os.path.getsize(p), reverse=True)
            video_path = files[0]
            size_mb = os.path.getsize(video_path) / (1024 * 1024)

            bot = context.bot

            if size_mb <= MAX_TELEGRAM_MB:
                with open(video_path, "rb") as f:
                    bot.send_video(
                        chat_id=chat_id,
                        video=InputFile(f, filename=os.path.basename(video_path)),
                        supports_streaming=True,
                    )
                return True, "تم الإرسال"

            return False, f"الفيديو حجمه ({size_mb:.1f}MB) أكبر من حد الإرسال عبر البوت."

    except Exception as e:
        logger.exception("خطأ أثناء التحميل")
        return False, "صار خطأ أثناء التحميل أو الموقع مانع التحميل."


def main():
    if not BOT_TOKEN:
        print("❌ TG_BOT_TOKEN غير موجود. ضعه في إعدادات Render كمتغير بيئة.")
        raise SystemExit(1)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    print("🚀 Ultra High Bot يعمل الآن...")
    app.run_polling(stop_signals=None)


if __name__ == "__main__":
    main()
