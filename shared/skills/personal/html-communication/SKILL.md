---
name: html-communication
description: Use when the user asks to communicate through an HTML document.
metadata:
  harness: [claude, codex]
  platform: [darwin, linux]
  scope: fleet
  requires: "npx (postplan is run via npx)"
---

# HTML Communication

## When to Use

### ✅ DO

Use this skill when the user wants a plan, spec, write-up, findings, summary, report, comparison, chart, benchmark, or set of UI mocks presented as readable HTML.

### ❌ DON'T

Do not use it for HTML that ships as part of a product.

## Document

Create one self-contained HTML file, capped at 512 KB.

### ✅ DO

- Write it like a spec, not a landing page: dense, scannable, no hero, decorative chrome, marketing voice, or em dashes. Large numbers are fine on data pages when they carry the answer.
- Prefer charts, tables and short labelled rows over paragraphs. Keep each block of prose to a few sentences; a wall of text defeats the point of a visual page.
- Take every color, font and the page padding from the Look tokens below.
- Make it mobile-readable with a responsive viewport and no fixed-width layout.
- Use semantic HTML, inline CSS, inline SVG, and HTTPS or data-URL images.
- Use an inline classic script only when interactivity materially helps. Keep scripted pages useful without JavaScript; the sandbox blocks storage, fetch, workers, frames, forms, and popups.
- In script-free files, give external links `target="_blank"` and `rel="noopener noreferrer"`. If any script exists, omit `target="_blank"`.

### ❌ DON'T

Never include external or module scripts, inline event handlers, `javascript:` URLs, forms, frames, embeds, objects, applets, meta refresh, linked stylesheets, secrets, private URLs, or local filesystem paths.

## Look

Every page uses this fixed look wherever it is shown: near-black zinc surfaces, white and zinc text, one green accent, Inter for prose and a monospace for labels. Restyle the skill by editing these values here, not per page.

```css
:root {
  --bg: #09090b;
  --surface: #0c0c0e;
  --surface-2: #121214;
  --rule: #27272a;
  --grid: #18181b;
  --fg: #fafafa;
  --fg-2: #e4e4e7;
  --muted: #d4d4d8;
  --body: #a1a1aa;
  --dim: #71717a;
  --faint: #52525b;
  --accent: #86efac;
  --bar: #3f3f46;
  --c1: #86efac;
  --c2: #7dd3fc;
  --c3: #fcd34d;
  --c4: #c4b5fd;
  --c5: #fda4af;
  --c6: #a1a1aa;
  --good: #86efac;
  --bad: #fca5a5;
  --font: "Inter", -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
  --mono: "JetBrains Mono", "Geist Mono", ui-monospace, "SF Mono", Menlo, monospace;
  --pad: clamp(20px, 5vw, 96px);
  --radius: 6px;
}
html { background: var(--bg); color: var(--fg); font-family: var(--font); }
body { margin: 0; padding: var(--pad); }
```

Use only these tokens in the rest of the CSS. Don't map them to a harness's theme variables.

### Type

- **Eyebrow:** `--mono`, uppercase, `letter-spacing: .2em`, `--dim`, prefixed with `// `.
- **Headline:** `--font`, weight 700, `line-height: 1.05`, `letter-spacing: -.035em`, `font-size: clamp(32px, 5.5vw, 80px)`. State the answer in it; color the key figure `--accent`. A second line can drop to `--muted`.
- **Lede:** `--font`, `clamp(16px, 1.8vw, 28px)`, `--body`. Inline code sits in a `--surface-2` chip with a `--rule` border and `--radius`.
- **Panel title:** `--mono`, uppercase, `letter-spacing: .15em`, `--fg-2`, in a `--surface-2` header row with its qualifier ("lower is better") right-aligned in `--dim`.
- **Row label:** `--font` in `--fg-2`, followed by a smaller sublabel in `--dim`.
- **Values and deltas:** `--mono`; deltas in `--accent` (or `--bad` when worse), neutral notes like "baseline" in `--dim`.
- **Footnote:** `--mono`, small, `--faint`, prefixed with `// `, with key numbers lifted to `--body`. Put the method and hardware there.

### Surfaces

- Panels are `--surface` with a 1px `--rule` border and `--radius`; their header row is `--surface-2` with a `--rule` bottom border.
- A thin header can carry the subject on the left (name, a 1px `--rule` divider, a `--mono` uppercase tag) and the exact command or setting in a bordered `--mono` chip on the right.
- Faint 1px `--grid` vertical guide lines may mark the content edges and center. Nothing else is decorative: no gradients, glows or shadows.

## Charts and Benchmarks

Read `references/charts.md` before building a chart, benchmark table or metric page.

## UI Mocks

When the user asks for variants:

### ✅ DO

- Render real styled variants, not descriptions.
- Label them `A`, `B`, `C`... for easy selection.
- Lay them out for direct comparison.
- Keep one file across iterations so its Postplan URL stays stable.

## Publish

Publishing to Postplan makes the page reachable by URL, so it needs Donald's confirmation every time, including for re-uploads of an already published file and in Auto mode.

### ✅ DO

1. Write the HTML file locally.
2. If the harness has a tool that shows HTML inline in the conversation, show the file there with the palette and padding above.
3. Ask whether to publish it to Postplan with the harness's question tool, such as Claude Code's `AskUserQuestion` or Codex's `request_user_input`. Without a question tool, ask in the reply and stop.
4. Only after Donald confirms, run `npx postplan upload <file path>` and report the returned URL. Otherwise, report the local path.

Re-upload the same absolute path to update the existing URL. Use `npx postplan upload <file path> --new` only when a new draft is wanted.

If validation fails, fix the markup and retry. If a scripted upload needs authentication, ask the user to run `postplan auth login`, then retry without removing the requested interactivity.

### ❌ DON'T

Never upload without confirmation, open a browser, or claim the document is hosted before upload succeeds. Do not verify in a browser unless the user asks. A harness's own HTML preview tool is fine for checking charts.
