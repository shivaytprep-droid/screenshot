#!/usr/bin/env python3
"""Conservative live URL audit for https://lagale.in/ (Python stdlib only)."""
import argparse,csv,datetime as dt,html.parser,re,time,urllib.error,urllib.parse,urllib.request,urllib.robotparser
from collections import deque
from pathlib import Path
UA="LagaleLiveAuditBot/1.0 (+https://github.com/shivaytprep-droid/screenshot)"
SKIP={".jpg",".jpeg",".png",".gif",".webp",".svg",".ico",".pdf",".zip",".gz",".mp4",".mp3",".woff",".woff2",".ttf",".css",".js",".json"}
class Parser(html.parser.HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True); self.links=[]; self.canonical=""; self.title=""; self.h1=""; self.robots=""; self.t=False; self.h=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs); t=tag.lower()
  if t=="a" and a.get("href"): self.links.append((a["href"],a.get("aria-label","")))
  if t=="link" and "canonical" in a.get("rel","").lower(): self.canonical=a.get("href","")
  if t=="meta" and a.get("name","").lower()=="robots": self.robots=a.get("content","")
  if t=="title": self.t=True
  if t=="h1": self.h=True
 def handle_endtag(self,tag):
  if tag.lower()=="title": self.t=False
  if tag.lower()=="h1": self.h=False
 def handle_data(self,data):
  if self.t:self.title+=data
  if self.h:self.h1+=data+" "
def norm(u):
 p=urllib.parse.urlsplit(u)
 if p.scheme.lower() not in ("http","https"):return None
 return urllib.parse.urlunsplit((p.scheme.lower(),p.netloc.lower(),re.sub(r"/{2,}","/",p.path or "/"),p.query,""))
def get(u,timeout):
 req=urllib.request.Request(u,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.5"})
 try:
  with urllib.request.urlopen(req,timeout=timeout) as r:
   b=r.read(3000000); ct=r.headers.get("Content-Type","")
   text=b.decode(r.headers.get_content_charset() or "utf-8",errors="replace") if ("html" in ct.lower() or "xml" in ct.lower() or not ct) else ""
   return r.status,r.geturl(),ct,text,""
 except urllib.error.HTTPError as e:return e.code,e.geturl(),e.headers.get("Content-Type",""),"",str(e)
 except Exception as e:return 0,u,"","",str(e)
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--base",default="https://lagale.in/");ap.add_argument("--max-pages",type=int,default=1600);ap.add_argument("--delay",type=float,default=.25);ap.add_argument("--timeout",type=int,default=18);ap.add_argument("--out",default="reports");a=ap.parse_args()
 base=norm(a.base);host=urllib.parse.urlsplit(base).netloc;scheme=urllib.parse.urlsplit(base).scheme;out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 started=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
 robots_url=f"{scheme}://{host}/robots.txt";rc,_,_,rb,_=get(robots_url,a.timeout);rp=urllib.robotparser.RobotFileParser()
 if rc and rc<400 and rb:rp.parse(rb.splitlines())
 else:rp=None
 smurl=f"{scheme}://{host}/sitemap.xml";sc,_,_,smt,_=get(smurl,a.timeout)
 sm={norm(urllib.parse.urljoin(smurl,re.sub("&amp;","&",x.strip()))) for x in re.findall(r"<loc>\s*(.*?)\s*</loc>",smt,re.I|re.S)} if sc and sc<400 else set()
 q=deque([base]);queued={base};visited=set();rows=[];links=[];disallowed=0
 while q and len(visited)<a.max_pages:
  u=norm(q.popleft())
  if not u or u in visited or urllib.parse.urlsplit(u).netloc!=host:continue
  if rp and not rp.can_fetch(UA,u):disallowed+=1;continue
  visited.add(u);status,final,ct,body,err=get(u,a.timeout)
  row={"url":u,"http_status":status,"final_url":final,"redirected":bool(norm(final) and norm(final)!=u),"content_type":ct,"title":"","h1":"","canonical":"","canonical_matches_final":"","robots_meta":"","internal_links":0,"in_sitemap":u in sm,"error":err}
  if body and "html" in ct.lower():
   p=Parser()
   try:p.feed(body)
   except Exception:pass
   row["title"]=" ".join(p.title.split());row["h1"]=" ".join(p.h1.split());row["canonical"]=urllib.parse.urljoin(final,p.canonical) if p.canonical else "";row["canonical_matches_final"]=bool(row["canonical"] and norm(row["canonical"])==norm(final));row["robots_meta"]=p.robots
   for href,label in p.links:
    target=norm(urllib.parse.urljoin(final,href.strip()))
    if not target or urllib.parse.urlsplit(target).netloc!=host or Path(urllib.parse.urlsplit(target).path).suffix.lower() in SKIP:continue
    row["internal_links"]+=1;links.append({"source":u,"target":target,"anchor_label":label})
    if target not in queued and target not in visited:q.append(target);queued.add(target)
  rows.append(row)
  if a.delay>0:time.sleep(a.delay)
 htmlrows=[r for r in rows if r["http_status"] and r["http_status"]<400 and "html" in r["content_type"].lower()]
 errors=[r for r in rows if r["http_status"]>=400 or r["http_status"]==0];redirects=[r for r in rows if r["redirected"]]
 canonbad=[r for r in htmlrows if r["canonical"] and not r["canonical_matches_final"]];nocanon=[r for r in htmlrows if not r["canonical"]];notitle=[r for r in htmlrows if not r["title"]];noh1=[r for r in htmlrows if not r["h1"]]
 missing=[r for r in rows if r["http_status"] and r["http_status"]<400 and r["url"] not in sm];notcrawled=sorted(x for x in sm if x and x not in visited)
 def writecsv(path,fields,items):
  with (out/path).open("w",newline="",encoding="utf-8-sig") as f:
   w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(items)
 fields=list(rows[0]) if rows else ["url","http_status","final_url","redirected","content_type","title","h1","canonical","canonical_matches_final","robots_meta","internal_links","in_sitemap","error"]
 writecsv("live-url-audit.csv",fields,rows);writecsv("internal-links.csv",["source","target","anchor_label"],links);writecsv("sitemap-not-crawled.csv",["url"],[{"url":u} for u in notcrawled])
 md=out/"LIVE-AUDIT-REPORT.md"
 with md.open("w",encoding="utf-8") as f:
  f.write(f"# Lagale Live Website Audit\n\n- Started: {started}\n- Base: {base}\n- robots.txt HTTP: {rc}\n- sitemap.xml HTTP: {sc}\n- Sitemap URLs parsed: {len(sm)}\n- URLs crawled: {len(rows)} (limit {a.max_pages})\n- Successful HTML pages: {len(htmlrows)}\n- Internal links recorded: {len(links)}\n- robots-disallowed candidates skipped: {disallowed}\n\n## Summary\n\n| Check | Count |\n|---|---:|\n| HTTP errors/request failures | {len(errors)} |\n| Redirecting URLs | {len(redirects)} |\n| Canonical review candidates | {len(canonbad)} |\n| HTML without canonical | {len(nocanon)} |\n| HTML without title | {len(notitle)} |\n| HTML without H1 | {len(noh1)} |\n| Successful crawled URLs absent from sitemap | {len(missing)} |\n| Sitemap URLs not reached in crawl | {len(notcrawled)} |\n\n")
  def section(name,items,keys):
   f.write(f"## {name}\n\n")
   if not items:f.write("No findings.\n\n");return
   f.write("| "+" | ".join(keys)+" |\n|"+"|".join(["---"]*len(keys))+"|\n")
   for x in items[:200]:f.write("| "+" | ".join(str(x.get(k,"")).replace("|","\\|").replace("\n"," ")[:240] for k in keys)+" |\n")
   if len(items)>200:f.write(f"\n_First 200 of {len(items)} findings shown._\n")
   f.write("\n")
  section("HTTP errors / request failures",errors,["http_status","url","final_url","error"]);section("Redirects",redirects,["url","http_status","final_url"]);section("Canonical review candidates",canonbad,["url","canonical","final_url"]);section("Successful URLs absent from sitemap",missing,["http_status","url"]);section("Sitemap URLs not reached during crawl",[{"url":u} for u in notcrawled],["url"])
  f.write("\n## Caveats\n\n- This is a point-in-time crawl; rate limits, bot restrictions and transient network errors can affect results.\n- Sitemap URLs not reached are not automatically broken; they may not be internally linked, may be disallowed by robots.txt, or may fall beyond the crawl limit.\n- Canonical differences are review candidates, not automatic failures.\n- Google indexing status must be checked in Search Console.\n")
 print(f"CRAWLED={len(rows)} SITEMAP={len(sm)} ERRORS={len(errors)} REDIRECTS={len(redirects)}")
 print(f"REPORT={md} CSV={out/'live-url-audit.csv'}")
if __name__=="__main__":main()
