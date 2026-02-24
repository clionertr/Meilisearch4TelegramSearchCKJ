#!/usr/bin/env python
"""
集成测试 CLI 入口

编排完整的集成测试流程：
  1. 启动环境（MeiliSearch + API server）
  2. 创建测试群组（可选）
  3. 运行 pytest 测试

用法:
    # 完整流程
    python tests/integration/run.py

    # 跳过群组创建（使用已有群组）
    python tests/integration/run.py --skip-setup

    # 不自动管理环境（假设已在运行）
    python tests/integration/run.py --no-env

    # 只运行指定测试
    python tests/integration/run.py --only health_check,search_basic

    # 跳过指定测试
    python tests/integration/run.py --skip download_history,websocket_progress

    # 强制重建测试群组
    python tests/integration/run.py --force-setup

    # 也可以直接用 pytest 运行（需自行管理环境）
    RUN_INTEGRATION_TESTS=true pytest tests/integration/test_api_e2e.py -v -s
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="integration-test",
        description="Meilisearch4TelegramSearchCKJ 集成测试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python tests/integration/run.py                          # 完整流程
  python tests/integration/run.py --no-env                 # 不管理环境
  python tests/integration/run.py --skip-setup             # 跳过群组创建
  python tests/integration/run.py --only health_check,search_basic
  python tests/integration/run.py --skip download_history
        """,
    )

    parser.add_argument(
        "--no-env",
        action="store_true",
        help="不自动管理环境（不启动 MeiliSearch / API server）",
    )
    parser.add_argument(
        "--skip-setup",
        action="store_true",
        help="跳过测试群组创建（使用已有 .test_groups.json）",
    )
    parser.add_argument(
        "--force-setup",
        action="store_true",
        help="强制重新创建测试群组（即使已存在）",
    )
    parser.add_argument(
        "--only",
        type=str,
        default="",
        help="逗号分隔的测试名列表，仅运行这些测试",
    )
    parser.add_argument(
        "--skip",
        type=str,
        default="",
        help="逗号分隔的测试名列表，跳过这些测试",
    )
    parser.add_argument(
        "--pytest-args",
        type=str,
        default="-v -s --tb=short",
        help="传递给 pytest 的额外参数（默认: -v -s --tb=short）",
    )
    parser.add_argument(
        "--list-tests",
        action="store_true",
        help="列出所有可用的测试开关名称并退出",
    )

    return parser.parse_args()


def list_available_tests() -> None:
    """列出所有可用测试及其默认状态"""
    from tests.integration.config import _DEFAULT_SWITCHES

    print("\n可用的测试开关：")
    print("-" * 50)
    for name, default in _DEFAULT_SWITCHES.items():
        status = "✅ 默认启用" if default else "⏭️  默认跳过"
        print(f"  {name:<25} {status}")
    print("-" * 50)
    print("\n使用 --only 或 --skip 控制执行/跳过")
    print("或设置环境变量: INTEGRATION_ONLY / INTEGRATION_SKIP")


def main() -> int:
    args = parse_args()

    if args.list_tests:
        list_available_tests()
        return 0

    print("=" * 60)
    print("  Meilisearch4TelegramSearchCKJ 集成测试")
    print("=" * 60)
    print(f"  时间: {datetime.now().isoformat()}")
    print(f"  项目: {PROJECT_ROOT}")
    print()

    # 设置 INTEGRATION_ONLY / INTEGRATION_SKIP 环境变量
    if args.only:
        os.environ["INTEGRATION_ONLY"] = args.only
        print(f"  仅运行: {args.only}")
    if args.skip:
        os.environ["INTEGRATION_SKIP"] = args.skip
        print(f"  跳过: {args.skip}")

    # 开启集成测试
    os.environ["RUN_INTEGRATION_TESTS"] = "true"

    # ====== Step 1: 启动环境 ======
    if not args.no_env:
        print("\n📦 Step 1: 启动测试环境...")
        print("-" * 40)
        from tests.integration.env_manager import start_all, wait_for_ready

        start_all()

        if not wait_for_ready():
            print("❌ 环境启动失败")
            return 1
        print("✅ 环境就绪\n")
    else:
        print("\n⏭️  Step 1: 跳过环境管理（--no-env）\n")

    # ====== Step 2: 准备测试群组 ======
    if not args.skip_setup:
        print("👥 Step 2: 准备测试群组...")
        print("-" * 40)
        try:
            from tests.integration.test_group_setup import run_setup

            group_data = run_setup(force=args.force_setup)
            print(f"✅ 测试群组就绪: {group_data.get('group_title')} "
                  f"(ID: {group_data.get('group_id')}, "
                  f"消息: {group_data.get('message_count')}条)\n")
            if group_data.get("probe_marker"):
                print(
                    "  审查探针: "
                    f"marker={group_data.get('probe_marker')}, "
                    f"keyword={group_data.get('probe_keyword')}, "
                    f"count={group_data.get('probe_message_count')}"
                )
                print("  将执行强保证校验: 下载链路审核 / 搜索结果格式审核 / 高亮审核")
                print()
        except Exception as e:
            print(f"⚠️  测试群组创建失败: {e}")
            print("   继续运行测试（某些需要群组的测试会跳过）\n")
    else:
        print("⏭️  Step 2: 跳过群组创建（--skip-setup）\n")

    # ====== Step 3: 运行集成测试 ======
    print("🧪 Step 3: 运行集成测试...")
    print("-" * 40)

    import pytest as _pytest

    # 运行整个 tests/integration/ 目录，发现所有 test_*.py 文件
    test_dir = str(Path(__file__).parent)
    pytest_args = args.pytest_args.split() + [test_dir]

    print(f"  pytest {' '.join(pytest_args)}\n")

    exit_code = _pytest.main(pytest_args)

    # ====== 报告 ======
    print("\n" + "=" * 60)
    if exit_code == 0:
        print("  ✅ 所有测试通过！")
    else:
        print(f"  ❌ 测试失败 (exit code: {exit_code})")
    print("=" * 60)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
