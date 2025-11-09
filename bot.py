#!/usr/bin/env python3
import os
import asyncio
import logging
import tempfile
from datetime import datetime
from typing import Tuple

from yt_dlp import YoutubeDL
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================== إعدادات أساسية ==================

BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
CHANNEL_USERNAME = "@free0GM"      # القناة الرسمية
BOT_NAME_SHOW = "Kinga Downloader" # الاسم داخل الرسائل

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("kinga_downloader")

MAX_TELEGRAM_MB = 48  # الحد التقريبي لتيليجرام (MB)

YTDL_OPTS = {
    "format": "mp4[height<=720]/mp4/best",
    "noplaylist": False,
    "quiet": True,
    "no_warnings": True,
    "merge_output_format": "mp4",
    "outtmpl": "%(title)s.%(ext)s",
    "geo_bypass": True,
    "ignoreerrors": True,
}

# ================== نظام اللغة (بدون ملفات) ==================

def get_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """تحديد لغة المستخدم:
    1) لو مختار سابقاً من زر -> من user_data
    2) غير كذا -> من Telegram (language_code)
    3) غير كذا -> عربي افتراضي
    """
    user = update.effective_user
    if not user:
        return "ar"

    stored = context.user_data.get("lang")
    if stored in ("ar", "en"):
        return stored

    code = (user.language_code or "").lower()
    if code.startswith("ar"):
        lang = "ar"
    else:
        lang = "en"

    context.user_data["lang"] = lang
    return lang


def set_lang(context: ContextTypes.DEFAULT_TYPE, lang: str):
    if lang in ("ar", "en"):
        context.user_data["lang"] = lang


def tr(lang: str, key: str) -> str:
    """نصوص بسيطة بالعربي/إنجليزي"""
    texts = {
        "ar": {
            "start_welcome": (
                f"مرحباً بك في بوت {BOT_NAME_SHOW}.\n"
                "يمكنك تحميل الفيديوهات من المنصات المدعومة عن طريق إرسال الرابط هنا."
            ),
            "need_sub": (
                "لتفعيل حسابك، اشترك أولاً في القناة الرسمية:\n"
                f"{CHANNEL_USERNAME}\n\n"
                "ثم اضغط أدناه لتأكيد المتابعة:\n"
                "تم الاشتراك | Subscribed"
            ),
            "sub_ok": (
                "تم التحقق من اشتراكك بنجاح.\n\n"
                f"مرحباً بك في بوت {BOT_NAME_SHOW}.\n"
                "الآن يمكنك تحميل الفيديوهات من المنصات التالية:\n"
                "TikTok, YouTube, Instagram, Twitter, Facebook.\n\n"
                "أرسل أي رابط وسأقوم بتحميله لك.\n"
                "يمكنك تغيير اللغة من زر (تغيير اللغة | Change Language)."
            ),
            "sub_fail": (
                "لم يتم التحقق من الاشتراك.\n"
                f"يرجى التأكد من الانضمام إلى القناة {CHANNEL_USERNAME} ثم المحاولة مرة أخرى."
            ),
            "send_link": "أرسل رابط الفيديو الذي تريد تحميله.",
            "invalid_link": "يرجى إرسال رابط صحيح.",
            "downloading": "جاري التحميل...",
            "too_big": "حجم الفيديو أكبر من الحد المسموح في تيليجرام.",
            "download_fail": "لم أتمكن من تحميل هذا الرابط.",
            "sent_ok": "تم إرسال الفيديو.",
            "vip_coming": "نظام VIP غير متاح حالياً. سيتم الإعلان عنه في القناة لاحقاً.",
            "choose_lang": "اختر اللغة:",
            "lang_set_ar": "تم تغيير اللغة إلى العربية.",
            "lang_set_en": "Language changed to English.",
            "channel_link": f"القناة الرسمية: {CHANNEL_USERNAME}",
        },
        "en": {
            "start_welcome": (
                f"Welcome to {BOT_NAME_SHOW}.\n"
                "Send a supported video link to download."
            ),
            "need_sub": (
                "To activate your account, please join the official channel first:\n"
                f"{CHANNEL_USERNAME}\n\n"
                "Then press below to confirm:\n"
                "Subscribed"
            ),
            "sub_ok": (
                "Subscription verified successfully.\n\n"
                f"Welcome to {BOT_NAME_SHOW}.\n"
                "You can now download videos from:\n"
                "TikTok, YouTube, Instagram, Twitter, Facebook.\n\n"
                "Send any link to start.\n"
                "You can change language from (Change Language)."
            ),
            "sub_fail": (
                "We couldn't verify your subscription.\n"
                f"Please make sure you joined {CHANNEL_USERNAME} and try again."
            ),
            "send_link": "Send the video link you want to download.",
            "invalid_link": "Please send a valid URL.",
            "downloading": "Downloading...",
            "too_big": "The video file is too large for Telegram.",
            "download_fail": "Failed to download this link.",
            "sent_ok": "Video sent.",
            "vip_coming": "VIP system is not available yet. Stay tuned on the channel.",
            "choose_lang": "Choose language:",
            "lang_set_ar": "تم تغيير اللغة إلى العربية.",
            "lang_set_en": "Language changed to English.",
            "channel_link": f"Official channel: {CHANNEL_USERNAME}",
        },
    }
    return texts.get(lang, texts["ar"]).get(key, key)

# ================== الكيبورد ==================

def main_keyboard(lang: str) -> ReplyKeyboardMarkup:
    if lang == "en":
        rows = [
            [KeyboardButton("Download Video")],
            [KeyboardButton("Change Language"), KeyboardButton("VIP (Soon)")],
            [KeyboardButton("Official Channel")],
        ]
    else:
        rows = [
            [KeyboardButton("تحميل فيديو")],
            [KeyboardButton("🌐 تغيير اللغة | Change Language"),
             KeyboardButton("💎 اشتراك VIP (قريبًا)")],
            [KeyboardButton("📡 القناة الرسمية")],
        ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def subscribe_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("تم الاشتراك | Subscribed", callback_data="check_sub")],
    ])


def language_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("العربية", callback_data="setlang:ar")],
        [InlineKeyboardButton("English", callback_data="setlang:en")],
    ])

# ================== التحقق من الاشتراك ==================

async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ("left", "kicked"):
            return False
        return True
    except Exception as e:
        logger.error(f"check member failed: {e}")
        # لو صار خطأ شبكي، ما نحبس المستخدم: نسمح مؤقتاً
        return False

async def ensure_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """يتأكد من الاشتراك؛ لو مو مشترك يرسل رسالة الاشتراك ويرجع False"""
    user = update.effective_user
    if not user:
        return False
    user_id = user.id
    lang = get_lang(update, context)

    if await is_subscribed(user_id, context):
        return True

    msg = tr(lang, "need_sub")
    if update.message:
        await update.message.reply_text(msg, reply_markup=subscribe_inline_keyboard())
    elif update.callback_query:
        await update.callback_query.message.reply_text(msg, reply_markup=subscribe_inline_keyboard())
    return False

# ================== أوامر وكول باك ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    # لو مو مشترك -> نطلب اشتراك مباشرة
    if not await is_subscribed(update.effective_user.id, context):
        await update.message.reply_text(
            tr(lang, "need_sub"),
            reply_markup=subscribe_inline_keyboard()
        )
        return

    await update.message.reply_text(
        tr(lang, "start_welcome"),
        reply_markup=main_keyboard(lang),
    )


async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    lang = context.user_data.get("lang", "ar")

    if await is_subscribed(user.id, context):
        await query.answer("تم التحقق", show_alert=False)
        await query.message.reply_text(
            tr(lang, "sub_ok"),
            reply_markup=main_keyboard(lang),
        )
    else:
        await query.answer("لم يتم التحقق", show_alert=False)
        await query.message.reply_text(
            tr(lang, "sub_fail"),
            reply_markup=subscribe_inline_keyboard(),
        )


async def change_language_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update, context)
    await update.message.reply_text(
        tr(lang, "choose_lang"),
        reply_markup=language_inline_keyboard(),
    )


async def set_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    _, lang = data.split(":", 1)

    set_lang(context, lang)

    if lang == "ar":
        await query.answer()
        await query.edit_message_text(tr("ar", "lang_set_ar"))
        await query.message.reply_text(
            tr("ar", "start_welcome"),
            reply_markup=main_keyboard("ar"),
        )
    else:
        await query.answer()
        await query.edit_message_text(tr("en", "lang_set_en"))
        await query.message.reply_text(
            tr("en", "start_welcome"),
            reply_markup=main_keyboard("en"),
        )

# ================== تحميل الفيديو ==================

def download_video_file(url: str) -> Tuple[str, float]:
    """
    يرجع (مسار_الملف, حجم_MB)
    أو (None, 0) في حال الفشل.
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            opts = YTDL_OPTS.copy()
            opts["outtmpl"] = os.path.join(tmpdir, "%(id)s.%(ext)s")
            ydl = YoutubeDL(opts)
            info = ydl.extract_info(url, download=True)
            if info is None:
                return None, 0.0

            if "entries" in info and info["entries"]:
                info = info["entries"][0]

            files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir)]
            if not files:
                return None, 0.0

            files.sort(key=lambda p: os.path.getsize(p), reverse=True)
            video_path = files[0]
            size_mb = os.path.getsize(video_path) / (1024 * 1024)

            final_path = os.path.join("/tmp", os.path.basename(video_path))
            os.rename(video_path, final_path)
            return final_path, size_mb

    except Exception as e:
        logger.error(f"download error: {e}")
        return None, 0.0


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    user_id = user.id
    lang = get_lang(update, context)
    text = (update.message.text or "").strip()

    # أزرار ثابتة
    lower = text.lower()

    # تغيير اللغة
    if "change language" in lower or "تغيير اللغة" in text:
        return await change_language_menu(update, context)

    # VIP قريباً
    if "vip" in lower or "اشترك vip" in text:
        return await update.message.reply_text(
            tr(lang, "vip_coming"),
            reply_markup=main_keyboard(lang),
        )

    # القناة الرسمية
    if "القناة الرسمية" in text or "official channel" in lower:
        return await update.message.reply_text(
            tr(lang, "channel_link"),
            reply_markup=main_keyboard(lang),
        )

    # تحميل فيديو (زر)
    if "تحميل فيديو" in text or "download video" in lower:
        return await update.message.reply_text(
            tr(lang, "send_link"),
            reply_markup=main_keyboard(lang),
        )

    # أي شيء ثاني نفترض أنه رابط
    # أولاً نتأكد مشترك
    if not await ensure_subscription(update, context):
        return

    url = text
    if not (url.startswith("http://") or url.startswith("https://")):
        return await update.message.reply_text(
            tr(lang, "invalid_link"),
            reply_markup=main_keyboard(lang),
        )

    waiting = await update.message.reply_text(
        tr(lang, "downloading"),
        reply_markup=main_keyboard(lang),
    )

    try:
        loop = asyncio.get_running_loop()
        video_path, size_mb = await loop.run_in_executor(None, download_video_file, url)

        if not video_path:
            return await waiting.edit_text(tr(lang, "download_fail"))

        if size_mb > MAX_TELEGRAM_MB:
            os.remove(video_path)
            return await waiting.edit_text(tr(lang, "too_big"))

        with open(video_path, "rb") as f:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=f,
            )

        await waiting.edit_text(tr(lang, "sent_ok"))
    except Exception as e:
        logger.error(f"send error: {e}")
        await waiting.edit_text(tr(lang, "download_fail"))
    finally:
        if "video_path" in locals() and video_path and os.path.exists(video_path):
            os.remove(video_path)

# ================== main ==================

def main():
    if not BOT_TOKEN:
        print("TG_BOT_TOKEN is missing.")
        raise SystemExit(1)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # أوامر
    app.add_handler(CommandHandler("start", start))

    # كولباك
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))
    app.add_handler(CallbackQueryHandler(set_language_callback, pattern="^setlang:(ar|en)$"))

    # كل نص
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print(f"{datetime.now()} - Kinga Downloader is running...")
    app.run_polling(stop_signals=None)


if __name__ == "__main__":
    main()
