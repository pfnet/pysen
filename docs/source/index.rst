.. pysen documentation master file, created by
   sphinx-quickstart on Mon Apr 25 09:37:35 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pysen's documentation!
=================================

.. code-block:: toml

   [tool.pysen]
   version       = "0.10"

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


- For ``[tool.pysen]``, you can specify entries available in :class:`~pysen.pyproject_model.Config`
- For ``[tool.pysen.lint]``, :class:`~pysen.pyproject_model.LintConfig`
- You can instead specify ``[[tool.pysen.lint.{entry_name}]]``.


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
