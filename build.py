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


def pub_figures(pub: dict) -> list[dict]:
    """`figures` (list, current schema) or the single `figure` (older exports); at most two."""
    figs = pub.get("figures")
    if not isinstance(figs, list):
        figs = [pub["figure"]] if isinstance(pub.get("figure"), dict) else []
    return [f for f in figs if isinstance(f, dict) and f.get("file")][:2]


def source_link(url: str | None) -> str:
    """'https://doi.org/... — note' -> a link on the URL part, the rest as text."""
    if not url:
        return ""
    head, _, rest = str(url).partition(" ")
    if head.startswith("http"):
        host = head.split("//", 1)[-1].split("/", 1)[0]
        return f'<a href="{escape(head)}">{escape(host)}</a>' + (f" {escape(rest)}" if rest else "")
    return escape(str(url))


def image_size(rel: str) -> tuple[int, int] | None:
    """(width, height) of a PNG or JPEG in this repository, from its header; None if unknown."""
    try:
        b = (ROOT / rel).read_bytes()[:256 * 1024]
    except OSError:
        return None
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big")
    i = 2 if b[:2] == b"\xff\xd8" else len(b)
    while i + 9 < len(b):
        if b[i] != 0xFF:
            i += 1
            continue
        m = b[i + 1]
        if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            return int.from_bytes(b[i + 7:i + 9], "big"), int.from_bytes(b[i + 5:i + 7], "big")
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
            i += 2
            continue
        i += 2 + int.from_bytes(b[i + 2:i + 4], "big")
    return None


def figure_html(fig: dict | None, up: str, cls: str) -> str:
    if not fig:
        return ""
    cap = escape(fig["caption"]) if fig.get("caption") else ""
    extra = []
    if fig.get("credit"):
        extra.append(f'<span class="credit">{escape(fig["credit"])}</span>')
    if str(fig.get("source") or "").startswith("http"):       # an original diagram has no outside source to link
        extra.append(f'<span class="credit">Source: {source_link(fig["source"])}</span>')
    alt = fig.get("alt") or fig.get("caption") or "figure"
    size = image_size(fig["file"])
    dims = f' width="{size[0]}" height="{size[1]}"' if size else ""
    if size and size[0] > 2.5 * size[1]:
        cls += " wide"   # a wide diagram gets the full row on the Publications page
    return (f'<figure class="{cls}"><a href="{up}{escape(fig["file"])}"><img src="{up}{escape(fig["file"])}" '
            f'alt="{escape(alt)}"{dims} loading="lazy" decoding="async"></a>'
            f'<figcaption>{cap}{"".join(extra)}</figcaption></figure>')


def keywords_html(pub: dict) -> str:
    kws = [k for k in pub.get("keywords") or [] if isinstance(k, str)]
    if not kws:
        return ""
    return ('<p class="pub-kw"><span class="kw-label">Keywords:</span> '
            + "; ".join(f'<span class="kw">{escape(k)}</span>' for k in kws) + "</p>")


# ------------------------------------------------------------------ lines and time
# Presentation only: which coloured line an entry is drawn on is read from words already in the data.

AGENT_WORDS = ("mcp", "langgraph", "llm agent", "agentic")
LINE_NAMES = {"v": "3D vision", "a": "AI agents"}


def on_agent_line(texts: list[str]) -> bool:
    return any(w in (t or "").lower() for t in texts for w in AGENT_WORDS)


def year_f(v: str | None, today: float) -> float:
    """A date string as a fractional year. A bare year sits mid-year (the month is unknown)."""
    v = str(v or "")
    if not v or v.lower() == "present":
        return today
    parts = v.split("-")
    if len(parts) >= 2 and parts[1].isdigit():
        return int(parts[0]) + (int(parts[1]) - 1) / 12
    return int(parts[0]) + 0.5


def today_f(data: dict) -> float:
    d = date.fromisoformat(data["updated"])
    return d.year + (d.month - 1) / 12 + d.day / 365


def line_start(data: dict) -> float:
    """The research line begins with the first publication."""
    t = today_f(data)
    return min((year_f(p.get("date"), t) for p in data.get("publications") or [] if p.get("date")), default=t)


def pre(data: dict, when: str | None) -> str:
    return " pre" if year_f(when, today_f(data)) < line_start(data) else ""


def slug(text: str) -> str:
    out = "".join(c.lower() if c.isascii() and c.isalnum() else "-" for c in text)
    return "-".join(x for x in out.split("-") if x)[:60]


def short(text: str, limit: int = 34) -> str:
    text = text.split(" (")[0]
    return text if len(text) <= limit else text.split(",")[0]


def my_authorship(pub: dict, me: set[str]) -> str:
    authors = pub.get("authors") or []
    for i, a in enumerate(authors):
        if a["name"] in me:
            first_block = all(x.get("equal") for x in authors[:i + 1])
            if a.get("equal") and first_block:
                return "joint first author"
            return "first author" if i == 0 else ""
    return ""


def venue_short(pub: dict) -> str:
    v = pub.get("venue", "")
    if v.endswith(")") and " (" in v:
        return v.rsplit(" (", 1)[1][:-1]
    return v


# ------------------------------------------------------------------ entries

def entry(title: str, when: str = "", rest: str = "", mark: str = "ring", cls: str = "", id_: str = "",
          tag: str = "h3") -> str:
    ident = f' id="{escape(id_)}"' if id_ else ""
    return (f'<li class="e {mark}{cls}"{ident}><{tag} class="e-title">{title}</{tag}>'
            + (f'<p class="e-when">{when}</p>' if when else "")
            + (f'<div class="e-rest">{rest}</div>' if rest else "") + "</li>")


def pub_entry(data: dict, pub: dict, me: set[str], rich: bool = False, up: str = "", brief: bool = False,
              tag: str = "h4") -> str:
    title = escape(pub["title"])
    if pub.get("doi"):
        title = f'<a href="https://doi.org/{escape(pub["doi"])}">{title}</a>'
    elif brief and pub.get("id"):
        title = f'<a href="{up}publications/#{escape(pub["id"])}">{title}</a>'
    if pub.get("title_en"):
        title += f' <span class="title-en">({escape(pub["title_en"])})</span>'
    details = f", {escape(pub['details'])}" if pub.get("details") else ""
    rest = (f'<p class="pub-authors">{authors_html(pub, me)}</p>'
            f'<p class="pub-venue"><em>{escape(pub.get("venue", ""))}</em>{details}</p>')
    if not brief:
        if pub.get("summary"):
            rest += f'<p class="pub-summary">{escape(pub["summary"])}</p>'
        rest += keywords_html(pub)
    if rich:
        if pub.get("abstract"):
            rest += (f'<details class="abstract"><summary>Abstract</summary><p>{escape(pub["abstract"])}</p>'
                     f'<p class="src">Source: {source_link(pub.get("abstract_source"))}</p></details>')
        figs = "".join(figure_html(f, up, "pub-fig") for f in pub_figures(pub))
        rest += f'<div class="pub-figs">{figs}</div>' if figs else ""
    year = str(pub.get("date") or "")[:4]
    mark = "square" if pub.get("kind") == "patent" else "dot"
    ident = pub.get("id", "") if rich else ""
    return entry(title, year, rest, mark, " pub" + pre(data, pub.get("date")), ident, tag)


def publications_html(data: dict, heading_tag: str = "h3", rich: bool = False, up: str = "",
                      brief: bool = False) -> str:
    me = set(data["profile"].get("me") or [data["profile"]["name"]])
    pubs = data.get("publications") or []
    sub = "h3" if heading_tag == "h2" else "h4"
    parts = []
    for kind, label in PUB_GROUPS:
        items = [p for p in pubs if p.get("kind") == kind]
        if items:
            rows = '<ol class="line">' + "".join(pub_entry(data, p, me, rich, up, brief, sub) for p in items) + "</ol>"
            parts.append(band(kind, label, rows) if rich else f'<{heading_tag} class="pub-group">{label}</{heading_tag}>{rows}')
    if any(a.get("equal") for p in pubs for a in p.get("authors") or []):
        note = data.get("site", {}).get("equal_contribution_note") or "# these authors contributed equally to this work"
        parts.append(f'<p class="eq-note">{escape(note)}</p>')
    return "".join(parts)


def experience_html(data: dict) -> str:
    out = []
    for i, e in enumerate(data.get("experience") or []):
        roles = []
        for j, r in enumerate(e.get("roles") or []):
            bullets = "".join(f"<li>{escape(b['text'])}</li>" for b in r.get("bullets") or [])
            now = " now" if str(r.get("to", "")).lower() == "present" else ""
            roles.append(entry(escape(r["title"]), fmt_range(r.get("from"), r.get("to")),
                               f"<ul>{bullets}</ul>" if bullets else "", "ring",
                               now + pre(data, r.get("from")), f"exp-{i}-{j}", "h4"))
        place = f' <span class="org-place">{escape(e["place"])}</span>' if e.get("place") else ""
        out.append(f'<div class="org"><h3 class="org-name">{escape(e["org"])}{place}</h3>'
                   f'<ol class="line">{"".join(roles)}</ol></div>')
    return "".join(out)


def skills_html(data: dict) -> str:
    rows = "".join(f'<div class="skill"><dt>{escape(g["group"])}</dt><dd>{escape(", ".join(g.get("items") or []))}</dd></div>'
                   for g in data.get("skills") or [])
    return f'<dl class="skills">{rows}</dl>' if rows else ""


def cv_body(data: dict) -> str:
    edu = "".join(entry(escape(e["school"]), fmt_range(e.get("from"), e.get("to")),
                        f'<p class="e-sub">{escape(e["degree"])}</p>', "ring", pre(data, e.get("from")), f"edu-{i}")
                  for i, e in enumerate(data.get("education") or []))
    hon = "".join(entry(escape(h["title"]), fmt_range(h.get("from"), h.get("to")), "", "tick", pre(data, h.get("from")))
                  for h in data.get("honors") or [])
    act = "".join(entry(escape(a["title"]), fmt_range(a.get("from"), a.get("to")),
                        f'<p class="e-sub">{escape(a["text"])}</p>' if a.get("text") else "", "tick",
                        pre(data, a.get("from")))
                  for a in data.get("activities") or [])
    lang = "".join(f"<p>{escape(x['text'])}</p>" for x in data.get("languages") or [])

    sec = band

    return (sec("experience", "Experience", experience_html(data))
            + sec("education", "Education", f'<ol class="line">{edu}</ol>')
            + (sec("skills", "Skills", skills_html(data)) if data.get("skills") else "")
            + sec("publications", "Publications and Patents", publications_html(data))
            + (sec("honors", "Honors and Scholarships", f'<ol class="line">{hon}</ol>') if hon else "")
            + (sec("activities", "Activities", f'<ol class="line">{act}</ol>') if act else "")
            + (sec("languages", "Languages", lang) if lang else ""))


# ------------------------------------------------------------------ structured data

def scholarly_items(data: dict) -> list[dict]:
    """schema.org ScholarlyArticle (papers) / CreativeWork (patents) per publication, for crawlers and LLM readers."""
    base = (data.get("site", {}).get("url") or "").rstrip("/")
    me = set(data["profile"].get("me") or [data["profile"]["name"]])
    graph = []
    for pub in data.get("publications") or []:
        kind = pub.get("kind")
        item = {"@type": "CreativeWork" if kind == "patent" else "ScholarlyArticle",
                "name": pub.get("title"), "headline": pub.get("title"),
                "author": [{"@type": "Person", "name": a["name"], **({"@id": f"{base}/#person"} if a["name"] in me else {})}
                           for a in pub.get("authors") or []]}
        if pub.get("id"):
            item["@id"] = f"{base}/publications/#{pub['id']}"
            item["url"] = item["@id"]
        if kind == "patent":
            item["additionalType"] = "Patent"
        if pub.get("title_en"):
            item["alternateName"] = pub["title_en"]
        if any(ord(c) > 0x3000 for c in pub.get("title", "")):
            item["inLanguage"] = "ko"
        if pub.get("date"):
            item["datePublished"] = str(pub["date"])
        if pub.get("venue"):
            item["isPartOf"] = {"@type": "Periodical" if kind == "journal" else "CreativeWork", "name": pub["venue"]}
        if pub.get("publisher"):
            item["publisher"] = {"@type": "Organization", "name": pub["publisher"]}
        if pub.get("summary"):
            item["description"] = pub["summary"]
        if pub.get("abstract"):
            item["abstract"] = pub["abstract"]
        if pub.get("keywords"):
            item["keywords"] = ", ".join(pub["keywords"])
        if pub.get("doi"):
            item["sameAs"] = f"https://doi.org/{pub['doi']}"
            item["identifier"] = {"@type": "PropertyValue", "propertyID": "DOI", "value": pub["doi"]}
        imgs = [{"@type": "ImageObject", "contentUrl": f"{base}/{f['file']}", "caption": f.get("caption"),
                 "description": f.get("alt"), "creditText": f.get("credit")} for f in pub_figures(pub)]
        if imgs:
            item["image"] = [{k: v for k, v in i.items() if v} for i in imgs]
        graph.append({k: v for k, v in item.items() if v})
    return graph


def person_item(data: dict) -> dict:
    """schema.org Person built only from fields of data/cv.json."""
    p, base = data["profile"], (data.get("site", {}).get("url") or "").rstrip("/")
    links = [l["url"] for l in p.get("links") or []]
    current = next(((e, r) for e in data.get("experience") or [] for r in e.get("roles") or []
                    if str(r.get("to", "")).lower() == "present"), None)
    topics, seen = [], set()
    for t in ([t for g in data.get("skills") or [] for t in g.get("items") or []]
              + [t for prj in data.get("projects") or [] for t in prj.get("tags") or []]
              + [k for pub in data.get("publications") or [] for k in pub.get("keywords") or []]):
        if t.lower() not in seen:
            seen.add(t.lower())
            topics.append(t)
    schools = list(dict.fromkeys(e["school"] for e in data.get("education") or []))
    item = {"@type": "Person", "@id": f"{base}/#person", "name": p["name"],
            "alternateName": [n for n in [p.get("name_native"), *(p.get("me") or [])] if n and n != p["name"]],
            "url": f"{base}/", "image": f"{base}/{p['photo']}" if p.get("photo") else None,
            "description": " ".join(a["text"] for a in data.get("about") or []),
            "jobTitle": current[1]["title"] if current else None,
            "worksFor": {"@type": "Organization", "name": current[0]["org"]} if current else None,
            "address": {"@type": "PostalAddress", "addressLocality": p["location"]} if p.get("location") else None,
            "email": next((u for u in links if u.startswith("mailto:")), None),
            "sameAs": [u for u in links if u.startswith("http")],
            "alumniOf": [{"@type": "CollegeOrUniversity", "name": s} for s in schools],
            "knowsAbout": topics}
    item["alternateName"] = list(dict.fromkeys(item["alternateName"]))
    return {k: v for k, v in item.items() if v}


def jsonld(data: dict, kind: str) -> str:
    base = (data.get("site", {}).get("url") or "").rstrip("/")
    graph = [person_item(data)]
    if kind == "about":
        graph.insert(0, {"@type": "ProfilePage", "@id": f"{base}/", "url": f"{base}/", "name": data["profile"]["name"],
                         "dateModified": data["updated"], "inLanguage": "en", "mainEntity": {"@id": f"{base}/#person"}})
    if kind in ("cv", "publications"):
        graph += scholarly_items(data)
    doc = {"@context": "https://schema.org", "@graph": graph}
    return ('<script type="application/ld+json">'
            + json.dumps(doc, ensure_ascii=False, indent=1).replace("</", "<\\/") + "</script>")


# ------------------------------------------------------------------ pages

NAV = [("About", "", "about"), ("CV", "cv/", "cv"), ("Publications", "publications/", "publications"),
       ("Portfolio", "portfolio/", "portfolio")]
FONT = "assets/fonts/archivo-latin-wght-normal.woff2"


def links_html(data: dict, up: str, cls: str = "links") -> str:
    items = [f'<li><a href="{escape(l["url"])}" rel="me">{escape(l["label"])}</a></li>'
             for l in data["profile"].get("links") or []]
    items.append(f'<li><a href="{up}files/cv.pdf">CV (PDF)</a></li>')
    return f'<ul class="{cls}">{"".join(items)}</ul>'


def band(name: str, title: str, body: str, note: str = "") -> str:
    """One section of the grid: a label column (heading and an optional note) beside the content."""
    note = f'<p class="band-note">{note}</p>' if note else ""
    return (f'<section class="band" id="{name}" aria-labelledby="{name}-h"><div class="band-head">'
            f'<h2 id="{name}-h">{title}</h2>{note}</div><div class="band-body">{body}</div></section>')


def page(data: dict, title: str, active: str, body: str, depth: int, description: str = "") -> str:
    p, site = data["profile"], data.get("site", {})
    up, base = "../" * depth, (site.get("url") or "").rstrip("/")
    nav = [n for n in NAV if n[2] != "portfolio" or data.get("projects")]
    path = next(h for _, h, k in nav if k == active)
    cur = ' aria-current="page"'
    nav_html = "".join(f'<li><a href="{(up + h) or "./"}"{cur if k == active else ""}>{n}</a></li>' for n, h, k in nav)
    desc = escape(description or f'{p["name"]}: {p.get("headline", "")}')
    image = f'<meta property="og:image" content="{base}/{escape(p["photo"])}">' if p.get("photo") else ""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{desc}">
<meta name="author" content="{escape(p["name"])}">
<link rel="canonical" href="{base}/{path}">
<link rel="alternate" type="text/markdown" href="{base}/cv.md" title="CV as plain text">
<link rel="alternate" type="application/pdf" href="{base}/files/cv.pdf" title="CV as PDF">
<meta property="og:type" content="profile"><meta property="og:url" content="{base}/{path}">
<meta property="og:title" content="{escape(title)}"><meta property="og:description" content="{desc}">{image}
<meta name="twitter:card" content="summary">
<meta name="color-scheme" content="light">
<link rel="preload" href="{up}{FONT}" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{up}assets/style.css">
{jsonld(data, active)}
</head><body>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="wrap"><a class="brand" href="{up or "./"}">{escape(p["name"])}</a>
<nav aria-label="Pages"><ul>{nav_html}</ul></nav>
<a class="pdf" href="{up}files/cv.pdf">CV (PDF)</a></div></header>
<main id="main" class="wrap">{body}</main>
<footer class="foot"><div class="wrap"><p class="foot-name">{escape(p["name"])}</p>{links_html(data, up, "foot-links")}
<p class="foot-note">Last updated {long_date(data["updated"])}. Generated from a sourced career record.
Plain text: <a href="{up}cv.md">cv.md</a></p></div></footer>
</body></html>
"""


def page_head(data: dict, title: str, extra: str = "") -> str:
    p = data["profile"]
    native = f' ({escape(p["name_native"])})' if p.get("name_native") else ""
    return (f'<header class="page-head"><h1>{title}</h1>'
            f'<p class="page-who">{escape(p["name"])}{native} · {escape(p.get("headline", ""))}</p>{extra}</header>')


def print_page(data: dict) -> str:
    p = data["profile"]

    def shown(url: str) -> str:
        return url.removeprefix("mailto:").split("//", 1)[-1].removeprefix("www.")

    links = " · ".join(f'<a href="{escape(l["url"])}">{escape(shown(l["url"]))}</a>' for l in p.get("links") or [])
    site = data.get("site", {}).get("url", "")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{escape(p["name"])} CV</title>
<meta name="author" content="{escape(p["name"])}"><meta name="robots" content="noindex">
<link rel="stylesheet" href="../assets/style.css"><link rel="stylesheet" href="../assets/print.css">
</head><body class="print">
<header class="cv-head"><h1>{escape(p["name"])}</h1>
<p>{escape(p.get("headline", ""))} · {escape(p.get("location", ""))}</p>
<p class="cv-links"><a href="{escape(site)}">{escape(site.split("//", 1)[-1])}</a> · {links}</p></header>
{cv_body(data)}
<p class="cv-updated">Last updated {long_date(data["updated"])}</p>
</body></html>
"""


def line_codes(on_ai: bool, on_3d: bool = True) -> str:
    codes = (['<span class="code v">3D vision</span>'] if on_3d else []) + (['<span class="code a">AI agents</span>'] if on_ai else [])
    return f'<span class="codes">{"".join(codes)}</span>'


def project_lines(prj: dict) -> tuple[bool, bool]:
    tags = prj.get("tags") or []
    on_ai = on_agent_line(tags + [prj.get("title", "")])
    return on_ai, (not on_ai) or any(not on_agent_line([t]) for t in tags)


def project_html(prj: dict, up: str, home: bool = False) -> str:
    """One project row: title, line codes, summary and every result sentence beside its figure."""
    title = escape(prj["title"])
    if home:
        title = f'<a href="portfolio/#{slug(prj["title"])}">{title}</a>'
    bullets = "".join(f"<li>{escape(b['text'])}</li>" for b in prj.get("bullets") or [])
    tags = "" if home else "".join(f'<li>{escape(t)}</li>' for t in prj.get("tags") or [])
    meta = " · ".join(x for x in (escape(prj.get("org", "")), fmt_range(prj.get("from"), prj.get("to"))) if x)
    img = figure_html(prj.get("image"), up, "job-fig")
    ident = "" if home else f' id="{slug(prj["title"])}"'
    return (f'<article class="job{" has-fig" if img else ""}"{ident}><div class="job-text">'
            f'<{"h3" if home else "h2"} class="job-title">{title}</{"h3" if home else "h2"}>'
            f'<p class="job-meta">{line_codes(*project_lines(prj))}<span>{meta}</span></p>'
            f'<p class="job-sum{"" if bullets else " lead"}">{escape(prj.get("summary", ""))}</p>'
            + (f'<ul class="res">{bullets}</ul>' if bullets else "")
            + (f'<ul class="tags">{tags}</ul>' if tags else "") + f"</div>{img}</article>")


def home_pubs(data: dict) -> str:
    """Journal articles, international conferences and patents, newest first, as type-only rows."""
    me = set(data["profile"].get("me") or [data["profile"]["name"]])
    pubs = [p for p in data.get("publications") or [] if p.get("kind") != "domestic"]
    rows = []
    for p in sorted(pubs, key=lambda x: str(x.get("date") or ""), reverse=True):
        href = f'publications/#{escape(p["id"])}' if p.get("id") else "publications/"
        note = my_authorship(p, me)
        venue = f'<b>{escape(p.get("venue", ""))}</b>' + (f', {escape(p["details"])}' if p.get("details") else "")
        rows.append(f'<li class="pub-row"><span class="pub-year">{str(p.get("date") or "")[:4]}</span> '
                    f'<h3><a href="{href}">{escape(p["title"])}</a></h3>'
                    f'<p>{venue}{f" · {note}" if note else ""}</p></li>')
    counts = [(sum(1 for p in data.get("publications") or [] if p.get("kind") == k), label)
              for k, label in (("journal", "journal"), ("conference", "international conference"), ("domestic", "domestic"),
                               ("patent", "patent"))]
    note = ", ".join(f"{n} {label}{'s' if n > 1 and label != 'domestic' else ''}" for n, label in counts if n)
    more = '<p class="more"><a href="publications/">All publications, with abstracts and figures</a></p>'
    return band("publications", "Publications and patents", f'<ol class="pub-rows">{"".join(rows)}</ol>{more}', note) if rows else ""


def home_record(data: dict) -> str:
    """Roles at the current employer and degrees; the full record is on the CV page."""
    rows = []
    for e in data.get("experience") or []:
        roles = e.get("roles") or []
        if any(str(r.get("to", "")).lower() == "present" for r in roles):
            rows += [(fmt_range(r.get("from"), r.get("to")), r["title"], e["org"]) for r in roles]
    rows += [(fmt_range(e.get("from"), e.get("to")), e["degree"], e["school"]) for e in data.get("education") or []
             if e.get("to") != e.get("from")]
    items = "".join(f'<li><span class="row-when">{escape(a)}</span> <span class="row-what">{escape(b)}</span> '
                    f'<span class="row-where">{escape(c)}</span></li>' for a, b, c in rows)
    more = '<p class="more"><a href="cv/">Full CV</a></p>'
    return band("record", "Experience and education", f'<ul class="rows">{items}</ul>{more}') if rows else ""


def home_html(data: dict) -> str:
    p = data["profile"]
    about = data.get("about") or []
    photo = (f'<img class="photo" src="{escape(p["photo"])}" alt="Portrait of {escape(p["name"])}" width="400" height="400">'
             if p.get("photo") else "")
    sub = " · ".join(x for x in (p.get("name_native"), p.get("headline")) if x)
    cur = next(((e, r) for e in data.get("experience") or [] for r in e.get("roles") or []
                if str(r.get("to", "")).lower() == "present"), None)
    now = (f'<p class="now-role">{escape(cur[1]["title"])}</p><p class="now-meta">{escape(cur[0]["org"])} · '
           f'{fmt_range(cur[1].get("from"), cur[1].get("to"))}<br>{escape(p.get("location", ""))}</p>') if cur else ""
    lede = f'<p class="lede">{escape(about[0]["text"])}</p>' if about else ""
    lines = [project_lines(x) for x in data.get("projects") or []]
    codes = (f'<p class="hero-codes">{line_codes(any(a for a, _ in lines), any(v for _, v in lines))}</p>' if lines else "")
    hero = (f'<section class="hero"><h1>{escape(p["name"])} <span class="h1-sub">{escape(sub)}</span></h1>{photo}'
            f'<div class="hero-now">{now}</div><div class="hero-links">{codes}{links_html(data, "")}</div>{lede}</section>')
    work = "".join(project_html(x, "", home=True) for x in data.get("projects") or [])
    rest = "".join(f"<p>{escape(a['text'])}</p>" for a in about[1:])
    return (hero + (band("work", "Selected work", work) if work else "") + home_pubs(data) + home_record(data)
            + (band("about", "About", f'<div class="prose">{rest}</div>') if rest else "")
            + (band("skills", "Skills", skills_html(data)) if data.get("skills") else ""))


def assets_used(data: dict) -> list[str]:
    files = [data["profile"].get("photo")]
    files += [f.get("file") for p in data.get("publications") or [] for f in pub_figures(p)]
    files += [(p.get("image") or {}).get("file") for p in data.get("projects") or []]
    return [f for f in files if f]


# ------------------------------------------------------------------ plain text for machine readers

def cv_markdown(data: dict) -> str:
    p, base = data["profile"], (data.get("site", {}).get("url") or "").rstrip("/")
    me = set(p.get("me") or [p["name"]])
    native = f' ({p["name_native"]})' if p.get("name_native") else ""
    out = [f'# {p["name"]}{native}', "", f'{p.get("headline", "")} · {p.get("location", "")}', ""]
    out += [f'- {l["label"]}: {l["url"].removeprefix("mailto:")}' for l in p.get("links") or []]
    out += [f"- Website: {base}/", f"- CV (PDF): {base}/files/cv.pdf", "", "## About", ""]
    out += [a["text"] + "\n" for a in data.get("about") or []]
    out += ["## Experience", ""]
    for e in data.get("experience") or []:
        out += [f'### {e["org"]}' + (f' ({e["place"]})' if e.get("place") else ""), ""]
        for r in e.get("roles") or []:
            out.append(f'**{r["title"]}** · {fmt_range(r.get("from"), r.get("to"))}')
            out += [f'- {b["text"]}' for b in r.get("bullets") or []] + [""]
    out += ["## Education", ""]
    out += [f'- **{e["school"]}** · {e["degree"]} · {fmt_range(e.get("from"), e.get("to"))}' for e in data.get("education") or []]
    if data.get("skills"):
        out += ["", "## Skills", ""] + [f'- **{g["group"]}**: {", ".join(g.get("items") or [])}' for g in data["skills"]]
    out += ["", "## Publications and Patents", ""]
    for kind, label in PUB_GROUPS:
        items = [x for x in data.get("publications") or [] if x.get("kind") == kind]
        if not items:
            continue
        out += [f"### {label}", ""]
        for pub in items:
            authors = ", ".join((f'**{a["name"]}**' if a["name"] in me else a["name"]) + ("#" if a.get("equal") else "")
                                for a in pub.get("authors") or [])
            title = pub["title"] + (f' ({pub["title_en"]})' if pub.get("title_en") else "")
            venue = pub.get("venue", "") + (f', {pub["details"]}' if pub.get("details") else "")
            out.append(f"- {title}. {authors}. *{venue}*."
                       + (f' https://doi.org/{pub["doi"]}' if pub.get("doi") else ""))
            if pub.get("summary"):
                out.append(f'  {pub["summary"]}')
            if pub.get("keywords"):
                out.append(f'  Keywords: {"; ".join(pub["keywords"])}')
        out.append("")
    if any(a.get("equal") for x in data.get("publications") or [] for a in x.get("authors") or []):
        out += [data.get("site", {}).get("equal_contribution_note") or "# these authors contributed equally to this work", ""]
    if data.get("projects"):
        out += ["## Projects", ""]
        for prj in data["projects"]:
            meta = " · ".join(x for x in (prj.get("org", ""), fmt_range(prj.get("from"), prj.get("to"))) if x)
            out += [f'### {prj["title"]}', "", meta, "", prj.get("summary", ""), ""]
            out += [f'- {b["text"]}' for b in prj.get("bullets") or []]
            if prj.get("tags"):
                out += ["", f'Tags: {", ".join(prj["tags"])}']
            out.append("")
    for key, label in (("honors", "Honors and Scholarships"), ("activities", "Activities")):
        if data.get(key):
            out += [f"## {label}", ""]
            out += [f'- {x["title"]} · {fmt_range(x.get("from"), x.get("to"))}' + (f'. {x["text"]}' if x.get("text") else "")
                    for x in data[key]]
            out.append("")
    if data.get("languages"):
        out += ["## Languages", ""] + [x["text"] for x in data["languages"]] + [""]
    out.append(f'Last updated {long_date(data["updated"])}.')
    return "\n".join(out) + "\n"


def llms_txt(data: dict) -> str:
    p, base = data["profile"], (data.get("site", {}).get("url") or "").rstrip("/")
    native = f' ({p["name_native"]})' if p.get("name_native") else ""
    pages = [f"- [CV as Markdown]({base}/cv.md): the complete CV in plain text",
             f"- [CV as PDF]({base}/files/cv.pdf)", f"- [CV]({base}/cv/): experience, education, publications",
             f"- [Publications]({base}/publications/): summaries, keywords, abstracts and figures, with schema.org JSON-LD"]
    if data.get("projects"):
        pages.append(f"- [Portfolio]({base}/portfolio/): projects")
    about = "\n\n".join(a["text"] for a in data.get("about") or [])
    return (f'# {p["name"]}{native}\n\n> {p.get("headline", "")} · {p.get("location", "")}\n\n{about}\n\n'
            f'Every statement on this site is generated from a sourced career record. Last updated {data["updated"]}.\n\n'
            "## Pages\n\n" + "\n".join(pages) + "\n")


def build(data: dict) -> list[tuple[str, str]]:
    p, base = data["profile"], (data.get("site", {}).get("url") or "").rstrip("/")
    name, pdf = p["name"], cv_filename(data)
    who = f'{name}, {p.get("headline", "")}'
    cv = (page_head(data, "CV", f'<p class="download"><a class="button" href="../files/{pdf}">Download PDF</a>'
                                f'<span class="muted">{pdf}, updated {long_date(data["updated"])}</span></p>')
          + cv_body(data))
    pubs = page_head(data, "Publications") + publications_html(data, "h2", rich=True, up="../")
    about = ""                                   # whole paragraphs only, never a sentence cut in the middle
    for a in data.get("about") or []:
        if about and len(about) + len(a["text"]) > 300:
            break
        about = (about + " " + a["text"]).strip()
    pages = [
        ("index.html", page(data, f'{name}: {p.get("headline", "")}', "about", home_html(data), 0, about)),
        ("cv/index.html", page(data, f"CV: {name}", "cv", cv, 1, f"Curriculum vitae of {who}: experience, education, publications and patents.")),
        ("publications/index.html", page(data, f"Publications: {name}", "publications", pubs, 1,
                                         f"Publications and patents of {who}, with summaries, keywords, abstracts and figures.")),
        ("cv/print.html", print_page(data)),
        ("cv.md", cv_markdown(data)),
        ("llms.txt", llms_txt(data)),
        ("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n"),
    ]
    urls = ["", "cv/", "publications/"]
    if data.get("projects"):
        body = page_head(data, "Portfolio") + '<div class="jobs">' + "".join(project_html(x, "../") for x in data["projects"]) + "</div>"
        pages.append(("portfolio/index.html", page(data, f"Portfolio: {name}", "portfolio", body, 1, f"Projects of {who}.")))
        urls.append("portfolio/")
    sitemap = "".join(f"<url><loc>{base}/{u}</loc><lastmod>{data['updated']}</lastmod></url>" for u in urls)
    pages.append(("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n'
                                 f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sitemap}</urlset>\n'))
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
