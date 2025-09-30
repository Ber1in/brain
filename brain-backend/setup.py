# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import setuptools
from datetime import datetime


def load_requirements(filename="requirements.txt"):
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def get_version():
    now = datetime.now()
    version = f"{now.year % 100}.{now.month}.{now.day}.{now.hour}{now.minute}"
    return version


setuptools.setup(
    name="brain",
    description="A lightweight cloud management system to manage all mv200",
    license="Proprietary",
    license_files=["LICENSE.txt"],
    author="Yunsilicon",
    version=get_version(),
    packages=setuptools.find_packages(),
    install_requires=load_requirements(),
    include_package_data=True,
)
