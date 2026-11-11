---
name: html-communication
description: Write a standalone HTML page that presents a report, quick report, audit, plan, spec, write-up, summary, comparison, chart, benchmark or UI mocks, and publish it only after Donald confirms. Use whenever the user asks for HTML, a page or a visual report to read or share, even when they don't name this skill.
metadata:
  harness: [claude, codex]
  platform: [darwin, linux]
  scope: fleet
  requires: "npx (postplan is run via npx), Helium (renders the X image)"
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

## Words

Every line of text states a fact from the work. Cut any text that brands the page, labels it or introduces it.

### ✅ DO

- Open the page with the headline. It states the main result in plain words with its number, such as "Cold start is 2x faster."
- Name each section by what it contains, in two to four plain words: "Results", "How it works", "Not changed".
- Keep code identifiers in their real case, such as `useMemo` and `u64`, even inside uppercase labels.

### ❌ DON'T

- Don't put an eyebrow, kicker, product name, tagline or category tag above or beside the headline. "Acme | THE ALL-IN-ONE WORKSPACE", "Acme | PERFORMANCE" and "// What changed and why it matters" are all banned.
- Don't mention the PR, its number, title, branch or commit unless Donald asks.
- Don't write jokes, slogans, punchlines, teasers or clever section headings, such as "Fast was never fast enough." or "What we left on the table".
- Don't prefix headings or labels with `//`, `#`, numbers or other decoration.

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

- **Headline:** `--font`, weight 700, `line-height: 1.05`, `letter-spacing: -.035em`, `font-size: clamp(32px, 5.5vw, 80px)`. Color the key figure `--accent`. A second line can drop to `--muted`.
- **Section heading:** `--font`, weight 600, `--fg-2`, sentence case.
- **Lede:** `--font`, `clamp(16px, 1.8vw, 28px)`, `--body`. Inline code sits in a `--surface-2` chip with a `--rule` border and `--radius`.
- **Panel title:** `--mono`, uppercase, `letter-spacing: .15em`, `--fg-2`, in a `--surface-2` header row with its qualifier ("lower is better") right-aligned in `--dim`.
- **Row label:** `--font` in `--fg-2`, followed by a smaller sublabel in `--dim`.
- **Values and deltas:** `--mono`; deltas in `--accent` (or `--bad` when worse), neutral notes like "baseline" in `--dim`.
- **Footnote:** `--mono`, small, `--faint`, with key numbers lifted to `--body`. Put the method and hardware there.

### Surfaces

- Panels are `--surface` with a 1px `--rule` border and `--radius`; their header row is `--surface-2` with a `--rule` bottom border.
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
3. Ask two questions in one call to the harness's question tool, such as Claude Code's `AskUserQuestion` or Codex's `request_user_input`: whether to publish it to Postplan, and whether to make a version to post on X (see Post on X). Ask the second one every time; the full page is usually too long for one image. Without a question tool, ask both in the reply and stop.
4. Only after Donald confirms, run `npx postplan upload <file path>` and report the returned URL. Otherwise, report the local path.
5. If he wants the X version, build and render it as described below.

Re-upload the same absolute path to update the existing URL. Use `npx postplan upload <file path> --new` only when a new draft is wanted.

If validation fails, fix the markup and retry. If a scripted upload needs authentication, ask the user to run `postplan auth login`, then retry without removing the requested interactivity.

### ❌ DON'T

Never upload without confirmation, open a browser, or claim the document is hosted before upload succeeds. Do not verify in a browser unless the user asks. A harness's own HTML preview tool is fine for checking charts.

## Post on X

The X version is a separate 1600×900 image that tells the page's main point on its own. Don't screenshot the full page or shrink it to fit.

### ✅ DO

- Write it as a second file next to the page, named `<page>-x.html`, with a fixed `1600px` × `900px` body, `overflow: hidden` and the Look tokens. The fixed size replaces the mobile-readable rule for this file only.
- Use the page's headline word for word. Don't write a new one for the image, and don't swap in a PR title or a post caption.
- Under the headline, keep only the one chart, table or three to five rows that prove it, and a footnote with the source or method. Leave out sections, prose and secondary charts. The Words rules apply here too.
- Size for a phone timeline, where X shows the image at about a quarter of its width: headline at least 72px, every other text at least 28px, padding at least 64px. If the content doesn't fit at those sizes, cut more instead of shrinking it.
- Render it with headless Helium (Chromium), using a profile in the scratch folder so it doesn't touch the running browser:

  ```sh
  helium=/Applications/Helium.app/Contents/MacOS/Helium  # Linux: /usr/bin/helium-browser
  "$helium" --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --user-data-dir="<scratch dir>/helium-x" --window-size=1600,900 \
    --screenshot="<page>-x.png" "file://<absolute path>/<page>-x.html"
  ```

- Look at the PNG before reporting it. Fix clipped text, overflow and empty areas, then render again. Report the PNG's absolute path.

### ❌ DON'T

Don't upload the X version to Postplan unless Donald asks; the PNG is what he posts. Don't post to X yourself.
