---
name: html-communication
description: Use when the user asks to communicate through an HTML document, including charts, benchmarks and metric reports, or if they mention "HTML" with no additional context.
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

- Write it like a spec, not a landing page: dense, scannable, no hero, decorative chrome, marketing voice, or em dashes. A chart page may lead with one large number when that number is the answer.
- Take every color and font from the theme tokens below.
- Make it mobile-readable with a responsive viewport and no fixed-width layout.
- Use semantic HTML, inline CSS, inline SVG, and HTTPS or data-URL images.
- Use an inline classic script only when interactivity materially helps. Keep scripted pages useful without JavaScript; the sandbox blocks storage, fetch, workers, frames, forms, and popups.
- In script-free files, give external links `target="_blank"` and `rel="noopener noreferrer"`. If any script exists, omit `target="_blank"`.

### ❌ DON'T

Never include external or module scripts, inline event handlers, `javascript:` URLs, forms, frames, embeds, objects, applets, meta refresh, linked stylesheets, secrets, private URLs, or local filesystem paths.

## Theme

Some harnesses show HTML inline and inject their active theme as CSS custom properties on `:root`, such as `--background`, `--foreground` and `--chart-1` to `--chart-6`. The harness's HTML tool description lists them. Map them to your own tokens with a fallback, so the same file matches the harness theme inline, including light mode, and uses the black palette everywhere else, including Postplan:

```css
:root {
  --bg: var(--background, #000);
  --fg: var(--foreground, #fff);
  --dim: var(--muted-foreground, #8a8a8a);
  --rule: var(--border, #2a2a2a);
  --surface: var(--card, #111);
  --c1: var(--chart-1, #f0712c);
  --c2: var(--chart-2, #3b8ee8);
  --c3: var(--chart-3, #23a878);
  --c4: var(--chart-4, #d4d4d4);
  --c5: var(--chart-5, #a78bfa);
  --c6: var(--chart-6, #e5c07b);
  --good: var(--success, #23a878);
  --bad: var(--destructive, #f0574a);
  --font: var(--font-sans, -apple-system, BlinkMacSystemFont, "Inter", system-ui, sans-serif);
  --mono: var(--font-mono, ui-monospace, "SF Mono", Menlo, monospace);
}
html { background: var(--bg); color: var(--fg); font-family: var(--font); }
```

Use only these tokens in the rest of the CSS. Never hardcode a color that assumes a dark background, because the harness theme may be light.

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

Donald has given standing permission to upload every artifact created or updated with this skill. Upload is required, including in Auto mode. Do not ask for separate permission or stop at the local file.

### ✅ DO

1. Write the HTML file locally.
2. Run `npx postplan upload <file path>`.
3. Report the local path and returned Postplan URL.
4. If the harness has a tool that shows HTML inline in the conversation, also show the same file there, following that tool's layout rules. It is the only place the harness theme applies.

Re-upload the same absolute path to update the existing URL. Use `npx postplan upload <file path> --new` only when a new draft is wanted.

If validation fails, fix the markup and retry. If a scripted upload needs authentication, ask the user to run `postplan auth login` — then retry without removing the requested interactivity.

### ❌ DON'T

Never open a browser or claim the document is hosted before upload succeeds. Do not verify in a browser unless the user asks. A harness's own HTML preview tool is fine for checking charts, in both light and dark when it offers both.
