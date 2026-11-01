# Stageshow

A skill and a small React kit for product illustrations, cursor stories, and
motion design. Start with `SKILL.md`; follow its links for the task at hand.

## Preview

Requires Node 20.19 or later and Vite+ (`vp`), which supplies Vite. From this folder:

```sh
vp install
vpr dev
```

Open the local URL it prints (normally **http://127.0.0.1:5173**).

The playground includes the gold
examples, nine visual styles, and labeled bad/good teaching pairs.
Pause, replay, slow down, or advance one frame. Phone changes the available
width to 358px; Reduced motion shows each scene's still. The viewer and its
controls stay outside the example's isolated clock.

## Use the kit

Copy `kit/` into your React project. Its components import their own CSS:

```tsx
import { Stage, Window, type Act } from './kit'
```

Copy an example as a starting point. Keep its relative kit imports, copy any
assets it imports, and adapt the composition and look to your product. These
are authored illustrations: a scripted `a.click()` draws feedback; `a.set()`
changes the scene. They do not automate real application controls.

The kit supports React 18 and later. It needs no third-party animation runtime. The
playground uses Vite through Vite+; filming uses `playwright-core` and locally installed
Chrome (or `CHROME_PATH`). Those tools are not runtime dependencies of a demo.

## Verify

```sh
vpr typecheck
vpr check:css
node scripts/film.mjs '<your URL>' --select '.your-demo' --gate
node scripts/film.mjs '<your URL>' --select '.your-demo' --width 390 --gate
node scripts/film.mjs '<your URL>' --select '.your-demo' --states --gate
```

For the bundled viewer, use `?capture=hero-demo` as the filming URL. The ordinary
viewer contains an iframe; use the direct capture route on native clocks. See
`references/rehearse.md` for coverage, phone, hover, reduced-motion, and visual
review. No automated clean result replaces watching the motion.

## Contents

- `kit/`: portable React source and styles.
- `examples/`: gold scenes and reference specimens.
- `teaching/`: explicitly flawed/corrected pairs, separate from gold.
- `references/`: design judgment, APIs, and verification guidance.
- `assets/`: local icon assets used by examples.
- `scripts/`: verification tools, independent of the host's markup.
- `playground/`: the standalone local viewer.

The skill, kit, examples and verification tools are included in this folder.
See `NOTICE.md` for third-party names and optional assets.
