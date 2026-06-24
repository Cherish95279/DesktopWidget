#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一键推送脚本
用法:
  push.py                # 交互式运行
  push.py "提交信息"      # 直接推送全部文件
  push.py "提交信息" tag  # 推送全部文件 + 打标签
"""

import os
import sys
import subprocess
import re


def get_git_root():
    """获取 Git 仓库根目录"""
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ 当前目录不是 Git 仓库")
        sys.exit(1)
    return result.stdout.strip()


def run_git_command(cmd, description="执行Git命令"):
    """执行 Git 命令并返回结果"""
    print(f"→ {description}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ 失败: {result.stderr.strip()}")
        return False
    if result.stdout.strip():
        print(f"✅ {result.stdout.strip()}")
    else:
        print(f"✅ 完成")
    return True


def get_changed_files():
    """获取已修改和未跟踪的文件列表"""
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    files = []
    for line in result.stdout.strip().split('\n'):
        if line:
            status = line[:2]
            file_path = line[3:]
            files.append((status, file_path))
    return files


def main():
    # 切换到 Git 根目录
    os.chdir(get_git_root())
    print(f"📁 当前目录: {os.getcwd()}")

    # 获取当前分支
    branch_result = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
    current_branch = branch_result.stdout.strip()
    print(f"🌿 当前分支: {current_branch}")

    # 获取变更文件
    changed = get_changed_files()
    if not changed:
        print("✅ 没有需要提交的变更")
        return

    print(f"\n📋 变更文件 ({len(changed)} 个):")
    for status, file_path in changed:
        status_map = {
            "M ": "修改",
            "A ": "新增",
            "D ": "删除",
            "R ": "重命名",
            "??": "未跟踪",
        }
        desc = status_map.get(status, status)
        print(f"  {desc}: {file_path}")

    # 检查是否有参数传入
    if len(sys.argv) > 1:
        # 命令行模式
        commit_msg = sys.argv[1]
        create_tag = len(sys.argv) > 2 and sys.argv[2].lower() in ["tag", "t"]
        add_all = True
    else:
        # 交互式模式
        print("\n" + "=" * 50)
        choice = input(
            "【选择操作】\n  [A] 添加所有文件并提交\n  [F] 只提交指定文件\n  [C] 取消\n请选择 (A/F/C): ").strip().lower()

        if choice == 'c':
            print("已取消")
            return
        elif choice == 'f':
            files_to_add = input("请输入要提交的文件名（用空格分隔）: ").strip().split()
            if not files_to_add:
                print("未选择任何文件，已取消")
                return
            for f in files_to_add:
                if not run_git_command(["git", "add", f], f"添加 {f}"):
                    return
            add_all = False
        else:
            # 默认 A
            add_all = True

        commit_msg = input("请输入提交信息: ").strip()
        if not commit_msg:
            print("提交信息不能为空，已取消")
            return

        create_tag_input = input("是否创建版本标签？(y/n): ").strip().lower()
        create_tag = create_tag_input in ['y', 'yes', '是']

    # 执行 git add
    if add_all:
        if not run_git_command(["git", "add", "."], "添加所有文件"):
            return

    # 执行 git commit
    if not run_git_command(["git", "commit", "-m", commit_msg], f"提交: {commit_msg}"):
        return

    # 执行 git push
    if not run_git_command(["git", "push"], f"推送到 {current_branch}"):
        return

    # 创建并推送标签
    if create_tag:
        # 从提交信息中提取版本号（如 v1.1.9 或 1.1.9）
        tag_pattern = r'v?\d+\.\d+\.\d+'
        matches = re.findall(tag_pattern, commit_msg)
        if matches:
            tag_name = matches[0]
            if not tag_name.startswith('v'):
                tag_name = 'v' + tag_name
        else:
            tag_name = input("请输入标签名（如 v1.1.9）: ").strip()
            if not tag_name:
                print("未指定标签名，跳过创建标签")
                create_tag = False

        if create_tag:
            if not run_git_command(["git", "tag", tag_name], f"创建标签 {tag_name}"):
                return
            if not run_git_command(["git", "push", "--tags"], f"推送标签 {tag_name}"):
                return

    print(f"\n✅ 全部完成！")
    print(f"   - 提交: {commit_msg}")
    if create_tag and tag_name:
        print(f"   - 标签: {tag_name}")
    print(f"   - 分支: {current_branch}")


if __name__ == "__main__":
    main()