from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import logging
import json
import os
import re
from datetime import datetime, timedelta

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BAD_WORDS = [
    "حيوان", "غبي", "قشمر", "ولي", "تفه", "كلب", "قندرة", "عرص", "خرة", "زربة", "سافل",
    "قواد", "ابن الكلب", "ابن الحمار", "صرماية", "شرموطة", "زاني", "داعر", "خسيس", "تافه",
    "ابن الزانية", "انعل ابو", "يلعن ابو", "منيوك", "زربان", "زرب", "حمار", "تيس", "معفن",
    "ابن القحبة", "ابن كحبه", "كسمك", "كسختك", "كسخته", "كس اختك", "كس امك", "كس عرضك",
    "كسها", "كسه", "كس", "كحبه", "قحب", "منيك", "طيز", "طيزك", "طيزه", "سكط", "سگط", "كواد",
    "طيزج", "كسج", "كسمج", "كس امج", "ام عيورة", "ام عيوره", "تف", "تف عليك", "خرا", "خرا عليك",
    "خرا بحلكك", "طيزي", "زعطوط", "زعاطيط", "طيزها"
]

WARN_FILE = "warns.json"

if os.path.exists(WARN_FILE):
    with open(WARN_FILE, "r", encoding="utf-8") as f:
        warns = json.load(f)
else:
    warns = {}

def save_warns():
    with open(WARN_FILE, "w", encoding="utf-8") as f:
        json.dump(warns, f, ensure_ascii=False)

def normalize_text(text: str) -> str:
    text = re.sub(r'\s+', '', text)
    text = re.sub(r'(.)\1{2,}', r'\1', text)
    return text

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id=None) -> bool:
    if user_id is None:
        user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    member = await context.bot.get_chat_member(chat_id, user_id)
    return member.status in ["administrator", "creator"]

async def bot_has_permission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    bot_id = (await context.bot.get_me()).id
    return await is_admin(update, context, bot_id)

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, duration_seconds: int = None):
    if duration_seconds:
        until_date = datetime.utcnow() + timedelta(seconds=duration_seconds)
    else:
        until_date = None
    permissions = ChatPermissions(can_send_messages=False)
    await context.bot.restrict_chat_member(
        chat_id=update.effective_chat.id,
        user_id=user_id,
        permissions=permissions,
        until_date=until_date
    )

async def unmute_member(chat_id, user_id, context: ContextTypes.DEFAULT_TYPE):
    permissions = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True
    )
    await context.bot.restrict_chat_member(chat_id=chat_id, user_id=user_id, permissions=permissions)

# ===== تحذير الأعضاء بدون حظر =====
async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, username: str):
    chat_id = str(update.effective_chat.id)
    user_id_str = str(user_id)
    if chat_id not in warns:
        warns[chat_id] = {}
    if user_id_str not in warns[chat_id]:
        warns[chat_id][user_id_str] = 0
    warns[chat_id][user_id_str] += 1
    save_warns()

    count = warns[chat_id][user_id_str]
    if count == 1:
        await mute_user(update, context, user_id, 3600)  # ساعة
        await update.message.reply_text(f"تحذير 1 لـ @{username}: كتم لمدة ساعة.")
    elif count == 2:
        await mute_user(update, context, user_id, 86400)  # 24 ساعة
        await update.message.reply_text(f"تحذير 2 لـ @{username}: كتم لمدة 24 ساعة.")
    else:
        await mute_user(update, context, user_id)  # كتم دائم
        await update.message.reply_text(f"تحذير {count} لـ @{username}: كتم دائم بسبب تكرار الكلمات السيئة.")

async def check_bad_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return
    if not await bot_has_permission(update, context):
        return
    text = normalize_text(update.message.text)
    for bad_word in BAD_WORDS:
        if bad_word in text:
            user = update.message.from_user
            await warn_user(update, context, user.id, user.username or user.first_name)
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
            break

# ===== الترحيب مع زر قبول القوانين =====
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await mute_user(update, context, member.id)
        keyboard = [[InlineKeyboardButton("أوافق على القوانين ✅", callback_data=f"accept_{member.id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        welcome_text = f"أهلاً وسهلاً بـ {member.first_name}!\n\n" \
                       "📌 قوانين المجموعة:\n" \
                       "1. ممنوع استخدام أي كلمات سيئة.\n" \
                       "2. احترم جميع الأعضاء.\n" \
                       "3. أي مخالفة راح تتعرض للتحذير والكتم.\n\n" \
                       "اضغط على الزر أدناه للموافقة على القوانين والدردشة."
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("accept_"):
        user_id = int(data.split("_")[1])
        if query.from_user.id != user_id:
            await query.edit_message_text("هذا الزر ليس لك!")
            return
        await unmute_member(query.message.chat.id, user_id, context)
        await query.edit_message_text(f"تم تفعيل الدردشة لـ {query.from_user.first_name} ✅")

# ===== أوامر الأدمن =====
async def warns_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("عذراً، هذه الخاصية للأدمن فقط.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("الرجاء الرد على رسالة العضو لمعرفة عدد تحذيراته.")
        return
    target_user = update.message.reply_to_message.from_user
    user_id_str = str(target_user.id)
    count = warns.get(str(update.effective_chat.id), {}).get(user_id_str, 0)
    await update.message.reply_text(f"عدد التحذيرات لـ @{target_user.username or target_user.first_name} هو: {count}")

async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("عذراً، هذه الخاصية للأدمن فقط.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("الرجاء الرد على رسالة العضو لفك كتمه.")
        return
    target_user = update.message.reply_to_message.from_user
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, target_user.id)
    except Exception:
        pass
    await unmute_member(update.effective_chat.id, target_user.id, context)
    await update.message.reply_text(f"تم فك الكتم عن @{target_user.username or target_user.first_name}")

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("عذراً، هذه الخاصية للأدمن فقط.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("الرجاء الرد على رسالة العضو لكتمه.")
        return
    target_user = update.message.reply_to_message.from_user
    permissions = ChatPermissions(can_send_messages=False)
    await context.bot.restrict_chat_member(update.effective_chat.id, target_user.id, permissions=permissions)
    await update.message.reply_text(f"تم كتم @{target_user.username or target_user.first_name} كتم دائم.")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("عذراً، هذه الخاصية للأدمن فقط.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("الرجاء الرد على رسالة العضو لفك حظره.")
        return
    target_user = update.message.reply_to_message.from_user
    try:
        await context.bot.unban_chat_member(chat_id=update.effective_chat.id, user_id=target_user.id)
        await update.message.reply_text(f"تم فك الحظر عن @{target_user.username or target_user.first_name}")
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ عند فك الحظر: {e}")

# ===== تشغيل البوت =====
def main():
    TOKEN = "8302691947:AAHxPeTGo4s-OmRQ8bmkC1KQzghw6cyBMAc"
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), check_bad_words))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("warns", warns_command))
    application.add_handler(CommandHandler("unmute", unmute_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("mute", mute_command))

    application.run_polling()

if __name__ == "__main__":
    main()