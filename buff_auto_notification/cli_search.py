#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI 工具：根据用户输入的名称搜索 Buff 市场物品，并在选择后按物品 ID 进行精确查询。

用法：
  - 非交互：
    python3 cli_search.py --cookie "session=..." --query "Golden Basher" --game dota2 --select 0
  - 交互：
    python3 cli_search.py  # 按提示输入 Cookie、关键词并选择条目

结果保存：
  - 会将搜索与精确查询结果保存到 `../shared_market_cache/json/<goods_id>_detail.json`
  - 结构示例：
    {
      "query": {"keyword": "...", "game": "dota2", "selected_id": 123, "selected_name": "..."},
      "search_results": [{简化字段...}],
      "detail": {"items": [...], "goods_infos": {...}},
      "timestamp": "ISO 时间"
    }
"""

import os
import sys
import json
import argparse
from datetime import datetime

# 允许从环境变量读取 Cookie
DEFAULT_COOKIE_ENV = "BUFF_COOKIE"

# 相对路径假设从 buff_auto_notification 目录运行
CACHE_JSON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "shared_market_cache", "json"))

# 兼容直接运行时的模块导入
try:
    from BuffApiPublic import BuffAccount
except Exception:
    # 支持从项目根目录执行
    sys.path.append(os.path.dirname(__file__))
    from BuffApiPublic import BuffAccount


def pick_cookie(args_cookie: str) -> str:
    """选择 Cookie 来源：命令行参数优先，其次环境变量，否则交互输入。"""
    if args_cookie:
        return args_cookie
    env_cookie = os.environ.get(DEFAULT_COOKIE_ENV)
    if env_cookie:
        return env_cookie
    print("未提供 --cookie，且未检测到环境变量 BUFF_COOKIE。")
    return input("请输入 Buff Cookie (至少包含 session=...): ").strip()


def parse_args():
    p = argparse.ArgumentParser(description="按名称搜索并精确查询 Buff 市场物品")
    p.add_argument("--cookie", type=str, default=None, help="Buff Cookie（如不提供则读取环境变量 BUFF_COOKIE 或交互输入）")
    p.add_argument("--query", type=str, default=None, help="搜索关键词（物品名称或关键字）")
    p.add_argument("--game", type=str, default="dota2", help="游戏名称，默认 dota2")
    p.add_argument("--select", type=int, default=None, help="自动选择搜索结果的索引（从 0 开始）")
    p.add_argument("--limit", type=int, default=10, help="搜索结果展示的最大条数")
    return p.parse_args()


def ensure_cache_dir():
    os.makedirs(CACHE_JSON_DIR, exist_ok=True)


def simplify_item(item: dict) -> dict:
    """提取常用字段，便于存储与展示。"""
    fields = [
        "id", "appid", "game", "name", "short_name", "market_hash_name",
        "sell_min_price", "sell_num", "buy_max_price", "buy_num", "quick_price"
    ]
    return {k: item.get(k) for k in fields if k in item}


def search_items(buff: BuffAccount, keyword: str, game: str, limit: int = 10):
    items = buff.search_goods_list(key=keyword, game_name=game)
    if not items:
        return []
    # 保留前 limit 条，并简化
    return [simplify_item(it) for it in (items[:limit] if isinstance(items, list) else items)]


def choose_index(items: list, preselect: int | None) -> int:
    if preselect is not None:
        if 0 <= preselect < len(items):
            return preselect
        raise ValueError(f"--select 超出范围 (0..{len(items)-1})")

    print("\n搜索结果：")
    for i, it in enumerate(items):
        name = it.get("name") or it.get("market_hash_name") or it.get("short_name") or "<未知>"
        print(f"[{i}] id={it.get('id')} | {name} | 价格: {it.get('sell_min_price','-')} | 在售: {it.get('sell_num','-')}")
    while True:
        s = input(f"\n请选择索引 (0..{len(items)-1}): ").strip()
        try:
            idx = int(s)
            if 0 <= idx < len(items):
                return idx
        except Exception:
            pass
        print("输入无效，请重试。")


def save_result(goods_id: str, keyword: str, game: str, selected_name: str, search_results: list, detail_payload: dict) -> str:
    ensure_cache_dir()
    out_path = os.path.join(CACHE_JSON_DIR, f"{goods_id}_detail.json")
    content = {
        "query": {
            "keyword": keyword,
            "game": game,
            "selected_id": goods_id,
            "selected_name": selected_name,
        },
        "search_results": search_results,
        "detail": detail_payload,
        "timestamp": datetime.now().isoformat(),
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    return out_path


def main():
    args = parse_args()

    # 1) 获取 Cookie 并初始化 Buff 客户端
    cookie = pick_cookie(args.cookie)
    try:
        buff = BuffAccount(buffcookie=cookie)
    except Exception as e:
        print(f"Buff 登录失败，请检查 Cookie 是否正确：{e}")
        sys.exit(1)

    # 2) 获取搜索关键词
    keyword = args.query or input("请输入搜索关键词（物品名称/关键字）: ").strip()
    if not keyword:
        print("关键词不能为空。")
        sys.exit(1)

    # 3) 搜索并展示候选条目
    items = search_items(buff, keyword, args.game, limit=args.limit)
    if not items:
        print("未找到匹配条目。")
        sys.exit(0)

    idx = choose_index(items, args.select)
    chosen = items[idx]
    goods_id = str(chosen.get("id"))
    selected_name = chosen.get("name") or chosen.get("market_hash_name") or chosen.get("short_name") or "<未知>"

    # 4) 精确查询（按商品 ID）
    detail = buff.get_goods_info(goods_id=goods_id, game_name=args.game)
    if not detail:
        print("精确查询失败或返回为空。")
        sys.exit(2)

    # 5) 保存结果到缓存目录
    out_path = save_result(goods_id, keyword, args.game, selected_name, items, detail)
    print(f"\n已保存结果：{out_path}")
    print("你可以在前端选择 shared_market_cache/json/ 目录查看该 JSON 文件。")


if __name__ == "__main__":
    main()