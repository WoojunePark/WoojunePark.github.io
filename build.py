"""Render data/cv.json into a static site (_site/) and a dated PDF CV.

Python standard library only. The data file is exported from the private career wiki by
`final-offer site export`; edit content there, not here. This repository owns layout and style.

    python build.py            # HTML only
    python build.py --pdf      # HTML + files/CV_<name>_<Mon><YYYY>.pdf via headless Chrome
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
PUB_GROUPS = [("journal", "Journal Articles"), ("conference", "International Conferences"),
              ("domestic", "Domestic Conferences and Workshops"), ("patent", "Patents")]


# ------------------------------------------------------------------ formatting

def fmt_date(v: str | None) -> str:
    if not v:
        return ""
    v = str(v)
    if v.lower() == "present":
        return "Present"
    parts = v.split("-")
    if len(parts) >= 2 and parts[1].isdigit():
        return f"{MONTHS[int(parts[1]) - 1]} {parts[0]}"
    return parts[0]


def fmt_range(a: str | None, b: str | None) -> str:
    fa, fb = fmt_date(a), fmt_date(b)
    if not fb or fa == fb:
        return fa
    return f"{fa} – {fb}"


def long_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return d.strftime("%B ") + str(d.day) + d.strftime(", %Y")


def cv_filename(data: dict) -> str:
    d = date.fromisoformat(data["updated"])
    prefix = data.get("site", {}).get("cv_file_prefix") or "CV"
    return f"{prefix}_{MONTHS[d.month - 1]}{d.year}.pdf"


def authors_html(pub: dict, me: set[str]) -> str:
    out = []
    for a in pub.get("authors") or []:
        name = escape(a["name"])
        if a["name"] in me:
            name = f"<strong>{name}</strong>"
        if a.get("equal"):
            name += '<sup class="eq">#</sup>'
        out.append(name)
    return ", ".join(out)


def figure_html(fig: dict | None, up: str, cls: str) -> str:
    if not fig:
        return ""
    cap = f'<figcaption>{escape(fig["caption"])}</figcaption>' if fig.get("caption") else ""
    credit = f'<span class="credit">{escape(fig["credit"])}</span>' if fig.get("credit") else ""
    return (f'<figure class="{cls}"><a href="{up}{escape(fig["file"])}"><img src="{up}{escape(fig["file"])}" '
            f'alt="{escape(fig.get("caption") or "figure")}" loading="lazy"></a>{cap}{credit}</figure>')


def pub_html(pub: dict, me: set[str], rich: bool = False, up: str = "") -> str:
    title = escape(pub["title"])
    if pub.get("doi"):
        title = f'<a href="https://doi.org/{escape(pub["doi"])}">{title}</a>'
    en = f'<span class="title-en">({escape(pub["title_en"])})</span>' if pub.get("title_en") else ""
    venue = escape(pub.get("venue", ""))
    details = f", {escape(pub['details'])}" if pub.get("details") else ""
    text = (f'<div class="pub-title">{title} {en}</div>'
            f'<div class="pub-authors">{authors_html(pub, me)}</div>'
            f'<div class="pub-venue"><em>{venue}</em>{details}</div>')
    if not rich:
        return f'<li class="pub">{text}</li>'
    if pub.get("abstract"):
        src = escape(pub.get("abstract_source", ""))
        text += (f'<details class="abstract"><summary>Abstract</summary><p>{escape(pub["abstract"])}</p>'
                 f'<p class="src">Source: <a href="{src}">{src.split("//", 1)[-1].split("/", 1)[0]}</a></p></details>')
    fig = figure_html(pub.get("figure"), up, "pub-fig")
    return f'<li class="pub rich{" has-fig" if fig else ""}">{fig}<div class="pub-text">{text}</div></li>'


def publications_html(data: dict, heading_tag: str = "h2", rich: bool = False, up: str = "") -> str:
    me = set(data["profile"].get("me") or [data["profile"]["name"]])
    pubs = data.get("publications") or []
    parts = []
    for kind, label in PUB_GROUPS:
        items = [p for p in pubs if p.get("kind") == kind]
        if items:
            parts.append(f'<{heading_tag} class="pub-group">{label}</{heading_tag}>'
                         f'<ul class="pubs">{"".join(pub_html(p, me, rich, up) for p in items)}</ul>')
    if any(a.get("equal") for p in pubs for a in p.get("authors") or []):
        note = data.get("site", {}).get("equal_contribution_note") or "# these authors contributed equally to this work"
        parts.append(f'<p class="eq-note">{escape(note)}</p>')
    return "".join(parts)


def row(left: str, right: str, sub: str = "", body: str = "") -> str:
    return (f'<div class="row"><div class="row-head"><span class="row-title">{left}</span>'
            f'<span class="row-date">{right}</span></div>'
            + (f'<div class="row-sub">{sub}</div>' if sub else "") + body + "</div>")


def experience_html(data: dict) -> str:
    out = []
    for e in data.get("experience") or []:
        roles = []
        for r in e.get("roles") or []:
            bullets = "".join(f"<li>{escape(b['text'])}</li>" for b in r.get("bullets") or [])
            roles.append(row(escape(r["title"]), fmt_range(r.get("from"), r.get("to")),
                             body=f"<ul>{bullets}</ul>" if bullets else ""))
        out.append(f'<div class="org"><div class="org-name">{escape(e["org"])}'
                   f'<span class="org-place">{escape(e.get("place", ""))}</span></div>{"".join(roles)}</div>')
    return "".join(out)


def cv_body(data: dict, pub_heading: str = "h3") -> str:
    edu = "".join(row(escape(e["school"]), fmt_range(e.get("from"), e.get("to")), escape(e["degree"]))
                  for e in data.get("education") or [])
    hon = "".join(row(escape(h["title"]), fmt_range(h.get("from"), h.get("to"))) for h in data.get("honors") or [])
    act = "".join(row(escape(a["title"]), fmt_range(a.get("from"), a.get("to")),
                      body=f'<p class="row-text">{escape(a["text"])}</p>' if a.get("text") else "")
                  for a in data.get("activities") or [])
    lang = "".join(f"<p>{escape(x['text'])}</p>" for x in data.get("languages") or [])
    return (f'<section><h2>Experience</h2>{experience_html(data)}</section>'
            f'<section><h2>Education</h2>{edu}</section>'
            f'<section><h2>Publications and Patents</h2>{publications_html(data, pub_heading)}</section>'
            + (f'<section><h2>Honors and Scholarships</h2>{hon}</section>' if hon else "")
            + (f'<section><h2>Activities</h2>{act}</section>' if act else "")
            + (f'<section><h2>Languages</h2>{lang}</section>' if lang else ""))


# ------------------------------------------------------------------ pages

def links_html(data: dict) -> str:
    items = [f'<li><a href="{escape(l["url"])}" rel="me">{escape(l["label"])}</a></li>'
             for l in data["profile"].get("links") or []]
    return f'<ul class="links">{"".join(items)}</ul>'


def page(data: dict, title: str, active: str, body: str, depth: int) -> str:
    p = data["profile"]
    up = "../" * depth
    nav = [("About", f"{up}index.html", "about"), ("CV", f"{up}cv/", "cv"),
           ("Publications", f"{up}publications/", "publications")]
    if data.get("projects"):
        nav.append(("Portfolio", f"{up}portfolio/", "portfolio"))
    nav_html = "".join(f'<a href="{h}"{" aria-current=page" if k == active else ""}>{n}</a>' for n, h, k in nav)
    if p.get("photo"):
        avatar = f'<img class="avatar" src="{up}{escape(p["photo"])}" alt="{escape(p["name"])}" width="112" height="112">'
    else:
        initials = "".join(w[0] for w in p["name"].split()[:2])
        avatar = f'<div class="avatar" aria-hidden="true">{escape(initials)}</div>'
    native = f'<p class="native">{escape(p["name_native"])}</p>' if p.get("name_native") else ""
    desc = escape(f'{p["name"]} — {p.get("headline", "")}')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{escape(title)}"><meta property="og:description" content="{desc}">
<link rel="canonical" href="{escape(data.get('site', {}).get('url', ''))}/">
<link rel="stylesheet" href="{up}assets/style.css">
</head><body>
<header class="top"><div class="wrap"><a class="brand" href="{up}index.html">{escape(p["name"])}</a><nav>{nav_html}</nav></div></header>
<div class="wrap layout">
<aside class="side">
{avatar}
<h1 class="name">{escape(p["name"])}</h1>{native}
<p class="headline">{escape(p.get("headline", ""))}</p>
<p class="loc">{escape(p.get("location", ""))}</p>
{links_html(data)}
</aside>
<main>{body}</main>
</div>
<footer class="wrap foot">Last updated {long_date(data["updated"])} · generated from a sourced career record</footer>
</body></html>
"""


def print_page(data: dict) -> str:
    p = data["profile"]
    def shown(url: str) -> str:
        return url.removeprefix("mailto:").split("//", 1)[-1].removeprefix("www.")

    links = " · ".join(f'<a href="{escape(l["url"])}">{escape(shown(l["url"]))}</a>' for l in p.get("links") or [])
    site = data.get("site", {}).get("url", "")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{escape(p["name"])} — CV</title>
<link rel="stylesheet" href="../assets/style.css"><link rel="stylesheet" href="../assets/print.css">
</head><body class="print">
<header class="cv-head"><h1>{escape(p["name"])}</h1>
<p>{escape(p.get("headline", ""))} · {escape(p.get("location", ""))}</p>
<p class="cv-links"><a href="{escape(site)}">{escape(site.split("//", 1)[-1])}</a> · {links}</p></header>
{cv_body(data)}
<p class="cv-updated">Last updated {long_date(data["updated"])}</p>
</body></html>
"""


def project_html(prj: dict, up: str) -> str:
    bullets = "".join(f"<li>{escape(b['text'])}</li>" for b in prj.get("bullets") or [])
    tags = "".join(f'<li>{escape(t)}</li>' for t in prj.get("tags") or [])
    when = fmt_range(prj.get("from"), prj.get("to"))
    meta = " · ".join(x for x in (escape(prj.get("org", "")), when) if x)
    img = figure_html(prj.get("image"), up, "prj-img")
    return (f'<article class="project{" has-img" if img else ""}">{img}<div class="prj-text">'
            f'<h2 class="prj-title">{escape(prj["title"])}</h2><p class="prj-meta">{meta}</p>'
            f'<p>{escape(prj.get("summary", ""))}</p>'
            + (f"<ul>{bullets}</ul>" if bullets else "")
            + (f'<ul class="tags">{tags}</ul>' if tags else "") + "</div></article>")


def assets_used(data: dict) -> list[str]:
    files = [data["profile"].get("photo")]
    files += [(p.get("figure") or {}).get("file") for p in data.get("publications") or []]
    files += [(p.get("image") or {}).get("file") for p in data.get("projects") or []]
    return [f for f in files if f]


def build(data: dict) -> list[tuple[str, str]]:
    name = data["profile"]["name"]
    about = "".join(f"<p>{escape(a['text'])}</p>" for a in data.get("about") or [])
    pdf = cv_filename(data)
    cv = (f'<h1 class="page-title">CV</h1><p class="download"><a href="../files/{pdf}">Download PDF</a>'
          f' <span class="muted">({pdf}, updated {long_date(data["updated"])})</span></p>' + cv_body(data))
    pubs = '<h1 class="page-title">Publications</h1>' + publications_html(data, rich=True, up="../")
    pages = [
        ("index.html", page(data, name, "about", f'<h1 class="page-title">About me</h1>{about}', 0)),
        ("cv/index.html", page(data, f"CV — {name}", "cv", cv, 1)),
        ("publications/index.html", page(data, f"Publications — {name}", "publications", pubs, 1)),
        ("cv/print.html", print_page(data)),
    ]
    if data.get("projects"):
        body = ('<h1 class="page-title">Portfolio</h1>'
                + "".join(project_html(p, "../") for p in data["projects"]))
        pages.append(("portfolio/index.html", page(data, f"Portfolio — {name}", "portfolio", body, 1)))
    return pages


# ------------------------------------------------------------------ pdf

def find_chrome() -> str | None:
    cands = [os.environ.get("CHROME"), shutil.which("google-chrome"), shutil.which("chromium"),
             shutil.which("chromium-browser"), shutil.which("chrome"),
             r"C:\Program Files\Google\Chrome\Application\chrome.exe",
             r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
             "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    return next((c for c in cands if c and Path(c).exists()), None)


def render_pdf(src: Path, dest: Path) -> None:
    chrome = find_chrome()
    if not chrome:
        sys.exit("no Chrome/Chromium found; set CHROME or build without --pdf")
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                    f"--print-to-pdf={dest}", src.resolve().as_uri()],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    if not dest.is_file() or dest.stat().st_size < 1000:
        sys.exit(f"PDF was not written: {dest}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", action="store_true")
    ap.add_argument("--data", default=str(ROOT / "data" / "cv.json"))
    args = ap.parse_args()
    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    missing = [f for f in assets_used(data) if not (ROOT / f).is_file()]
    if missing:
        sys.exit("files named in data/cv.json are missing from this repository: " + ", ".join(missing))
    if OUT.exists():
        shutil.rmtree(OUT)
    for rel, html in build(data):
        f = OUT / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(html, encoding="utf-8")
    shutil.copytree(ROOT / "assets", OUT / "assets")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    if args.pdf:
        pdf = OUT / "files" / cv_filename(data)
        render_pdf(OUT / "cv" / "print.html", pdf)
        shutil.copy(pdf, OUT / "files" / "cv.pdf")
    print(f"built {OUT} (updated {data['updated']}{', ' + cv_filename(data) if args.pdf else ''})")


if __name__ == "__main__":
    main()
