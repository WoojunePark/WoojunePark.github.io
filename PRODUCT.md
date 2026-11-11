# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Human reviewers**: hiring managers, engineers who will interview Woojune Park, and recruiters. They arrive from a
  resume link, LinkedIn, GitHub or a name search, often on a phone, and want to learn within a minute who he is,
  what he has shipped and published, and whether to talk to him. Some then read in depth before an interview.
- **Machine readers**: applicant tracking systems, recruiting agents, search crawlers and LLMs that fetch the pages
  or the PDF and summarize or score the candidate. They need complete, unambiguous, well-structured text and data.

## Product Purpose

The personal CV site of Woojune Park (박우준), a research engineer. It presents his experience, publications,
patent and projects, and offers the same CV as a PDF. Success: a reader, human or machine, comes away with an
accurate picture of a research engineer who carries work from research to product, and a human reader wants to
interview him.

## Positioning

A research engineer whose work runs from research to shipped product: 3D vision research (camera pose estimation,
multi-view stereo, 3D Gaussian Splatting; journal papers and a granted US patent) together with production work
(3D asset optimization deployed on LG.com, an MCP tool and a LangGraph agent used by non-engineers). Both threads,
3D vision and AI agents, lead; neither is a footnote. Every statement on the site is generated from a sourced
career record.

## Operating Context

- Pages: About (home), CV, Publications, Portfolio, and a print page that headless Chrome renders to the PDF CV.
- All content comes from `data/cv.json`, exported by a private career record. This repository owns only layout and
  style (`build.py`, `assets/`). Python standard library only; deployed by GitHub Pages on every push to `master`.
- Readers follow links to DOIs, the patent, LinkedIn, GitHub and the PDF.

## Capabilities and Constraints

- Design work may restructure and restyle; it never rewrites, adds or removes facts. Text, numbers and claims come
  only from `data/cv.json`.
- English only. Korean appears in the native name and in the titles and bylines of Korean-language publications.
- The HTML must stay complete without JavaScript and without CSS: every fact present as text in the document, in a
  sensible reading order, with schema.org JSON-LD.
- The PDF is rendered from `cv/print.html`, which shares markup with the CV page; A4, light, selectable text.
- Publication figures carry their verbatim caption, credit line and source. Some may not be altered (licence).
- Skills list only terms the career record states; project diagrams are drawn in the content repository from the
  same record. Do not fabricate either here.

## Brand Commitments

- Not a marketing landing page: no hero slogans, no self-promotional copy, no heavy animation.
- Not a developer-portfolio cliche: no terminal or neon styling, no skill gauges.
- Fast to read: the key career facts and publications are visible with little scrolling or clicking.
- Importance, not chronology, sets size and position: current role, selected work and its results, and publications
  lead; early or unrelated history appears only on the CV page.
- The photo and email address are published at the owner's request.

## Evidence on Hand

- `data/cv.json`: profile, 3 about paragraphs, experience with bullets, education, 7 publications (2 journal,
  2 international conference, 2 domestic, 1 US patent) with summaries, keywords, abstracts, 4 projects with tags,
  honors, activities, languages.
- `assets/pubs/`: 8 publication figures with alt text, caption and credit. `assets/photo.jpg`.
- No testimonials, metrics dashboards, logos or demo videos.

## Product Principles

1. Facts over claims: show the paper, the patent, the number; never an adjective the record does not hold.
2. One read, two readers: the same document must satisfy a person scanning on a phone and a parser reading markup.
3. The shortest path to proof: the strongest evidence sits closest to the top of each page.
4. Quiet confidence: restraint and precision carry the impression, not decoration.

## Accessibility & Inclusion

WCAG 2.2 AA: text contrast, visible focus, keyboard navigation, alt text on every figure, reduced-motion respected,
no horizontal scrolling at 320 px width.
