# `libraries/discord/` & `libraries/voice.py` — Shared Discord Utilities

Four modules providing Discord-specific shared functionality used across extensions.

---

## `admin.py` — Admin alerts & feature flags

**`send_error_to_admin(error, bot)`**
DMs the admin user (`CONFIG.ADMIN_USER_ID`) a red embed with the full traceback. Redacts `BOT_TOKEN` from the output. No-ops if admin user can't be fetched.

**`Features(str, Enum)`**
Feature flags for optional bot behaviours. Currently: `VOICE_ANNOUNCER`.
Flags are enabled by adding their literal string value to the bot's Discord application description (comma- or colon-separated).

**`has_features(*flags, bot) -> bool`**
Async check: returns True if all given flags are present in the bot's description. Use inside listeners.

**`requires_features(*flags)`**
Slash command check decorator (wraps `ipy.check`). **Not usable with listeners** — use `has_features` there instead.

---

## `api.py` — Discord REST session

**`get_api_session()`**
Async context manager. Returns an `aiohttp.ClientSession` pre-configured with the Discord API v10 base URL and `Authorization: Bot <token>` header.

**`get_bot_description() -> str`**
Fetches the bot's application description via `GET /applications/@me`. Returns `""` on failure. Used by the feature flag system in `admin.py`.

---

## `messaging.py` — Message helpers & link parsing

**`DiscordMesageLink(NamedTuple)`** — `guild_id`, `channel_id`, `message_id`; `.url` property reconstructs the full link.

**`is_messagable(channel) -> TypeGuard`**
Type guard for `ipy.TYPE_MESSAGEABLE_CHANNEL`. Use before sending messages to an arbitrary channel.

**`disable_message_components(msg) -> Message | None`**
Edits a message to disable all interactive components (buttons, selects). No-ops on `None` or messages without components.

**`get_discord_msg_links(content) -> Iterator[DiscordMesageLink]`**
Regex-based iterator over all `discord.com/channels/<g>/<c>/<m>` URLs in a string.

**`parse_discord_msg_link(link) -> DiscordMesageLink | None`**
Parses a single link string; returns `None` if invalid.

**`BAD_TWITTER_LINKS`** — `["https://twitter.com", "https://x.com"]`; used by extensions that rewrite tweet links.

---

## `voice.py` — BotVoice singleton & voice utilities

**`BotVoice`** — Singleton. Must be initialized at startup via `BotVoice.init(bot)` (done in `peanuts_bot/__init__.py`). Maintains a `queue.Queue` of audio work items and an `asyncio.Task` worker that plays them sequentially in the bot's current voice channel.

- `BotVoice().queue_audio(filename, callback=None)` — enqueues an audio file. If no worker is running, starts one. `callback(bot)` is awaited after playback (even on failure) — use for file cleanup (see `libraries/voice.py:build_cleanup_callback`).
- Audio plays via `ipy.ActiveVoiceState.play()` in `CONFIG.GUILD_ID`. Skips silently if bot is not in a VC.

**`get_active_user_ids(bot_vstate)`**
Generator of `Snowflake` IDs for non-bot members in the bot's current voice channel.

**`get_most_active_voice_channel(bot) -> GuildVoice | None`**
Finds the guild VC with the most non-bot users. Returns `None` if all VCs are empty.

**`announcer_rejoin_on_startup`** (`@ipy.listen(Startup)`)
On bot startup: if `VOICE_ANNOUNCER` feature is enabled and a non-empty VC exists, joins it and queues a TTS announcement (`"<botname> restarted."`).

---

## `libraries/voice.py` — TTS audio generation & cleanup

Non-Discord-specific voice layer. Consumed by `libraries/discord/voice.py`.

**`generate_tts_audio(text: str) -> str`**
Generates a gTTS audio file on disk using UK English accent (`tld="co.uk"`). Max 64 characters. Returns the filename (UUID-based `.wav`). Files are written to disk because interactions-py cannot play from an in-memory buffer (noted as a TODO in source).

**`build_cleanup_callback(filename) -> Callable`**
Returns an async callback that deletes the given file. Pass as the `callback` arg to `BotVoice().queue_audio()` so TTS files are cleaned up after playback.
