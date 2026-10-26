#!/usr/bin/env python3
"""Crawl the live Lagale site and produce CSV + Markdown audit reports.

Uses only Python standard library. Conservative crawl: same-host links only,
robots.txt disallow rules are respected, and a delay is applied between requests.
"""
from __future__ import annotations
import argparse, csv, datetime as dt, html.parser, re, time, urllib.error, urllib.parse, urllib.request, urllib.robotparser
from collections import deque
from pathlib import Path

UA = "LagaleLiveAuditBot/1.0 (+https://github.com/shivaytprep-droid/lagale-live-site-audit)"
SKIP_EXT = {".jpg",".jpeg",".png",".gif",".webp",".svg",".ico",".pdf",".zip",".gz",".mp4",".mp3",".woff",".woff2",".ttf",".css",".js",".json",".xml"}
class Parser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.links=[]; self.canonical=""; self.title=""; self._title=False; self.robots=""; self.h1=[]; self._h1=0
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag.lower()=="a" and a.get("href"): self.links.append((a["href"],a.get("rel",""),a.get("aria-label","")))
        if tag.lower()=="link" and "canonical" in a.get("rel","").lower(): self.canonical=a.get("href","")
        if tag.lower()=="meta" and a.get("name","").lower()=="robots": self.robots=a.get("content","")
        if tag.lower()=="title": self._title=True
        if tag.lower()=="h1": self._h1+=1
    def handle_endtag(self, tag):
        if tag.lower()=="title": self._title=False
        if tag.lower()=="h1" and self._h1: self._h1-=1
    def handle_data(self, data):
        if self._title: self.title += data
        if self._h1: self.h1.append(data.strip())

def norm_url(url):
    u=urllib.parse.urlsplit(url)
    if u.scheme.lower() not in ("http","https"): return None
    path=re.sub(r"/{2,}","/",u.path or "/")
    return urllib.parse.urlunsplit((u.scheme.lower(),u.netloc.lower(),path,u.query,""))

def fetch(url, timeout=18):
    req=urllib.request.Request(url, headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.5"})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            data=r.read(3_000_000)
            ctype=r.headers.get("Content-Type","")
            enc=r.headers.get_content_charset() or "utf-8"
            text=data.decode(enc,errors="replace") if ("html" in ctype.lower() or "xml" in ctype.lower() or not ctype) else ""
            return r.status,r.geturl(),ctype,text,""
    except urllib.error.HTTPError as e:
        return e.code,e.geturl(),e.headers.get("Content-Type",""),"",str(e)
    except Exception as e:
        return 0,url,"","",str(e)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--base",default="https://lagale.in/")
    ap.add_argument("--max-pages",type=int,default=1600)
    ap.add_argument("--delay",type=float,default=0.25)
    ap.add_argument("--timeout",type=int,default=18)
    ap.add_argument("--out",default="reports")
    args=ap.parse_args()
    base=norm_url(args.base)
    host=urllib.parse.urlsplit(base).netloc
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    robots=urllib.robotparser.RobotFileParser()
    robots_url=f"{urllib.parse.urlsplit(base).scheme}://{host}/robots.txt"
    code,final,ctype,body,err=fetch(robots_url,args.timeout)
    robots_text=body
    if code and code<400 and body:
        robots.parse(body.splitlines())
    else:
        # Fail conservatively if robots file cannot be read: continue public-page audit,
        # but note that robots policy could not be verified.
        robots=None

    q=deque([base]); seen=set(); rows=[]; link_rows=[]; sitemap_urls=[]; skipped_robots=0
    sitemap_url=f"{urllib.parse.urlsplit(base).scheme}://{host}/sitemap.xml"
    sc, sf, sct, stxt, serr=fetch(sitemap_url,args.timeout)
    if sc and sc<400 and stxt:
        sitemap_urls=re.findall(r"<loc>\\s*(.*?)\\s*</loc>",stxt,re.I|re.S)
        sitemap_urls=[urllib.parse.urljoin(sitemap_url,re.sub(r"&amp;","&",x.strip())) for x in sitemap_urls]
    sitemap_set=set(map(norm_url,sitemap_urls))
    while q and len(seen)<args.max_pages:
        url=norm_url(q.popleft())
        if not url or url in seen: continue
        if urllib.parse.urlsplit(url).netloc != host: continue
        if robots and not robots.can_fetch(UA,url):
            skipped_robots+=1; continue
        seen.add(url)
        status,final_url,ctype,body,error=fetch(url,args.timeout)
        final_norm=norm_url(final_url)
        row={"url":url,"status":status,"final_url":final_url,"redirected":bool(final_norm and final_norm!=url),"content_type":ctype,"title":"","canonical":"","canonical_ok":"","robots_meta":"","h1":"","internal_links":0,"broken_internal_links":0,"in_sitemap":url in sitemap_set,"error":error}
        p=Parser()
        if body and "html" in ctype.lower():
            try: p.feed(body)
            except Exception: pass
            row["title"]=" ".join(p.title.split())
            row["canonical"]=urllib.parse.urljoin(final_url,p.canonical) if p.canonical else ""
            row["canonical_ok"]=(norm_url(row["canonical"])==norm_url(final_url)) if row["canonical"] else False
            row["robots_meta"]=p.robots
            row["h1"]=" ".join(" ".join(p.h1).split())
            for href,rel,aria in p.links:
                resolved=norm_url(urllib.parse.urljoin(final_url,href.strip()))
                if not resolved: continue
                if urllib.parse.urlsplit(resolved).netloc==host and urllib.parse.urlsplit(resolved).path.lower().rsplit(".",1)[-1] not in {x.lstrip(".") for x in SKIP_EXT}:
                    row["internal_links"]+=1
                    link_rows.append({"source":url,"target":resolved,"anchor_label":aria,"rel":rel})
                    if resolved not in seen and resolved not in q: q.append(resolved)
        rows.append(row)
        if args.delay: time.sleep(max(0,args.delay))
    # Link integrity can be matched after crawl.
    status_map={r["url"]:r["status"] for r in rows}
    status_map.update({norm_url(r["final_url"]):r["status"] for r in rows if r["final_url"]})
    for r in rows:
        broken=0
        for lr in link_rows:
            if lr["source"]==r["url"] and lr["target"] in status_map and (status_map[lr["target"]]>=400 or status_map[lr["target"]]==0): broken+=1
        r["broken_internal_links"]=broken
    csv_path=out/"live-url-audit.csv"
    fields=list(rows[0].keys()) if rows else ["url","status","final_url","redirected","content_type","title","canonical","canonical_ok","robots_meta","h1","internal_links","broken_internal_links","in_sitemap","error"]
    with csv_path.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    with (out/"internal-links.csv").open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=["source","target","anchor_label","rel"]); w.writeheader(); w.writerows(link_rows)
    missing=[r for r in rows if r["url"] not in sitemap_set and r["status"] and r["status"]<400]
    sitemap_not_crawled=[u for u in sitemap_set if u not in seen]
    errors=[r for r in rows if r["status"]>=400 or r["status"]==0]
    redirects=[r for r in rows if r["redirected"]]
    canon_bad=[r for r in rows if r["status"]<400 and r["content_type"] and "html" in r["content_type"].lower() and r["canonical"] and not r["canonical_ok"]]
    no_canon=[r for r in rows if r["status"]<400 and r["content_type"] and "html" in r["content_type"].lower() and not r["canonical"]]
    no_title=[r for r in rows if r["status"]<400 and r["content_type"] and "html" in r["content_type"].lower() and not r["title"]]
    no_h1=[r for r in rows if r["status"]<400 and r["content_type"] and "html" in r["content_type"].lower() and not r["h1"]]
    md=out/"LIVE-AUDIT-REPORT.md"
    with md.open("w",encoding="utf-8") as f:
        f.write(f"# Lagale live website audit\n\n- Started: {stamp}\n- Base URL: {base}\n- Host: {host}\n- robots.txt: HTTP {code if code else 'unavailable'} ({robots_url})\n- Sitemap: HTTP {sc if sc else 'unavailable'} ({sitemap_url})\n- Sitemap URLs parsed: {len(sitemap_set)}\n- Crawled URLs: {len(rows)} (limit {args.max_pages})\n- Internal links recorded: {len(link_rows)}\n- robots-disallowed candidates skipped: {skipped_robots}\n\n## Summary\n\n| Check | Count |\n|---|---:|\n| HTTP errors / request failures | {len(errors)} |\n| Redirecting URLs | {len(redirects)} |\n| HTML canonical points elsewhere / mismatch | {len(canon_bad)} |\n| HTML without canonical | {len(no_canon)} |\n| HTML without title | {len(no_title)} |\n| HTML without H1 | {len(no_h1)} |\n| Crawlable successful URLs not listed in sitemap | {len(missing)} |\n| Sitemap URLs not reached during crawl | {len(sitemap_not_crawled)} |\n\n")
        def section(name,items,fmt):
            f.write(f"## {name}\n\n")
            if not items: f.write("No findings.\n\n"); return
            f.write("| " + " | ".join(fmt) + " |\n|"+ "|".join(["---"]*len(fmt))+"|\n")
            for x in items[:250]:
                f.write("| "+" | ".join(str(x.get(k,"")).replace("|","\\|").replace("\n"," ")[:300] for k in fmt)+" |\n")
            if len(items)>250:f.write(f"\n_Showing first 250 of {len(items)}._\n")
            f.write("\n")
        section("HTTP errors / failures",errors,["status","url","final_url","error"])
        section("Redirects",redirects,["url","status","final_url"])
        section("Canonical mismatches",canon_bad,["url","canonical","final_url"])
        section("Successful URLs missing from sitemap",missing,["status","url"])
        section("Sitemap URLs not reached during crawl", [{"url":u} for u in sorted(sitemap_not_crawled)],["url"])
        f.write("\n## Interpretation notes\n\n- This is a point-in-time crawl from the runner; bot restrictions, transient network errors, or rate limits may affect results.\n- Sitemap URLs not reached may be outside internal navigation, blocked by robots.txt, queued beyond the page limit, or non-HTML resources. Inspect before treating them as failures.\n- A canonical mismatch is a review candidate, not automatically an error: alternate URLs may intentionally canonicalize to a preferred URL.\n- Sitemap inclusion does not guarantee Google indexing. Use Search Console for Google’s actual indexing state.\n")
    print(f"REPORT={md}")
    print(f"CSV={csv_path}")
    print(f"CRAWLED={len(rows)} ERRORS={len(errors)} REDIRECTS={len(redirects)} SITEMAP={len(sitemap_set)}")
if __name__=="__main__": main()
