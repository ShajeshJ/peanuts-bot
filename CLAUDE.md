# peanuts-bot — Claude Context

## Project Overview
Python Discord bot for a private server. Uses `interactions-py` (`discord-py-interactions`) library. Deployed as a **systemd service on a Raspberry Pi** via Tailscale SSH.

**Active goal:** Migrate from `interactions-py` to `discord.py`.

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
│   ├── ipy.Client created (token, ALL intents, debug_scope=GUILD_ID,
│   │   delete_unused_application_cmds=True, send_command_tracebacks=False,
│   │   activity=Watching "/help")
│   ├── on_error listener registered (disable_default_listeners=True)
│   ├── voice listener + BotVoice.init(bot) registered
│   ├── bot.load_extension() called for each entry in ALL_EXTENSIONS
│   └── protocol validation: all loaded extensions must implement HelpCmdProto
├── health_probe.start_background_server()  → if CONFIG.HEALTH_PROBE
└── bot.start()             → connect to Discord
```

**`errors.py` handler detail:**
- `disable_default_listeners=True` — fully replaces ipy's built-in error handler (not additive)
- `BotUsageError` → sends error message to user ephemerally, silently
- Any other error → sends `SOMETHING_WRONG` to user, DMs admin the traceback, then re-raises
- Non-`InteractionContext` source → re-raises as wrapped exception (crashes the process)

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

## Extension Pattern (interactions-py)
```python
class MyExtension(ipy.Extension):
    @staticmethod
    def get_help_color() -> ipy.Color: ...          # Required by HelpCmdProto

    @ipy.slash_command(scopes=[CONFIG.GUILD_ID])
    async def my_cmd(self, ctx: ipy.SlashContext): ...
```
- All extensions must implement `HelpCmdProto` (validated at startup via `bot.ext.values()`)
- Raise `BotUsageError` for user-facing errors (caught by global error handler)
- Slash commands scoped to `CONFIG.GUILD_ID` (dev: same guild as prod for this bot)

## interactions-py → discord.py Migration Map

| interactions-py | discord.py |
|---|---|
| `ipy.Client(token=..., intents=ipy.Intents.ALL, debug_scope=GUILD_ID)` | `commands.Bot(intents=discord.Intents.all())` |
| `ipy.Extension` | `commands.Cog` |
| `@ipy.slash_command(scopes=[GUILD_ID])` | `@app_commands.command()` + guild sync |
| `ipy.SlashContext` | `discord.Interaction` |
| `@ipy.listen()` | `@bot.event` |
| `ipy.events.Error` | `on_command_error` event |
| `bot.load_extension(path)` | `await bot.load_extension(path)` (must be async, in `setup_hook`) |
| `bot.ext.values()` | `bot.cogs.values()` |
| `ipy.Intents.ALL` | `discord.Intents.all()` |

### Migration Notes
- `config.py`, `health_probe.py`, the protocol pattern, and `errors.py` logic are library-agnostic — reuse as-is
- discord.py extension loading is **async** — use `async def setup_hook(self)` on the Bot subclass
- No built-in `debug_scope`; use `bot.tree.sync(guild=discord.Object(id=GUILD_ID))` in `setup_hook` for guild-scoped slash commands
- discord.py slash commands live in `app_commands.CommandTree` (`bot.tree`); must call `tree.sync()` to register

## Dependency Policy

All dependencies in `pyproject.toml` must be pinned to an **exact version** (no `^`, `~`, `>=`, or other range specifiers). When adding a new dependency, pin it to the specific version resolved at install time.

## Libraries & Dependencies (relevant to migration)
- `typedenv` — config loading (keep)
- `aiohttp` — async HTTP (keep)
- `async-lru` — async caching (keep)
- `fastapi` + `uvicorn` — health probe (keep)
- `matplotlib`, `mcstatus`, `gtts`, `python-dateutil` — feature libs (keep)
- `discord-py-interactions` v5.16.0rc3 — **replace with `discord.py`**

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
- Extensions inherit `ipy.Extension`, must implement `HelpCmdProto` (`get_help_color` static method)
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
| `.claude/MIGRATION.md` | Executing or tracking the interactions-py → discord.py migration (step status, open questions, ipy→dpy API map) |
