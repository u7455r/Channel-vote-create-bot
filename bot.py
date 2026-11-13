import os
import json
import time
import threading
import telebot
from telebot import types
from flask import Flask

# ================= CONFIGURATION =================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "9224149092:AAHO-bMBo-UsquA36EB7ay-f708mk7iaFWw")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8298133943"))
ADMIN_USERNAME = "@rafimhossen"

# ৫টি বাধ্যতামূলক চ্যানেল ও গ্রুপ
REQUIRED_CHATS = [
    {"username": "@optchannel6", "url": "https://t.me/optchannel6", "name": "Opt Channel 6"},
    {"username": "@PremiumApkVaultBD", "url": "https://t.me/PremiumApkVaultBD", "name": "Premium Apk Vault BD"},
    {"username": "@ProApkHub_Official", "url": "https://t.me/ProApkHub_Official", "name": "Pro Apk Hub Official"},
    {"username": "@bdgivewaychat", "url": "https://t.me/bdgivewaychat", "name": "BD Giveaway Chat"},
    {"username": "@bdgiveaways24", "url": "https://t.me/bdgiveaways24", "name": "BD Giveaways 24"},
]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

DB_FILE = "voting_bot_db.json"
db_lock = threading.Lock()
user_states = {}

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "log_channel": os.environ.get("LOG_CHANNEL", ""),
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
        "lang_set": "✅ ভাষা পরিবর্তন করে **বাংলা** করা হয়েছে!",
        "force_join": "⚠️ <b>বটটি ব্যবহার করতে হলে নিচের ৫টি চ্যানেল ও গ্রুপে অবশ্যই জয়েন থাকতে হবে!</b>\n\nসবগুলোতে জয়েন করার পর নিচের <b>✅ Verify / যাচাই করুন</b> বাটনে ক্লিক করুন:",
        "verify_btn": "✅ Verify / যাচাই করুন",
        "not_joined": "❌ আপনি এখনো সব চ্যানেল ও গ্রুপে জয়েন করেননি! দয়া করে সবগুলোতে জয়েন করে আবার চেষ্টা করুন।",
        "welcome": (
            "👋 আসসালামু আলাইকুম <b>{name}</b>!\n\n"
            "🏆 <b>Channel Voting & Contest Maker Bot</b>-এ আপনাকে স্বাগতম।\n"
            "এখান থেকে আপনি নিজের চ্যানেল বা কনটেস্টের জন্য লাইভ ভোটিং পোস্ট তৈরি করতে পারবেন।\n\n"
            "🔓 <b>আনলক স্ট্যাটাস:</b> {status}\n"
            "👥 <b>মোট রেফার:</b> {refs} জন"
        ),
        "unlocked": "আনলকড ✅",
        "locked": "লকড 🔒 (ভোট পোস্ট বানাতে ১টি রেফার প্রয়োজন)",
        "btn_create": "🗳️ ভোট পোস্ট তৈরি করুন",
        "btn_my_posts": "📊 আমার ভোট ক্যাম্পেইন",
        "btn_refer": "🔗 রেফার ও আনলক",
        "btn_lang": "🌐 ভাষা (Language)",
        "btn_support": "🆘 সাপোর্ট",
        "btn_admin": "👑 Admin Panel",
        "need_refer": (
            "🔒 <b>এই ফিচারটি লক করা আছে!</b>\n\n"
            "নিজের চ্যানেল বা কনটেস্টের জন্য ভোট পোস্ট তৈরি করতে হলে আপনাকে কমপক্ষে <b>১ জন বন্ধুকে</b> রেফার করে বটটি আনলক করতে হবে।\n\n"
            "🔗 <b>আপনার রেফারেল লিংক:</b>\n<code>{ref_link}</code>\n\n"
            "👥 বর্তমান রেফার: <b>{refs}/1</b>"
        ),
        "refer_info": (
            "🔗 <b>আপনার পার্সোনাল রেফারেল ড্যাশবোর্ড</b>\n\n"
            "আপনার লিংক শেয়ার করে বন্ধুদের ইনভাইট করুন। মাত্র ১টি সফল রেফার হলেই আপনার অ্যাকাউন্ট আজীবনের জন্য আনলক হয়ে যাবে!\n\n"
            "📎 <b>রেফারেল লিংক:</b>\n<code>{ref_link}</code>\n\n"
            "👥 <b>মোট সফল রেফার:</b> {refs} জন\n"
            "🔓 <b>অ্যাকাউন্ট স্ট্যাটাস:</b> {status}"
        ),
        "ask_title": "📝 আপনার ভোট ক্যাম্পেইন বা চ্যানেলের <b>টাইটেল ও বিবরণ</b> লিখুন (অথবা একটি ছবিসহ ক্যাপশন পাঠান):",
        "post_created": (
            "🎉 <b>আপনার ভোটিং পোস্ট তৈরি হয়ে গেছে!</b>\n\n"
            "🆔 <b>Campaign ID:</b> <code>#{cid}</code>\n"
            "📌 <b>শিরোনাম:</b> {title}\n\n"
            "নিচের বাটনে ক্লিক করে এটি আপনার চ্যানেল বা গ্রুপে শেয়ার করুন এবং ভোট সংগ্রহ শুরু করুন!"
        ),
        "vote_btn": "❤️ ভোট দিন ({count})",
        "share_btn": "📤 চ্যানেলে শেয়ার করুন",
        "voted_ok": "✅ আপনার ভোট সফলভাবে যুক্ত হয়েছে! (মোট ভোট: {count})",
        "already_voted": "⚠️ আপনি ইতোমধ্যে এই ক্যাম্পেইনে ভোট দিয়েছেন!",
        "camp_not_found": "❌ দুঃখিত, এই ভোট ক্যাম্পেইনটি খুঁজে পাওয়া যায়নি!",
        "no_my_posts": "📭 আপনি এখনো কোনো ভোট ক্যাম্পেইন তৈরি করেননি।",
        "my_posts_header": "📊 <b>আপনার তৈরি করা ভোট ক্যাম্পেইনসমূহ:</b>\n\n",
        "support_msg": f"🆘 যেকোনো প্রয়োজনে বা সাপোর্টের জন্য যোগাযোগ করুন:\n👤 Admin: {ADMIN_USERNAME}\n💬 Group: @bdgivewaychat",
        "new_ref_notify": "🎊 <b>অভিনন্দন!</b> আপনার রেফারেল লিংক থেকে <b>{new_user}</b> বটে জয়েন করেছেন!\nআপনার অ্যাকাউন্ট এখন <b>আনলকড 🔓</b> হয়ে গেছে!"
    },
    "en": {
        "choose_lang": "🌐 Please select your language / অনুগ্রহ করে আপনার ভাষা নির্বাচন করুন:",
        "lang_set": "✅ Language has been set to **English**!",
        "force_join": "⚠️ <b>You must join all 5 required channels & groups below to use this bot!</b>\n\nAfter joining all of them, click the <b>✅ Verify</b> button below:",
        "verify_btn": "✅ Verify Joined",
        "not_joined": "❌ You haven't joined all required channels/groups yet! Please join all and try again.",
        "welcome": (
            "👋 Welcome <b>{name}</b>!\n\n"
            "🏆 Welcome to <b>Channel Voting & Contest Maker Bot</b>.\n"
            "Create live voting contests for your channel or group easily.\n\n"
            "🔓 <b>Unlock Status:</b> {status}\n"
            "👥 <b>Total Referrals:</b> {refs}"
        ),
        "unlocked": "Unlocked ✅",
        "locked": "Locked 🔒 (1 Referral required to create vote post)",
        "btn_create": "🗳️ Create Vote Post",
        "btn_my_posts": "📊 My Vote Campaigns",
        "btn_refer": "🔗 Refer & Unlock",
        "btn_lang": "🌐 Language (ভাষা)",
        "btn_support": "🆘 Support",
        "btn_admin": "👑 Admin Panel",
        "need_refer": (
            "🔒 <b>This feature is currently locked!</b>\n\n"
            "To create a voting campaign for your channel, you must refer at least <b>1 friend</b> to unlock the bot.\n\n"
            "🔗 <b>Your Referral Link:</b>\n<code>{ref_link}</code>\n\n"
            "👥 Current Referrals: <b>{refs}/1</b>"
        ),
        "refer_info": (
            "🔗 <b>Your Personal Referral Dashboard</b>\n\n"
            "Share your link and invite friends. Just 1 successful referral unlocks all creation features permanently!\n\n"
            "📎 <b>Referral Link:</b>\n<code>{ref_link}</code>\n\n"
            "👥 <b>Total Referrals:</b> {refs}\n"
            "🔓 <b>Account Status:</b> {status}"
        ),
        "ask_title": "📝 Send the <b>Title & Description</b> for your voting campaign (or send a Photo with caption):",
        "post_created": (
            "🎉 <b>Your Voting Campaign is Live!</b>\n\n"
            "🆔 <b>Campaign ID:</b> <code>#{cid}</code>\n"
            "📌 <b>Title:</b> {title}\n\n"
            "Click the button below to share it in your channel or group and collect votes!"
        ),
        "vote_btn": "❤️ Vote ({count})",
        "share_btn": "📤 Share to Channel",
        "voted_ok": "✅ Your vote has been counted! (Total Votes: {count})",
        "already_voted": "⚠️ You have already voted in this campaign!",
        "camp_not_found": "❌ Sorry, this voting campaign was not found!",
        "no_my_posts": "📭 You haven't created any voting campaigns yet.",
        "my_posts_header": "📊 <b>Your Created Voting Campaigns:</b>\n\n",
        "support_msg": f"🆘 For any help or support, contact:\n👤 Admin: {ADMIN_USERNAME}\n💬 Group: @bdgivewaychat",
        "new_ref_notify": "🎊 <b>Congratulations!</b> <b>{new_user}</b> joined using your referral link!\nYour account is now <b>Unlocked 🔓</b>!"
    }
}

# ================= FLASK KEEP-ALIVE =================
@app.route("/")
def home():
    return "Rafim Ultimate Voting & Contest Bot is Running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ================= HELPER FUNCTIONS =================
def get_lang(user_id):
    uid = str(user_id)
    return db["users"].get(uid, {}).get("lang", "bn")

def t(user_id, key):
    lang = get_lang(user_id)
    return TEXTS.get(lang, TEXTS["bn"]).get(key, "")

def is_unlocked(user_id):
    if user_id == ADMIN_ID:
        return True
    uid = str(user_id)
    return db["users"].get(uid, {}).get("referrals", 0) >= 1

def check_all_joined(user_id):
    if user_id == ADMIN_ID:
        return True
    for chat in REQUIRED_CHATS:
        try:
            member = bot.get_chat_member(chat["username"], user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            # যদি বট চ্যানেলে অ্যাডমিন না থাকে তবে এরর এড়িয়ে যাবে
            continue
    return True

def send_force_join_msg(chat_id, user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHATS:
        markup.add(types.InlineKeyboardButton(f"📢 Join {ch['name']}", url=ch["url"]))
    markup.add(types.InlineKeyboardButton(t(user_id, "verify_btn"), callback_data="verify_join"))
    bot.send_message(chat_id, t(user_id, "force_join"), reply_markup=markup, disable_web_page_preview=True)

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
        # রেফারেল প্রসেসিং
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

        # নতুন ইউজার স্টার্ট করলে অ্যাডমিন ও লগ চ্যানেলে নোটিফিকেশন
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
    uid = str(user.id)
    refs = db["users"][uid]["referrals"]
    status = t(user.id, "unlocked") if is_unlocked(user.id) else t(user.id, "locked")
    msg = t(user.id, "welcome").format(name=user.first_name, status=status, refs=refs)
    bot.send_message(chat_id, msg, reply_markup=main_menu_keyboard(user.id))

# ================= COMMANDS & HANDLERS =================
@bot.message_handler(commands=["start"])
def handle_start(message):
    args = message.text.split()
    payload = args[1] if len(args) > 1 else ""

    ref_by = None
    vote_camp_id = None

    if payload.startswith("ref_"):
        ref_by = payload.replace("ref_", "")
    elif payload.startswith("vote_"):
        vote_camp_id = payload.replace("vote_", "")

    is_new = register_user(message.from_user, ref_by=ref_by)

    # যদি কেউ সরাসরি ভোট লিংকে ক্লিক করে বটে আসে
    if vote_camp_id and vote_camp_id in db["campaigns"]:
        if not check_all_joined(message.from_user.id):
            user_states[message.from_user.id] = f"pending_vote:{vote_camp_id}"
            send_force_join_msg(message.chat.id, message.from_user.id)
            return
        send_campaign_card(message.chat.id, message.from_user.id, vote_camp_id)
        return

    if is_new:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🇧🇩 বাংলা", callback_data="setlang:bn"),
            types.InlineKeyboardButton("🇺🇸 English", callback_data="setlang:en")
        )
        bot.send_message(message.chat.id, TEXTS["bn"]["choose_lang"], reply_markup=markup)
        return

    if not check_all_joined(message.from_user.id):
        send_force_join_msg(message.chat.id, message.from_user.id)
        return

    send_welcome_dashboard(message.chat.id, message.from_user)

@bot.callback_query_handler(func=lambda call: call.data.startswith("setlang:"))
def handle_set_lang(call):
    lang = call.data.split(":")[1]
    uid = str(call.from_user.id)
    register_user(call.from_user)
    db["users"][uid]["lang"] = lang
    save_db(db)

    bot.answer_callback_query(call.id, "Language Updated!")
    bot.delete_message(call.message.chat.id, call.message.message_id)

    if not check_all_joined(call.from_user.id):
        send_force_join_msg(call.message.chat.id, call.from_user.id)
    else:
        send_welcome_dashboard(call.message.chat.id, call.from_user)

@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def handle_verify_join(call):
    if check_all_joined(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        state = user_states.pop(call.from_user.id, "")
        if state.startswith("pending_vote:"):
            cid = state.split(":")[1]
            send_campaign_card(call.message.chat.id, call.from_user.id, cid)
        else:
            send_welcome_dashboard(call.message.chat.id, call.from_user)
    else:
        bot.answer_callback_query(call.id, t(call.from_user.id, "not_joined"), show_alert=True)

# ================= LANGUAGE BUTTON =================
@bot.message_handler(func=lambda m: m.text in [TEXTS["bn"]["btn_lang"], TEXTS["en"]["btn_lang"]])
def menu_language(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇧🇩 বাংলা", callback_data="setlang:bn"),
        types.InlineKeyboardButton("🇺🇸 English", callback_data="setlang:en")
    )
    bot.reply_to(message, t(message.from_user.id, "choose_lang"), reply_markup=markup)

# ================= SUPPORT BUTTON =================
@bot.message_handler(func=lambda m: m.text in [TEXTS["bn"]["btn_support"], TEXTS["en"]["btn_support"]])
def menu_support(message):
    bot.reply_to(message, t(message.from_user.id, "support_msg"), disable_web_page_preview=True)

# ================= REFER & UNLOCK BUTTON =================
@bot.message_handler(func=lambda m: m.text in [TEXTS["bn"]["btn_refer"], TEXTS["en"]["btn_refer"]])
def menu_refer(message):
    if not check_all_joined(message.from_user.id):
        send_force_join_msg(message.chat.id, message.from_user.id)
        return
    uid = str(message.from_user.id)
    bot_username = bot.get_me().username
    ref_link = f"https://t.me/{bot_username}?start=ref_{uid}"
    refs = db["users"][uid]["referrals"]
    status = t(message.from_user.id, "unlocked") if is_unlocked(message.from_user.id) else t(message.from_user.id, "locked")
    bot.reply_to(
        message,
        t(message.from_user.id, "refer_info").format(ref_link=ref_link, refs=refs, status=status)
    )

# ================= CREATE VOTE CAMPAIGN =================
@bot.message_handler(func=lambda m: m.text in [TEXTS["bn"]["btn_create"], TEXTS["en"]["btn_create"]])
def menu_create_vote(message):
    if not check_all_joined(message.from_user.id):
        send_force_join_msg(message.chat.id, message.from_user.id)
        return
    uid = str(message.from_user.id)
    if not is_unlocked(message.from_user.id):
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start=ref_{uid}"
        refs = db["users"][uid]["referrals"]
        bot.reply_to(
            message,
            t(message.from_user.id, "need_refer").format(ref_link=ref_link, refs=refs)
        )
        return

    user_states[message.from_user.id] = "awaiting_campaign_post"
    bot.reply_to(message, t(message.from_user.id, "ask_title"))

@bot.message_handler(
    func=lambda m: user_states.get(m.from_user.id) == "awaiting_campaign_post",
    content_types=["text", "photo"]
)
def process_campaign_creation(message):
    user_states.pop(message.from_user.id, None)
    uid = str(message.from_user.id)

    db["campaign_counter"] += 1
    cid = str(db["campaign_counter"])

    photo_id = message.photo[-1].file_id if message.content_type == "photo" else None
    title = (message.caption or message.text or "Voting Contest").strip()

    db["campaigns"][cid] = {
        "id": cid,
        "owner_id": message.from_user.id,
        "owner_name": message.from_user.first_name,
        "owner_username": f"@{message.from_user.username}" if message.from_user.username else "No Username",
        "title": title,
        "photo_id": photo_id,
        "voters": [],
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    save_db(db)

    bot_username = bot.get_me().username
    vote_link = f"https://t.me/{bot_username}?start=vote_{cid}"

    # ইউজারকে কনফার্মেশন ও শেয়ার কার্ড পাঠানো
    bot.reply_to(message, t(message.from_user.id, "post_created").format(cid=cid, title=title))
    send_campaign_card(message.chat.id, message.from_user.id, cid)

    # পাবলিক লগ চ্যানেল ও অ্যাডমিনের কাছে ফুল ডিটেইলস পাঠানো
    log_text = (
        f"🗳️ <b>New Voting Campaign Created!</b>\n\n"
        f"🆔 <b>Campaign ID:</b> <code>#{cid}</code>\n"
        f"📌 <b>Title:</b> {title}\n"
        f"👤 <b>Creator:</b> {message.from_user.first_name} ({db['campaigns'][cid]['owner_username']})\n"
        f"🔢 <b>Creator ID:</b> <code>{uid}</code>\n"
        f"🔗 <b>Direct Vote Link:</b> {vote_link}"
    )
    send_log_to_channel(log_text)
    if message.from_user.id != ADMIN_ID:
        try:
            bot.send_message(ADMIN_ID, log_text, disable_web_page_preview=True)
        except Exception:
            pass

def send_campaign_card(chat_id, user_id, cid):
    camp = db["campaigns"].get(cid)
    if not camp:
        bot.send_message(chat_id, t(user_id, "camp_not_found"))
        return

    bot_username = bot.get_me().username
    vote_link = f"https://t.me/{bot_username}?start=vote_{cid}"
    vote_count = len(camp["voters"])

    card_text = (
        f"🏆 <b>VOTING CONTEST (#{cid})</b>\n\n"
        f"📌 {camp['title']}\n\n"
        f"👤 <b>Participant:</b> {camp['owner_name']}\n"
        f"❤️ <b>Total Votes:</b> <code>{vote_count}</code>\n"
        f"🔗 <b>Vote Link:</b> {vote_link}"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(t(user_id, "vote_btn").format(count=vote_count), callback_data=f"cast_vote:{cid}"),
        types.InlineKeyboardButton(t(user_id, "share_btn"), switch_inline_query=f"vote_{cid}")
    )

    if camp.get("photo_id"):
        bot.send_photo(chat_id, camp["photo_id"], caption=card_text, reply_markup
