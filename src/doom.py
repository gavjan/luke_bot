from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from cons import actions

DOOM_START_LINK = "https://doom.p2r3.com/ei.webp"
_DOOM_SUFFIX = "i.webp"
_VALID_KEYS = {"w", "a", "s", "d", "q", "e"}
_GAME_TTL = timedelta(minutes=30)


@dataclass
class DoomGameState:
    link: str
    bot_message_id: int
    channel_id: int
    updated_at: datetime


# user_id -> DoomGameState
_doom_games: dict[int, DoomGameState] = {}


def _now() -> datetime:
    return datetime.utcnow()


def _is_expired(state: DoomGameState) -> bool:
    return _now() - state.updated_at > _GAME_TTL


def _append_key(link: str, key: str) -> str:
    # Insert the key immediately before the trailing "i.webp".
    if link.endswith(_DOOM_SUFFIX):
        return link[: -len(_DOOM_SUFFIX)] + key + _DOOM_SUFFIX

    # Fallback: if format is unexpected, just append.
    return link + key


def _doom_prompt(user_mention: str, link: str) -> str:
    return (
        f"{user_mention}\n"
        "Send one key at a time:\n"
        "move: `w` `a` `s` `d`\n"
        "shoot: `q`\n"
        "interact: `e`\n"
        "`/doom`: start a new game.\n"
        f"{link}"
    )


async def doom_entry(client, message):
    """Handle /doom and per-key inputs.

    Returns True if the message was a doom control message (consumed), else False.
    """

    content = (message.content or "").strip().lower()
    user_id = message.author.id

    if content == "/doom":
        link = DOOM_START_LINK
        sent = await message.channel.send(_doom_prompt(message.author.mention, link))
        _doom_games[user_id] = DoomGameState(
            link=link,
            bot_message_id=sent.id,
            channel_id=sent.channel.id,
            updated_at=_now(),
        )
        return True

    if content in _VALID_KEYS and user_id in _doom_games:
        prev_state = _doom_games.get(user_id)
        if not prev_state:
            return True

        # Expired games are ignored (doom backend clears after ~30 mins).
        if _is_expired(prev_state):
            _doom_games.pop(user_id, None)
            return True

        # Compute + send the updated state first, then clean up old messages.
        new_link = _append_key(prev_state.link, content)
        sent = await message.channel.send(_doom_prompt(message.author.mention, new_link))

        _doom_games[user_id] = DoomGameState(
            link=new_link,
            bot_message_id=sent.id,
            channel_id=sent.channel.id,
            updated_at=_now(),
        )

        # Delete the user's keypress message (silently ignore failures).
        try:
            await message.delete()
        except Exception:
            pass

        # Delete the previous bot game message (silently ignore failures).
        try:
            channel = client.get_channel(prev_state.channel_id)
            if channel:
                prev = await channel.fetch_message(prev_state.bot_message_id)
                await prev.delete()
        except Exception:
            pass
        return True

    return False


def has_active_game(user_id: int) -> bool:
    state = _doom_games.get(user_id)
    return bool(state) and not _is_expired(state)


def clear_game(user_id: int) -> None:
    _doom_games.pop(user_id, None)
