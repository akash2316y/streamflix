import os
import asyncio
import requests
import string
import random
import datetime
import logging
from asyncio import TimeoutError
from biisal.bot import StreamBot
from biisal.utils.database import Database
from biisal.utils.human_readable import humanbytes
from biisal.vars import Var
from urllib.parse import quote_plus
from pyrogram import filters, Client
from pyrogram.errors import FloodWait, UserNotParticipant
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from biisal.utils.file_properties import get_name, get_hash, get_media_file_size, get_media_from_message
from biisal.utils.media_probe import quality_label_from_height, probe_and_store
db = Database(Var.DATABASE_URL, Var.name)

# Default expiry kept for auto-generated links so existing behaviour
# (message auto-cleanup after 6 hours, see below) stays unchanged.
AUTO_LINK_EXPIRY_SECONDS = 21600

def generate_random_alphanumeric(): 
    characters = string.ascii_letters + string.digits 
    return ''.join(random.choice(characters) for _ in range(8)) 

def get_shortlink(url): 
    rget = requests.get(
        f"https://{Var.SHORTLINK_URL}/api?api={Var.SHORTLINK_API}&url={url}&alias={generate_random_alphanumeric()}"
    ) 
    rjson = rget.json() 
    if rjson.get("status") == "success": 
        return rjson.get("shortenedUrl", url) 
    return url

MY_PASS = os.environ.get("MY_PASS", None)
pass_dict = {}
pass_db = Database(Var.DATABASE_URL, "ag_passwords")

# ================= FIX 1 (ONLY THIS CHANGED) =================
msg_text ="""
<b>ʏᴏᴜʀ ʟɪɴᴋ ɪs ɢᴇɴᴇʀᴀᴛᴇᴅ...⚡</b>

<b>📧 ꜰɪʟᴇ ɴᴀᴍᴇ : </b> <i>{name}</i>

<b>📦 ꜰɪʟᴇ sɪᴢᴇ : </b> <i>{size}</i>

<b>📥 ᴅᴏᴡɴʟᴏᴀᴅ : </b>{download}

<b>🎬 sᴛʀᴇᴀᴍ : </b>{stream}

<b>⚠️ ᴛʜɪꜱ ʟɪɴᴋ ᴡɪʟʟ ᴇxᴘɪʀᴇ ᴀꜰᴛᴇʀ 𝟼 ʜᴏᴜʀꜱ</b>"""
# =============================================================

@StreamBot.on_message((filters.private) & (filters.document | filters.video | filters.audio | filters.photo) , group=4)
async def private_receive_handler(c: Client, m: Message):
    if not await db.is_user_exist(m.from_user.id):
        await db.add_user(m.from_user.id)
        await c.send_message(
            Var.NEW_USER_LOG,
            f"#𝐍𝐞𝐰𝐔𝐬𝐞𝐫\n\n**᚛› 𝐍𝐚𝐦𝐞 - [{m.from_user.first_name}](tg://user?id={m.from_user.id})**"
        )
    if Var.UPDATES_CHANNEL != "None":
        try:
            user = await c.get_chat_member(Var.UPDATES_CHANNEL, m.chat.id)
            if user.status == "kicked":
                await c.send_message(
                    chat_id=m.chat.id,
                    text="You are banned!\n\n  Contact Developer [Rahul](https://telegram.me/AlwaysToHelpBot) he will help you.",
                    disable_web_page_preview=True
                )
                return 
        except UserNotParticipant:
            await c.send_photo(
                chat_id=m.chat.id,
                photo="https://graph.org/file/a8095ab3c9202607e78ad.jpg",
                caption="""<b>ᴊᴏɪɴ ᴏᴜʀ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜꜱᴇ ᴍᴇ</b>""",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("ᴊᴏɪɴ ɴᴏᴡ", url=f"https://telegram.me/{Var.UPDATES_CHANNEL}")
                        ]
                    ]
                ),
            )
            return
        except Exception as e:
            await m.reply_text(e)
            await c.send_message(
                chat_id=m.chat.id,
                text="sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ. ᴄᴏɴᴛᴀᴄᴛ ᴍʏ [ʙᴏss](https://telegram.me/CallOwnerBot)",
                disable_web_page_preview=True
            )
            return
    ban_chk = await db.is_banned(int(m.from_user.id))
    if ban_chk == True:
        return await m.reply(Var.BAN_ALERT)

    try:  # This is the outer try block
        log_msg = await m.copy(chat_id=Var.BIN_CHANNEL)
        stream_link = f"{Var.URL}watch/{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
        online_link = f"{Var.URL}{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
        try:  # This is the inner try block
            if Var.SHORTLINK:
                stream = get_shortlink(stream_link)
                download = get_shortlink(online_link)
            else:
                stream = stream_link
                download = online_link
        except Exception as e:
            print(f"An error occurred: {e}")

        # ---- Track this generated link (expiry / deletion support) ----
        link_code = generate_random_alphanumeric()
        try:
            media_obj = get_media_from_message(log_msg)
            height = getattr(media_obj, "height", None)
            width = getattr(media_obj, "width", None)
            expire_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=AUTO_LINK_EXPIRY_SECONDS)
            await db.create_link(
                link_code=link_code,
                group_id=link_code,
                message_id=log_msg.id,
                channel_id=Var.BIN_CHANNEL,
                file_unique_id_hash=get_hash(log_msg),
                file_name=get_name(log_msg),
                quality_label=quality_label_from_height(height) or "Original",
                width=width,
                height=height,
                is_primary=True,
                source_chat_id=m.chat.id,
                source_message_id=m.id,
                expire_at=expire_at,
                created_by=m.from_user.id,
                created_by_name=m.from_user.first_name,
                generated_via="auto",
            )
            asyncio.create_task(probe_and_store(db, log_msg.id))
        except Exception as e:
            logging.getLogger(__name__).debug(f"Failed to store link metadata: {e}")

        a = await log_msg.reply_text(
            text=f"ʀᴇǫᴜᴇꜱᴛᴇᴅ ʙʏ : [{m.from_user.first_name}](tg://user?id={m.from_user.id})\n"
                 f"Uꜱᴇʀ ɪᴅ : `{m.from_user.id}`\n"
                 f"Stream ʟɪɴᴋ : {stream_link}\n"
                 f"Lɪɴᴋ ID : `{link_code}` (ᴀᴅᴍɪɴ : /delfile {link_code} ᴛᴏ ʀᴇᴍᴏᴠᴇ)",
            disable_web_page_preview=True,
            quote=True
        )

        k = await m.reply_text(
            text=msg_text.format(
                name=get_name(log_msg),
                size=humanbytes(get_media_file_size(m)),
                stream=stream,
                download=download
            ),
            quote=True,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("• ꜱᴛʀᴇᴀᴍ •", url=stream),
                    InlineKeyboardButton("• ᴅᴏᴡɴʟᴏᴀᴅ •", url=download)
                ]
            ])
        )

        await m.delete()  # Delete the original message after processing
        
        await asyncio.sleep(21600)

        
        try:
            await log_msg.delete()
            await a.delete()
            await k.delete()
        except Exception as e:
            print(f"Error during deletion: {e}")
        try:
            await db.deactivate_message(log_msg.id)
        except Exception as e:
            logging.getLogger(__name__).debug(f"Failed to deactivate link record: {e}")

    except FloodWait as e:
        print(f"Sleeping for {str(e.x)}s")
        await asyncio.sleep(e.x)
        await c.send_message(chat_id=Var.BIN_CHANNEL, text=f"Gᴏᴛ FʟᴏᴏᴅWᴀɪᴛ ᴏғ {str(e.x)}s from [{m.from_user.first_name}](tg://user?id={m.from_user.id})\n\n**𝚄𝚜𝚎𝚛 𝙸𝙳 :** `{str(m.from_user.id)}`", disable_web_page_preview=True)

@StreamBot.on_message(filters.channel & ~filters.group & (filters.document | filters.video | filters.photo)  & ~filters.forwarded, group=-1)
async def channel_receive_handler(bot, broadcast):
    if int(broadcast.chat.id) in Var.BAN_CHNL:
        print("chat trying to get straming link is found in BAN_CHNL,so im not going to give stram link")
        return
    ban_chk = await db.is_banned(int(broadcast.chat.id))
    if (int(broadcast.chat.id) in Var.BANNED_CHANNELS) or (ban_chk == True):
        await bot.leave_chat(broadcast.chat.id)
        return
    try:  # This is the outer try block
        log_msg = await broadcast.forward(chat_id=Var.BIN_CHANNEL)
        stream_link = f"{Var.URL}watch/{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
        online_link = f"{Var.URL}{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
        try:  # This is the inner try block
            if Var.SHORTLINK:
                stream = get_shortlink(stream_link)
                download = get_shortlink(online_link)
            else:
                stream = stream_link
                download = online_link
        except Exception as e:
            print(f"An error occurred: {e}")

        await log_msg.reply_text(
            text=f"**Channel Name:** `{broadcast.chat.title}`\n**CHANNEL ID:** `{broadcast.chat.id}`\n**Rᴇǫᴜᴇsᴛ ᴜʀʟ:** {stream_link}",
            quote=True
        )
        await bot.edit_message_reply_markup(
            chat_id=broadcast.chat.id,
            message_id=broadcast.id,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("• ꜱᴛʀᴇᴀᴍ •", url=stream),
                    InlineKeyboardButton("• ᴅᴏᴡɴʟᴏᴀᴅ •", url=download)
                ]
            ])
        )
    except FloodWait as w:
        print(f"Sleeping for {str(w.x)}s")
        await asyncio.sleep(w.x)
        await bot.send_message(chat_id=Var.BIN_CHANNEL,
                            text=f"GOT FLOODWAIT OF {str(w.x)}s FROM {broadcast.chat.title}\n\n**CHANNEL ID:** `{str(broadcast.chat.id)}`",
                            disable_web_page_preview=True)
    except Exception as e:
        await bot.send_message(chat_id=Var.BIN_CHANNEL, text=f"**#ERROR_TRACKEBACK:** `{e}`", disable_web_page_preview=True)
        print(f"Cᴀɴ'ᴛ Eᴅɪᴛ Bʀᴏᴀᴅᴄᴀsᴛ Mᴇssᴀɢᴇ!\nEʀʀᴏʀ:  **Give me edit permission in updates and bin Channel!{e}**")
















