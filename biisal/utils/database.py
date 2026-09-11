# (c) TechifyBots
# (c) @biisal
#(c) Adarsh-Goel
import datetime
import motor.motor_asyncio


class Database:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users
        self.bannedList = self.db.bannedList
        # Collection used to track every generated private-file link
        # (both auto-generated on upload and admin /genlink links) so
        # they can be validated, expired and deleted on demand.
        self.links = self.db.links

    def new_user(self, id):
        return dict(
            id=id,
            join_date=datetime.date.today().isoformat()
        )

    async def add_user(self, id):
        user = self.new_user(id)
        await self.col.insert_one(user)
        
    async def add_user_pass(self, id, ag_pass):
        await self.add_user(int(id))
        await self.col.update_one({'id': int(id)}, {'$set': {'ag_p': ag_pass}})
    
    async def get_user_pass(self, id):
        user_pass = await self.col.find_one({'id': int(id)})
        return user_pass.get("ag_p", None) if user_pass else None
    
    async def is_user_exist(self, id):
        user = await self.col.find_one({'id': int(id)})
        return True if user else False

    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count

    async def get_all_users(self):
        all_users = self.col.find({})
        return all_users

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})
        
    async def ban_user(self , user_id):
        user = await self.bannedList.find_one({'banId' : int(user_id)})
        if user:
            return False
        else:
            await self.bannedList.insert_one({'banId' : int(user_id)})
            return True
        
    async def is_banned(self , user_id):
        user = await self.bannedList.find_one({'banId' : int(user_id)})
        return True if user else False
    
    async def is_unbanned(self , user_id):
        try : 
            if await self.bannedList.find_one({'banId' : int(user_id)}):
                await self.bannedList.delete_one({'banId' : int(user_id)})
                return True
            else:
                return False
        except Exception as e:
            e = f'Fᴀɪʟᴇᴅ ᴛᴏ ᴜɴʙᴀɴ.Rᴇᴀsᴏɴ : {e}'
            print(e)
            return e

    # ------------------------------------------------------------------
    # Private-file link tracking (expiry / deletion / quality-audio meta)
    #
    # Every generated private-file link (auto-generated on upload, or via
    # the admin /genlink command) gets one document per quality variant.
    # Documents that belong to the same logical link (e.g. several quality
    # variants of the same video) share the same `link_code`/`group_id`,
    # while `message_id` (unique within BIN_CHANNEL) identifies one exact
    # variant that a stream/download URL points to.
    # ------------------------------------------------------------------

    async def create_link(
        self,
        *,
        link_code: str,
        group_id: str,
        message_id: int,
        channel_id: int,
        file_unique_id_hash: str,
        file_name: str,
        quality_label: str = None,
        width: int = None,
        height: int = None,
        audio_tracks: list = None,
        is_primary: bool = True,
        source_chat_id: int = None,
        source_message_id: int = None,
        expire_at=None,
        created_by: int = None,
        created_by_name: str = None,
        generated_via: str = "auto",
    ):
        doc = dict(
            link_code=link_code,
            group_id=group_id,
            message_id=int(message_id),
            channel_id=int(channel_id),
            file_unique_id_hash=file_unique_id_hash,
            file_name=file_name,
            quality_label=quality_label,
            width=width,
            height=height,
            audio_tracks=audio_tracks or [],
            is_primary=is_primary,
            source_chat_id=source_chat_id,
            source_message_id=source_message_id,
            expire_at=expire_at,
            created_at=datetime.datetime.utcnow(),
            created_by=created_by,
            created_by_name=created_by_name,
            generated_via=generated_via,
            deleted=False,
            deleted_at=None,
        )
        await self.links.insert_one(doc)
        return doc

    async def get_link_by_message_id(self, message_id):
        return await self.links.find_one({"message_id": int(message_id)})

    async def get_links_by_group(self, group_id):
        cursor = self.links.find({"group_id": group_id, "deleted": False})
        return [doc async for doc in cursor]

    async def get_links_by_code(self, link_code):
        cursor = self.links.find({"link_code": link_code})
        return [doc async for doc in cursor]

    async def update_link_media_info(self, message_id, update: dict):
        if not update:
            return
        await self.links.update_one({"message_id": int(message_id)}, {"$set": update})

    async def set_group_expiry(self, group_id, expire_at):
        result = await self.links.update_many(
            {"group_id": group_id, "deleted": False},
            {"$set": {"expire_at": expire_at}},
        )
        return result.modified_count

    async def deactivate_message(self, message_id):
        """Marks a single link document as deleted (e.g. once its underlying
        message has been auto-cleaned-up). Does not touch sibling quality
        variants."""
        await self.links.update_one(
            {"message_id": int(message_id)},
            {"$set": {"deleted": True, "deleted_at": datetime.datetime.utcnow()}},
        )

    async def delete_link_group(self, link_code):
        """Marks every document sharing link_code as deleted and returns the
        documents that were affected (so the caller can also remove the
        underlying Telegram messages)."""
        cursor = self.links.find({"link_code": link_code})
        docs = [doc async for doc in cursor]
        await self.links.update_many(
            {"link_code": link_code},
            {"$set": {"deleted": True, "deleted_at": datetime.datetime.utcnow()}},
        )
        return docs

    @staticmethod
    def is_link_expired(record) -> bool:
        """Returns True only when `record` exists AND is deleted/expired.
        A None record (i.e. a link that isn't tracked in this collection,
        such as older channel-post links) is treated as not managed by this
        system, so existing behaviour for those is left completely
        untouched."""
        if not record:
            return False
        if record.get("deleted"):
            return True
        expire_at = record.get("expire_at")
        if expire_at and datetime.datetime.utcnow() >= expire_at:
            return True
        return False
