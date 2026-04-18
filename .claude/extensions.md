# Extensions

One section per extension. Open this file when working on any extension.

---

## `extensions/help.py` — `/help` command

**`HelpExtensions(ipy.Extension)`** — single `/help` slash command. Paginates all registered `application_commands` into embeds using `interactions.ext.paginators.Paginator` (select menu enabled, 5-minute timeout). Admin commands are hidden from non-admins.

**`SortOrder(int, Enum)`** — page ordering: `SLASH_CMD=0`, `CONTEXT_MENU=8`, `SLASH_ADMIN_CMD=16`.

**`HelpPage(dataclass)`**
- `from_command(c, *, ignore_admin=True) -> HelpPage | None` — factory for a single command page:
  - Reads embed color from the command's extension via `HelpCmdProto.get_help_color()`.
  - Returns `None` for admin commands when `ignore_admin=True`, and for parent/group slash commands with no description (detected by `_get_slash_cmd_desc`).
  - Parameter display: extracts `SlashCommandOption` from `Annotated[T, SlashCommandOption]` type metadata using `get_annotated_subtype`. Shows name, type, and optional flag.
- `to_embed() -> ipy.Embed` — renders the page as a Discord embed with each parameter as a field.

**Private helpers:**
- `_get_slash_cmd_desc(c)` — returns `None` for parent/group commands (no direct invocation use).
- `_requires_admin(c)` — checks `default_member_permissions & ADMINISTRATOR`.
- `_get_cmd_option(p)` — unwraps `SlashCommandOption` from `Annotated` parameter metadata; returns `None` if metadata is missing or malformed.

---

## `extensions/roles.py` — `/role` commands

**`RoleExtension(ipy.Extension)`** — manages user-joinable mention roles. A role is considered "joinable" if it is `mentionable=True` and has `permissions == Permissions.NONE` (checked by `is_joinable()`).

**Commands (all subcommands of `/role`):**
- `/role create <name>` — creates a new mentionable role with zero permissions. Rejects if a role with that name already exists.
- `/role delete <role>` — deletes a joinable role. Rejects if the role is not joinable or still has other members.
- `/role join` — sends an ephemeral dropdown of joinable roles the user hasn't joined yet. Selection handled by `join_selection` component callback (`custom_id="role_join"`).
- `/role leave` — sends an ephemeral dropdown of joinable roles the user is currently in. Selection handled by `leave_selection` component callback (`custom_id="role_leave"`).

**Dropdown selection flow:**
Both join/leave callbacks use `get_valid_roles()` — an async generator that fetches each selected role, re-validates joinability, applies a `should_skip` predicate (already in role → skip join; not in role → skip leave), and calls `invalid_role_callback` for roles that no longer exist or aren't joinable.

**Encoding:** dropdown option values encode `role.id|role.name` via `get_role_option_value` / `split_role_option_value` to avoid a fetch-before-display round trip.

---

## `extensions/channels.py` — `/channel` commands + voice auto-management

**`ChannelExtension(ipy.Extension)`**

**`/channel create <name> [category]`** — creates a text channel, optionally nested under a category. Rejects if a non-category channel with that name already exists.

**Voice event listeners** (all gated on `Features.VOICE_ANNOUNCER`; all ignore bot-triggered events):

- `announce_user_join` (`VoiceUserJoin`) — when a user joins a VC: if bot isn't in any VC, joins that channel; if bot is in the same channel, plays a join announcement.
- `announce_user_move` (`VoiceStateUpdate`) — when a user moves between VCs: if bot's current channel is now empty (only the moving user remains), follows the user; plays an announcement if the destination is already active with others.
- `bot_leave` (`VoiceUserLeave`) — when a user leaves the bot's VC: if other non-bot users remain, stays; if no users remain, disconnects or moves to the most active VC (via `get_most_active_voice_channel`) and announces arrival.

**`_play_announcer_audio(user, action)`** — waits 1 second (to let voice state settle), generates TTS (`"<username> has joined/left."`), queues it via `BotVoice()` with a cleanup callback.

---

## `extensions/users.py` — User info automation

**`UserExtension(ipy.Extension)`** — no slash commands; one passive listener.

**`add_username_to_nickname`** (`on_member_update`) — enforces that every member's nickname contains their username. On any nick update:
- If nick is `None` (reset), does nothing.
- If username already in nick, does nothing.
- Otherwise appends ` [username]` to the nick.
- If the result exceeds 32 characters, resets the nick to `None` and DMs the user to shorten it.
- Silently swallows HTTP error code `50013` (Missing Permissions — e.g. can't edit admins' nicks).

---

## `extensions/messages.py` — Message utility commands & automation

**`MessageExtension(ipy.Extension)`**

**Admin-only slash commands:**
- `/speak <message>` — bot sends the message text verbatim.
- `/messages delete [amount=1]` — bulk-deletes last N messages in the channel (defers ephemerally first).

**User slash commands:**
- `/quote <link>` — fetches the linked message and sends it as a quote embed (author, content, image, timestamp, channel footer, jump link).

**Passive listeners (`on_message_create`):**
- `auto_quote` — detects Discord message links in any message and auto-replies with a quote embed (first link only).
- `auto_fix_twitter_links` — if message contains `twitter.com` or `x.com`, replies with a blockquoted version where those are replaced with `fxtwitter.com`, then suppresses original embeds.
- `send_league_ping_check` — if a message mentions `CONFIG.LEAGUE_ROLE_ID`, replies with a `_LeagueOptions` dropdown (Yes/Aram/Ranked/Penta/Later/No) and a "Ping to gather" button.

**League ping flow:**
1. User selects availability via `_LEAGUE_DROPDOWN` callback. "Later" triggers a modal asking for a time. User's mention is appended to the relevant row in the bot's message.
2. Admin clicks "Ping to gather" (`_LEAGUE_PING_BUTTON`) → picks game mode (Ranked/Aram/Either) → bot replies mentioning all opted-in users, excluding those who picked "No" or the excluded mode.

---

## `extensions/emojis.py` — Emoji request & approval flow

**`EmojiExtension(ipy.Extension)`**

**Entry points (both route through `_request_emoji`):**
- `/emoji <shortcut> <attachment>` — slash command; user uploads an image directly.
- `Convert to Emoji` (message context menu) — right-click a message; modal collects a shortcut name per image (up to 5). Each image with a name entered creates a separate request.

**`_request_emoji(req, ctx)`** — validates file type (PNG/JPEG/GIF only), file size (≤ `MAX_EMOJI_FILE_SIZE` = 256 KB), and shortcut format (alphanumeric + underscore, ≥ 2 chars). DMs the admin user an approval message with Approve/Deny buttons.

**`EmojiRequest(dataclass)`** — holds request data. `to_approval_msg()` / `from_approval_msg()` serialize/deserialize the DM text so the approval callback can reconstruct the request without a database.

**Admin approval callbacks:**
- `approve_emoji` — downloads the image URL and calls `guild.create_custom_emoji()`; notifies the requester in their original channel.
- `reject_emoji` → opens a rejection reason modal → `reject_emoji_modal` sends the reason to the requester.
- Both disable the Approve/Deny buttons on the admin DM after completion via `.post_run` hooks and `disable_message_components`.

---

## `extensions/rng.py` — Random & dice commands

**`RngExtension(ipy.Extension)`**

- `/random <min> <max>` — generates a random integer (inclusive). Sends result in a code block with a "Randomize Again" button. Each re-roll appends to the same message (italicised latest result). Button `custom_id` encodes `random_<min>_<max>`.
- `/roll <expression>` — parses dice notation via `parse_dice_roll` (e.g. `2d6+3`). Shows individual rolls and total. "Roll Again" button re-uses the same expression. Button `custom_id` encodes `roll_<DiceRoll.__str__>`.

**`append_new_result(msg, result, is_first)`** — helper that appends a new result line inside the trailing code block of a message, italicising all but the most recent.

---

## `extensions/stocks.py` — Stock lookup commands

Only loaded when `CONFIG.ALPHAV_CONNECTED` guard passes. Uses matplotlib for chart generation (this is where the matplotlib dependency lives, not `libraries/image.py`).

**`StockExtension(ipy.Extension)`**

- `/stock <ticker>` — fetches daily stock history via `StockAPI(AlphaV).get_stock(ticker)`, generates a matplotlib line chart (`_gen_stock_graph`), sends embed + chart PNG. Autocomplete on the `ticker` field searches symbols via `StockAPI(AlphaV).search_symbol()` (note: autocomplete is API rate-limited, warned in description).
- Raises `BotUsageError` on `StocksAPIRateLimitError`; other errors propagate to the global handler.

**`daily_stock_to_embed(stock, *, graph)`** — builds the embed: title links to Yahoo Finance, description shows close delta (coloured diff block), fields from `stock.get_summary()`, image set to the attached graph file.

**`_gen_stock_graph(stock)`** — renders a matplotlib figure (15×10, dpi=60) of closing prices over time. Uses `"agg"` backend (no display). Returns an `ipy.File` from a `BytesIO` buffer, or `None` if fewer than 2 data points.

---

## `extensions/minecraft.py` — Minecraft server commands

Only loaded when `CONFIG.MC_CONFIG` guard passes. Reads config via `MC_CONFIG()` at module import time.

**`MinecraftExtension(ipy.Extension)`**

- `/minecraft status` — queries the server via `mcstatus.JavaServer`. Three states: online (green embed, player count, version), offline (`ConnectionRefusedError`/`OSError` → red embed), unknown error (black embed + DMs admin). Server icon decoded via `decode_b64_image` and attached as thumbnail.
- `/minecraft link <username>` — validates username against Mojang API (`get_minecraft_user`, 5-min cache), then whitelists via `tailscale ssh` into a `screen` session running the MC server (`whitelist add <username>`).
- `/minecraft unlink <username>` — same flow but `whitelist remove`.

**`_whitelist_user(username, operation)`** — runs `tailscale ssh <MC_TS_HOST> '/usr/bin/screen -S mc-peanuts -X stuff "/whitelist <op> <user>\n"'` as a subprocess. Uses `shlex.quote` on user-supplied values.

---

## `extensions/local.py` — Dev-only commands

Only loaded when `CONFIG.IS_LOCAL` is true.

**`LocalExtension(ipy.Extension)`**

- `/reload <ext>` (admin-only) — reloads a bot extension at runtime. Choices are populated from `ALL_EXTENSIONS`. Known limitation: patterned component callbacks may not unload cleanly (TODO in source).
