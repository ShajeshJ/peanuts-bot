# peanuts-bot — Claude Context

## Project Overview
Python Discord bot for a private server. Uses `discord.py` library. Deployed as a **systemd service on a Raspberry Pi** via Tailscale SSH.

## Key Commands
```bash
make init           # Set up venv and install deps
make run            # Run the bot locally
make remote_deploy  # Deploy to Pi from origin/main
```

## Startup Flow
```
app.py main()
├── load_env()              → loads .env, returns ENV value
├── configure_logging()     → colored console logging
├── import peanuts_bot      → deferred deliberately so logging is ready first
│   │                         triggers peanuts_bot/__init__.py:
│   ├── PeanutsBot (commands.Bot subclass) created (all intents, _PeanutsTree)
│   ├── setup_hook(): BotVoice.init(), load_extension() for each ALL_EXTENSIONS
│   │   entry, validate Cog protocols, sync tree to GUILD_ID
│   └── on_ready(): set "Watching /help" activity, announcer rejoin on startup
├── health_probe.start_background_server()  → if CONFIG.HEALTH_PROBE
└── bot.start()             → connect to Discord
```

**`errors.py` handler detail:**
- `_PeanutsTree.on_error` — replaces discord.py's default tree error handler (not additive)
- `BotUsageError` → sends error message to user ephemerally, silently
- Any other error → sends `SOMETHING_WRONG` to user, DMs admin the traceback, then re-raises
- View/component errors: each `View.on_error` calls `handle_interaction_error` directly

## Critical Files

| File | Purpose |
|---|---|
| `app.py` | Entrypoint; env loading, logging, bot start |
| `peanuts_bot/__init__.py` | Bot instance creation, listener registration, extension loading & runtime protocol validation |
| `peanuts_bot/config.py` | Typed singleton config via `typedenv`; global `CONFIG` instance |
| `peanuts_bot/errors.py` | Global `on_error` event listener; `BotUsageError` for user-facing errors |
| `peanuts_bot/health_probe.py` | FastAPI `/ping` on port 8000 in a daemon thread |
| `peanuts_bot/extensions/__init__.py` | `ALL_EXTENSIONS` manifest; conditionally includes stock/MC/local extensions |
| `peanuts_bot/extensions/internals/protocols.py` | `HelpCmdProto` — runtime-checked protocol enforced on all extensions at startup |

## Configuration (`peanuts_bot/config.py`)
Global singleton: `from peanuts_bot.config import CONFIG`

Key fields: `ENV`, `BOT_TOKEN`, `GUILD_ID`, `ADMIN_USER_ID`, `HEALTH_PROBE`, `LOG_LEVEL`, `LEAGUE_ROLE_ID`, `MC_SERVER_IP`, `MC_TS_HOST`, `ALPHAV_API_URL/KEY`, `MSH_API_URL/TOKEN`

Convenience properties: `CONFIG.IS_LOCAL`, `CONFIG.IS_DEBUG`

Optional config guards (raise `ValueError` if missing): `ALPHAV_CONNECTED`, `MC_CONFIG`

## Extension Pattern (discord.py)
```python
class MyExtension(commands.Cog):
    @staticmethod
    def get_help_color() -> discord.Color: ...      # Required by HelpCmdProto

    @app_commands.command()
    async def my_cmd(self, interaction: discord.Interaction): ...
```
- All extensions must implement `HelpCmdProto` (validated at startup via `bot.cogs.values()`)
- Raise `BotUsageError` for user-facing errors (caught by `_PeanutsTree.on_error`)
- Commands synced to `CONFIG.GUILD_ID` via `tree.sync(guild=...)` in `setup_hook`

## Dependency Policy

All dependencies in `pyproject.toml` must be pinned to an **exact version** (no `^`, `~`, `>=`, or other range specifiers). When adding a new dependency, pin it to the specific version resolved at install time.

## Libraries & Dependencies
- `discord.py` — Discord API library (v2.7.1, voice extras)
- `typedenv` — config loading
- `aiohttp` — async HTTP
- `async-lru` — async caching
- `fastapi` + `uvicorn` — health probe
- `matplotlib`, `mcstatus`, `gtts`, `python-dateutil` — feature libs

## Standing Session Rules

After making any code additions or changes:
1. **Update context docs** — reflect the change in whichever `.claude/` file covers the affected area (or `CLAUDE.md` itself if it's always-needed info)
2. **Check user stories** — open `.claude/user_stories.md`; update existing stories or add new ones if the change affects bot behaviour
3. **Lint & format** — run `mypy` and `ruff format` on every changed file before considering the task done

## Style Guide
See `.claude/STYLE_GUIDE.md` for full coding conventions. Key rules:
- Strong typing everywhere; use `X | Y` unions, `Annotated[T, ...]` for slash options; avoid `cast()`
- Module structure: imports → `__all__` → `logger` → constants → classes → private helpers
- All imports are absolute (`from peanuts_bot.x import y`)
- Extensions inherit `commands.Cog`, must implement `HelpCmdProto` (`get_help_color` static method)
- User-facing errors → `raise BotUsageError(...)`, system errors propagate to global handler
- Business logic without `self` belongs as private module-level functions, not class methods

## Context To-Do
See `.claude/TODO.md` for the incremental list of codebase sections not yet documented. Work through it in order when expanding context in future sessions — libraries first, then extensions, then migration tracking.

## Context File Conventions

**`CLAUDE.md` is the always-loaded hub.** Keep it scannable — summaries and pointers only. If a section would exceed ~20 lines, extract it into a dedicated file under `.claude/` and replace it with a 3–5 line summary + pointer here.

**Use a separate `.claude/` file when:**
- Content only matters for a specific kind of task (writing code → `STYLE_GUIDE.md`, planning what to document → `TODO.md`, migration work → `MIGRATION.md`)
- A topic needs more than ~20 lines to be useful
- Content will grow or be updated independently of the rest of `CLAUDE.md`

**Keep in `CLAUDE.md` when:**
- Every session is likely to need the information (overview, startup flow, config, extension pattern)
- A short summary is enough to be actionable — full detail isn't necessary to proceed

**Current `.claude/` context files:**
| File | Open when... |
|---|---|
| `.claude/STYLE_GUIDE.md` | Writing or reviewing any code |
| `.claude/TODO.md` | Deciding what context to document next |
| `.claude/libraries_discord.md` | Working with shared Discord/voice utilities (`admin`, `api`, `messaging`, `discord/voice`, `libraries/voice`) |
| `.claude/libraries_stocks_api.md` | Working with the stock data abstraction layer or Alpha Vantage provider |
| `.claude/libraries_image.md` | Working with image type detection, metadata fetching, or base64 decoding |
| `.claude/deployment.md` | Deploying the bot, managing the Pi service, or understanding CI/CD |
| `.claude/user_stories.md` | Manual validation, writing tests, or verifying feature behaviour |
| `.claude/libraries_utils.md` | Working with dice parsing, `Annotated` introspection, or iterable counting helpers |
| `.claude/extensions.md` | Working on any extension (help, roles, channels, users, messages, emojis, rng, stocks, minecraft, local) |
| `.claude/MIGRATION.md` | Archived migration log — all 11 steps complete; kept for reference |
