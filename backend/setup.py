"""Liuhecai Backend — setup.py

安装后所有 backend/src/ 下的模块可通过标准包导入，不再需要 sys.path 操作。

安装方式：
    # 开发模式（推荐，修改即时生效）
    pip install -e backend/

    # 正式安装
    pip install backend/

安装后即可在任意位置运行测试和脚本：
    pytest backend/src/tests/unit -q
    python -m liuhecai.main --host 127.0.0.1 --port 8000
"""

from setuptools import setup, find_packages

setup(
    name="liuhecai-backend",
    version="1.0.0",
    description="Liuhecai (Mark Six Lottery) backend API and prediction engine",
    python_requires=">=3.10",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "psycopg>=3.0",
        "psycopg[binary]>=3.0",
    ],
    entry_points={
        "console_scripts": [
            "liuhecai-server=main:main",
        ],
    },
    author="Liuhecai Team",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
