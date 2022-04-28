.. pysen documentation master file, created by
   sphinx-quickstart on Mon Apr 25 09:37:35 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pysen's documentation!
=================================

.. code-block:: toml

   [tool.pysen]
   version       = "0.10"
   builder       = "lint.py"

   [tool.pysen.lint]
   enable_black  = true
   enable_flake8 = true
   enable_isort  = true
   enable_mypy   = true
   mypy_preset   = "strict"
   line_length   = 88
   py_version    = "py37"

   [[tool.pysen.lint.mypy_targets]]
   paths         = ["."]


- ``tool.pysen`` corresponds to :class:`pysen.pyproject_model.Config`
   - For example, ``builder`` under ``[tool.pysen]`` passes to :class:`pysen.pyproject_model.Config`

- ``tool.pysen.lint`` corresponds to :class:`pysen.pyproject_model.LintConfig`
   - If you specify ``line_length`` to ``88``, it is passed to :class:`pysen.pyproject_model.LintConfig`

- ``tool.pysen.plugin`` corresponds to :class:`pysen.pyproject_model.PluginConfig`

You can know what you can change a configuration by checking :class:`~pysen.pyproject_model.Config`,
:class:`~pysen.pyproject_model.LintConfig`, and :class:`~pysen.pyproject_model.PluginConfig`.

If a entry is not an instance of Python built-in class, it cannot be directly specified.
For example, ``mypy_targets`` corresponds to :class:`pysen.ext.mypy_wrapper.MypyTarget`, which is not a Python built-in (or equivarent to built-in) class.
To configure such option, you need to create a section ``[[tool.pysen.lint.mypy_targets]]``.
:class:`~pysen.ext.mypy_wrapper.MypyPlugin` has parameters ``paths`` and ``namespace_packages``.
Since ``paths`` is equivarent to ``str`` and ``namespace_packages`` is ``bool``, you can set them in the section.
Note that ``namespace_packages`` is omitted since it is :obj:`False` by default.


reference
=========

.. toctree::
   :maxdepth: 2

   reference/ext/index
   reference/factory
   reference/mypy
   reference/py_version
   reference/pyproject_model
   reference/source


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
