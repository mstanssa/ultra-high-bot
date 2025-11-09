#!/usr/bin/env python3
import os, asyncio, logging, tempfile, json
from yt_dlp import YoutubeDL
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, CallbackQueryHandler, filters
)

# =========================
# إعدادات عامة
# =========================
BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
CHANNEL_USERNAME = "@free0GM"
MAX_TELEGRAM_MB = 48
COOKIE_FILE = "/etc/secrets/youtube_cookies.txt" if os.path.exists("/etc/secrets/youtube_cookies.txt") else None

LANGUAGES = {
    "ar": "🇸🇦 العربية",
    "en": "🇺🇸 English",
    "ru": "🇷🇺 Русский",
    "uk": "🇺🇦 Українська",
    "hi": "🇮🇳 हिंदी",
    "fa": "🇮🇷 فارسی"
}

# =========================
# اللغة الافتراضية
# =========================
def get_user_lang(user_id):
    try:
        with open("users_lang.json", "r", encoding="utf-8") as f:
            langs = json.load(f)
        return langs.get(str(user_id), "ar")
    except:
        return "ar"

def set_user_lang(user_id, lang):
    try:
        langs = {}
        if os.path.exists("users_lang.json"):
            with open("users_lang.json", "r", encoding="utf-8") as f:
                langs = json.load(f)
        langs[str(user_id)] = lang
        with open("users_lang.json", "w", encoding="utf-8") as f:
            json.dump(langs, f)
    except:
        pass

# =========================
# إعداد yt-dlp
# =========================
YTDL_OPTS = {
    "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
    "merge_output_format": "mp4",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "geo_bypass": True,
    "ignoreerrors": True,
    "retries": 10,
    "http_headers": {"User-Agent": "Mozilla/5.0"},
}
if COOKIE_FILE:
    YTDL_OPTS["cookiefile"] = COOKIE_FILE

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("kinga_final")

# =========================
# التحقق من الاشتراك
# =========================
async def check_subscription(update, context):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

async def ask_to_join(update):
    keyboard = [
        [InlineKeyboardButton("📡 قناة البوت الرسمية", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("🔘 تم الاشتراك | Subscribed", callback_data="check_sub")]
    ]
    text = (
        "🚫 لا يمكنك استخدام البوت حالياً!\n\n"
        "اشترك في القناة الرسمية أولاً:\n"
        f"{CHANNEL_USERNAME}\n\n"
        "ثم اضغط أدناه لتأكيد المتابعة 👇"
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# =========================
# الواجهة
# =========================
def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 تغيير اللغة | Change Language", callback_data="lang")],
        [
            InlineKeyboardButton("💎 اشتراك VIP (قريباً)", callback_data="vip"),
            InlineKeyboardButton("📡 القناة الرسمية", url="https://t.me/free0GM"),
        ],
    ])

WELCOME_TEXT = {
    "ar": (
        "✅ تم التحقق من اشتراكك بنجاح!\n\n"
        "👋 مرحباً بك في *Kinga Downloader*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡️ يمكنك تحميل الفيديوهات من:\n"
        "📱 TikTok | YouTube | Instagram | Twitter | Facebook\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎬 أرسل أي رابط وسأقوم بتحميله لك 🔥\n\n"
        "🌐 يمكنك تغيير اللغة من الزر أدناه:"
    ),
    "en": (
        "✅ Subscription verified!\n\n"
        "👋 Welcome to *Kinga Downloader*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡️ You can download videos from:\n"
        "📱 TikTok | YouTube | Instagram | Twitter | Facebook\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎬 Send any link and I’ll download it for you 🔥\n\n"
        "🌐 You can change language below:"
    ),
}

# =========================
# /start
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update, context):
        await ask_to_join(update)
        return

    lang = get_user_lang(update.effective_user.id)
    await update.message.reply_text(
        WELCOME_TEXT[lang],
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

# =========================
# تغيير اللغة
# =========================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "lang":
        buttons = [
            [InlineKeyboardButton(v, callback_data=f"setlang_{k}")]
            for k, v in LANGUAGES.items()
        ]
        await query.message.reply_text("🌍 اختر لغتك / Choose your language:", reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data.startswith("setlang_"):
        lang = query.data.split("_")[1]
        set_user_lang(query.from_user.id, lang)
        await query.message.reply_text(
            f"✅ تم تغيير اللغة إلى: {LANGUAGES[lang]}",
            reply_markup=main_keyboard()
        )

    elif query.data == "check_sub":
        if await check_subscription(update, context):
            await query.message.reply_text("✅ تم التحقق من اشتراكك، أرسل الآن أي رابط فيديو 🎬", reply_markup=main_keyboard())
        else:
            await query.message.reply_text("🚫 لم يتم العثور على اشتراكك بعد، تأكد من متابعتك للقناة.")

# =========================
# تحميل الفيديو
# =========================
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update, context):
        await ask_to_join(update)
        return

    url = (update.message.text or "").strip()
    if not url.startswith(("http://", "https://")):
        await update.message.reply_text("🚫 أرسل رابط فيديو صحيح.")
        return

    waiting = await update.message.reply_text("⏳ جاري التحميل...")

    try:
        video_path, size_mb = await asyncio.get_event_loop().run_in_executor(None, download_video, url)
        if not video_path:
            await waiting.edit_text("⚠️ لم أتمكن من تحميل الفيديو.")
            return
        if size_mb > MAX_TELEGRAM_MB:
            await waiting.edit_text(f"⚠️ حجم الفيديو {size_mb:.1f}MB أكبر من الحد المسموح به.")
            return

        await waiting.edit_text("📤 جاري إرسال الفيديو...")
        await context.bot.send_video(
            chat_id=update.effective_chat.id,
            video=open(video_path, "rb"),
            caption="🎬 تم التحميل بنجاح!",
            supports_streaming=True,
        )
        await waiting.delete()
    except Exception as e:
        logger.error(f"Download error: {e}")
        await waiting.edit_text("⚠️ فشل التحميل، الموقع ربما يمنع التنزيل.")
    finally:
        if "video_path" in locals() and video_path and os.path.exists(video_path):
            os.remove(video_path)

def download_video(url):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            opts = YTDL_OPTS.copy()
            opts["outtmpl"] = os.path.join(tmpdir, "%(id)s.%(ext)s")
            ydl = YoutubeDL(opts)
            info = ydl.extract_info(url, download=True)
            files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir)]
            if not files:
                return None, 0
            video_path = max(files, key=os.path.getsize)
            size_mb = os.path.getsize(video_path) / (1024 * 1024)
            final_path = os.path.join("/tmp", os.path.basename(video_path))
            os.rename(video_path, final_path)
            return final_path, size_mb
    except Exception as e:
        logger.error(e)
        return None, 0

# =========================
# تشغيل البوت
# =========================
def main():
    if not BOT_TOKEN:
        print("❌ TG_BOT_TOKEN غير موجود.")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("🚀 Kinga Downloader v4.0 يعمل الآن...")
    app.run_polling(stop_signals=None)

if __name__ == "__main__":
    main()
