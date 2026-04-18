# Small Utility Libraries

Three small, self-contained modules with no dependencies on other `peanuts_bot` code.

---

## `libraries/tabletop_roller.py` — Dice expression parser

**`DICE_REGEX`** — matches expressions like `2d6`, `d20`, `3d8+2`, `-1d4-1`.

**`DiceRoll(frozen dataclass)`** — `count: int`, `sides: int`, `modifier: int`. `__str__` renders back to dice notation (e.g. `"2d6+3"`).

**`parse_dice_roll(roll: str) -> DiceRoll`**
Strips spaces, applies `DICE_REGEX`. Raises `ValueError` on invalid input. Defaults: `count=1`, `modifier=0`.

---

## `libraries/types_ext.py` — Annotated type introspection

**`get_annotated_subtype(t_annotation) -> tuple[type, list[Any]]`**
Unpacks an `Annotated[T, ...]` type into `(T, [metadata...])`. Raises `TypeError` if not given an `Annotated` type. Used by `extensions/help.py` to introspect slash command parameter metadata at runtime.

Note: file includes inline assertion tests (no separate test file yet — TODO comment to move them).

---

## `libraries/itertools_ext.py` — Iterable counting helpers

**`at_least_n(iterable, /, n=1) -> bool`**
Returns True if at least `n` truthy items exist. Uses lazy `any()` chaining — does not consume the whole iterable.

**`exactly_n(iterable, /, n=1) -> bool`**
Returns True if exactly `n` truthy items exist.

Note: file includes inline assertion tests (TODO comment to move them to `tests/`).
