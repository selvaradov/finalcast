# **Design Spec — “Chalkboard with a Wink”**
https://chatgpt.com/c/69f8c0b7-7478-8333-a12b-ec1cc986e76a

## 1. Core idea

A lightly academic, slightly hand-drawn interface that signals:

* this is grounded in real data and methods
* but it is exploratory, imperfect, and a bit playful

The tone should feel like:

> a smart student explaining a model on a chalkboard after a long problem class

Not:

* a formal Oxford publication
* a novelty gimmick site

---

## 2. Design principles

### 2.1 Always signal uncertainty

Every major visual element should reinforce that outputs are *priors*:

* ranges > point estimates
* soft edges, not hard boxes
* annotations, not declarations

### 2.2 Structured but imperfect

Layout is grid-based and clean, but:

* lines are slightly irregular
* charts have subtle hand-drawn touches
* annotations feel “added” rather than typeset

### 2.3 Layered seriousness

* First glance: clear, usable, structured
* Second glance: small playful details, annotations, caveats

### 2.4 Don’t block usability with theme

The chalkboard is a *skin*, not the product:

* contrast must remain high
* inputs must feel modern and responsive
* charts must remain readable

---

## 3. Colour system

### 3.1 Base palette

| Token           | Colour               | Usage              |
| --------------- | -------------------- | ------------------ |
| `bg-main`       | #0F2A1F (deep green) | primary background |
| `bg-panel`      | #133526              | cards/panels       |
| `chalk-primary` | #F4F1E8              | main text          |
| `chalk-muted`   | #CFC8B8              | secondary text     |
| `chalk-faint`   | #8F8A7C              | gridlines, labels  |

Avoid pure white (#FFFFFF); everything should feel slightly dusty.

---

### 3.2 Accent colours (subject + UI)

| Purpose              | Colour                 |
| -------------------- | ---------------------- |
| Philosophy           | #6FD3C1 (chalk teal)   |
| Politics             | #FF8C69 (chalk coral)  |
| Economics            | #7FA7FF (chalk blue)   |
| Highlight            | #F2C14E (chalk yellow) |
| Warning / volatility | #E76F51                |
| Success / “First”    | #9BE564                |

Use accents sparingly — mostly for:

* chart segments
* tags
* key numbers

---

### 3.3 Surface hierarchy

* Background: deep green
* Panels: slightly lighter green
* Hover: subtle lift + faint outline (chalk stroke)
* Active: highlighted with yellow or subject colour underline

---

## 4. Typography

### 4.1 Primary fonts

* **Body/UI:** Inter (or similar clean sans-serif)
* **Headings:** a soft serif (e.g. Fraunces, Spectral)
* **Accent (very limited):** handwritten/chalk-style font for annotations only

---

### 4.2 Typographic hierarchy

| Element         | Style                                |
| --------------- | ------------------------------------ |
| H1 (page title) | serif, large, slightly loose spacing |
| H2 (sections)   | serif, medium                        |
| Body            | sans-serif                           |
| Labels          | small caps or uppercase sans         |
| Annotations     | handwritten style, small, muted      |

---

### 4.3 Tone rules

* Avoid authoritative phrasing (“you will”, “this means”)
* Prefer probabilistic language:

  * “suggests”
  * “implies”
  * “historically”
  * “roughly”

---

## 5. Layout system

### 5.1 Grid

* 12-column grid (desktop)
* Max width: ~1100–1200px
* Generous vertical spacing

---

### 5.2 Panels (“chalk cards”)

Each card:

* rounded corners (8–12px)
* subtle inner texture (optional grain)
* faint chalk border (1px, slightly uneven opacity)
* padding: 20–28px

---

### 5.3 Section rhythm

Typical page flow:

```
[Header]
[Primary interaction area]
[Result / output]
[Context panels]
[Exploration links]
[Method / caveats]
```

---

## 6. Navigation

### 6.1 Top nav

Persistent, simple:

* Calculator
* Explorer
* Overview
* About

Style:

* minimal underline for active tab (chalk yellow)
* hover = soft glow or underline

---

### 6.2 Sub-navigation (Calculator flow)

Use a 3-step indicator:

```
1. Papers → 2. Ability → 3. Results
```

* current step highlighted
* previous steps clickable
* future steps dimmed

---

## 7. Key components

## 7.1 Paper picker

**Layout:**

* grouped by subject
* each paper = row with:

  * checkbox
  * name
  * μ and σ
  * difficulty badge

**Badges:**

* Gentle
* Moderate
* Hard
* Kingmaker

Style:

* pill-shaped
* lightly coloured (subject tint)
* chalk-outline

---

## 7.2 Ability slider

**Visual:**

* horizontal chalk line
* circular handle (slightly textured)
* tick marks at percentiles

**Labels:**

* “Lower”
* “About average”
* “Top”

Optional quick buttons:

* Bottom third
* Middle third
* Top third

**Microcopy:**

* “This shifts all paper means in the model”
* Keep tone explanatory but brief

---

## 7.3 Results display

### Primary chart: donut or stacked bar

* segmented by classification
* soft edges, not harsh boundaries
* labelled with ranges

Example:

* First: 23–27%
* 2.1: 30–34%

---

### Key result panel

Contains:

* headline:

  > “Roughly 23–27% chance of a First”
* subtext:

  > “Based on historical priors for similar paper choices”

---

### Uncertainty indicator

* show ± range explicitly
* annotate:

  > “uncertainty ~±3pp”

---

## 7.4 Swap suggestion panel

Structure:

```
If you swapped:
[Paper A] → [Paper B]

Estimated change:
+2.4pp First rate
```

Style:

* arrow or transformation visual
* subtle highlight on improvement

Tone:

* “small effect, not guaranteed”

---

## 7.5 What-if mode

Inputs:

* numeric fields per paper

Behaviour:

* recalculate only remaining uncertainty

UI:

* light highlight when active
* “conditioned on your inputs” label

---

## 7.6 Paper profile (Explorer)

Card includes:

* μ (mean)
* σ (volatility)
* % First
* % below 50
* candidate counts
* trend

Visual:

* small distribution chart (histogram or curve)
* annotation:

  * “high variance → swings possible”

---

## 7.7 Charts

### Style rules

* gridlines: faint chalk
* axes: minimal
* labels: small and muted
* lines: slightly rounded

Optional:

* tiny imperfections in stroke (very subtle)

---

## 8. Microcopy system

### 8.1 Persistent disclaimer (important)

Always visible (footer or header strip):

> This is a prior based on historical data. Not a prediction.

---

### 8.2 Tone examples

Good:

* “historically”
* “roughly”
* “based on similar students”
* “small effect”

Avoid:

* “you will”
* “this guarantees”
* “optimal choice”

---

### 8.3 Playful touches (sparingly)

* “made with data, handled with care”
* “the model shrugs slightly”
* “no crystal balls involved”

Keep these:

* optional
* low-frequency
* never in core results

---

## 9. Page-level specs

## 9.1 Calculator

Sections:

1. Intro / CTA
2. Paper picker
3. Ability
4. Results
5. Context panels
6. What-if
7. Caveats

---

## 9.2 Explorer

Sections:

* search + filters
* paper cards
* comparison tool
* scatter plot
* kingmaker section

---

## 9.3 Big Picture

More editorial:

* time series charts
* annotated insights
* callouts (COVID, gender gap, etc.)

---

## 10. Motion & interaction

### 10.1 Transitions

* subtle fade + slide (150–250ms)
* no heavy animation

---

### 10.2 Feedback

* hover = slight brightness shift
* click = soft press effect
* loading = skeleton or subtle shimmer

---

## 11. Variations to consider

### A. Light-mode chalkboard

* cream background
* green panels
* better for accessibility

---

### B. Hybrid mode

* chalkboard for calculator
* clean white dashboard for explorer

---

### C. Annotation-heavy vs minimal

* more handwritten notes vs cleaner UI

---

### D. Chart style

* precise (clean lines)
* expressive (slightly hand-drawn)

---

## 12. Accessibility considerations

* ensure contrast (green vs text)
* avoid relying on colour alone for categories
* labels always visible (not just hover)
* slider usable via keyboard
* charts readable without animation

---

## 13. What success looks like

A user should:

* understand what the tool does within ~10 seconds
* not mistake outputs for predictions
* feel comfortable exploring “what if” scenarios
* not feel judged or directed toward specific paper choices

And ideally:

* find it slightly charming without noticing why
