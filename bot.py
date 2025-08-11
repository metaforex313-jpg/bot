import re
import json
from telegram.ext import Updater, MessageHandler, Filters
from telegram.error import BadRequest
TOKEN = "8302691947:AAEa4Vnd8c_TBBk9MMZArLszqZXy7WwPrP4"
# قائمة الكلمات السيئة الأساسية
bad_words_list = [
    "حمار", "كلب", "زبالة", "حيوان", "قذر", "وغد", "نذل", "كسي", "خنزير", "كلخ",
    "أرعن", "شرموط", "حرامية", "لص", "حقير", "كلخرا", "غباء", "واطي", "زفت", "طيز", "عير",
    "عبيط", "كسخت", "كس", "نيك", "مص", "كسخته", "تافه", "سافل", "مشعوذ",
    "كسمك", "عرص", "زفت", "واطي", "عبيط", "دحيح", "شرموط", "خايب", "حمار و حشي",
    "طيزي", "كسختة", "انجب", "انجبي",
    "fuck", "shit", "bitch", "asshole", "dumb", "stupid", "idiot", "bastard", "damn",
    "dick", "piss", "crap", "slut", "whore", "jerk", "suck", "fag", "faggot",
    "cunt", "motherfucker", "bollocks", "bugger", "wanker",
    "cock", "twat", "arsehole", "prick", "douche", "douchebag", "pussy"
]
def create_regex_pattern(word):
    pattern = ''
    for char in word:
        if char.isalpha():
            pattern += f"[{char}{char.upper()}*@0]"
        else:
            pattern += char
    return pattern

bad_word_patterns = [re.compile(create_regex_pattern(word)) for word in bad_words_list]

def contains_bad_word(text):
    for pattern in bad_word_patterns:
        if pattern.search(text):
            return True
    return False

def load_warnings():
    try:
        with open(WARNINGS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_warnings(warnings_data):
    with open(WARNINGS_FILE, 'w') as f:
        json.dump(warnings_data, f)

user_warnings = load_warnings()

def filter_messages(update, context):
    message = update.message
    user_id = str(message.from_user.id)
    chat_id = message.chat_id
    text = message.text.lower()

    if contains_bad_word(text):
        try:
            context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
        except BadRequest:
            pass

        warnings = user_warnings.get(user_id, 0) + 1
        user_warnings[user_id] = warnings
        save_warnings(user_warnings)

        if warnings < 3:
            context.bot.send_message(chat_id=chat_id, text=f"⚠️ @{message.from_user.username or message.from_user.first_name}، هذه هي تحذيرك رقم {warnings}. الرجاء الالتزام بقوانين المجموعة.")
        else:
            try:
                context.bot.kick_chat_member(chat_id=chat_id, user_id=int(user_id))
                context.bot.send_message(chat_id=chat_id, text=f"🚫 @{message.from_user.username or message.from_user.first_name} تم حظره من المجموعة بعد تجاوز عدد التحذيرات.")
                user_warnings.pop(user_id, None)
                save_warnings(user_warnings)
            except BadRequest as e:
                context.bot.send_message(chat_id=chat_id, text=f"حدث خطأ أثناء محاولة حظر المستخدم: {e}")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.text & (~Filters.command), filter_messages))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()