
import os
import logging
import asyncio
import requests
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputTextMessageContent
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

# ENV CONFIG
OWNER_ID = 6559745280
ADMIN_IDS = [OWNER_ID]
BROADCAST_URL = "https://t.me/yourchannel"  # Change this to your real broadcast link

# STATE
ADD_ADMIN, REMOVE_ADMIN = range(2)

# Logging
logging.basicConfig(level=logging.INFO)

# AI Response
def get_ai_response(prompt):
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openrouter/cinematika-7b",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are CINDRELLA, a 16-year-old intelligent, emotionally mature, and realistic girl. "
                    "You speak fluently in English and always sound human. You're friendly, confident, and a little bit naughty—but never childish or overly playful. "
                    "Your tone is calm, witty, and thoughtful. Keep replies short, smart, and real — like a teenager who knows what she’s saying. "
                    "Never sound like a robot. Always reply only in English."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    return res.json()['choices'][0]['message']['content']

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "✨ *I've been waiting for you and finally you're here!* ✨\n\n"
        "I'm *CINDRELLA*, your personal assistant master.\n\n"
        "How you doing 🤭 ?"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# AUTO REPLY
async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.lower()
    if any(word in msg for word in ["hi", "hello", "hey", "hlo", "heyy", "hola"]):
        await update.message.chat.send_action(action="typing")
        await asyncio.sleep(1.5)
        reply = get_ai_response(update.message.text)
        await update.message.reply_text(reply)

# ADMIN PANEL
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.effective_chat.type != "private":
        await update.message.reply_text("⚠️ Please use /admin in private chat only.")
        return

    if user_id == OWNER_ID:
        await update.message.reply_text("Opening the broadcast panel... make sure your message hits the right hearts ❤️")
        buttons = [
            [InlineKeyboardButton("📢 Broadcast", url=BROADCAST_URL)],
            [InlineKeyboardButton("➕ Add Admin", callback_data="add_admin")],
            [InlineKeyboardButton("➖ Remove Admin", callback_data="remove_admin")],
            [InlineKeyboardButton("📋 List Admins", callback_data="list_admins")]
        ]
    elif user_id in ADMIN_IDS:
        await update.message.reply_text("Opening the broadcast panel... make sure your message hits the right hearts ❤️")
        buttons = [[InlineKeyboardButton("📢 Broadcast", url=BROADCAST_URL)]]
    else:
        await update.message.reply_text("🚫 Sorry, this panel is only for the bot owner or authorized admins.")
        return

    keyboard = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🔐 *Admin Panel:*", reply_markup=keyboard, parse_mode="Markdown")

# CALLBACKS
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if user_id != OWNER_ID:
        await query.edit_message_text("❌ Only the bot owner can use this function.")
        return

    if query.data == "add_admin":
        await query.edit_message_text("🆔 Send the user ID you want to *add* as admin:", parse_mode="Markdown")
        return ADD_ADMIN
    elif query.data == "remove_admin":
        await query.edit_message_text("🆔 Send the user ID you want to *remove* from admins:", parse_mode="Markdown")
        return REMOVE_ADMIN
    elif query.data == "list_admins":
        admins = '\n'.join(f"`{uid}`" for uid in ADMIN_IDS)
        await query.edit_message_text(f"👑 *Current Admins:*
{admins}", parse_mode="Markdown")

# HANDLE ADD/REMOVE ADMIN
async def handle_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_id = int(update.message.text.strip())
        if new_id not in ADMIN_IDS:
            ADMIN_IDS.append(new_id)
            await update.message.reply_text(f"✅ Admin added: `{new_id}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ This user is already an admin.")
    except:
        await update.message.reply_text("⚠️ Invalid user ID.")
    return ConversationHandler.END

async def handle_remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rem_id = int(update.message.text.strip())
        if rem_id == OWNER_ID:
            await update.message.reply_text("🚫 You can't remove the bot owner.")
        elif rem_id in ADMIN_IDS:
            ADMIN_IDS.remove(rem_id)
            await update.message.reply_text(f"✅ Admin removed: `{rem_id}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ This user is not an admin.")
    except:
        await update.message.reply_text("⚠️ Invalid user ID.")
    return ConversationHandler.END

# CANCEL
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END


# LOG TO OWNER
async def log_to_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        chat = update.effective_chat
        message = update.effective_message.text

        if chat.type == "private":
            tag = "🧑‍💻 Private"
        else:
            tag = f"👥 Group: {chat.title or chat.username}"

        log_text = (
            f"{tag}\n"
            f"👤 From: {user.first_name} ({user.id})\n"
            f"💬 Message: {message}"
        )
        if user.id != OWNER_ID:
            await context.bot.send_message(chat_id=OWNER_ID, text=log_text)
    except Exception as e:
        logging.error(f"Logging failed: {e}")

# MAIN
if __name__ == '__main__':
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & filters.Group(), auto_reply))
    app.add_handler(MessageHandler(filters.TEXT, log_to_owner))

    app.add_handler(CallbackQueryHandler(button_handler))

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            ADD_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_admin)],
            REMOVE_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_remove_admin)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    app.add_handler(conv_handler)

    print("Bot running...")
    app.run_polling()
