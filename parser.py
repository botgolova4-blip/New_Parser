import asyncio
from datetime import datetime
from pyrogram import Client
from pyrogram.errors import FloodWait, ChatAdminRequired, ChannelPrivate, UsernameNotOccupied
from pyrogram.types import Message
from userbot import get_userbot


def extract_username(user) -> str | None:
    if user and user.username:
        return f"@{user.username.lower()}"
    return None


async def parse_channel(
    channel: str,
    mode: str,
    count_value: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    progress_callback=None,
) -> list:
    client = get_userbot()
    if not client:
        raise RuntimeError("Userbot не подключён")

    if channel.startswith("https://t.me/"):
        channel = channel[len("https://t.me/"):]
    elif channel.startswith("t.me/"):
        channel = channel[len("t.me/"):]
    channel = channel.strip("/").strip()

    limit = None
    skip = 0

    if mode == "count" and count_value:
        count_value = count_value.strip()
        if "," in count_value:
            parts = count_value.split(",")
            skip = abs(int(parts[0].strip()))
            limit = int(parts[1].strip())
        else:
            limit = int(count_value)

    posts = []
    total_fetched = 0

    try:
        async for message in client.get_chat_history(channel):
            if not isinstance(message, Message):
                continue

            msg_date = message.date

            if date_to and msg_date > date_to:
                continue
            if date_from and msg_date < date_from:
                break

            if skip > 0:
                skip -= 1
                continue

            posts.append(message)
            total_fetched += 1

            if progress_callback:
                await progress_callback(total_fetched)

            if limit and total_fetched >= limit:
                break

            await asyncio.sleep(0)

    except FloodWait as e:
        await asyncio.sleep(e.value)
    except (ChannelPrivate, UsernameNotOccupied, ChatAdminRequired):
        raise

    usernames = set()

    for i, post in enumerate(posts):
        if progress_callback:
            await progress_callback(f"post_{i+1}/{len(posts)}")

        try:
            async for reply in client.get_discussion_replies(channel, post.id):
                if reply.from_user:
                    u = extract_username(reply.from_user)
                    if u:
                        usernames.add(u)
                await asyncio.sleep(0)
        except Exception:
            pass

        try:
            from pyrogram.raw.functions.messages import GetMessageReactionsList
            reactions = await client.invoke(
                GetMessageReactionsList(
                    peer=await client.resolve_peer(channel),
                    id=post.id,
                    limit=100,
                )
            )
            for user in getattr(reactions, "users", []):
                u = extract_username(user)
                if u:
                    usernames.add(u)
        except Exception:
            pass

        await asyncio.sleep(0.3)

    return list(usernames)
