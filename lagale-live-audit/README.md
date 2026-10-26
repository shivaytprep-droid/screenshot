# Lagale Live Site Audit

Crawler for the public live website **https://lagale.in/**. It checks HTTP status, redirects, canonical tags, titles/H1s, sitemap membership and internal links.

## Run locally

```bash
python lagale-live-audit/scripts/live_audit.py --base https://lagale.in/ --max-pages 1600 --delay 0.25 --out reports
```

Generated reports:
- `reports/LIVE-AUDIT-REPORT.md`
- `reports/live-url-audit.csv`
- `reports/internal-links.csv`

## GitHub Actions
Open **Actions → Lagale Live URL Audit → Run workflow**. It also runs weekly (Monday 02:25 UTC) and commits the latest report to `reports/`.

The crawler stays on `lagale.in`, fetches `robots.txt` and `sitemap.xml`, respects disallow rules where they can be read, and applies a delay between requests. Findings are reported only; the script does not modify the production site. Google’s actual index state must still be checked in Search Console.
