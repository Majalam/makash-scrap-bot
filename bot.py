import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Get token from environment
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("❌ ERROR: No bot token found!")
    print("Please set TELEGRAM_BOT_TOKEN environment variable in Railway")
    exit(1)

# ==================== USER AUTHENTICATION ====================
# This will check if a user is authorized
def is_user_authorized(telegram_id):
    """
    Check if user is in your customer list.
    For now, we'll use a simple list. 
    Later we'll connect to Google Sheets.
    """
    # Example authorized users (you'll replace with Google Sheets data)
    authorized_users = {
        # Format: Telegram ID: {"name": "Customer Name", "tier": "Gold"}
        123456789: {"name": "Test Customer", "tier": "Gold"},
        1271245454: {"name": "Musty", "tier": "Silver"},
        # Add more users here for testing
    }
    
    return authorized_users.get(telegram_id)

# ==================== TIER-BASED PRICES ====================
def get_price_for_tier(item_code, tier):
    """
    Get price based on customer tier.
    Later we'll connect to Google Sheets.
    """
    # Example price database
    price_db = {
        '2160.0': {"Gold": '₦950', "Silver": '₦930', "Bronze": '₦900'},
        '6261': {"Gold": '₦650', "Silver": '₦630', "Bronze": '₦600'},
        '6261.0': {"Gold": '₦650', "Silver": '₦630', "Bronze": '₦600'},
        '6531E': {"Gold": '₦480', "Silver": '₦460', "Bronze": '₦430'}
    }
    
    item_code_upper = item_code.upper()
    if item_code_upper in price_db:
        return price_db[item_code_upper].get(tier, "Price not available")
    return None

# ==================== COMMAND HANDLERS ====================
# Command: /start - With authentication check
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    telegram_id = user.id
    
    # Check if user is authorized
    user_info = is_user_authorized(telegram_id)
    
    if user_info:
        # Authorized user
        await update.message.reply_html(
            f"👋 Welcome back {user_info['name']}!\n\n"
            f"Account Tier: {user_info['tier']}\n\n"
            "Commands:\n"
            "/prices - View prices for your tier\n"
            "/myinfo - Your account details\n\n"
            "Just send an item code like: 6261"
        )
    else:
        # Unauthorized user
        await update.message.reply_html(
            f"👋 Hello {user.mention_html()}!\n\n"
            "This bot is for Makash Scrap customers only.\n\n"
            "If you're a customer, please:\n"
            "1. Contact Makash to add you to the system\n"
            "2. Send your phone number to register\n\n"
            "Example: 09059408329"
        )

# Command: /prices - Show prices based on tier
async def prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user_info = is_user_authorized(telegram_id)
    
    if not user_info:
        await update.message.reply_text("❌ Unauthorized. Contact Makash to register.")
        return
    
    tier = user_info['tier']
    
    # Example prices for the user's tier
    price_list = {
        '2160.0': get_price_for_tier('2160.0', tier),
        '6261': get_price_for_tier('6261', tier),
        '6261.0': get_price_for_tier('6261.0', tier),
        '6531E': get_price_for_tier('6531E', tier)
    }
    
    message = f"📋 PRICES ({tier} Tier)\n\n"
    for item, price in price_list.items():
        if price:
            message += f"• {item}: {price}\n"
    
    message += "\n────────\n"
    message += "Send item code to check price"
    
    await update.message.reply_text(message)

# Command: /myinfo - Show user info
async def myinfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user_info = is_user_authorized(telegram_id)
    
    if not user_info:
        await update.message.reply_text("❌ Unauthorized. Contact Makash to register.")
        return
    
    await update.message.reply_text(
        f"👤 YOUR ACCOUNT\n\n"
        f"Name: {user_info['name']}\n"
        f"Tier: {user_info['tier']}\n"
        f"Telegram ID: {telegram_id}\n\n"
        f"For account updates, contact Makash."
    )

# Handle item codes - With authentication
async def check_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user_info = is_user_authorized(telegram_id)
    
    if not user_info:
        await update.message.reply_text("❌ Unauthorized. Contact Makash to register.")
        return
    
    text = update.message.text.strip().upper()
    tier = user_info['tier']
    
    price = get_price_for_tier(text, tier)
    
    if price:
        await update.message.reply_text(f"✅ {text} ({tier} tier): {price}")
    else:
        await update.message.reply_text(f"❌ Item '{text}' not found\nTry: 6261")

# Handle registration attempt (phone number)
async def register_attempt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # Check if it looks like a phone number
    if text.replace(' ', '').isdigit() and len(text) >= 10:
        await update.message.reply_text(
            f"📱 Phone number received: {text}\n\n"
            "I've forwarded your number to Makash.\n"
            "You'll be added to the system within 24 hours.\n\n"
            "Thank you!"
        )
    else:
        await update.message.reply_text("Please send your phone number to register.\nExample: 09059408329")

# Handle unauthorized messages
async def unauthorized_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text.startswith('/'):
        await update.message.reply_text("❌ Unauthorized. Contact Makash to register.")
    else:
        # Check if it might be a registration attempt
        if text.replace(' ', '').isdigit() and len(text) >= 10:
            await register_attempt(update, context)
        else:
            await update.message.reply_text("❌ This bot is for registered customers only.\n\nSend your phone number to register.\nExample: 09059408329")

# Main function
def main():
    print("🚀 Starting Makash Bot with Authentication...")
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers (for authorized users)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("prices", prices))
    application.add_handler(CommandHandler("myinfo", myinfo))
    
    # Handle item codes (2-10 alphanumeric chars)
    item_handler = MessageHandler(filters.Regex(r'^[A-Z0-9]{2,10}$'), check_item)
    application.add_handler(item_handler)
    
    # Handle phone numbers (for registration)
    phone_handler = MessageHandler(filters.Regex(r'^[\d\s]{10,15}$'), register_attempt)
    application.add_handler(phone_handler)
    
    # Handle all other messages (unauthorized users will see this)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unauthorized_message))
    
    # Start polling
    print("✅ Bot is running with authentication!")
    application.run_polling()

if __name__ == '__main__':
    main()
