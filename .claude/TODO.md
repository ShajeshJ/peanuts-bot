# Claude Context TODO

Tracks incremental sections of the codebase still to be understood and documented into context files. Work through these in order — each builds on the previous.

Check items off as context is added to `CLAUDE.md` or dedicated context files.

### When to split a TODO into smaller parts

Break a TODO into sub-items before starting it if **any** of the following apply:
- It requires reading **3+ files** to document fully — each file is likely its own sub-item
- The module covers **2+ distinct concerns** (e.g., voice state management AND TTS AND audio queue) — each concern warrants its own sub-item
- Documenting it would push a context file **past the ~20-line threshold** on its own — split the documentation target first, then document each piece separately
- It touches **shared state or cross-cutting logic** that needs to be understood before dependent TODOs can be tackled accurately (document that piece first as its own sub-item)

When splitting: replace the single checkbox with numbered sub-items inline, each with its own `[ ]`. Don't create a new top-level section — keep the sub-items nested under the original heading.

---

## Libraries

### [x] `libraries/discord/` — Shared Discord utilities
Four modules used across multiple extensions. Document what each provides and when to use it.
- `admin.py` — sending error/alert messages to admin user
- `api.py` — shared aiohttp session management (async context manager)
- `messaging.py` — helpers for fetching/sending messages, type guards, DiscordMessageLink
- `voice.py` — `BotVoice` singleton: voice channel join/leave/move logic, TTS announcement

### [x] `libraries/voice.py` — Voice state & TTS
The non-Discord-specific voice layer: TTS audio generation, file cleanup, audio queue management. Feeds into `libraries/discord/voice.py`.

### [x] `libraries/stocks_api/` — Stock data abstraction
Multi-provider stock API with an interface/protocol layer:
- `interface.py` — `IStockProvider`, `IDaily`, `IQuote` abstract interfaces + TypeVars
- `providers/alphav.py` — Alpha Vantage implementation
- `__init__.py` — `StockAPI` wrapper that accepts any provider
- `errors.py` — Stock-specific exceptions

### [x] `libraries/image.py` — Image generation
Chart/graph rendering (matplotlib-based). Used by the stocks extension.

### [x] `libraries/tabletop_roller.py` — Dice roller
Regex-based dice expression parser and roller. Used by the RNG extension.

### [x] `libraries/types_ext.py` + `libraries/itertools_ext.py` — Pure utilities
Small typed utility functions. `types_ext` includes `get_annotated_subtype` used by `help.py` for introspecting slash command parameters.

---

## Extensions

### [x] `extensions/help.py` — `/help` command
Paginates all registered app tree commands into embeds. Reads extension colors via `HelpCmdProto`. Uses a custom `HelpPaginator(discord.ui.View)`.

### [x] `extensions/roles.py` — `/role` commands
Manages joinable mention roles: create, delete, join (dropdown), leave (dropdown). Joinable roles are identified by zero permissions + mentionable flag.

### [x] `extensions/channels.py` — `/channel` + voice auto-management
Channel management commands + event listeners that auto-create/delete temporary voice channels.

### [x] `extensions/users.py` — User info commands
Slash commands for looking up user info (nicknames, avatar, etc.).

### [x] `extensions/messages.py` — Message utility commands
Right-click context menu commands and slash commands for working with messages (quoting, linking, etc.).

### [x] `extensions/emojis.py` — Emoji management
Admin-gated emoji upload flow: user submits image → admin approves/rejects via buttons → emoji added to server.

### [x] `extensions/rng.py` — Random & dice commands
Dice rolls, random selection, coin flip. Uses `tabletop_roller.py` for dice parsing.

### [x] `extensions/stocks.py` — Stock lookup commands
Slash commands for querying stock quotes/charts. Uses `StockAPI` from `libraries/stocks_api/`. Only loaded when `ALPHAV_CONNECTED` config is valid.

### [x] `extensions/minecraft.py` — Minecraft server commands
Slash commands for checking Minecraft server status, looking up player info. Only loaded when `MC_CONFIG` config is valid.

### [x] `extensions/local.py` — Dev-only commands
Commands only available in local/dev environment (`CONFIG.IS_LOCAL`). Useful for testing bot behaviour without affecting prod.

---

## Infrastructure & Core Detail

### [x] Deployment infrastructure — `pi_bootstrap/` + Makefile
The Pi deployment flow is undocumented. Document:
- `make remote_deploy` flow (SSH_HOST + START_DIR env vars, remote-deploy.sh steps)
- `make pi_install` (systemd install), `pi_status`, `pi_logs` targets
- systemd service behaviour (auto-restart, 120s delay, `pi` user, network-online dependency)
- `.legacy_render_bootstrap/` — note it's a dead legacy Render deployment, no longer active

### [x] `peanuts_bot/__init__.py` + `app.py` — Bot init detail
Key bot options:
- `PeanutsBot(commands.Bot)` subclass with `_PeanutsTree` as `tree_cls`
- `setup_hook()` — async setup: BotVoice.init, extension loading, Cog protocol validation, tree sync to GUILD_ID
- `on_ready()` — sets "Watching /help" activity, calls `announcer_rejoin_on_startup`
- `app.py` defers `import peanuts_bot` into `main()` deliberately so logging is configured first

### [x] `peanuts_bot/errors.py` — Error handler detail
Key details:
- `_PeanutsTree.on_error` — replaces discord.py's default tree error handler (not additive)
- `handle_interaction_error(interaction, error)` — shared handler called by tree and Views
- Non-`BotUsageError` errors DM the admin and re-raise (process continues)
- `SOMETHING_WRONG` constant — importable generic message used by extensions (e.g. `emojis.py`)

---

## Migration Progress

### [x] Document the discord.py migration plan
Migration plan written to `.claude/MIGRATION.md`. Includes 10 ordered steps, open questions (OQ-1 through OQ-5), per-step file lists, implementation notes, user stories to verify, and a full ipy→discord.py API quick-reference table.

### [x] Update CLAUDE.md extension pattern section
Updated all ipy/interactions-py references across CLAUDE.md, STYLE_GUIDE.md, extensions.md, libraries_discord.md, libraries_image.md, TODO.md, and README.md.
