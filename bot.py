#!/usr/bin/env python3
import os
import asyncio
import logging
import tempfile
from yt_dlp import YoutubeDL
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputFile,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# إعدادات أساسية
# =========================
BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
CHANNEL_USERNAME = "@free0GM"
MAX_TELEGRAM_MB = 48

YTDL_OPTS = {
    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
    "merge_output_format": "mp4",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "geo_bypass": True,
    "ignoreerrors": True,
    "outtmpl": "%(title)s.%(ext)s",
    "retries": 10,
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "en-US,en;q=0.9",
    },
}

# =========================
# تسجيل الأخطاء
# =========================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("kinga_downloader")

# =========================
# دالة التحقق من الاشتراك
# =========================
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False


# =========================
# رسالة التحقق من الاشتراك
# =========================
async def ask_to_join(update: Update):
    keyboard = [
        [InlineKeyboardButton("📡 قناة البوت الرسمية", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("🔘 تم الاشتراك | Subscribed", callback_data="check_sub")]
    ]
    text = (
        "🚫 لا يمكنك استخدام البوت حالياً!\n\n"
        "لتفعيل حسابك، اشترك أولاً في القناة الرسمية:\n"
        f"{CHANNEL_USERNAME}\n\n"
        "ثم اضغط أدناه لتأكيد المتابعة 👇"
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# =========================
# رسالة الترحيب
# =========================
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌐 تغيير اللغة | Change Language", callback_data="lang"),
        ],
        [
            InlineKeyboardButton("💎 اشتراك VIP (قريباً)", callback_data="vip"),
            InlineKeyboardButton("📡 القناة الرسمية", url="https://t.me/free0GM"),
        ],
    ])


WELCOME_TEXT = (
    "🎉 **تم التحقق من اشتراكك بنجاح**\n\n"
    "👋 مرحباً بك في بوت *Kinga Downloader*\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "⚡️ الآن يمكنك تحميل الفيديوهات من المنصات التالية:\n"
    "📱 TikTok  |  YouTube  |  Instagram  |  Twitter  |  Facebook\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "🎬 أرسل أي رابط وسأقوم بتحميله لك مباشرة.\n\n"
    "🌐 يمكنك تغيير اللغة من الزر أدناه:"
)


# =========================
# /start
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update, context):
        await ask_to_join(update)
        return

    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )


# =========================
# تحميل الفيديو
# =========================
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update, context):
        await ask_to_join(update)
        return

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
        await context.bot.send_video(
            chat_id=update.effective_chat.id,
            video=open(video_path, "rb"),
            caption="🎬 تم التحميل، احفظه من هنا 👇",
            supports_streaming=True,
        )

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
            print(f"✅ Downloaded: {temp_path} ({size_mb:.1f}MB)")
            return temp_path, size_mb
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return None, 0


# =========================
# تشغيل البوت
# =========================
def main():
    if not BOT_TOKEN:
        print("❌ TG_BOT_TOKEN غير موجود. ضعه في إعدادات Render كمتغير بيئة.")
        raise SystemExit(1)

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    print("🚀 Kinga Downloader يعمل الآن...")
    app.run_polling(stop_signals=None)


if __name__ == "__main__":
    main()
