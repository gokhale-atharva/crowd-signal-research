# Spatial research design

A compact research app with a narrow persistent navigation rail, exchange/mode controls
in the header, a five-company perspective selector, and a data-driven 3D price surface
next to a contrasting acid-lime estimate inspector. The primary visual is the data itself.
The old large editorial introduction and empty metric strip are removed from the visible layout.

Tokens: near-black #08090E; raised #11141D; cobalt #3254E6; acid lime #D6F769;
primary text #F2F3F8; secondary #9CA4B6. Local system fonts preserve offline portability.
The palette follows the user's standing preference; the current brief selects 3D and motion.

Motion uses the installed Motion 14.10.1 browser runtime: staged entry, selected-company
changes, perspective card feedback and numerical progress driving the Three.js reveal.
Three.js 0.160.1 is vendored under MIT for a self-contained classic-script report.
One paused/reduced-motion-aware rendering loop is capped at30fps, with limited pixel ratio,
resource disposal on asset changes and offscreen/hidden-tab suspension. The materialized
price surface uses actual selected-period closes; blue background bars show sampled volume.
3D perspective is illustrative; OHLC preserves exact axes and candles.

There is an explicit pause control, left/right/reset controls, keyboard arrows and a WebGL
fallback to OHLC. Mobile keeps native page scrolling and a compact company dropdown.
Read docs/design_references.md for inspected references, licensing and constraints.


The landing page uses the same palette in a different composition: large two-line typography
opposite a material 3D stack. Price, crowd and model layers link to dedicated pages. A deliberate
entrance reveals the headline and scene; an explicit control separates/reassembles the stack.
Reset, pointer/keyboard rotation, pause, reduced-motion and static fallback keep it usable.
Landing copy: “Price is only the first layer.” Cards ask visitors to follow price, check sources
or inspect the model record. A real saved-price sparkline and actual validation errors make
those destinations concrete. Ten company links provide direct entry.

Research pages share a visible page bar and active state. Header navigation changes URLs;
company cards and the phone selector open company pages. A company's return link retains
its exchange/mode. The methodology page avoids downloading datasets, Plotly and Three.js.
Shared assets cache across the remaining pages. All links also work in the exported folder.
