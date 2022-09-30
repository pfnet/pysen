try:
    import pysen

    setup = pysen.setup_from_pyproject(__file__)
except ImportError:
    import setuptools

    setup = setuptools.setup  # type: ignore


setup(
    name="example-sync-cmdclass-pyproject",
    version="0.0.0",
    packages=[],
)
