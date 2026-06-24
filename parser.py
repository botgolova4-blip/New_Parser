import asyncio
from datetime import datetime
from pyrogram import Client
from pyrogram.errors import FloodWait, ChatAdminRequired, ChannelPrivate, UsernameNotOccupied
from pyrogram.types import Message
from utils.userbot import get_userbot


def extract_username(user) -> str | None:
    """Extract @username from a Pyrogram User object."""
    if user and user.username:
        return f"@{user.username.lower()}"
    return None


async def get_channel_posts(
    client: Client,
    channel: str,
    limit: int | None = None,
    skip: int = 0,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    progress_callback=None,
) -> list:
    """
    Fetch posts from a channel according to filters.
    
    If date_from/date_to are set — filter by date.
    If limit is set — take `limit` posts after skipping `skip` most recent.
    """
    posts = []
    total_fetched = 0

    try:
        async for message in client.get_chat_history(channel):
            if not isinstance(message, Message):
                continue

            msg_date = message.date

            # Date range filter
            if date_to and msg_date > date_to:
                continue
            if date_from and msg_date < date_from:
                break  # history is reverse chronological, can stop here

            # Skip mode
            if skip > 0:
                skip -= 1
                continue

            posts.append(message)
            total_fetched += 1

            if progress_callback:
                await progress_callback(total_fetched)

            if limit and total_fetched >= limit:
                break

            await asyncio.sleep(0)  # yield

    except FloodWait as e:
        await asyncio.sleep(e.value)
    except (ChannelPrivate, UsernameNotOccupied, ChatAdminRequired):
        raise

    return posts


async def parse_channel(
    channel: str,
    mode: str,  # "count" or "dates"
    count_value: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    progress_callback=None,
) -> list[str]:
    """
    Main parsing function. Returns list of unique @usernames.
    
    count_value examples:
      "10"     → parse last 10 posts
      "-10, 5" → skip 10 most recent, parse next 5
    """
    client = get_userbot()
    if not client:
        raise RuntimeError("Userbot не подключён")

    # Normalize channel link
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
            skip_part = int(parts[0].strip())
            limit = int(parts[1].strip())
            skip = abs(skip_part)
        else:
            limit = int(count_value)
            skip = 0

    # Fetch posts
    posts = await get_channel_posts(
        client,
        channel,
        limit=limit,
        skip=skip,
        date_from=date_from,
        date_to=date_to,
        progress_callback=progress_callback,
    )

    usernames = set()

    for i, post in enumerate(posts):
        if progress_callback:
            await progress_callback(f"post_{i+1}/{len(posts)}")

        # Commenters
        try:
            async for reply in client.get_discussion_replies(channel, post.id):
                if reply.from_user:
                    u = extract_username(reply.from_user)
                    if u:
                        usernames.add(u)
                await asyncio.sleep(0)
        except Exception:
            pass  # comments may be disabled

        # Reactions (who reacted)
        try:
            async for reactor in client.get_message_reactions(channel, post.id):
                if hasattr(reactor, "peer_id"):
                    # reactions list — individual users
                    pass
            # Pyrogram approach for reactions voters
            reactions = await client.invoke(
                __import__("pyrogram.raw.functions.messages", fromlist=["GetMessageReactionsList"])
                .GetMessageReactionsList(
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

        await asyncio.sleep(0.3)  # be gentle with the API

    return list(usernames)
