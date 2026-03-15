"""
מנטר עסקאות טלגרם - גרסת שרת (ללא GUI)
הרץ על VPS עם: python monitor.py
"""

import asyncio
import json
import os
import re
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient, events
import config

BASE     = os.path.dirname(__file__)
SESSION  = os.path.join(BASE, "session")
PRODUCTS_FILE = os.path.join(BASE, "products.json")
CHANNELS_FILE = os.path.join(BASE, "channels.json")


def load_products():
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return config.PRODUCTS[:]


def load_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return [{"label": str(ch), "value": ch} for ch in config.CHANNELS_TO_MONITOR]


def extract_url(text):
    urls = re.findall(r'https?://[^\s\)\]\>]+', text)
    return urls[0] if urls else ""


def check_message(text, products):
    text_lower = text.lower()
    found = []
    for product in products:
        if any(kw.lower() in text_lower for kw in product["keywords"]):
            if not any(ex.lower() in text_lower for ex in product.get("exclude_keywords", [])):
                found.append(product)
    return found


def log(msg):
    ts = datetime.now().strftime("%d/%m %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


async def main():
    products = load_products()
    channels = load_channels()

    if not products:
        log("❌ אין מוצרים מוגדרים. הגדר ב-app.py ושמור products.json")
        return
    if not channels:
        log("❌ אין ערוצים מוגדרים.")
        return

    log("🔌 מתחבר לטלגרם...")
    client = TelegramClient(SESSION, config.API_ID, config.API_HASH)
    await client.start()
    log("✅ מחובר!")

    valid_channels = []
    for ch in channels:
        try:
            entity = await client.get_entity(ch["value"])
            name   = getattr(entity, "title", str(ch["value"]))
            valid_channels.append(entity)
            log(f"   📢 ערוץ: {name}")
        except Exception as e:
            log(f"   ❌ {ch['label']}: {e}")

    if not valid_channels:
        log("❌ לא נמצאו ערוצים תקינים")
        return

    log(f"👁  מנטר {len(valid_channels)} ערוצים | {len(products)} מוצרים")

    # סריקת 24 שעות אחרונות
    log("🔎 סורק 24 שעות אחרונות...")
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    found_count = 0

    for entity in valid_channels:
        ch_name = getattr(entity, "title", str(entity.id))
        async for msg in client.iter_messages(entity, limit=500):
            if msg.date < since:
                break
            text = msg.text or ""
            if not text:
                continue
            for product in check_message(text, products):
                found_count += 1
                link = (f"https://t.me/{entity.username}/{msg.id}"
                        if getattr(entity, "username", None) else extract_url(text))
                log(f"   🛒 [היסטוריה] {product['name']} ב-{ch_name}")
                alert = (f"🛒 **[היסטוריה] עסקה!**\n"
                         f"📦 {product['name']}\n📢 {ch_name}\n\n"
                         f"{text[:400]}{'...' if len(text)>400 else ''}")
                if link:
                    alert += f"\n\n🔗 {link}"
                await client.send_message("me", alert, parse_mode="markdown")

    log(f"✅ סריקה הסתיימה — {found_count} עסקאות")
    log("⏳ מאזין להודעות חדשות... (Ctrl+C לעצור)\n")

    channel_ids = [ch.id for ch in valid_channels]

    @client.on(events.NewMessage(chats=channel_ids))
    async def handler(event):
        text = event.message.text or ""
        if not text:
            return
        channel_name = getattr(event.chat, "title", "ערוץ לא ידוע")
        for product in check_message(text, products):
            link = ""
            try:
                if getattr(event.chat, "username", None):
                    link = f"https://t.me/{event.chat.username}/{event.message.id}"
            except Exception:
                pass
            if not link:
                link = extract_url(text)

            log(f"🛒 עסקה חדשה! {product['name']} ב-{channel_name}")
            alert = (f"🛒 **עסקה חדשה!**\n"
                     f"📦 {product['name']}\n📢 {channel_name}\n\n"
                     f"{text[:400]}{'...' if len(text)>400 else ''}")
            if link:
                alert += f"\n\n🔗 {link}"
            try:
                await client.send_message("me", alert, parse_mode="markdown")
            except Exception as e:
                log(f"⚠️ שגיאה בשליחה: {e}")

    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("👋 הופסק.")
