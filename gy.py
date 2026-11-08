import base64
import hashlib
import json
import os
import time
import requests
import telebot
from telebot import types
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding

# ================= CONFIG =================
# Yahan @Gyftrrobot ka naya token daalo
BOT_TOKEN = "9074819613:AAGj3A-whxBze6-wlDLv0Q-luvGND8q4HxU" 
ADMIN_ID = 8101876637

# Channels / Groups list (Jo join karna zaroori hai)
CHANNELS = [
    {"link": "https://t.me/vishalxupdate", "username": "@vishalxupdate"},
    {"link": "https://t.me/lostworldoflost", "username": "@lostworldoflost"},
    {"link": "https://t.me/earningstarrrr", "username": "@earningstarrrr"}
]

# Naya Bot Username
BOT_USERNAME = "Gyftrrobot" 

API_BASE = "https://api.gyftr.com"
CAMPAIGN = "DIWALI2026"
PLAY_PATH = "/gyftrapi/api/v1/caimpaign/diwali2026"
PASSPHRASE = "d909dg78609e47ak47diy4cf87t90c4a"
SESSION_DB = "users.json"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": "https://www.gyftr.com",
    "referer": "https://www.gyftr.com/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36",
}
AUTH_HEADERS = {
    "device": "desktop", "platform": "web",
    "cache-control": "no-cache, no-store, must-revalidate", "pragma": "no-cache"
}

bot = telebot.TeleBot(BOT_TOKEN)

# ================= DATABASE =================
def load_db():
    if os.path.exists(SESSION_DB):
        try: return json.load(open(SESSION_DB))
        except: return {}
    return {}

def save_db(data):
    with open(SESSION_DB, "w") as f: json.dump(data, f, indent=2)

# ================= CRYPTO =================
def _evp_bytes_to_key(password, salt, key_len=32, iv_len=16):
    out, prev = b"", b""
    while len(out) < key_len + iv_len:
        prev = hashlib.md5(prev + password + salt).digest()
        out += prev
    return out[:key_len], out[key_len:key_len + iv_len]

def encrypt_cryptojs(plaintext, passphrase=PASSPHRASE):
    salt = os.urandom(8)
    key, iv = _evp_bytes_to_key(passphrase.encode(), salt)
    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    enc = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    ct = enc.update(padded) + enc.finalize()
    return base64.b64encode(b"Salted__" + salt + ct).decode()

def decrypt_cryptojs(b64_blob, passphrase=PASSPHRASE):
    raw = base64.b64decode(b64_blob)
    if raw[:8] != b"Salted__": raise ValueError("Not CryptoJS blob")
    salt, ct = raw[8:16], raw[16:]
    key, iv = _evp_bytes_to_key(passphrase.encode(), salt)
    dec = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    padded = dec.update(ct) + dec.finalize()
    unpadder = sym_padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()

def api_call(method, path, *, params=None, body=None, token=None, auth=False):
    headers = {**HEADERS}
    if auth:
        headers.update(AUTH_HEADERS)
        if token: headers["token"] = token
    r = requests.request(method, API_BASE + path, params=params, data=body, headers=headers, timeout=30)
    try: payload = r.json()
    except: raise RuntimeError(f"HTTP {r.status_code}")
    if payload.get("code") not in (200, 201, 202) or payload.get("status") not in ("SUCCESS", None):
        raise RuntimeError(payload.get("message") or "API Error")
    return payload

def do_login_step1(mobile):
    enc = encrypt_cryptojs(json.dumps({"mobile": mobile}, separators=(",", ":")).encode())
    return api_call("POST", "/gyftrapi/api/v1/chrismas/checkMobile", params={"campaign": CAMPAIGN}, body=json.dumps({"encryptedBody": enc}))

def do_login_step2(mobile, otp):
    enc = encrypt_cryptojs(json.dumps({"mobile": mobile, "otp": otp}, separators=(",", ":")).encode())
    return api_call("POST", "/gyftrapi/api/v1/chrismas/validateOtp", params={"campaign": CAMPAIGN}, body=json.dumps({"encryptedBody": enc}))

def fetch_profile(token):
    try:
        return api_call("GET", "/gyftrapi/api/v1/user/profile", params={"_": str(int(time.time() * 1000))}, token=token, auth=True)
    except: return None

def play_game(token, user_type, points):
    enc = encrypt_cryptojs(json.dumps({"user_type": user_type, "points": points}, separators=(",", ":")).encode())
    return api_call("POST", PLAY_PATH, body=json.dumps({"encryptedBody": enc}), token=token, auth=True)

# ================= FORCE SUBSCRIBE LOGIC =================
def is_subscribed(user_id):
    for channel in CHANNELS:
        try:
            member = bot.get_chat_member(channel["username"], user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception as e:
            print(f"Error checking {channel['username']}: {e}")
            return False
    return True

# ================= UI =================
def main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🎁 Claim Reward (1 Point)", callback_data="claim")
    btn2 = types.InlineKeyboardButton("🔗 Refer & Earn", callback_data="refer")
    btn3 = types.InlineKeyboardButton("💰 My Points", callback_data="pts")
    markup.add(btn1)
    markup.add(btn2, btn3)
    return markup

def admin_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("📊 Stats", callback_data="a_stats")
    btn2 = types.InlineKeyboardButton("🎁 Gift Points", callback_data="a_gift")
    btn3 = types.InlineKeyboardButton("⬅️ Main Menu", callback_data="a_back")
    markup.add(btn1, btn2, btn3)
    return markup

# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    args = message.text.split()
    db = load_db()

    # Referral Logic (5 Points)
    if len(args) > 1 and args[1].startswith("ref_"):
        ref_id = args[1].replace("ref_", "")
        if uid not in db and ref_id in db and ref_id != uid:
            db[ref_id]["points"] = db[ref_id].get("points", 0) + 5 
            save_db(db)
            try: bot.send_message(int(ref_id), "🎉 **Referral Successful!** Aapko 5 Points mil gaye hain.")
            except: pass

    if uid not in db:
        db[uid] = {"points": 0}
        save_db(db)

    # Force Subscribe Check
    if not is_subscribed(message.from_user.id):
        markup = types.InlineKeyboardMarkup(row_width=1)
        for channel in CHANNELS:
            markup.add(types.InlineKeyboardButton(f"Join {channel['username']}", url=channel["link"]))
        markup.add(types.InlineKeyboardButton("🔄 I have Joined All", callback_data="check_join"))
        bot.send_message(message.chat.id, "⚠️ **Bot use karne ke liye in saare channels/groups ko join karna zaroori hai!**\n\nJoin karke 'I have Joined All' pe click karein.", reply_markup=markup, parse_mode="Markdown")
        return

    bot.send_message(message.chat.id, f"👋 **Welcome!**\n💰 Points: **{db[uid].get('points',0)}**", reply_markup=main_menu(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def cb_check_join(call):
    if is_subscribed(call.from_user.id):
        bot.edit_message_text("✅ Thanks for joining all channels! Use /start to begin.", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ Aapne saare channels/groups join nahi kiye hain!", show_alert=True)

# ================= CALLBACKS =================
@bot.callback_query_handler(func=lambda call: call.data == "refer")
def cb_refer(call):
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{call.from_user.id}"
    bot.send_message(call.message.chat.id, f"🔗 **Your Referral Link:**\n`{link}`\n\n*(Har naye refer pe 5 Points milenge)*", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "pts")
def cb_pts(call):
    db = load_db()
    pts = db.get(str(call.from_user.id), {}).get("points", 0)
    bot.send_message(call.message.chat.id, f"💰 **Your Points:** {pts}")

# ================= CLAIM =================
@bot.callback_query_handler(func=lambda call: call.data == "claim")
def cb_claim(call):
    uid = str(call.from_user.id)
    db = load_db()
    if db.get(uid, {}).get("points", 0) < 1:
        bot.answer_callback_query(call.id, "❌ You need 1 Point to claim!", show_alert=True)
        return
    
    bot.answer_callback_query(call.id, "✅ Verified.")
    msg = bot.send_message(call.message.chat.id, "📱 **Enter 10-digit Mobile Number:**")
    bot.register_next_step_handler(msg, process_mobile)

def process_mobile(message):
    mobile = message.text.strip()
    if len(mobile) != 10 or not mobile.isdigit():
        msg = bot.send_message(message.chat.id, "❌ Invalid number. Try again:")
        bot.register_next_step_handler(msg, process_mobile)
        return

    db = load_db()
    db[str(message.chat.id)]["mobile"] = mobile
    save_db(db)

    msg = bot.send_message(message.chat.id, "⏳ Sending OTP...")
    try:
        do_login_step1(mobile)
        bot.edit_message_text(f"✅ OTP sent to `{mobile}`.\nEnter OTP:", message.chat.id, msg.message_id, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_otp, mobile)
    except Exception as e:
        bot.edit_message_text(f"❌ Failed: {e}", message.chat.id, msg.message_id)

def process_otp(message, mobile):
    otp = message.text.strip()
    msg = bot.send_message(message.chat.id, "⏳ Verifying & Claiming...")
    
    try:
        resp = do_login_step2(mobile, otp)
        token = resp.get("token")
        if not token: raise Exception("No token received.")

        play_res = play_game(token, "B2C", 150)
        epay = play_res.get("data", {}).get("epay", 0)
        
        # Deduct point
        db = load_db()
        db[str(message.chat.id)]["points"] -= 1
        save_db(db)

        bot.edit_message_text(
            f"🎉 **CLAIM SUCCESSFUL!**\n\n"
            f"📱 Number: `{mobile}`\n"
            f"💰 E-Pay Won: ₹{epay}\n"
            f"💸 Point Deducted: 1", 
            message.chat.id, msg.message_id, parse_mode="Markdown", reply_markup=main_menu()
        )
    except Exception as e:
        bot.edit_message_text(f"❌ Claim failed: {e}\n(Point not deducted)", message.chat.id, msg.message_id, reply_markup=main_menu())

# ================= ADMIN =================
@bot.message_handler(commands=['admin'])
def admin(message):
    if message.from_user.id != ADMIN_ID: return
    bot.send_message(message.chat.id, "🛠️ Admin Panel", reply_markup=admin_menu())

@bot.callback_query_handler(func=lambda call: call.data == "a_back")
def a_back(call):
    bot.edit_message_text("👋 Main Menu", call.message.chat.id, call.message.message_id, reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "a_stats")
def a_stats(call):
    if call.from_user.id != ADMIN_ID: return
    db = load_db()
    bot.edit_message_text(f"📊 Total Users: `{len(db)}`", call.message.chat.id, call.message.message_id, reply_markup=admin_menu(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "a_gift")
def a_gift(call):
    if call.from_user.id != ADMIN_ID: return
    msg = bot.send_message(call.message.chat.id, "🆔 Enter **Telegram ID** or **Mobile Number**:")
    bot.register_next_step_handler(msg, process_gift_id)

def process_gift_id(message):
    target = message.text.strip()
    db = load_db()
    found = None

    if target in db:
        found = target
    else:
        for k, v in db.items():
            if v.get("mobile") == target:
                found = k
                break

    if not found:
        bot.send_message(ADMIN_ID, "❌ User not found.")
        return

    msg = bot.send_message(ADMIN_ID, f"✅ User ID: `{found}`\nEnter points to gift:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_gift_amt, found)

def process_gift_amt(message, target_id):
    try: amt = int(message.text.strip())
    except: return bot.send_message(ADMIN_ID, "❌ Invalid amount.")
    
    db = load_db()
    db[target_id]["points"] = db[target_id].get("points", 0) + amt
    save_db(db)
    
    bot.send_message(ADMIN_ID, f"✅ Gifted {amt} points to `{target_id}`", parse_mode="Markdown")
    try: bot.send_message(int(target_id), f"🎁 **Admin Gift!**\nYou got {amt} Points.")
    except: pass

if __name__ == "__main__":
    bot.infinity_polling()