## Build docker image for pysen-test

```bash
$ docker build -t quay.io/pysen/pysen-test .
$ docker push quay.io/pysen/pysen-test
```

## Directories

- `post_310` / `post_313`: smoke-test projects exercised by the corresponding
  `tox` environments for newer Python interpreters.
- `post_mypy2`: smoke-test project for `mypy >=2` (`py{313,314}-mypy2` tox env).

### Note on mypy >=2 and `py_version`

mypy `>=2` only supports type-checking against `python_version >= 3.10`. When a
pysen config sets an older `py_version` (e.g. `py27`, `py38`, `py39`), pysen
still emits `python_version = 3.x` into the mypy config. mypy `>=2` prints a
warning (`python_version: Python 3.8 is not supported (must be 3.10 or higher)`)
and silently falls back to its minimum supported version, so the effective
type-checking semantics differ from what the user requested. The `post_mypy2`
example therefore uses `py_version = "py313"`.
