import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Get token from environment (Railway will set this)
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("❌ ERROR: No bot token found!")
    print("Please set TELEGRAM_BOT_TOKEN environment variable in Railway")
    exit(1)

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_html(
        f"👋 Welcome {user.mention_html()}!\n\n"
        "I'm Makash Scrap Bot!\n\n"
        "Commands:\n"
        "/start - Welcome message\n"
        "/help - Show commands\n"
        "/prices - View all prices\n\n"
        "Just send an item code like: 6261"
    )

# Command: /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 MAKASH BOT HELP\n\n"
        "Available commands:\n"
        "/start - Welcome message\n"
        "/help - This help\n"
        "/prices - View all prices\n\n"
        "Or just send item codes like:\n"
        "6261\n"
        "6531E\n"
        "2160.0"
    )

# Command: /prices
async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 CURRENT PRICES\n\n"
        "• 2160.0: ₦950\n"
        "• 6261.0: ₦650\n"
        "• 6531E: ₦480\n\n"
        "Send item code to check price"
    )

# Handle item codes (like 6261, 6531E)
async def check_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    
    # Price database (we'll connect to Google Sheets later)
    price_db = {
        '2160.0': '₦950',
        '6261': '₦650',
        '6261.0': '₦650',
        '6531E': '₦480'
    }
    
    if text in price_db:
        await update.message.reply_text(f"✅ {text}: {price_db[text]}")
    else:
        await update.message.reply_text(f"❌ Item '{text}' not found\nTry: 6261")

# Echo other messages
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.startswith('/'):
        await update.message.reply_text("❌ Unknown command. Try /help")
    else:
        await update.message.reply_text(f"🤖 You said: {text}")

# Main function
def main():
    print("🚀 Starting Makash Bot...")
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("prices", prices))
    
    # Handle item codes (numbers and letters, 2-10 characters)
    application.add_handler(MessageHandler(filters.Regex(r'^[A-Z0-9]{2,10}$'), check_item))
    
    # Add echo for other messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # Start polling
    print("✅ Bot is running!")
    application.run_polling()

if __name__ == '__main__':
    main()
