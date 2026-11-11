---
version: 1
slug: "build-py"
primary_target: "build.py"
related_targets: ["assets/style.css","assets/print.css"]
---

# Surface brief: the CV site (all pages rendered by build.py)

Scope: About (home), CV, Publications, Portfolio, and cv/print.html (PDF). Visitor mode: Read. Build path: code-led.

Audience and job: a hiring manager, interviewer or recruiter, often on a phone, deciding within a minute whether to
talk to Woojune Park, then reading in depth; and ATS, crawlers and LLMs parsing the same HTML and PDF.
Content: only data/cv.json. Constraints: no JavaScript, standard library build, English, WCAG AA, 320 px.
Confirmed with the owner: identity = 3D vision x AI agents, a research engineer who carries research to product.
The owner rejected the first build (a to-scale career route map): it gave length to unimportant years, squeezed
recent work into a corner and emphasised nothing. Importance, not chronology, sets size and position. The owner then
chose mockup A (Swiss grid) from three full-content mockups. Project order follows the data file.

## Direction contract

THESIS: The work is the poster. The name and the results are set large on a strict grid; what matters most is biggest
and first. Refuses the chronological CV, the academic sidebar page and decoration of any kind.

OWN-WORLD: Swiss International Style poster. Poster-white ground, black grotesk (Archivo), one red used only for the
current page, the current role, the AI agents code and hover. A 6px black rule opens every band; a label column on
the left names the band and the content sits on columns 4 to 12. Hairlines separate rows. No shadows, no rounded
corners, no cards, no gradients. Diagrams are drawn in the same black, white and red.

STORY: The visitor reads the name and current role, sees what was built and its results in a few large sentences
with a figure each, then the publications, then opens the CV or a paper.

FIRST VIEWPORT: Top bar with name, four page links and CV (PDF) over a heavy rule. The name at display size across
nine columns, the portrait in grayscale on the right three. Below: the current role with a red dot and the links in
the label column, the opening sentence at lede size beside it. Selected work begins under the next heavy rule.

FORM: Swiss grid poster wall, a dealt challenger that beat the assigned grounded direction on audience identification
and product clarity (catalog id design-canon-swiss-grid-poster-wall); seed:83641f7afecba661, re-roll 1. Signature:
result sentences set as large bold lines under a 2px rule beside each project's figure. Motion: none.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
