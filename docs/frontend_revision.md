# Frontend revision · 2026-11-07

The first preview was rejected for its generic dashboard appearance. This revision
replaces the presentation while retaining the existing pipeline checkpoint.

## Result

- A publication-style masthead, exchange title and compact session metadata.
- A table-led research universe in place of the slogan, diagram and repeated stat cards.
- A persistent selected-company inspector with actual configured aliases, collection
  state, copy action and per-company export.
- A source ledger and native research-note disclosures.
- Midnight background, cobalt inspector and selective lime active states; square rules,
  serif exchange titles, readable sans UI and monospaced identifiers.
- Phone selection brings the inspector into view and moves focus to its heading;
  the return control restores focus to the selected row.
- Exchange local names and timezone labels now come from YAML, using optional fields
  so existing custom configurations remain valid.

## Workflow evidence

The exact UI/UX Pro Max queries and adopted/discarded recommendations are recorded
in `design_system.md`. The 21st.dev Financial Markets Table and Project Data Table
were inspected: React/Tailwind with Framer Motion, and next-themes for the financial
component. Source requires an account and its license was not verified, so no source
was integrated. CSS handles the simple transitions and inspector entrance; the Motion
package is not installed. The Instagram reel could not be fetched; the user's
previously reviewed instructions remain the workflow requirements.

## Validation

36 existing tests pass; Ruff lint and formatting pass. Browser checks cover company
selection, alias copying, Chinese/Korean search, empty results, sorting, source/notes
navigation, keyboard disclosure and phone focus/return behavior. Checked 375, 768,
1024 and 1440px layouts; no page-wide horizontal overflow. The data table scrolls
within its own region. No browser JavaScript errors were observed. Screenshots in
`docs/img/` and README now show the revised design.

No live scraping or statistical results were added. This remains a milestone 1
research preview, with deliberately unavailable market values.
