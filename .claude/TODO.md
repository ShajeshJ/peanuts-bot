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

### [ ] `libraries/discord/` — Shared Discord utilities
Four modules used across multiple extensions. Document what each provides and when to use it.
- `admin.py` — sending error/alert messages to admin user
- `api.py` — shared aiohttp session management (async context manager)
- `messaging.py` — helpers for fetching/sending messages, type guards, DiscordMessageLink
- `voice.py` — `BotVoice` singleton: voice channel join/leave/move logic, TTS announcement

### [ ] `libraries/voice.py` — Voice state & TTS
The non-Discord-specific voice layer: TTS audio generation, file cleanup, audio queue management. Feeds into `libraries/discord/voice.py`.

### [ ] `libraries/stocks_api/` — Stock data abstraction
Multi-provider stock API with an interface/protocol layer:
- `interface.py` — `IStockProvider`, `IDaily`, `IQuote` abstract interfaces + TypeVars
- `providers/alphav.py` — Alpha Vantage implementation
- `__init__.py` — `StockAPI` wrapper that accepts any provider
- `errors.py` — Stock-specific exceptions

### [ ] `libraries/image.py` — Image generation
Chart/graph rendering (matplotlib-based). Used by the stocks extension.

### [ ] `libraries/tabletop_roller.py` — Dice roller
Regex-based dice expression parser and roller. Used by the RNG extension.

### [ ] `libraries/types_ext.py` + `libraries/itertools_ext.py` — Pure utilities
Small typed utility functions. `types_ext` includes `get_annotated_subtype` used by `help.py` for introspecting slash command parameters.

---

## Extensions

### [ ] `extensions/help.py` — `/help` command
Paginates all registered slash commands into embeds. Reads extension colors via `HelpCmdProto`. Uses `Paginator` from interactions-py.

### [ ] `extensions/roles.py` — `/role` commands
Manages joinable mention roles: create, delete, join (dropdown), leave (dropdown). Joinable roles are identified by zero permissions + mentionable flag.

### [ ] `extensions/channels.py` — `/channel` + voice auto-management
Channel management commands + event listeners that auto-create/delete temporary voice channels.

### [ ] `extensions/users.py` — User info commands
Slash commands for looking up user info (nicknames, avatar, etc.).

### [ ] `extensions/messages.py` — Message utility commands
Right-click context menu commands and slash commands for working with messages (quoting, linking, etc.).

### [ ] `extensions/emojis.py` — Emoji management
Admin-gated emoji upload flow: user submits image → admin approves/rejects via buttons → emoji added to server.

### [ ] `extensions/rng.py` — Random & dice commands
Dice rolls, random selection, coin flip. Uses `tabletop_roller.py` for dice parsing.

### [ ] `extensions/stocks.py` — Stock lookup commands
Slash commands for querying stock quotes/charts. Uses `StockAPI` from `libraries/stocks_api/`. Only loaded when `ALPHAV_CONNECTED` config is valid.

### [ ] `extensions/minecraft.py` — Minecraft server commands
Slash commands for checking Minecraft server status, looking up player info. Only loaded when `MC_CONFIG` config is valid.

### [ ] `extensions/local.py` — Dev-only commands
Commands only available in local/dev environment (`CONFIG.IS_LOCAL`). Useful for testing bot behaviour without affecting prod.

---

## Migration Progress

### [ ] Document the discord.py migration plan
Once migration begins, track which files have been migrated vs. still using interactions-py. Add a `MIGRATION.md` or a section in `CLAUDE.md` with per-file status.

### [ ] Update CLAUDE.md extension pattern section
After the migration is complete, update the extension pattern examples in `CLAUDE.md` from `ipy.Extension` to `commands.Cog`.
