import os
import json
import time
import threading
import telebot
from telebot import types
from flask import Flask, request

# ================= CONFIGURATION =================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "9224149092:AAHO-bMBo-UsquA36EB7ay-f708mk7iaFWw")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8298133943"))
ADMIN_USERNAME = "@rafimhossen"
BOT_USERNAME = "Votemaker5bot"
DEFAULT_LOG_CHANNEL = "@optchannel6"
PROMO_CHANNEL = "@bdgiveaways24"

REQUIRED_CHATS = [
    {"username": "@optchannel6", "url": "https://t.me/optchannel6", "name": "Opt Channel 6"},
    {"username": "@PremiumApkVaultBD", "url": "https://t.me/PremiumApkVaultBD", "name": "Premium Apk Vault BD"},
    {"username": "@ProApkHub_Official", "url": "https://t.me/ProApkHub_Official", "name": "Pro Apk Hub Official"},
    {"username": "@bdgivewaychat", "url": "https://t.me/bdgivewaychat", "name": "BD Giveaway Chat"},
    {"username": "@bdgiveaways24", "url": "https://t.me/bdgiveaways24", "name": "BD Giveaways 24"},
]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=False)
app = Flask(__name__)

DB_FILE = "voting_bot_db.json"
db_lock = threading.Lock()
user_states = {}
draft_polls = {}

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "vip_users" not in data:
                data["vip_users"] = []
            if not data.get("log_channel"):
                data["log_channel"] = DEFAULT_LOG_CHANNEL
            return data
    return {
        "log_channel": DEFAULT_LOG_CHANNEL,
        "vip_users": [],
        "users": {},
        "polls": {},
        "poll_counter": 100
    }

def save_db(data):
    with db_lock:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

db = load_db()

# ================= MULTI-LANGUAGE TEXTS =================
TEXTS = {
    "bn": {
        "choose_lang": "🌐 অনুগ্রহ করে আপনার ভাষা নির্বাচন করুন / Please select your language:",
        "force_join": (
            "⚠️ <b>বটটি ব্যবহার করতে হলে নিচের ৫টি চ্যানেল ও গ্রুপে অবশ্যই জয়েন থাকতে হবে!</b>\n\n"
            "সবগুলোতে জয়েন করার পর নিচের <b>✅ Verify / যাচাই করুন</b> বাটনে ক্লিক করুন:"
        ),
        "verify_btn": "✅ Verify / যাচাই করুন",
        "not_joined": "❌ আপনি এখনো সব চ্যানেল ও গ্রুপে জয়েন করেননি! ৫টিতেই জয়েন করে আবার চেষ্টা করুন।",
        "bot_locked_screen": (
            "😇 <b>নিচের বাটন থেকে অপশন নির্বাচন করুন এবং চ্যানেলে নিজের পোল তৈরি করুন।</b>\n\n"
            "🔒 বটটি আনলক করতে কমপক্ষে <b>১ জন বন্ধুকে</b> রেফার করুন!\n"
            "🔗 <b>রেফারেল লিংক:</b> <code>{ref_link}</code>\n"
            "👥 <b>বর্তমান রেফার:</b> <code>{refs}/1</code>"
        ),
        "check_unlock_btn": "🔄 Check Unlock / আনলক যাচাই করুন",
        "still_locked_alert": "❌ আপনার এখনো ১টি রেফার পূর্ণ হয়নি! আপনার লিংকটি বন্ধুদের শেয়ার করুন।",
        "welcome": (
            "😇 <b>স্বাগতম {name}!</b>\n"
            "নিচের বাটন থেকে অপশন নির্বাচন করুন এবং চ্যানেলে নিজের পোল তৈরি করুন।\n\n"
            "🔓 <b>স্ট্যাটাস:</b> আনলকড ✅ | 👥 <b>রেফার:</b> {refs} জন"
        ),
        "btn_create": "📣 চ্যানেল পোল তৈরি",
        "btn_edit": "✏️ পোল এডিট করুন",
        "btn_buy": "🛒 কোড কিনুন",
        "btn_support": "📞 সাপোর্ট",
        "btn_refer": "🔗 রেফার ও ইনভাইট",
        "btn_lang": "🌐 ভাষা (Language)",
        "btn_admin": "👑 Admin Panel",
        "btn_cancel": "❌ Cancel",
        "btn_text_only": "🟢 শুধুমাত্র লেখা",
        "create_prompt_inline": "😇 নিচের বাটন থেকে অপশন নির্বাচন করুন এবং চ্যানেলে নিজের পোল তৈরি করুন।",
        "create_now_btn": "🗳 Create Now Poll 🚀",
        "ask_channel": (
            "📢 <b>এখন আপনার চ্যানেল বা গ্রুপের লিংক / ইউজারনেম / ID পাঠান</b>\n\n"
            "উদাহরণস্বরূপ 👉 <code>@mychannel</code> অথবা <code>https://t.me/mychannel</code> অথবা <code>-1001234567890</code>\n\n"
            "⚠️ <b>শর্তাবলী:</b>\n"
            "১. আপনাকে অবশ্যই ওই চ্যানেল/গ্রুপের <b>Owner বা Admin</b> হতে হবে।\n"
            "২. এই বটটিকেও ওই চ্যানেল/গ্রুপে <b>Admin</b> হিসেবে যুক্ত রাখতে হবে।"
        ),
        "not_bot_admin": (
            "❌ <b>Error! বটটি ওই চ্যানেল/গ্রুপে Admin নয় অথবা চ্যানেলটি খুঁজে পাওয়া যায়নি।</b>\n\n"
            "আগে বটকে চ্যানেলে Admin বানিয়ে আবার চ্যানেলের <code>@username</code> বা ID পাঠান:"
        ),
        "not_user_admin": (
            "🚫 <b>অ্যাক্সেস প্রত্যাখ্যাত! আপনি এই চ্যানেল বা গ্রুপের Admin বা Owner নন।</b>\n\n"
            "অন্য কারো চ্যানেলে পোল তৈরি করা সম্পূর্ণ নিষিদ্ধ! শুধুমাত্র যে চ্যানেল বা গ্রুপের আপনি নিজে <b>Admin/Owner</b>, সেটির <code>@username</code> বা ID পাঠান:"
        ),
        "ask_question": (
            "❓ <b>আপনার পোলের জন্য প্রশ্ন পাঠান</b>\n\n"
            "➡️ মোটা লিখতে হলে: <code>&lt;b&gt;আপনার লেখা&lt;/b&gt;</code>\n"
            "➡️ বাঁকা লিখতে হলে: <code>&lt;i&gt;আপনার লেখা&lt;/i&gt;</code>\n"
            "➡️ কোডের মতো লিখতে: <code>&lt;code&gt;আপনার লেখা&lt;/code&gt;</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ <b>এখন আপনার প্রশ্ন পাঠান:</b>"
        ),
        "question_preview": (
            "📝 <b>আপনার পোলের প্রশ্নের প্রিভিউ:</b>\n\n"
            "{question}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ <b>প্রশ্নটি কি ঠিক আছে?</b>"
        ),
        "btn_q_ok": "✅ হ্যাঁ, ঠিক আছে",
        "btn_q_rewrite": "✏️ আবার লিখুন",
        "ask_photo": (
            "📸 <b>আপনার পোলের জন্য একটি ছবি/ব্যানার যুক্ত করুন</b>\n\n"
            "পোলের সাথে কোনো ছবি দেখাতে চাইলে তা এখন বটের ইনবক্সে পাঠিয়ে দিন (ফটো আকারে)।\n\n"
            "(কোনো ছবি যুক্ত করতে না চাইলে নিচের <b>\"🟢 শুধুমাত্র লেখা\"</b> বাটনে ক্লিক করুন)"
        ),
        "ask_options": (
            "📋 <b>পোলের প্রার্থী/অংশগ্রহণকারীদের নাম লিখুন</b>\n\n"
            "🔸 <b>কিভাবে লিখবেন:</b>\n"
            "প্রত্যেকের নামের মাঝে <code>&amp;</code> চিহ্ন দিন\n\n"
            "🔸 <b>উদাহরণ:</b>\n"
            "<code>নাম লিখুন&amp;নাম লিখুন&amp;নাম লিখুন</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "ℹ️ <b>নোট:</b>\n"
            "• সর্বোচ্চ ৩০ জনের নাম দিতে পারবেন\n"
            "• পরে নাম যোগ বা বাদ দিতে পোল এডিট মেনু ব্যবহার করুন"
        ),
        "invalid_options": "❌ কমপক্ষে ১ জন এবং সর্বোচ্চ ৩০ জন প্রার্থীর নাম <code>&amp;</code> চিহ্ন দিয়ে লিখুন!",
        "poll_sent": "🚀 <b>আপনার চ্যানেলে পোল পাঠানো হয়েছে।</b>\n\n🗳 পোলটি স্বয়ংক্রিয়ভাবে ট্র্যাক করা হচ্ছে।",
        "buy_code_msg": (
            f"🛒 <b>নিজের নামে এমন প্রফেশনাল পোল মেকার বট বা সোর্স কোড কিনতে চান?</b>\n\n"
            f"সরাসরি অ্যাডমিনের সাথে যোগাযোগ করুন:\n"
            f"👤 <b>Admin:</b> {ADMIN_USERNAME}"
        ),
        "support_msg": (
            f"📞 <b>সাপোর্ট ও হেল্প ডেস্ক</b>\n\n"
            f"যেকোনো সমস্যা বা সাহায্যের জন্য যোগাযোগ করুন:\n"
            f"👤 <b>Admin:</b> {ADMIN_USERNAME}\n"
            f"💬 <b>Support Group:</b> @bdgivewaychat\n"
            f"📢 <b>Official Channel:</b> @bdgiveaways24"
        ),
        "cancelled": "❌ বাতিল করা হয়েছে। ড্যাশবোর্ডে ফিরে আসা হলো।"
    },
    "en": {
        "choose_lang": "🌐 Please select your language / অনুগ্রহ করে আপনার ভাষা নির্বাচন করুন:",
        "force_join": (
            "⚠️ <b>You must join all 5 required channels & groups below to use this bot!</b>\n\n"
            "After joining all of them, click the <b>✅ Verify Joined</b> button below:"
        ),
        "verify_btn": "✅ Verify Joined",
        "not_joined": "❌ You haven't joined all 5 required channels/groups yet! Please join all and try again.",
        "bot_locked_screen": (
            "😇 <b>Select an option below to create your channel poll.</b>\n\n"
            "🔒 Refer at least <b>1 friend</b> to unlock the bot!\n"
            "🔗 <b>Referral Link:</b> <code>{ref_link}</code>\n"
            "👥 <b>Current Referrals:</b> <code>{refs}/1</code>"
        ),
        "check_unlock_btn": "🔄 Check Unlock",
        "still_locked_alert": "❌ You still have 0 referrals! Share your referral link first.",
        "welcome": (
            "😇 <b>Welcome {name}!</b>\n"
            "Select an option below to create and manage your channel polls.\n\n"
            "🔓 <b>Status:</b> Unlocked ✅ | 👥 <b>Referrals:</b> {refs}"
        ),
        "btn_create": "📣 Create Channel Poll",
        "btn_edit": "✏️ Edit Polls",
        "btn_buy": "🛒 Buy Code",
        "btn_support": "📞 Support",
        "btn_refer": "🔗 Refer & Invite",
        "btn_lang": "🌐 Language (ভাষা)",
        "btn_admin": "👑 Admin Panel",
        "btn_cancel": "❌ Cancel",
        "btn_text_only": "🟢 Text Only",
        "create_prompt_inline": "😇 Click the button below to create a new poll for your channel.",
        "create_now_btn": "🗳 Create Now Poll 🚀",
        "ask_channel": (
            "📢 <b>Now send your channel or group link / @username / ID</b>\n\n"
            "Example 👉 <code>@mychannel</code> or <code>https://t.me/mychannel</code> or <code>-1001234567890</code>\n\n"
            "⚠️ <b>Requirements:</b>\n"
            "1. You must be an <b>Owner or Admin</b> of that channel/group.\n"
            "2. This bot must also be added as an <b>Admin</b> there."
        ),
        "not_bot_admin": (
            "❌ <b>Error! Bot is not an Admin in that channel/group or not found.</b>\n\n"
            "Add the bot as Admin first, then send the channel <code>@username</code> or ID again:"
        ),
        "not_user_admin": (
            "🚫 <b>Access Denied! You are NOT an Admin or Owner of this channel/group.</b>\n\n"
            "Creating polls in someone else's channel is strictly prohibited! Please enter a channel/group where you are an <b>Admin/Owner</b>:"
        ),
        "ask_question": (
            "❓ <b>Send the question/title for your poll</b>\n\n"
            "➡️ Bold: <code>&lt;b&gt;Your Text&lt;/b&gt;</code>\n"
            "➡️ Italic: <code>&lt;i&gt;Your Text&lt;/i&gt;</code>\n"
            "➡️ Mono: <code>&lt;code&gt;Your Text&lt;/code&gt;</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ <b>Send your question now:</b>"
        ),
        "question_preview": (
            "📝 <b>Poll Question Preview:</b>\n\n"
            "{question}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ <b>Is the question okay?</b>"
        ),
        "btn_q_ok": "✅ Yes, Looks Good",
        "btn_q_rewrite": "✏️ Rewrite",
        "ask_photo": (
            "📸 <b>Add a photo/banner for your poll</b>\n\n"
            "Send an image now if you want a banner with your poll.\n\n"
            "(Or click <b>\"🟢 Text Only\"</b> below to skip)"
        ),
        "ask_options": (
            "📋 <b>Send candidate/option names</b>\n\n"
            "🔸 <b>Format:</b> Separate each name with <code>&amp;</code>\n"
            "🔸 <b>Example:</b> <code>Name 1&amp;Name 2&amp;Name 3</code>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "ℹ️ <b>Note:</b> Maximum 30 candidates allowed."
        ),
        "invalid_options": "❌ Please send 1 to 30 candidate names separated by <code>&amp;</code>!",
        "poll_sent": "🚀 <b>Poll has been sent to your channel!</b>\n\n🗳 Live vote tracking is now active.",
        "buy_code_msg": (
            f"🛒 <b>Want to buy this Poll Maker Bot or Source Code?</b>\n\n"
            f"Contact Admin directly:\n"
            f"👤 <b>Admin:</b> {ADMIN_USERNAME}"
        ),
        "support_msg": (
            f"📞 <b>Support & Help Desk</b>\n\n"
            f"Contact for any help:\n"
            f"👤 <b>Admin:</b> {ADMIN_USERNAME}\n"
            f"💬 <b>Support Group:</b> @bdgivewaychat"
        ),
        "cancelled": "❌ Cancelled. Returned to Dashboard."
    }
}

# ================= HELPER FUNCTIONS =================
def get_lang(user_id):
    return db["users"].get(str(user_id), {}).get("lang", "bn")

def t(user_id, key):
    return TEXTS.get(get_lang(user_id), TEXTS["bn"]).get(key, "")

def is_vip(user_id):
    return user_id == ADMIN_ID or int(user_id) in db.get("vip_users", [])

def is_unlocked(user_id):
    if is_vip(user_id):
        return True
    return db["users"].get(str(user_id), {}).get("referrals", 0) >= 1

def check_all_joined(user_id):
    if is_vip(user_id):
        return True
    for chat in REQUIRED_CHATS:
        try:
            member = bot.get_chat_member(chat["username"], user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True

def main_menu_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(t(user_id, "btn_create"))
    markup.row(t(user_id, "btn_edit"))
    markup.row(t(user_id, "btn_buy"), t(user_id, "btn_support"))
    markup.row(t(user_id, "btn_refer"), t(user_id, "btn_lang"))
    if user_id == ADMIN_ID:
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
    for ch in REQUIRED_CHATS:
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
        types.InlineKeyboardButton("🌐 ভাষা / Language", callback_data="open_lang")
    )
    bot.send_message(chat_id, t(user_id, "bot_locked_screen").format(ref_link=ref_link, refs=refs), reply_markup=markup)

def send_log_to_channel(text):
    log_ch = db.get("log_channel") or DEFAULT_LOG_CHANNEL
    if log_ch:
        try:
            bot.send_message(log_ch, text, disable_web_page_preview=True)
        except Exception as e:
            print("Log error:", e)

def make_progress_bar(count, total):
    if total <= 0:
        return "░░░░░░░░ 0%"
    pct = round((count / total) * 100)
    filled = round((pct / 100) * 8)
    bar = "▓" * filled + "░" * (8 - filled)
    return f"{bar} {pct}%"

def build_channel_poll_caption(poll_id):
    poll = db["polls"][poll_id]
    total_votes = sum(len(o["voters"]) for o in poll["options"])

    stats_lines = []
    for o in poll["options"]:
        cnt = len(o["voters"])
        p_bar = make_progress_bar(cnt, total_votes)
        stats_lines.append(f"▫️ <b>{o['name']}</b> — <code>{cnt}</code>\n   <code>{p_bar}</code>")
    stats_block = "\n".join(stats_lines)

    timer_info = ""
    if poll.get("close_at") and poll.get("is_open", True):
        rem_sec = int(poll["close_at"] - time.time())
        if rem_sec > 0:
            hrs = rem_sec // 3600
            mins = (rem_sec % 3600) // 60
            timer_info = f"\n⏳ <b>Time Left:</b> {hrs}h {mins}m"

    return (
        f"🗳 <b>{poll['question']}</b>\n\n"
        f"{stats_block}\n\n"
        f"📈 <b>Total Votes:</b> <code>{total_votes}</code>{timer_info}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ Poll Create :- @{BOT_USERNAME}\n"
        f"📢 Join :- {PROMO_CHANNEL}"
    )

def build_channel_poll_markup(poll_id):
    poll = db["polls"][poll_id]
    markup = types.InlineKeyboardMarkup(row_width=1)
    is_open = poll.get("is_open", True)

    for idx, opt in enumerate(poll["options"]):
        v_count = len(opt["voters"])
        btn_text = f"🗳 {v_count} | 🔥 {opt['name']}" if is_open else f"🔒 {v_count} | {opt['name']}"
        cb = f"pvote:{poll_id}:{idx}" if is_open else f"pclosed:{poll_id}"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=cb))

    if is_open:
        markup.row(
            types.InlineKeyboardButton("🔄 ভোট প্রত্যাহার করুন", callback_data=f"pwithdraw:{poll_id}"),
            types.InlineKeyboardButton("🛑 পোল বন্ধ করুন", callback_data=f"pclose:{poll_id}")
        )
    else:
        markup.add(types.InlineKeyboardButton("🔒 পোলটি বন্ধ করা হয়েছে", callback_data=f"pclosed:{poll_id}"))
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
    except Exception as e:
        print("Refresh channel message error:", e)

def announce_poll_winner(pid, auto_closed=False):
    poll = db["polls"].get(pid)
    if not poll:
        return
    poll["is_open"] = False
    poll["close_at"] = None
    save_db(db)
    refresh_channel_poll_message(pid)

    sorted_opts = sorted(poll["options"], key=lambda x: len(x["voters"]), reverse=True)
    winner = sorted_opts[0] if sorted_opts else {"name": "N/A", "voters": []}
    total_v = sum(len(o["voters"]) for o in poll["options"])
    standings = "\n".join([f"{idx+1}. <b>{o['name']}</b> — <code>{len(o['voters'])}</code> ভোট" for idx, o in enumerate(sorted_opts)])
    reason_tag = "⏰ নির্ধারিত সময় শেষ (Auto-Closed)" if auto_closed else "🛑 ভোটিং সমাপ্ত"

    win_msg = (
        f"🏆🎉 <b>FINAL POLL RESULT (#{pid})</b> 🎉🏆\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"❓ <b>প্রশ্ন:</b> {poll['question']}\n\n"
        f"👑 <b>বিজয়ী (Winner):</b> 🔥 <b>{winner['name']}</b> ({len(winner['voters'])} ভোট)\n\n"
        f"📊 <b>চূড়ান্ত ফলাফল (মোট {total_v} ভোট):</b>\n"
        f"{standings}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{reason_tag}"
    )
    try:
        bot.send_message(poll["channel_id"], win_msg)
    except Exception:
        pass
    send_log_to_channel(f"🏁 <b>পোল #{pid} সমাপ্ত হয়েছে!</b> ({poll['channel_username']})\n👑 বিজয়ী: <b>{winner['name']}</b> ({len(winner['voters'])} ভোট)")

# ================= AUTO-TIMER BACKGROUND WORKER =================
def auto_close_watcher():
    while True:
        try:
            now = time.time()
            for pid, poll in list(db.get("polls", {}).items()):
                close_ts = poll.get("close_at")
                if poll.get("is_open", True) and close_ts and now >= close_ts:
                    announce_poll_winner(pid, auto_closed=True)
        except Exception as e:
            print("Auto-timer watcher error:", e)
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
            "referrals": 0,
            "referred_by": None,
            "joined_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        if ref_by and ref_by != uid and ref_by in db["users"]:
            db["users"][uid]["referred_by"] = ref_by
            db["users"][ref_by]["referrals"] += 1
            try:
                bot.send_message(int(ref_by), f"🎊 অভিনন্দন! <b>{user.first_name}</b> আপনার রেফারে জয়েন করেছেন! বট আনলক হয়েছে 🔓")
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
        db["users"][uid]["name"] = user.first_name or "User"
        db["users"][uid]["username"] = f"@{user.username}" if user.username else "No Username"
        save_db(db)
    return is_new

def send_dashboard(chat_id, user):
    if not check_all_joined(user.id):
        send_force_join_msg(chat_id, user.id)
        return
    if not is_unlocked(user.id):
        send_lock_screen(chat_id, user.id)
        return
    refs = db["users"][str(user.id)]["referrals"]
    bot.send_message(chat_id, t(user.id, "welcome").format(name=user.first_name, refs=refs), reply_markup=main_menu_keyboard(user.id))

def passes_gate(message):
    uid = message.from_user.id
    if not check_all_joined(uid):
        send_force_join_msg(message.chat.id, uid)
        return False
    if not is_unlocked(uid):
        send_lock_screen(message.chat.id, uid)
        return False
    return True

# ================= START, DEEP-LINK DIRECT VOTE & LANGUAGE =================
@bot.message_handler(commands=["start"])
def handle_start(message):
    user_states.pop(message.from_user.id, None)
    draft_polls.pop(message.from_user.id, None)
    args = message.text.split()
    payload = args[1] if len(args) > 1 else ""

    # ডিরেক্ট ক্যান্ডিডেট ভোট লিংক হ্যান্ডলার (?start=v_101_0)
    if payload.startswith("v_"):
        register_user(message.from_user)
        parts = payload.split("_")
        if len(parts) == 3 and parts[1] in db["polls"] and parts[2].isdigit():
            pid = parts[1]
            opt_idx = int(parts[2])
            poll = db["polls"][pid]
            if 0 <= opt_idx < len(poll["options"]):
                cand_name = poll["options"][opt_idx]["name"]
                markup = types.InlineKeyboardMarkup(row_width=1)
                markup.add(
                    types.InlineKeyboardButton(f"✅ হ্যাঁ, {cand_name}-কে ভোট দিন", callback_data=f"directvote:{pid}:{opt_idx}"),
                    types.InlineKeyboardButton("📢 চ্যানেল দেখুন", url=f"https://t.me/{poll['channel_username'].lstrip('@')}")
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
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🇧🇩 বাংলা", callback_data="setlang:bn"),
            types.InlineKeyboardButton("🇺🇸 English", callback_data="setlang:en")
        )
        bot.send_message(message.chat.id, TEXTS["bn"]["choose_lang"], reply_markup=markup)
        return
    send_dashboard(message.chat.id, message.from_user)

@bot.callback_query_handler(func=lambda c: c.data.startswith("directvote:"))
def cb_direct_candidate_vote(call):
    parts = call.data.split(":")
    pid, opt_idx = parts[1], int(parts[2])
    process_vote_action(call, pid, opt_idx, from_direct=True)

@bot.callback_query_handler(func=lambda c: c.data == "open_lang")
def cb_open_lang(call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇧🇩 বাংলা", callback_data="setlang:bn"),
        types.InlineKeyboardButton("🇺🇸 English", callback_data="setlang:en")
    )
    bot.send_message(call.message.chat.id, t(call.from_user.id, "choose_lang"), reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("setlang:"))
def cb_set_lang(call):
    lang = call.data.split(":")[1]
    register_user(call.from_user)
    db["users"][str(call.from_user.id)]["lang"] = lang
    save_db(db)
    bot.answer_callback_query(call.id, "Updated!")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
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
@bot.message_handler(func=lambda m: m.text in [TEXTS["bn"]["btn_cancel"], TEXTS["en"]["btn_cancel"], "/cancel"])
def handle_cancel_btn(message):
    user_states.pop(message.from_user.id, None)
    draft_polls.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, t(message.from_user.id, "cancelled"), reply_markup=main_menu_keyboard(message.from_user.id))

# ================= MENU BUTTONS =================
@bot.message_handler(func=lambda m: m.text in [TEXTS["bn"]["btn_lang"], TEXTS["en"]["btn_lang"]])
def menu_lang(message):
    cb_open_lang(type("Obj", (), {"message": message, "from_user": message.from_user}))

@bot.message_handler(func=lambda m: m.text in [TEXTS["bn"]["btn_buy"], TEXTS["en"]["btn_buy"]])
def menu_buy(message):
    if not passes_gate(message):
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💬 Contact Admin", url="https://t.me/rafimhossen"))
    bot.send_message(message.chat.id, t(message.from_user.id, "buy_code_msg"), reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in [TEXTS["bn"]["btn_support"], TEXTS["en"]["btn_support"]])
def menu_support(message):
    if not passes_gate(message):
        return
    bot.send_message(message.chat.id, t(message.from_user.id, "support_msg"))

@bot.message_handler(func=lambda m: m.text in [TEXTS["bn"]["btn_refer"], TEXTS["en"]["btn_refer"]])
def menu_refer(message):
    if not passes_gate(message):
        return
    uid = str(message.from_user.id)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
    refs = db["users"][uid]["referrals"]
    bot.send_message(message.chat.id, f"🔗 <b>রেফারেল লিংক:</b>\n<code>{ref_link}</code>\n\n👥 <b>মোট রেফার:</b> {refs} জন")

# ================= POLL CREATION WIZARD (WITH TIMER & ADMIN CHECK) =================
@bot.message_handler(func=lambda m: m.text in [TEXTS["bn"]["btn_create"], TEXTS["en"]["btn_create"]])
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
    draft_polls[uid] = {"timer_hours": 0}
    bot.send_message(call.message.chat.id, t(uid, "ask_channel"), reply_markup=cancel_keyboard(uid))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "step_channel", content_types=["text"])
def wizard_step_channel(message):
    uid = message.from_user.id
    target = message.text.strip()
    if "t.me/" in target:
        target = "@" + target.split("t.me/")[-1].strip("/")

    try:
        bot_id = bot.get_me().id
        chat = bot.get_chat(target)

        bot_member = bot.get_chat_member(chat.id, bot_id)
        if bot_member.status not in ["administrator", "creator"]:
            bot.send_message(message.chat.id, t(uid, "not_bot_admin"), reply_markup=cancel_keyboard(uid))
            return

        user_member = bot.get_chat_member(chat.id, uid)
        if user_member.status not in ["administrator", "creator"] and uid != ADMIN_ID:
            bot.send_message(message.chat.id, t(uid, "not_user_admin"), reply_markup=cancel_keyboard(uid))
            return

        draft_polls[uid]["channel_id"] = chat.id
        draft_polls[uid]["channel_username"] = f"@{chat.username}" if chat.username else str(chat.id)
        draft_polls[uid]["channel_title"] = chat.title or target
        draft_polls[uid]["user_role"] = user_member.status
        user_states[uid] = "step_question"
        bot.send_message(
            message.chat.id,
            f"✅ <b>ভেরিফাই সফল!</b> ({chat.title or target} — পদবী: <b>{user_member.status.upper()}</b>)\n\n" + t(uid, "ask_question"),
            reply_markup=cancel_keyboard(uid)
        )
    except Exception:
        bot.send_message(message.chat.id, t(uid, "not_bot_admin"), reply_markup=cancel_keyboard(uid))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "step_question", content_types=["text"])
def wizard_step_question(message):
    uid = message.from_user.id
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
    action = call.data.split(":")[1]
    if action == "rewrite":
        user_states[uid] = "step_question"
        bot.send_message(call.message.chat.id, t(uid, "ask_question"), reply_markup=cancel_keyboard(uid))
    else:
        user_states[uid] = "step_photo"
        bot.send_message(call.message.chat.id, t(uid, "ask_photo"), reply_markup=cancel_keyboard(uid, include_text_only=True))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "step_photo", content_types=["text", "photo"])
def wizard_step_photo(message):
    uid = message.from_user.id
    if message.content_type == "photo":
        draft_polls[uid]["photo_id"] = message.photo[-1].file_id
    elif message.text in [TEXTS["bn"]["btn_text_only"], TEXTS["en"]["btn_text_only"]]:
        draft_polls[uid]["photo_id"] = None
    else:
        bot.send_message(message.chat.id, t(uid, "ask_photo"), reply_markup=cancel_keyboard(uid, include_text_only=True))
        return

    user_states[uid] = "step_options"
    bot.send_message(message.chat.id, t(uid, "ask_options"), reply_markup=cancel_keyboard(uid))

def build_draft_preview(uid):
    d = draft_polls[uid]
    cands_list = "\n".join([f"👤 {idx+1}. {name}" for idx, name in enumerate(d["options"])])
    has_pic = "হ্যাঁ ✅" if d.get("photo_id") else "না"
    hrs = d.get("timer_hours", 0)
    timer_label = f"{hrs} ঘণ্টা পর অটো বন্ধ হবে" if hrs > 0 else "Manual (ম্যানুয়াল বন্ধ)"

    text = (
        f"📊 <b>পোলের ফাইনাল প্রিভিউ:</b>\n\n"
        f"📣 <b>চ্যানেল:</b> {d['channel_title']} ({d['channel_username']})\n"
        f"❓ <b>প্রশ্ন:</b> {d['question']}\n"
        f"🖼 <b>ছবি যুক্ত:</b> {has_pic}\n"
        f"⏳ <b>অটো টাইমার:</b> {timer_label}\n\n"
        f"📝 <b>প্রার্থীসমূহ:</b>\n{cands_list}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ <i>নিচের বাটন থেকে অটো-ক্লোজ টাইমার সেট করতে পারেন:</i>"
    )
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("⏳ 1h", callback_data="settimer:1"),
        types.InlineKeyboardButton("⏳ 6h", callback_data="settimer:6"),
        types.InlineKeyboardButton("⏳ 12h", callback_data="settimer:12"),
        types.InlineKeyboardButton("⏳ 24h", callback_data="settimer:24"),
        types.InlineKeyboardButton("♾ Manual", callback_data="settimer:0")
    )
    markup.add(types.InlineKeyboardButton("🚀 Send to Channel", callback_data="publish_poll_now"))
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_draft"))
    return text, markup

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "step_options", content_types=["text"])
def wizard_step_options(message):
    uid = message.from_user.id
    raw_names = [name.strip() for name in message.text.split("&") if name.strip()]
    if not raw_names or len(raw_names) > 30:
        bot.send_message(message.chat.id, t(uid, "invalid_options"), reply_markup=cancel_keyboard(uid))
        return

    draft_polls[uid]["options"] = raw_names
    user_states[uid] = "step_final_preview"
    text, markup = build_draft_preview(uid)
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("settimer:"))
def cb_set_draft_timer(call):
    uid = call.from_user.id
    if uid not in draft_polls:
        return
    hrs = int(call.data.split(":")[1])
    draft_polls[uid]["timer_hours"] = hrs
    text, markup = build_draft_preview(uid)
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        pass

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
    options_data = [{"name": name, "voters": []} for name in d["options"]]
    db["polls"][pid] = {
        "id": pid,
        "owner_id": uid,
        "owner_name": call.from_user.first_name,
        "owner_username": creator_uname,
        "channel_id": d["channel_id"],
        "channel_username": d["channel_username"],
        "channel_title": d["channel_title"],
        "question": d["question"],
        "photo_id": d.get("photo_id"),
        "options": options_data,
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
        save_db(db)
    except Exception as e:
        del db["polls"][pid]
        save_db(db)
        bot.send_message(call.message.chat.id, f"❌ চ্যানেলে পাঠাতে সমস্যা হয়েছে: {e}", reply_markup=main_menu_keyboard(uid))
        return

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    # ক্রিয়েটরকে ডিরেক্ট ক্যান্ডিডেট ভোট লিংকসহ মেসেজ পাঠানো
    direct_links_list = "\n".join([
        f"🔥 <b>{o['name']}:</b> <code>https://t.me/{BOT_USERNAME}?start=v_{pid}_{idx}</code>"
        for idx, o in enumerate(options_data)
    ])
    bot.send_message(
        call.message.chat.id,
        f"{t(uid, 'poll_sent')}\n\n"
        f"🔗 <b>প্রতিযোগীদের পার্সোনাল ডিরেক্ট ভোট লিংক (শেয়ার করার জন্য):</b>\n{direct_links_list}",
        reply_markup=main_menu_keyboard(uid)
    )

    cands_str = ", ".join(d["options"])
    auto_log = (
        f"🆕 <b>নতুন ভোট/পোল তৈরি হয়েছে! (Poll #{pid})</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>যিনি ভোট বানিয়েছেন:</b> {call.from_user.first_name} ({d.get('user_role', 'Admin').upper()})\n"
        f"🔰 <b>ক্রিয়েটর ইউজারনেম:</b> {creator_uname}\n"
        f"🆔 <b>ক্রিয়েটর আইডি:</b> <code>{uid}</code>\n"
        f"📢 <b>যে চ্যানেলে বানানো হয়েছে:</b> {d['channel_title']}\n"
        f"🔗 <b>চ্যানেল লিংক/ID:</b> {d['channel_username']} (<code>{d['channel_id']}</code>)\n"
        f"❓ <b>পোলের প্রশ্ন:</b> {d['question']}\n"
        f"📋 <b>প্রার্থীসমূহ:</b> {cands_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    send_log_to_channel(auto_log)

# ================= LIVE VOTING, WITHDRAW & CLOSE =================
def process_vote_action(call, pid, opt_idx, from_direct=False):
    voter = call.from_user
    vid = voter.id

    poll = db["polls"].get(pid)
    if not poll:
        bot.answer_callback_query(call.id, "❌ পোলটি খুঁজে পাওয়া যায়নি!", show_alert=True)
        return
    if not poll.get("is_open", True):
        bot.answer_callback_query(call.id, "🛑 পোলটি বন্ধ হয়ে গেছে!", show_alert=True)
        return

    try:
        ch_member = bot.get_chat_member(poll["channel_id"], vid)
        if ch_member.status in ["left", "kicked"]:
            bot.answer_callback_query(call.id, "⚠️ ভোট দিতে হলে আগে এই চ্যানেলে জয়েন করুন!", show_alert=True)
            return
    except Exception:
        pass

    for o in poll["options"]:
        if vid in o["voters"]:
            bot.answer_callback_query(call.id, "⚠️ আপনি ইতোমধ্যে ভোট দিয়েছেন! পরিবর্তন করতে চ্যানেলের পোস্টে 'ভোট প্রত্যাহার করুন' চাপুন।", show_alert=True)
            return

    poll["options"][opt_idx]["voters"].append(vid)
    if not from_direct:
        poll["message_id"] = call.message.message_id
    save_db(db)

    chosen_name = poll["options"][opt_idx]["name"]
    cand_total = len(poll["options"][opt_idx]["voters"])
    poll_total = sum(len(o["voters"]) for o in poll["options"])
    bot.answer_callback_query(call.id, f"✅ আপনার ভোট '{chosen_name}'-কে যুক্ত হয়েছে!", show_alert=True)

    refresh_channel_poll_message(pid)

    uname = f"@{voter.username}" if voter.username else "No Username"
    creator_notify = (
        f"👷 <b>ভোট দিয়েছেন:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>নাম :</b> {voter.first_name}\n"
        f"🔰 <b>ইউজারনেম :</b> {uname}\n"
        f"🆔 <b>ইউজার আইডি :</b> <code>{vid}</code>\n"
        f"📌 <b>ভোট দিয়েছে :</b> {chosen_name} (মোট ভোট: {cand_total} জন)\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    try:
        bot.send_message(poll["owner_id"], creator_notify)
    except Exception:
        pass

    breakdown = "\n".join([f"   • {o['name']}: <b>{len(o['voters'])}</b> ভোট" for o in poll["options"]])
    channel_report = (
        f"📊 <b>লাইভ ভোট আপডেট (Poll #{pid})</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📢 <b>চ্যানেল:</b> {poll['channel_title']} ({poll['channel_username']})\n"
        f"👑 <b>পোল ক্রিয়েটর:</b> {poll['owner_name']} (<code>{poll['owner_id']}</code>)\n"
        f"🙋‍♂️ <b>ভোটার:</b> {voter.first_name} ({uname} | <code>{vid}</code>)\n"
        f"📌 <b>ভোট পেয়েছেন:</b> {chosen_name}\n\n"
        f"📈 <b>বর্তমান ভোটের হিসাব (মোট {poll_total} ভোট):</b>\n"
        f"{breakdown}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    send_log_to_channel(channel_report)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pclosed:"))
def cb_poll_closed(call):
    bot.answer_callback_query(call.id, "🛑 এই পোলটি বন্ধ হয়ে গেছে!", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pvote:"))
def cb_cast_poll_vote(call):
    parts = call.data.split(":")
    pid, opt_idx = parts[1], int(parts[2])
    process_vote_action(call, pid, opt_idx, from_direct=False)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pwithdraw:"))
def cb_withdraw_vote(call):
    pid = call.data.split(":")[1]
    vid = call.from_user.id
    poll = db["polls"].get(pid)
    if not poll or not poll.get("is_open", True):
        return

    removed_from = None
    for o in poll["options"]:
        if vid in o["voters"]:
            o["voters"].remove(vid)
            removed_from = o["name"]
            break

    if not removed_from:
        bot.answer_callback_query(call.id, "⚠️ আপনি এখনো এই পোলে কোনো ভোট দেননি!", show_alert=True)
        return

    save_db(db)
    bot.answer_callback_query(call.id, f"🔄 '{removed_from}' থেকে আপনার ভোট প্রত্যাহার করা হয়েছে!", show_alert=True)
    refresh_channel_poll_message(pid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pclose:"))
def cb_close_poll_from_channel(call):
    pid = call.data.split(":")[1]
    poll = db["polls"].get(pid)
    if not poll:
        return
    if call.from_user.id != poll["owner_id"] and call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "🚫 শুধুমাত্র পোল ক্রিয়েটর বা অ্যাডমিন পোলটি বন্ধ করতে পারবেন!", show_alert=True)
        return

    poll["is_open"] = False
    poll["close_at"] = None
    save_db(db)
    bot.answer_callback_query(call.id, "🛑 পোলটি বন্ধ করে দেওয়া হয়েছে!", show_alert=True)
    refresh_channel_poll_message(pid)

# ================= FULL EDIT POLLS MENU (ADD, REMOVE, QUESTION, WINNER, CLOSE, DELETE) =================
@bot.message_handler(func=lambda m: m.text in [TEXTS["bn"]["btn_edit"], TEXTS["en"]["btn_edit"]])
def menu_edit_polls(message):
    if not passes_gate(message):
        return
    uid = message.from_user.id
    my_polls = [p for p in db["polls"].values() if p["owner_id"] == uid]
    if not my_polls:
        bot.send_message(message.chat.id, "📭 আপনি এখনো কোনো পোল তৈরি করেননি।")
        return

    lines = ["✏️ <b>আপনার তৈরি করা পোলসমূহ (এডিট করতে বাটনে চাপুন):</b>\n"]
    markup = types.InlineKeyboardMarkup(row_width=2)
    for p in my_polls[-10:]:
        st = "🟢 চালু" if p.get("is_open", True) else "🔴 বন্ধ"
        tv = sum(len(o["voters"]) for o in p["options"])
        cands = ", ".join(o["name"] for o in p["options"])
        lines.append(
            f"🆔 <b>#{p['id']}</b> ({st}) — {p['channel_username']}\n"
            f"👥 প্রার্থী ({len(p['options'])}): {cands[:45]}\n"
            f"📈 মোট ভোট: <b>{tv}</b>\n"
        )
        btn_txt = f"🛑 বন্ধ #{p['id']}" if p.get("is_open", True) else f"🟢 চালু #{p['id']}"
        markup.add(
            types.InlineKeyboardButton(f"➕ নাম যোগ #{p['id']}", callback_data=f"editadd:{p['id']}"),
            types.InlineKeyboardButton(f"➖ নাম বাদ #{p['id']}", callback_data=f"editrem:{p['id']}")
        )
        markup.add(
            types.InlineKeyboardButton(f"📝 প্রশ্ন এডিট #{p['id']}", callback_data=f"editq:{p['id']}"),
            types.InlineKeyboardButton(f"🏆 উইনার ঘোষণা #{p['id']}", callback_data=f"editwin:{p['id']}")
        )
        markup.add(
            types.InlineKeyboardButton(btn_txt, callback_data=f"edittoggle:{p['id']}"),
            types.InlineKeyboardButton(f"🗑 ডিলিট #{p['id']}", callback_data=f"editdel:{p['id']}")
        )
    bot.send_message(message.chat.id, "\n".join(lines), reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("editadd:"))
def cb_edit_add_candidate(call):
    pid = call.data.split(":")[1]
    poll = db["polls"].get(pid)
    if not poll or (call.from_user.id != poll["owner_id"] and call.from_user.id != ADMIN_ID):
        return
    uid = call.from_user.id
    user_states[uid] = f"adding_cand:{pid}"
    bot.send_message(
        call.message.chat.id,
        f"➕ <b>পোল #{pid}-এ নতুন প্রার্থীর নাম যোগ করুন:</b>\n\n"
        f"একজন বা একাধিক নাম যোগ করতে চাইলে মাঝে <code>&amp;</code> দিয়ে লিখুন:",
        reply_markup=cancel_keyboard(uid)
    )

@bot.message_handler(func=lambda m: str(user_states.get(m.from_user.id, "")).startswith("adding_cand:"), content_types=["text"])
def process_add_candidate(message):
    uid = message.from_user.id
    pid = user_states.pop(uid).split(":")[1]
    poll = db["polls"].get(pid)
    if not poll:
        return

    new_names = [n.strip() for n in message.text.split("&") if n.strip()]
    if not new_names:
        bot.send_message(message.chat.id, "❌ সঠিক নাম লিখুন!", reply_markup=main_menu_keyboard(uid))
        return
    if len(poll["options"]) + len(new_names) > 30:
        bot.send_message(message.chat.id, "❌ একটি পোলে সর্বোচ্চ ৩০ জনের বেশি প্রার্থী রাখা যাবে না!", reply_markup=main_menu_keyboard(uid))
        return

    for name in new_names:
        poll["options"].append({"name": name, "voters": []})
    save_db(db)
    refresh_channel_poll_message(pid)
    bot.send_message(
        message.chat.id,
        f"✅ পোল <b>#{pid}</b>-এ নতুন নাম (<b>{', '.join(new_names)}</b>) যুক্ত করা হয়েছে!",
        reply_markup=main_menu_keyboard(uid)
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("editrem:"))
def cb_edit_remove_menu(call):
    pid = call.data.split(":")[1]
    poll = db["polls"].get(pid)
    if not poll or (call.from_user.id != poll["owner_id"] and call.from_user.id != ADMIN_ID):
        return
    if len(poll["options"]) <= 1:
        bot.answer_callback_query(call.id, "⚠️ অন্তত ১ জন প্রার্থী রাখতেই হবে!", show_alert=True)
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for idx, o in enumerate(poll["options"]):
        markup.add(types.InlineKeyboardButton(f"❌ বাদ দিন: {o['name']} ({len(o['voters'])} ভোট)", callback_data=f"remopt:{pid}:{idx}"))
    bot.send_message(call.message.chat.id, f"➖ <b>পোল #{pid} থেকে যে প্রার্থীকে বাদ দিতে চান তাতে চাপুন:</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("remopt:"))
def cb_confirm_remove_opt(call):
    parts = call.data.split(":")
    pid, idx = parts[1], int(parts[2])
    poll = db["polls"].get(pid)
    if not poll or (call.from_user.id != poll["owner_id"] and call.from_user.id != ADMIN_ID):
        return
    if len(poll["options"]) <= 1 or idx >= len(poll["options"]):
        bot.answer_callback_query(call.id, "⚠️ বাদ দেওয়া সম্ভব নয়!", show_alert=True)
        return
    removed = poll["options"].pop(idx)
    save_db(db)
    refresh_channel_poll_message(pid)
    bot.answer_callback_query(call.id, f"🗑 '{removed['name']}'-কে পোল থেকে বাদ দেওয়া হয়েছে!", show_alert=True)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("editq:"))
def cb_edit_question(call):
    pid = call.data.split(":")[1]
    poll = db["polls"].get(pid)
    if not poll or (call.from_user.id != poll["owner_id"] and call.from_user.id != ADMIN_ID):
        return
    uid = call.from_user.id
    user_states[uid] = f"editing_q:{pid}"
    bot.send_message(call.message.chat.id, f"📝 <b>পোল #{pid}-এর নতুন প্রশ্ন/শিরোনাম লিখে পাঠান:</b>", reply_markup=cancel_keyboard(uid))

@bot.message_handler(func=lambda m: str(user_states.get(m.from_user.id, "")).startswith("editing_q:"), content_types=["text"])
def process_edit_question(message):
    uid = message.from_user.id
    pid = user_states.pop(uid).split(":")[1]
    poll = db["polls"].get(pid)
    if not poll:
        return
    poll["question"] = message.text.strip()
    save_db(db)
    refresh_channel_poll_message(pid)
    bot.send_message(message.chat.id, f"✅ পোল <b>#{pid}</b>-এর প্রশ্ন সফলভাবে আপডেট করা হয়েছে!", reply_markup=main_menu_keyboard(uid))

@bot.callback_query_handler(func=lambda c: c.data.startswith("editwin:"))
def cb_edit_winner(call):
    pid = call.data.split(":")[1]
    poll = db["polls"].get(pid)
    if not poll or (call.from_user.id != poll["owner_id"] and call.from_user.id != ADMIN_ID):
        return
    announce_poll_winner(pid, auto_closed=False)
    bot.answer_callback_query(call.id, "🏆 চ্যানেলে উইনার রেজাল্ট পোস্ট করা হয়েছে!", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("edittoggle:"))
def cb_edit_toggle(call):
    pid = call.data.split(":")[1]
    poll = db["polls"].get(pid)
    if not poll or (call.from_user.id != poll["owner_id"] and call.from_user.id != ADMIN_ID):
        return
    poll["is_open"] = not poll.get("is_open", True)
    save_db(db)
    refresh_channel_poll_message(pid)
    bot.answer_callback_query(call.id, f"পোল #{pid} স্ট্যাটাস আপডেট করা হয়েছে!", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("editdel:"))
def cb_edit_delete(call):
    pid = call.data.split(":")[1]
    poll = db["polls"].get(pid)
    if not poll or (call.from_user.id != poll["owner_id"] and call.from_user.id != ADMIN_ID):
        return
    del db["polls"][pid]
    save_db(db)
    bot.answer_callback_query(call.id, f"🗑 পোল #{pid} মুছে ফেলা হয়েছে!", show_alert=True)

# ================= ADMIN PANEL & VIP BYPASS =================
def grant_vip(tid):
    tid = int(tid)
    if tid not in db["vip_users"]:
        db["vip_users"].append(tid)
        save_db(db)
    try:
        bot.send_message(tid, "👑 অ্যাডমিন আপনাকে <b>VIP Direct Access 🔓</b> দিয়েছেন! /start চাপুন।")
    except Exception:
        pass

@bot.message_handler(commands=["vip"])
def cmd_vip(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.reply_to(message, "ব্যবহার: <code>/vip 123456789</code>")
        return
    grant_vip(int(parts[1]))
    bot.reply_to(message, f"✅ User ID <code>{parts[1]}</code>-কে VIP Access দেওয়া হয়েছে!")

@bot.message_handler(commands=["unvip"])
def cmd_unvip(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.reply_to(message, "ব্যবহার: <code>/unvip 123456789</code>")
        return
    tid = int(parts[1])
    if tid in db["vip_users"]:
        db["vip_users"].remove(tid)
        save_db(db)
    bot.reply_to(message, f"🔒 User ID <code>{tid}</code>-এর VIP Access বাতিল করা হয়েছে।")

@bot.message_handler(commands=["setlog"])
def cmd_setlog(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "ব্যবহার: <code>/setlog @optchannel6</code>")
        return
    db["log_channel"] = parts[1].strip()
    save_db(db)
    bot.reply_to(message, f"✅ লগ চ্যানেল সেট হয়েছে: <code>{db['log_channel']}</code>")

@bot.message_handler(commands=["admin"])
@bot.message_handler(func=lambda m: m.text in [TEXTS["bn"]["btn_admin"], TEXTS["en"]["btn_admin"]] and m.from_user.id == ADMIN_ID)
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Live Stats", callback_data="adm:stats"),
        types.InlineKeyboardButton("👥 Users & Referrals", callback_data="adm:users"),
        types.InlineKeyboardButton("🗳 All Polls & Votes", callback_data="adm:polls"),
        types.InlineKeyboardButton("🔓 Give VIP Access", callback_data="adm:add_vip"),
        types.InlineKeyboardButton("🔒 Remove VIP", callback_data="adm:rem_vip"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="adm:broadcast")
    )
    bot.send_message(message.chat.id, "👑 <b>Rafim Ultimate Admin Control Panel</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm:") and c.from_user.id == ADMIN_ID)
def cb_admin(call):
    act = call.data.split(":")[1]
    if act == "stats":
        total_u = len(db["users"])
        total_p = len(db["polls"])
        total_v = sum(sum(len(o["voters"]) for o in p["options"]) for p in db["polls"].values())
        bot.send_message(
            ADMIN_ID,
            f"📊 <b>Live Statistics</b>\n\n"
            f"👥 Total Users: <code>{total_u}</code>\n"
            f"👑 VIP Users: <code>{len(db['vip_users'])}</code>\n"
            f"🗳 Total Polls: <code>{total_p}</code>\n"
            f"❤️ Total Votes: <code>{total_v}</code>\n"
            f"📢 Log Channel: <code>{db.get('log_channel') or DEFAULT_LOG_CHANNEL}</code>"
        )
    elif act == "users":
        lines = ["👥 <b>Recent Users & Referrals:</b>\n"]
        for u in list(db["users"].values())[-25:]:
            st = "👑" if int(u["id"]) in db["vip_users"] else ("🔓" if u.get("referrals", 0) >= 1 else "🔒")
            lines.append(f"{st} <b>{u['name']}</b> ({u['username']}) | ID: <code>{u['id']}</code> | Refs: <b>{u.get('referrals', 0)}</b>")
        bot.send_message(ADMIN_ID, "\n".join(lines))
    elif act == "polls":
        if not db["polls"]:
            bot.send_message(ADMIN_ID, "কোনো পোল নেই।")
            return
        lines = ["🗳 <b>All Channel Polls:</b>\n"]
        for p in list(db["polls"].values())[-15:]:
            tv = sum(len(o["voters"]) for o in p["options"])
            lines.append(f"🆔 <b>#{p['id']}</b> | Ch: {p['channel_username']} | By: {p['owner_name']} (<code>{p['owner_id']}</code>) | Votes: <b>{tv}</b>")
        bot.send_message(ADMIN_ID, "\n".join(lines))
    elif act == "add_vip":
        user_states[ADMIN_ID] = "adm_vip"
        bot.send_message(ADMIN_ID, "🔓 VIP Access দেওয়ার জন্য ইউজারের <b>User ID</b> লিখুন:")
    elif act == "rem_vip":
        user_states[ADMIN_ID] = "adm_unvip"
        bot.send_message(ADMIN_ID, "🔒 VIP বাতিল করার জন্য ইউজারের <b>User ID</b> লিখুন:")
    elif act == "broadcast":
        user_states[ADMIN_ID] = "adm_bc"
        bot.send_message(ADMIN_ID, "📢 সব ইউজারকে পাঠানোর জন্য ব্রডকাস্ট মেসেজ লিখুন:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID) in ["adm_vip", "adm_unvip", "adm_bc"])
def handle_admin_text(message):
    st = user_states.pop(ADMIN_ID)
    txt = message.text.strip()
    if st == "adm_vip" and txt.isdigit():
        grant_vip(int(txt))
        bot.reply_to(message, f"✅ <code>{txt}</code>-কে VIP Access দেওয়া হয়েছে!")
    elif st == "adm_unvip" and txt.isdigit():
        tid = int(txt)
        if tid in db["vip_users"]:
            db["vip_users"].remove(tid)
            save_db(db)
        bot.reply_to(message, f"🔒 <code>{txt}</code>-এর VIP Access বাতিল করা হয়েছে।")
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
    return "Channel Vote Maker (@Votemaker5bot) Pro Edition is Live 24/7!", 200

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
            bot.set_webhook(url=f"{RENDER_URL}/{BOT_TOKEN}")
    except Exception as e:
        print("Webhook error:", e)

if __name__ == "__main__":
    threading.Thread(target=auto_close_watcher, daemon=True).start()
    if RENDER_URL:
        threading.Thread(target=setup_webhook_async, daemon=True).start()
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)
    else:
        bot.remove_webhook()
        time.sleep(1)
        bot.infinity_polling(skip_pending=True)
