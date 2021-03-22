## Description

This is an advanced example to know the custom builder of `pysen`.
This example configures linter settings for pysen without using `tool.pysen.lint` of `pyproject.toml`.
Please see `pyproject.toml` and `lint.py` to know how to define and use a custom builder.

```sh
$ pysen list
available targets:
 * lint
   - mypy
   - flake8

$ pysen run lint
...
```
