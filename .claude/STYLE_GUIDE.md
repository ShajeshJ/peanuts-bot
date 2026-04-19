# peanuts-bot Code Style Guide

## Type Hints

**Strongly typed throughout.** Every function signature, class attribute, and variable with a non-obvious type must be annotated.

- Use `X | Y` union syntax (PEP 604) — never `Union[X, Y]`
- Use `X | None` — never `Optional[X]`
- Use `Annotated[T, ...]` for slash command parameters (see [Discord Commands](#discord-commands))
- Avoid `typing.cast` — if a cast is needed, first consider whether a type guard (`isinstance` check) or a better-typed interface would eliminate it
- Untyped code is acceptable only when enforcing types would significantly increase complexity; this should be rare and deliberate

**Protocols:**
- Use `@runtime_checkable` Protocol classes for structural contracts enforced at runtime
- See `peanuts_bot/extensions/internals/protocols.py`

**Generics:**
- Use `TypeVar` with `bound=` to constrain inheritance hierarchies
- Use `Generic[T]` when a class must be typed for multiple concrete implementations

---

## Module Structure

Every module follows this top-to-bottom order:

```python
# 1. Standard library imports
# 2. Third-party imports
# 3. Local imports (peanuts_bot.*)

__all__ = ["PublicClass"]           # Always present; lists public API

logger = logging.getLogger(__name__)  # Always present in every module

CONSTANT = ...                       # Module-level constants (UPPER_SNAKE_CASE)
_PRIVATE_CONSTANT = ...              # Private constants (leading underscore)

class PublicClass: ...               # Class definitions

def _private_helper(): ...           # Private module-level helpers at the bottom
def public_helper(): ...
```

Rules:
- All imports are **absolute** (`from peanuts_bot.x import y`) — no relative imports
- `__all__` must be declared in every module; list only publicly intended exports
- `logger = logging.getLogger(__name__)` is declared at module level in every file

---

## Naming Conventions

| Thing | Convention | Example |
|---|---|---|
| Classes | PascalCase | `RoleExtension`, `HelpPage` |
| Functions / methods | snake_case | `get_help_color`, `split_role_option_value` |
| Constants | UPPER_SNAKE_CASE | `ROLE_JOIN_ID`, `MAX_EMOJI_FILE_SIZE` |
| Private / internal | leading `_` | `_JOINABLE_PERMISSION_SET`, `_get_slash_cmd_desc` |
| Module logger | always `logger` | `logger = logging.getLogger(__name__)` |
| Loop variables | descriptive unless single-use | `role`, `member`; `r` only for very short lambdas |

---

## Extension Structure

All extensions live in `peanuts_bot/extensions/` and inherit from `commands.Cog`.

**Required contract:** Every extension must implement `HelpCmdProto` — a static `get_help_color() -> discord.Color` method. This is validated at bot startup.

**Method ordering inside a Cog class:**

1. `get_help_color()` static method (always first)
2. Top-level app commands (`@app_commands.command()`)
3. Group subcommands (`@_group.command()`) — group defined as class variable
4. Autocomplete handlers (`@cmd.autocomplete("param")`)
5. Event listeners (`@commands.Cog.listener(...)`)

**Business logic** that doesn't need `self` belongs as private module-level functions, not as methods on the class.

```python
class MyExtension(commands.Cog):
    _group = app_commands.Group(name="group", description="Group of commands")

    @staticmethod
    def get_help_color() -> discord.Color:
        return discord.Color.red()

    @app_commands.command(name="cmd")
    async def cmd(self, interaction: discord.Interaction):
        """Docstring is the help text shown in Discord"""
        ...

    @_group.command(name="subcommand")
    @app_commands.describe(param="description")
    async def group_subcommand(self, interaction: discord.Interaction, param: str):
        """Docstring is the help text shown in Discord"""
        ...
```

---

## Discord Commands

**Slash command parameters** use `@app_commands.describe` for descriptions; types are native Python types:

```python
@app_commands.describe(name="The name", role="The role to assign")
async def cmd(
    self,
    interaction: discord.Interaction,
    name: str,
    role: discord.Role,
):
```

**Group commands** use a class-variable `app_commands.Group`; no empty parent pass-through needed:

```python
class MyExtension(commands.Cog):
    _group = app_commands.Group(name="group", description="...")

    @_group.command(name="sub")
    async def sub(self, interaction: discord.Interaction):
        ...
```

**Guild scope** is handled by `tree.sync(guild=discord.Object(id=CONFIG.GUILD_ID))` in `setup_hook` — commands are registered globally then copied to the guild.

**Admin-only commands** use `@app_commands.default_permissions(administrator=True)` on commands, or `default_permissions=discord.Permissions(administrator=True)` on `app_commands.Group`.

**Component custom IDs** are module-level constants:

```python
ROLE_JOIN_ID = "role_join"
```

---

## Error Handling

**User-facing errors** → raise `BotUsageError` from `peanuts_bot.errors`:

```python
raise BotUsageError("This command can only be used in a server")
```

These are caught by `_PeanutsTree.on_error` (for slash commands) or `View.on_error` (for components) and sent back to the user as a message.

**System errors** (unexpected failures) → let them propagate or log and re-raise. The global handler will notify the admin and log the traceback.

**HTTP errors** → catch specific status codes to handle expected API failures gracefully; don't swallow unexpected codes.

**Guild guard pattern** (required at the top of most command handlers):

```python
if not interaction.guild:
    raise BotUsageError("This command can only be used in a server")
```

---

## Logging

Use the module-level `logger` instance. Follow these level conventions:

| Level | When to use |
|---|---|
| `logger.debug(...)` | Detailed internal state, loop iterations, skip reasons |
| `logger.info(...)` | Important state transitions (bot joining a channel, etc.) |
| `logger.warning(...)` | Recoverable unexpected situations |
| `logger.exception(...)` / `exc_info=True` | Caught exceptions where traceback is needed |

---

## Data Structures

**`@dataclass`** for structured data containers with multiple fields:
- Use `frozen=True` for immutable data
- Use `field(default_factory=...)` for mutable defaults

**`NamedTuple`** for lightweight value types that behave like tuples:
- Can include methods
- Preferred over plain tuples when field names add clarity

**`(str, Enum)` / `(int, Enum)`** for enumerations that need a concrete base type for serialization or comparison.

---

## Async Patterns

- All Discord command handlers and event listeners are `async`
- Use `asyncio.gather(*tasks, return_exceptions=True)` for concurrent operations where failures should be collected rather than raised immediately
- Use `@asynccontextmanager` for async resource management
- Use `async for` with async generators for streaming results (see `get_valid_roles` in `roles.py`)
- Use `asyncio.create_task()` for fire-and-forget background work; attach a done callback to handle errors

---

## Libraries (`peanuts_bot/libraries/`)

Libraries are **pure utilities** — no Discord-specific dependencies unless placed in `libraries/discord/`.

- Full type coverage, including generics where appropriate
- Public APIs have docstrings with parameter descriptions (`:param name: description`)
- Module-level assertions at the bottom of utility modules serve as lightweight inline tests

---

## Configuration

Always import the global singleton:

```python
from peanuts_bot.config import CONFIG
```

- Use `CONFIG.IS_LOCAL` / `CONFIG.IS_DEBUG` for environment checks
- Optional feature configs (`ALPHAV_CONNECTED`, `MC_CONFIG`) are validated at extension load time — extensions that depend on them are only loaded when config is valid
- Never hardcode guild IDs, channel IDs, or role IDs — they belong in `config.py`
