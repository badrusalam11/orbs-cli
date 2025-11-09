from setuptools import setup, find_packages

setup(
    name="orbs",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "typer[all]",
        "flask",
        "pyyaml",
        "apscheduler",
        "jinja2",
        "requests",
        "python-dotenv",
        "Appium-Python-Client",
        "selenium",
        "behave",
        "reportlab",
        "InquirerPy"
    ],
    entry_points={
        'console_scripts': [
            'orbs=orbs.cli:app',
        ],
    },
    package_data={
        'orbs': [
            'templates/**/*',
            'spy/js/*.js',
        ]
    },
    include_package_data=True,
)