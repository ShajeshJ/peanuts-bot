import types
import typing as t


def get_annotated_subtype(t_annotation) -> tuple[type, list[t.Any]]:
    """
    Given an `Annotated` type, will return its underlying type, and additional metadata.

    Raises `TypeError` if not given an `Annotated` type.
    """
    if t.get_origin(t_annotation) is not t.Annotated:
        raise TypeError(f"<{t_annotation}> is not an `Annotated` type")

    main_type, *metadata = t.get_args(t_annotation)
    return main_type, metadata


def get_optional_subtype(t_annotation):
    """
    Given an optional type annotation, will return the subtype. Otherwise raises `ValueError`.

    Optional type annotations include `Optional[x]`, `Union[x, None]` and `x | None`
    """
    t_args = t.get_args(t_annotation)

    if not t_args:
        raise ValueError(f"<{t_annotation}> is not an optional type")

    match t_args:
        case (subtype, types.NoneType) | (types.NoneType, subtype):
            pass
        case _:
            raise ValueError(f"<{t_annotation}> is not an optional type")

    if t.Optional[subtype] != t_annotation:
        raise ValueError(f"<{t_annotation}> is not an optional type")

    return subtype


assert get_optional_subtype(str | None) == str
assert get_optional_subtype(None | str) == str
assert get_optional_subtype(t.Union[None, str]) == str
assert get_optional_subtype(t.Union[str, None]) == str
assert get_optional_subtype(t.Optional[str]) == str

fail_cases = [
    str,
    None,
    str | bool,
    t.Union[bool, str],
    t.Union[None, None],
    t.Union[str, bool, None],
    t.Optional[None],
    list[None],
    list[str],
    dict[str, None],
    dict[None, str],
    t.Annotated[str, None],
    t.Annotated[None, str],
]

for case in fail_cases:
    try:
        val = get_optional_subtype(case)
        assert False, f"{case} returned {val} for optional subtype"
    except ValueError:
        pass
