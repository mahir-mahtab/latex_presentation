# VAE Presentation — Theme & Style Guide

Group presentation on **Variational Autoencoders** (CSE 200, BUET). 3 members, ~3 minutes each.
Built in **LaTeX Beamer + TikZ**. The reference implementation of the theme is `demo.tex` — copy its preamble for every new slide file.

Goal: show off TikZ drawings and Beamer features (overlays, step-by-step builds), while keeping diagrams **muted and academic**.

---

## 1. Colour palette

| Name    | Hex       | Role |
|---------|-----------|------|
| `navy`  | `#0E237A` | Primary: frame titles, main title, key nodes (`z`), structure |
| `steel` | `#4D6FAD` | Secondary: encoder, KL/regularisation items, subtitles, footer text |
| `sky`   | `#5DADF5` | Decorative only: title-slide stripes, dots, small accent bars |
| `clay`  | `#A86A52` | Warm accent: decoder, reconstruction items, current-step highlight, labels like "CSE 200" |
| `slate` | `#5B6475` | Neutral: arrows, captions, noise/ε, grey diagram parts |
| `paper` | `#FBFAF7` | Slide background (warm off-white) |
| `ink`   | `#1C2233` | Body text, pixel-grid "images" |

```latex
\definecolor{navy}{HTML}{0E237A}
\definecolor{steel}{HTML}{4D6FAD}
\definecolor{sky}{HTML}{5DADF5}
\definecolor{clay}{HTML}{A86A52}
\definecolor{slate}{HTML}{5B6475}
\definecolor{paper}{HTML}{FBFAF7}
\definecolor{ink}{HTML}{1C2233}
```

**Do not use yellow / gold / wheat.** It was tried and rejected; `clay` replaces it.

Colour meaning stays consistent across all members' slides:
**encoder / inference / KL → steel (blue)**, **decoder / generation / reconstruction → clay (brown)**, **latent `z` → navy**, **noise / neutral → slate**.

---

## 2. Typography & layout

- `\documentclass[aspectratio=169,11pt]{beamer}` — 16:9, page is 16 × 9 cm.
- Font: `\usepackage[sfdefault]{FiraSans}` + `\usepackage[T1]{fontenc}`. Frame titles use `\fontseries{eb}` (ExtraBold) in `navy`.
- Math: `amsmath, amssymb, bm`. Bold vectors with `\bm{\mu}`, `\bm{\sigma}`. Write `D_{\text{KL}}` (not `\mathrm{KL}`, which falls back to a bitmap serif).
- Notation (use everywhere): input `x`, reconstruction `\hat{x}`, latent `z`, encoder `q_\phi(z\mid x)`, decoder `p_\theta(x\mid z)`, prior `p(z)=\mathcal{N}(0,I)`, noise `\epsilon\sim\mathcal{N}(0,I)`, reparameterisation `z=\bm{\mu}+\bm{\sigma}\odot\epsilon`.
- Navigation symbols off.

### Title slide (Canva-inspired)
`[plain]` frame, no background/footline. Three dots top-left and bottom-right (`navy, sky, clay`), diagonal corner stripes top-right and bottom-left (`navy, sky, clay`-thin, `steel`), big two-line ExtraBold title on the left, a circular TikZ "latent space" medallion on the right. Only the first slide of the whole deck uses this.

### Content frames
- **Frame title**: ExtraBold navy, followed by a short `clay` bar + a tiny `sky` bar underline.
- **Background**: three thin corner stripes top-right (`navy, sky, clay`).
- **Footline**: left "Variational Autoencoder | CSE 200" in `steel`; right three dots + frame number.
- **Blocks / formula boxes**: `block body` background `slate!7`, rounded, no shadow.

---

## 3. TikZ diagram rules (muted, academic)

- **Flat fills only**: light tints such as `steel!12`, `clay!10`, `navy!8`, `slate!10`, or `white`.
- **No gradients (`top color`/`shade`), no shadows, no glow** inside diagrams. (Gradient only allowed in the title-slide medallion.)
- **Thin outlines**: `line width=0.7pt`–`0.8pt`, outline in the element's role colour.
- **Arrows**: `slate`, `0.7pt`, `Stealth[length=2mm]`. Dashed arrow for stochastic inputs (noise).
- **Labels/captions**: `\footnotesize`, `slate`. Not bold.
- **Braces** (`decorations.pathreplacing`) for annotating loss terms/regions, coloured by role.
- "Images" (MNIST digits etc.) drawn as TikZ pixel grids in `ink`; reconstructions slightly faded (`ink!60` + a few `slate!25` cells).
- Prefer drawing in TikZ over pasting raster images. If an image is unavoidable, keep it small and framed with a thin `slate!50` border.

Standard styles (see `demo.tex`):

```latex
arr/.style   = {->, line width=0.7pt, draw=slate},
lbl/.style   = {font=\footnotesize, text=slate, align=center},
block/.style = {trapezium, trapezium stretches=true, minimum width=2.4cm,
                minimum height=1.55cm, line width=0.8pt, font=\bfseries},
param/.style = {rectangle, rounded corners=2pt, minimum width=0.95cm, minimum height=0.6cm,
                draw=steel, line width=0.8pt, fill=white, text=navy},
op/.style    = {circle, draw=slate, line width=0.8pt, fill=white, inner sep=1pt},
```

Encoder: `block, shape border rotate=270, fill=steel!12, draw=steel, text=navy`.
Decoder: `block, shape border rotate=90, fill=clay!10, draw=clay, text=clay!70!black`.

---

## 4. Beamer overlays (the "animation")

All animation is done with Beamer overlays — **no GIFs, no video, no `animate` package**. Build diagrams step by step with these helpers (in the preamble):

```latex
\tikzset{
  invisible/.style={opacity=0,text opacity=0},
  visible on/.style={alt={#1{}{invisible}}},
  alt/.code args={<#1>#2#3}{\alt<#1>{\pgfkeysalso{#2}}{\pgfkeysalso{#3}}},
  focus on/.style={alt={#1{draw=clay,line width=1.3pt}{}}},
}
```

- `visible on=<2->` — element appears from step 2 and **keeps its space** (layout does not jump).
- `focus on=<2>` — thin `clay` outline on the element introduced in that step.
- Use `\only<n>{...}` for text/formula boxes that replace each other; `\uncover`/`\pause` for bullet lists.
- Aim for **3–5 steps** per build; one idea per click. Remember each member has only ~3 minutes (~4–6 frames each).

---

## 5. Building

- Compile with **pdflatex, twice** (page-anchored TikZ `remember picture` needs the second pass):
  ```
  pdflatex -interaction=nonstopmode demo.tex
  pdflatex -interaction=nonstopmode demo.tex
  ```
- If the PDF is open in a viewer and locked, build under another name: `-jobname=<name>`.
- Check the output visually (e.g. `pdftoppm -r 110 -png file.pdf out`) — nothing may overlap the footline.

---

## 6. Don'ts

- No yellow/gold/wheat colours.
- No gradients, shadows, or saturated fills in diagrams.
- No GIFs/embedded video.
- No new colours outside the palette (use tints of existing ones instead).
- Don't change notation between members.
