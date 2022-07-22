import types
import typing as t


def get_optional_subtype(t_annotation):
    """
    Given an optional type annotation, will return the subtype.

    Optional type annotations include "Optional[x]", "Union[x, None]" and "x | None"
    """

    if not hasattr(t_annotation, "__args__") or not isinstance(
        t_annotation.__args__, tuple
    ):
        raise ValueError(f"<{t_annotation}> is not an optional type")

    try:
        a1, a2 = t_annotation.__args__
        sub_type = next(a for a in (a1, a2) if a is not types.NoneType)

        # Implicitly checks for at least 1 NoneType
        next(a for a in (a1, a2) if a is types.NoneType)
    except (ValueError, StopIteration):
        raise ValueError(f"<{t_annotation}> is not an optional type")

    if t.Optional[sub_type] != t_annotation:
        raise ValueError(f"<{t_annotation}> is not an optional type")

    return sub_type
