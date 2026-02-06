from setuptools import setup

setup(
    name="charles",
    version="0.1.0",
    py_modules=["charles"],
    entry_points={
        "console_scripts": [
            "charles=charles:main",
        ],
    },
    python_requires=">=3.8",
)
