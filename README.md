# woojunepark.github.io

Personal CV site: https://woojunepark.github.io

## How it updates

```
final-offer (private)                         this repository (public)
wiki/candidate/records/*.md  (claims)
channels/cv-site/site.yaml   (presentation)
        │ push to main
        ▼
publish-cv-site.yml: final-offer site export ──► data/cv.json ──► deploy.yml: build.py --pdf ──► GitHub Pages
  (refuses unsourced, internal or unverified                       HTML pages + files/CV_Woojune_Park_<Mon><YYYY>.pdf
   claims and numbers the claims do not hold)                      + files/cv.pdf (stable link)
```

- Content is edited in the private repository, not here. `data/cv.json` is generated; do not hand-edit it.
- `updated` (shown on the pages and in the PDF file name) changes only when the exported content changes.
- Joint first authors carry `#`, explained by the note "# these authors contributed equally to this work".
- Layout and style live here: `build.py` (standard library only), `assets/`.

Local preview: `python build.py --pdf` (needs Chrome or Edge; set `CHROME` if it is not found), then open `_site/index.html`.

The previous Jekyll blog (2019) is kept on the `legacy-2019-blog` branch.
