# BidDelta: procurement amendment review bench

Audience: supplier bid managers protecting already-approved work when a tender changes.
Primary job: connect the official change to its evidence and affected tasks, then apply a version-checked plan while retaining a colleague's work.

## Visual plan
- Procurement blue #143D96: app rail and action. Paper white #FFFFFF: evidence. Ledger grey #EDF1F7: workspace. Ink #172641: body. Decision amber #C67913: stale plan and missing guidance. Retention teal #19746B: unchanged assets.
- Type: IBM Plex Sans for practical procurement copy; IBM Plex Serif for the historical deadline movement. Use locally bundled fonts if available, with sans/serif fallbacks. No detached number cards.
- Left aligned, wide desktop review bench with a compact blue brand rail; the tender title and old/new deadline form one decisive banner. Evidence occupies the left column; a connected task list occupies the right. A persistent full-width action footer contains exactly the next executable action.

```
[BidDelta | South Norfolk / CRM                         Zetaris connected]
[2 Dec, 12:00  ------------------- 9 Dec, 16:00           3 changes]
[Official amendment evidence       | Five affected tasks + retained T6]
[ C1 / C2 / C3                     | T1 ... T5 / version / proposal  ]
[ Sources, SQL and provenance      | Shared missing guidance         ]
[Run source query -> teammate edit -> version check -> refresh -> apply]
```

Principles: evidence is the visual anchor, document collection is one shared dependency, and a blocked batch shows zero writes in the same place as an eventual successful receipt. Task identifiers and version markers carry actual state. Status changes answer user actions; the screen has no autonomous animation.

## Brief review
A uniform KPI-card layout would conceal the chain from clause to task. Replaced it with an evidence/task split and one deadline banner. Boldness is concentrated in the large old/new deadline; source facts, missing files and retained work have quiet row-based treatments. Historical public notice facts and illustrative supplier records are labeled once at the tender header and at source references.

## Public film & watch page

Audience: a supplier bid manager and the Demo Challenge's reviewing judges. Lead with the real deadline correction, then the recorded stale-stop/fresh-apply result. Reuse the bench's institutional blue `#143D96`, navy `#17304F`, white `#FFFFFF`, document pale blue `#EDF2FB`, and retained-work green `#24654F`; IBM Plex Sans for interface/body and Plex Serif for the tender headline. A single large film sits below a short two-date headline, followed by the chronological replay and direct source/receipt links. Left-aligned, no dashboard metrics or extra feature sections. The film's blue document frame gives the genuine workbench most of the image; scene-specific callouts identify the action, and captions have a dedicated strip below the controls. The source/workspace/narrator distinctions remain visible in the page and credits. Review: this visual hierarchy follows a dated procurement decision and its actual evidence, and matches the existing bench.

Film implementation: the recorded bench and watch page retain Plex. Frame titles and captions reuse the supplied getting-started site's Plus Jakarta Sans TrueType file, keeping the encode independent of WOFF2 conversion dependencies.
