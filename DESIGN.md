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
An interaction-driven/reduced-motion-aware rendering loop is capped at30fps, with limited pixel ratio,
resource disposal on asset changes and offscreen/hidden-tab suspension. The materialized
price surface uses actual selected-period closes; blue background bars show sampled volume.
3D perspective is illustrative; OHLC preserves exact axes and candles.

There are left/right orbit controls, keyboard arrows and a WebGL
fallback to OHLC. Mobile keeps native page scrolling and a compact company dropdown.
Read docs/design_references.md for inspected references, licensing and constraints.


The landing page uses the same palette in a different composition: large two-line typography
opposite a material 3D stack. Price, crowd and model layers link to dedicated pages. A deliberate
entrance reveals the headline and scene; an explicit control separates/reassembles the stack.
Pointer/keyboard rotation, reduced-motion and static fallback keep it usable.
Landing copy: “Price is only the first layer.” Cards ask visitors to follow price, check sources
or inspect the model record. A real saved-price sparkline and actual validation errors make
those destinations concrete. Ten company links provide direct entry.

Research pages share a visible page bar and active state. Header navigation changes URLs;
company cards and the phone selector open company pages. A company's return link retains
its exchange/mode. The methodology page avoids downloading datasets, Plotly and Three.js.
Shared assets cache across the remaining pages. All links also work in the exported folder.

## Source-availability revision

The chart's unavailable state includes an explicit recovery action and a source-status link,
following the UI/UX Pro Max Empty States / Error Recovery guidance. It keeps the saved-price
line visible; it does not fill a missing sentiment series. The existing dark/cobalt/lime design,
Motion feedback and separate-page architecture remain. Source status uses text as well as
colour, and its wide table is keyboard/touch scrollable on phones.

## Focused explorer revision — 2026-11-13

The user removed Reset and Pause from the brief. Both landing and research pages now omit
those controls. Scene entrances and state transitions finish; idle scenes do not bob or
rotate automatically. Rendering stops once pointer/camera motion settles. OS reduced motion,
keyboard orbit, ordinary chart views and WebGL fallback remain.

The hero replaces three floating destination labels plus a boxed dock with one sliding
acid-lime layer selector and an open readout. The selected 3D plate responds to the same
state, and the larger stack remains the focal scene. The destination grid now features
prices in a tall left panel, with source and model links stacked on the right; phones stack
them vertically. Research pages use a continuous five-company strip, rounded chart controls,
a flat saved-close readout and a compact two-button orbit tool.
