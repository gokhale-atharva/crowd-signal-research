# Current design system

See [DESIGN.md](../DESIGN.md) for the current spatial research workspace and
[PRODUCT.md](../PRODUCT.md) for the confirmed product brief.

Revised2026-11-08 following the explicit request for visible Motion animation and real3D.
The composition now uses a slim navigation rail, compact exchange/mode header,
perspective company selector, a data-driven Three.js price surface and a lime estimate
inspector. The long introduction and empty metric strip are no longer visible.

Motion14.10.1 drives the scene reveal, staged entrance, company changes and card feedback.
Three.js0.160.1 supplies material, perspective, lighting, orbit and a geometry-based price
surface. The regular Plotly OHLC/sentiment/backtest views remain available. Both libraries
are embedded under their retained MIT licences; the page remains a portable HTML file.

The3D view is illustrative: exact chart axes are in OHLC. Continuous camera movement has
an explicit pause, keyboard/button orbit controls, reset, reduced-motion behavior, pixel-ratio
and frame caps, geometry disposal, and offscreen/hidden-tab suspension. Missing WebGL shows
an OHLC recovery action. Mobile retains native page scrolling and a horizontally scrollable
company selector. No decorative effect changes the prices or implies a streaming feed.

UI/UX Pro Max's broad query returned an irrelevant enterprise gateway pattern; it was
rejected. A focused style query verified Data-Dense Dashboard guidance. Impeccable context
and animation/craft references, Taste Skill motion guidance, the supplied video prompts,
Skiper UI and Vengeance UI informed the revision. Read design_references.md for provenance.
