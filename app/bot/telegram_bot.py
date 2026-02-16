import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from dotenv import load_dotenv

from app.utils.validators import detect_platform
from app.services.transcript_service import get_transcript_from_url
from app.services.formatter_service import TranscriptFormatter
from app.services.file_service import FileGenerator

# Load environment variables
load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to TranscriptFlow!\n\n"
        "Send me a YouTube video URL, and I'll extract the transcript for you.\n"
        "I support TXT, DOCX, and PDF formats."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Simply paste a YouTube link to get started.\n"
        "Example: https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    try:
        # Detect platform
        platform = detect_platform(url)
        context.user_data['url'] = url
        context.user_data['platform'] = platform
        
        keyboard = [
            [
                InlineKeyboardButton("Clean Text (.txt)", callback_data='clean|txt'),
                InlineKeyboardButton("With Timestamps (.txt)", callback_data='timestamp|txt'),
            ],
            [
                InlineKeyboardButton("Paragraph Mode (.docx)", callback_data='paragraph|docx'),
                InlineKeyboardButton("Clean PDF (.pdf)", callback_data='clean|pdf'),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        platform_name = platform.capitalize()
        await update.message.reply_text(
            f"✅ {platform_name} video detected! Choose a format:", 
            reply_markup=reply_markup
        )
        
    except ValueError as e:
        await update.message.reply_text(
            "❌ That doesn't look like a valid YouTube or Vimeo URL. Please try again."
        )
    except Exception as e:
        logging.error(f"Error handling URL: {e}")
        await update.message.reply_text("Something went wrong processing that URL.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    format_type, file_extension = data.split('|')
    
    url = context.user_data.get('url')
    platform = context.user_data.get('platform', 'video')
    
    if not url:
        await query.edit_message_text(text="Session expired. Please send the link again.")
        return

    await query.edit_message_text(
        text=f"⏳ Generating {format_type} transcript as .{file_extension}..."
    )
    
    try:
        # Extract transcript using unified function
        raw_transcript = get_transcript_from_url(url)
        
        # Format
        formatted_text = TranscriptFormatter.format(raw_transcript, format_type=format_type)
        
        # Generate File
        file_stream = FileGenerator.generate_file(formatted_text, file_extension)
        
        # Send File
        file_stream.name = f"transcript_{platform}.{file_extension}"
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=file_stream,
            filename=f"transcript_{platform}.{file_extension}",
            caption=f"✅ Here is your {platform.capitalize()} transcript!\nFormat: {format_type}"
        )
        
    except Exception as e:
        logging.error(f"Error generating transcript: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ Failed to generate transcript: {str(e)}"
        )

def run_bot():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or token == "your_token_here":
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        return

    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_url))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("Bot is polling...")
    application.run_polling()

if __name__ == '__main__':
    run_bot()
