from setuptools import find_packages, setup

setup(
    name="uptime-sentinel",
    version="0.1.0",
    description="A free, self-hosted website uptime and latency monitor with alerting and Markdown reports.",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "requests>=2.31",
        "PyYAML>=6.0",
    ],
    extras_require={
        "dev": ["pytest>=7.4"],
    },
    entry_points={
        "console_scripts": [
            "sentinel=uptime_sentinel.cli:main",
        ],
    },
    python_requires=">=3.9",
)
