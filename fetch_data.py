"""抓取 Nager.Date 公共假期数据，存成本地 JSON。

零依赖（urllib）。数据缓存到 data/，构建时直接读本地文件。

用法：
    python fetch_data.py              # 默认 3 国 3 年
    python fetch_data.py --all        # 全部 110+ 国家
    python fetch_data.py --countries US,GB,DE --years 2025,2026,2027,2028
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

API_BASE = "https://date.nager.at/api/v3"
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")

DEFAULT_COUNTRIES = ["US", "GB"]
DEFAULT_YEARS = [2025, 2026, 2027]


def _get(url: str, retries: int = 3) -> list | dict:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            time.sleep(1 + attempt * 2)
    raise RuntimeError(f"请求失败 {url}: {last_err}")


def fetch_countries() -> list[dict]:
    """国家代码 -> 英文名映射。"""
    rows = _get(f"{API_BASE}/AvailableCountries")
    countries = [{"code": r["countryCode"], "name": r["name"]} for r in rows]
    with open(os.path.join(DATA_DIR, "countries.json"), "w", encoding="utf-8") as f:
        json.dump(countries, f, ensure_ascii=False, indent=1)
    return countries


def fetch_holidays(country: str, year: int) -> list[dict]:
    path = os.path.join(DATA_DIR, f"holidays_{country}_{year}.json")
    rows = _get(f"{API_BASE}/PublicHolidays/{year}/{country}")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--countries", default="")
    ap.add_argument("--years", default="")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    countries = fetch_countries()
    print(f"国家列表：{len(countries)} 个", flush=True)

    if args.all:
        codes = [c["code"] for c in countries]
    elif args.countries:
        codes = [c.strip().upper() for c in args.countries.split(",") if c.strip()]
    else:
        codes = DEFAULT_COUNTRIES

    years = (
        [int(y) for y in args.years.split(",") if y.strip()]
        if args.years
        else DEFAULT_YEARS
    )

    ok = 0
    for code in codes:
        for year in years:
            try:
                rows = fetch_holidays(code, year)
                print(f"  {code} {year}: {len(rows)} 个假期", flush=True)
                ok += 1
            except RuntimeError as e:
                print(f"  {code} {year}: 失败 {e}", flush=True)

    print(f"完成 {ok}/{len(codes) * len(years)}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
