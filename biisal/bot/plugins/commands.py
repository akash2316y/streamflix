import random
from biisal.bot import StreamBot
from biisal.vars import Var
import logging
logger = logging.getLogger(__name__)
from biisal.bot.plugins.stream import MY_PASS
from biisal.utils.human_readable import humanbytes
from biisal.utils.database import Database
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from biisal.utils.file_properties import get_name, get_hash, get_media_file_size
db = Database(Var.DATABASE_URL, Var.name)
from pyrogram.types import ReplyKeyboardMarkup


TechifyBots = """<b>Hey {}</b>

𝖲𝖾𝗇𝖽 𝗆𝖾 𝖺 𝖿𝗂𝗅𝖾 𝗈𝗋 𝖺𝖽𝖽 𝗆𝖾 𝖺𝗌 𝖺𝗇 𝖺𝖽𝗆𝗂𝗇 𝗍𝗈 𝖺𝗇𝗒 𝖼𝗁𝖺𝗇𝗇𝖾𝗅 𝗍𝗈 𝗂𝗇𝗌𝗍𝖺𝗇𝗍𝗅𝗒 𝗀𝖾𝗇𝖾𝗋𝖺𝗍𝖾 𝗉𝖾𝗋𝗆𝖺𝗇𝖾𝗇𝗍 𝗅𝗂𝗇𝗄𝗌.

𝖠𝖽𝖽 𝗆𝖾 𝗍𝗈 𝗒𝗈𝗎𝗋 𝖼𝗁𝖺𝗇𝗇𝖾𝗅 𝗍𝗈 𝗂𝗇𝗌𝗍𝖺𝗇𝗍𝗅𝗒 𝗀𝖾𝗇𝖾𝗋𝖺𝗍𝖾 𝗅𝗂𝗇𝗄𝗌 𝖿𝗈𝗋 𝖺𝗇𝗒 𝖽𝗈𝗐𝗇𝗅𝗈𝖺𝖽𝖺𝖻𝗅𝖾 𝗆𝖾𝖽𝗂𝖺. 𝖮𝗇𝖼𝖾 𝗋𝖾𝖼𝖾𝗂𝗏𝖾𝖽, 𝖨 𝗐𝗂𝗅𝗅 𝖺𝗎𝗍𝗈𝗆𝖺𝗍𝗂𝖼𝖺𝗅𝗅𝗒 𝖺𝗍𝗍𝖺𝖼𝗁 𝖺𝗉𝗉𝗋𝗈𝗉𝗋𝗂𝖺𝗍𝖾 𝖻𝗎𝗍𝗍𝗈𝗇𝗌 𝗍𝗈 𝗍𝗁𝖾 𝗉𝗈𝗌𝗍 𝖼𝗈𝗇𝗍𝖺𝗂𝗇𝗂𝗇𝗀 𝗍𝗁𝖾 𝖴𝖱𝖫.

<b>𝘕𝘰𝘵𝘦 :</b>𝘎𝘦𝘯𝘦𝘳𝘢𝘵𝘪𝘯𝘨 𝘓𝘪𝘯𝘬 𝘖𝘧 𝘈𝘥𝘶𝘭𝘵 𝘊𝘰𝘯𝘵𝘦𝘯𝘵 𝘐𝘴 𝘚𝘵𝘳𝘪𝘤𝘵𝘭𝘺 𝘗𝘳𝘰𝘩𝘪𝘣𝘪𝘵𝘦𝘥. 𝘐𝘧 𝘠𝘰𝘶 𝘞𝘪𝘭𝘭 𝘋𝘰 𝘠𝘰𝘶 𝘞𝘪𝘭𝘭 𝘎𝘦𝘵 𝘗𝘦𝘳𝘮𝘢𝘯𝘦𝘯𝘵 𝘉𝘢𝘯."""

@StreamBot.on_message(filters.command("start") & filters.private )
async def start(b, m):
    if not await db.is_user_exist(m.from_user.id):
        await db.add_user(m.from_user.id)
        await b.send_message(
            Var.NEW_USER_LOG,
            f"#𝐍𝐞𝐰𝐔𝐬𝐞𝐫\n\n**᚛› 𝐍𝐚𝐦𝐞 - [{m.from_user.first_name}](tg://user?id={m.from_user.id})**"
        )
    if Var.FORCE_SUB and Var.UPDATES_CHANNEL != "None":
        try:
            user = await b.get_chat_member(Var.UPDATES_CHANNEL, m.chat.id)
            if user.status == "kicked":
                await b.send_message(
                    chat_id=m.chat.id,
                    text="ꜱᴏʀʀʏ ʏᴏᴜ ᴀʀᴇ ʙᴀɴɴᴇᴅ ᴛᴏ ᴜꜱᴇ ᴍᴇ ᴘʟᴇᴀꜱᴇ ᴄᴏɴᴛᴀᴄᴛ ᴏᴡɴᴇʀ ꜰᴏʀ ᴍᴏʀᴇ ᴅᴇᴛᴀɪʟꜱ.",
                    disable_web_page_preview=True
                )
                return
        except UserNotParticipant:
             await StreamBot.send_photo(
                chat_id=m.chat.id,
                photo="https://graph.org/file/a8095ab3c9202607e78ad.jpg",
                caption=f"{m.from_user.mention},\n\n<b><i>⚠️ ᴊᴏɪɴ ᴍʏ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜsᴇ ᴍᴇ.</i></b>\n\n<i>ᴅᴜᴇ ᴛᴏ sᴇʀᴠᴇʀ ᴏᴠᴇʀʟᴏᴀᴅ, ᴏɴʟʏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ sᴜʙsᴄʀɪʙᴇʀs ᴄᴀɴ ᴜsᴇ ᴛʜɪs ʙᴏᴛ 😊</i>",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("ᴊᴏɪɴ ɴᴏᴡ", url=f"https://telegram.me/{Var.UPDATES_CHANNEL}")
                        ]
                    ]
                ),
                
            )
             return
        except Exception:
            await b.send_message(
                chat_id=m.chat.id,
                text="<b>ꜱᴏᴍᴇᴛʜɪɴɢ  ᴡᴇɴᴛ  ᴡʀᴏɴɢ  <a href='https://telegram.me/UnknownBotzChat'>ᴄʟɪᴄᴋ  ʜᴇʀᴇ  ꜰᴏʀ  ꜱᴜᴘᴘᴏʀᴛ</a></b>",
                
                disable_web_page_preview=True)
            return
    await StreamBot.send_photo(
    chat_id=m.chat.id,
    photo=random.choice(Var.PICS),
    caption= TechifyBots.format(m.from_user.mention(style="md")),
    reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("ᴜᴘᴅᴀᴛᴇ", url="https://telegram.me/UnknownBotz"),
                        InlineKeyboardButton("sᴜᴘᴘᴏʀᴛ", url="https://telegram.me/UnknownBotzChat")
                    ],
                    [
                        InlineKeyboardButton("ᴀʙᴏᴜᴛ", callback_data="about"),
                        InlineKeyboardButton("ʜᴇʟᴘ", callback_data="help")
                    ]
                    
                ]
            )
)

@StreamBot.on_message(filters.command("help") & filters.private )
async def help_cd(b, m):
    if not await db.is_user_exist(m.from_user.id):
        await db.add_user(m.from_user.id)
        await b.send_message(
            Var.NEW_USER_LOG,
            f"#𝐍𝐞𝐰𝐔𝐬𝐞𝐫\n\n**᚛› 𝐍𝐚𝐦𝐞 - [{m.from_user.first_name}](tg://user?id={m.from_user.id})**"
        )
    if Var.UPDATES_CHANNEL != "None":
        try:
            user = await b.get_chat_member(Var.UPDATES_CHANNEL, m.chat.id)
            if user.status == "kicked":
                await b.send_message(
                    chat_id=m.chat.id,
                    text="ꜱᴏʀʀʏ ʏᴏᴜ ᴀʀᴇ ʙᴀɴɴᴇᴅ ᴛᴏ ᴜꜱᴇ ᴍᴇ ᴘʟᴇᴀꜱᴇ ᴄᴏɴᴛᴀᴄᴛ ᴏᴡɴᴇʀ ꜰᴏʀ ᴍᴏʀᴇ ᴅᴇᴛᴀɪʟꜱ.",
                    disable_web_page_preview=True
                )
                return
        except UserNotParticipant:
             await StreamBot.send_photo(
                chat_id=m.chat.id,
                photo="https://graph.org/file/a8095ab3c9202607e78ad.jpg",
                caption=f"<b>Hey{m.from_user.mention},\n\n<i>⚠️ ᴊᴏɪɴ ᴍʏ ᴜᴘᴅᴀᴛᴇs ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜsᴇ ᴍᴇ.</i>\n\n<i>ᴅᴜᴇ ᴛᴏ sᴇʀᴠᴇʀ ᴏᴠᴇʀʟᴏᴀᴅ, ᴏɴʟʏ ᴏᴜʀ ᴄʜᴀɴɴᴇʟ sᴜʙsᴄʀɪʙᴇʀs ᴄᴀɴ ᴜsᴇ ᴛʜɪs ʙᴏᴛ 😊</i>",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("ᴊᴏɪɴ ɴᴏᴡ", url=f"https://telegram.me/{Var.UPDATES_CHANNEL}")
                        ]
                    ]
                ),
                
            )
             return
        except Exception:
            await b.send_message(
                chat_id=m.chat.id,
                text="ꜱᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ ᴄᴏɴᴛᴀᴄᴛ [ᴏᴡɴᴇʀ](https://telegram.me/AlwaysToHelpBot).",
                disable_web_page_preview=True)
            return
    await StreamBot.send_photo(
    chat_id=m.chat.id,
    photo=random.choice(Var.PICS),
    caption="""<b>You Don't Need Many Commands To Use This Bot 😅.

Just Send Me Files And I Will Give You Direct Download & Streaming Link.

Also You Can Use Me In Your Channel..Just Add Me And Make Me Admin And See My Power 🔥</b>""",
    reply_markup=InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✗ ᴄʟᴏsᴇ ✗", callback_data="close")]
        ]
    )
)

@StreamBot.on_message(filters.command('ban') & filters.user(Var.OWNER_ID))
async def do_ban(bot ,  message):
    userid = message.text.split(" ", 2)[1] if len(message.text.split(" ", 1)) > 1 else None
    reason = message.text.split(" ", 2)[2] if len(message.text.split(" ", 2)) > 2 else None
    if not userid:
        return await message.reply('<b>ᴘʟᴇᴀsᴇ ᴀᴅᴅ ᴀ ᴠᴀʟɪᴅ ᴜsᴇʀ/ᴄʜᴀɴɴᴇʟ ɪᴅ ᴡɪᴛʜ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ\n\nᴇx : /ban (user/channel_id) (banning reason[Optional]) \nʀᴇᴀʟ ᴇx : <code>/ban 1234567899</code>\nᴡɪᴛʜ ʀᴇᴀsᴏɴ ᴇx:<code>/ban 1234567899 seding adult links to bot</code>\nᴛᴏ ʙᴀɴ ᴀ ᴄʜᴀɴɴᴇʟ :\n<code>/ban CHANEL_ID</code>\nᴇx : <code>/ban -1001234567899</code></b>')
    text = await message.reply("<b>ʟᴇᴛ ᴍᴇ ᴄʜᴇᴄᴋ 👀</b>")
    banSts = await db.ban_user(userid)
    if banSts == True:
        await text.edit(
    text=f"<b><code>{userid}</code> ʜᴀs ʙᴇᴇɴ ʙᴀɴɴᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ\n\nSʜᴏᴜʟᴅ I sᴇɴᴅ ᴀɴ ᴀʟᴇʀᴛ ᴛᴏ ᴛʜᴇ ʙᴀɴɴᴇᴅ ᴜsᴇʀ?</b>",
    reply_markup=InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("ʏᴇs ✅", callback_data=f"sendAlert_{userid}_{reason if reason else 'no reason provided'}"),
                InlineKeyboardButton("ɴᴏ ❌", callback_data=f"noAlert_{userid}"),
            ],
        ]
    ),
)
    else:
        await text.edit(f"<b>Cᴏɴᴛʀᴏʟʟ ʏᴏᴜʀ ᴀɴɢᴇʀ ʙʀᴏ...\n<code>{userid}</code> ɪs ᴀʟʀᴇᴀᴅʏ ʙᴀɴɴᴇᴅ !!</b>")
    return


@StreamBot.on_message(filters.command('unban') & filters.user(Var.OWNER_ID))
async def do_unban(bot ,  message):
    userid = message.text.split(" ", 2)[1] if len(message.text.split(" ", 1)) > 1 else None
    if not userid:
        return await message.reply('ɢɪᴠᴇ ᴍᴇ ᴀɴ ɪᴅ\nᴇx : <code>/unban 1234567899<code>')
    text = await message.reply("<b>ʟᴇᴛ ᴍᴇ ᴄʜᴇᴄᴋ 🥱</b>")
    unban_chk = await db.is_unbanned(userid)
    if  unban_chk == True:
        await text.edit(text=f'<b><code>{userid}</code> ɪs ᴜɴʙᴀɴɴᴇᴅ\nSʜᴏᴜʟᴅ I sᴇɴᴅ ᴛʜᴇ ʜᴀᴘᴘʏ ɴᴇᴡs ᴀʟᴇʀᴛ ᴛᴏ ᴛʜᴇ ᴜɴʙᴀɴɴᴇᴅ ᴜsᴇʀ?</b>',
        reply_markup=InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("ʏᴇs ✅", callback_data=f"sendUnbanAlert_{userid}"),
                InlineKeyboardButton("ɴᴏ ❌", callback_data=f"NoUnbanAlert_{userid}"),
            ],
        ]
    ),
)

    elif unban_chk==False:
        await text.edit('<b>ᴜsᴇʀ ɪs ɴᴏᴛ ʙᴀɴɴᴇᴅ ʏᴇᴛ.</b>')
    else :
        await text.edit(f"<b>ғᴀɪʟᴇᴅ ᴛᴏ ᴜɴʙᴀɴ ᴜsᴇʀ/ᴄʜᴀɴɴᴇʟ.\nʀᴇᴀsᴏɴ : {unban_chk}</b>")

@StreamBot.on_callback_query()
async def cb_handler(client, query):
    data = query.data
    if data == "close":
        await query.message.delete()


    if data == "start":
        await query.message.edit_caption(
        caption= TechifyBots.format(query.from_user.mention(style="md")),
        reply_markup=InlineKeyboardMarkup(
                    [
                        [
                        InlineKeyboardButton("ᴜᴘᴅᴀᴛᴇ", url="https://telegram.me/UnknownBotz"),
                        InlineKeyboardButton("sᴜᴘᴘᴏʀᴛ", url="https://telegram.me/UnknownBotzChat")
                    ],
                    [
                        InlineKeyboardButton("ᴀʙᴏᴜᴛ", callback_data="about"),
                        InlineKeyboardButton("ʜᴇʟᴘ", callback_data="help")
                     ]
                    ]
                )
        )

    elif data == "about":
        await query.message.edit_caption(
            caption=f"<b>ᴍʏ ɴᴀᴍᴇ : <a href='https://telegram.me/StreamFllixBot'>sᴛʀᴇᴀᴍ ғʟɪx</a>\nʜᴏsᴛᴇᴅ ᴏɴ : ᴋᴏʏᴇʙ\nᴅᴀᴛᴀʙᴀsᴇ : ᴍᴏɴɢᴏ ᴅʙ\nʟᴀɴɢᴜᴀɢᴇ : ᴘʏᴛʜᴏɴ 𝟹\nᴍʏ ᴄʀᴇᴀᴛᴏʀ : <a href='https://telegram.me/AlwaysToHelpBot'>ᴜɴᴋɴᴏᴡɴ</a></b>",
            reply_markup=InlineKeyboardMarkup(
                [[ 
                     InlineKeyboardButton("ʜᴏᴍᴇ", callback_data="start"),
                     InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")
                  ]]
            )
        )

    elif data == "help":
        await query.message.edit_caption(
        caption=f"<b>You Don't Need Many Commands To Use This Bot 😅.\n\nJust Send Me Files And I Will Give You Direct Download & Streaming Link.\n\nAlso You Can Use Me In Your Channel..Just Add Me And Make Me Admin And See My Power 🔥</b>",
            reply_markup=InlineKeyboardMarkup(
            [
             [InlineKeyboardButton("ʜᴏᴍᴇ", callback_data="start")]
            ]
        )
        )

    elif data.startswith("sendAlert"):
        user_id =(data.split("_")[1])
        user_id = int(user_id.replace(' ' , ''))
        if len(str(user_id)) == 10:
            reason = str(data.split("_")[2])
            try:
                await client.send_message(user_id , f"<b>ʏᴏᴜ ᴀʀᴇ ʙᴀɴɴᴇᴅ ʙʏ [ᴜɴᴋɴᴏᴡɴ](https://telegram.me/AlwaysToHelpBot)\nʀᴇᴀsᴏɴ : {reason}</b>")
                await query.message.edit(f"<b>Aʟᴇʀᴛ sᴇɴᴛ ᴛᴏ <code>{user_id}</code>\nʀᴇᴀsᴏɴ : {reason}</b>")
            except Exception as e:
                await query.message.edit(f"<b>sʀʏ ɪ ɢᴏᴛ ᴛʜɪs ᴇʀʀᴏʀ : {e}</b>")
        else:
            await query.message.edit(f"<b>Tʜᴇ ᴘʀᴏᴄᴇss ᴡᴀs ɴᴏᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ʙᴇᴄᴀᴜsᴇ ᴛʜᴇ ᴜsᴇʀ ɪᴅ ᴡᴀs ɴᴏᴛ ᴠᴀʟɪᴅ, ᴏʀ ᴘᴇʀʜᴀᴘs ɪᴛ ᴡᴀs ᴀ ᴄʜᴀɴɴᴇʟ ɪᴅ</b>")

    elif data.startswith('noAlert'):
        user_id =(data.split("_")[1])
        user_id = int(user_id.replace(' ' , ''))
        await query.message.edit(f"<b>Tʜᴇ ʙᴀɴ ᴏɴ <code>{user_id}</code> ᴡᴀs ᴇxᴇᴄᴜᴛᴇᴅ sɪʟᴇɴᴛʟʏ.</b>")

    elif data.startswith('sendUnbanAlert'):
        user_id =(data.split("_")[1])
        user_id = int(user_id.replace(' ' , ''))
        if len(str(user_id)) == 10:
            try:
                unban_text = "<b>ʜᴜʀʀᴀʏ..ʏᴏᴜ ᴀʀᴇ ᴜɴʙᴀɴɴᴇᴅ ʙʏ [ᴜɴᴋɴᴏᴡɴ](https://telegram.me/AlwaysToHelpBot)</b>"
                await client.send_message(user_id , unban_text)
                await query.message.edit(f"<b>Uɴʙᴀɴɴᴇᴅ Aʟᴇʀᴛ sᴇɴᴛ ᴛᴏ <code>{user_id}</code>\nᴀʟᴇʀᴛ ᴛᴇxᴛ : {unban_text}</b>")
            except Exception as e:
                await query.message.edit(f"<b>sʀʏ ɪ ɢᴏᴛ ᴛʜɪs ᴇʀʀᴏʀ : {e}</b>")
        else:
            await query.message.edit(f"<b>Tʜᴇ ᴘʀᴏᴄᴇss ᴡᴀs ɴᴏᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ ʙᴇᴄᴀᴜsᴇ ᴛʜᴇ ᴜsᴇʀ ɪᴅ ᴡᴀs ɴᴏᴛ ᴠᴀʟɪᴅ, ᴏʀ ᴘᴇʀʜᴀᴘs ɪᴛ ᴡᴀs ᴀ ᴄʜᴀɴɴᴇʟ ɪᴅ</b>")   
    elif data.startswith('NoUnbanAlert'):
        user_id =(data.split("_")[1])
        user_id = int(user_id.replace(' ' , ''))

        await query.message.edit(f"Tʜᴇ ᴜɴʙᴀɴ ᴏɴ <code>{user_id}</code> ᴡᴀs ᴇxᴇᴄᴜᴛᴇᴅ sɪʟᴇɴᴛʟʏ.")











