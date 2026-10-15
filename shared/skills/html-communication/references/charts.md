# Charts and Benchmarks

A chart page answers one question. Everything on it should help the reader get that answer, check it, and see how sure it is.

## Page structure

1. **Title as the question:** "Can I run Opus full-time on one Max account?", "Which model understands this codebase best?"
2. **Answer line:** a short verdict word in an accent color, then the key numbers in bold: "**Close.** My workload uses **59–107%** of one weekly limit." For a single metric, a very large number can be the answer instead: "400,000 users".
3. **Charts:** one to three, each with a short bold heading that says what it measures, and a legend only when color or pattern carries meaning.
4. **Stat row (optional):** three or four large numbers, each with a one-line caption. Use bold in the caption for the unit that matters ("per **1% of the weekly limit**").
5. **Footnote:** source, date range, timezone, method and caveats, in small muted monospace. State what was excluded and which numbers are estimates.

Separate sections with thin rules in `--rule`, not cards or boxes.

## Honest numbers

- Use only real data the user gave you or you measured. Never invent or smooth values.
- Show uncertainty as a range: a solid bar for the lower estimate and a hatched extension up to the upper one. Label it "59–107%", not a midpoint.
- Draw reference lines for meaningful thresholds, such as 100% of a limit, and label them on the axis.
- Bar lengths must be proportional to the values. Start bar axes at zero.
- Say how scores were produced, such as judges, criteria and averaging, and give counts behind rates ("2 of 42").

## Chart types

**Horizontal bars, for comparing a few values:**
- Put the row label and a muted sublabel (a date range or setting) on the left, the bar in the middle, and the value right-aligned in large type.
- Give the bars fixed heights and build them as HTML (a track with a filled child at `width: N%`). They stay crisp and reflow on phones.
- Hatch a range with `repeating-linear-gradient(-45deg, var(--c1) 0 3px, transparent 3px 7px)`.

**Stacked columns, for composition:**
- Put the total above the column, the main segment's value and name inside it in white, and the period below.
- Use `--c4` or `--surface` for "other", so the highlighted segment stands out.

**Ranking tables, for benchmarks:**
- Columns: rank, name with a muted secondary line (harness, version, setting), the settings that differ, the score with an inline bar, then supporting metrics such as error rate, time and tokens.
- Sort by the primary score. Right-align numbers with `font-variant-numeric: tabular-nums`.
- Color names by group (vendor, team) with a legend underneath.
- Mark a bad outlier with `--bad` on the offending cells only.
- Write "n/a" for missing data and explain it in the footnote.

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
- Use one accent for the verdict and the highlighted point. Don't add decorative color.
- Size the type with `clamp()`, so a 728px reply column and a 360px phone both work. On narrow screens, stack side-by-side charts and let wide tables scroll horizontally inside their own container.

## Check before publishing

- Every number on the page matches the source data, and totals add up.
- The page reads correctly in the harness's light and dark themes and in the black fallback.
- Nothing overflows at 360px wide.
