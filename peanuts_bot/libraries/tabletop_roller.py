from dataclasses import dataclass
import re

DICE_REGEX = re.compile(r"^(?P<count>[+-]?\d+)?d(?P<sides>\d+)(?P<modifier>[+-]\d+)?$")


@dataclass(frozen=True)
class DiceRoll:
    count: int
    sides: int
    modifier: int

    def __str__(self):
        count_str = f"{self.count}" if self.count != 1 else ""
        modifier_str = f"{self.modifier:+}" if self.modifier != 0 else ""
        return f"{count_str}d{self.sides}{modifier_str}"


def parse_dice_roll(roll: str) -> DiceRoll:
    match = DICE_REGEX.match(roll.replace(" ", ""))
    if not match:
        raise ValueError(f"Invalid dice roll: {roll}")

    count = int(match.group("count") or 1)
    sides = int(match.group("sides"))
    modifier = int(match.group("modifier") or 0)

    return DiceRoll(count=count, sides=sides, modifier=modifier)
