# Charts and Benchmarks

Choose the layout, sections and chart types that fit the data and what the user asked for. Nothing here is a required structure; the user steers the shape of each page. The patterns below are options that have worked well, not a template.

## Honest numbers

- Use only real data the user gave you or you measured. Never invent or smooth values.
- Show uncertainty as a range, labelled "59–107%", not as a midpoint.
- Draw reference lines for meaningful thresholds, such as 100% of a limit, and label them on the axis.
- Bar lengths must be proportional to the values. Start bar axes at zero.
- Say how scores were produced, such as judges, criteria and averaging, and give counts behind rates ("2 of 42").

## Patterns that work

**Horizontal bars, for comparing a few values:**
- A range can be a solid bar for the lower estimate plus a hatched extension up to the upper one.
- Put the row label and a muted sublabel (a date range or setting) on the left, the bar in the middle, and the value right-aligned in large type.
- Give the bars fixed heights and build them as HTML (a track with a filled child at `width: N%`). They stay crisp and reflow on phones.
- Hatch a range with `repeating-linear-gradient(-45deg, var(--c1) 0 3px, transparent 3px 7px)`.

**Stacked columns, for composition:**
- Put the total above the column, the main segment's value and name inside it in a contrasting color, and the period below.
- Use `--c4` or `--surface` for "other", so the highlighted segment stands out.

**Ranking tables, for benchmarks:**
- Columns: rank, name with a muted secondary line (harness, version, setting), the settings that differ, the score with an inline bar, then supporting metrics such as error rate, time and tokens.
- Sort by the primary score. Right-align numbers with `font-variant-numeric: tabular-nums`.
- Color names by group (vendor, team) with a legend underneath.
- Mark a bad outlier with `--bad` on the offending cells only.
- Write "n/a" for missing data and say why on the page.

**Growth lines, for progress over time:**
- Pair the line with a very large current value and one line of deltas ("2x in 43 days · +42.8K in the last 7 days").
- Draw it in inline SVG with a fixed pixel height, a `viewBox`, `preserveAspectRatio="none"` and `vector-effect: non-scaling-stroke`. Under the line, fill a faint gradient of the line color.
- Annotate milestones on the line itself with a dot, a bold value and a muted date. Add dashed drop lines to the axis, with the interval between milestones ("22 days") in muted text along the axis.
- Highlight only the latest point with the accent color.
- Position text in HTML over the SVG, not in the SVG itself, so it doesn't stretch with the chart.

## Type and color

- Headings use `--font` at weight 700 with slightly tight letter spacing. Numbers use the same font at large sizes, with `tabular-nums` wherever they line up in columns.
- Body text is `--fg`. Labels, sublabels, axis text and captions are `--dim`.
- Assign series colors in order from `--c1` and keep each series' color across every chart on the page.
- Use one accent for what matters most. Don't add decorative color.
- Size the type with `clamp()`, so a 728px reply column and a 360px phone both work. On narrow screens, stack side-by-side charts and let wide tables scroll horizontally inside their own container.

## Check before publishing

- Every number on the page matches the source data, and totals add up.
- Nothing overflows at 360px wide.
