import os
import logging
from datetime import datetime
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

# ==================== CONFIGURATION ====================
# Your Telegram User ID (for admin notifications)
ADMIN_USER_ID = 1271245454  # ⬅️ REPLACE WITH YOUR TELEGRAM ID

# Tiers and their permissions
TIERS = {
    'Gold': {'description': 'Gold Tier', 'access': 'full'},
    'Silver': {'description': 'Silver Tier', 'access': 'full'},
    'Bronze': {'description': 'Bronze Tier', 'access': 'full'},
    'Stone': {'description': 'Unregistered', 'access': 'limited'}  # Only see base prices
}

# ==================== SIMULATED DATABASE ====================
# This will be replaced with Google Sheets later

# Simulated Suppliers data (from your Google Sheets)
SIMULATED_SUPPLIERS = [
    {
        'phone': '08107104806',
        'name': 'Musab',
        'tier': 'Gold',
        'telegram_id': None,  # Will be filled when registered
        'status': 'Active',  # Active, Pending, Registered, Rejected
        'approved_by': None,
        'approval_date': None
    },
    {
        'phone': '09059408329',
        'name': 'Musty',
        'tier': 'Silver',
        'telegram_id': None,
        'status': 'Active',
        'approved_by': None,
        'approval_date': None
    },
    {
        'phone': '08144630629',
        'name': 'abi cus',
        'tier': 'Bronze',
        'telegram_id': None,
        'status': 'Active',
        'approved_by': None,
        'approval_date': None
    }
]

# Simulated Items data
SIMULATED_ITEMS = {
    '2160.0': {
        'name': '2160.0',
        'base_price': 1000,
        'Gold': 950,
        'Silver': 930,
        'Bronze': 900,
        'Stone': 850  # Stone sees lowest price
    },
    '6261': {
        'name': '6261',
        'base_price': 700,
        'Gold': 650,
        'Silver': 630,
        'Bronze': 600,
        'Stone': 550
    },
    '6261.0': {
        'name': '6261.0',
        'base_price': 700,
        'Gold': 650,
        'Silver': 630,
        'Bronze': 600,
        'Stone': 550
    },
    '6531E': {
        'name': '6531E',
        'base_price': 530,
        'Gold': 480,
        'Silver': 460,
        'Bronze': 430,
        'Stone': 400
    }
}

# Registration requests pending approval
PENDING_REGISTRATIONS = {}

# ==================== HELPER FUNCTIONS ====================
def clean_phone(phone):
    """Clean phone number for comparison."""
    if not phone:
        return ""
    phone = str(phone)
    # Remove all non-digits
    phone = ''.join(filter(str.isdigit, phone))
    # Remove leading 0 if present
    if phone.startswith('0'):
        phone = phone[1:]
    # Remove Nigeria country code if present
    if phone.startswith('234'):
        phone = phone[3:]
    return phone

def find_customer_by_phone(phone):
    """Find customer by phone number in simulated database."""
    cleaned_phone = clean_phone(phone)
    for customer in SIMULATED_SUPPLIERS:
        if clean_phone(customer['phone']) == cleaned_phone:
            return customer
    return None

def find_customer_by_telegram_id(telegram_id):
    """Find customer by Telegram ID."""
    for customer in SIMULATED_SUPPLIERS:
        if customer['telegram_id'] == telegram_id:
            return customer
    return None

def get_price_for_tier(item_code, tier):
    """Get price for item based on tier."""
    item_code_upper = item_code.upper()
    if item_code_upper in SIMULATED_ITEMS:
        price = SIMULATED_ITEMS[item_code_upper].get(tier)
        if price:
            return f"₦{price}"
    return None

def send_admin_notification(bot, message):
    """Send notification to admin (you)."""
    try:
        bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=message,
            parse_mode='HTML'
        )
        return True
    except Exception as e:
        print(f"Failed to send admin notification: {e}")
        return False

# ==================== APPROVAL SYSTEM ====================
async def handle_approval_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /approve_<user_id> command."""
    telegram_id = update.effective_user.id
    
    # Check if admin
    if telegram_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin only command.")
        return
    
    command_text = update.message.text
    # Extract user_id from command like /approve_123456789
    try:
        target_user_id = int(command_text.split('_')[1])
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Invalid command. Use: /approve_<user_id>")
        return
    
    # Check if user is in pending registrations
    if target_user_id not in PENDING_REGISTRATIONS:
        await update.message.reply_text(f"❌ User {target_user_id} not found in pending registrations.")
        return
    
    # Get pending registration data
    pending_data = PENDING_REGISTRATIONS[target_user_id]
    customer = pending_data['customer']
    user_info = pending_data['user']
    
    # Update customer status
    customer['status'] = 'Registered'
    customer['approved_by'] = telegram_id
    customer['approval_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Remove from pending
    del PENDING_REGISTRATIONS[target_user_id]
    
    # Notify user
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"✅ REGISTRATION APPROVED!\n\n"
                 f"Hello {user_info['first_name']}!\n\n"
                 f"Your registration has been approved by Makash.\n"
                 f"Account Details:\n"
                 f"• Name: {customer['name']}\n"
                 f"• Tier: {customer['tier']}\n\n"
                 f"You can now use the bot with your tier prices.\n"
                 f"Send /start to begin."
        )
    except Exception as e:
        print(f"Could not notify user {target_user_id}: {e}")
    
    # Confirm to admin
    await update.message.reply_text(
        f"✅ Approved registration for:\n"
        f"Name: {customer['name']}\n"
        f"Phone: {customer['phone']}\n"
        f"Tier: {customer['tier']}\n"
        f"User ID: {target_user_id}"
    )

async def handle_rejection_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /reject_<user_id> command."""
    telegram_id = update.effective_user.id
    
    # Check if admin
    if telegram_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin only command.")
        return
    
    command_text = update.message.text
    # Extract user_id from command like /reject_123456789
    try:
        target_user_id = int(command_text.split('_')[1])
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Invalid command. Use: /reject_<user_id>")
        return
    
    # Check if user is in pending registrations
    if target_user_id not in PENDING_REGISTRATIONS:
        await update.message.reply_text(f"❌ User {target_user_id} not found in pending registrations.")
        return
    
    # Get pending registration data
    pending_data = PENDING_REGISTRATIONS[target_user_id]
    customer = pending_data['customer']
    user_info = pending_data['user']
    
    # Update customer status
    customer['status'] = 'Rejected'
    customer['approved_by'] = telegram_id
    customer['approval_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Remove from pending
    del PENDING_REGISTRATIONS[target_user_id]
    
    # Notify user
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"❌ REGISTRATION REJECTED\n\n"
                 f"Hello {user_info['first_name']},\n\n"
                 f"Your registration has been rejected.\n\n"
                 f"Please contact Makash for more information."
        )
    except Exception as e:
        print(f"Could not notify user {target_user_id}: {e}")
    
    # Confirm to admin
    await update.message.reply_text(
        f"❌ Rejected registration for:\n"
        f"Name: {customer['name']}\n"
        f"Phone: {customer['phone']}\n"
        f"User ID: {target_user_id}"
    )

# ==================== COMMAND HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    telegram_id = user.id
    
    # Check if user is already registered
    customer = find_customer_by_telegram_id(telegram_id)
    
    if customer:
        # Already registered
        if customer['status'] == 'Registered':
            await update.message.reply_html(
                f"👋 Welcome back {customer['name']}!\n\n"
                f"Tier: <b>{customer['tier']}</b>\n"
                f"Status: ✅ Approved\n\n"
                "Commands:\n"
                "/prices - View your tier prices\n"
                "/myinfo - Your account details\n\n"
                "Just send an item code like: 6261"
            )
        elif customer['status'] == 'Pending':
            await update.message.reply_html(
                f"👋 Hello {user.mention_html()}!\n\n"
                "Your registration is <b>pending approval</b>.\n\n"
                "You'll be notified when Makash approves your account.\n"
                "This usually takes 24 hours.\n\n"
                "Contact Makash if you have questions."
            )
        elif customer['status'] == 'Rejected':
            await update.message.reply_html(
                f"👋 Hello {user.mention_html()}!\n\n"
                "Your registration was <b>rejected</b>.\n\n"
                "Please contact Makash for more information."
            )
    else:
        # New user - ask for phone number
        await update.message.reply_html(
            f"👋 Welcome to Makash Scrap Bot!\n\n"
            "I can help you check scrap prices.\n\n"
            "To register, please send your <b>phone number</b>.\n\n"
            "Example: 09059408329\n\n"
            "Your phone number must be in our system to register."
        )

async def handle_phone_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle phone number for registration."""
    telegram_id = update.effective_user.id
    user = update.effective_user
    phone_input = update.message.text.strip()
    
    # Check if already registered
    existing_customer = find_customer_by_telegram_id(telegram_id)
    if existing_customer:
        if existing_customer['status'] == 'Registered':
            await update.message.reply_text(
                f"✅ You're already registered as {existing_customer['name']}."
            )
            return
        elif existing_customer['status'] == 'Pending':
            await update.message.reply_text(
                "⏳ Your registration is still pending approval."
            )
            return
    
    # Find customer by phone
    customer = find_customer_by_phone(phone_input)
    
    if not customer:
        # Phone not found
        await update.message.reply_text(
            f"❌ Phone number <b>{phone_input}</b> not found in our system.\n\n"
            "Please:\n"
            "1. Check if you entered the correct number\n"
            "2. Contact Makash to be added to our supplier list\n\n"
            "Try again or contact Makash for assistance.",
            parse_mode='HTML'
        )
        return
    
    # Check if this phone is already registered to someone else
    if customer['telegram_id'] is not None and customer['telegram_id'] != telegram_id:
        await update.message.reply_text(
            "❌ This phone number is already registered to another account.\n"
            "Please contact Makash if this is an error."
        )
        return
    
    # Check if already approved
    if customer['status'] == 'Registered':
        await update.message.reply_text(
            f"✅ You're already registered as {customer['name']}.\n"
            f"Send /start to begin."
        )
        return
    
    # Register user (pending approval)
    customer['telegram_id'] = telegram_id
    customer['status'] = 'Pending'
    
    # Store in pending registrations
    PENDING_REGISTRATIONS[telegram_id] = {
        'customer': customer,
        'user': {
            'id': user.id,
            'first_name': user.first_name,
            'username': user.username
        },
        'timestamp': update.message.date
    }
    
    # Send confirmation to user
    await update.message.reply_text(
        f"✅ Registration submitted for <b>{customer['name']}</b>!\n\n"
        f"Tier: <b>{customer['tier']}</b>\n"
        f"Phone: <b>{customer['phone']}</b>\n\n"
        "Status: ⏳ <b>Pending Approval</b>\n\n"
        "Makash will review your registration within 24 hours.\n"
        "You'll receive a notification when approved.",
        parse_mode='HTML'
    )
    
    # Send notification to admin (you)
    admin_message = (
        f"🆕 NEW REGISTRATION REQUEST\n\n"
        f"Name: {customer['name']}\n"
        f"Phone: {customer['phone']}\n"
        f"Tier: {customer['tier']}\n"
        f"Telegram: @{user.username or 'N/A'} ({user.first_name})\n"
        f"User ID: {telegram_id}\n\n"
        f"To approve: /approve_{telegram_id}\n"
        f"To reject: /reject_{telegram_id}"
    )
    
    # Send to admin
    try:
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=admin_message
        )
    except Exception as e:
        print(f"Could not send admin notification: {e}")

async def check_item_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check price for an item based on user's tier."""
    telegram_id = update.effective_user.id
    text = update.message.text.strip().upper()
    
    # Find customer
    customer = find_customer_by_telegram_id(telegram_id)
    
    if not customer:
        # Unregistered user - show Stone tier prices
        price = get_price_for_tier(text, 'Stone')
        if price:
            await update.message.reply_text(
                f"💰 {text}: {price}\n\n"
                "ℹ️ This is the base price. Register to see your tier prices.\n"
                "Send /start to register."
            )
        else:
            await update.message.reply_text(f"❌ Item '{text}' not found")
        return
    
    # Check status
    if customer['status'] != 'Registered':
        if customer['status'] == 'Pending':
            await update.message.reply_text(
                "⏳ Your registration is pending approval.\n"
                "You can only see base prices until approved."
            )
        elif customer['status'] == 'Rejected':
            await update.message.reply_text(
                "❌ Your registration was rejected.\n"
                "Contact Makash for assistance."
            )
        # Show Stone tier for non-approved
        price = get_price_for_tier(text, 'Stone')
        if price:
            await update.message.reply_text(f"💰 {text}: {price}")
        else:
            await update.message.reply_text(f"❌ Item '{text}' not found")
        return
    
    # Approved user - show tier prices
    tier = customer['tier']
    price = get_price_for_tier(text, tier)
    
    if price:
        # Get base price for comparison
        base_price = SIMULATED_ITEMS.get(text, {}).get('Stone', 'N/A')
        base_price_text = f"₦{base_price}" if base_price != 'N/A' else 'N/A'
        
        await update.message.reply_text(
            f"✅ {text}\n"
            f"Your Tier: {tier}\n"
            f"Your Price: {price}\n"
            f"Base Price: {base_price_text}\n\n"
            f"Savings: ₦{base_price - int(price[1:]) if isinstance(base_price, int) else 'N/A'}"
        )
    else:
        await update.message.reply_text(f"❌ Item '{text}' not found")

async def view_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all prices for user's tier."""
    telegram_id = update.effective_user.id
    customer = find_customer_by_telegram_id(telegram_id)
    
    if not customer or customer['status'] != 'Registered':
        # Show Stone tier for unregistered/pending
        tier = 'Stone'
        tier_name = 'Base Prices (Unregistered)'
    else:
        tier = customer['tier']
        tier_name = f'{tier} Tier'
    
    # Build price list
    message = f"📋 {tier_name}\n\n"
    count = 0
    
    for item_code, item_data in SIMULATED_ITEMS.items():
        if count >= 15:  # Limit to 15 items to avoid long messages
            message += f"\n... and {len(SIMULATED_ITEMS) - 15} more items"
            break
        
        price = item_data.get(tier)
        if price:
            message += f"• {item_code}: ₦{price}\n"
            count += 1
    
    if count == 0:
        message += "No prices available for your tier."
    
    message += f"\n{'─' * 30}\n"
    
    if not customer or customer['status'] != 'Registered':
        message += "🔒 Register to see your actual tier prices\nSend /start to register"
    else:
        message += f"Send item code to check price\nExample: 6261"
    
    await update.message.reply_text(message)

async def my_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's account information."""
    telegram_id = update.effective_user.id
    customer = find_customer_by_telegram_id(telegram_id)
    
    if not customer:
        await update.message.reply_text(
            "🔓 You're not registered yet.\n\n"
            "Send /start to begin registration."
        )
        return
    
    status_emoji = {
        'Registered': '✅',
        'Pending': '⏳',
        'Rejected': '❌',
        'Active': '📝'
    }
    
    emoji = status_emoji.get(customer['status'], '❓')
    
    message = (
        f"👤 YOUR ACCOUNT\n\n"
        f"Name: {customer['name']}\n"
        f"Phone: {customer['phone']}\n"
        f"Tier: {customer['tier']}\n"
        f"Status: {emoji} {customer['status']}\n"
        f"Telegram ID: {telegram_id}\n"
    )
    
    if customer['approved_by']:
        message += f"Approved by: {customer['approved_by']}\n"
    if customer['approval_date']:
        message += f"Approval date: {customer['approval_date']}\n"
    
    message += "\n────────────\n"
    
    if customer['status'] == 'Pending':
        message += "Your registration is pending approval.\n"
        message += "You'll be notified when approved."
    elif customer['status'] == 'Registered':
        message += "Your account is active.\n"
        message += "Send /prices to view your prices."
    elif customer['status'] == 'Rejected':
        message += "Your registration was rejected.\n"
        message += "Contact Makash for more information."
    
    await update.message.reply_text(message)

# ==================== ADMIN COMMANDS ====================
async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending registrations (admin only)."""
    telegram_id = update.effective_user.id
    
    # Check if admin
    if telegram_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin only command.")
        return
    
    if not PENDING_REGISTRATIONS:
        await update.message.reply_text("✅ No pending registrations.")
        return
    
    message = "📋 PENDING REGISTRATIONS\n\n"
    
    for idx, (user_id, data) in enumerate(PENDING_REGISTRATIONS.items(), 1):
        customer = data['customer']
        user = data['user']
        timestamp = data['timestamp'].strftime("%Y-%m-%d %H:%M") if hasattr(data['timestamp'], 'strftime') else str(data['timestamp'])
        
        message += (
            f"{idx}. {customer['name']}\n"
            f"   Phone: {customer['phone']}\n"
            f"   Tier: {customer['tier']}\n"
            f"   Telegram: @{user['username'] or 'N/A'} ({user['first_name']})\n"
            f"   User ID: {user_id}\n"
            f"   Time: {timestamp}\n\n"
        )
    
    message += "────────────────────\n"
    message += "To approve: /approve_<user_id>\n"
    message += "To reject: /reject_<user_id>\n"
    message += "Example: /approve_123456789"
    
    await update.message.reply_text(message)

# ==================== MAIN BOT SETUP ====================
def main():
    print("🚀 Starting Makash Bot with Registration & Approval System...")
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("prices", view_prices))
    application.add_handler(CommandHandler("myinfo", my_info))
    application.add_handler(CommandHandler("admin_pending", admin_pending))
    
    # Handle dynamic approval/rejection commands
    # These are like /approve_123456789 or /reject_123456789
    application.add_handler(MessageHandler(
        filters.Regex(r'^/approve_\d+$'),
        handle_approval_command
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^/reject_\d+$'),
        handle_rejection_command
    ))
    
    # Handle item codes
    application.add_handler(MessageHandler(
        filters.Regex(r'^[A-Z0-9\.]{2,10}$'),
        check_item_price
    ))
    
    # Handle phone numbers (for registration)
    application.add_handler(MessageHandler(
        filters.Regex(r'^[\d\s\-+]{10,15}$'),
        handle_phone_registration
    ))
    
    # Handle unknown commands/messages
    async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if text.startswith('/'):
            await update.message.reply_text(
                "❌ Unknown command. Try /start"
            )
        else:
            # Check if it might be a phone number
            if any(c.isdigit() for c in text) and len(text) >= 10:
                await handle_phone_registration(update, context)
            else:
                await update.message.reply_text(
                    "Send /start to begin or send your phone number to register.\n"
                    "Example: 09059408329"
                )
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    
    # Start polling
    print("✅ Bot is running with registration and approval system!")
    application.run_polling()

if __name__ == '__main__':
    main()
