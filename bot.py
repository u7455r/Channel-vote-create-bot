import os
import json
import time
import threading
from datetime import datetime, timezone, timedelta
import telebot
from telebot import types
from flask import Flask, request

# ================= CONFIGURATION =================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "9224149092:AAGME-O6M8BzELYSa4k-GULcMApsO2hACQo")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8298133943"))
ADMIN_USERNAME = "@rafimhossen"
BOT_USERNAME = "Votemaker5bot"
DEFAULT_LOG_CHANNEL = "@otpchannrl"
PROMO_CHANNEL = "@bdgiveaways24"

DEFAULT_REQUIRED_CHATS = [
    {"username": "@bdgiveaways24", "url": "https://t.me/bdgiveaways24", "name": "BD Giveaways 24"},
    {"username": "@bdgivewaychat", "url": "https://t.me/bdgivewaychat", "name": "BD Giveaway Chat"},
]

BAR_STYLES = {
    "classic": ("▓", "░"),
    "green": ("🟩", "⬜"),
    "blue": ("🔵", "⚪"),
    "fire": ("🔥", "🖤")
}

TIMEZONES = {
    "BST": ("🇧🇩 Bangladesh (UTC+6)", 6),
    "IST": ("🇮🇳 India (UTC+5:30)", 5.5),
    "GST": ("🇦🇪 UAE/Gulf (UTC+4)", 4),
    "UTC": ("🌐 UTC (UTC+0)", 0)
}

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=False)
app = Flask(__name__)

DB_FILE = "voting_bot_db.json"
db_lock = threading.Lock()
backup_dirty = False
user_states = {}
draft_polls = {}

def default_db_structure():
    return {
        "log_channel": DEFAULT_LOG_CHANNEL,
        "backup_msg_id": None,
        "vip_users": [],
        "verified_users": [],
        "banned_users": [],
        "required_chats": list(DEFAULT_REQUIRED_CHATS),
        "global_notice": "",
        "maintenance_mode": False,
        "milestone_targets": [100, 500, 1000],
        "suggestions": [],
        "ratings": {},
        "scheduled_posts": [],
        "last_daily_report_date": "",
        "users": {},
        "polls": {},
        "poll_counter": 100
    }

# ================= TELEGRAM PINNED CLOUD BACKUP & RESTORE =================
def ensure_db_defaults(data):
    defaults = default_db_structure()
    for k, v in defaults.items():
        data.setdefault(k, v)
    data["log_channel"] = DEFAULT_LOG_CHANNEL
    return data

def restore_db_from_telegram():
    try:
        chat = bot.get_chat(DEFAULT_LOG_CHANNEL)
        pinned = getattr(chat, "pinned_message", None)
        if pinned and getattr(pinned, "document", None):
            file_info = bot.get_file(pinned.document.file_id)
            downloaded = bot.download_file(file_info.file_path)
            data = json.loads(downloaded.decode("utf-8"))
            if isinstance(data, dict) and "polls" in data:
                data = ensure_db_defaults(data)
                data["backup_msg_id"] = pinned.message_id
                with open(DB_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"✅ Restored {len(data['polls'])} polls & {len(data['users'])} users from Cloud!")
                return data
    except Exception as e:
        print("Telegram restore check:", e)
    return None

def load_db():
    cloud_data = restore_db_from_telegram()
    if cloud_data:
        return cloud_data
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return ensure_db_defaults(json.load(f))
        except Exception:
            pass
    return default_db_structure()

def push_backup_to_telegram():
    global backup_dirty
    try:
        with db_lock:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2, ensure_ascii=False)
            old_msg_id = db.get("backup_msg_id")

        with open(DB_FILE, "rb") as doc:
            sent = bot.send_document(
                DEFAULT_LOG_CHANNEL,
                doc,
                caption=f"💾 <b>Auto Cloud Backup</b> | Polls: {len(db['polls'])} | Users: {len(db['users'])} | {time.strftime('%Y-%m-%d %H:%M:%S')}",
                disable_notification=True
            )
        bot.pin_chat_message(DEFAULT_LOG_CHANNEL, sent.message_id, disable_notification=True)
        db["backup_msg_id"] = sent.message_id
        with db_lock:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2, ensure_ascii=False)

        if old_msg_id and old_msg_id != sent.message_id:
            try:
                bot.delete_message(DEFAULT_LOG_CHANNEL, old_msg_id)
            except Exception:
                pass
        backup_dirty = False
    except Exception as e:
        print("Backup push error:", e)

def save_db(data, immediate_cloud=False):
    global backup_dirty
    with db_lock:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    backup_dirty = True
    if immediate_cloud:
        threading.Thread(target=push_backup_to_telegram, daemon=True).start()

db = load_db()

# ================= MULTI-LANGUAGE TEXTS (BN, EN, HI, AR) =================
TEXTS = {
    "bn": {
        "choose_lang": "🌐 অনুগ্রহ করে আপনার ভাষা নির্বাচন করুন / Select Language:",
        "force_join": "⚠️ <b>বটটি ব্যবহার করতে নিচের চ্যানেল ও গ্রুপে জয়েন করুন!</b>\n\nজয়েন করার পর <b>✅ Verify</b> বাটনে চাপুন:",
        "verify_btn": "✅ Verify / যাচাই করুন",
        "not_joined": "❌ আপনি এখনো সব চ্যানেল ও গ্রুপে জয়েন করেননি!",
        "bot_locked_screen": "😇 <b>নিচের বাটন থেকে অপশন নির্বাচন করুন।</b>\n\n🔒 বটটি আনলক করতে <b>১ জন বন্ধুকে</b> রেফার করুন!\n🔗 <b>রেফার লিংক:</b> <code>{ref_link}</code>\n👥 <b>বর্তমান রেফার:</b> <code>{refs}/1</code>",
        "check_unlock_btn": "🔄 Check Unlock",
        "still_locked_alert": "❌ এখনো ১টি রেফার পূর্ণ হয়নি!",
        "welcome": "😇 <b>স্বাগতম {name}!</b>\nনিচের বাটন থেকে অপশন নির্বাচন করুন এবং চ্যানেলে পোল তৈরি করুন।\n\n🔓 <b>স্ট্যাটাস:</b> আনলকড ✅ | 👥 <b>রেফার:</b> {refs} জন{v_badge}",
        "btn_create": "📣 চ্যানেল পোল তৈরি",
        "btn_edit": "✏️ পোল এডিট",
        "btn_profile": "🌟 প্রোফাইল ও হল অফ ফেম",
        "btn_schedule": "⏰ পোস্ট শিডিউল",
        "btn_search": "🔍 পোল খুঁজুন",
        "btn_refer": "🔗 রেফার ও ইনভাইট",
        "btn_support": "📞 সাপোর্ট ও রেটিং",
        "btn_lang": "🌐 ভাষা / Timezone",
        "btn_admin": "👑 Admin Panel",
        "btn_cancel": "❌ Cancel",
        "btn_text_only": "🟢 শুধুমাত্র লেখা",
        "create_prompt_inline": "😇 নিচের বাটনে চাপ দিয়ে নতুন পোল তৈরি শুরু করুন:",
        "create_now_btn": "🗳 Create Now Poll 🚀",
        "ask_channel": "📢 <b>আপনার চ্যানেল বা গ্রুপের লিংক / @username / ID পাঠান:</b>\n\n⚠️ আপনাকে ওই চ্যানেলের <b>Owner/Admin</b> হতে হবে এবং বটকেও <b>Admin</b> রাখতে হবে।",
        "not_bot_admin": "❌ <b>Error! বটটি ওই চ্যানেলে Admin নয় অথবা চ্যানেল পাওয়া যায়নি।</b> আবার চেষ্টা করুন:",
        "not_user_admin": "🚫 <b>অ্যাক্সেস প্রত্যাখ্যাত! আপনি এই চ্যানেলের Admin বা Owner নন।</b>",
        "ask_question": "❓ <b>আপনার পোলের প্রশ্ন/শিরোনাম লিখে পাঠান:</b>",
        "question_preview": "📝 <b>প্রশ্নের প্রিভিউ:</b>\n\n{question}\n━━━━━━━━━━━━━━━━━━━━\n✅ প্রশ্নটি কি ঠিক আছে?",
        "btn_q_ok": "✅ হ্যাঁ, ঠিক আছে",
        "btn_q_rewrite": "✏️ আবার লিখুন",
        "ask_photo": "📸 <b>পোলের জন্য ছবি/ব্যানার পাঠান</b> (অথবা <b>\"🟢 শুধুমাত্র লেখা\"</b> চাপুন):",
        "ask_options": "📋 <b>প্রার্থীদের নাম <code>&amp;</code> চিহ্ন দিয়ে লিখুন</b> (সর্বোচ্চ ৩০ জন):\nউদাহরণ: <code>নাম ১&amp;নাম ২&amp;নাম ৩</code>",
        "invalid_options": "❌ ১ থেকে ৩০ জন প্রার্থীর নাম <code>&amp;</code> দিয়ে লিখুন!",
        "poll_sent": "🚀 <b>আপনার চ্যানেলে পোল পাঠানো হয়েছে!</b>",
        "withdraw_btn": "🔄 ভোট প্রত্যাহার",
        "close_btn": "🛑 পোল বন্ধ",
        "closed_btn": "🔒 পোলটি বন্ধ করা হয়েছে",
        "cancelled": "❌ বাতিল করা হয়েছে। ড্যাশবোর্ডে ফিরে আসা হলো।"
    },
    "en": {
        "choose_lang": "🌐 Please select your language:",
        "force_join": "⚠️ <b>Please join the required channels & groups below to use this bot!</b>",
        "verify_btn": "✅ Verify Joined",
        "not_joined": "❌ You haven't joined all required chats yet!",
        "bot_locked_screen": "🔒 Refer at least <b>1 friend</b> to unlock the bot!\n🔗 <b>Link:</b> <code>{ref_link}</code>\n👥 <b>Referrals:</b> <code>{refs}/1</code>",
        "check_unlock_btn": "🔄 Check Unlock",
        "still_locked_alert": "❌ You still need 1 referral!",
        "welcome": "😇 <b>Welcome {name}!</b>\nCreate and manage live channel polls effortlessly.\n\n🔓 <b>Status:</b> Unlocked ✅ | 👥 <b>Referrals:</b> {refs}{v_badge}",
        "btn_create": "📣 Create Poll",
        "btn_edit": "✏️ Edit Polls",
        "btn_profile": "🌟 Profile & Hall of Fame",
        "btn_schedule": "⏰ Schedule Post",
        "btn_search": "🔍 Search Poll",
        "btn_refer": "🔗 Refer & Invite",
        "btn_support": "📞 Support & Rate",
        "btn_lang": "🌐 Language / Timezone",
        "btn_admin": "👑 Admin Panel",
        "btn_cancel": "❌ Cancel",
        "btn_text_only": "🟢 Text Only",
        "create_prompt_inline": "😇 Click below to create a new channel poll:",
        "create_now_btn": "🗳 Create Now Poll 🚀",
        "ask_channel": "📢 <b>Send your channel/group @username, link, or ID:</b>",
        "not_bot_admin": "❌ <b>Bot is not Admin there or chat not found.</b> Try again:",
        "not_user_admin": "🚫 <b>Access Denied! You are not an Admin/Owner of this chat.</b>",
        "ask_question": "❓ <b>Send your poll question/title:</b>",
        "question_preview": "📝 <b>Question Preview:</b>\n\n{question}\n━━━━━━━━━━━━━━━━━━━━\n✅ Looks good?",
        "btn_q_ok": "✅ Yes, Proceed",
        "btn_q_rewrite": "✏️ Rewrite",
        "ask_photo": "📸 <b>Send a banner photo</b> (or click <b>\"🟢 Text Only\"</b>):",
        "ask_options": "📋 <b>Send candidate names separated by <code>&amp;</code></b> (max 30):",
        "invalid_options": "❌ Send 1 to 30 names separated by <code>&amp;</code>!",
        "poll_sent": "🚀 <b>Poll has been published to your channel!</b>",
        "withdraw_btn": "🔄 Withdraw Vote",
        "close_btn": "🛑 Close Poll",
        "closed_btn": "🔒 Voting Closed",
        "cancelled": "❌ Cancelled. Returned to Dashboard."
    },
    "hi": {
        "choose_lang": "🌐 कृपया अपनी भाषा चुनें:",
        "force_join": "⚠️ <b>बॉट का उपयोग करने के लिए नीचे दिए गए चैनल और ग्रुप जॉइन करें!</b>",
        "verify_btn": "✅ Verify / सत्यापित करें",
        "not_joined": "❌ आपने अभी तक सभी चैनल जॉइन नहीं किए हैं!",
        "bot_locked_screen": "🔒 बॉट अनलॉक करने के लिए कम से कम <b>1 दोस्त</b> को रेफर करें!\n🔗 <b>लिंक:</b> <code>{ref_link}</code>\n👥 <b>रेफरल:</b> <code>{refs}/1</code>",
        "check_unlock_btn": "🔄 Check Unlock",
        "still_locked_alert": "❌ अभी 1 रेफरल पूरा नहीं हुआ है!",
        "welcome": "😇 <b>स्वागत है {name}!</b>\nनीचे दिए गए बटन से अपना चैनल पोल बनाएं।\n\n🔓 <b>स्टेटस:</b> अनलॉक ✅ | 👥 <b>रेफरल:</b> {refs}{v_badge}",
        "btn_create": "📣 नया पोल बनाएं",
        "btn_edit": "✏️ पोल एडिट करें",
        "btn_profile": "🌟 प्रोफ़ाइल और रिकॉर्ड",
        "btn_schedule": "⏰ पोस्ट शेड्यूल",
        "btn_search": "🔍 पोल खोजें",
        "btn_refer": "🔗 रेफर और इनवाइट",
        "btn_support": "📞 सपोर्ट और रेटिंग",
        "btn_lang": "🌐 भाषा / Timezone",
        "btn_admin": "👑 Admin Panel",
        "btn_cancel": "❌ Cancel",
        "btn_text_only": "🟢 केवल टेक्स्ट",
        "create_prompt_inline": "😇 नया पोल बनाने के लिए नीचे क्लिक करें:",
        "create_now_btn": "🗳 Create Now Poll 🚀",
        "ask_channel": "📢 <b>अपने चैनल या ग्रुप का @username या ID भेजें:</b>",
        "not_bot_admin": "❌ <b>बॉट इस चैनल में एडमिन नहीं है।</b> पुनः प्रयास करें:",
        "not_user_admin": "🚫 <b>आप इस चैनल के एडमिन या ओनर नहीं हैं।</b>",
        "ask_question": "❓ <b>अपने पोल का प्रश्न भेजें:</b>",
        "question_preview": "📝 <b>प्रश्न पूर्वावलोकन:</b>\n\n{question}\n━━━━━━━━━━━━━━━━━━━━\n✅ क्या यह सही है?",
        "btn_q_ok": "✅ हाँ, सही है",
        "btn_q_rewrite": "✏️ फिर से लिखें",
        "ask_photo": "📸 <b>पोल के लिए फोटो भेजें</b> (या <b>\"🟢 केवल टेक्स्ट\"</b> दबाएं):",
        "ask_options": "📋 <b>उम्मीदवारों के नाम <code>&amp;</code> से अलग करके लिखें:</b>",
        "invalid_options": "❌ 1 से 30 नाम <code>&amp;</code> के साथ लिखें!",
        "poll_sent": "🚀 <b>आपका पोल चैनल में भेज दिया गया है!</b>",
        "withdraw_btn": "🔄 वोट वापस लें",
        "close_btn": "🛑 पोल बंद करें",
        "closed_btn": "🔒 पोल बंद है",
        "cancelled": "❌ रद्द किया गया।"
    },
    "ar": {
        "choose_lang": "🌐 يرجى اختيار لغتك:",
        "force_join": "⚠️ <b>يجب الانضمام إلى القنوات والمجموعات أدناه لاستخدام البوت!</b>",
        "verify_btn": "✅ تحقق من الانضمام",
        "not_joined": "❌ لم تنضم إلى جميع القنوات المطلوبة بعد!",
        "bot_locked_screen": "🔒 قم بدعوة <b>صديق واحد</b> لفتح البوت!\n🔗 <b>الرابط:</b> <code>{ref_link}</code>\n👥 <b>الدعوات:</b> <code>{refs}/1</code>",
        "check_unlock_btn": "🔄 تحقق من الفتح",
        "still_locked_alert": "❌ تحتاج إلى دعوة صديق واحد أولاً!",
        "welcome": "😇 <b>مرحباً {name}!</b>\nأنشئ استطلاعات احترافية لقناتك بسهولة.\n\n🔓 <b>الحالة:</b> مفعل ✅ | 👥 <b>الدعوات:</b> {refs}{v_badge}",
        "btn_create": "📣 إنشاء استطلاع",
        "btn_edit": "✏️ تعديل الاستطلاعات",
        "btn_profile": "🌟 الملف الشخصي",
        "btn_schedule": "⏰ جدولة منشور",
        "btn_search": "🔍 بحث عن استطلاع",
        "btn_refer": "🔗 دعوة الأصدقاء",
        "btn_support": "📞 الدعم والتقييم",
        "btn_lang": "🌐 اللغة / الوقت",
        "btn_admin": "👑 Admin Panel",
        "btn_cancel": "❌ إلغاء",
        "btn_text_only": "🟢 نص فقط",
        "create_prompt_inline": "😇 اضغط أدناه لإنشاء استطلاع جديد:",
        "create_now_btn": "🗳 Create Now Poll 🚀",
        "ask_channel": "📢 <b>أرسل معرف القناة أو المجموعة (@username أو ID):</b>",
        "not_bot_admin": "❌ <b>البوت ليس مشرفاً في هذه القناة.</b> حاول مرة أخرى:",
        "not_user_admin": "🚫 <b>لست مشرفاً في هذه القناة.</b>",
        "ask_question": "❓ <b>أرسل سؤال الاستطلاع:</b>",
        "question_preview": "📝 <b>معاينة السؤال:</b>\n\n{question}\n━━━━━━━━━━━━━━━━━━━━\n✅ هل السؤال صحيح؟",
        "btn_q_ok": "✅ نعم، متابعة",
        "btn_q_rewrite": "✏️ إعادة كتابة",
        "ask_photo": "📸 <b>أرسل صورة للاستطلاع</b> (أو اختر <b>\"🟢 نص فقط\"</b>):",
        "ask_options": "📋 <b>أرسل أسماء المرشحين مفصولة بـ <code>&amp;</code>:</b>",
        "invalid_options": "❌ أرسل من 1 إلى 30 اسماً مفصولة بـ <code>&amp;</code>!",
        "poll_sent": "🚀 <b>تم نشر الاستطلاع في قناتك بنجاح!</b>",
        "withdraw_btn": "🔄 سحب التصويت",
        "close_btn": "🛑 إغلاق الاستطلاع",
        "closed_btn": "🔒 الاستطلاع مغلق",
        "cancelled": "❌ تم الإلغاء."
    }
}

# ================= HELPER FUNCTIONS =================
def get_lang(user_id):
    return db["users"].get(str(user_id), {}).get("lang", "bn")

def t(user_id, key):
    lang = get_lang(user_id)
    return TEXTS.get(lang, TEXTS["bn"]).get(key, TEXTS["bn"].get(key, ""))

def get_user_tz_offset(user_id):
    tz_code = db["users"].get(str(user_id), {}).get("timezone", "BST")
    return TIMEZONES.get(tz_code, TIMEZONES["BST"])[1]

def format_user_time(ts, user_id):
    offset = get_user_tz_offset(user_id)
    dt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=offset)))
    return dt.strftime("%Y-%m-%d %I:%M %p")

def is_banned(user_id):
    return int(user_id) != ADMIN_ID and int(user_id) in db.get("banned_users", [])

def is_vip(user_id):
    return int(user_id) == ADMIN_ID or int(user_id) in db.get("vip_users", [])

def is_verified_creator(user_id):
    uid_int = int(user_id)
    if uid_int == ADMIN_ID or uid_int in db.get("vip_users", []) or uid_int in db.get("verified_users", []):
        return True
    return db["users"].get(str(uid_int), {}).get("referrals", 0) >= 5

def is_unlocked(user_id):
    if is_vip(user_id):
        return True
    return db["users"].get(str(user_id), {}).get("referrals", 0) >= 1

def can_manage_poll(poll, user_id):
    uid = int(user_id)
    if uid == ADMIN_ID or uid == int(poll["owner_id"]):
        return True
    return uid in [int(x) for x in poll.get("co_hosts", [])]

def check_all_joined(user_id):
    if is_vip(user_id):
        return True
    for chat in db.get("required_chats", DEFAULT_REQUIRED_CHATS):
        try:
            member = bot.get_chat_member(chat["username"], user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True

def get_option_total_votes(opt):
    return max(0, len(opt.get("voters", [])) + int(opt.get("bonus_votes", 0)))

def main_menu_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(t(user_id, "btn_create"), t(user_id, "btn_edit"))
    markup.row(t(user_id, "btn_profile"), t(user_id, "btn_search"))
    markup.row(t(user_id, "btn_schedule"), t(user_id, "btn_refer"))
    markup.row(t(user_id, "btn_support"), t(user_id, "btn_lang"))
    if int(user_id) == ADMIN_ID:
        markup.row(t(user_id, "btn_admin"))
    return markup

def cancel_keyboard(user_id, include_text_only=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if include_text_only:
        markup.row(t(user_id, "btn_text_only"))
    markup.row(t(user_id, "btn_cancel"))
    return markup

def send_force_join_msg(chat_id, user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in db.get("required_chats", DEFAULT_REQUIRED_CHATS):
        markup.add(types.InlineKeyboardButton(f"📢 Join {ch['name']}", url=ch["url"]))
    markup.add(types.InlineKeyboardButton(t(user_id, "verify_btn"), callback_data="verify_join"))
    bot.send_message(chat_id, t(user_id, "force_join"), reply_markup=markup, disable_web_page_preview=True)

def send_lock_screen(chat_id, user_id):
    uid = str(user_id)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
    refs = db["users"].get(uid, {}).get("referrals", 0)
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📤 Share Referral Link", url=f"https://t.me/share/url?url={ref_link}"),
        types.InlineKeyboardButton(t(user_id, "check_unlock_btn"), callback_data="check_unlock"),
        types.InlineKeyboardButton("🌐 Language / ভাষা", callback_data="open_lang")
    )
    bot.send_message(chat_id, t(user_id, "bot_locked_screen").format(ref_link=ref_link, refs=refs), reply_markup=markup)

def send_log_to_channel(text):
    log_ch = db.get("log_channel") or DEFAULT_LOG_CHANNEL
    if log_ch:
        try:
            bot.send_message(log_ch, text, disable_web_page_preview=True)
        except Exception as e:
            print("Log error:", e)

def make_progress_bar(count, total, style="classic"):
    fill_ch, empty_ch = BAR_STYLES.get(style, ("▓", "░"))
    if total <= 0:
        return f"{empty_ch * 8} 0%"
    pct = round((count / total) * 100)
    filled = round((pct / 100) * 8)
    bar = fill_ch * filled + empty_ch * (8 - filled)
    return f"{bar} {pct}%"

def get_rank_medals(options):
    counts = sorted(list(set(get_option_total_votes(o) for o in options if get_option_total_votes(o) > 0)), reverse=True)
    medals = {}
    for idx, o in enumerate(options):
        c = get_option_total_votes(o)
        if c == 0 or not counts:
            medals[idx] = "🔥"
        elif c == counts[0]:
            medals[idx] = "🥇"
        elif len(counts) > 1 and c == counts[1]:
            medals[idx] = "🥈"
        elif len(counts) > 2 and c == counts[2]:
            medals[idx] = "🥉"
        else:
            medals[idx] = "🔥"
    return medals

def build_channel_poll_caption(poll_id):
    poll = db["polls"][poll_id]
    total_votes = sum(get_option_total_votes(o) for o in poll["options"])
    medals = get_rank_medals(poll["options"])
    bar_style = poll.get("bar_style", "classic")

    stats_lines = []
    for idx, o in enumerate(poll["options"]):
        cnt = get_option_total_votes(o)
        p_bar = make_progress_bar(cnt, total_votes, bar_style)
        stats_lines.append(f"{medals[idx]} <b>{o['name']}</b> — <code>{cnt}</code>\n   <code>{p_bar}</code>")
    stats_block = "\n".join(stats_lines)

    meta_lines = []
    if poll.get("target_votes") and poll.get("is_open", True):
        meta_lines.append(f"🎯 <b>Target Goal:</b> <code>{poll['target_votes']}</code> Votes")
    if poll.get("close_at") and poll.get("is_open", True):
        rem_sec = int(poll["close_at"] - time.time())
        if rem_sec > 0:
            hrs = rem_sec // 3600
            mins = (rem_sec % 3600) // 60
            meta_lines.append(f"⏳ <b>Time Left:</b> {hrs}h {mins}m")
    if is_verified_creator(poll["owner_id"]):
        meta_lines.append("✅ <b>Verified Organizer</b>")

    meta_block = ("\n" + "\n".join(meta_lines)) if meta_lines else ""

    owner_data = db["users"].get(str(poll["owner_id"]), {})
    custom_footer = owner_data.get("custom_footer", "") if is_vip(poll["owner_id"]) else ""
    footer_block = (
        f"⚡ Poll Create :- @{BOT_USERNAME}\n"
        f"{custom_footer if custom_footer else f'📢 Join :- {PROMO_CHANNEL}'}"
    )

    return (
        f"🗳 <b>{poll['question']}</b>\n\n"
        f"{stats_block}\n\n"
        f"📈 <b>Total Votes:</b> <code>{total_votes}</code>{meta_block}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{footer_block}"
    )

def build_channel_poll_markup(poll_id):
    poll = db["polls"][poll_id]
    owner_id = poll["owner_id"]
    markup = types.InlineKeyboardMarkup(row_width=1)
    is_open = poll.get("is_open", True)
    medals = get_rank_medals(poll["options"])

    for idx, opt in enumerate(poll["options"]):
        v_count = get_option_total_votes(opt)
        medal = medals[idx]
        btn_text = f"🗳 {v_count} | {medal} {opt['name']}" if is_open else f"🔒 {v_count} | {medal} {opt['name']}"
        cb = f"pvote:{poll_id}:{idx}" if is_open else f"pclosed:{poll_id}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=cb))

    if is_open:
        markup.row(
            types.InlineKeyboardButton(t(owner_id, "withdraw_btn"), callback_data=f"pwithdraw:{poll_id}"),
            types.InlineKeyboardButton(t(owner_id, "close_btn"), callback_data=f"pclose:{poll_id}")
        )
    else:
        markup.add(types.InlineKeyboardButton(t(owner_id, "closed_btn"), callback_data=f"pclosed:{poll_id}"))
    return markup

def refresh_channel_poll_message(pid):
    poll = db["polls"].get(pid)
    if not poll or not poll.get("message_id"):
        return
    caption = build_channel_poll_caption(pid)
    if not poll.get("is_open", True):
        caption += "\n\n🛑 <b>[VOTING CLOSED]</b>"
    markup = build_channel_poll_markup(pid)
    try:
        if poll.get("photo_id"):
            bot.edit_message_caption(caption, poll["channel_id"], poll["message_id"], reply_markup=markup)
        else:
            bot.edit_message_text(caption, poll["channel_id"], poll["message_id"], reply_markup=markup)
    except Exception:
        pass

def deduct_vote_on_channel_leave(channel_id, left_user_id):
    changed_any = False
    for pid, poll in list(db.get("polls", {}).items()):
        if not poll.get("is_open", True):
            continue
        if str(poll.get("channel_id")) != str(channel_id):
            continue
        for opt in poll["options"]:
            if left_user_id in opt["voters"]:
                opt["voters"].remove(left_user_id)
                changed_any = True
                save_db(db)
                refresh_channel_poll_message(pid)
                rem_total = sum(get_option_total_votes(o) for o in poll["options"])
                leave_log = (
                    f"⚠️ <b>চ্যানেল লিভ করার কারণে ভোট মাইনাস (-1) হয়েছে!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"🆔 <b>Poll ID:</b> <code>#{pid}</code> ({poll['channel_username']})\n"
                    f"👤 <b>যিনি লিভ নিয়েছেন:</b> <code>{left_user_id}</code>\n"
                    f"➖ <b>ভোট কমেছে:</b> {opt['name']} (বর্তমান মোট ভোট: {rem_total})\n"
                    f"━━━━━━━━━━━━━━━━━━━━"
                )
                send_log_to_channel(leave_log)
                break
    return changed_any

@bot.chat_member_handler()
def handle_member_leave_update(update: types.ChatMemberUpdated):
    try:
        if update.new_chat_member.status in ["left", "kicked"]:
            deduct_vote_on_channel_leave(update.chat.id, update.new_chat_member.user.id)
    except Exception as e:
        print("Chat member update error:", e)

def build_hourly_graph_report(pid):
    poll = db["polls"].get(pid)
    if not poll:
        return "❌ পোল পাওয়া যায়নি।"
    hourly = poll.get("hourly_votes", {})
    total_v = sum(get_option_total_votes(o) for o in poll["options"])

    if not hourly or total_v == 0:
        return f"📈 <b>Hourly Vote Analytics (Poll #{pid})</b>\n━━━━━━━━━━━━━━━━━━━━\n📭 এখনো কোনো ভোট পড়েনি।"

    max_v = max(hourly.values())
    peak_hour = max(hourly, key=hourly.get)
    lines = [
        f"📈 <b>Hourly Vote Graph (Poll #{pid})</b>",
        f"📣 <b>চ্যানেল:</b> {poll['channel_username']}",
        f"🔥 <b>Peak Hour:</b> <code>{peak_hour}</code> ({max_v} ভোট)",
        "━━━━━━━━━━━━━━━━━━━━"
    ]
    for hr, cnt in sorted(hourly.items()):
        bar = "▇" * max(1, round((cnt / max_v) * 10))
        lines.append(f"🕒 <code>{hr}</code> | <code>{bar}</code> <b>{cnt}</b>")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📊 <b>সর্বমোট ভোট:</b> <code>{total_v}</code>")
    return "\n".join(lines)

def announce_poll_winner(pid, close_reason="🛑 ভোটিং সমাপ্ত"):
    poll = db["polls"].get(pid)
    if not poll:
        return
    poll["is_open"] = False
    poll["close_at"] = None
    if poll.get("auto_delete_24h"):
        poll["delete_at"] = time.time() + 86400
    save_db(db, immediate_cloud=True)
    refresh_channel_poll_message(pid)

    sorted_opts = sorted(poll["options"], key=lambda x: get_option_total_votes(x), reverse=True)
    winner = sorted_opts[0] if sorted_opts else {"name": "N/A", "voters": [], "bonus_votes": 0}
    total_v = sum(get_option_total_votes(o) for o in poll["options"])
    rank_icons = ["🥇", "🥈", "🥉"]
    standings = "\n".join([
        f"{rank_icons[idx] if idx < 3 else f'{idx+1}.'} <b>{o['name']}</b> — <code>{get_option_total_votes(o)}</code> ভোট"
        for idx, o in enumerate(sorted_opts)
    ])

    win_msg = (
        f"🏆🎉 <b>FINAL POLL RESULT (#{pid})</b> 🎉🏆\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"❓ <b>প্রশ্ন:</b> {poll['question']}\n\n"
        f"👑 <b>বিজয়ী (Winner):</b> 🥇 <b>{winner['name']}</b> ({get_option_total_votes(winner)} ভোট)\n\n"
        f"📊 <b>চূড়ান্ত ফলাফল (মোট {total_v} ভোট):</b>\n"
        f"{standings}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{close_reason}"
    )
    try:
        bot.send_message(poll["channel_id"], win_msg)
    except Exception:
        pass
    send_log_to_channel(f"🏁 <b>পোল #{pid} সমাপ্ত!</b> ({poll['channel_username']})\n🥇 বিজয়ী: <b>{winner['name']}</b> ({get_option_total_votes(winner)} ভোট)")

def generate_daily_admin_summary():
    today_str = datetime.now(timezone(timedelta(hours=6))).strftime("%Y-%m-%d")
    new_users_today = sum(1 for u in db["users"].values() if str(u.get("joined_at", "")).startswith(today_str))
    new_polls_today = sum(1 for p in db["polls"].values() if str(p.get("created_at", "")).startswith(today_str))
    total_votes = sum(sum(get_option_total_votes(o) for o in p["options"]) for p in db["polls"].values())
    active_polls = sum(1 for p in db["polls"].values() if p.get("is_open", True))
    avg_rating = round(sum(r["stars"] for r in db.get("ratings", {}).values()) / len(db["ratings"]), 2) if db.get("ratings") else 0

    return (
        f"📊 <b>Daily Midnight Admin Summary ({today_str})</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆕 <b>আজকের নতুন ইউজার:</b> <code>{new_users_today}</code> জন\n"
        f"👥 <b>সর্বমোট ইউজার:</b> <code>{len(db['users'])}</code> জন\n"
        f"🆕 <b>আজকের তৈরি পোল:</b> <code>{new_polls_today}</code> টি\n"
        f"🟢 <b>বর্তমানে চলমান পোল:</b> <code>{active_polls}</code> টি\n"
        f"❤️ <b>সর্বমোট ভোট:</b> <code>{total_votes}</code> টি\n"
        f"⭐ <b>গড় বট রেটিং:</b> <code>{avg_rating}/5.0</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

# ================= BACKGROUND WATCHER (TIMERS + SCHEDULED POSTS + AUTO-DELETE + DAILY REPORT) =================
def background_watcher():
    global backup_dirty
    tick = 0
    while True:
        try:
            now = time.time()
            tick += 1

            if backup_dirty:
                push_backup_to_telegram()

            # 1. Midnight Daily Report (Bangladesh UTC+6)
            bd_now = datetime.now(timezone(timedelta(hours=6)))
            today_key = bd_now.strftime("%Y-%m-%d")
            if bd_now.hour == 0 and bd_now.minute < 5 and db.get("last_daily_report_date") != today_key:
                db["last_daily_report_date"] = today_key
                save_db(db, immediate_cloud=True)
                try:
                    bot.send_message(ADMIN_ID, generate_daily_admin_summary())
                except Exception:
                    pass

            # 2. Scheduled Channel Posts (#58)
            remaining_sched = []
            sched_changed = False
            for sp in list(db.get("scheduled_posts", [])):
                if now >= sp["send_at"]:
                    sched_changed = True
                    try:
                        if sp.get("photo_id"):
                            bot.send_photo(sp["channel_id"], sp["photo_id"], caption=sp["text"])
                        else:
                            bot.send_message(sp["channel_id"], sp["text"])
                        bot.send_message(sp["owner_id"], f"✅ আপনার শিডিউল করা পোস্টটি <b>{sp['channel_username']}</b> চ্যানেলে সফলভাবে পাবলিশ হয়েছে!")
                    except Exception as e:
                        try:
                            bot.send_message(sp["owner_id"], f"❌ শিডিউল পোস্ট পাঠাতে ব্যর্থ ({sp['channel_username']}): {e}")
                        except Exception:
                            pass
                else:
                    remaining_sched.append(sp)
            if sched_changed:
                db["scheduled_posts"] = remaining_sched
                save_db(db, immediate_cloud=True)

            # 3. Polls Watcher (Auto-Timer, Auto-Delete 24h after close, Anti-Leave Audit)
            for pid, poll in list(db.get("polls", {}).items()):
                if not poll.get("is_open", True):
                    del_ts = poll.get("delete_at")
                    if del_ts and now >= del_ts and poll.get("message_id"):
                        try:
                            bot.delete_message(poll["channel_id"], poll["message_id"])
                        except Exception:
                            pass
                        poll["delete_at"] = None
                        save_db(db)
                    continue

                close_ts = poll.get("close_at")
                if close_ts and now >= close_ts:
                    announce_poll_winner(pid, close_reason="⏰ নির্ধারিত সময় শেষ (Auto-Closed)")
                    continue

                if tick % 3 == 0:
                    ch_id = poll.get("channel_id")
                    removed_in_poll = False
                    for opt in poll["options"]:
                        for vid in list(opt["voters"]):
                            try:
                                mem = bot.get_chat_member(ch_id, vid)
                                if mem.status in ["left", "kicked"]:
                                    opt["voters"].remove(vid)
                                    removed_in_poll = True
                                    send_log_to_channel(
                                        f"⚠️ <b>অ্যান্টি-লিভ অটো রিমুভ (-1 ভোট)!</b>\n"
                                        f"🆔 Poll: <code>#{pid}</code> ({poll['channel_username']})\n"
                                        f"👤 লিভ নেওয়া ভোটার: <code>{vid}</code> (প্রার্থী: {opt['name']})"
                                    )
                            except Exception:
                                pass
                            time.sleep(0.15)
                    if removed_in_poll:
                        save_db(db)
                        refresh_channel_poll_message(pid)
        except Exception as e:
            print("Background watcher error:", e)
        time.sleep(20)

def register_user(user, ref_by=None):
    uid = str(user.id)
    is_new = False
    if uid not in db["users"]:
        is_new = True
        db["users"][uid] = {
            "id": user.id,
            "name": user.first_name or "User",
            "username": f"@{user.username}" if user.username else "No Username",
            "lang": "bn",
            "timezone": "BST",
            "custom_footer": "",
            "votes_cast": 0,
            "referrals": 0,
            "referred_by": None,
            "joined_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        if ref_by and ref_by != uid and ref_by in db["users"]:
            db["users"][uid]["referred_by"] = ref_by
            db["users"][ref_by]["referrals"] += 1
            new_ref_cnt = db["users"][ref_by]["referrals"]
            bonus_txt = "\n🏅 <b>৫টি রেফার পূর্ণ হওয়ায় আপনি '✅ Verified Organizer' ব্যাজ পেয়েছেন!</b>" if new_ref_cnt == 5 else ""
            try:
                bot.send_message(int(ref_by), f"🎊 অভিনন্দন! <b>{user.first_name}</b> আপনার রেফারে জয়েন করেছেন! বট আনলক হয়েছে 🔓{bonus_txt}")
            except Exception:
                pass
        save_db(db)

        log_msg = (
            f"🆕 <b>নতুন ইউজার বট স্টার্ট করেছেন!</b>\n"
            f"👤 <b>নাম:</b> {user.first_name}\n"
            f"🔰 <b>ইউজারনেম:</b> {db['users'][uid]['username']}\n"
            f"🆔 <b>ইউজার আইডি:</b> <code>{uid}</code>\n"
            f"👥 <b>রেফার বাই:</b> <code>{ref_by if ref_by else 'Direct'}</code>"
        )
        send_log_to_channel(log_msg)
        if user.id != ADMIN_ID:
            try:
                bot.send_message(ADMIN_ID, log_msg)
            except Exception:
                pass
    else:
        db["users"][uid].setdefault("timezone", "BST")
        db["users"][uid].setdefault("custom_footer", "")
        db["users"][uid].setdefault("votes_cast", 0)
        db["users"][uid]["name"] = user.first_name or "User"
        db["users"][uid]["username"] = f"@{user.username}" if user.username else "No Username"
        save_db(db)
    return is_new

def send_dashboard(chat_id, user):
    if is_banned(user.id):
        bot.send_message(chat_id, "🚫 <b>আপনাকে এই বট থেকে ব্যান করা হয়েছে।</b>")
        return
    if db.get("maintenance_mode") and user.id != ADMIN_ID:
        bot.send_message(chat_id, "🛠️ <b>বটে বর্তমানে জরুরি আপডেটের কাজ চলছে। কিছুক্ষণ পর আবার চেষ্টা করুন!</b>")
        return
    if not check_all_joined(user.id):
        send_force_join_msg(chat_id, user.id)
        return
    if not is_unlocked(user.id):
        send_lock_screen(chat_id, user.id)
        return
    refs = db["users"].get(str(user.id), {}).get("referrals", 0)
    v_badge = " | ✅ <b>Verified Organizer</b>" if is_verified_creator(user.id) else ""
    notice = db.get("global_notice", "").strip()
    notice_block = f"\n\n📌 <b>Notice:</b> {notice}" if notice else ""
    bot.send_message(
        chat_id,
        t(user.id, "welcome").format(name=user.first_name, refs=refs, v_badge=v_badge) + notice_block,
        reply_markup=main_menu_keyboard(user.id)
    )

def passes_gate(message):
    register_user(message.from_user)
    uid = message.from_user.id
    if is_banned(uid):
        bot.send_message(message.chat.id, "🚫 <b>আপনাকে এই বট থেকে ব্যান করা হয়েছে।</b>")
        return False
    if db.get("maintenance_mode") and uid != ADMIN_ID:
        bot.send_message(message.chat.id, "🛠️ <b>বটে বর্তমানে জরুরি আপডেটের কাজ চলছে। কিছুক্ষণ পর আবার চেষ্টা করুন!</b>")
        return False
    if not check_all_joined(uid):
        send_force_join_msg(message.chat.id, uid)
        return False
    if not is_unlocked(uid):
        send_lock_screen(message.chat.id, uid)
        return False
    return True

# ================= START, DEEP-LINK DIRECT VOTE & LANGUAGE / TIMEZONE =================
@bot.message_handler(commands=["start"])
def handle_start(message):
    user_states.pop(message.from_user.id, None)
    draft_polls.pop(message.from_user.id, None)
    args = message.text.split()
    payload = args[1] if len(args) > 1 else ""

    if payload.startswith("v_"):
        register_user(message.from_user)
        parts = payload.split("_")
        if len(parts) == 3 and parts[1] in db["polls"] and parts[2].isdigit():
            pid = parts[1]
            opt_idx = int(parts[2])
            poll = db["polls"][pid]
            if 0 <= opt_idx < len(poll["options"]):
                cand_name = poll["options"][opt_idx]["name"]
                ch_clean = poll["channel_username"].lstrip("@")
                markup = types.InlineKeyboardMarkup(row_width=1)
                markup.add(
                    types.InlineKeyboardButton(f"✅ হ্যাঁ, {cand_name}-কে ভোট দিন", callback_data=f"directvote:{pid}:{opt_idx}"),
                    types.InlineKeyboardButton("📢 চ্যানেল দেখুন", url=f"https://t.me/{ch_clean}" if not ch_clean.startswith("-100") else "https://t.me/bdgiveaways24")
                )
                bot.send_message(
                    message.chat.id,
                    f"🗳 <b>ডিরেক্ট ভোট কনফার্মেশন (#{pid})</b>\n\n"
                    f"❓ <b>প্রশ্ন:</b> {poll['question']}\n"
                    f"🔥 <b>প্রার্থী:</b> <b>{cand_name}</b>\n\n"
                    f"👇 ভোট নিশ্চিত করতে নিচের বাটনে চাপুন:",
                    reply_markup=markup
                )
                return

    ref_by = payload.replace("ref_", "") if payload.startswith("ref_") else None
    is_new = register_user(message.from_user, ref_by=ref_by)
    if is_new and not is_vip(message.from_user.id):
        send_lang_tz_menu(message.chat.id, message.from_user.id)
        return
    send_dashboard(message.chat.id, message.from_user)

def send_lang_tz_menu(chat_id, uid):
    cur_tz = db["users"].get(str(uid), {}).get("timezone", "BST")
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇧🇩 বাংলা", callback_data="setlang:bn"),
        types.InlineKeyboardButton("🇺🇸 English", callback_data="setlang:en"),
        types.InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="setlang:hi"),
        types.InlineKeyboardButton("🇸🇦 العربية", callback_data="setlang:ar")
    )
    markup.add(
        types.InlineKeyboardButton(f"🕒 BST (+6){' ✅' if cur_tz=='BST' else ''}", callback_data="settz:BST"),
        types.InlineKeyboardButton(f"🕒 IST (+5:30){' ✅' if cur_tz=='IST' else ''}", callback_data="settz:IST"),
        types.InlineKeyboardButton(f"🕒 GST (+4){' ✅' if cur_tz=='GST' else ''}", callback_data="settz:GST"),
        types.InlineKeyboardButton(f"🕒 UTC (+0){' ✅' if cur_tz=='UTC' else ''}", callback_data="settz:UTC")
    )
    bot.send_message(chat_id, t(uid, "choose_lang") + f"\n🕒 <b>Current Timezone:</b> <code>{cur_tz}</code>", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("directvote:"))
def cb_direct_candidate_vote(call):
    parts = call.data.split(":")
    process_vote_action(call, parts[1], int(parts[2]), from_direct=True)

@bot.callback_query_handler(func=lambda c: c.data == "open_lang")
def cb_open_lang(call):
    send_lang_tz_menu(call.message.chat.id, call.from_user.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("setlang:"))
def cb_set_lang(call):
    lang = call.data.split(":")[1]
    register_user(call.from_user)
    db["users"][str(call.from_user.id)]["lang"] = lang
    save_db(db)
    bot.answer_callback_query(call.id, "Language Updated!")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_dashboard(call.message.chat.id, call.from_user)

@bot.callback_query_handler(func=lambda c: c.data.startswith("settz:"))
def cb_set_tz(call):
    tz_code = call.data.split(":")[1]
    register_user(call.from_user)
    db["users"][str(call.from_user.id)]["timezone"] = tz_code
    save_db(db)
    bot.answer_callback_query(call.id, f"Timezone set to {tz_code}!", show_alert=True)
    send_dashboard(call.message.chat.id, call.from_user)

@bot.callback_query_handler(func=lambda c: c.data == "verify_join")
def cb_verify_join(call):
    if check_all_joined(call.from_user.id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        send_dashboard(call.message.chat.id, call.from_user)
    else:
        bot.answer_callback_query(call.id, t(call.from_user.id, "not_joined"), show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data == "check_unlock")
def cb_check_unlock(call):
    if not check_all_joined(call.from_user.id):
        bot.answer_callback_query(call.id, t(call.from_user.id, "not_joined"), show_alert=True)
        return
    if is_unlocked(call.from_user.id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        send_dashboard(call.message.chat.id, call.from_user)
    else:
        bot.answer_callback_query(call.id, t(call.from_user.id, "still_locked_alert"), show_alert=True)

# ================= CANCEL HANDLER =================
@bot.message_handler(func=lambda m: m.text in [TEXTS[l]["btn_cancel"] for l in TEXTS] + ["/cancel"])
def handle_cancel_btn(message):
    user_states.pop(message.from_user.id, None)
    draft_polls.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, t(message.from_user.id, "cancelled"), reply_markup=main_menu_keyboard(message.from_user.id))

# ================= MENU BUTTONS & NEW FEATURES =================
@bot.message_handler(func=lambda m: m.text in [TEXTS[l]["btn_lang"] for l in TEXTS])
def menu_lang(message):
    send_lang_tz_menu(message.chat.id, message.from_user.id)

@bot.message_handler(func=lambda m: m.text in [TEXTS[l]["btn_refer"] for l in TEXTS])
def menu_refer(message):
    if not passes_gate(message):
        return
    uid = str(message.from_user.id)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
    refs = db["users"][uid]["referrals"]
    v_status = "✅ Verified Organizer (Active)" if is_verified_creator(message.from_user.id) else f"🔒 আরও {max(0, 5-refs)}টি রেফার করলে '✅ Verified Organizer' ব্যাজ পাবেন!"
    vip_note = "\n👑 <b>VIP Custom Footer:</b> <code>/setfooter আপনার লেখা</code> দিয়ে নিজের ফুটার সেট করতে পারবেন!" if is_vip(message.from_user.id) else ""
    bot.send_message(
        message.chat.id,
        f"🔗 <b>রেফারেল লিংক:</b>\n<code>{ref_link}</code>\n\n"
        f"👥 <b>মোট রেফার:</b> {refs} জন\n"
        f"🏅 <b>ব্যাজ স্ট্যাটাস:</b> {v_status}{vip_note}"
    )

# VIP Custom Footer (#94)
@bot.message_handler(commands=["setfooter"])
def cmd_set_vip_footer(message):
    if not passes_gate(message):
        return
    uid = message.from_user.id
    if not is_vip(uid):
        bot.reply_to(message, "🔒 এই ফিচারটি শুধুমাত্র <b>VIP ইউজারদের</b> জন্য! অ্যাডমিনের সাথে যোগাযোগ করুন: @rafimhossen")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "📝 <b>ব্যবহার:</b> <code>/setfooter 📢 Join :- @YourChannel</code>\nমুছে ফেলতে: <code>/setfooter reset</code>")
        return
    val = parts[1].strip()
    db["users"][str(uid)]["custom_footer"] = "" if val.lower() == "reset" else val
    save_db(db, immediate_cloud=True)
    bot.reply_to(message, "✅ আপনার কাস্টম পোল ফুটার আপডেট হয়েছে!")

# Profile Card (#65) & Hall of Fame (#66)
@bot.message_handler(commands=["profile", "halloffame"])
@bot.message_handler(func=lambda m: m.text in [TEXTS[l]["btn_profile"] for l in TEXTS])
def menu_profile_and_hof(message):
    if not passes_gate(message):
        return
    uid = message.from_user.id
    u = db["users"].get(str(uid), {})
    my_polls = [p for p in db["polls"].values() if int(p["owner_id"]) == uid]
    total_votes_received = sum(sum(get_option_total_votes(o) for o in p["options"]) for p in my_polls)
    badge = "👑 VIP Organizer" if is_vip(uid) else ("✅ Verified Organizer" if is_verified_creator(uid) else "👤 Standard Member")

    text = (
        f"🌟 <b>ইউজার প্রোফাইল কার্ড (#{uid})</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>নাম:</b> {u.get('name', 'User')}\n"
        f"🏅 <b>স্ট্যাটাস:</b> {badge}\n"
        f"🗳 <b>তৈরি করা পোল:</b> <code>{len(my_polls)}</code> টি\n"
        f"📈 <b>পোলে প্রাপ্ত মোট ভোট:</b> <code>{total_votes_received}</code> টি\n"
        f"❤️ <b>অন্যদের পোলে ভোট দিয়েছেন:</b> <code>{u.get('votes_cast', 0)}</code> বার\n"
        f"👥 <b>মোট রেফার:</b> <code>{u.get('referrals', 0)}</code> জন\n"
        f"🕒 <b>টাইমজোন:</b> <code>{u.get('timezone', 'BST')}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🏆 Hall of Fame (টপ ১০ রেকর্ড পোল)", callback_data="show_hof"))
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "show_hof")
def cb_show_hall_of_fame(call):
    all_polls = list(db.get("polls", {}).values())
    if not all_polls:
        bot.answer_callback_query(call.id, "📭 এখনো কোনো পোল রেকর্ড নেই!", show_alert=True)
        return
    ranked = sorted(all_polls, key=lambda p: sum(get_option_total_votes(o) for o in p["options"]), reverse=True)[:10]
    lines = ["🏆 <b>HALL OF FAME — বটের সেরা ১০টি পোল</b> 🏆\n━━━━━━━━━━━━━━━━━━━━"]
    medals = ["🥇", "🥈", "🥉"]
    for idx, p in enumerate(ranked):
        tv = sum(get_option_total_votes(o) for o in p["options"])
        ic = medals[idx] if idx < 3 else f"#{idx+1}"
        lines.append(f"{ic} <b>Poll #{p['id']}</b> ({p['channel_username']}) — <b>{tv} ভোট</b>\n   ❓ {p['question'][:40]}")
    bot.send_message(call.message.chat.id, "\n".join(lines))
    bot.answer_callback_query(call.id)

# Search Poll (#77)
@bot.message_handler(commands=["search"])
@bot.message_handler(func=lambda m: m.text in [TEXTS[l]["btn_search"] for l in TEXTS])
def menu_search_poll(message):
    if not passes_gate(message):
        return
    uid = message.from_user.id
    user_states[uid] = "searching_poll"
    bot.send_message(message.chat.id, "🔍 <b>খুঁজতে চাওয়া পোলের ID (যেমন: <code>102</code>) অথবা প্রশ্ন/চ্যানেলের নাম লিখুন:</b>", reply_markup=cancel_keyboard(uid))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "searching_poll", content_types=["text"])
def process_search_poll(message):
    uid = message.from_user.id
    user_states.pop(uid, None)
    q = message.text.strip().lstrip("#").lower()
    matches = []
    for p in db["polls"].values():
        if q == p["id"].lower() or q in p["question"].lower() or q in p["channel_username"].lower() or q in p["channel_title"].lower():
            matches.append(p)
    if not matches:
        bot.send_message(message.chat.id, "❌ এই নামে বা আইডিতে কোনো পোল খুঁজে পাওয়া যায়নি।", reply_markup=main_menu_keyboard(uid))
        return
    lines = [f"🔍 <b>সার্চ ফলাফল ({len(matches[:10])}টি পাওয়া গেছে):</b>\n"]
    for p in matches[:10]:
        st = "🟢 চালু" if p.get("is_open", True) else "🔴 বন্ধ"
        tv = sum(get_option_total_votes(o) for o in p["options"])
        lines.append(f"🆔 <b>#{p['id']}</b> ({st}) | {p['channel_username']}\n❓ {p['question'][:50]} — <b>{tv} ভোট</b>\n")
    bot.send_message(message.chat.id, "\n".join(lines), reply_markup=main_menu_keyboard(uid))

# Schedule Post (#58)
@bot.message_handler(commands=["schedule"])
@bot.message_handler(func=lambda m: m.text in [TEXTS[l]["btn_schedule"] for l in TEXTS])
def menu_schedule_post(message):
    if not passes_gate(message):
        return
    uid = message.from_user.id
    user_states[uid] = "sched_channel"
    bot.send_message(message.chat.id, "⏰ <b>শিডিউল পোস্ট তৈরি</b>\n\n📢 যে চ্যানেলে পোস্ট শিডিউল করতে চান তার <code>@username</code> বা ID দিন:", reply_markup=cancel_keyboard(uid))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "sched_channel", content_types=["text"])
def step_sched_channel(message):
    uid = message.from_user.id
    target = message.text.strip()
    if "t.me/" in target:
        target = "@" + target.split("t.me/")[-1].strip("/")
    try:
        chat = bot.get_chat(target)
        bm = bot.get_chat_member(chat.id, bot.get_me().id)
        um = bot.get_chat_member(chat.id, uid)
        if bm.status not in ["administrator", "creator"] or (um.status not in ["administrator", "creator"] and uid != ADMIN_ID):
            bot.send_message(message.chat.id, "❌ আপনি ও বট উভয়কেই ওই চ্যানেলে Admin হতে হবে!", reply_markup=cancel_keyboard(uid))
            return
        draft_polls[uid] = {"sched_ch_id": chat.id, "sched_ch_uname": f"@{chat.username}" if chat.username else str(chat.id)}
        user_states[uid] = "sched_content"
        bot.send_message(message.chat.id, "📝 <b>এখন পোস্টের লেখা বা ক্যাপশনসহ ছবি পাঠান:</b>", reply_markup=cancel_keyboard(uid))
    except Exception:
        bot.send_message(message.chat.id, "❌ চ্যানেল খুঁজে পাওয়া যায়নি!", reply_markup=cancel_keyboard(uid))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "sched_content", content_types=["text", "photo"])
def step_sched_content(message):
    uid = message.from_user.id
    if message.content_type == "photo":
        draft_polls[uid]["sched_photo"] = message.photo[-1].file_id
        draft_polls[uid]["sched_text"] = message.caption or ""
    else:
        draft_polls[uid]["sched_photo"] = None
        draft_polls[uid]["sched_text"] = message.text
    user_states[uid] = "sched_minutes"
    bot.send_message(message.chat.id, "⏳ <b>কত মিনিট পর পোস্টটি চ্যানেলে যাবে?</b> সংখ্যা লিখুন (যেমন: <code>30</code> বা <code>60</code>):", reply_markup=cancel_keyboard(uid))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "sched_minutes", content_types=["text"])
def step_sched_minutes(message):
    uid = message.from_user.id
    txt = message.text.strip()
    if not txt.isdigit() or int(txt) < 1 or int(txt) > 10080:
        bot.send_message(message.chat.id, "❌ ১ থেকে ১০০৮০-এর মধ্যে মিনিট সংখ্যা লিখুন:", reply_markup=cancel_keyboard(uid))
        return
    mins = int(txt)
    d = draft_polls.pop(uid)
    user_states.pop(uid, None)
    send_at = time.time() + (mins * 60)
    db["scheduled_posts"].append({
        "id": str(int(time.time())),
        "owner_id": uid,
        "channel_id": d["sched_ch_id"],
        "channel_username": d["sched_ch_uname"],
        "text": d["sched_text"],
        "photo_id": d["sched_photo"],
        "send_at": send_at
    })
    save_db(db, immediate_cloud=True)
    bot.send_message(
        message.chat.id,
        f"✅ পোস্ট শিডিউল সম্পন্ন!\n📢 চ্যানেল: {d['sched_ch_uname']}\n🕒 পোস্ট হবে: <b>{format_user_time(send_at, uid)}</b>",
        reply_markup=main_menu_keyboard(uid)
    )

# Support, Feedback (#67) & Rate Bot (#70)
@bot.message_handler(commands=["suggest", "ratebot"])
@bot.message_handler(func=lambda m: m.text in [TEXTS[l]["btn_support"] for l in TEXTS])
def menu_support_and_rate(message):
    if not passes_gate(message):
        return
    avg_r = round(sum(r["stars"] for r in db.get("ratings", {}).values()) / len(db["ratings"]), 1) if db.get("ratings") else 5.0
    markup = types.InlineKeyboardMarkup(row_width=5)
    markup.add(*[types.InlineKeyboardButton(f"⭐{i}", callback_data=f"ratebot:{i}") for i in range(1, 6)])
    markup.add(types.InlineKeyboardButton("💡 আইডিয়া / ফিডব্যাক পাঠান", callback_data="send_suggestion"))
    bot.send_message(
        message.chat.id,
        f"📞 <b>সাপোর্ট, ফিডব্যাক ও রেটিং ডেস্ক</b>\n\n"
        f"👤 <b>Admin:</b> {ADMIN_USERNAME}\n"
        f"📢 <b>Channel:</b> @bdgiveaways24 | 💬 <b>Group:</b> @bdgivewaychat\n"
        f"⭐ <b>বটের বর্তমান গড় রেটিং:</b> <code>{avg_r}/5.0</code> ({len(db.get('ratings', {}))} জন)\n\n"
        f"👇 নিচের স্টারে চাপ দিয়ে বটকে রেটিং দিন অথবা আইডিয়া পাঠান:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("ratebot:"))
def cb_rate_bot(call):
    stars = int(call.data.split(":")[1])
    uid = str(call.from_user.id)
    db["ratings"][uid] = {"stars": stars, "name": call.from_user.first_name, "time": time.strftime("%Y-%m-%d")}
    save_db(db, immediate_cloud=True)
    bot.answer_callback_query(call.id, f"❤️ ধন্যবাদ! আপনি বটকে {stars} স্টার রেটিং দিয়েছেন!", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data == "send_suggestion")
def cb_send_suggestion(call):
    uid = call.from_user.id
    user_states[uid] = "writing_suggestion"
    bot.send_message(call.message.chat.id, "💡 <b>বটের জন্য আপনার নতুন আইডিয়া বা সমস্যার কথা লিখে পাঠান (সরাসরি অ্যাডমিনের কাছে যাবে):</b>", reply_markup=cancel_keyboard(uid))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "writing_suggestion", content_types=["text"])
def process_user_suggestion(message):
    uid = message.from_user.id
    user_states.pop(uid, None)
    sug_id = str(len(db["suggestions"]) + 1)
    db["suggestions"].append({
        "id": sug_id,
        "user_id": uid,
        "name": message.from_user.first_name,
        "text": message.text.strip(),
        "time": time.strftime("%Y-%m-%d %H:%M")
    })
    save_db(db, immediate_cloud=True)
    bot.send_message(message.chat.id, "✅ আপনার ফিডব্যাক অ্যাডমিনের ইনবক্সে পাঠানো হয়েছে! ধন্যবাদ।", reply_markup=main_menu_keyboard(uid))
    try:
        bot.send_message(ADMIN_ID, f"💡 <b>নতুন ফিডব্যাক (#{sug_id})</b>\n👤 {message.from_user.first_name} (<code>{uid}</code>):\n\n{message.text}")
    except Exception:
        pass

# ================= POLL CREATION WIZARD (WITH GOAL #86, BAR STYLE #83, AUTO-DELETE #78) =================
@bot.message_handler(func=lambda m: m.text in [TEXTS[l]["btn_create"] for l in TEXTS])
def menu_create_poll(message):
    if not passes_gate(message):
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(t(message.from_user.id, "create_now_btn"), callback_data="start_poll_wizard"))
    bot.send_message(message.chat.id, t(message.from_user.id, "create_prompt_inline"), reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "start_poll_wizard")
def cb_start_wizard(call):
    if not check_all_joined(call.from_user.id) or not is_unlocked(call.from_user.id):
        return
    uid = call.from_user.id
    user_states[uid] = "step_channel"
    draft_polls[uid] = {"timer_hours": 0, "target_votes": 0, "bar_style": "classic", "auto_delete_24h": False}
    bot.send_message(call.message.chat.id, t(uid, "ask_channel"), reply_markup=cancel_keyboard(uid))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "step_channel", content_types=["text"])
def wizard_step_channel(message):
    uid = message.from_user.id
    draft_polls.setdefault(uid, {"timer_hours": 0, "target_votes": 0, "bar_style": "classic", "auto_delete_24h": False})
    target = message.text.strip()
    if "t.me/" in target:
        target = "@" + target.split("t.me/")[-1].strip("/")

    try:
        chat = bot.get_chat(target)
        bm = bot.get_chat_member(chat.id, bot.get_me().id)
        if bm.status not in ["administrator", "creator"]:
            bot.send_message(message.chat.id, t(uid, "not_bot_admin"), reply_markup=cancel_keyboard(uid))
            return
        um = bot.get_chat_member(chat.id, uid)
        if um.status not in ["administrator", "creator"] and uid != ADMIN_ID:
            bot.send_message(message.chat.id, t(uid, "not_user_admin"), reply_markup=cancel_keyboard(uid))
            return

        draft_polls[uid]["channel_id"] = chat.id
        draft_polls[uid]["channel_username"] = f"@{chat.username}" if chat.username else str(chat.id)
        draft_polls[uid]["channel_title"] = chat.title or target
        draft_polls[uid]["user_role"] = um.status
        user_states[uid] = "step_question"
        bot.send_message(message.chat.id, f"✅ <b>ভেরিফাই সফল!</b> ({chat.title or target})\n\n" + t(uid, "ask_question"), reply_markup=cancel_keyboard(uid))
    except Exception:
        bot.send_message(message.chat.id, t(uid, "not_bot_admin"), reply_markup=cancel_keyboard(uid))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "step_question", content_types=["text"])
def wizard_step_question(message):
    uid = message.from_user.id
    if uid not in draft_polls:
        return
    q_text = message.text.strip()
    draft_polls[uid]["question"] = q_text
    user_states[uid] = "step_question_confirm"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(t(uid, "btn_q_ok"), callback_data="q_confirm:ok"),
        types.InlineKeyboardButton(t(uid, "btn_q_rewrite"), callback_data="q_confirm:rewrite")
    )
    bot.send_message(message.chat.id, t(uid, "question_preview").format(question=q_text), reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("q_confirm:"))
def cb_question_confirm(call):
    uid = call.from_user.id
    if uid not in draft_polls:
        return
    if call.data.split(":")[1] == "rewrite":
        user_states[uid] = "step_question"
        bot.send_message(call.message.chat.id, t(uid, "ask_question"), reply_markup=cancel_keyboard(uid))
    else:
        user_states[uid] = "step_photo"
        bot.send_message(call.message.chat.id, t(uid, "ask_photo"), reply_markup=cancel_keyboard(uid, include_text_only=True))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "step_photo", content_types=["text", "photo"])
def wizard_step_photo(message):
    uid = message.from_user.id
    if uid not in draft_polls:
        return
    if message.content_type == "photo":
        draft_polls[uid]["photo_id"] = message.photo[-1].file_id
    elif message.text in [TEXTS[l]["btn_text_only"] for l in TEXTS]:
        draft_polls[uid]["photo_id"] = None
    else:
        bot.send_message(message.chat.id, t(uid, "ask_photo"), reply_markup=cancel_keyboard(uid, include_text_only=True))
        return
    user_states[uid] = "step_options"
    bot.send_message(message.chat.id, t(uid, "ask_options"), reply_markup=cancel_keyboard(uid))

def build_draft_preview(uid):
    d = draft_polls[uid]
    cands_list = "\n".join([f"👤 {idx+1}. {name}" for idx, name in enumerate(d["options"])])
    hrs = d.get("timer_hours", 0)
    goal = d.get("target_votes", 0)
    bs = d.get("bar_style", "classic")
    adel = "হ্যাঁ ✅" if d.get("auto_delete_24h") else "না"

    text = (
        f"📊 <b>পোলের ফাইনাল প্রিভিউ:</b>\n\n"
        f"📣 <b>চ্যানেল:</b> {d['channel_title']} ({d['channel_username']})\n"
        f"❓ <b>প্রশ্ন:</b> {d['question']}\n"
        f"⏳ <b>টাইমার:</b> {f'{hrs}h' if hrs else 'Manual'} | 🎯 <b>ভোট গোল:</b> {f'{goal} ভোট' if goal else 'Off'}\n"
        f"🎛️ <b>বার স্টাইল:</b> {BAR_STYLES[bs][0]*4}{BAR_STYLES[bs][1]*2} | 🗑 <b>বন্ধের ২৪h পর অটো-ডিলিট:</b> {adel}\n\n"
        f"📝 <b>প্রার্থীসমূহ:</b>\n{cands_list}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("⏳ 1h", callback_data="settimer:1"),
        types.InlineKeyboardButton("⏳ 12h", callback_data="settimer:12"),
        types.InlineKeyboardButton("⏳ 24h", callback_data="settimer:24")
    )
    markup.add(
        types.InlineKeyboardButton("🎯 Goal: 50", callback_data="setgoal:50"),
        types.InlineKeyboardButton("🎯 Goal: 200", callback_data="setgoal:200"),
        types.InlineKeyboardButton("🎯 Goal: Off", callback_data="setgoal:0")
    )
    markup.add(
        types.InlineKeyboardButton("▓ Classic", callback_data="setbar:classic"),
        types.InlineKeyboardButton("🟩 Green", callback_data="setbar:green"),
        types.InlineKeyboardButton("🔵 Blue", callback_data="setbar:blue"),
        types.InlineKeyboardButton("🔥 Fire", callback_data="setbar:fire")
    )
    markup.add(types.InlineKeyboardButton(f"🗑 Auto-Delete 24h: {'ON' if d.get('auto_delete_24h') else 'OFF'}", callback_data="toggle_adel"))
    markup.add(types.InlineKeyboardButton("🚀 Send to Channel", callback_data="publish_poll_now"))
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_draft"))
    return text, markup

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "step_options", content_types=["text"])
def wizard_step_options(message):
    uid = message.from_user.id
    if uid not in draft_polls:
        return
    raw_names = [name.strip() for name in message.text.split("&") if name.strip()]
    if not raw_names or len(raw_names) > 30:
        bot.send_message(message.chat.id, t(uid, "invalid_options"), reply_markup=cancel_keyboard(uid))
        return
    draft_polls[uid]["options"] = raw_names
    user_states[uid] = "step_final_preview"
    text, markup = build_draft_preview(uid)
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith(("settimer:", "setgoal:", "setbar:")) or c.data == "toggle_adel")
def cb_draft_options_toggles(call):
    uid = call.from_user.id
    if uid not in draft_polls:
        return
    if call.data.startswith("settimer:"):
        draft_polls[uid]["timer_hours"] = int(call.data.split(":")[1])
    elif call.data.startswith("setgoal:"):
        draft_polls[uid]["target_votes"] = int(call.data.split(":")[1])
    elif call.data.startswith("setbar:"):
        draft_polls[uid]["bar_style"] = call.data.split(":")[1]
    elif call.data == "toggle_adel":
        draft_polls[uid]["auto_delete_24h"] = not draft_polls[uid].get("auto_delete_24h", False)

    text, markup = build_draft_preview(uid)
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        pass
    bot.answer_callback_query(call.id, "Updated!")

@bot.callback_query_handler(func=lambda c: c.data == "cancel_draft")
def cb_cancel_draft(call):
    uid = call.from_user.id
    user_states.pop(uid, None)
    draft_polls.pop(uid, None)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    bot.send_message(call.message.chat.id, t(uid, "cancelled"), reply_markup=main_menu_keyboard(uid))

# ================= PUBLISH POLL TO CHANNEL =================
@bot.callback_query_handler(func=lambda c: c.data == "publish_poll_now")
def cb_publish_poll(call):
    uid = call.from_user.id
    d = draft_polls.pop(uid, None)
    user_states.pop(uid, None)
    if not d:
        return

    db["poll_counter"] += 1
    pid = str(db["poll_counter"])
    hrs = d.get("timer_hours", 0)
    close_at = (time.time() + hrs * 3600) if hrs > 0 else None

    creator_uname = f"@{call.from_user.username}" if call.from_user.username else "No Username"
    options_data = [{"name": name, "voters": [], "bonus_votes": 0} for name in d["options"]]
    db["polls"][pid] = {
        "id": pid,
        "owner_id": uid,
        "owner_name": call.from_user.first_name,
        "owner_username": creator_uname,
        "co_hosts": [],
        "channel_id": d["channel_id"],
        "channel_username": d["channel_username"],
        "channel_title": d["channel_title"],
        "question": d["question"],
        "photo_id": d.get("photo_id"),
        "options": options_data,
        "hourly_votes": {},
        "milestones_sent": [],
        "target_votes": d.get("target_votes", 0),
        "bar_style": d.get("bar_style", "classic"),
        "auto_delete_24h": d.get("auto_delete_24h", False),
        "delete_at": None,
        "message_id": None,
        "close_at": close_at,
        "is_open": True,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    caption = build_channel_poll_caption(pid)
    markup = build_channel_poll_markup(pid)
    try:
        if d.get("photo_id"):
            sent_msg = bot.send_photo(d["channel_id"], d["photo_id"], caption=caption, reply_markup=markup)
        else:
            sent_msg = bot.send_message(d["channel_id"], caption, reply_markup=markup)
        db["polls"][pid]["message_id"] = sent_msg.message_id
        save_db(db, immediate_cloud=True)
    except Exception as e:
        del db["polls"][pid]
        save_db(db)
        bot.send_message(call.message.chat.id, f"❌ চ্যানেলে পাঠাতে সমস্যা হয়েছে: {e}", reply_markup=main_menu_keyboard(uid))
        return

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    direct_links_list = "\n".join([
        f"🔥 <b>{o['name']}:</b> <code>https://t.me/{BOT_USERNAME}?start=v_{pid}_{idx}</code>"
        for idx, o in enumerate(options_data)
    ])
    bot.send_message(
        call.message.chat.id,
        f"{t(uid, 'poll_sent')}\n\n🔗 <b>ডিরেক্ট ভোট লিংকসমূহ:</b>\n{direct_links_list}",
        reply_markup=main_menu_keyboard(uid)
    )
    send_log_to_channel(
        f"🆕 <b>নতুন পোল তৈরি হয়েছে! (Poll #{pid})</b>\n"
        f"👤 ক্রিয়েটর: {call.from_user.first_name} ({creator_uname} | <code>{uid}</code>)\n"
        f"📢 চ্যানেল: {d['channel_title']} ({d['channel_username']})\n"
        f"❓ প্রশ্ন: {d['question']}"
    )

# ================= LIVE VOTING, MILESTONES (#63), TARGET GOAL (#86), WITHDRAW & CLOSE =================
def process_vote_action(call, pid, opt_idx, from_direct=False):
    voter = call.from_user
    vid = voter.id
    register_user(voter)

    poll = db["polls"].get(pid)
    if not poll:
        bot.answer_callback_query(call.id, "⚠️ পোলটি খুঁজে পাওয়া যায়নি!", show_alert=True)
        return
    if not poll.get("is_open", True):
        bot.answer_callback_query(call.id, "🛑 পোলটি বন্ধ হয়ে গেছে!", show_alert=True)
        return
    if opt_idx < 0 or opt_idx >= len(poll["options"]):
        bot.answer_callback_query(call.id, "❌ এই প্রার্থীটি আর তালিকায় নেই!", show_alert=True)
        return

    try:
        ch_member = bot.get_chat_member(poll["channel_id"], vid)
        if ch_member.status in ["left", "kicked"]:
            bot.answer_callback_query(call.id, "⚠️ ভোট দিতে আগে এই চ্যানেলে জয়েন করুন! (চ্যানেল ছাড়লে ভোট বাতিল হবে)", show_alert=True)
            return
    except Exception:
        pass

    for o in poll["options"]:
        if vid in o["voters"]:
            bot.answer_callback_query(call.id, "⚠️ আপনি ইতোমধ্যে ভোট দিয়েছেন! পরিবর্তন করতে 'ভোট প্রত্যাহার' চাপুন।", show_alert=True)
            return

    poll["options"][opt_idx]["voters"].append(vid)
    if not from_direct:
        poll["message_id"] = call.message.message_id

    hour_key = datetime.now().strftime("%I %p")
    poll.setdefault("hourly_votes", {})
    poll["hourly_votes"][hour_key] = poll["hourly_votes"].get(hour_key, 0) + 1
    db["users"][str(vid)]["votes_cast"] = db["users"][str(vid)].get("votes_cast", 0) + 1

    save_db(db)

    chosen_name = poll["options"][opt_idx]["name"]
    cand_total = get_option_total_votes(poll["options"][opt_idx])
    poll_total = sum(get_option_total_votes(o) for o in poll["options"])
    bot.answer_callback_query(call.id, f"✅ আপনার ভোট '{chosen_name}'-কে যুক্ত হয়েছে!", show_alert=True)

    refresh_channel_poll_message(pid)

    # Creator Milestone Alert (#63)
    poll.setdefault("milestones_sent", [])
    for m_target in db.get("milestone_targets", [100, 500, 1000]):
        if poll_total >= m_target and m_target not in poll["milestones_sent"]:
            poll["milestones_sent"].append(m_target)
            save_db(db)
            try:
                bot.send_message(poll["owner_id"], f"🎉 <b>মাইলস্টোন অ্যালার্ট!</b> আপনার পোল <b>#{pid}</b> ({poll['channel_username']}) সফলভাবে <b>{m_target} ভোট</b> পূর্ণ করেছে!")
            except Exception:
                pass

    # Target Goal Auto-Winner (#86)
    t_goal = int(poll.get("target_votes", 0))
    if t_goal > 0 and cand_total >= t_goal:
        announce_poll_winner(pid, close_reason=f"🎯 টার্গেট গোল ({t_goal} ভোট) পূর্ণ হওয়ায় অটো সমাপ্ত!")
        return

    uname = f"@{voter.username}" if voter.username else "No Username"
    try:
        bot.send_message(
            poll["owner_id"],
            f"👷 <b>ভোট দিয়েছেন:</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>নাম :</b> {voter.first_name}\n🔰 <b>ইউজারনেম :</b> {uname}\n"
            f"🆔 <b>আইডি :</b> <code>{vid}</code>\n📌 <b>প্রার্থী :</b> {chosen_name} (মোট: {cand_total})"
        )
    except Exception:
        pass

    breakdown = "\n".join([f"   • {o['name']}: <b>{get_option_total_votes(o)}</b> ভোট" for o in poll["options"]])
    send_log_to_channel(
        f"📊 <b>লাইভ ভোট আপডেট (Poll #{pid})</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📢 <b>চ্যানেল:</b> {poll['channel_title']} ({poll['channel_username']})\n"
        f"🙋‍♂️ <b>ভোটার:</b> {voter.first_name} ({uname} | <code>{vid}</code>) ➡️ <b>{chosen_name}</b>\n"
        f"📈 <b>বর্তমান হিসাব (মোট {poll_total} ভোট):</b>\n{breakdown}"
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("pclosed:"))
def cb_poll_closed(call):
    bot.answer_callback_query(call.id, "🛑 এই পোলটি বন্ধ হয়ে গেছে!", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pvote:"))
def cb_cast_poll_vote(call):
    parts = call.data.split(":")
    process_vote_action(call, parts[1], int(parts[2]), from_direct=False)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pwithdraw:"))
def cb_withdraw_vote(call):
    pid = call.data.split(":")[1]
    vid = call.from_user.id
    poll = db["polls"].get(pid)
    if not poll or not poll.get("is_open", True):
        bot.answer_callback_query(call.id, "🛑 পোলটি বন্ধ হয়ে গেছে!", show_alert=True)
        return
    removed_from = None
    for o in poll["options"]:
        if vid in o["voters"]:
            o["voters"].remove(vid)
            removed_from = o["name"]
            break
    if not removed_from:
        bot.answer_callback_query(call.id, "⚠️ আপনি এখনো ভোট দেননি!", show_alert=True)
        return
    save_db(db)
    bot.answer_callback_query(call.id, f"🔄 '{removed_from}' থেকে ভোট প্রত্যাহার করা হয়েছে!", show_alert=True)
    refresh_channel_poll_message(pid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pclose:"))
def cb_close_poll_from_channel(call):
    pid = call.data.split(":")[1]
    poll = db["polls"].get(pid)
    if not poll or not can_manage_poll(poll, call.from_user.id):
        bot.answer_callback_query(call.id, "🚫 শুধুমাত্র পোল ক্রিয়েটর, Co-Host বা অ্যাডমিন বন্ধ করতে পারবেন!", show_alert=True)
        return
    poll["is_open"] = False
    poll["close_at"] = None
    if poll.get("auto_delete_24h"):
        poll["delete_at"] = time.time() + 86400
    save_db(db, immediate_cloud=True)
    bot.answer_callback_query(call.id, "🛑 পোলটি বন্ধ করা হয়েছে!", show_alert=True)
    refresh_channel_poll_message(pid)

# ================= FULL EDIT POLLS (WITH CLONE #89 & CO-HOST #64) =================
@bot.message_handler(func=lambda m: m.text in [TEXTS[l]["btn_edit"] for l in TEXTS])
def menu_edit_polls(message):
    if not passes_gate(message):
        return
    uid = message.from_user.id
    my_polls = [p for p in db["polls"].values() if can_manage_poll(p, uid)]
    if not my_polls:
        bot.send_message(message.chat.id, "📭 আপনি এখনো কোনো পোল তৈরি করেননি।")
        return

    lines = ["✏️ <b>আপনার নিয়ন্ত্রণাধীন পোলসমূহ:</b>\n"]
    markup = types.InlineKeyboardMarkup(row_width=2)
    for p in my_polls[-8:]:
        st = "🟢 চালু" if p.get("is_open", True) else "🔴 বন্ধ"
        tv = sum(get_option_total_votes(o) for o in p["options"])
        lines.append(f"🆔 <b>#{p['id']}</b> ({st}) — {p['channel_username']} | মোট ভোট: <b>{tv}</b>")
        btn_txt = f"🛑 বন্ধ #{p['id']}" if p.get("is_open", True) else f"🟢 চালু #{p['id']}"
        markup.add(
            types.InlineKeyboardButton(f"➕ নাম যোগ #{p['id']}", callback_data=f"editadd:{p['id']}"),
            types.InlineKeyboardButton(f"➖ নাম বাদ #{p['id']}", callback_data=f"editrem:{p['id']}")
        )
        markup.add(
            types.InlineKeyboardButton(f"📈 ভোট গ্রাফ #{p['id']}", callback_data=f"editgraph:{p['id']}"),
            types.InlineKeyboardButton(f"🏆 উইনার #{p['id']}", callback_data=f"editwin:{p['id']}")
        )
        markup.add(
            types.InlineKeyboardButton(f"♻️ Clone #{p['id']}", callback_data=f"editclone:{p['id']}"),
            types.InlineKeyboardButton(f"🤝 Co-Host #{p['id']}", callback_data=f"editcohost:{p['id']}")
        )
        markup.add(
            types.InlineKeyboardButton(f"📝 প্রশ্ন #{p['id']}", callback_data=f"editq:{p['id']}"),
            types.InlineKeyboardButton(btn_txt, callback_data=f"edittoggle:{p['id']}")
        )
        markup.add(types.InlineKeyboardButton(f"🗑 ডিলিট #{p['id']}", callback_data=f"editdel:{p['id']}"))
    bot.send_message(message.chat.id, "\n".join(lines), reply_markup=markup)

# One-Click Poll Clone (#89)
@bot.callback_query_handler(func=lambda c: c.data.startswith("editclone:"))
def cb_clone_poll(call):
    pid = call.data.split(":")[1]
    old_p = db["polls"].get(pid)
    if not old_p or not can_manage_poll(old_p, call.from_user.id):
        return
    uid = call.from_user.id
    draft_polls[uid] = {
        "channel_id": old_p["channel_id"],
        "channel_username": old_p["channel_username"],
        "channel_title": old_p["channel_title"],
        "user_role": "Admin",
        "question": old_p["question"],
        "photo_id": old_p.get("photo_id"),
        "options": [o["name"] for o in old_p["options"]],
        "timer_hours": 0,
        "target_votes": old_p.get("target_votes", 0),
        "bar_style": old_p.get("bar_style", "classic"),
        "auto_delete_24h": old_p.get("auto_delete_24h", False)
    }
    user_states[uid] = "step_final_preview"
    text, markup = build_draft_preview(uid)
    bot.send_message(call.message.chat.id, "♻️ <b>পোল ক্লোন রেডি! নিচে দেখে চ্যানেলে পাঠিয়ে দিন:</b>\n\n" + text, reply_markup=markup)
    bot.answer_callback_query(call.id)

# Add Co-Host (#64)
@bot.callback_query_handler(func=lambda c: c.data.startswith("editcohost:"))
def cb_add_cohost_prompt(call):
    pid = call.data.split(":")[1]
    poll = db["polls"].get(pid)
    if not poll or (call.from_user.id != int(poll["owner_id"]) and call.from_user.id != ADMIN_ID):
        bot.answer_callback_query(call.id, "🚫 শুধুমাত্র মূল ক্রিয়েটর Co-Host যুক্ত করতে পারবেন!", show_alert=True)
        return
    uid = call.from_user.id
    user_states[uid] = f"adding_cohost:{pid}"
    cur = ", ".join(str(x) for x in poll.get("co_hosts", [])) or "কেউ নেই"
    bot.send_message(call.message.chat.id, f"🤝 <b>পোল #{pid}-এ Co-Host যুক্ত করুন</b>\nবর্তমান Co-Host: <code>{cur}</code>\n\nনতুন যাকে অ্যাড করতে চান তার <b>User ID</b> লিখুন:", reply_markup=cancel_keyboard(uid))

@bot.message_handler(func=lambda m: str(user_states.get(m.from_user.id, "")).startswith("adding_cohost:"), content_types=["text"])
def process_add_cohost(message):
    uid = message.from_user.id
    pid = user_states.pop(uid).split(":")[1]
    poll = db["polls"].get(pid)
    txt = message.text.strip()
    if not poll or not txt.isdigit():
        bot.send_message(message.chat.id, "❌ সঠিক User ID দিন!", reply_markup=main_menu_keyboard(uid))
        return
    cid = int(txt)
    poll.setdefault("co_hosts", [])
    if cid not in poll["co_hosts"]:
        poll["co_hosts"].append(cid)
        save_db(db, immediate_cloud=True)
    bot.send_message(message.chat.id, f"✅ User ID <code>{cid}</code>-কে পোল <b>#{pid}</b>-এর Co-Host হিসেবে যুক্ত করা হয়েছে!", reply_markup=main_menu_keyboard(uid))

@bot.callback_query_handler(func=lambda c: c.data.startswith("editgraph:"))
def cb_edit_graph(call):
    pid = call.data.split(":")[1]
    poll = db["polls"].get(pid)
    if not poll or not can_manage_poll(poll, call.from_user.id):
        return
    bot.send_message(call.message.chat.id, build_hourly_graph_report(pid))
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("editadd:"))
def cb_edit_add_candidate(call):
    pid = call.data.split(":")[1]
    poll = db["polls"].get(pid)
    if not poll or not can_manage_poll(poll, call.from_user.id):
        return
    uid = call.from_user.id
    user_states[uid] = f"adding_cand:{pid}"
    bot.send_message(call.message.chat.id, f"➕ <b>পোল #{pid}-এ নতুন প্রার্থীর নাম লিখুন</b> (একাধিক হলে <code>&amp;</code> দিন):", reply_markup=cancel_keyboard(uid))

@bot.message_handler(func=lambda m: str(user_states.get(m.from_user.id, "")).startswith("adding_cand:"), content_types=["text"])
def process_add_candidate(message):
    uid = message.from_user.id
    pid = user_states.pop(uid).split(":")[1]
    poll = db["polls"].get(pid)
    if not poll:
        return
    new_names = [n.strip() for n in message.text.split("&") if n.strip()]
    if not new_names or len(poll["options"]) + len(new_names) > 30:
        bot.send_message(message.chat.id, "❌ সঠিক নাম দিন (সর্বোচ্চ ৩০ জন)!", reply_markup=main_menu_keyboard(uid))
        return
    for name in new_names:
        poll["options"].append({"name": name, "voters": [], "bonus_votes": 0})
    save_db(db, immediate_cloud=True)
    refresh_channel_poll_message(pid)
    bot.send_message(message.chat.id, f"✅ পোল <b>#{pid}</b>-এ নতুন নাম যুক্ত হয়েছে!", reply_markup=main_menu_keyboard(uid))

@bot.callback_query_handler(func=lambda c: c.data.startswith("editrem:"))
def cb_edit_remove_menu(call):
    pid = call.data.split(":")[1]
    poll = db["polls"].get(pid)
    if not poll or not can_manage_poll(poll, call.from_user.id) or len(poll["options"]) <= 1:
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for idx, o in enumerate(poll["options"]):
        markup.add(types.InlineKeyboardButton(f"❌ বাদ দিন: {o['name']}", callback_data=f"remopt:{pid}:{idx}"))
    bot.send_message(call.message.chat.id, f"➖ <b>পোল #{pid} থেকে কাকে বাদ দেবেন সিলেক্ট করুন:</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("remopt:"))
def cb_confirm_remove_opt(call):
    parts = call.data.split(":")
    pid, idx = parts[1], int(parts[2])
    poll = db["polls"].get(pid)
    if not poll or not can_manage_poll(poll, call.from_user.id) or len(poll["options"]) <= 1 or idx >= len(poll["options"]):
        return
    removed = poll["options"].pop(idx)
    save_db(db, immediate_cloud=True)
    refresh_channel_poll_message(pid)
    bot.answer_callback_query(call.id, f"🗑 '{removed['name']}'-কে বাদ দেওয়া হয়েছে!", show_alert=True)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("editq:"))
def cb_edit_question(call):
    pid = call.data.split(":")[1]
    poll = db["polls"].get(pid)
    if not poll or not can_manage_poll(poll, call.from_user.id):
        return
    uid = call.from_user.id
    user_states[uid] = f"editing_q:{pid}"
    bot.send_message(call.message.chat.id, f"📝 <b>পোল #{pid}-এর নতুন প্রশ্ন লিখুন:</b>", reply_markup=cancel_keyboard(uid))

@bot.message_handler(func=lambda m: str(user_states.get(m.from_user.id, "")).startswith("editing_q:"), content_types=["text"])
def process_edit_question(message):
    uid = message.from_user.id
    pid = user_states.pop(uid).split(":")[1]
    poll = db["polls"].get(pid)
    if not poll:
        return
    poll["question"] = message.text.strip()
    save_db(db, immediate_cloud=True)
    refresh_channel_poll_message(pid)
    bot.send_message(message.chat.id, f"✅ পোল <b>#{pid}</b>-এর প্রশ্ন আপডেট হয়েছে!", reply_markup=main_menu_keyboard(uid))

@bot.callback_query_handler(func=lambda c: c.data.startswith("editwin:"))
def cb_edit_winner(call):
    pid = call.data.split(":")[1]
    poll = db["polls"].get(pid)
    if not poll or not can_manage_poll(poll, call.from_user.id):
        return
    announce_poll_winner(pid)
    bot.answer_callback_query(call.id, "🏆 উইনার রেজাল্ট চ্যানেলে পোস্ট হয়েছে!", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("edittoggle:"))
def cb_edit_toggle(call):
    pid = call.data.split(":")[1]
    poll = db["polls"].get(pid)
    if not poll or not can_manage_poll(poll, call.from_user.id):
        return
    poll["is_open"] = not poll.get("is_open", True)
    save_db(db, immediate_cloud=True)
    refresh_channel_poll_message(pid)
    bot.answer_callback_query(call.id, f"পোল #{pid} স্ট্যাটাস আপডেট হয়েছে!", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("editdel:"))
def cb_edit_delete(call):
    pid = call.data.split(":")[1]
    poll = db["polls"].get(pid)
    if not poll or not can_manage_poll(poll, call.from_user.id):
        return
    del db["polls"][pid]
    save_db(db, immediate_cloud=True)
    bot.answer_callback_query(call.id, f"🗑 পোল #{pid} মুছে ফেলা হয়েছে!", show_alert=True)

# ================= RECOVER OLD POLL & SECRET ADMIN VOTE BOOST (+ / -) =================
@bot.message_handler(commands=["recoverpoll"])
def cmd_recover_old_poll(message):
    if message.from_user.id != ADMIN_ID:
        return
    raw = message.text.replace("/recoverpoll", "", 1).strip()
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) != 5 or not parts[2].isdigit():
        bot.reply_to(message, "♻️ ফরম্যাট: <code>/recoverpoll @channel | 102 | 381 | প্রশ্ন | নাম১:23&amp;নাম২:5</code>")
        return
    ch_target, pid, msg_id_str, q_text, cands_raw = parts
    try:
        chat = bot.get_chat(ch_target)
        options_data = []
        for item in cands_raw.split("&"):
            if ":" in item:
                cname, vnum = item.rsplit(":", 1)
                options_data.append({"name": cname.strip(), "voters": [], "bonus_votes": int(vnum.strip())})
            else:
                options_data.append({"name": item.strip(), "voters": [], "bonus_votes": 0})
        db["polls"][pid] = {
            "id": pid, "owner_id": ADMIN_ID, "owner_name": "Rafim", "owner_username": ADMIN_USERNAME,
            "co_hosts": [], "channel_id": chat.id,
            "channel_username": f"@{chat.username}" if chat.username else str(chat.id),
            "channel_title": chat.title or ch_target, "question": q_text, "photo_id": None,
            "options": options_data, "hourly_votes": {}, "milestones_sent": [],
            "target_votes": 0, "bar_style": "classic", "auto_delete_24h": False, "delete_at": None,
            "message_id": int(msg_id_str), "close_at": None, "is_open": True,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        if pid.isdigit() and int(pid) >= db["poll_counter"]:
            db["poll_counter"] = int(pid) + 1
        save_db(db, immediate_cloud=True)
        refresh_channel_poll_message(pid)
        bot.reply_to(message, f"✅ পোল <b>#{pid}</b> ({chat.title}) আগের সব ভোটসহ সচল হয়েছে!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

def apply_admin_vote_adjustment(pid, opt_idx, amount):
    poll = db["polls"].get(pid)
    if not poll or opt_idx < 0 or opt_idx >= len(poll["options"]):
        return False, "❌ পোল বা প্রার্থী পাওয়া যায়নি।"
    opt = poll["options"][opt_idx]
    amount = int(amount)
    if amount >= 0:
        opt["bonus_votes"] = int(opt.get("bonus_votes", 0)) + amount
        action_word = f"<b>+{amount}</b> ভোট যুক্ত হয়েছে"
    else:
        to_cut = abs(amount)
        if to_cut >= get_option_total_votes(opt):
            opt["bonus_votes"] = 0
            opt["voters"] = []
        else:
            opt["bonus_votes"] = int(opt.get("bonus_votes", 0)) - to_cut
        action_word = f"<b>-{to_cut}</b> ভোট কাটা হয়েছে"
    save_db(db, immediate_cloud=True)
    refresh_channel_poll_message(pid)
    return True, f"✅ Poll <b>#{pid}</b> এর <b>{opt['name']}</b> থেকে {action_word}! (মোট: <b>{get_option_total_votes(opt)}</b>)"

@bot.message_handler(commands=["addvote", "cutvote"])
def cmd_admin_vote_adjust(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) != 4 or not parts[2].isdigit() or not parts[3].lstrip("-").isdigit():
        bot.reply_to(message, "ব্যবহার: <code>/addvote 102 1 50</code> অথবা <code>/cutvote 102 1 20</code>")
        return
    pid = parts[1].lstrip("#")
    opt_idx = int(parts[2]) - 1
    amt = int(parts[3])
    if message.text.startswith("/cutvote"):
        amt = -abs(amt)
    ok, msg = apply_admin_vote_adjustment(pid, opt_idx, amt)
    bot.reply_to(message, msg)

# ================= ULTIMATE 15-FEATURE ADMIN CONTROL PANEL =================
@bot.message_handler(commands=["admin"])
@bot.message_handler(func=lambda m: m.text in [TEXTS[l]["btn_admin"] for l in TEXTS] and m.from_user.id == ADMIN_ID)
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    maint_lbl = "🛠️ Maint: ON" if db.get("maintenance_mode") else "🟢 Maint: OFF"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⚡ Boost Votes (+)", callback_data="adm:boost"),
        types.InlineKeyboardButton("✂️ Cut Votes (-)", callback_data="adm:cut"),
        types.InlineKeyboardButton("📢 Global Notice (#1)", callback_data="adm:notice"),
        types.InlineKeyboardButton("📬 Feedback Inbox (#2)", callback_data="adm:feedback"),
        types.InlineKeyboardButton("⭐ Bot Ratings (#3)", callback_data="adm:ratings"),
        types.InlineKeyboardButton("🚫 Ban / Unban (#4)", callback_data="adm:ban_menu"),
        types.InlineKeyboardButton("🔍 Super Poll Ctrl (#5)", callback_data="adm:polls"),
        types.InlineKeyboardButton("⏰ Sched Monitor (#6)", callback_data="adm:scheds"),
        types.InlineKeyboardButton("🏷️ Reset VIP Footer (#7)", callback_data="adm:vip_footer"),
        types.InlineKeyboardButton("📊 Daily Summary (#8)", callback_data="adm:daily_rep"),
        types.InlineKeyboardButton("🔗 Force-Join Mgr (#9)", callback_data="adm:fj_mgr"),
        types.InlineKeyboardButton("🎯 Milestones (#10)", callback_data="adm:milestones"),
        types.InlineKeyboardButton("🧹 Cleanup Dead (#11)", callback_data="adm:cleanup"),
        types.InlineKeyboardButton("✉️ Direct User DM (#12)", callback_data="adm:dm"),
        types.InlineKeyboardButton("🔄 Cloud Restore (#13)", callback_data="adm:restore"),
        types.InlineKeyboardButton("🏆 Reset HoF (#14)", callback_data="adm:hof_info"),
        types.InlineKeyboardButton(f"{maint_lbl} (#15)", callback_data="adm:maint"),
        types.InlineKeyboardButton("💾 Force Backup", callback_data="adm:backup"),
        types.InlineKeyboardButton("🔓 Give VIP", callback_data="adm:add_vip"),
        types.InlineKeyboardButton("🔒 Remove VIP", callback_data="adm:rem_vip"),
        types.InlineKeyboardButton("📢 Broadcast All", callback_data="adm:broadcast")
    )
    bot.send_message(message.chat.id, "👑 <b>Rafim Ultimate Admin Control Panel (All 15 Tools Active)</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm:") and c.from_user.id == ADMIN_ID)
def cb_admin(call):
    act = call.data.split(":")[1]

    if act in ["boost", "cut"]:
        if not db["polls"]:
            bot.send_message(ADMIN_ID, "কোনো পোল নেই।")
            return
        markup = types.InlineKeyboardMarkup(row_width=1)
        for p in list(db["polls"].values())[-15:]:
            tv = sum(get_option_total_votes(o) for o in p["options"])
            markup.add(types.InlineKeyboardButton(f"#{p['id']} — {p['channel_username']} ({tv} votes)", callback_data=f"admvpoll:{act}:{p['id']}"))
        bot.send_message(ADMIN_ID, "<b>পোল সিলেক্ট করুন:</b>", reply_markup=markup)

    elif act == "notice":
        user_states[ADMIN_ID] = "adm_set_notice"
        cur = db.get("global_notice") or "None"
        bot.send_message(ADMIN_ID, f"📢 <b>বর্তমান নোটিশ:</b> {cur}\n\nনতুন গ্লোবাল নোটিশ লিখুন (মুছে ফেলতে <code>off</code> লিখুন):")

    elif act == "feedback":
        sugs = db.get("suggestions", [])[-10:]
        if not sugs:
            bot.send_message(ADMIN_ID, "📭 কোনো ফিডব্যাক নেই।")
            return
        lines = ["📬 <b>সাম্প্রতিক ইউজার ফিডব্যাক:</b>\n"]
        for s in sugs:
            lines.append(f"🆔 <b>#{s['id']}</b> | <b>{s['name']}</b> (<code>{s['user_id']}</code>):\n💬 {s['text']}\n")
        lines.append("➡️ রিপ্লাই দিতে লিখুন: <code>/reply USER_ID আপনার মেসেজ</code>")
        bot.send_message(ADMIN_ID, "\n".join(lines))

    elif act == "ratings":
        rats = db.get("ratings", {})
        if not rats:
            bot.send_message(ADMIN_ID, "⭐ এখনো কেউ রেটিং দেয়নি।")
            return
        avg = round(sum(r["stars"] for r in rats.values()) / len(rats), 2)
        lines = [f"⭐ <b>গড় বট রেটিং: {avg}/5.0 ({len(rats)} জন)</b>\n"]
        for uid_k, r in list(rats.items())[-20:]:
            lines.append(f"• <b>{r['name']}</b> (<code>{uid_k}</code>): {'⭐'*r['stars']}")
        bot.send_message(ADMIN_ID, "\n".join(lines))

    elif act == "ban_menu":
        user_states[ADMIN_ID] = "adm_ban_toggle"
        banned = ", ".join(str(x) for x in db.get("banned_users", [])) or "কেউ নেই"
        bot.send_message(ADMIN_ID, f"🚫 <b>Banned Users:</b> <code>{banned}</code>\n\nযাকে Ban বা Unban করতে চান তার <b>User ID</b> লিখুন:")

    elif act == "polls":
        if not db["polls"]:
            bot.send_message(ADMIN_ID, "কোনো পোল নেই।")
            return
        lines = ["🔍 <b>All Channel Polls:</b>\n"]
        for p in list(db["polls"].values())[-15:]:
            tv = sum(get_option_total_votes(o) for o in p["options"])
            st = "🟢" if p.get("is_open", True) else "🔴"
            lines.append(f"{st} <b>#{p['id']}</b> | {p['channel_username']} | By: <code>{p['owner_id']}</code> | Votes: <b>{tv}</b>")
        lines.append("\n➡️ যেকোনো পোল বন্ধ করতে: <code>/forceclose Poll_ID</code>")
        bot.send_message(ADMIN_ID, "\n".join(lines))

    elif act == "scheds":
        sps = db.get("scheduled_posts", [])
        if not sps:
            bot.send_message(ADMIN_ID, "⏰ কোনো পেন্ডিং শিডিউল পোস্ট নেই।")
            return
        lines = ["⏰ <b>পেন্ডিং শিডিউল পোস্টসমূহ:</b>\n"]
        for idx, s in enumerate(sps):
            lines.append(f"{idx+1}. {s['channel_username']} | By: <code>{s['owner_id']}</code> | Time: {format_user_time(s['send_at'], ADMIN_ID)}")
        bot.send_message(ADMIN_ID, "\n".join(lines))

    elif act == "vip_footer":
        user_states[ADMIN_ID] = "adm_reset_footer"
        bot.send_message(ADMIN_ID, "🏷️ যে VIP ইউজারের কাস্টম ফুটার রিসেট করতে চান তার <b>User ID</b> দিন:")

    elif act == "daily_rep":
        bot.send_message(ADMIN_ID, generate_daily_admin_summary())

    elif act == "fj_mgr":
        user_states[ADMIN_ID] = "adm_fj_update"
        cur = "\n".join(f"• {c['username']} ({c['name']})" for c in db.get("required_chats", []))
        bot.send_message(ADMIN_ID, f"🔗 <b>বর্তমান Force-Join চ্যানেলসমূহ:</b>\n{cur}\n\nনতুন চ্যানেল যোগ করতে লিখুন: <code>+ @channelusername | Channel Name</code>\nবাদ দিতে লিখুন: <code>- @channelusername</code>")

    elif act == "milestones":
        user_states[ADMIN_ID] = "adm_milestones"
        bot.send_message(ADMIN_ID, f"🎯 <b>বর্তমান মাইলস্টোন টার্গেট:</b> <code>{db.get('milestone_targets')}</code>\n\nনতুন টার্গেট দিন (কমা দিয়ে, যেমন: <code>50, 100, 500, 1000</code>):")

    elif act == "cleanup":
        before = len(db["polls"])
        db["polls"] = {k: v for k, v in db["polls"].items() if v.get("is_open", True)}
        removed = before - len(db["polls"])
        save_db(db, immediate_cloud=True)
        bot.answer_callback_query(call.id, f"🧹 {removed}টি বন্ধ হয়ে যাওয়া পুরনো পোল মুছে ফেলা হয়েছে!", show_alert=True)

    elif act == "dm":
        user_states[ADMIN_ID] = "adm_dm_user"
        bot.send_message(ADMIN_ID, "✉️ মেসেজ পাঠানোর ফরম্যাট লিখুন:\n<code>USER_ID | আপনার মেসেজ</code>")

    elif act == "restore":
        res = restore_db_from_telegram()
        if res:
            db.clear()
            db.update(res)
            bot.answer_callback_query(call.id, "✅ @otpchannrl থেকে সব ডাটা রিস্টোর হয়েছে!", show_alert=True)
        else:
            bot.answer_callback_query(call.id, "⚠️ ব্যাকআপ ফাইল পাওয়া যায়নি!", show_alert=True)

    elif act == "hof_info":
        bot.send_message(ADMIN_ID, "🏆 Hall of Fame স্বয়ংক্রিয়ভাবে বটের সর্বোচ্চ ভোট পাওয়া টপ ১০টি পোল প্রদর্শন করে।")

    elif act == "maint":
        db["maintenance_mode"] = not db.get("maintenance_mode", False)
        save_db(db, immediate_cloud=True)
        st = "ON (সাধারণ ইউজারদের জন্য সাময়িক বন্ধ)" if db["maintenance_mode"] else "OFF (সবার জন্য চালু)"
        bot.answer_callback_query(call.id, f"🛠️ Maintenance Mode: {st}", show_alert=True)

    elif act == "backup":
        push_backup_to_telegram()
        bot.answer_callback_query(call.id, "✅ Cloud Backup @otpchannrl এ সেভ হয়েছে!", show_alert=True)

    elif act == "add_vip":
        user_states[ADMIN_ID] = "adm_vip"
        bot.send_message(ADMIN_ID, "🔓 VIP দেওয়ার জন্য <b>User ID</b> লিখুন:")

    elif act == "rem_vip":
        user_states[ADMIN_ID] = "adm_unvip"
        bot.send_message(ADMIN_ID, "🔒 VIP বাতিল করার জন্য <b>User ID</b> লিখুন:")

    elif act == "broadcast":
        user_states[ADMIN_ID] = "adm_bc"
        bot.send_message(ADMIN_ID, "📢 সব ইউজারকে পাঠানোর জন্য ব্রডকাস্ট মেসেজ লিখুন:")

@bot.message_handler(commands=["reply", "forceclose"])
def cmd_admin_quick_actions(message):
    if message.from_user.id != ADMIN_ID:
        return
    if message.text.startswith("/reply"):
        parts = message.text.split(maxsplit=2)
        if len(parts) == 3 and parts[1].isdigit():
            try:
                bot.send_message(int(parts[1]), f"📩 <b>Admin Reply:</b>\n\n{parts[2]}")
                bot.reply_to(message, "✅ রিপ্লাই পাঠানো হয়েছে!")
            except Exception as e:
                bot.reply_to(message, f"❌ ব্যর্থ: {e}")
    elif message.text.startswith("/forceclose"):
        parts = message.text.split()
        if len(parts) == 2 and parts[1].lstrip("#") in db["polls"]:
            announce_poll_winner(parts[1].lstrip("#"), close_reason="🛑 Admin Force-Closed")
            bot.reply_to(message, f"✅ পোল #{parts[1]} জোরপূর্বক বন্ধ করা হয়েছে!")

@bot.callback_query_handler(func=lambda c: c.data.startswith("admvpoll:") and c.from_user.id == ADMIN_ID)
def cb_admin_select_vote_cand(call):
    parts = call.data.split(":")
    mode, pid = parts[1], parts[2]
    poll = db["polls"].get(pid)
    if not poll:
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for idx, o in enumerate(poll["options"]):
        markup.add(types.InlineKeyboardButton(f"🔥 {o['name']} ({get_option_total_votes(o)})", callback_data=f"admvqty:{mode}:{pid}:{idx}"))
    bot.send_message(ADMIN_ID, f"<b>Poll #{pid} — প্রার্থী সিলেক্ট করুন:</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("admvqty:") and c.from_user.id == ADMIN_ID)
def cb_admin_enter_vote_qty(call):
    parts = call.data.split(":")
    user_states[ADMIN_ID] = f"adm_v_qty:{parts[1]}:{parts[2]}:{parts[3]}"
    bot.send_message(ADMIN_ID, "🔢 ভোট সংখ্যা লিখুন (যেমন: <code>50</code>):")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and str(user_states.get(ADMIN_ID, "")).startswith("adm_v_qty:"))
def handle_admin_vote_qty(message):
    parts = user_states.pop(ADMIN_ID).split(":")
    mode, pid, opt_idx = parts[1], parts[2], int(parts[3])
    if not message.text.strip().isdigit():
        bot.reply_to(message, "❌ সঠিক সংখ্যা লিখুন।")
        return
    qty = int(message.text.strip()) if mode == "boost" else -int(message.text.strip())
    ok, msg = apply_admin_vote_adjustment(pid, opt_idx, qty)
    bot.reply_to(message, msg)

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID) in [
    "adm_vip", "adm_unvip", "adm_bc", "adm_set_notice", "adm_ban_toggle",
    "adm_reset_footer", "adm_fj_update", "adm_milestones", "adm_dm_user"
])
def handle_admin_states(message):
    st = user_states.pop(ADMIN_ID)
    txt = message.text.strip()

    if st == "adm_vip" and txt.isdigit():
        tid = int(txt)
        if tid not in db["vip_users"]:
            db["vip_users"].append(tid)
            save_db(db, immediate_cloud=True)
        try:
            bot.send_message(tid, "👑 অ্যাডমিন আপনাকে <b>VIP Access 🔓</b> ও <b>✅ Verified Badge</b> দিয়েছেন!")
        except Exception:
            pass
        bot.reply_to(message, f"✅ <code>{tid}</code>-কে VIP দেওয়া হয়েছে!")

    elif st == "adm_unvip" and txt.isdigit():
        tid = int(txt)
        if tid in db["vip_users"]:
            db["vip_users"].remove(tid)
            save_db(db, immediate_cloud=True)
        bot.reply_to(message, f"🔒 <code>{tid}</code>-এর VIP বাতিল হয়েছে।")

    elif st == "adm_set_notice":
        db["global_notice"] = "" if txt.lower() == "off" else txt
        save_db(db, immediate_cloud=True)
        bot.reply_to(message, "✅ গ্লোবাল নোটিশ আপডেট হয়েছে!")

    elif st == "adm_ban_toggle" and txt.isdigit():
        tid = int(txt)
        db.setdefault("banned_users", [])
        if tid in db["banned_users"]:
            db["banned_users"].remove(tid)
            res = f"🔓 <code>{tid}</code>-কে Unban করা হয়েছে!"
        else:
            db["banned_users"].append(tid)
            res = f"🚫 <code>{tid}</code>-কে Ban করা হয়েছে!"
        save_db(db, immediate_cloud=True)
        bot.reply_to(message, res)

    elif st == "adm_reset_footer" and txt.isdigit():
        if txt in db["users"]:
            db["users"][txt]["custom_footer"] = ""
            save_db(db, immediate_cloud=True)
        bot.reply_to(message, f"✅ <code>{txt}</code>-এর কাস্টম ফুটার রিসেট হয়েছে।")

    elif st == "adm_fj_update":
        if txt.startswith("+") and "|" in txt:
            u_part, n_part = [x.strip() for x in txt[1:].split("|", 1)]
            if not u_part.startswith("@"):
                u_part = "@" + u_part
            db["required_chats"].append({"username": u_part, "url": f"https://t.me/{u_part.lstrip('@')}", "name": n_part})
            save_db(db, immediate_cloud=True)
            bot.reply_to(message, f"✅ Force-Join চ্যানেল <b>{u_part}</b> যুক্ত হয়েছে!")
        elif txt.startswith("-"):
            u_part = txt[1:].strip()
            if not u_part.startswith("@"):
                u_part = "@" + u_part
            db["required_chats"] = [c for c in db["required_chats"] if c["username"].lower() != u_part.lower()]
            save_db(db, immediate_cloud=True)
            bot.reply_to(message, f"🗑 <b>{u_part}</b> বাদ দেওয়া হয়েছে!")

    elif st == "adm_milestones":
        nums = [int(x.strip()) for x in txt.split(",") if x.strip().isdigit()]
        if nums:
            db["milestone_targets"] = sorted(list(set(nums)))
            save_db(db, immediate_cloud=True)
            bot.reply_to(message, f"✅ নতুন মাইলস্টোন সেট হয়েছে: <code>{db['milestone_targets']}</code>")

    elif st == "adm_dm_user" and "|" in txt:
        uid_s, msg_s = [x.strip() for x in txt.split("|", 1)]
        if uid_s.isdigit():
            try:
                bot.send_message(int(uid_s), f"📩 <b>Message from Admin:</b>\n\n{msg_s}")
                bot.reply_to(message, "✅ মেসেজ পাঠানো হয়েছে!")
            except Exception as e:
                bot.reply_to(message, f"❌ ব্যর্থ: {e}")

    elif st == "adm_bc":
        sent = 0
        for uid in list(db["users"].keys()):
            try:
                bot.send_message(int(uid), f"📢 <b>Announcement:</b>\n\n{txt}")
                sent += 1
            except Exception:
                pass
        bot.reply_to(message, f"✅ মোট <b>{sent}</b> জনকে পাঠানো হয়েছে!")

# ================= WEBHOOK & SERVER RUNNER =================
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")

@app.route("/")
def home():
    return "Channel Vote Maker (@Votemaker5bot) Ultra Pro 2026 Edition is Live 24/7!", 200

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

def setup_webhook_async():
    time.sleep(2)
    try:
        bot.remove_webhook()
        time.sleep(1)
        if RENDER_URL:
            bot.set_webhook(url=f"{RENDER_URL}/{BOT_TOKEN}", allowed_updates=["message", "callback_query", "chat_member", "my_chat_member"])
    except Exception as e:
        print("Webhook error:", e)

if __name__ == "__main__":
    threading.Thread(target=background_watcher, daemon=True).start()
    if RENDER_URL:
        threading.Thread(target=setup_webhook_async, daemon=True).start()
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)
    else:
        bot.remove_webhook()
        time.sleep(1)
        bot.infinity_polling(skip_pending=True, allowed_updates=["message", "callback_query", "chat_member", "my_chat_member"])
