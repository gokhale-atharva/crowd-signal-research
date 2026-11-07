# Crowd Signal · Research desk

Revised 2026-11-07 after the user rejected the first preview's generic dashboard treatment.

## Direction

A compact exchange research desk. Show the five configured assets, evidence availability,
and the selected company's search coverage in the first view. Use publication hierarchy:
a masthead, exchange name, numbered sections, hairlines, aligned data and marginal notes.
Remove the marketing slogan, glowing diagram, repeated metric cards, monogram avatars
and dashboard sidebar. The exchange name is the title.

Keep the user's midnight / cobalt / acid-lime palette. Midnight is the canvas,
cobalt identifies the selected-asset inspector, and lime marks active controls.
Lime never implies live-data availability. All absent data remains explicitly unavailable.

## Skill and component research

UI/UX Pro Max queries for this revision:

- `financial research terminal --design-system`: Swiss Modernism 2.0 and institutional
  research typography. Adopt its modular/asymmetric grid. Discard its portfolio conversion pattern.
- `Swiss editorial typography --domain style`: Editorial Grid / Magazine and Minimalism
  & Swiss Style. Adopt rules, deliberate whitespace and clear type hierarchy.
- `financial editorial serif --domain typography`: Financial Trust and editorial serif/mono
  pairings. Use Georgia for the exchange title, Bahnschrift / Segoe UI for interface text,
  and Consolas for IDs and numbers. These system fonts preserve offline portability.

Inspected [Financial Markets Table](https://21st.dev/@isaiahbjork/components/financial-markets-table)
and [Project Data Table](https://21st.dev/@ravikatiyar162/components/project-data-table).
Both use React/Tailwind and list Framer Motion; the financial component also lists
next-themes. Component source requires an account and no verified license was exposed.
No component source is integrated. All report markup/CSS/JS is original. The reel itself
could not be fetched in this session; the user's previously reviewed workflow notes apply.

## Tokens and composition

| Role | Value |
| --- | --- |
| Midnight canvas | `#10120F` |
| Secondary surface | `#171A16` |
| Primary ink | `#EAEDE4` |
| Supporting ink | `#A6AC9F` |
| Hairline | `#3B4137` |
| Cobalt inspector | `#2548E8` |
| Acid-lime accent | `#D6F769` |
| Negative status | `#FF9C9C` |

Values are implementation choices, not transcribed reel hex codes. Georgia exchange
names use 64px desktop / 46px phone. UI text uses 14–16px with 12px supporting labels.
Numbers and ticker IDs use tabular monospace. No shadows, gradients, blur or pill badges.
Borders are square. Whitespace follows an 8px rhythm with a 4px sub-step.

The desktop table and asset inspector occupy an asymmetric 8/4-column composition.
Below 1000px the inspector follows the table. At phone widths only the table's labeled
region scrolls horizontally; the page itself stays within the viewport. Masthead and
exchange controls wrap. Session time, currency and lookback are configuration metadata,
not performance metrics. The complete watchlist starts near the top of the page.

## Interaction and motion

Native exchange buttons expose selection. Asset buttons update a persistent inspector.
Search accepts ticker/name/local aliases; sorting uses a native select. The inspector
supports copying the configured search terms and exporting the selected asset.
Source and method sections use real anchor links. Method details use native disclosure.

Use CSS transitions for selection feedback and a short opacity/6px reveal for the
changed inspector. These effects do not need JavaScript animation, so Motion is not
installed. Use the motion package when complex JavaScript animation is introduced.
Honor reduced motion, visible focus, semantic labels and keyboard operation.

## Content

No invented price series or sentiment. Unavailable numbers remain em dashes. Explain
availability once beside the table. Surface the distinction between a listed actor,
a verified social source and an actual model result. Keep implementation commands
in documentation rather than the primary research flow.
