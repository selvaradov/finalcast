# **Design Spec — "Chalkboard with a Wink"**

## 1. Core idea

A scrappy, educational interface on a dark chalkboard:

* grounded in real data and methods
* exploratory, imperfect, and a bit playful
* feels hand-drawn, not corporate

> a smart student explaining a model on a chalkboard after a long problem class

---

## 2. Colour system

### 2.1 Base palette

| Token        | Colour            | Usage              |
|------------- |-------------------|--------------------|
| `bg`         | #1a1a1e (near-black) | primary background |
| `bg-card`    | #222228           | cards/panels       |
| `chalk`      | #e8e5dc           | main text          |
| `chalk-dim`  | #9a978e           | secondary text     |
| `chalk-faint`| #5e5c56           | gridlines, labels  |

No pure white or pure black. Everything slightly dusty/warm.

### 2.2 Accent colours

| Purpose    | Colour             |
|-----------|---------------------|
| Blue      | #5b9bf5 (primary accent — Philosophy, Firsts, CTAs) |
| Red       | #e8614d (Politics, warnings, risk)  |
| Gold      | #f0c75e (Economics, moderate difficulty) |

Three accents only. Used for chart segments, tags, key numbers.

### 2.3 Subject mapping

* Philosophy → Blue
* Politics → Red
* Economics → Gold

---

## 3. Typography

* **Headings / chalk feel:** Caveat (Google Fonts), 700 weight. Used for h1-h3, labels, badges, buttons, stat numbers.
* **Body / UI:** Inter, 400-600. Used for body text, inputs, table cells.
* Caveat at large sizes (20px+) reads as chalk-handwritten. Below 16px it gets hard — keep Inter for small text.

---

## 4. Layout

### 4.1 Landing page

Two-column layout:
* Left: big chalk headline, subtext, CTA button, caveat
* Right: stat boxes (2×2 grid) + placeholder distribution chart

On mobile: stacks vertically.

### 4.2 Calculator flow

3-step indicator: Pick Papers → Set Ability → See Results

Each step in a card. Steps are sequential — current highlighted, previous clickable, future dimmed.

### 4.3 Results page

* Headline with range (dashed border, faint blue tint)
* Donut chart + classification table side-by-side
* Paper-by-paper breakdown table (expected marks, P(70+), below-50 risk, spread)
* Context panels: route comparison, swap suggestion

---

## 5. Texture and feel

* Chalk dust noise overlay: SVG feTurbulence filter at ~3% opacity, fixed position, pointer-events none
* Dashed borders (not solid) for decorative elements
* Slightly uneven border-radii on cards (not needed, optional)
* No heavy drop shadows — keep flat

---

## 6. Microcopy

### Persistent disclaimer
> This is a prior, not a prediction.

### Tone
* "historically", "roughly", "based on similar students", "small effect"
* Never: "you will", "this guarantees", "optimal choice"

### Playful touches (sparingly, never in core results)
* "made with data, handled with care"
* "no crystal balls involved"

---

## 7. Pages

### 7.1 Landing → Calculator
One-page flow. Landing has "Start calculator" CTA.

### 7.2 Explorer (planned)
Paper profiles, comparison tool, scatter plots.

### 7.3 Overview (planned)
Time series, annotated insights, COVID/gender callouts.

---

## 8. Accessibility

* High contrast (chalk on near-black, WCAG AA)
* Labels always visible (not hover-only)
* Slider usable via keyboard
* Don't rely on colour alone — labels + colour together
