"""
Setup script for DetoxBuddy
"""

from setuptools import setup, find_packages

setup(
    name="detoxbuddy",
    version="1.0.0",
    description="Telegram Bot для цифрового детокса",
    author="DetoxBuddy Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "python-telegram-bot==20.7",
        "sqlalchemy==2.0.27",
        "alembic==1.13.1",
        "psycopg2-binary==2.9.9",
        "redis==5.0.1",
        "celery==5.3.4",
        "pillow==10.2.0",
        "opencv-python==4.9.0.80",
        "pandas==2.2.0",
        "numpy==1.26.4",
        "matplotlib==3.8.3",
        "python-dotenv==1.0.1",
        "pydantic==2.6.1",
        "pydantic-settings==2.2.1",
        "structlog==24.1.0",
        "aiofiles==23.2.1",
    ],
    extras_require={
        "dev": [
            "pytest==8.0.2",
            "pytest-asyncio==0.23.5",
            "black==24.2.0",
            "isort==5.13.2",
            "flake8==7.0.0",
            "mypy==1.8.0",
        ]
    }
)
