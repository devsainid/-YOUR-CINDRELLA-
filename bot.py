import os
import logging
import asyncio
import requests
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    InlineQueryHandler, ConversationHandler, ContextTypes, filters
)

# ENV
OWNER_ID = int(os.getenv("OWNER_ID"))
ADMIN_IDS = [OWNER_ID]
BROADCAST_URL = "https://t.me/yourchannel"  # Replace with real broadcast URL
ADD_ADMIN, REMOVE_ADMIN = range(2)

# Logging
logging.basicConfig(level=logging.INFO)

# AI REPLY
def get_ai_response(prompt):
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openrouter/cinematika-7b",
        "messages": [
            {"role": "system", "content":
             "You are CINDRELLA, a 16-year-old emotionally smart girl. You're fluent, natural, realistic, witty and slightly naughty. "
             "You reply only in English. Be friendly but never childish or robotic."},
            {"role": "user", "content": prompt}
        ]
    }
    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    return res.json()['choices'][0]['message']['content']

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "✨ *I've been waiting for you and finally you're here!* ✨\n\n"
        "I'm *CINDRELLA*, your personal assistant master.\n\n"
        "How you doing 🤭 ?"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# Auto reply
async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if any(word in text for word in ["hi", "hello", "hey", "hlo", "heyy", "hola"]):
        await update.message.chat.send_action("typing")
        await asyncio.sleep(1.5)
        reply = get_ai_response(update.message.text)
        await update.message.reply_text(reply)

# Message logger
async def log_to_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        chat = update.effective_chat
        message = update.effective_message.text

        if user.id == OWNER_ID:
            return

        tag = "Private" if chat.type == "private" else f"Group: {chat.title or chat.username}"
        log = f"📥 {tag}\n👤 {user.first_name} ({user.id})\n💬 {message}"
        await context.bot.send_message(chat_id=OWNER_ID, text=log)
    except Exception as e:
        logging.warning(f"Log error: {e}")

# /admin
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.effective_chat.type != "private":
        await update.message.reply_text("⚠️ Use /admin in private chat.")
        return

    if user_id == OWNER_ID:
        buttons = [
            [InlineKeyboardButton("📢 Broadcast", url=BROADCAST_URL)],
            [InlineKeyboardButton("➕ Add Admin", callback_data="add_admin")],
            [InlineKeyboardButton("➖ Remove Admin", callback_data="remove_admin")],
            [InlineKeyboardButton("📋 List Admins", callback_data="list_admins")]
        ]
    elif user_id in ADMIN_IDS:
        buttons = [[InlineKeyboardButton("📢 Broadcast", url=BROADCAST_URL)]]
    else:
        await update.message.reply_text("🚫 Only authorized admins can access this.")
        return

    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🔐 *Admin Panel:*", reply_markup=markup, parse_mode="Markdown")

# Callback handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if user_id != OWNER_ID:
        await query.edit_message_text("❌ Only the bot owner can do this.")
        return

    if query.data == "add_admin":
        await query.edit_message_text("Send the ID to *add* as admin:", parse_mode="Markdown")
        return ADD_ADMIN
    elif query.data == "remove_admin":
        await query.edit_message_text("Send the ID to *remove* from admin:", parse_mode="Markdown")
        return REMOVE_ADMIN
    elif query.data == "list_admins":
        admin_list = '\n'.join(f"`{uid}`" for uid in ADMIN_IDS)
        await query.edit_message_text(f"👑 *Current Admins:*\n{admin_list}", parse_mode="Markdown")

# Add/remove handlers
async def handle_add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = int(update.message.text.strip())
        if uid not in ADMIN_IDS:
            ADMIN_IDS.append(uid)
            await update.message.reply_text(f"✅ Admin added: `{uid}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ Already admin.")
    except:
        await update.message.reply_text("❌ Invalid ID.")
    return ConversationHandler.END

async def handle_remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        uid = int(update.message.text.strip())
        if uid == OWNER_ID:
            await update.message.reply_text("🚫 Can't remove owner.")
        elif uid in ADMIN_IDS:
            ADMIN_IDS.remove(uid)
            await update.message.reply_text(f"✅ Removed: `{uid}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ Not an admin.")
    except:
        await update.message.reply_text("❌ Invalid ID.")
    return ConversationHandler.END

# Cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

# Inline query
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query:
        return
    response = get_ai_response(query)
    results = [
        InlineQueryResultArticle(
            id="1",
            title="✨ CINDRELLA's answer",
            description="Tap to send",
            input_message_content=InputTextMessageContent(response)
        )
    ]
    await update.inline_query.answer(results, cache_time=1)

# Main
if __name__ == '__main__':
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(MessageHandler(filters.TEXT & filters.Group(), auto_reply))
    app.add_handler(MessageHandler(filters.TEXT, log_to_owner))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(InlineQueryHandler(inline_query))

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
