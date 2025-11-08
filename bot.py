#!/usr/bin/env python3
import os
import asyncio
import logging
import tempfile
from yt_dlp import YoutubeDL
from telegram import InputFile, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# قراءة التوكن من متغير البيئة
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
    "outtmpl": "%(title)s.%(ext)s",
    "geo_bypass": True,
    "ignoreerrors": True,
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

    try:
        video_path, size_mb = await asyncio.get_event_loop().run_in_executor(None, download_video, url)

        if not video_path:
            await waiting.edit_text("⚠️ لم أتمكن من تحميل الفيديو.")
            return

        if size_mb > MAX_TELEGRAM_MB:
            await waiting.edit_text(f"⚠️ حجم الفيديو ({size_mb:.1f}MB) أكبر من حد التحميل عبر تيليجرام.")
            return

        await waiting.edit_text("📤 جاري إرسال الفيديو...")

        async with await context.bot.send_video(
            chat_id=update.effective_chat.id,
            video=open(video_path, "rb"),
            caption="🎬 تم التحميل، احفظه من هنا 👇",
            supports_streaming=True,
        ):
            pass

        await waiting.edit_text("✅ تم التحميل والإرسال ❤️")
    except Exception as e:
        logger.exception("خطأ أثناء التحميل")
        await waiting.edit_text("⚠️ صار خطأ أثناء التحميل أو الموقع مانع التحميل.")
    finally:
        if "video_path" in locals() and os.path.exists(video_path):
            os.remove(video_path)


def download_video(url: str):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            opts = YTDL_OPTS.copy()
            opts["outtmpl"] = os.path.join(tmpdir, "%(id)s.%(ext)s")
            ydl = YoutubeDL(opts)
            info = ydl.extract_info(url, download=True)
            files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir)]
            if not files:
                return None, 0
            files.sort(key=lambda p: os.path.getsize(p), reverse=True)
            video_path = files[0]
            size_mb = os.path.getsize(video_path) / (1024 * 1024)
            temp_path = os.path.join("/tmp", os.path.basename(video_path))
            os.rename(video_path, temp_path)
            return temp_path, size_mb
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return None, 0


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
