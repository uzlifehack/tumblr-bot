import requests
import re
import os
import subprocess
from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto, InputMediaDocument, InputMediaVideo, InlineKeyboardMarkup, InlineKeyboardButton

API_ID = 

API_HASH = 
BOT_TOKEN = 
TUMBLR_KEY = "n2cPpTkls4Cr3cXKXFxZn3munIzAgOitGZ8zzVpCdiKoNt0b1A"

TMPDIR = os.path.expanduser("~/downloads/tumblr_tmp")
os.makedirs(TMPDIR, exist_ok=True)

app = Client("tumblr_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
cache = {}

def download(url, path):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=60, stream=True)
    with open(path, 'wb') as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    return path

def gif_to_mp4(gif_path):
    mp4_path = gif_path.replace('.gif', '.mp4')
    subprocess.run(['ffmpeg', '-i', gif_path, '-movflags', 'faststart', '-pix_fmt', 'yuv420p', '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-an', mp4_path, '-y'], capture_output=True)
    return mp4_path

def get_post_data(url):
    m = re.search(r'tumblr\.com/([^/]+)/([0-9]+)', url)
    if not m:
        return [], "", set()
    blog, post_id = m.group(1), m.group(2)
    api = f"https://api.tumblr.com/v2/blog/{blog}/posts?id={post_id}&api_key={TUMBLR_KEY}"
    try:
        r = requests.get(api, timeout=15)
        posts = r.json().get("response", {}).get("posts", [])
        if not posts:
            return [], "", set()
        post = posts[0]
        body = post.get("body", "")
        caption = re.sub(r'<[^>]+>', '', body).strip()
        caption = re.sub(r'\n{3,}', '\n\n', caption).strip()
        media = []
        seen = set()
        imgs = re.findall(r'srcset="([^"]+)"', body)
        for s in imgs:
            best = s.split(", ")[-1].split(" ")[0]
            if best and best not in seen:
                seen.add(best)
                media.append(("gif" if ".gif" in best else "photo", best))
        for u in re.findall(r'https://[^\s"<>]+', body):
            if u not in seen:
                if "64.media.tumblr.com" in u and ".gif" in u:
                    seen.add(u)
                    media.append(("gif", u))
                elif "va.media.tumblr.com" in u:
                    seen.add(u)
                    media.append(("video", u))
        types = set(t for t, _ in media)
        return media, caption, types
    except Exception as e:
        print(f"Xato: {e}")
        return [], "", set()

@app.on_message(filters.command("start"))
async def start(c, m):
    await m.reply("Salom! Tumblr post linkini yuboring!")

@app.on_message(filters.regex(r'https?://.*tumblr\.com/.*'))
async def handle(c, m):
    url = m.text.strip()
    msg = await m.reply("⏳ Tekshirilmoqda...")
    media, caption, types = get_post_data(url)
    if not media:
        await msg.edit("❌ Media topilmadi.")
        return
    cache[m.id] = (media, caption, url)
    row = []
    if "photo" in types:
        row.append(InlineKeyboardButton("📷 Rasm", callback_data=f"photo_{m.id}"))
    if "gif" in types:
        row.append(InlineKeyboardButton("🎞 GIF", callback_data=f"gif_{m.id}"))
        row.append(InlineKeyboardButton("🎬 MP4 Group", callback_data=f"mp4_{m.id}"))
    row.append(InlineKeyboardButton("📁 Fayl", callback_data=f"file_{m.id}"))
    await msg.edit("Qanday yuboray?", reply_markup=InlineKeyboardMarkup([row]))

@app.on_callback_query()
async def callback(c, q):
    data = q.data
    parts = data.split("_")
    mode = parts[0]
    msg_id = int(parts[1])
    if msg_id not in cache:
        await q.answer("Xato! Linkni qayta yuboring.")
        return
    media, caption, url = cache[msg_id]
    await q.answer()
    status = await q.message.reply("⏳ Boshlanmoqda...")
    files = []
    try:
        group = []
        for i, (t, u) in enumerate(media[:10]):
            await status.edit(f"⏳ {i+1}/{min(len(media),10)} yuklanmoqda...")
            ext = ".gif" if t == "gif" else ".mp4" if t == "video" else ".jpg"
            path = os.path.join(TMPDIR, f"tumblr_{msg_id}_{i}{ext}")
            download(u, path)
            files.append(path)
            c_text = caption[:1024] if i == 0 else ""
            if mode == "file":
                group.append(InputMediaDocument(path, caption=c_text))
            elif mode == "gif":
                group.append(InputMediaDocument(path, caption=c_text))
            elif mode == "mp4":
                if t == "gif":
                    mp4 = gif_to_mp4(path)
                    files.append(mp4)
                    group.append(InputMediaVideo(mp4, caption=c_text, supports_streaming=True))
                else:
                    group.append(InputMediaVideo(path, caption=c_text, supports_streaming=True))
            else:
                if t == "gif":
                    mp4 = gif_to_mp4(path)
                    files.append(mp4)
                    group.append(InputMediaVideo(mp4, caption=c_text, supports_streaming=True))
                elif t == "video":
                    group.append(InputMediaVideo(path, caption=c_text, supports_streaming=True))
                else:
                    group.append(InputMediaPhoto(path, caption=c_text))
        await status.edit("📤 Yuborilmoqda...")
        await q.message.reply_media_group(group)
        await status.delete()
        await q.message.delete()
    except Exception as e:
        await status.edit(f"❌ Xato: {e}")
    finally:
        for f in files:
            try:
                os.remove(f)
            except:
                pass

print("Bot ishga tushdi!")
app.run()
