"""长周末 / 拼假（Bridge Day）算法。

找出两类信息：
1. 自然长周末：假期与周末相连，无需请假。
2. 拼假选项：请 1-3 个工作日，把假期和另一个周末/假期连成更长假期。

全国性假期由 normalize() 判定：global=True，或 counties 覆盖全部一级行政区；
地方性假期不参与拼假计算，但在年度总表页完整列出并标注适用地区。
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional
import json
import os

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]

_HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(_HERE, "data", "subdivisions.json"), encoding="utf-8") as _f:
    SUBDIVISIONS: dict[str, list[str]] = json.load(_f)


def apply_corrections(holidays: list[dict], country_code: str, year: int) -> list[dict]:
    """应用 data/corrections.json 中对该国该年的官方校正（先 remove 再 add）。

    remove 项按 date 匹配（若提供 name 则需同时匹配）。
    返回校正后的"原始"行列表（仍需再经过 normalize）。
    """
    path = os.path.join(_HERE, "data", "corrections.json")
    if not os.path.exists(path):
        return holidays
    spec = json.load(open(path, encoding="utf-8")).get(f"{country_code}_{year}")
    if not spec:
        return holidays
    rows = list(holidays)
    for r in spec.get("remove", []):
        rows = [h for h in rows
                if not (h["date"] == r["date"]
                        and (not r.get("name") or h["name"] == r["name"]))]
    rows.extend(spec.get("add", []))
    return rows


def _parse(s: str) -> date:
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d))


def normalize(holidays: list[dict], country_code: str) -> list[dict]:
    """归一化假期行。

    1. 按 (date, name) 去重，合并 counties（并集）、types（并集），global 取 OR；
    2. is_national：global=True，或 counties 覆盖该国全部一级行政区
       —— 例如 GB 元旦 global=False 但 counties=[ENG,SCT,WLS,NIR]，属事实上的全国假期。
    返回新增了 counties(去重排序)/is_national 字段的行列表，按日期排序。
    """
    all_subs = set(SUBDIVISIONS.get(country_code, []))
    merged: dict[tuple[str, str], dict] = {}
    for h in holidays:
        key = (h["date"], h["name"])
        counties = set(h.get("counties") or [])
        types = list(h.get("types") or [])
        if key in merged:
            m = merged[key]
            m["counties"] |= counties
            m["types"] = sorted(set(m["types"]) | set(types))
            m["global"] = m["global"] or bool(h.get("global", False))
        else:
            merged[key] = {
                **h,
                "counties": counties,
                "types": sorted(set(types)),
                "global": bool(h.get("global", False)),
            }

    out = []
    for row in merged.values():
        counties = row["counties"]
        covers_all = bool(all_subs) and all_subs <= counties
        row["is_national"] = row["global"] or covers_all
        row["counties"] = sorted(counties)
        out.append(row)
    return sorted(out, key=lambda x: (x["date"], x["name"]))


def analyze(holidays: list[dict], year: int) -> list[dict]:
    """返回长周末块列表（按日期排序）。holidays 需先经 normalize() 处理。"""
    hol_names: dict[date, str] = {}
    for h in holidays:
        if h.get("is_national"):
            hol_names[_parse(h["date"])] = h["name"]

    def is_off(d: date) -> bool:
        return d.weekday() >= 5 or d in hol_names

    # 连续非工作日段（只保留含假期的）
    raw_blocks: list[tuple[date, date, list[str]]] = []
    d = date(year, 1, 1)
    year_end = date(year, 12, 31)
    while d <= year_end:
        if is_off(d):
            start = d
            names: list[str] = []
            while d <= year_end and is_off(d):
                if d in hol_names:
                    names.append(hol_names[d])
                d += timedelta(days=1)
            end = d - timedelta(days=1)
            if names:
                raw_blocks.append((start, end, names))
        else:
            d += timedelta(days=1)

    def extend_side(block_end: date, forward: bool) -> list[dict]:
        """从块端点向外探测拼假选项：请 k 个工作日后是否能接上非工作日。"""
        options = []
        step = timedelta(days=1) if forward else timedelta(days=-1)
        for k in (1, 2, 3):
            probe = block_end
            leave_dates = []
            ok = True
            for _ in range(k):
                probe += step
                if not is_off(probe):
                    leave_dates.append(probe)
                else:
                    ok = False  # 中间夹着非工作日，不需要请假，本就该是同一块
                    break
            if not ok:
                break
            join_day = probe + step
            if is_off(join_day):
                # 计算接上后的连续非工作日长度
                tail = join_day
                tail_len = 0
                while is_off(tail):
                    tail_len += 1
                    tail += step
                options.append({
                    "leave_days": k,
                    "leave_dates": [x.isoformat() for x in sorted(leave_dates)],
                    "extra_days": tail_len,
                })
        return options

    blocks = []
    for start, end, names in raw_blocks:
        after = extend_side(end, forward=True)
        before = extend_side(start, forward=False)
        blocks.append({
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": (end - start).days + 1,
            "start_weekday": WEEKDAY_NAMES[start.weekday()],
            "end_weekday": WEEKDAY_NAMES[end.weekday()],
            "holidays": names,
            "extend_after": after,
            "extend_before": before,
            "best_leave": min(
                [o for side in (after, before) for o in side],
                key=lambda o: (o["leave_days"], -o["extra_days"]),
                default=None,
            ),
        })
    return blocks
