#!/usr/bin/env python3
"""Create a public-safe demo database for screenshots and local UI review."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db import connect, create_conclusion, init_db  # noqa: E402


DEMO_CONCLUSIONS = [
    {
        "title": "把深度学习安排在上午",
        "question": "每天应该在什么时间处理最需要专注的学习任务？",
        "conclusion": "工作日早上先留出九十分钟做深度学习，再处理消息和零碎任务。",
        "reason": "上午的注意力更稳定，也更少被临时事项打断。",
        "tradeoffs": "需要推迟查看消息，并接受部分早晨安排缺少弹性。",
        "conditions": "如果上午出现固定会议，重新选择当天最早的完整专注时段。",
        "category": "学习",
        "tags": ["深度学习", "时间安排"],
        "confidence": "High",
        "decision_analysis": {
            "version": 1,
            "models": [
                {
                    "model_id": "time-horizons",
                    "answers": {
                        "ten_hours": "当天更早完成高难度任务，晚些时候压力更小。",
                        "ten_days": "连续执行后，更容易形成稳定的启动习惯。",
                        "ten_months": "长期积累的完整专注时段会显著增加。",
                        "ten_years": "具体时段不重要，保护长期深度工作的习惯更重要。",
                    },
                },
                {
                    "model_id": "munger-checklist",
                    "answers": {
                        "incentives": "即时消息奖励快速回应，但不奖励真正重要的长期学习。",
                        "opportunity_cost": "把上午给零碎任务，就放弃了当天质量最高的注意力。",
                        "inversion": "想保证学不深，只要每天先打开消息并不断切换任务。",
                        "second_order_effects": "先完成深度学习会降低拖延带来的持续心理负担。",
                        "circle_of_competence": "已观察到自己的上午专注度更高，但还需继续记录。",
                        "disconfirming_evidence": "如果连续两周上午产出更低，就应调整时间。",
                    },
                },
            ],
        },
        "timestamp": "2026-07-11T13:00:00Z",
    },
    {
        "title": "先改善睡眠，再增加训练量",
        "question": "近期精力不足时，应该增加锻炼还是优先调整作息？",
        "conclusion": "先连续两周稳定睡眠时间，恢复后再逐步增加训练量。",
        "reason": "睡眠不足会降低恢复质量，直接加量更容易让疲劳持续累积。",
        "tradeoffs": "短期训练进度会慢一些，但降低了受伤和中断计划的风险。",
        "conditions": "连续两周睡眠稳定且白天精力恢复后，再增加训练量。",
        "category": "健康",
        "tags": ["睡眠", "训练"],
        "confidence": "High",
        "timestamp": "2026-07-09T15:30:00Z",
    },
    {
        "title": "暂不更换现有书桌",
        "question": "现有书桌还能使用，是否应该立即升级为升降桌？",
        "conclusion": "暂不购买，等现有书桌明显限制使用时再重新评估。",
        "reason": "当前改善有限，不值得立即占用预算和空间。",
        "tradeoffs": "暂时接受高度和收纳不够理想。",
        "conditions": "现有书桌影响坐姿或无法容纳必要设备时重新评估。",
        "category": "购物",
        "tags": ["家具", "延迟购买"],
        "confidence": "Medium",
        "timestamp": "2026-07-06T18:20:00Z",
    },
    {
        "title": "应急金不参与长期投资",
        "question": "为了提高收益，是否应该把应急金也投入波动资产？",
        "conclusion": "保留六个月基本支出的高流动性应急金，不参与长期投资。",
        "reason": "应急金的目标是随时可用，而不是最大化收益。",
        "tradeoffs": "接受这部分资金的长期收益低于股票等风险资产。",
        "conditions": "基本支出或收入稳定性显著变化时，重新计算应急金额度。",
        "category": "投资",
        "tags": ["应急金", "资产配置"],
        "confidence": "High",
        "timestamp": "2026-07-02T14:10:00Z",
    },
]


def remove_database_files(database_path: Path) -> None:
    for path in (
        database_path,
        Path(f"{database_path}-wal"),
        Path(f"{database_path}-shm"),
    ):
        if path.exists():
            path.unlink()


def seed(database_path: Path, *, clean: bool = False) -> None:
    if database_path.exists() and not clean:
        raise FileExistsError(f"Demo database already exists: {database_path}")
    if clean:
        remove_database_files(database_path)

    with connect(database_path) as connection:
        init_db(connection)
        for item in DEMO_CONCLUSIONS:
            values = {key: value for key, value in item.items() if key != "timestamp"}
            created = create_conclusion(connection, values)
            connection.execute(
                """
                UPDATE conclusions
                SET created_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (item["timestamp"], item["timestamp"], created["id"]),
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=ROOT / "build" / "screenshots" / "conclusion.sqlite3",
    )
    parser.add_argument("--clean", action="store_true", help="Replace an existing demo database")
    args = parser.parse_args()

    seed(args.database, clean=args.clean)
    print(f"Seeded {len(DEMO_CONCLUSIONS)} demo Conclusions in {args.database.resolve()}")


if __name__ == "__main__":
    main()
