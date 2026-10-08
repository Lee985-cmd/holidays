# Holidays — Annual Leave Optimizer

A static site that helps travelers and remote workers combine public holidays with annual leave to plan longer breaks.

🌐 **Live site:** <https://holidays-e88.pages.dev>

## What's inside

- **Annual holiday tables** — public holidays per country/year, sourced from [Nager.Date](https://date.nager.at/) (CC BY 4.0)
- **Leave optimizer pages** — visualizations showing how to turn a few days of leave into a long break (e.g. "3 days off → 11 days total")
- **Email subscription** — updates when new optimization plans are published

## Stack

- Zero third-party runtime dependencies — pure Python static generator (`build.py`)
- Mobile-first CSS, server-rendered HTML
- Deployed on Cloudflare Pages (free tier)

## Project layout

```
fetch_data.py      # Scrape + normalize holiday data from Nager.Date
long_weekend.py    # Long weekend / leave-combining algorithm
build.py           # Static site generator
style.css          # Mobile-adapted styles
out/               # Build output (gitignored)
```

## Build

```bash
python build.py
```

Output lands in `out/`. Serve any way you like, or connect this repo to Cloudflare Pages with:

- **Build command:** `python build.py`
- **Output directory:** `out`

## Links

- Live site: <https://holidays-e88.pages.dev>
- Sitemap: <https://holidays-e88.pages.dev/sitemap.xml>
- Data source: <https://date.nager.at/> (CC BY 4.0)
