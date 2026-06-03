import logging
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = 123456789          # <--- YAHAN APNI TELEGRAM USER ID DALEIN (e.g., 54637281)
CHANNELS = ["@araspacez", "@uxiopix"]
CHANNEL_LINKS = ["https://t.me/araspacez", "https://t.me/uxiopix"]
REFERRAL_BONUS = 0.50
DAILY_BONUS_AMOUNT = 0.10
MIN_WITHDRAWAL = 5.00              # Updated to $5.00

# Temporary In-Memory Database
USER_DB = {}

# --- Helper Functions ---

async def is_subscribed(bot, user_id: int) -> bool:
    """Checks if a user is a member of all required channels."""
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception as e:
            logger.error(f"Error checking sub for {channel}: {e}")
            return False
    return True

def get_join_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel 1", url=CHANNEL_LINKS[0])],
        [InlineKeyboardButton("📢 Join Channel 2", url=CHANNEL_LINKS[1])],
        [InlineKeyboardButton("✅ Check Verification", callback_data="check_join")]
    ])

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 Balance", callback_data="menu_balance"),
            InlineKeyboardButton("🔗 Referral", callback_data="menu_referral")
        ],
        [
            InlineKeyboardButton("🎁 Daily Bonus", callback_data="menu_bonus"),
            InlineKeyboardButton("📖 Earning Guide", callback_data="menu_guide")
        ]
    ])

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    args = context.args
    referrer_id = None
    if args and args[0].isdigit():
        referrer_id = int(args[0])

    if user_id not in USER_DB:
        USER_DB[user_id] = {
            "balance": 0.0,
            "referred_by": referrer_id if referrer_id != user_id else None,
            "referrals": 0,
            "has_joined": False,
            "last_bonus": None
        }

    if await is_subscribed(context.bot, user_id):
        USER_DB[user_id]["has_joined"] = True
        await update.message.reply_text(
            f"👋 Welcome back *{user.first_name}*\!\n\nWelcome to the Refer & Earn Bot\. Use the interface buttons below to manage your earnings\.",
            parse_mode="MarkdownV2",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            f"👋 Hello *{user.first_name}*\!\n\nTo access the earning features of this bot, you **must join our sponsor channels** first\.",
            parse_mode="MarkdownV2",
            reply_markup=get_join_keyboard()
        )

# --- Callback Query Handler ---

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    await query.answer()

    if user_id not in USER_DB:
        USER_DB[user_id] = {"balance": 0.0, "referred_by": None, "referrals": 0, "has_joined": False, "last_bonus": None}

    # 1. Verification System
    if data == "check_join":
        if await is_subscribed(context.bot, user_id):
            if not USER_DB[user_id]["has_joined"]:
                USER_DB[user_id]["has_joined"] = True
                
                ref_id = USER_DB[user_id]["referred_by"]
                if ref_id and ref_id in USER_DB:
                    USER_DB[ref_id]["balance"] += REFERRAL_BONUS
                    USER_DB[ref_id]["referrals"] += 1
                    try:
                        await context.bot.send_message(
                            chat_id=ref_id,
                            text=f"🎉 *New Referral\!* User completed verification\. You earned *${REFERRAL_BONUS:.2f}*\.",
                            parse_mode="MarkdownV2"
                        )
                    except Exception:
                        pass

            await query.edit_message_text(
                "✅ Verification successful! Welcome to the main menu. Select an option below to begin earning:",
                reply_markup=get_main_keyboard()
            )
        else:
            await query.edit_message_text(
                "❌ Verification failed! You have not joined all mandatory channels yet. Please join them and click check again.",
                reply_markup=get_join_keyboard()
            )
        return

    if not await is_subscribed(context.bot, user_id):
        USER_DB[user_id]["has_joined"] = False
        await query.edit_message_text(
            "⚠️ Access Revoked! You left one or more required channels. Please rejoin to reactivate your portal.",
            reply_markup=get_join_keyboard()
        )
        return

    # 2. Main Menu Actions
    bot_info = await context.bot.get_me()
    bot_username = bot_info.username

    if data == "menu_main":
        await query.edit_message_text(
            "🎛️ **Main Menu**\nSelect an option below to manage your earnings:",
            reply_markup=get_main_keyboard()
        )

    elif data == "menu_balance":
        bal = USER_DB[user_id]["balance"]
        text = f"💳 **Your Financial Account Summary**\n\n💰 Current Balance: **${bal:.2f}**\n🏁 Minimum Payout threshold: **${MIN_WITHDRAWAL:.2f}**"
        keyboard = [
            [InlineKeyboardButton("💵 Request Withdrawal", callback_data="action_withdraw")],
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu_main")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "menu_referral":
        refs = USER_DB[user_id]["referrals"]
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        text = f"🔗 **Your Dynamic Referral Portal**\n\nShare your custom link below with friends. When they complete the channel check system, you get credited immediately!\n\n👥 Total Referrals: **{refs}**\n💵 Earnings per Referral: **${REFERRAL_BONUS:.2f}**\n\n`{ref_link}`"
        keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "menu_bonus":
        now = datetime.now()
        last_bonus = USER_DB[user_id]["last_bonus"]
        
        if last_bonus is None or (now - last_bonus) >= timedelta(days=1):
            USER_DB[user_id]["balance"] += DAILY_BONUS_AMOUNT
            USER_DB[user_id]["last_bonus"] = now
            text = f"🎁 **Daily Check-in Successful!**\n\nYou received **${DAILY_BONUS_AMOUNT:.2f}** straight to your active wallet balance! Come back tomorrow."
        else:
            time_left = timedelta(days=1) - (now - last_bonus)
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            text = f"⏳ **Bonus Cooldown Active!**\n\nYou have already collected your daily bonus. Please return in **{hours}h {minutes}m** to claim your next cycle reward."
            
        keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "menu_guide":
        text = (
            "📖 **Earning Guide & FAQ**\n\n"
            f"1️⃣ **Refer Friends:** Share your unique referral link found under the 'Referral' menu. You will receive **${REFERRAL_BONUS:.2f}** for each friend who launches the bot and joins our required channels.\n\n"
            f"2️⃣ **Daily Claims:** Tap the 'Daily Bonus' button once every 24 hours to collect a free allocation of **${DAILY_BONUS_AMOUNT:.2f}**.\n\n"
            f"3️⃣ **Withdrawals:** Once your balance reaches **${MIN_WITHDRAWAL:.2f}** or higher, navigate to the Balance screen to initiate a checkout transaction."
        )
        keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # 3. Withdrawal Action WITH Admin Notification
    elif data == "action_withdraw":
        bal = USER_DB[user_id]["balance"]
        if bal >= MIN_WITHDRAWAL:
            user_username = query.from_user.username or "No Username"
            user_fullname = query.from_user.full_name
            
            # --- ADMIN KO ALERT BHEJNA ---
            try:
                admin_msg = (
                    "🚨 **NEW WITHDRAWAL REQUEST** 🚨\n\n"
                    f"👤 **Name:** {user_fullname}\n"
                    f"🆔 **User ID:** `{user_id}`\n"
                    f"🏷️ **Username:** @{user_username}\n"
                    f"💰 **Amount Requested:** ${bal:.2f}\n"
                    f"📅 **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    "Status: Pending Admin Manual Payment."
                )
                await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Could not send alert to admin: {e}")

            # Deduct balance and clear
            USER_DB[user_id]["balance"] = 0.0
            text = f"✅ **Withdrawal Request Submitted Successfully!**\n\nYour entire balance of **${bal:.2f}** has been sent to the admin team for manual review. Payout will be processed shortly."
        else:
            text = f"❌ **Withdrawal Denied!**\n\nYour present balance is **${bal:.2f}**. You require at least **${MIN_WITHDRAWAL:.2f}** before you can unlock a cashout request."
            
        keyboard = [[InlineKeyboardButton("⬅️ Back to Wallet Balance", callback_data="menu_balance")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callbacks))
    print("🤖 Bot is initialized and pulling transaction frames...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
