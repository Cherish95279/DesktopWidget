#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
一键打包脚本

用法:
python tools/build.py v1.2.2
"""

import os
import sys
import re
import subprocess
import shutil
from datetime import datetime


# GitHub Actions Windows Runner UTF-8兼容
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# 颜色输出
try:
    from colorama import init, Fore, Style

    init()

    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    RED = Fore.RED
    RESET = Style.RESET_ALL

except ImportError:
    GREEN = YELLOW = RED = RESET = ""


def print_info(msg):
    print(f"{GREEN}[INFO]{RESET} {msg}")


def print_warn(msg):
    print(f"{YELLOW}[WARN]{RESET} {msg}")


def print_error(msg):
    print(f"{RED}[ERROR]{RESET} {msg}")


def get_project_root():
    """获取项目根目录"""
    return os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )


def archive_dist(version):
    """归档旧dist"""

    project_root = get_project_root()

    archive_root = os.environ.get(
        "BUILD_ARCHIVE_DIR",
        r"D:\PythonProjects\_archived_builds"
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    archive_name = (
        f"DesktopWidget_{version}_{timestamp}"
    )

    archive_path = os.path.join(
        archive_root,
        archive_name
    )

    dist_path = os.path.join(
        project_root,
        "dist"
    )

    if not os.path.exists(dist_path):
        print_info(
            "没有 dist/ 文件夹需要归档"
        )
        return


    os.makedirs(
        archive_path,
        exist_ok=True
    )


    shutil.move(
        dist_path,
        os.path.join(
            archive_path,
            "dist"
        )
    )

    print_info(
        f"已归档: dist/ -> {archive_path}\\dist"
    )


    build_path = os.path.join(
        project_root,
        "build"
    )

    if os.path.exists(build_path):

        shutil.rmtree(
            build_path
        )

        print_info(
            "已删除: build/"
        )


def update_version(version):
    """
    更新:
    constants.py
    DesktopWidget.iss
    """

    project_root = get_project_root()

    clean_version = version.lstrip("v")


    # constants.py

    constants_path = os.path.join(
        project_root,
        "src",
        "constants.py"
    )


    with open(
        constants_path,
        "r",
        encoding="utf-8"
    ) as f:

        content = f.read()


    content = re.sub(
        r'VERSION = "v\d+\.\d+\.\d+"',
        f'VERSION = "{version}"',
        content
    )


    with open(
        constants_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(content)


    print_info(
        f"已更新 {constants_path}: VERSION = {version}"
    )



    # DesktopWidget.iss

    iss_path = os.path.join(
        project_root,
        "DesktopWidget.iss"
    )


    with open(
        iss_path,
        "r",
        encoding="utf-8"
    ) as f:

        content = f.read()



    content = re.sub(
        r'#define MyAppVersion "\d+\.\d+\.\d+"',
        f'#define MyAppVersion "{clean_version}"',
        content
    )


    content = re.sub(
        r'VersionInfoTextVersion=\d+\.\d+\.\d+',
        f'VersionInfoTextVersion={clean_version}',
        content
    )

    content = re.sub(
        r'DesktopWidget-v\d+\.\d+\.\d+-windows-x64-Setup',
        f'DesktopWidget-v{clean_version}-windows-x64-Setup',
        content
    )


    with open(
        iss_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(content)



    print_info(
        f"已更新 {iss_path}: MyAppVersion = {clean_version}"
    )



def run_pyinstaller():

    project_root = get_project_root()

    print_info(
        "正在执行 PyInstaller 打包..."
    )


    os.chdir(
        project_root
    )


    cmd = [

        "pyinstaller",

        "-D",

        "--windowed",

        "--noconsole",

        "-n",
        "DesktopWidget",

        "-i",
        "icons/app.ico",

        "--collect-all",
        "zhdate",

        "--hidden-import",
        "zhdate",

        "--add-data",
        f"skins{os.pathsep}skins",

        "--add-data",
        f"icons{os.pathsep}icons",

        "--add-data",
        f"src/translations{os.pathsep}translations",

        "widget.py"
    ]


    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )


    if result.returncode != 0:

        print_error(
            "PyInstaller 打包失败！"
        )

        print(result.stderr)

        sys.exit(1)



    print_info(
        "PyInstaller 打包完成！"
    )



def run_inno_setup():

    project_root = get_project_root()


    print_info(
        "正在执行 Inno Setup 编译..."
    )


    # 查找iscc.exe

    iscc_path = os.environ.get(
        "ISCC_PATH"
    )


    if not iscc_path:

        iscc_path = shutil.which(
            "iscc"
        )


    if not iscc_path:

        iscc_path = (
            r"D:\Program Files (x86)"
            r"\Inno Setup 6\iscc.exe"
        )



    if not os.path.exists(iscc_path):

        print_error(
            f"未找到 Inno Setup Compiler: {iscc_path}"
        )

        sys.exit(1)



    iss_path = os.path.join(
        project_root,
        "DesktopWidget.iss"
    )


    if not os.path.exists(iss_path):

        print_error(
            f"未找到脚本: {iss_path}"
        )

        sys.exit(1)



    os.chdir(
        project_root
    )


    result = subprocess.run(
        [
            iscc_path,
            iss_path
        ],

        capture_output=True,

        text=True,

        encoding="utf-8",

        errors="replace"
    )


    if result.returncode != 0:

        print_error(
            "Inno Setup 编译失败！"
        )

        print(result.stderr)

        sys.exit(1)



    print_info(
        "Inno Setup 编译完成！"
    )



def main():


    if len(sys.argv) < 2:

        print_error(
            "请指定版本号！"
        )

        print(
            "用法: python tools/build.py v1.2.2"
        )

        sys.exit(1)



    version = sys.argv[1]


    if not re.match(
        r"v?\d+\.\d+\.\d+",
        version
    ):

        print_error(
            f"无效版本号: {version}"
        )

        sys.exit(1)



    if not version.startswith("v"):

        version = "v" + version



    print_info(
        f"开始打包 {version}..."
    )

    print("=" * 50)



    update_version(version)

    archive_dist(version)

    run_pyinstaller()

    run_inno_setup()



    clean_version = version.lstrip("v")



    print("=" * 50)

    print_info(
        "✅ 打包完成！"
    )


    print_info(
        f"输出文件: dist\\DesktopWidget-v{clean_version}-windows-x64-Setup.exe"

        
    )


    print_info(
        f"版本号: {version}"
    )


    print_info("")

    print_info(
        "📌 下一步:"
    )

    print_info(
        "  1. 测试安装包是否正常"
    )

    print_info(
        "  2. 提交 Git"
    )

    print_info(
        "  3. 创建 Tag"
    )

    print_info(
        "  4. 推送 Release"
    )



if __name__ == "__main__":
    main()