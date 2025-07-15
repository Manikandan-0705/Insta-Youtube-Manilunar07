import os
import yt_dlp
import logging
import tempfile
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackQueryHandler
)

TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a YouTube or Instagram link to download the media.")

async def handle_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    context.user_data["url"] = url

    if "youtube.com" in url or "youtu.be" in url:
        keyboard = [
            [InlineKeyboardButton("🎥 Download Video", callback_data="yt_video")],
            [InlineKeyboardButton("🎧 Download Audio", callback_data="yt_audio")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Choose format to download:", reply_markup=reply_markup)

    elif "instagram.com" in url:
        await download_instagram(update, url)
    else:
        await update.message.reply_text("❗ Send a valid YouTube or Instagram link.")

async def download_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str):
    url = context.user_data.get("url", "")
    if not url:
        await update.callback_query.message.reply_text("❗ No URL found.")
        return

    await update.callback_query.message.reply_text("⏬ Downloading from YouTube...")

    with tempfile.TemporaryDirectory() as tmpdir:
        if mode == "video":
            ydl_opts = {
                'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'),
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
            }
        else:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(tmpdir, '%(title)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if mode == "audio":
                    filename = filename.rsplit(".", 1)[0] + ".mp3"

            with open(filename, 'rb') as f:
                if mode == "audio":
                    await update.callback_query.message.reply_audio(audio=f)
                else:
                    await update.callback_query.message.reply_video(video=f)
        except Exception as e:
            await update.callback_query.message.reply_text(f"❌ Error: {e}")

async def download_instagram(update: Update, url: str):
    await update.message.reply_text("📷 Downloading Instagram media...")

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "instagram-media-downloader.p.rapidapi.com"
    }
    params = {"url": url}

    try:
        response = requests.get(
            "https://instagram-media-downloader.p.rapidapi.com/rapid/post.php",
            headers=headers,
            params=params
        )
        result = response.json()

        if "media" in result:
            media_url = result["media"]
            if result["type"] == "video":
                await update.message.reply_video(media_url)
            else:
                await update.message.reply_photo(media_url)
        else:
            await update.message.reply_text("⚠️ Could not retrieve media.")
    except Exception as e:
        await update.message.reply_text(f"❌ Instagram error: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "yt_video":
        await download_youtube(update, context, mode="video")
    elif query.data == "yt_audio":
        await download_youtube(update, context, mode="audio")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_links))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
