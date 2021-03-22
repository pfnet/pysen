## Description

This is an advanced example to know our plugin system.

The overview of our plugin system:
```
+-----------+ 1.  n. +-----------+ n.   1. +----------+
| pyproject | -----> | component | ------> | manifest |
+-----------+ plugin +-----------+ builder +----------+
```

This example shows

- How to implement a custom plugin and use it from pyproject.toml
- How to implement a custom builder and use it from pyproject.toml

In this example, we implemented `ShellPlugin` that executes a given command when a given target.
We register the plugin to pysen in `tool.pysen.plugin` section of `pyproject.toml`,
then define configurations for the plugin in `tool.pysen.plugin.shell` and `tool.pysen.plugin.pwd`.

Please see `pyproject.toml`, `plugin.py`, and `builder.py` to know how to use a custom builder.

```sh
$ pysen list
available targets:
 * lint
   - flake8
   - check ls
 * hook
   - check ls
   - check pwd

$ pysen --ignore-lint list
available targets:
 * lint
   - check ls
 * hook
   - check ls
   - check pwd

$ pysen run lint
...
$ pysen run hook
...
```
