#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键推送脚本
用法:
  push.py                    # 交互式运行（推荐）
  push.py "提交信息"          # 快速推送
  push.py "提交信息" tag      # 快速推送 + 打标签
  push.py "提交信息" tag v1.2.2  # 快速推送 + 指定标签名
"""

import os
import sys
import subprocess
import re

# ===== 颜色输出 =====
try:
    from colorama import init, Fore, Style
    init()
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    RED = Fore.RED
    CYAN = Fore.CYAN
    RESET = Style.RESET_ALL
except ImportError:
    GREEN = YELLOW = RED = CYAN = RESET = ""


def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")


def print_info(msg):
    print(f"{YELLOW}ℹ️ {msg}{RESET}")


def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")


def print_title(msg):
    print(f"\n{CYAN}{'='*50}{RESET}")
    print(f"{CYAN}{msg}{RESET}")
    print(f"{CYAN}{'='*50}{RESET}")


def get_git_root():
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode != 0:
        print_error("当前目录不是 Git 仓库")
        sys.exit(1)
    return result.stdout.strip()


def run_git_command(cmd, description="执行Git命令", capture=False):
    print(f"→ {description}...")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode != 0:
        err_msg = result.stderr.strip() if result.stderr else "未知错误"
        print_error(f"失败: {err_msg}")
        if capture:
            return None
        return False
    if result.stdout and result.stdout.strip():
        print_success(result.stdout.strip())
    else:
        print_success("完成")
    if capture:
        return result.stdout.strip()
    return True


def get_changed_files():
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, encoding='utf-8', errors='replace')
    files = []
    for line in result.stdout.strip().split('\n'):
        if line:
            status = line[:2]
            file_path = line[3:]
            files.append((status, file_path))
    return files


def get_current_branch():
    result = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, encoding='utf-8', errors='replace')
    return result.stdout.strip()


def get_version_from_files():
    """从 constants.py 或 .iss 中读取版本号"""
    try:
        with open("src/constants.py", 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'VERSION = "v?([\d.]+)"', content)
        if match:
            return match.group(1)
    except:
        pass

    try:
        with open("DesktopWidget.iss", 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'#define MyAppVersion "([\d.]+)"', content)
        if match:
            return match.group(1)
    except:
        pass

    return None


def main():
    os.chdir(get_git_root())
    print_info(f"当前目录: {os.getcwd()}")

    current_branch = get_current_branch()
    print_info(f"当前分支: {current_branch}")

    # 获取变更文件
    changed = get_changed_files()
    if not changed:
        print_success("没有需要提交的变更")
        return

    print_title(f"📋 变更文件 ({len(changed)} 个):")
    status_map = {
        "M ": "修改",
        "A ": "新增",
        "D ": "删除",
        "R ": "重命名",
        "??": "未跟踪",
    }
    for status, file_path in changed:
        desc = status_map.get(status, status)
        print(f"  {desc}: {file_path}")

    # ===== 解析命令行参数 =====
    if len(sys.argv) >= 2:
        # 命令行模式：快速推送
        commit_msg = sys.argv[1]
        create_tag = len(sys.argv) > 2 and sys.argv[2].lower() in ["tag", "t"]
        tag_name = sys.argv[3] if len(sys.argv) > 3 else None
        add_all = True
    else:
        # ===== 交互式模式 =====
        print()
        print_title("📝 提交选项")

        # 1. 选择操作
        print("  [A] 添加所有文件并提交 (推荐)")
        print("  [F] 只提交指定文件")
        print("  [C] 取消")
        choice = input("\n请选择 (A/F/C): ").strip().lower()

        if choice == 'c':
            print_info("已取消")
            return
        elif choice == 'f':
            files_to_add = input("请输入要提交的文件名（用空格分隔）: ").strip().split()
            if not files_to_add:
                print_error("未选择任何文件，已取消")
                return
            add_all = False
        else:
            add_all = True

        # 2. 提交信息
        # 尝试从版本号自动生成提交信息
        version = get_version_from_files()
        if version:
            default_msg = f"v{version}: 更新代码"
        else:
            default_msg = "更新代码"
        commit_msg = input(f"提交信息 (回车使用: {default_msg}): ").strip()
        if not commit_msg:
            commit_msg = default_msg
            print_info(f"使用默认提交信息: {commit_msg}")

        # 3. 是否打标签
        create_tag_input = input("是否创建版本标签？(y/n，默认 n): ").strip().lower()
        create_tag = create_tag_input in ['y', 'yes', '是']

        tag_name = None
        if create_tag:
            # 自动从版本号提取
            version = get_version_from_files()
            if version:
                default_tag = f"v{version}"
            else:
                default_tag = ""
            tag_input = input(f"标签名 (回车使用: {default_tag}): ").strip()
            if tag_input:
                tag_name = tag_input
            elif default_tag:
                tag_name = default_tag
                print_info(f"使用默认标签: {tag_name}")
            else:
                print_error("未指定标签名，跳过创建标签")
                create_tag = False

    # ===== 执行 git add =====
    if add_all:
        if not run_git_command(["git", "add", "."], "添加所有文件"):
            return
    else:
        for f in files_to_add:
            if not run_git_command(["git", "add", f], f"添加 {f}"):
                return

    # ===== 执行 git commit =====
    if not run_git_command(["git", "commit", "-m", commit_msg], f"提交: {commit_msg}"):
        return

    # ===== 执行 git push =====
    if not run_git_command(["git", "push"], f"推送到 {current_branch}"):
        return

    # ===== 创建并推送标签 =====
    if create_tag and tag_name:
        if not run_git_command(["git", "tag", tag_name], f"创建标签 {tag_name}"):
            return
        if not run_git_command(["git", "push", "--tags"], f"推送标签 {tag_name}"):
            return

    # ===== 完成 =====
    print()
    print_title("✅ 全部完成！")
    print(f"   - 提交: {commit_msg}")
    if create_tag and tag_name:
        print(f"   - 标签: {tag_name}")
    print(f"   - 分支: {current_branch}")


if __name__ == "__main__":
    main()