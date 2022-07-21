from collections.abc import Iterable


def at_least_n(__iterable: Iterable, /, n: int=1) -> bool:
    """Return True if bool(x) is True for at least n items"""

    if n < 1:
        raise ValueError(f"n must be >= 1")

    iterator = iter(__iterable)

    # `any` will consume the iterator up to the first truthy item and pauses.
    # So calling `any` n times will consume up to the first n truthy items.
    for _ in range(n):
        if not any(iterator):
            return False

    return True


def exactly_n(__iterable: Iterable, /, n: int=1) -> bool:
    """Return True if bool(x) is True for exactly n items"""

    if n < 1:
        raise ValueError(f"n must be >= 1")

    iterator = iter(__iterable)

    # `at_least_n` consumes the iterator up to the first n truthy items.
    # So for exact, we make sure the leftovers have no more truthy items.
    return at_least_n(iterator, n=n) and not any(iterator)

# TODO: Move below to tests/

assert at_least_n([]) is False
assert at_least_n([True, False, False]) is True
assert at_least_n([False, True, False]) is True
assert at_least_n([False, False, True]) is True
assert at_least_n([True, True, False]) is True
assert at_least_n([True, True, True]) is True
assert at_least_n([False, True, True], n=2) is True
assert at_least_n([True, True, True], n=2) is True
assert at_least_n([False, False, True], n=2) is False

assert exactly_n([]) is False
assert exactly_n([True, False, False]) is True
assert exactly_n([False, True, False]) is True
assert exactly_n([False, False, True]) is True
assert exactly_n([True, True, False]) is False
assert exactly_n([True, True, True]) is False
assert exactly_n([False, True, True], n=2) is True
assert exactly_n([True, True, True], n=2) is False
assert exactly_n([False, False, True], n=2) is False
