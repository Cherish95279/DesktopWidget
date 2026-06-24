#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键打包脚本
用法: python build.py v1.1.9
"""

import os
import sys
import re
import subprocess
import shutil
from datetime import datetime

# 颜色输出（可选）
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


def archive_dist(version):
    """将 dist/ 归档到项目外，带时间戳防止重名"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    archive_root = r"D:\PythonProjects\_archived_builds"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"DesktopWidget_{version}_{timestamp}"
    archive_path = os.path.join(archive_root, archive_name)

    if not os.path.exists("dist"):
        print_info("没有 dist/ 文件夹需要归档")
        return

    os.makedirs(archive_path, exist_ok=True)
    dest = os.path.join(archive_path, "dist")
    shutil.move("dist", dest)
    print_info(f"已归档: dist/ -> {archive_path}\\dist")

    if os.path.exists("build"):
        shutil.rmtree("build")
        print_info("已删除: build/")


def update_version(version):
    """更新 constants.py 和 DesktopWidget.iss 中的版本号"""
    clean_version = version.lstrip('v')

    constants_path = "src/constants.py"
    with open(constants_path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = re.sub(r'VERSION = "v\d+\.\d+\.\d+"', f'VERSION = "{version}"', content)
    with open(constants_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print_info(f"已更新 {constants_path}: VERSION = {version}")

    iss_path = "DesktopWidget.iss"
    with open(iss_path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = re.sub(r'#define MyAppVersion "\d+\.\d+\.\d+"', f'#define MyAppVersion "{clean_version}"', content)
    content = re.sub(r'VersionInfoTextVersion=\d+\.\d+\.\d+', f'VersionInfoTextVersion={clean_version}', content)
    content = re.sub(r'DesktopWidget-v\d+\.\d+\.\d+-win64-Cherish-Setup',
                     f'DesktopWidget-v{clean_version}-win64-Cherish-Setup', content)
    with open(iss_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print_info(f"已更新 {iss_path}: MyAppVersion = {clean_version}")


def run_pyinstaller():
    """执行 PyInstaller 打包（已移除 astral）"""
    print_info("正在执行 PyInstaller 打包...")
    cmd = [
        "pyinstaller",
        "-D", "-w",
        "-n", "DesktopWidget",
        "-i", "icons/app.ico",
        "--collect-all", "requests",
        "--collect-all", "certifi",
        "--hidden-import=requests",
        "--hidden-import=urllib3",
        "--hidden-import=certifi",
        "--hidden-import=charset_normalizer",
        "--hidden-import=idna",
        "--hidden-import=zhdate",
        "--add-data", "skins;skins",
        "--add-data", "icons;icons",
        "widget.py"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print_error("PyInstaller 打包失败！")
        print(result.stderr)
        sys.exit(1)
    print_info("PyInstaller 打包完成！")


def run_inno_setup():
    """执行 Inno Setup 编译"""
    print_info("正在执行 Inno Setup 编译...")
    iscc_path = r"D:\Program Files (x86)\Inno Setup 6\iscc.exe"

    if not os.path.exists(iscc_path):
        print_error(f"未找到 Inno Setup Compiler: {iscc_path}")
        print_warn("请确认路径是否正确，或修改脚本中的 iscc_path")
        sys.exit(1)

    result = subprocess.run([iscc_path, "DesktopWidget.iss"], capture_output=True, text=True)
    if result.returncode != 0:
        print_error("Inno Setup 编译失败！")
        print(result.stderr)
        sys.exit(1)
    print_info("Inno Setup 编译完成！")


def main():
    if len(sys.argv) < 2:
        print_error("请指定版本号！")
        print("用法: python build.py v1.1.9")
        sys.exit(1)

    version = sys.argv[1]
    if not re.match(r'v?\d+\.\d+\.\d+', version):
        print_error(f"无效的版本号格式: {version}")
        print("请使用 v1.1.9 或 1.1.9 格式")
        sys.exit(1)

    if not version.startswith('v'):
        version = 'v' + version

    print_info(f"开始打包 {version}...")
    print("=" * 50)

    update_version(version)
    archive_dist(version)
    run_pyinstaller()
    run_inno_setup()

    clean_version = version.lstrip('v')
    print("=" * 50)
    print_info(f"✅ 打包完成！")
    print_info(f"输出文件: dist\\DesktopWidget-v{clean_version}-win64-Cherish-Setup.exe")
    print_info(f"版本号: {version}")
    print_info("")
    print_info("📌 下一步:")
    print_info("  1. 测试安装包是否正常")
    print_info("  2. 手动提交 Git: git add . && git commit -m 'v{clean_version}'")
    print_info("  3. 手动创建 Tag: git tag {version}")
    print_info("  4. 推送到 GitHub: git push && git push --tags")


if __name__ == "__main__":
    main()