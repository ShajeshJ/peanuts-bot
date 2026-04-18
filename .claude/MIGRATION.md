# interactions-py → discord.py Migration Guide

## Overview

This document is the single source of truth for the migration from `discord-py-interactions` to `discord.py`. It tracks:
- The ordered migration steps
- Which files are changed per step
- Which user stories to verify before marking a step complete
- Open questions that must be answered before the step can begin

---

## Open Questions

These must be resolved before the affected migration step begins. Leave a note inline once answered.

### OQ-1 · FFmpeg on the Pi (blocks Step 7)

discord.py's voice playback (`discord.FFmpegPCMAudio`) requires FFmpeg to be installed on the host machine. The Pi's current voice setup uses interactions-py's built-in audio. 

**Action needed:** Confirm FFmpeg is installed on the Pi.
```bash
ssh pi@<pi-host> which ffmpeg
```
If missing, install it first: `sudo apt install ffmpeg`

**Answered:** FFmpeg is already installed on the Pi. No setup needed before Step 7.

---

### OQ-2 · Help command paginator strategy (blocks Step 8)

`interactions.ext.paginators.Paginator` does not exist in discord.py. The current `/help` command also introspects `self.bot.application_commands` (an ipy type) and `ipy.SlashCommandOption` metadata.

Two options:
- **A (recommended):** Implement a minimal paginator `discord.ui.View` (prev/next buttons + select menu). Introspect commands via `bot.tree.get_commands(guild=...)` — each `discord.app_commands.Command` exposes `.parameters` with `.name`, `.description`, `.required`, `.type`. This is actually cleaner than the ipy approach.
- **B:** Simplify `/help` to a flat embed list (no pagination) to reduce migration scope.

**Action needed:** Decide approach before Step 8.

**Answered:** Option A — build a custom paginator `discord.ui.View` with prev/next buttons + select menu.

---

### OQ-3 · `guild.fetch_role(id)` replacement (blocks Step 4)

`roles.py` calls `ctx.guild.fetch_role(role_id)` to re-validate a role by ID. discord.py has no `Guild.fetch_role(id)` method — only `Guild.get_role(id)` (from cache) or `Guild.fetch_roles()` (fetches all roles).

Options:
- Use `guild.get_role(role_id)` — relies on cache being populated, which it should be for guild-scoped bots with the Members intent
- Use `guild.fetch_roles()` and search — works but fetches all roles for every selection

**Action needed:** Decide approach (recommendation: use `guild.get_role()` with fallback log warning).

**Answered:** Use `guild.get_role(id)` (cache lookup). Safe given the bot uses all intents.

---

### OQ-4 · Voice audio format: disk files vs. BytesIO (blocks Step 7)

The current `libraries/voice.py` generates gTTS audio and saves to disk with a `.wav` extension (but gTTS actually writes MP3 format — the `.wav` name is a latent bug that ipy tolerates). The comment in the file says BytesIO doesn't work with interactions-py.

With discord.py + FFmpegPCMAudio, we **can** pipe from BytesIO:
```python
discord.FFmpegPCMAudio(io.BytesIO(data), pipe=True)
```
This would eliminate disk I/O and the build-cleanup callback pattern entirely.

**Action needed:** Decide whether to switch to BytesIO in Step 7, or keep the disk-file approach (simpler migration, lower risk). Also decide whether to fix the `.wav` → `.mp3` extension.

**Answered:** Keep disk-file approach for now. Fix the extension to `.mp3` (correctness). Add a TODO comment in `libraries/voice.py` to switch to BytesIO after migration is complete.

---

### OQ-5 · discord.py version pin (blocks Step 1)

`DynamicItem` support (needed for regex-matched custom_ids in rng.py) was introduced in discord.py 2.4.0. We should pin a specific version.

**Recommendation:** `discord.py[voice] = "^2.4.0"` — picks up the latest 2.x with DynamicItem and all intents support.

**Action needed:** Confirm version before updating `pyproject.toml` in Step 1.

**Answered:** Pin to `2.7.1` (latest stable as of 2026-04-18, includes DynamicItem support).

---

## Migration Progress

| Step | Status | Description |
|---|---|---|
| 1 | `[x] done` | Core infrastructure: dependencies + bot startup (no extensions) |
| 2 | `[x] done` | `users.py` + `channels.py` (channel create only, no voice) |
| 3 | `[ ] pending` | `rng.py` (slash commands + DynamicItem buttons) |
| 4 | `[ ] pending` | `roles.py` (slash commands + persistent View dropdowns) |
| 5 | `[ ] pending` | `messages.py` (listeners + league ping flow) |
| 6 | `[ ] pending` | `emojis.py` (modals + context menu + persistent approval View) |
| 7 | `[ ] pending` | Voice infrastructure (`libraries/discord/voice.py` + voice events) |
| 8 | `[ ] pending` | `help.py` (custom paginator + discord.py tree introspection) |
| 9 | `[ ] pending` | `stocks.py`, `minecraft.py`, `local.py` |
| 10 | `[ ] pending` | Remove `discord-py-interactions` from all code and dependencies |

Mark each step `[x] done` after you have verified the user stories and committed.

---

## Conventions for Every Step

Before closing any step:
1. Run `mypy peanuts_bot/` — must pass with no new errors
2. Run `ruff format peanuts_bot/` — must be clean (run `ruff format peanuts_bot/` to auto-fix)
3. Tell the user what to run (`make run`) and which user stories to verify — then **stop and wait**
4. Only after the user confirms the stories pass: update the step status in the Migration Progress table and commit: `git commit -m "refactor: <description>"`
5. Confirm with the user before starting the next step (you may want to pause between sessions)

---

## Step 1 — Core Infrastructure

**Goal:** Replace the ipy `Client` with a discord.py `commands.Bot`. No extensions loaded yet. The bot should come online in Discord and appear as "online" in the server member list.

**Requires OQ-5 answered first.**

### Setup — install discord.py

```bash
# In pyproject.toml:
# - Add: discord-py = { version = "^2.4.0", extras = ["voice"] }
# - Keep discord-py-interactions for now (extensions still use it until Step 10)
poetry add "discord.py[voice]"
```

### Files changed

| File | Change |
|---|---|
| `pyproject.toml` | Add `discord.py[voice]`, keep `discord-py-interactions` |
| `peanuts_bot/__init__.py` | Replace `ipy.Client` with `commands.Bot` subclass, async `setup_hook`, no extensions loaded yet |
| `peanuts_bot/errors.py` | Replace `@ipy.listen` with `on_app_command_error` hook; keep `BotUsageError` and `SOMETHING_WRONG` as-is |
| `peanuts_bot/extensions/internals/protocols.py` | `ipy.Color` → `discord.Color` |
| `peanuts_bot/libraries/discord/admin.py` | `ipy.Client` → `discord.Client`, `ipy.BrandColors.RED` → `discord.Color.red()`, `EMBED_MAX_DESC_LENGTH` → `4096`, use `await bot.application_info()` for description |
| `peanuts_bot/libraries/discord/messaging.py` | `ipy.TYPE_MESSAGEABLE_CHANNEL` → `discord.abc.Messageable`; rewrite `disable_message_components` with `View.from_message()` |
| `peanuts_bot/extensions/__init__.py` | Drop `to_slash_command_choice()` from `ExtInfo` (ipy-specific); `ALL_EXTENSIONS` list unchanged |

### Key implementation notes

**`peanuts_bot/__init__.py`:**
```python
# New structure — discord.py commands.Bot with async setup_hook
class PeanutsBot(commands.Bot):
    async def setup_hook(self):
        # Extensions loaded here in Step 2+; empty for Step 1
        for proto in REQUIRED_EXTENSION_PROTOS:
            for cog in self.cogs.values():
                if not isinstance(cog, proto):
                    raise RuntimeError(f"{cog.__class__.__name__} does not implement {proto.__name__}")

        guild = discord.Object(id=CONFIG.GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def on_ready(self):
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="/help")
        )

bot = PeanutsBot(
    command_prefix="!",  # unused but required by commands.Bot
    intents=discord.Intents.all(),
)
```

Note: `tree.sync()` replaces the full guild command list on each sync, which is equivalent to `delete_unused_application_cmds=True`.

**`peanuts_bot/__init__.py` — error handler wiring:**
Do NOT use `on_app_command_error` as a Bot method — it is not automatically wired to `CommandTree.on_error`. Instead subclass `CommandTree` and pass it via `tree_cls`:

```python
class _PeanutsTree(app_commands.CommandTree):
    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        await handle_interaction_error(interaction, error)

bot = PeanutsBot(..., tree_cls=_PeanutsTree)
```

Errors from component callbacks (View buttons/selects) go to each View's `on_error` method — see Step 3+ for the shared error handler pattern.

```python
async def handle_interaction_error(interaction: discord.Interaction, error: Exception):
    """Shared error handler for slash commands and View callbacks"""
    cause = getattr(error, '__cause__', error)  # unwrap TransformerError etc.
    if isinstance(cause, BotUsageError):
        await interaction.response.send_message(str(cause), ephemeral=True)
        return
    try:
        await interaction.response.send_message(SOMETHING_WRONG, ephemeral=True)
    except discord.InteractionResponded:
        await interaction.followup.send(SOMETHING_WRONG, ephemeral=True)
    await send_error_to_admin(cause, interaction.client)
    raise cause
```

**`libraries/discord/messaging.py` — `disable_message_components`:**
```python
async def disable_message_components(msg: discord.Message | None) -> discord.Message | None:
    if msg is None or not msg.components:
        return msg
    view = discord.ui.View.from_message(msg, timeout=None)
    for child in view.children:
        child.disabled = True
    return await msg.edit(view=view)
```

**`libraries/discord/admin.py` — `has_features`:**
`bot.app.description` (sync, ipy-specific) → use the existing `get_bot_description()` from `libraries/discord/api.py` (already pure aiohttp, no ipy). No changes needed to `api.py`.

### User stories to verify
- Bot appears **online** in the Discord server member list
- No slash commands appear (none loaded yet — expected)
- Check logs for any startup errors

### Commit message
`refactor: migrate core bot infrastructure to discord.py`

---

## Step 2 — `users.py` + `channels.py` (channel create only)

**Goal:** Load two extensions. Voice events in `channels.py` are temporarily skipped; they are restored in Step 7.

### Files changed

| File | Change |
|---|---|
| `peanuts_bot/__init__.py` | Add `extensions/users` and `extensions/channels` to `setup_hook` load list |
| `peanuts_bot/extensions/users.py` | `ipy.Extension` → `commands.Cog`; listener → `@commands.Cog.listener()`; ipy HTTP errors → `discord.HTTPException` |
| `peanuts_bot/extensions/channels.py` | `ipy.Extension` → `commands.Cog`; channel create slash command migrated; voice listeners (`announce_user_join`, `announce_user_move`, `bot_leave`) **commented out with TODO** until Step 7 |

### Key implementation notes

**Extension pattern (discord.py):**
```python
class UserExtension(commands.Cog):
    @staticmethod
    def get_help_color() -> discord.Color:
        return discord.Color.from_str("#1ABC9C")  # was ipy.FlatUIColors.GREENSEA

    @commands.Cog.listener("on_member_update")
    async def add_username_to_nickname(self, before: discord.Member, after: discord.Member):
        ...
```

**Slash commands (discord.py):**
```python
channel_group = app_commands.Group(name="channel", description="Channel management")

class ChannelExtension(commands.Cog):
    @staticmethod
    def get_help_color() -> discord.Color: ...

    @channel_group.command(name="create")
    @app_commands.describe(name="The name of the new channel", category="Category to nest the channel under")
    async def create(self, interaction: discord.Interaction, name: str, category: Optional[discord.CategoryChannel] = None):
        ...
```

Note: do NOT use `channel = _channel_group` as a Cog class attribute — the Cog metaclass copies the group and alters callback dispatch, causing `CommandSignatureMismatch` at runtime. Instead register the group directly on the tree in `setup()`:
```python
async def setup(bot: commands.Bot) -> None:
    bot.tree.add_command(_channel_group)
    await bot.add_cog(ChannelExtension())
```

**Color mapping** (reference for all steps):
| ipy color | discord.py replacement |
|---|---|
| `ipy.FlatUIColors.GREENSEA` | `discord.Color.from_str("#1ABC9C")` |
| `ipy.FlatUIColors.ALIZARIN` | `discord.Color.from_str("#E74C3C")` |
| `ipy.FlatUIColors.PETERRIVER` | `discord.Color.from_str("#3498DB")` |
| `ipy.FlatUIColors.CARROT` | `discord.Color.from_str("#E67E22")` |
| `ipy.FlatUIColors.CLOUDS` | `discord.Color.from_str("#ECF0F1")` |
| `ipy.FlatUIColors.SUNFLOWER` | `discord.Color.from_str("#F1C40F")` |
| `ipy.FlatUIColors.MIDNIGHTBLUE` | `discord.Color.from_str("#2C3E50")` |
| `ipy.BrandColors.RED` | `discord.Color.red()` |

**`ipy.errors.HTTPException`** → `discord.HTTPException` (same structure: `.status`, `.code`)

**`ctx.guild.fetch_channels()`** → `guild.fetch_channels()`  (same method name, same return)

**Channel type check:** `c.type != ipy.ChannelType.GUILD_CATEGORY` → `not isinstance(c, discord.CategoryChannel)`

**`ctx.guild.create_channel(channel_type=ipy.ChannelType.GUILD_TEXT, ...)`** → `guild.create_text_channel(name=name, category=category, reason=...)`

**`channel.mention`** → same in discord.py (`.mention` is a Discord.py property too)

**`ctx.author.display_name`** → `interaction.user.display_name`

**`member.edit_nickname(None, reason=...)`** → `member.edit(nick=None, reason=...)`

**`member.send(...)`** → same in discord.py

### Setup for this step
```bash
poetry install
make run
```

### User stories to verify
- U-1 through U-5 (username enforcement)
- C-1 through C-3 (channel create)

### Commit message
`refactor: migrate users and channel create extensions to discord.py`

---

## Step 3 — `rng.py`

**Goal:** Migrate the dice roller. Buttons use `discord.ui.DynamicItem` with regex templates for persistent, pattern-matched custom IDs — the discord.py equivalent of `@ipy.component_callback(REGEX)`.

### Files changed

| File | Change |
|---|---|
| `peanuts_bot/extensions/rng.py` | Full rewrite using `commands.Cog`, `app_commands`, `DynamicItem` buttons |
| `peanuts_bot/__init__.py` | Register `RandomButton` and `RollButton` via `bot.add_dynamic_items(...)` in `setup_hook`; add `rng` to extension load list |

### Key implementation notes

**`discord.ui.DynamicItem` pattern:**
```python
class RandomButton(discord.ui.DynamicItem[discord.ui.Button], template=r'random_(?P<min>-?\d+)_(?P<max>-?\d+)'):
    def __init__(self, min_val: int, max_val: int):
        super().__init__(
            discord.ui.Button(
                label="Randomize Again",
                style=discord.ButtonStyle.primary,
                custom_id=f"random_{min_val}_{max_val}",
            )
        )
        self.min_val = min_val
        self.max_val = max_val

    @classmethod
    async def from_custom_id(
        cls,
        interaction: discord.Interaction,
        item: discord.ui.Button,
        match: re.Match[str],
    ) -> "RandomButton":
        return cls(int(match["min"]), int(match["max"]))

    async def callback(self, interaction: discord.Interaction):
        if not interaction.message:
            return
        content = append_new_result(interaction.message.content, str(random.randint(self.min_val, self.max_val)))
        await interaction.response.edit_message(content=content)
```

Register in `setup_hook`:
```python
bot.add_dynamic_items(RandomButton, RollButton)
```

Sending a message with the dynamic button:
```python
view = discord.ui.View()
view.add_item(RandomButton(min_val, max_val))
await interaction.response.send_message(content, view=view)
```

Error handling in DynamicItem callbacks: override `on_error` on the item or catch inline.

**`ipy.ComponentContext` → `discord.Interaction`** (same pattern everywhere)

**`ctx.edit_origin(content=..., components=...)`** → `interaction.response.edit_message(content=..., view=view)` (reconstruct view from existing components or pass new view)

### User stories to verify
- RN-1 through RN-3 (random number)
- RL-1 through RL-4 (dice roll)

### Commit message
`refactor: migrate rng extension to discord.py with DynamicItem buttons`

---

## Step 4 — `roles.py`

**Goal:** Migrate role management commands. Dropdowns use a persistent `discord.ui.View` with fixed `custom_id`s.

**Requires OQ-3 answered first.**

### Files changed

| File | Change |
|---|---|
| `peanuts_bot/extensions/roles.py` | Full rewrite; `commands.Cog`, `app_commands.Group`, persistent dropdown Views |
| `peanuts_bot/__init__.py` | Register persistent Views; add `roles` to extension load list |

### Key implementation notes

**Persistent dropdown View:**
```python
class RoleJoinView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(custom_id=ROLE_JOIN_ID, placeholder="Join a mention role", min_values=1, max_values=25)
    async def join_selection(self, interaction: discord.Interaction, select: discord.ui.Select):
        ...
```

**Sending with dynamic options** (options aren't part of the persistent class definition — they're set at send time):
```python
view = RoleJoinView()
view.join_selection.options = [
    discord.SelectOption(label=role.name, value=get_role_option_value(role))
    for role in joinable_roles
]
view.join_selection.max_values = len(view.join_selection.options)
await interaction.response.send_message(view=view, ephemeral=True)
```

Register in `setup_hook`:
```python
bot.add_view(RoleJoinView())
bot.add_view(RoleLeaveView())
```

**`guild.fetch_role(id)`** → `guild.get_role(int(role_id))` (cache lookup; acceptable with Members intent active)

**`ipy.Snowflake(int(r_id))`** → `int(r_id)` (just a plain int)

**`ctx.author.has_role(role)`** → `role in interaction.user.roles` (discord.py Member has a `.roles` list)

**`role.id in ctx.author.roles`** → `discord.utils.get(interaction.user.roles, id=role.id) is not None`

**`ipy.Permissions.NONE`** → `discord.Permissions.none()`

**`r.permissions == _JOINABLE_PERMISSION_SET`** → `r.permissions == discord.Permissions.none()`

**`role.members`** → `role.members` (same in discord.py)

**`member.add_role(role, reason)`** → `member.add_roles(role, reason=reason)`

**`member.remove_role(role, reason)`** → `member.remove_roles(role, reason=reason)`

**`ctx.guild.create_role(name, mentionable, reason, permissions)`** → `guild.create_role(name=name, mentionable=True, reason=reason, permissions=discord.Permissions.none())`

### User stories to verify
- R-1 through R-13

### Commit message
`refactor: migrate roles extension to discord.py with persistent Views`

---

## Step 5 — `messages.py`

**Goal:** Migrate message utility commands and all passive listeners including the league ping flow. This is the most complex extension due to modals, multi-step interactions, and message content parsing.

### Files changed

| File | Change |
|---|---|
| `peanuts_bot/extensions/messages.py` | Full rewrite; `commands.Cog`, listeners, modals, persistent Views |
| `peanuts_bot/__init__.py` | Register league ping Views; add `messages` to extension load list |

### Key implementation notes

**Listeners:**
```python
@commands.Cog.listener("on_message")
async def auto_quote(self, message: discord.Message): ...

@commands.Cog.listener("on_message")
async def auto_fix_twitter_links(self, message: discord.Message): ...

@commands.Cog.listener("on_message")
async def send_league_ping_check(self, message: discord.Message): ...
```

Note: `on_message` in discord.py passes `discord.Message` directly, not an event wrapper.

**`msg.mention_roles`** — discord.py `Message.role_mentions` returns `list[discord.Role]` synchronously (from cache). No `async for`.

**`ipy_misc_utils.mention_reg`** — replace with a local Discord mention regex:
```python
_MENTION_REGEX = re.compile(r"<@[!&]?\d+>|<#\d+>")
```
Or more specifically for user mentions: `re.compile(r"<@!?\d+>")`

**`ctx.channel.purge(deletion_limit=N)`** → `channel.purge(limit=N)` — returns list of deleted messages; use `len()` for count. Note: discord.py `purge` raises on 0 deleted, handle gracefully.

**`ctx.defer(ephemeral=True)`** → `await interaction.response.defer(ephemeral=True)`, then `await interaction.followup.send(...)` for the reply.

**`msg.suppress_embeds()`** → `await msg.edit(suppress=True)`

**League ping modal:**
```python
class LeagueLaterModal(discord.ui.Modal, title="Confirm Time"):
    time_input = discord.ui.TextInput(
        label="When?",
        style=discord.TextStyle.short,
        placeholder="Leave blank to not specify",
        required=False,
    )

    def __init__(self, original_message: discord.Message, author: discord.Member):
        super().__init__()
        self.original_message = original_message
        self.author = author

    async def on_submit(self, interaction: discord.Interaction):
        entry = f" {self.author.mention}"
        if self.time_input.value:
            entry += f" ({self.time_input.value})"
        # update message content rows
        ...
        await interaction.response.edit_message(content=..., view=view)
```

**`bot.wait_for_modal(modal, author_id)`** (ipy) → not needed in discord.py; the modal handles its own `on_submit`. Send the modal directly:
```python
await interaction.response.send_modal(LeagueLaterModal(ctx.message, interaction.user))
```

**League ping persistent views** — `LeagueDropdownView` and `LeaguePingView` with fixed `custom_id`s. Register in `setup_hook`.

**`ctx.edit_origin(content=..., components=[])`** → `interaction.response.edit_message(content=..., view=discord.ui.View())` (empty View removes all components)

**`ctx.message.get_referenced_message()`** (ipy) → `message.reference.resolved` if `message.reference else None` (discord.py)

### User stories to verify
- SP-1 through SP-3
- MD-1 through MD-3
- Q-1 through Q-3
- AQ-1 through AQ-3
- TW-1 through TW-3
- LP-1 through LP-8

### Commit message
`refactor: migrate messages extension to discord.py`

---

## Step 6 — `emojis.py`

**Goal:** Migrate emoji request + approval flow. Uses context menus, modals, and persistent Views (approval buttons must survive bot restarts).

### Files changed

| File | Change |
|---|---|
| `peanuts_bot/extensions/emojis.py` | Full rewrite; `commands.Cog`, `app_commands.context_menu`, `discord.ui.Modal`, persistent approval View |
| `peanuts_bot/__init__.py` | Register `EmojiApprovalView`; add `emojis` to extension load list |

### Key implementation notes

**Context menu:**
```python
@app_commands.context_menu(name="Convert to Emoji")
async def emoji_from_attachment(self, interaction: discord.Interaction, message: discord.Message):
    ...
```
Context menus are registered on the tree directly, not on a Cog command group. Add via `self.bot.tree.add_command(...)` in `cog_load`:
```python
async def cog_load(self):
    self.bot.tree.add_command(self.emoji_from_attachment)

async def cog_unload(self):
    self.bot.tree.remove_command("Convert to Emoji", type=discord.AppCommandType.message)
```

**Dynamic modal (multiple fields):**
```python
class EmojiNamesModal(discord.ui.Modal, title="Emoji Names"):
    def __init__(self, images: list[discord.Attachment | discord.Embed], message_id: int):
        super().__init__()
        self.message_id = message_id
        for i, img in enumerate(images):
            self.add_item(discord.ui.TextInput(
                label=f"shortcut for {_get_file_name(img)}",
                custom_id=f"{SHORTCUT_TEXT_PREFIX}{i}",
                style=discord.TextStyle.short,
                placeholder="Leave blank to skip this image",
                required=False,
            ))

    async def on_submit(self, interaction: discord.Interaction):
        values = {item.custom_id: item.value for item in self.children if isinstance(item, discord.ui.TextInput)}
        ...
```

**`ctx.responses`** (ipy ModalContext) → iterate `self.children` (TextInput items) in `on_submit`; `item.value` is the submitted text.

**`ctx.custom_id`** (ipy ModalContext) → not available in discord.py Modal; pass message_id as constructor parameter instead.

**Persistent approval View:**
```python
class EmojiApprovalView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, custom_id=APPROVE_EMOJI_BTN)
    async def approve_emoji(self, interaction: discord.Interaction, button: discord.ui.Button):
        ...
        await disable_message_components(interaction.message)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger, custom_id=REJECT_EMOJI_BTN)
    async def reject_emoji(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EmojiRejectModal(interaction.message))
```

The `.post_run` hook (ipy-specific) → just call `disable_message_components` inline at the end of each button callback.

**`guild.create_custom_emoji(name, image, reason)`** → `guild.create_custom_emoji(name=name, image=bytes_data, reason=reason)` where `image` must be `bytes` (not `BytesIO`). Use `await res.read()` instead of `res.content.read()`.

**`bot.fetch_member(id, guild_id)`** (ipy) → `guild.fetch_member(id)` (discord.py)

### User stories to verify
- E-1 through E-6
- CE-1 through CE-6

### Commit message
`refactor: migrate emojis extension to discord.py`

---

## Step 7 — Voice Infrastructure

**Goal:** Migrate `libraries/discord/voice.py` (BotVoice) and `libraries/voice.py` (TTS generation) to discord.py. Re-enable the voice event listeners in `channels.py`.

**Requires OQ-1 (FFmpeg) and OQ-4 (audio format) answered first.**

### Files changed

| File | Change |
|---|---|
| `peanuts_bot/libraries/voice.py` | Replace `ipyaudio.AudioVolume` reference with FFmpegPCMAudio; optionally switch to BytesIO; fix `.wav` → `.mp3` file extension |
| `peanuts_bot/libraries/discord/voice.py` | Full rewrite; replace `ipy.Client`, `bot.connect_to_vc()`, `bot.get_bot_voice_state()`, `ipyaudio.AudioVolume`, `ActiveVoiceState` with discord.py equivalents |
| `peanuts_bot/extensions/channels.py` | Uncomment voice listeners; migrate them from ipy events to discord.py `on_voice_state_update` |
| `peanuts_bot/__init__.py` | Re-register startup voice listener (`announcer_rejoin_on_startup`) |

### Key implementation notes

**Voice API mapping:**

| interactions-py | discord.py |
|---|---|
| `bot.connect_to_vc(guild_id, channel_id, muted, deafened)` | `await channel.connect(self_deaf=True)` |
| `bot.get_bot_voice_state(guild_id)` | `guild.voice_client` (returns `discord.VoiceClient \| None`) |
| `bot_vstate.connected` | `voice_client.is_connected()` |
| `bot_vstate.channel` | `voice_client.channel` |
| `bot_vstate.channel.voice_members` | `voice_client.channel.members` |
| `await bot_vstate.play(AudioVolume(filename))` | `voice_client.play(FFmpegPCMAudio(filename))` + asyncio.Event for completion |
| `event.channel.disconnect()` | `await guild.voice_client.disconnect()` |

**Audio playback with completion tracking:**

discord.py's `voice_client.play()` is non-blocking and takes an `after: Callable[[Exception | None], None]` callback (not a coroutine). The queue worker needs to use an `asyncio.Event` to wait for each track:

```python
async def _play_audio(voice_client: discord.VoiceClient, filename: str):
    done = asyncio.Event()

    def after_play(error: Exception | None):
        if error:
            logger.warning("audio playback error", exc_info=error)
        voice_client._state.loop.call_soon_threadsafe(done.set)

    voice_client.play(discord.FFmpegPCMAudio(filename), after=after_play)
    await done.wait()
```

**Voice events — `ipy.events.VoiceUserJoin` / `VoiceUserLeave` → `on_voice_state_update`:**

discord.py merges join, leave, and move into one event:
```python
@commands.Cog.listener("on_voice_state_update")
async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    joined = before.channel is None and after.channel is not None  # VoiceUserJoin
    left   = before.channel is not None and after.channel is None  # VoiceUserLeave
    moved  = before.channel is not None and after.channel is not None and before.channel != after.channel  # VoiceStateUpdate (move)
```

The three ipy listeners (`announce_user_join`, `announce_user_move`, `bot_leave`) merge into a single `on_voice_state_update` handler that branches on `joined / left / moved`.

**`BotVoice.init(bot)`** — `ipy.Client` → `discord.Client`

**Startup rejoin listener:**
```python
# In setup_hook or on_ready:
async def on_ready(self):
    guild = self.bot.get_guild(CONFIG.GUILD_ID)
    if not guild or not await has_features(Features.VOICE_ANNOUNCER, bot=self.bot):
        return
    vc_to_join = get_most_active_voice_channel(self.bot)
    if vc_to_join:
        await vc_to_join.connect(self_deaf=True)
        ...
```

**`get_most_active_voice_channel`:**
`guild.channels` in discord.py includes all channels. Filter for `discord.VoiceChannel`, and use `.members` (all members including bots) filtering out `member.bot`.

**`get_active_user_ids`:**
`bot_vstate.channel.voice_members` (ipy) → `voice_client.channel.members` (discord.py) filtered by `not m.bot`.

**Voice channel connect to a specific channel (for move):**
discord.py: if already connected, use `await voice_client.move_to(new_channel)` instead of calling `connect()` again.

### User stories to verify
- V-1 through V-10

### Commit message
`refactor: migrate voice infrastructure to discord.py`

---

## Step 8 — `help.py`

**Goal:** Migrate the `/help` command. Requires building a custom paginator View to replace `interactions.ext.paginators.Paginator`.

**Requires OQ-2 (paginator strategy) answered first.**

### Files changed

| File | Change |
|---|---|
| `peanuts_bot/extensions/help.py` | Full rewrite; discord.py tree introspection, custom paginator View |
| `peanuts_bot/__init__.py` | Add `help` to extension load list |

### Key implementation notes

**Command introspection in discord.py:**
```python
commands_list = self.bot.tree.get_commands(guild=discord.Object(CONFIG.GUILD_ID))
# Each entry is discord.app_commands.Command or discord.app_commands.Group
for cmd in commands_list:
    if isinstance(cmd, discord.app_commands.Command):
        cmd.name       # "help"
        cmd.description  # "See help information..."
        cmd.parameters   # list[discord.app_commands.Parameter]
        for param in cmd.parameters:
            param.name        # "link"
            param.description # "The link to the message to quote"
            param.required    # bool
            param.type        # discord.AppCommandOptionType
    elif isinstance(cmd, discord.app_commands.Group):
        for sub in cmd.commands:  # sub-commands
            ...
```

**`HelpPage.from_command` rewrite** — replace the ipy `SlashCommandOption` introspection with discord.py `Parameter` introspection. The `HelpCmdProto.get_help_color()` return type changes from `ipy.Color` to `discord.Color` (already done in Step 1).

**Custom paginator View:**
```python
class HelpPaginator(discord.ui.View):
    def __init__(self, pages: list[discord.Embed], *, timeout: float = 300):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current = 0
        self._update_buttons()

    def _update_buttons(self):
        self.prev_btn.disabled = self.current == 0
        self.next_btn.disabled = self.current == len(self.pages) - 1
        self.page_select.options = [
            discord.SelectOption(label=p.title or f"Page {i+1}", value=str(i), default=(i == self.current))
            for i, p in enumerate(self.pages)
        ]

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction, button):
        self.current = max(0, self.current - 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction, button):
        self.current = min(len(self.pages) - 1, self.current + 1)
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.select(placeholder="Jump to a command...")
    async def page_select(self, interaction, select):
        self.current = int(select.values[0])
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)
```

**Admin check:**
`ctx.author.has_permission(ipy.Permissions.ADMINISTRATOR)` → `interaction.user.guild_permissions.administrator`

### User stories to verify
- H-1 through H-5

### Commit message
`refactor: migrate help extension to discord.py with custom paginator`

---

## Step 9 — `stocks.py`, `minecraft.py`, `local.py`

**Goal:** Migrate the three optional extensions. Each is relatively self-contained once the core patterns are established.

### Files changed

| File | Change |
|---|---|
| `peanuts_bot/extensions/stocks.py` | `ipy.Extension` → `commands.Cog`; slash command + autocomplete migration |
| `peanuts_bot/extensions/minecraft.py` | `ipy.Extension` → `commands.Cog`; slash command group migration |
| `peanuts_bot/extensions/local.py` | `ipy.Extension` → `commands.Cog`; `/reload` command using `bot.reload_extension()` |
| `peanuts_bot/__init__.py` | Add all three to extension load list |

### Key implementation notes

**Autocomplete (stocks.py):**
```python
@stock_cmd.autocomplete("ticker")
async def ticker_autocomplete(self, interaction: discord.Interaction, current: str) -> list[discord.app_commands.Choice[str]]:
    results = await StockAPI(AlphaV).search_symbol(current)
    return [discord.app_commands.Choice(name=r.name, value=r.symbol) for r in results[:25]]
```

**`ipy.SlashCommandChoice`** → `discord.app_commands.Choice`

**`ipy.File`** → `discord.File` (same constructor: `discord.File(fp, filename=...)`)

**`ctx.send(embeds=embed, files=[file])`** → `interaction.response.send_message(embed=embed, file=file)`

**`ipy.Embed` → `discord.Embed`** — same interface (title, description, color, fields, image, footer, author)

**`embed.set_image(url=...)`** → `embed.set_image(url=...)`  (same)

**Reload command (local.py):**
`bot.reload_extension(module_path)` is async in discord.py — `await self.bot.reload_extension(path)`.

`ALL_EXTENSIONS` choices → in discord.py, use `@app_commands.choices(ext=...)` or autocomplete.

### User stories to verify
- S-1 through S-4 _(if `ALPHAV_CONNECTED` config is set)_
- M-1 through M-8 _(if `MC_CONFIG` is set)_
- L-1 through L-3 _(local/dev env only)_

### Commit message
`refactor: migrate stocks, minecraft, and local extensions to discord.py`

---

## Step 10 — Remove interactions-py

**Goal:** Delete all remaining `interactions as ipy` imports and remove the library from dependencies. Any ipy reference that survives to this step is a bug.

### Files changed

| File | Change |
|---|---|
| `pyproject.toml` | Remove `discord-py-interactions` from `[tool.poetry.dependencies]` |
| All `peanuts_bot/**/*.py` | Verify no `import interactions` or `import interactions as ipy` remains |

### Verification commands

```bash
# Must return zero results
grep -r "import interactions" peanuts_bot/
grep -r "from interactions" peanuts_bot/

poetry remove discord-py-interactions
poetry install
make run
```

### User stories to verify
Re-run a representative sample across all feature areas to confirm nothing regressed after the dependency removal. At minimum: H-1, R-1, V-1, C-1, U-1, SP-1, Q-1, TW-1, LP-1, E-1, RN-1, RL-1.

Optional but recommended: full user story suite.

### Commit message
`refactor: remove discord-py-interactions dependency`

---

## Reference — ipy → discord.py Quick Map (Supplemental)

| ipy concept | discord.py equivalent |
|---|---|
| `ipy.Extension` | `commands.Cog` |
| `bot.load_extension(path)` | `await bot.load_extension(path)` (in `setup_hook`) |
| `bot.ext.values()` | `bot.cogs.values()` |
| `@ipy.slash_command(scopes=[GUILD_ID])` | `@app_commands.command()` + guild sync in `setup_hook` |
| `@ipy.listen("on_member_update")` | `@commands.Cog.listener("on_member_update")` |
| `@ipy.component_callback("id")` | Persistent `discord.ui.View` method with `custom_id=` on `@discord.ui.button` / `@discord.ui.select` |
| `@ipy.component_callback(REGEX)` | `discord.ui.DynamicItem` with regex `template=` |
| `@ipy.modal_callback("id")` | `discord.ui.Modal` subclass with `on_submit` |
| `@ipy.message_context_menu(name=...)` | `@app_commands.context_menu(name=...)` + register on tree |
| `ipy.SlashContext` | `discord.Interaction` |
| `ipy.ComponentContext` | `discord.Interaction` |
| `ipy.ModalContext` | `discord.Interaction` (inside modal `on_submit`) |
| `ctx.send(...)` | `interaction.response.send_message(...)` |
| `ctx.defer(ephemeral=True)` | `await interaction.response.defer(ephemeral=True)` |
| `ctx.edit_origin(...)` | `await interaction.response.edit_message(...)` |
| `ctx.send_modal(modal)` | `await interaction.response.send_modal(modal)` |
| `ctx.author` | `interaction.user` |
| `ctx.guild` | `interaction.guild` |
| `ctx.channel` | `interaction.channel` |
| `ctx.bot` | `interaction.client` |
| `ipy.events.Error` | `on_app_command_error` + View `on_error` |
| `ipy.BotUsageError` | (keep as-is, framework-agnostic) |
| `ipy.Embed` | `discord.Embed` |
| `ipy.File` | `discord.File` |
| `ipy.Button` | `discord.ui.Button` |
| `ipy.StringSelectMenu` | `discord.ui.Select` |
| `ipy.ButtonStyle.PRIMARY` | `discord.ButtonStyle.primary` |
| `ipy.ButtonStyle.SUCCESS` | `discord.ButtonStyle.success` |
| `ipy.ButtonStyle.DANGER` | `discord.ButtonStyle.danger` |
| `ipy.Modal` | `discord.ui.Modal` subclass |
| `ipy.InputText` | `discord.ui.TextInput` |
| `ipy.TextStyles.SHORT` | `discord.TextStyle.short` |
| `ipy.TextStyles.PARAGRAPH` | `discord.TextStyle.paragraph` |
| `ipy.StringSelectOption` | `discord.SelectOption` |
| `ipy.events.MemberUpdate` | `on_member_update(before, after)` — args are Members, not event wrapper |
| `ipy.events.MessageCreate` | `on_message(message)` |
| `ipy.events.VoiceUserJoin/Leave/StateUpdate` | `on_voice_state_update(member, before, after)` — single event |
| `ipy.events.Startup` | `on_ready` |
| `ipy.errors.HTTPException` | `discord.HTTPException` |
| `msg.mention_roles` (async iter) | `message.role_mentions` (sync list) |
| `msg.suppress_embeds()` | `await msg.edit(suppress=True)` |
| `msg.get_referenced_message()` | `message.reference.resolved` |
| `ctx.guild.fetch_role(id)` | `guild.get_role(int(id))` |
| `member.has_role(role)` | `role in member.roles` |
| `member.add_role(role, reason)` | `await member.add_roles(role, reason=reason)` |
| `member.remove_role(role, reason)` | `await member.remove_roles(role, reason=reason)` |
| `member.edit_nickname(nick, reason)` | `await member.edit(nick=nick, reason=reason)` |
| `ipy.Permissions.NONE` | `discord.Permissions.none()` |
| `ipy.Permissions.ADMINISTRATOR` | `discord.Permissions.administrator` |
| `member.has_permission(ipy.Permissions.ADMINISTRATOR)` | `interaction.user.guild_permissions.administrator` |
| `bot.app.description` | `(await bot.application_info()).description` or `get_bot_description()` |
| `bot.connect_to_vc(guild_id, ch_id, muted, deafened)` | `await channel.connect(self_deaf=True)` |
| `bot.get_bot_voice_state(guild_id)` | `guild.voice_client` |
| `bot_vstate.play(AudioVolume(file))` | `voice_client.play(FFmpegPCMAudio(file), after=cb)` + `asyncio.Event` |
| `channel.disconnect()` | `await guild.voice_client.disconnect()` |
| `EMBED_MAX_DESC_LENGTH` | `4096` (Discord's embed description limit) |
