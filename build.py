"""静态站点生成器：年假优化器（Annual Leave Optimizer）。

读取 data/ 的假期 JSON，归一化（见 long_weekend.normalize）后输出纯静态 HTML 到 out/。
零第三方依赖。当前规模：2 国 × 2027 = 4 页 + 首页。

页面：
  /                                  落地页（含邮件订阅）
  /holidays/{cc}/2027/               年度假期总表（全国 + 地方，标注适用地区）
  /long-weekends/{cc}/2027/          年假优化页（拼假榜 + 12 个月可视化日历）

用法：
    python build.py
    python build.py --site-url https://your-domain.com
"""
from __future__ import annotations

import argparse
import html
import json
import os
from datetime import date
from typing import Any

from long_weekend import analyze, normalize, apply_corrections

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
OUT_DIR = os.path.join(HERE, "out")

YEAR = 2027
COUNTRIES_FOCUS = ["US", "GB"]

WEEKDAY_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTH_NAMES = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"]

# 一级行政区代码 → 可读名称（与 data/subdivisions.json 对应，仅当前 2 国需要时使用）
REGION_NAMES: dict[str, str] = {
    "GB-ENG": "England", "GB-SCT": "Scotland", "GB-WLS": "Wales",
    "GB-NIR": "Northern Ireland",
    "US-AL": "Alabama", "US-AK": "Alaska", "US-AZ": "Arizona", "US-AR": "Arkansas",
    "US-CA": "California", "US-CO": "Colorado", "US-CT": "Connecticut",
    "US-DE": "Delaware", "US-FL": "Florida", "US-GA": "Georgia", "US-HI": "Hawaii",
    "US-ID": "Idaho", "US-IL": "Illinois", "US-IN": "Indiana", "US-IA": "Iowa",
    "US-KS": "Kansas", "US-KY": "Kentucky", "US-LA": "Louisiana", "US-ME": "Maine",
    "US-MD": "Maryland", "US-MA": "Massachusetts", "US-MI": "Michigan",
    "US-MN": "Minnesota", "US-MS": "Mississippi", "US-MO": "Missouri",
    "US-MT": "Montana", "US-NE": "Nebraska", "US-NV": "Nevada",
    "US-NH": "New Hampshire", "US-NJ": "New Jersey", "US-NM": "New Mexico",
    "US-NY": "New York", "US-NC": "North Carolina", "US-ND": "North Dakota",
    "US-OH": "Ohio", "US-OK": "Oklahoma", "US-OR": "Oregon",
    "US-PA": "Pennsylvania", "US-RI": "Rhode Island", "US-SC": "South Carolina",
    "US-SD": "South Dakota", "US-TN": "Tennessee", "US-TX": "Texas",
    "US-UT": "Utah", "US-VT": "Vermont", "US-VA": "Virginia", "US-WA": "Washington",
    "US-WV": "West Virginia", "US-WI": "Wisconsin", "US-WY": "Wyoming",
    "US-DC": "District of Columbia",
}


# ---------------- 工具 ----------------

def esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


def load_raw(cc: str, year: int) -> list[dict]:
    fn = os.path.join(DATA_DIR, f"holidays_{cc}_{year}.json")
    return json.load(open(fn, encoding="utf-8"))


def load_holidays(cc: str, year: int) -> list[dict]:
    """原始数据 → 官方校正 → 归一化。"""
    return normalize(apply_corrections(load_raw(cc, year), cc, year), cc)


def country_name(cc: str) -> str:
    for c in json.load(open(os.path.join(DATA_DIR, "countries.json"), encoding="utf-8")):
        if c["code"] == cc:
            return c["name"]
    return cc


def region_label(code: str) -> str:
    return REGION_NAMES.get(code, code)


# ---------------- HTML 外壳 ----------------

class Site:
    def __init__(self, site_url: str) -> None:
        self.site_url = site_url.rstrip("/")

    def page(self, *, title: str, desc: str, path: str, body: str,
             breadcrumb: str = "", jsonld: list[dict] | None = None) -> str:
        canonical = self.site_url + path
        ld_html = "\n".join(
            f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>'
            for x in (jsonld or [])
        )
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:type" content="website">
<meta name="msvalidate.01" content="93A3EF00926398559313DCA649D512A2">
<link rel="stylesheet" href="/assets/style.css">
{ld_html}
</head>
<body>
<header class="site"><div class="inner">
<a class="logo" href="/">Annual Leave Optimizer</a>
<nav><a href="/#countries">Countries</a><a href="/#newsletter">Newsletter</a></nav>
</div></header>
<div class="container">
{breadcrumb}
{body}
</div>
<footer class="site">
Data: <a href="https://date.nager.at" style="color:inherit">Nager.Date</a> (CC BY) ·
Regional scope is shown on every holiday ·
This site has no affiliation with any government.
</footer>
</body>
</html>
"""

    def crumb(self, items: list[tuple[str, str]]) -> str:
        parts = ['<nav class="breadcrumb"><a href="/">Home</a>']
        for label, url in items:
            parts.append(f' &rsaquo; <a href="{url}">{esc(label)}</a>')
        parts.append("</nav>")
        return "".join(parts)


def breadcrumb_jsonld(items: list[tuple[str, str]], site_url: str) -> dict:
    """items: (label, path or None). 最后一项为当前页（path=None）。"""
    nodes = [{"name": "Home", "url": site_url + "/"}]
    for label, path in items:
        nodes.append({"name": label} if path is None
                     else {"name": label, "url": site_url + path})
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "item": n}
            for i, n in enumerate(nodes)
        ],
    }


def write_file(rel_path: str, content: str) -> None:
    full = os.path.join(OUT_DIR, rel_path.lstrip("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)


# ---------------- 落地页 ----------------

def newsletter_box(cta: str = "Get reminded") -> str:
    action = os.environ.get("EMAIL_FORM_ACTION", "https://formsubmit.co/376384019@qq.com")
    return f"""
<form class="newsletter" id="newsletter" method="post" action="{esc(action)}">
<input type="hidden" name="_subject" value="Newsletter subscription">
<input type="hidden" name="_captcha" value="false">
<input type="email" name="email" placeholder="you@example.com" required aria-label="Email address">
<button type="submit">{esc(cta)}</button>
</form>
<p class="cc">One email when a new country guide or {YEAR + 1} dates land. Unsubscribe anytime.</p>
"""


def build_home(site: Site) -> list[str]:
    cards = []
    stats = []
    for cc in COUNTRIES_FOCUS:
        name = country_name(cc)
        hs = load_holidays(cc, YEAR)
        blocks = analyze(hs, YEAR)
        best = max(
            ((b["days"] + b["best_leave"]["leave_days"] + b["best_leave"]["extra_days"],
              b["best_leave"]["leave_days"])
             for b in blocks if b["best_leave"]),
            default=(0, 0),
        )
        cards.append(
            f'<a class="card" href="/long-weekends/{cc.lower()}/{YEAR}/">'
            f'<strong>{esc(name)}</strong> <span class="cc">({cc})</span>'
            f'<div class="cc">Best {YEAR} deal: take {best[1]} day(s) off, '
            f'get {best[0]} consecutive days</div>'
            f'<div class="cc"><a href="/holidays/{cc.lower()}/{YEAR}/">'
            f'Full {YEAR} holiday list</a></div></a>'
        )
        stats.append(best)
    headline_days = max((s[0] for s in stats), default=0)

    body = f"""
<h1>Stop wasting your annual leave</h1>
<p class="lead">Most people take holidays one at a time. A few bridge days &mdash; the single weekdays sandwiched between a weekend and a public holiday &mdash; can turn <strong>1 day of leave into 7 days off</strong>. This site calculates the exact days to book in {YEAR}. Best deal this year: up to <strong>{headline_days} consecutive days</strong>.</p>
<h2 id="countries">{YEAR} guides</h2>
<div class="grid">{''.join(cards)}</div>
<div class="card">
<h2 style="margin-top:0">What this site does differently</h2>
<ul>
<li><strong>Calculates, not lists.</strong> Every plan is the output of a bridge-day search across the full calendar &mdash; not something you want to compute by hand.</li>
<li><strong>Shows scope honestly.</strong> National holidays and regional days (Scotland vs England, US state holidays) are labeled separately.</li>
<li><strong>One calendar view.</strong> Weekends, holidays and the days to book off are color-coded across all 12 months.</li>
</ul>
</div>
<h2>Know when next year's dates drop</h2>
{newsletter_box()}
"""
    desc = (f"Annual leave optimizer for {YEAR}: exact bridge days to book so 1-3 days of "
            f"leave become up to {headline_days} consecutive days off. US and UK guides.")
    write_file("index.html", site.page(
        title=f"Annual Leave Optimizer {YEAR} - Bridge Days Calculator",
        desc=desc, path="/", body=body,
        jsonld=[{
            "@context": "https://schema.org",
            "@type": "WebApplication",
            "name": "Annual Leave Optimizer",
            "applicationCategory": "TravelApplication",
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        }],
    ))
    return ["/"]


# ---------------- 年度总表 ----------------

def build_year_table(site: Site, cc: str, hs: list[dict]) -> str:
    name = country_name(cc)
    national = [h for h in hs if h["is_national"]]
    regional = [h for h in hs if not h["is_national"]]

    rows = []
    for h in hs:
        y, m, d = (int(x) for x in h["date"].split("-"))
        wd = WEEKDAY_SHORT[date(y, m, d).weekday()]
        if h["is_national"]:
            scope = '<span class="badge free">National</span>'
        else:
            where = ", ".join(region_label(c) for c in h["counties"]) or "Some regions"
            scope = f'<span class="badge public">Regional</span> <span class="cc">{esc(where)}</span>'
        types = ", ".join(h.get("types") or [])
        rows.append(
            f"<tr><td>{h['date']}</td><td>{wd}</td>"
            f"<td>{esc(h['name'])}</td><td>{scope}</td>"
            f"<td class=\"cc\">{esc(types)}</td></tr>"
        )

    blocks = analyze(hs, YEAR)
    max_break = max(
        (b["days"] + b["best_leave"]["leave_days"] + b["best_leave"]["extra_days"]
         for b in blocks if b["best_leave"]),
        default=0,
    )
    crumb = site.crumb([(name, None)])
    body = f"""
<h1>Public Holidays in {esc(name)} {YEAR}</h1>
<p class="lead">{len(national)} national holidays{' and ' + str(len(regional)) + ' regional days' if regional else ''} · up to {max_break} consecutive days with bridge days</p>
<p><a class="badge free" href="/long-weekends/{cc.lower()}/{YEAR}/" style="text-decoration:none">
&#9873; {YEAR} annual leave optimizer &amp; calendar</a></p>
<table>
<thead><tr><th>Date</th><th>Day</th><th>Holiday</th><th>Scope</th><th>Type</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
<p class="cc">Scope is derived from official subdivision coverage. Always confirm with your employer before booking travel.</p>
"""
    path = f"/holidays/{cc.lower()}/{YEAR}/"
    desc = (f"All {YEAR} public holidays in {name} with dates, weekdays and regional scope "
            f"({len(regional)} regional days listed), plus link to the bridge-day optimizer.")
    write_file(f"holidays/{cc.lower()}/{YEAR}/index.html", site.page(
        title=f"Public Holidays in {name} {YEAR} - Dates & Scope",
        desc=desc, path=path, body=body, breadcrumb=crumb,
        jsonld=[breadcrumb_jsonld([(name, None)], site.site_url),
                {"@context": "https://schema.org", "@type": "Table",
                 "about": f"Public holidays in {name}, {YEAR}"}],
    ))
    return path


# ---------------- 年假优化页 ----------------

def render_month(year: int, month: int, hol_map: dict[date, str],
                 bridge: dict[date, str]) -> str:
    first = date(year, month, 1)
    cells = ['<td class="cal-empty"></td>'] * first.weekday()
    last_day = 31
    while True:
        try:
            date(year, month, last_day)
            break
        except ValueError:
            last_day -= 1
    for day in range(1, last_day + 1):
        d = date(year, month, day)
        cls, title = "", []
        if d in hol_map:
            cls = "cal-hol"
            title.append(hol_map[d])
        elif d.weekday() >= 5:
            cls = "cal-we"
        if d in bridge:
            cls = "cal-bridge"
            title.append(f"Book this day off ({bridge[d]})")
        cells.append(
            f'<td class="{cls}" title="{esc(" · ".join(title))}">{day}</td>'
        )
    while len(cells) % 7 != 0:
        cells.append('<td class="cal-empty"></td>')
    return f"""
<div class="cal">
<div class="cal-title">{MONTH_NAMES[month - 1]}</div>
<table class="cal-grid"><thead><tr>
<th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th><th>Fri</th><th>Sat</th><th>Sun</th>
</tr></thead><tbody>
{''.join(f'<tr>{"".join(cells[i:i+7])}</tr>' for i in range(0, len(cells), 7))}
</tbody></table>
</div>
"""


def build_optimizer(site: Site, cc: str, hs: list[dict]) -> str:
    name = country_name(cc)
    blocks = analyze(hs, YEAR)

    # 拼假榜：按 总天数/请假天数 的杠杆比排序
    deals = []
    bridge: dict[date, str] = {}
    hol_map: dict[date, str] = {}
    for h in hs:
        if h["is_national"]:
            hol_map[date.fromisoformat(h["date"])] = h["name"]

    for b in blocks:
        o = b["best_leave"]
        if not o:
            continue
        total = b["days"] + o["leave_days"] + o["extra_days"]
        ratio = total / o["leave_days"]
        deals.append((ratio, total, b, o))
    deals.sort(key=lambda x: (-x[0], x[3]["leave_days"]))

    deal_cards = []
    for ratio, total, b, o in deals:
        dates = ", ".join(o["leave_dates"])
        label = f"{total} days off for {o['leave_days']} day(s) of leave"
        deal_cards.append(f"""
<div class="card deal">
<div class="deal-head"><span class="deal-ratio">{ratio:g}&times;</span>
<strong>{total} consecutive days</strong> for just {o['leave_days']} day(s) of leave</div>
<p class="cc" style="margin:6px 0">Book off: <strong>{esc(dates)}</strong> ·
Window: {b['start']} &ndash; {_end_after(b, o)}</p>
<p class="cc" style="margin:0">Built around: {esc(', '.join(b['holidays']))}</p>
</div>
""")
        for ds in o["leave_dates"]:
            bridge[date.fromisoformat(ds)] = label

    # 全部块（含无需请假的自然长周末）
    block_rows = []
    for b in blocks:
        tag = (f'{b["days"]}-day long weekend' if b["days"] >= 3
               else 'Mid-week holiday')
        block_rows.append(
            f"<tr><td>{b['start']}</td><td>{b['end']}</td><td>{b['days']}</td>"
            f"<td>{esc(', '.join(b['holidays']))}</td>"
            f"<td class=\"cc\">{esc(tag)}</td></tr>"
        )

    natural = sum(1 for b in blocks if b["days"] >= 3)
    best = deals[0] if deals else None
    faq = [
        (f"How many long weekends does {name} have in {YEAR}?",
         f"There are {natural} natural long weekends of 3 days or more in {name} in {YEAR}, requiring no annual leave."),
    ]
    if best:
        ratio, total, b, o = best
        faq.append(
            (f"What is the best bridge-day deal in {name} in {YEAR}?",
             f"Book off {', '.join(o['leave_dates'])} ({o['leave_days']} day(s) of leave) "
             f"to get {total} consecutive days off around {b['holidays'][0]}."),
        )

    months = "".join(render_month(YEAR, m, hol_map, bridge) for m in range(1, 13))
    crumb = site.crumb([(name, f"/holidays/{cc.lower()}/{YEAR}/")])
    body = f"""
<h1>{esc(name)} Annual Leave Optimizer {YEAR}</h1>
<p class="lead">{natural} natural long weekends · {len(deals)} bridge-day plans ·
{'best deal: ' + str(best[1]) + ' days off for ' + str(best[3]['leave_days']) + ' day(s) of leave' if best else 'no bridge days needed this year'}</p>
<h2>Best bridge-day deals</h2>
{''.join(deal_cards) if deal_cards else '<p class="lead">Every national holiday already lands on or next to a weekend.</p>'}
<h2>12-month calendar</h2>
<div class="legend">
<span class="sw sw-hol"></span> Public holiday
<span class="sw sw-bridge"></span> Book this day off
<span class="sw sw-we"></span> Weekend
</div>
<div class="cal-grid-wrap">{months}</div>
<h2>All holiday blocks</h2>
<table>
<thead><tr><th>From</th><th>To</th><th>Days</th><th>Holidays</th><th></th></tr></thead>
<tbody>{''.join(block_rows)}</tbody>
</table>
<p><a href="/holidays/{cc.lower()}/{YEAR}/">&larr; Full {YEAR} holiday list for {esc(name)}</a></p>
"""
    path = f"/long-weekends/{cc.lower()}/{YEAR}/"
    desc = (f"{name} {YEAR} bridge-day calculator: {len(deals)} calculated plans, best is "
            f"{best[1] if best else 0} consecutive days off. Calendar marks exact days to book.")
    write_file(f"long-weekends/{cc.lower()}/{YEAR}/index.html", site.page(
        title=f"{name} {YEAR} Annual Leave Optimizer - Bridge Days",
        desc=desc, path=path, body=body, breadcrumb=crumb,
        jsonld=[breadcrumb_jsonld(
            [(name, f"/holidays/{cc.lower()}/{YEAR}/"),
             (f"Optimizer {YEAR}", None)],
            site.site_url),
            {"@context": "https://schema.org", "@type": "FAQPage",
             "mainEntity": [
                 {"@type": "Question", "name": q,
                  "acceptedAnswer": {"@type": "Answer", "text": a}}
                 for q, a in faq]}],
    ))
    return path


def _end_after(b: dict, o: dict) -> str:
    """拼假窗口结束日：块尾 + 请假天数 + 多接的非工作日。"""
    from datetime import timedelta
    end = date.fromisoformat(b["end"]) + timedelta(days=o["leave_days"] + o["extra_days"])
    return end.isoformat()


# ---------------- 主流程 ----------------

def copy_assets() -> None:
    import shutil
    dst = os.path.join(OUT_DIR, "assets")
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(os.path.join(HERE, "assets"), dst)
    # Cloudflare Pages 头文件（缓存策略）
    headers_src = os.path.join(HERE, "_headers")
    if os.path.exists(headers_src):
        shutil.copy(headers_src, os.path.join(OUT_DIR, "_headers"))


def main() -> None:
    ap = argparse.ArgumentParser()
    # NOTE: CF_PAGES_URL is intentionally ignored — it carries a per-deploy
    # hash prefix (e.g. https://078c5871.holidays-e88.pages.dev) which would
    # make sitemap URLs unstable across deployments. Prefer the explicit
    # SITE_URL env var (set in Cloudflare Pages if the production domain
    # changes), otherwise fall back to the stable production domain.
    default_url = os.environ.get("SITE_URL") or "https://holidays-e88.pages.dev"
    ap.add_argument("--site-url", default=default_url)
    args = ap.parse_args()
    site = Site(args.site_url)

    os.makedirs(OUT_DIR, exist_ok=True)
    copy_assets()

    all_paths = build_home(site)
    for cc in COUNTRIES_FOCUS:
        hs = load_holidays(cc, YEAR)
        all_paths.append(build_year_table(site, cc, hs))
        all_paths.append(build_optimizer(site, cc, hs))

    urls = "\n".join(
        f"  <url><loc>{args.site_url.rstrip('/')}{p}</loc></url>" for p in all_paths
    )
    write_file("sitemap.xml",
               f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n')
    write_file("robots.txt",
               f"User-agent: *\nAllow: /\nSitemap: {args.site_url.rstrip('/')}/sitemap.xml\n")

    print(f"OK {len(all_paths)} pages -> {OUT_DIR}")


if __name__ == "__main__":
    main()
