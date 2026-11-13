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
temp_campaign_data = {}

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "vip_users" not in data:
                data["vip_users"] = []
            return data
    return {
        "log_channel": os.environ.get("LOG_CHANNEL", ""),
        "vip_users": [],
        "users": {},
        "campaigns": {},
        "campaign_counter": 100
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
            "🔒 <b>বটটি বর্তমানে লক করা আছে!</b>\n\n"
            "এই বটের সকল ফিচার আনলক ও ব্যবহার করতে হলে আপনাকে কমপক্ষে <b>১ জন বন্ধুকে</b> রেফার করতে হবে।\n\n"
            "🔗 <b>আপনার পার্সোনাল রেফারেল লিংক:</b>\n<code>{ref_link}</code>\n\n"
            "👥 <b>বর্তমান রেফার:</b> <code>{refs}/1</code>\n\n"
            "১টি রেফার সম্পন্ন হলেই নিচের <b>🔄 Check Unlock</b> বাটনে ক্লিক করুন!"
        ),
        "check_unlock_btn": "🔄 Check Unlock / আনলক যাচাই করুন",
        "still_locked_alert": "❌ আপনার এখনো ১টি রেফার পূর্ণ হয়নি! আপনার লিংকটি বন্ধুদের শেয়ার করুন।",
        "welcome": (
            "👋 আসসালামু আলাইকুম <b>{name}</b>!\n\n"
            "🏆 <b>Channel Vote Maker</b>-এ আপনাকে স্বাগতম।\n"
            "আপনার অ্যাকাউন্ট সম্পূর্ণ <b>আনলকড 🔓</b>। নিচের মেনু ব্যবহার করে আপনার চ্যানেলের জন্য লাইভ ভোটিং পোস্ট তৈরি করুন!\n\n"
            "👥 <b>মোট রেফার:</b> {refs} জন"
        ),
        "btn_create": "🗳️ ভোট পোস্ট তৈরি করুন",
        "btn_my_posts": "📊 আমার ভোট ক্যাম্পেইন",
        "btn_refer": "🔗 রেফার ও ইনভাইট",
        "btn_lang": "🌐 ভাষা (Language)",
        "btn_support": "🆘 সাপোর্ট",
        "btn_admin": "👑 Admin Panel",
        "refer_info": (
            "🔗 <b>আপনার পার্সোনাল রেফারেল ড্যাশবোর্ড</b>\n\n"
            "📎 <b>রেফারেল লিংক:</b>\n<code>{ref_link}</code>\n\n"
            "👥 <b>মোট সফল রেফার:</b> {refs} জন\n"
            "🔓 <b>অ্যাকাউন্ট স্ট্যাটাস:</b> আনলকড ✅"
        ),
        "ask_channel": (
            "📢 <b>ধাপ ১/২: চ্যানেল যুক্ত করুন</b>\n\n"
            "আপনি যে চ্যানেলে ভোট পোস্টটি নিতে চান, প্রথমে <b>এই বটটিকে ওই চ্যানেলে Admin বানান</b> (Post Messages পারমিশনসহ)।\n\n"
            "এরপর আপনার চ্যানেলের <b>@username</b> (যেমন: <code>@mychannel</code>) অথবা প্রাইভেট চ্যানেলের <b>Channel ID</b> (যেমন: <code>-1001234567890</code>) লিখে পাঠান:\n\n"
            "❌ বাতিল করতে <code>/cancel</code> লিখুন।"
        ),
        "not_bot_admin": (
            "❌ <b>বটটি ওই চ্যানেলে Admin নয় বা চ্যানেলটি খুঁজে পাওয়া যায়নি!</b>\n\n"
            "দয়া করে আগে বটটিকে আপনার চ্যানেলে <b>Admin</b> হিসেবে অ্যাড করুন এবং তারপর আবার চ্যানেলের <code>@username</code> বা ID পাঠান:"
        ),
        "ask_title": (
            "✅ চ্যানেল ভেরিফাই সফল হয়েছে: <b>{ch_title}</b>!\n\n"
            "📝 <b>ধাপ ২/২: ভোটের বিবরণ দিন</b>\n"
            "এখন আপনার ভোট ক্যাম্পেইনের <b>টাইটেল ও বিবরণ</b> লিখে পাঠান (অথবা একটি ছবিসহ ক্যাপশন পাঠান):"
        ),
        "post_created": (
            "🎉 <b>অভিনন্দন! আপনার ভোটিং পোস্ট সরাসরি চ্যানেলে পাবলিশ হয়ে গেছে!</b>\n\n"
            "🆔 <b>Campaign ID:</b> <code>#{cid}</code>\n"
            "📢 <b>Channel:</b> {ch_title}\n"
            "📌 <b>শিরোনাম:</b> {title}\n"
            "🔗 <b>Direct Vote Link:</b> {vote_link}"
        ),
        "vote_btn": "❤️ ভোট দিন ({count})",
        "closed_btn": "🛑 ভোটিং বন্ধ ({count})",
        "share_btn": "📤 শেয়ার করুন",
        "voted_ok": "✅ আপনার ভোট সফলভাবে যুক্ত হয়েছে! (মোট ভোট: {count})",
        "already_voted": "⚠️ আপনি ইতোমধ্যে এই ক্যাম্পেইনে ভোট দিয়েছেন!",
        "voting_closed_alert": "🛑 দুঃখিত! এই ক্যাম্পেইনের ভোট গ্রহণ বন্ধ হয়ে গেছে।",
        "camp_not_found": "❌ দুঃখিত, এই ভোট ক্যাম্পেইনটি খুঁজে পাওয়া যায়নি!",
        "no_my_posts": "📭 আপনি এখনো কোনো ভোট ক্যাম্পেইন তৈরি করেননি।",
        "my_posts_header": "📊 <b>আপনার তৈরি করা ভোট ক্যাম্পেইনসমূহ (কন্ট্রোল করতে বাটনে চাপুন):</b>\n\n",
        "support_msg": f"🆘 যেকোনো প্রয়োজনে বা সাপোর্টের জন্য যোগাযোগ করুন:\n👤 Admin: {ADMIN_USERNAME}\n💬 Group: @bdgivewaychat",
        "new_ref_notify": "🎊 <b>অভিনন্দন!</b> আপনার রেফারেল লিংক থেকে <b>{new_user}</b> বটে জয়েন করেছেন!\nআপনার বট এখন <b>আনলকড 🔓</b> হয়ে গেছে! মেনু ওপেন করতে /start চাপুন।",
        "vip_granted": "👑 <b>অভিনন্দন!</b> অ্যাডমিন আপনাকে <b>VIP Direct Access 🔓</b> দিয়েছেন!\nএখন কোনো চ্যানেল জয়েন বা রেফার ছাড়াই আপনি বটের সব ফিচার ব্যবহার করতে পারবেন। মেনু খুলতে /start চাপুন।",
        "cancelled": "❌ বর্তমান প্রক্রিয়াটি বাতিল করা হয়েছে।"
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
            "🔒 <b>The bot is currently locked!</b>\n\n"
            "To unlock and use all features of this bot, you must refer at least <b>1 friend</b>.\n\n"
            "🔗 <b>Your Personal Referral Link:</b>\n<code>{ref_link}</code>\n\n"
            "👥 <b>Current Referrals:</b> <code>{refs}/1</code>\n\n"
            "Once you get 1 referral, click <b>🔄 Check Unlock</b> below!"
        ),
        "check_unlock_btn": "🔄 Check Unlock",
        "still_locked_alert": "❌ You still have 0 referrals! Share your referral link with a friend first.",
        "welcome": (
            "👋 Welcome <b>{name}</b>!\n\n"
            "🏆 Welcome to <b>Channel Vote Maker</b>.\n"
            "Your account is <b>Unlocked 🔓</b>. Use the menu below to create live voting polls for your channel!\n\n"
            "👥 <b>Total Referrals:</b> {refs}"
        ),
        "btn_create": "🗳️ Create Vote Post",
        "btn_my_posts": "📊 My Vote Campaigns",
        "btn_refer": "🔗 Refer & Invite",
        "btn_lang": "🌐 Language (ভাষা)",
        "btn_support": "🆘 Support",
        "btn_admin": "👑 Admin Panel",
        "refer_info": (
            "🔗 <b>Your Personal Referral Dashboard</b>\n\n"
            "📎 <b>Referral Link:</b>\n<code>{ref_link}</code>\n\n"
            "👥 <b>Total Referrals:</b> {refs}\n"
            "🔓 <b>Account Status:</b> Unlocked ✅"
        ),
        "ask_channel": (
            "📢 <b>Step 1/2: Connect Your Channel</b>\n\n"
            "First, <b>add this bot as an Admin</b> in the channel where you want to post the vote (with Post Messages permission).\n\n"
            "Then send your channel <b>@username</b> (e.g., <code>@mychannel</code>) or private <b>Channel ID</b> (e.g., <code>-1001234567890</code>):\n\n"
            "❌ Type <code>/cancel</code> to cancel."
        ),
        "not_bot_admin": (
            "❌ <b>This bot is NOT an Admin in that channel or channel not found!</b>\n\n"
            "Please add the bot as an <b>Admin</b> in your channel first, then send the channel <code>@username</code> or ID again:"
        ),
        "ask_title": (
            "✅ Channel verified: <b>{ch_title}</b>!\n\n"
            "📝 <b>Step 2/2: Campaign Details</b>\n"
            "Now send the <b>Title & Description</b> for your voting campaign (or send a Photo with caption):"
        ),
        "post_created": (
            "🎉 <b>Congratulations! Your voting post has been published directly to your channel!</b>\n\n"
            "🆔 <b>Campaign ID:</b> <code>#{cid}</code>\n"
            "📢 <b>Channel:</b> {ch_title}\n"
            "📌 <b>Title:</b> {title}\n"
            "🔗 <b>Direct Vote Link:</b> {vote_link}"
        ),
        "vote_btn": "❤️ Vote ({count})",
        "closed_btn": "🛑 Voting Closed ({count})",
        "share_btn": "📤 Share",
        "voted_ok": "✅ Your vote has been counted! (Total Votes: {count})",
        "already_voted": "⚠️ You have already voted in this campaign!",
        "voting_closed_alert": "🛑 Sorry! Voting for this campaign has been closed.",
        "camp_not_found": "❌ Sorry, this voting campaign was not found!",
        "no_my_posts": "📭 You haven't created any voting campaigns yet.",
        "my_posts_header": "📊 <b>Your Created Voting Campaigns (Use buttons below to manage):</b>\n\n",
        "support_msg": f"🆘 For any help or support, contact:\n👤 Admin: {ADMIN_USERNAME}\n💬 Group: @bdgivewaychat",
        "new_ref_notify": "🎊 <b>Congratulations!</b> <b>{new_user}</b> joined using your referral link!\nYour bot is now <b>Unlocked 🔓</b>! Press /start to open the menu.",
        "vip_granted": "👑 <b>Congratulations!</b> The Admin has granted you <b>VIP Direct Access 🔓</b>!\nYou can now use all features without joining channels or referring anyone. Press /start to open the menu.",
        "cancelled": "❌ Current operation cancelled."
    }
}

# ================= HELPER FUNCTIONS =================
def get_lang(user_id):
    uid = str(user_id)
    return db["users"].get(uid, {}).get("lang", "bn")

def t(user_id, key):
    lang = get_lang(user_id)
    return TEXTS.get(lang, TEXTS["bn"]).get(key, "")

def is_vip(user_id):
    return user_id == ADMIN_ID or int(user_id) in db.get("vip_users", [])

def is_unlocked(user_id):
    if is_vip(user_id):
        return True
    uid = str(user_id)
    return db["users"].get(uid, {}).get("referrals", 0) >= 1

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

def send_force_join_msg(chat_id, user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHATS:
        markup.add(types.InlineKeyboardButton(f"📢 Join {ch['name']}", url=ch["url"]))
    markup.add(types.InlineKeyboardButton(t(user_id, "verify_btn"), callback_data="verify_join"))
    bot.send_message(chat_id, t(user_id, "force_join"), reply_markup=markup, disable_web_page_preview=True)

def send_lock_screen(chat_id, user_id):
    uid = str(user_id)
    bot_username = bot.get_me().username
    ref_link = f"https://t.me/{bot_username}?start=ref_{uid}"
    refs = db["users"].get(uid, {}).get("referrals", 0)

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📤 Share Referral Link", url=f"https://t.me/share/url?url={ref_link}"),
        types.InlineKeyboardButton(t(user_id, "check_unlock_btn"), callback_data="check_unlock"),
        types.InlineKeyboardButton("🌐 ভাষা / Language", callback_data="open_lang")
    )
    bot.send_message(
        chat_id,
        t(user_id, "bot_locked_screen").format(ref_link=ref_link, refs=refs),
        reply_markup=markup
    )

def main_menu_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(t(user_id, "btn_create"), t(user_id, "btn_my_posts"))
    markup.add(t(user_id, "btn_refer"), t(user_id, "btn_lang"))
    markup.add(t(user_id, "btn_support"))
    if user_id == ADMIN_ID:
        markup.add(t(user_id, "btn_admin"))
    return markup

def send_log_to_channel(text):
    log_ch = db.get("log_channel", "")
    if log_ch:
        try:
            bot.send_message(log_ch, text, disable_web_page_preview=True)
        except Exception as e:
            print("Log channel error:", e)

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
                bot.send_message(
                    int(ref_by),
                    t(int(ref_by), "new_ref_notify").format(new_user=user.first_name)
                )
            except Exception:
                pass
        save_db(db)

        log_msg = (
            f"🆕 <b>New User Started Bot!</b>\n"
            f"👤 <b>Name:</b> {user.first_name}\n"
            f"🔗 <b>Username:</b> {db['users'][uid]['username']}\n"
            f"🆔 <b>User ID:</b> <code>{uid}</code>\n"
            f"👥 <b>Referred By:</b> <code>{ref_by if ref_by else 'Direct'}</code>"
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

def send_welcome_dashboard(chat_id, user):
    if not check_all_joined(user.id):
        send_force_join_msg(chat_id, user.id)
        return
    if not is_unlocked(user.id):
        send_lock_screen(chat_id, user.id)
        return
    uid = str(user.id)
    refs = db["users"][uid]["referrals"]
    vip_badge = " (👑 VIP Access)" if is_vip(user.id) and user.id != ADMIN_ID else ""
    msg = t(user.id, "welcome").format(name=f"{user.first_name}{vip_badge}", refs=refs)
    bot.send_message(chat_id, msg, reply_markup=main_menu_keyboard(user.id))

# ================= COMMANDS & HANDLERS =================
@bot.message_handler(commands=["cancel"])
def handle_cancel(message):
    user_states.pop(message.from_user.id, None)
    temp_campaign_data.pop(message.from_user.id, None)
    bot.reply_to(message, t(message.from_user.id, "cancelled"))

@bot.message_handler(commands=["start"])
def handle_start(message):
    user_states.pop(message.from_user.id, None)
    args = message.text.split()
    payload = args[1] if len(args) > 1 else ""

    ref_by = None
    vote_camp_id = None

    if payload.startswith("ref_"):
        ref_by = payload.replace("ref_", "")
    elif payload.startswith("vote_"):
        vote_camp_id = payload.replace("vote_", "")

    is_new = register_user(message.from_user, ref_by=ref_by)

    if vote_camp_id and vote_camp_id in db["campaigns"]:
        if not check_all_joined(message.from_user.id):
            user_states[message.from_user.id] = f"pending_vote:{vote_camp_id}"
            send_force_join_msg(message.chat.id, message.from_user.id)
            return
        send_campaign_card(message.chat.id, message.from_user.id, vote_camp_id)
        return

    if is_new and not is_vip(message.from_user.id):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🇧🇩 বাংলা", callback_data="setlang:bn"),
            types.InlineKeyboardButton("🇺🇸 English", callback_data="setlang:en")
        )
        bot.send_message(message.chat.id, TEXTS["bn"]["choose_lang"], reply_markup=markup)
        return

    send_welcome_dashboard(message.chat.id, message.from_user)

@bot.callback_query_handler(func=lambda call: call.data == "open_lang")
def handle_open_lang(call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇧🇩 বাংলা", callback_data="setlang:bn"),
        types.InlineKeyboardButton("🇺🇸 English", callback_data="setlang:en")
    )
    bot.send_message(call.message.chat.id, t(call.from_user.id, "choose_lang"), reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("setlang:"))
def handle_set_lang(call):
    lang = call.data.split(":")[1]
    uid = str(call.from_user.id)
    register_user(call.from_user)
    db["users"][uid]["lang"] = lang
    save_db(db)

    bot.answer_callback_query(call.id, "Language Updated!")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_welcome_dashboard(call.message.chat.id, call.from_user)

@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def handle_verify_join(call):
    if check_all_joined(call.from_user.id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        state = user_states.pop(call.from_user.id, "")
        if state.startswith("pending_vote:"):
            cid = state.split(":")[1]
            send_campaign_card(call.message.chat.id, call.from_user.id, cid)
        else:
            send_welcome_dashboard(call.message.chat.id, call.from_user)
    else:
        bot.answer_callback_query(call.id, t(call.from_user.id, "not_joined"), show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "check_unlock")
def handle_check_unlock(call):
    if not check_all_joined(call.from_user.id):
        bot.answer_callback_query(call.id, t(call.from_user.id, "not_joined"), show_alert=True)
        send_force_join_msg(call.message.chat.id, call.from_user.id)
        return
    if is_unlocked(call.from_user.id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        send_welcome_dashboard(call.message.chat.id, call.from_user)
    else:
        bot.answer_callback_query(call.id, t(call.from_user.id, "still_locked_alert"), show_alert=True)

def passes_security_gate(message):
    uid = message.from_user.id
    if not check_all_joined(uid):
        send_force_join_msg(message.chat.id, uid)
        return False
    if not is_unlocked(uid):
        send_lock_screen(message.chat.id, uid)
        return False
    return True

@bot.message_handler(func=lambda m: m.text in [TEXTS["bn"]["btn_lang"], TEXTS["en"]["btn_lang"]])
def menu_language(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇧🇩 বাংলা", callback_data="setlang:bn"),
        types.InlineKeyboardButton("🇺🇸 English", callback_data="setlang:en")
    )
    bot.reply_to(message, t(message.from_user.id, "choose_lang"), reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in [TEXTS["bn"]["btn_support"], TEXTS["en"]["btn_support"]])
def menu_support(message):
    if not passes_security_gate(message):
        return
    bot.reply_to(message, t(message.from_user.id, "support_msg"), disable_web_page_preview=True)

@bot.message_handler(func=lambda m: m.text in [TEXTS["bn"]["btn_refer"], TEXTS["en"]["btn_refer"]])
def menu_refer(message):
    if not passes_security_gate(message):
        return
    uid = str(message.from_user.id)
    bot_username = bot.get_me().username
    ref_link = f"https://t.me/{bot_username}?start=ref_{uid}"
    refs = db["users"][uid]["referrals"]
    bot.reply_to(message, t(message.from_user.id, "refer_info").format(ref_link=ref_link, refs=refs))

@bot.message_handler(func=lambda m: m.text in [TEXTS["bn"]["btn_create"], TEXTS["en"]["btn_create"]])
def menu_create_vote(message):
    if not passes_security_gate(message):
        return
    user_states[message.from_user.id] = "awaiting_target_channel"
    bot.reply_to(message, t(message.from_user.id, "ask_channel"))

@bot.message_handler(func=lambda m: user_states.get(m.from_user.id) == "awaiting_target_channel", content_types=["text"])
def process_target_channel(message):
    if message.text.strip() == "/cancel":
        handle_cancel(message)
        return

    target_ch = message.text.strip()
    if "t.me/" in target_ch:
        target_ch = "@" + target_ch.split("t.me/")[-1].strip("/")

    try:
        bot_id = bot.get_me().id
        chat_info = bot.get_chat(target_ch)
        bot_member = bot.get_chat_member(chat_info.id, bot_id)
        if bot_member.status not in ["administrator", "creator"]:
            bot.reply_to(message, t(message.from_user.id, "not_bot_admin"))
            return

        temp_campaign_data[message.from_user.id] = {
            "channel_id": chat_info.id,
            "channel_username": f"@{chat_info.username}" if chat_info.username else str(chat_info.id),
            "channel_title": chat_info.title or target_ch
        }
        user_states[message.from_user.id] = "awaiting_campaign_post"
        bot.reply_to(message, t(message.from_user.id, "ask_title").format(ch_title=chat_info.title or target_ch))

    except Exception:
        bot.reply_to(message, t(message.from_user.id, "not_bot_admin"))

@bot.message_handler(
    func=lambda m: user_states.get(m.from_user.id) == "awaiting_campaign_post",
    content_types=["text", "photo"]
)
def process_campaign_creation(message):
    if message.text and message.text.strip() == "/cancel":
        handle_cancel(message)
        return

    uid = str(message.from_user.id)
    ch_data = temp_campaign_data.pop(message.from_user.id, None)
    user_states.pop(message.from_user.id, None)

    if not ch_data:
        return

    db["campaign_counter"] += 1
    cid = str(db["campaign_counter"])

    photo_id = message.photo[-1].file_id if message.content_type == "photo" else None
    title = (message.caption or message.text or "Voting Contest").strip()

    db["campaigns"][cid] = {
        "id": cid,
        "owner_id": message.from_user.id,
        "owner_name": message.from_user.first_name,
        "owner_username": f"@{message.from_user.username}" if message.from_user.username else "No Username",
        "channel_id": ch_data["channel_id"],
        "channel_username": ch_data["channel_username"],
        "channel_title": ch_data["channel_title"],
        "title": title,
        "photo_id": photo_id,
        "voters": [],
        "is_open": True,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    save_db(db)

    bot_username = bot.get_me().username
    vote_link = f"https://t.me/{bot_username}?start=vote_{cid}"

    try:
        send_campaign_card(ch_data["channel_id"], message.from_user.id, cid)
    except Exception as e:
        bot.reply_to(message, f"⚠️ চ্যানেলে পোস্ট করতে সমস্যা হয়েছে: {e}")
        return

    bot.reply_to(
        message,
        t(message.from_user.id, "post_created").format(
            cid=cid,
            ch_title=ch_data["channel_title"],
            title=title,
            vote_link=vote_link
        ),
        disable_web_page_preview=True
    )

    log_text = (
        f"🗳️ <b>New Voting Campaign Created!</b>\n\n"
        f"🆔 <b>Campaign ID:</b> <code>#{cid}</code>\n"
        f"📢 <b>Target Channel:</b> {ch_data['channel_title']} ({ch_data['channel_username']})\n"
        f"🔢 <b>Channel ID:</b> <code>{ch_data['channel_id']}</code>\n"
        f"📌 <b>Title:</b> {title}\n"
        f"👤 <b>Creator:</b> {message.from_user.first_name} ({db['campaigns'][cid]['owner_username']})\n"
        f"🆔 <b>Creator ID:</b> <code>{uid}</code>\n"
        f"🔗 <b>Direct Vote Link:</b> {vote_link}"
    )
    send_log_to_channel(log_text)
    if message.from_user.id != ADMIN_ID:
        try:
            bot.send_message(ADMIN_ID, log_text, disable_web_page_preview=True)
        except Exception:
            pass

def build_campaign_markup(user_id, cid):
    camp = db["campaigns"][cid]
    vote_count = len(camp["voters"])
    is_open = camp.get("is_open", True)
    bot_username = bot.get_me().username
    vote_link = f"https://t.me/{bot_username}?start=vote_{cid}"

    markup = types.InlineKeyboardMarkup(row_width=1)
    if is_open:
        markup.add(
            types.InlineKeyboardButton(t(user_id, "vote_btn").format(count=vote_count), callback_data=f"cast_vote:{cid}"),
            types.InlineKeyboardButton(t(user_id, "share_btn"), url=f"https://t.me/share/url?url={vote_link}")
        )
    else:
        markup.add(
            types.InlineKeyboardButton(t(user_id, "closed_btn").format(count=vote_count), callback_data=f"closed_info:{cid}")
        )
    return markup

def send_campaign_card(chat_id, user_id, cid):
    camp = db["campaigns"].get(cid)
    if not camp:
        bot.send_message(chat_id, t(user_id, "camp_not_found"))
        return

    bot_username = bot.get_me().username
    vote_link = f"https://t.me/{bot_username}?start=vote_{cid}"
    vote_count = len(camp["voters"])
    status_tag = "🟢 LIVE" if camp.get("is_open", True) else "🔴 CLOSED"

    card_text = (
        f"🏆 <b>VOTING CONTEST (#{cid}) [{status_tag}]</b>\n\n"
        f"📌 {camp['title']}\n\n"
        f"👤 <b>Participant:</b> {camp['owner_name']}\n"
        f"❤️ <b>Total Votes:</b> <code>{vote_count}</code>\n"
        f"🔗 <b>Vote Link:</b> {vote_link}"
    )

    markup = build_campaign_markup(user_id, cid)

    if camp.get("photo_id"):
        bot.send_photo(chat_id, camp["photo_id"], caption=card_text, reply_markup=markup)
    else:
        bot.send_message(chat_id, card_text, reply_markup=markup, disable_web_page_preview=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("closed_info:"))
def handle_closed_info(call):
    bot.answer_callback_query(call.id, t(call.from_user.id, "voting_closed_alert"), show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("cast_vote:"))
def handle_cast_vote(call):
    voter_id = call.from_user.id
    cid = call.data.split(":")[1]

    if not check_all_joined(voter_id):
        bot.answer_callback_query(call.id, t(voter_id, "not_joined"), show_alert=True)
        return

    camp = db["campaigns"].get(cid)
    if not camp:
        bot.answer_callback_query(call.id, t(voter_id, "camp_not_found"), show_alert=True)
        return

    if not camp.get("is_open", True):
        bot.answer_callback_query(call.id, t(voter_id, "voting_closed_alert"), show_alert=True)
        return

    if voter_id in camp["voters"]:
        bot.answer_callback_query(call.id, t(voter_id, "already_voted"), show_alert=True)
        return

    register_user(call.from_user)
    camp["voters"].append(voter_id)
    save_db(db)

    new_count = len(camp["voters"])
    bot.answer_callback_query(call.id, t(voter_id, "voted_ok").format(count=new_count), show_alert=True)

    markup = build_campaign_markup(voter_id, cid)
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        pass

    voter_uname = f"@{call.from_user.username}" if call.from_user.username else "No Username"
    vote_log = (
        f"❤️ <b>New Vote Received!</b>\n\n"
        f"🆔 <b>Campaign ID:</b> <code>#{cid}</code> ({camp['title'][:30]})\n"
        f"📢 <b>Channel:</b> {camp.get('channel_title', 'N/A')} (<code>{camp.get('channel_id', '')}</code>)\n"
        f"🏆 <b>Creator:</b> {camp['owner_name']} (<code>{camp['owner_id']}</code>)\n"
        f"🙋‍♂️ <b>Voter:</b> {call.from_user.first_name} ({voter_uname})\n"
        f"🔢 <b>Voter ID:</b> <code>{voter_id}</code>\n"
        f"📊 <b>Updated Total Votes:</b> <code>{new_count}</code>"
    )
    send_log_to_channel(vote_log)

@bot.inline_handler(func=lambda query: True)
def handle_inline_share(inline_query):
    q = inline_query.query.strip()
    cid = q.replace("vote_", "") if q.startswith("vote_") else q
    camp = db["campaigns"].get(cid)
    if not camp:
        return

    bot_username = bot.get_me().username
    vote_link = f"https://t.me/{bot_username}?start=vote_{cid}"
    vote_count = len(camp["voters"])

    share_text = (
        f"🏆 <b>VOTING CONTEST (#{cid})</b>\n\n"
        f"📌 {camp['title']}\n\n"
        f"👤 <b>Participant:</b> {camp['owner_name']}\n"
        f"❤️ <b>Current Votes:</b> <code>{vote_count}</code>\n\n"
        f"👇 নিচের বাটনে ক্লিক করে ভোট দিন:"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"❤️ Vote Now ({vote_count})", url=vote_link))

    result = types.InlineQueryResultArticle(
        id=cid,
        title=f"Share Vote Contest #{cid}: {camp['title'][:30]}",
        description=f"Total Votes: {vote_count}",
        input_message_content=types.InputTextMessageContent(share_text, parse_mode="HTML"),
        reply_markup=markup
    )
    bot.answer_inline_query(inline_query.id, [result], cache_time=1)

@bot.message_handler(func=lambda m: m.text in [TEXTS["bn"]["btn_my_posts"], TEXTS["en"]["btn_my_posts"]])
def menu_my_campaigns(message):
    if not passes_security_gate(message):
        return
    uid = message.from_user.id
    my_camps = [c for c in db["campaigns"].values() if c["owner_id"] == uid]
    if not my_camps:
        bot.reply_to(message, t(uid, "no_my_posts"))
        return

    bot_username = bot.get_me().username
    text = t(uid, "my_posts_header")
    markup = types.InlineKeyboardMarkup(row_width=2)

    for c in my_camps[-10:]:
        v_link = f"https://t.me/{bot_username}?start=vote_{c['id']}"
        st = "🟢 Open" if c.get("is_open", True) else "🔴 Closed"
        text += (
            f"🆔 <b>#{c['id']}</b> [{st}] — {c['title'][:30]}\n"
            f"📢 <b>Channel:</b> {c.get('channel_title', 'N/A')}\n"
            f"❤️ <b>Votes:</b> <code>{len(c['voters'])}</code>\n"
            f"🔗 <code>{v_link}</code>\n\n"
        )
        toggle_label = f"🛑 Close #{c['id']}" if c.get("is_open", True) else f"🟢 Reopen #{c['id']}"
        markup.add(
            types.InlineKeyboardButton(toggle_label, callback_data=f"toggle_camp:{c['id']}"),
            types.InlineKeyboardButton(f"🏆 Winner #{c['id']}", callback_data=f"win_camp:{c['id']}")
        )
    bot.reply_to(message, text, reply_markup=markup, disable_web_page_preview=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_camp:"))
def handle_toggle_campaign(call):
    cid = call.data.split(":")[1]
    camp = db["campaigns"].get(cid)
    if not camp:
        return
    if call.from_user.id != camp["owner_id"] and call.from_user.id != ADMIN_ID:
        return
    camp["is_open"] = not camp.get("is_open", True)
    save_db(db)
    status_str = "Re-opened 🟢" if camp["is_open"] else "Closed 🛑"
    bot.answer_callback_query(call.id, f"Campaign #{cid} {status_str}!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("win_camp:"))
def handle_announce_winner(call):
    cid = call.data.split(":")[1]
    camp = db["campaigns"].get(cid)
    if not camp:
        return
    if call.from_user.id != camp["owner_id"] and call.from_user.id != ADMIN_ID:
        return

    camp["is_open"] = False
    save_db(db)
    total_v = len(camp["voters"])
    win_msg = (
        f"🏆🎉 <b>FINAL RESULT ANNOUNCED (#{cid})</b> 🎉🏆\n\n"
        f"📌 <b>Contest:</b> {camp['title']}\n"
        f"👤 <b>Participant:</b> {camp['owner_name']}\n"
        f"❤️ <b>Final Verified Votes:</b> <code>{total_v}</code>\n"
        f"🛑 <b>Status:</b> Voting Closed"
    )
    try:
        bot.send_message(camp["channel_id"], win_msg)
        bot.answer_callback_query(call.id, "✅ Winner result posted to channel!", show_alert=True)
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Error: {e}", show_alert=True)

def grant_vip_user(target_id):
    target_id = int(target_id)
    if target_id not in db["vip_users"]:
        db["vip_users"].append(target_id)
        save_db(db)
    try:
        bot.send_message(target_id, t(target_id, "vip_granted"))
    except Exception:
        pass

def revoke_vip_user(target_id):
    target_id = int(target_id)
    if target_id in db["vip_users"]:
        db["vip_users"].remove(target_id)
        save_db(db)

@bot.message_handler(commands=["vip"])
def cmd_add_vip(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.reply_to(message, "ব্যবহার: <code>/vip 123456789</code>")
        return
    tid = int(parts[1])
    grant_vip_user(tid)
    bot.reply_to(message, f"✅ User ID <code>{tid}</code>-কে চ্যানেল জয়েন ও রেফার ছাড়াই VIP Direct Access দেওয়া হয়েছে!")

@bot.message_handler(commands=["unvip"])
def cmd_remove_vip(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        bot.reply_to(message, "ব্যবহার: <code>/unvip 123456789</code>")
        return
    tid = int(parts[1])
    revoke_vip_user(tid)
    bot.reply_to(message, f"🔒 User ID <code>{tid}</code>-এর VIP Access বাতিল করা হয়েছে।")

@bot.message_handler(commands=["setlog"])
def set_log_channel(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "ব্যবহার: <code>/setlog @channelusername</code> অথবা <code>/setlog -100xxxxxxxxxx</code>\n(আগে বটকে ওই চ্যানেলে Admin বানান)")
        return
    db["log_channel"] = parts[1].strip()
    save_db(db)
    bot.reply_to(message, f"✅ পাবলিক লগ চ্যানেল সেট করা হয়েছে: <code>{db['log_channel']}</code>")

@bot.message_handler(commands=["admin"])
@bot.message_handler(func=lambda m: m.text in [TEXTS["bn"]["btn_admin"], TEXTS["en"]["btn_admin"]] and m.from_user.id == ADMIN_ID)
def admin_dashboard(message):
    if message.from_user.id != ADMIN_ID:
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Live Stats", callback_data="adm:stats"),
        types.InlineKeyboardButton("👥 Users & Referrals", callback_data="adm:users"),
        types.InlineKeyboardButton("🗳️ Campaigns & Votes", callback_data="adm:campaigns"),
        types.InlineKeyboardButton("🔓 Give VIP Access", callback_data="adm:add_vip"),
        types.InlineKeyboardButton("🔒 Remove VIP Access", callback_data="adm:rem_vip"),
        types.InlineKeyboardButton("📋 VIP List", callback_data="adm:vip_list"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="adm:broadcast"),
        types.InlineKeyboardButton("⚙️ Log Channel Info", callback_data="adm:loginfo")
    )
    bot.send_message(message.chat.id, "👑 <b>Rafim Ultimate Admin Control Panel</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm:") and call.from_user.id == ADMIN_ID)
def admin_callbacks(call):
    action = call.data.split(":")[1]

    if action == "stats":
        total_users = len(db["users"])
        unlocked_users = sum(1 for u in db["users"].values() if u.get("referrals", 0) >= 1)
        vip_count = len(db.get("vip_users", []))
        total_camps = len(db["campaigns"])
        total_votes = sum(len(c["voters"]) for c in db["campaigns"].values())
        msg = (
            f"📊 <b>Bot Live Statistics</b>\n\n"
            f"👥 <b>Total Users:</b> <code>{total_users}</code>\n"
            f"🔓 <b>Referral Unlocked Users:</b> <code>{unlocked_users}</code>\n"
            f"👑 <b>VIP Direct Access Users:</b> <code>{vip_count}</code>\n"
            f"🗳️ <b>Total Vote Campaigns:</b> <code>{total_camps}</code>\n"
            f"❤️ <b>Total Votes Cast:</b> <code>{total_votes}</code>\n"
            f"📢 <b>Log Channel:</b> <code>{db.get('log_channel') or 'Not Set'}</code>"
        )
        bot.send_message(ADMIN_ID, msg)

    elif action == "users":
        if not db["users"]:
            bot.send_message(ADMIN_ID, "কোনো ইউজার নেই।")
            return
        lines = ["👥 <b>Recent Users & Referral Details (Last 25):</b>\n"]
        for u in list(db["users"].values())[-25:]:
            if int(u["id"]) in db.get("vip_users", []):
                st = "👑"
            elif u.get("referrals", 0) >= 1:
                st = "🔓"
            else:
                st = "🔒"
            lines.append(
                f"{st} <b>{u['name']}</b> ({u['username']})\n"
                f"   🆔 <code>{u['id']}</code> | Refs: <b>{u.get('referrals', 0)}</b> | By: <code>{u.get('referred_by') or 'Direct'}</code>"
            )
        bot.send_message(ADMIN_ID, "\n".join(lines))

    elif action == "campaigns":
        if not db["campaigns"]:
            bot.send_message(ADMIN_ID, "এখনো কোনো ক্যাম্পেইন তৈরি হয়নি।")
            return
        lines = ["🗳️ <b>All Voting Campaigns & Voters Info:</b>\n"]
        for c in list(db["campaigns"].values())[-15:]:
            voter_ids = ", ".join(str(v) for v in c["voters"][:10])
            if len(c["voters"]) > 10:
                voter_ids += f" (+{len(c['voters'])-10} more)"
            st = "🟢" if c.get("is_open", True) else "🔴"
            lines.append(
                f"{st} <b>#{c['id']}</b> — {c['title'][:30]}\n"
                f"📢 Ch: {c.get('channel_title', 'N/A')} (<code>{c.get('channel_id', '')}</code>)\n"
                f"👤 Creator: {c['owner_name']} (<code>{c['owner_id']}</code>)\n"
                f"❤️ Total Votes: <b>{len(c['voters'])}</b> | Voters: <code>{voter_ids or 'None'}</code>\n"
            )
        bot.send_message(ADMIN_ID, "\n".join(lines))

    elif action == "add_vip":
        user_states[ADMIN_ID] = "admin_add_vip"
        bot.send_message(ADMIN_ID, "🔓 যে ইউজারকে চ্যানেল জয়েন ও রেফার ছাড়াই ফুল অ্যাক্সেস দিতে চান তার <b>User ID</b> লিখুন:")

    elif action == "rem_vip":
        user_states[ADMIN_ID] = "admin_rem_vip"
        bot.send_message(ADMIN_ID, "🔒 যে ইউজারের VIP Access বাতিল করতে চান তার <b>User ID</b> লিখুন:")

    elif action == "vip_list":
        vips = db.get("vip_users", [])
        if not vips:
            bot.send_message(ADMIN_ID, "বর্তমানে কোনো VIP ইউজার নেই।")
        else:
            vip_str = "\n".join(f"• <code>{vid}</code>" for vid in vips)
            bot.send_message(ADMIN_ID, f"👑 <b>VIP Direct Access Users:</b>\n\n{vip_str}")

    elif action == "broadcast":
        user_states[ADMIN_ID] = "admin_broadcast"
        bot.send_message(ADMIN_ID, "📢 সব ইউজারকে পাঠানোর জন্য ব্রডকাস্ট মেসেজটি লিখুন:")

    elif action == "loginfo":
        bot.send_message(
            ADMIN_ID,
            f"📢 বর্তমান লগ চ্যানেল: <code>{db.get('log_channel') or 'সেট করা নেই'}</code>\n\n"
            f"পরিবর্তন করতে লিখুন:\n<code>/setlog @YourLogChannel</code>"
        )

@bot.message_handler(
    func=lambda m: m.from_user.id == ADMIN_ID and user_states.get(ADMIN_ID) in ["admin_broadcast", "admin_add_vip", "admin_rem_vip"]
)
def handle_admin_inputs(message):
    state = user_states.pop(ADMIN_ID)
    text = message.text.strip()

    if state == "admin_add_vip":
        if not text.isdigit():
            bot.reply_to(message, "❌ সঠিক নিউমেরিক User ID দিন (যেমন: `123456789`)।")
            return
        tid = int(text)
        grant_vip_user(tid)
        bot.reply_to(message, f"✅ User ID <code>{tid}</code>-কে সফলভাবে <b>VIP Direct Access</b> দেওয়া হয়েছে!")

    elif state == "admin_rem_vip":
        if not text.isdigit():
            bot.reply_to(message, "❌ সঠিক নিউমেরিক User ID দিন।")
            return
        tid = int(text)
        revoke_vip_user(tid)
        bot.reply_to(message, f"🔒 User ID <code>{tid}</code>-এর VIP Access বাতিল করা হয়েছে।")

    elif state == "admin_broadcast":
        sent = 0
        for uid in list(db["users"].keys()):
            try:
                bot.send_message(int(uid), f"📢 <b>Announcement:</b>\n\n{text}")
                sent += 1
            except Exception:
                pass
        bot.reply_to(message, f"✅ মোট <b>{sent}</b> জন ইউজারের কাছে মেসেজ পাঠানো হয়েছে!")

# ================= WEBHOOK & SERVER RUNNER =================
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")

@app.route("/")
def home():
    return "Channel Vote Maker Bot is Running 24/7 via Webhook!", 200

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
        print("Webhook setup error:", e)

if __name__ == "__main__":
    if RENDER_URL:
        threading.Thread(target=setup_webhook_async, daemon=True).start()
        port = int(os.environ.get("PORT", 10000))
        app.run(host="0.0.0.0", port=port)
    else:
        bot.remove_webhook()
        time.sleep(1)
        bot.infinity_polling(skip_pending=True)
