# Claude Context TODO

Tracks codebase sections still to be done. Check items off as they are completed.

---

## Code Quality

### [ ] Move inline asserts in `itertools_ext.py` to tests
`libraries/itertools_ext.py` has `assert` statements below the function definitions (lines 36–54) that serve as tests. Move them to a proper test file under `tests/`.
