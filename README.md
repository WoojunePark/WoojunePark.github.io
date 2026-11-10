# woojunepark.github.io

Personal CV site: https://woojunepark.github.io

## How it updates

```
final-offer (private)                         this repository (public)
wiki/candidate/records/*.md  (claims)
channels/cv-site/site.yaml   (presentation)
channels/cv-site/assets/pubs (figures)
        │ push to main
        ▼
publish-cv-site.yml: final-offer site export ──► data/cv.json + assets/pubs/ ──► deploy.yml: build.py --pdf ──► GitHub Pages
  (refuses unsourced, internal or unverified                       HTML pages + files/CV_Woojune_Park_<Mon><YYYY>.pdf
   claims and numbers the claims do not hold)                      + files/cv.pdf (stable link)
```

- Content is edited in the private repository, not here. `data/cv.json` is generated; do not hand-edit it.
- `assets/pubs/` (publication figures) is also generated: the publish workflow copies the figures `cv.json` references
  from the private repository and removes the rest. Do not add or rename files there by hand.
- Publications page: per paper a one-line summary, keywords, the abstract (collapsed) and up to two figures with alt
  text, caption, credit and source. CV page and PDF: summary and keywords only. Both pages carry schema.org JSON-LD
  (`ScholarlyArticle`) for crawlers. `build.py` reads both `figures` (list) and the older single `figure`.
- `updated` (shown on the pages and in the PDF file name) changes only when the exported content changes.
- Joint first authors carry `#`, explained by the note "# these authors contributed equally to this work".
- Layout and style live here: `build.py` (standard library only), `assets/`.

Local preview: `python build.py --pdf` (needs Chrome or Edge; set `CHROME` if it is not found), then open `_site/index.html`.

The previous Jekyll blog (2019) is kept on the `legacy-2019-blog` branch.
