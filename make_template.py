"""生成 Notion 模板素材：6 国 2027 拼假优化表（Markdown）+ 原始 CSV。

复用站点同一套算法（long_weekend.analyze），数字与线上一致。
输出到 template/ 目录，不提交进 git（产品素材，与站点代码分离）。

用法：python make_template.py
"""
from __future__ import annotations

import csv
import os
from datetime import date

from build import YEAR, COUNTRIES_FOCUS, country_name, load_holidays, _end_after
from long_weekend import analyze

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "template")
GENERATED = date.today().isoformat()

WEEKDAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def wd(iso: str) -> str:
    return WEEKDAY[date.fromisoformat(iso).weekday()]


def compute(cc: str):
    hs = load_holidays(cc, YEAR)
    blocks = analyze(hs, YEAR)
    deals = []
    for b in blocks:
        o = b.get("best_leave")
        if not o:
            continue
        total = b["days"] + o["leave_days"] + o["extra_days"]
        deals.append({
            "ratio": total / o["leave_days"],
            "total": total,
            "leave_days": o["leave_days"],
            "leave_dates": o["leave_dates"],
            "start": b["start"],
            "end": _end_after(b, o),
            "holidays": b["holidays"],
        })
    deals.sort(key=lambda x: (-x["ratio"], x["leave_days"]))
    natural = [b for b in blocks if b["days"] >= 3]
    return deals, natural, blocks


def country_md(cc: str) -> str:
    deals, natural, blocks = compute(cc)
    name = country_name(cc)
    best = deals[0] if deals else None
    lines = [
        f"# {name} {YEAR} Annual Leave Optimizer",
        "",
        f"> {len(natural)} natural long weekends · {len(deals)} bridge-day plans · "
        + (f"best deal: **{best['total']} days off for {best['leave_days']} day(s) of leave**"
           if best else "no bridge days needed"),
        "",
        "## Best bridge-day deals",
        "",
        "| Book these days off | Leave used | Total days off | Window | Leverage |",
        "| --- | --- | --- | --- | --- |",
    ]
    for d in deals:
        dates = ", ".join(f"{x} ({wd(x)})" for x in d["leave_dates"])
        lines.append(
            f"| {dates} | {d['leave_days']} | {d['total']} | "
            f"{d['start']} → {d['end']} | {d['ratio']:.1f}× |"
        )
    lines += ["", "## Your booking checklist", ""]
    seen = set()
    for d in deals:
        for x in d["leave_dates"]:
            if x not in seen:
                seen.add(x)
                lines.append(f"- [ ] Book off **{x} ({wd(x)})** "
                             f"→ unlocks {d['total']}-day break "
                             f"({d['start']} → {d['end']})")
    lines += [
        "",
        "## All long weekends & holiday blocks",
        "",
        "| Start | End | Days | Type | Holidays |",
        "| --- | --- | --- | --- | --- |",
    ]
    for b in blocks:
        tag = f"{b['days']}-day long weekend" if b["days"] >= 3 else "Mid-week holiday"
        lines.append(f"| {b['start']} | {b['end']} | {b['days']} | {tag} | "
                     + ", ".join(b["holidays"]) + " |")
    lines += [
        "",
        "---",
        "",
        f"Generated {GENERATED} from [Nager.Date](https://date.nager.at) (CC BY 4.0) "
        f"public-holiday data with official-source corrections. "
        f"Live calculator: [holidays-e88.pages.dev](https://holidays-e88.pages.dev). "
        f"Always confirm dates with your employer before booking travel.",
        "",
    ]
    return "\n".join(lines)


def cover_md() -> str:
    lines = [
        f"# {YEAR} Annual Leave Optimizer — 6-Country Pack",
        "",
        "Turn 1–3 days of annual leave into the longest possible breaks. "
        "Every number below is computed by a bridge-day search over the full "
        f"{YEAR} calendar — not copied from a static list.",
        "",
        "| Country | Natural long weekends | Bridge-day plans | Best deal |",
        "| --- | --- | --- | --- |",
    ]
    for cc in COUNTRIES_FOCUS:
        deals, natural, _ = compute(cc)
        best = deals[0] if deals else None
        lines.append(
            f"| {country_name(cc)} | {len(natural)} | {len(deals)} | "
            + (f"{best['total']} days off for {best['leave_days']} leave day(s)"
               if best else "—") + " |"
        )
    lines += [
        "",
        "## What's inside",
        "",
    ]
    for cc in COUNTRIES_FOCUS:
        lines.append(f"- **{country_name(cc)}** — deals table, booking checklist, "
                     f"full {YEAR} holiday-block calendar")
    lines += [
        "- **bridge-days-2027.csv** — the same data, machine-readable, for spreadsheets",
        "",
        "## How to use",
        "",
        "1. Open your country page.",
        "2. Tick the booking checklist as you request each day off.",
        "3. Check the window column to see the full break you unlocked.",
        "",
        f"Data: Nager.Date (CC BY 4.0), generated {GENERATED}. "
        "Live calculator with 12-month visual calendar: "
        "[holidays-e88.pages.dev](https://holidays-e88.pages.dev).",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "00-COVER-6-country-pack.md"), "w", encoding="utf-8") as f:
        f.write(cover_md())
    for i, cc in enumerate(COUNTRIES_FOCUS, 1):
        fn = f"{i:02d}-{country_name(cc).replace(' ', '-')}-{YEAR}-bridge-days.md"
        with open(os.path.join(OUT, fn), "w", encoding="utf-8") as f:
            f.write(country_md(cc))
        print(f"  {fn}")
    with open(os.path.join(OUT, "bridge-days-2027.csv"), "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["country", "book_off_dates", "leave_days", "total_days_off",
                    "window_start", "window_end", "built_around"])
        for cc in COUNTRIES_FOCUS:
            deals, _, _ = compute(cc)
            for d in deals:
                w.writerow([cc, ";".join(d["leave_dates"]), d["leave_days"],
                            d["total"], d["start"], d["end"],
                            "; ".join(d["holidays"])])
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    main()
