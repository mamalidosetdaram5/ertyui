from telethon import TelegramClient, events
import asyncio
import re

# --- تنظیمات ---
api_id = 29206821
api_hash = '6fc091b004de021d44c76f01e27fe91c'

client = TelegramClient('mmd1', api_id, hash)

# لیست آیدی‌های ادمین‌ها (هر چقدر بخوای میتونی اضافه کنی)
# آیدی‌ها باید عددی و مثبت باشند
ADMINS = [
    8886156118,   # ادمین 1
    7644715017,    
]

spamming_tasks = {}

# تغییر: چک میکنیم آیا فرستنده در لیست ADMINS هست یا نه
@client.on(events.NewMessage(outgoing=False))
async def handle_admin_commands(event):
    sender_id = event.sender_id  # آیدی عددی فرستنده پیام
    
    # چک میکنیم آیا فرستنده یکی از ادمین‌هاست؟
    if sender_id not in ADMINS:
        return  # اگر ادمین نیست، هیچ کاری نکن

    chat_id = event.chat_id
    message_text = (event.raw_text or "").strip()
    
    # پترن اسپم
    spam_match = re.match(r'^\.spam\s+(\d+)\s+(.+)$', message_text)
    if spam_match:
        delay = int(spam_match.group(1))
        message = spam_match.group(2)
        
        if chat_id in spamming_tasks:
            await event.reply("اسپم درحال اجراست [ .stop ]بزن.")
            return

        async def spammer():
            # اسپم در همان چتی که دستور داده شده انجام میشه
            target_chat = chat_id 
            
            while True:
                try:
                    await client.send_message(target_chat, message)
                    await asyncio.sleep(delay)
                except Exception as e:
                    print(f"Error: {e}")
                    break

        task = asyncio.create_task(spammer())
        spamming_tasks[chat_id] = task
        await event.reply(f"✅ اسپم فعال شد توسط ادمین {sender_id}: هر {delay} ثانیه → «{message}»")

    # پترن توقف
    if message_text == '.stop':
        task = spamming_tasks.get(chat_id)
        if task:
            task.cancel()
            del spamming_tasks[chat_id]
            await event.reply("متوقف شد.")
        else:
            await event.reply("هیچ اسپمی در حال اجرا نیست.")

@client.on(events.NewMessage)
async def monitor_spawn_line(event):
    chat_id = event.chat_id
    message_text = (event.raw_text or "").strip()
    trigger_phrase = "❓ ᴀ ᴄʜᴀʀᴀᴄᴛᴇʀ ʜᴀs sᴘᴀᴡɴᴇᴅ ɪɴ ᴛʜᴇ ᴄʜᴀᴛ!"

    if trigger_phrase in message_text and chat_id in spamming_tasks:
        task = spamming_tasks[chat_id]
        task.cancel()
        del spamming_tasks[chat_id]
        await client.send_message(chat_id, "کارتت اومد")

client.start()
print(">> Self bot first (XCX) is running with MULTIPLE ADMINS.")
client.run_until_disconnected()
