# pysen

![](https://github.com/pfnet/pysen/blob/main/assets/imgs/pysen.gif?raw=true)

## What is pysen?

pysen aims to provide a unified platform to configure and run day-to-day development tools.
We envision the following scenarios in the future:

- You open any project and `pysen run lint`, `pysen run format` will check and format the entire codebase
- Standardized coding styles are setup with a few lines in a single `pyproject.toml` file

pysen centralizes the code and knowledge related to development tools that teams have accumulated, most notably for python linters.
You can make tasks that can be executed from both `setup.py` and our command-line tool.
We currently provide tasks that manage setting files for the following tools:

- linters
  - flake8
  - isort
  - mypy
  - black
- utilities
  - (planned) protoc

## What isn't pysen?

* pysen is not a linting tool per se. Rather, `pysen run lint` orchestrates multiple python linting tools by automatically setting up their configurations from a more abstract setting for pysen.
* pysen does not manage your depedencies and packages. We recommend using package managers such as [pipenv](https://github.com/pypa/pipenv) or [poetry](https://python-poetry.org/) to lock your dependecy versions, **including the versions for the linting tools that pysen coordinates** (i.e., isort, mypy, flake8, black). The supported versions for these tools can be found in the `extra_requires/lint` section in pysen's [setup.py](https://github.com/pfnet/pysen/blob/main/setup.py). You should **not** rely on `pip install pysen[lint]` to control the versions of your linting tools.
* pysen is not limited to linting purposes or python. See the [plugin section](README.md#create-a-plugin-to-customize-pysen) for details.

## Install

### PyPI

```sh
pip install "pysen[lint]"
```


### Other installation examples

```sh
# pipenv
pipenv install --dev "pysen[lint]==0.9.0"
# poetry
poetry add -D pysen==0.9.0 -E lint
```


## Quickstart: Set up linters using pysen

Put the following pysen configuration to `pyproject.toml` of your python package:
```toml
[tool.pysen]
version = "0.9"

[tool.pysen.lint]
enable_black = true
enable_flake8 = true
enable_isort = true
enable_mypy = true
mypy_preset = "strict"
line_length = 88
py_version = "py37"
[[tool.pysen.lint.mypy_targets]]
  paths = ["."]
```

then, execute the following command:
```sh
$ pysen run lint
$ pysen run format  # corrects errors with compatible commands (black, isort)
```

That's it!
pysen, or more accurately pysen tasks that support the specified linters, generate setting files for black, isort, mypy, and flake8
and run them with the appropriate configuration.
For more details about the configuration items that you can write in `pyproject.toml`, please refer to `pysen/pyproject_model.py`.

You can also add custom setup commands to your Python package by adding the following lines to its `setup.py`:
```py
import pysen
setup = pysen.setup_from_pyproject(__file__)
```

```sh
$ python setup.py lint
```

We also provide a Python interface for customizing our configuration and extending pysen.
For more details, please refer to the following two examples:
- Example configuration from Python: `examples/advanced_example/config.py`
- Example plugin for pysen: `examples/plugin_example/plugin.py`

## How it works: Settings file directory

Under the hood, whenever you run pysen, it generates the setting files as ephemeral temporary files to be used by linters.
You may want to keep those setting files on your disk, e.g. when you want to use them for your editor.
If that is the case, run the following command to generate the setting files to your directory of choice:

```sh
$ pysen generate [out_dir]
```

You can specify the settings directory that pysen uses when you `pysen run`.
To do so add the following section to your `pyproject.toml`:

```toml
[tool.pysen-cli]
settings_dir = "path/to/generate/settings"
```

When you specify a directory that already contains some configurations, pysen merges the contents. The resulting behavior may differ from when you don't specify `settings_dir`.

Also keep in mind that this option is honored only when you use pysen through its CLI. When using pre-commit or setuptools you need to specify `settings_dir` as arguments.

## Tips: IDE / Text editor integration

### vim

You can add errors that pysen reports to your quickfix window by:

```
:cex system("pysen run_files lint --error-format gnu ".expand('%:p'))
```

Another way is to set pysen to `makeprg`:

```
set makeprg=pysen\ run_files\ --error-format\ gnu\ lint\ %
```

Then running `:make` will populate your quickfix window with errors.
This also works with [`vim-dispatch`](https://github.com/tpope/vim-dispatch) as long as you invoke `:Make` instead of `:Dispatch` (for [this reason](https://github.com/tpope/vim-dispatch/issues/41#issuecomment-20555488))

The result will look like the following:

![pysen-vim](https://github.com/pfnet/pysen/blob/main/assets/imgs/pysen_vim.gif?raw=true)

### VSCode

Refer to the [example task setting](/assets/vscode/tasks.json).
Running the task will populate your "PROBLEMS" window like so:

![pysen-vscode](https://github.com/pfnet/pysen/blob/main/assets/imgs/pysen_vscode.jpg?raw=true)

Note that this may report duplicate errors if you have configured linters like `flake8` directly through your VSCode python extension.
We do not currently recommend watching for file changes to trigger the task in large projects since `pysen` will check for all files and may consume a considerable amount of time.

## Configure pysen

We provide two methods to write configuration for pysen.

One is the `[tool.pysen.lint]` section in `pyproject.toml`.
It is the most simple way to configure pysen, but the settings we provide are limited.

The other method is to write a python script that configures pysen directly.
If you want to customize configuration files that pysen generates, command-line arguments that pysen takes, or whatever actions pysen performs, we recommend you use this method.
For more examples, please refer to `pysen/examples`.

### pyproject.toml configuration model

Please refer to `pysen/pyproject_model.py` for the latest model.

Here is an example of a basic configuration:
```toml
[tool.pysen]
version = "0.9"

[tool.pysen.lint]
enable_black = true
enable_flake8 = true
enable_isort = true
enable_mypy = true
mypy_preset = "strict"
line_length = 88
py_version = "py37"
isort_known_third_party = ["numpy"]
isort_known_first_party = ["pysen"]
mypy_ignore_packages = ["pysen.generated.*"]
mypy_path = ["stubs"]
[[tool.pysen.lint.mypy_targets]]
  paths = [".", "tests/"]

[tool.pysen.lint.source]
  includes = ["."]
  include_globs = ["**/*.template"]
  excludes = ["third_party/"]
  exclude_globs = ["**/*_grpc.py"]

[tool.pysen.lint.mypy_modules."pysen.scripts"]
  preset = "entry"

[tool.pysen.lint.mypy_modules."numpy"]
  ignore_errors = true
```

### Create a plugin to customize pysen

We provide a plugin interface for customizing our tool support, setting files management, setup commands and so on.
For more details, please refer to `pysen/examples/plugin_example`.

## Development

`pipenv` is required for managing our development environment.
```sh
# setup your environment
$ pipenv sync
# activate the environment
$ pipenv shell
```

- Update depedencies in `Pipfile.lock`
```sh
$ pipenv lock --pre
```
- Run all tests
```sh
$ pipenv run tox
```
