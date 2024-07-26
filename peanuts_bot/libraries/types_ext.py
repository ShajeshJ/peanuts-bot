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


##############################
# get_annotated_subtype tests
##############################

assert get_annotated_subtype(t.Annotated[str, "metadata"]) == (str, ["metadata"])
assert get_annotated_subtype(t.Annotated[object, str, "world"]) == (
    object,
    [str, "world"],
)
assert get_annotated_subtype(t.Annotated[str, None]) == (str, [None])
assert get_annotated_subtype(t.Annotated[None, str]) == (type(None), [str])

fail_cases = [
    str,
    object,
    None,
    str | bool,
    t.Union[str, int],
    t.Optional[str],
    list[str],
    dict[str, None],
]

for case in fail_cases:
    try:
        val = get_annotated_subtype(case)
        assert False, f"{case} returned {val} for annotated subtype"
    except TypeError:
        pass
