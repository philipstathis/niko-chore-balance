# Niko's Lego chore board

Date: 2026-08-17

Turn the 960×640 e-ink JPEG into a kid-facing sticker chart: a Lego brick stack to 150 (the prize is a Lego set) plus today's six chores. Parents check off chores in one YAML file; the total is always computed.

## Goal

Niko (5) should see why points go up and how close he is to the Lego set. Parents should award points the same way every day, without editing a raw number.

Out of scope: a phone app, color, extra display sizes, deducting points, or changing how Cloudflare/GitHub serve `display960.jpeg`.

## Display

Device: Invisible Computers 10.2" e-ink, 960×640, 1-bit black and white. Output remains `display960.jpeg` with the existing download headers.

Layout:

- **Top — Niko's Lego!** A 15×10 grid of chunky bricks (150 bricks, one per point). Fill the bottom row left to right, then the next row up. Empty bricks are outlines; earned bricks are solid. Score under the stack: `{total} / 150`. Small **Lego set** label at the top of the tower.
- **Bottom — today's missions.** Six boxes in two rows of three, in rule order. Each box: star (filled if earned today, empty if not), short name, point value.

If today's date has no row yet, all six stars are empty. The brick stack still shows the running total.

## Rules

Each chore can be earned **once per day**. Weights, in order:

| id | Kid label | Points |
| --- | --- | --- |
| potty | Potty all day | 6 |
| quiet_voice | Quiet voice all day | 5 |
| sharing | Sharing & friends | 4 |
| tidy | Tidy toys | 3 |
| eating | Eat by myself | 2 |
| listening | Listen to grown-ups | 1 |

A perfect day is 21 points. Goal is 150 (a Lego set). Existing `balance.txt` value **16** becomes `starting_balance`.

**Total** = `min(150, starting_balance + sum of all checked chores on all days)`.

**Today's stars** use the row whose `date` is today in `America/New_York`. No row for today → six empty stars.

## Data

Replace `balance.txt` with a single `progress.yaml`.

```yaml
goal: 150
prize: Lego set
starting_balance: 16
timezone: America/New_York

chores:
  - id: potty
    label: Potty all day
    points: 6
  - id: quiet_voice
    label: Quiet voice all day
    points: 5
  - id: sharing
    label: Sharing & friends
    points: 4
  - id: tidy
    label: Tidy toys
    points: 3
  - id: eating
    label: Eat by myself
    points: 2
  - id: listening
    label: Listen to grown-ups
    points: 1

days:
  - date: 2026-08-17
    potty: true
    quiet_voice: false
    sharing: true
    tidy: true
    eating: true
    listening: true
```

Daily parent loop: add or edit today's block, set six booleans, commit to `main`.

A chore omitted or set false for a day counts as not earned. Do not keep a separate running total.

## Build flow

1. Load `progress.yaml`.
2. Compute total (capped at 150).
3. Resolve today's six stars in `America/New_York`.
4. Draw the 960×640 1-bit image.
5. Write `site/display960.jpeg` and the existing index/headers.

GitHub Action also installs PyYAML. Cloudflare worker and JPEG download behavior stay the same.

`render.py` splits **scoring** (pure, testable) from **drawing**.

## Errors

Fail the build (no JPEG) when:

- `progress.yaml` is missing or invalid YAML
- `chores` is not exactly those six ids, in that order, with those point values (labels are taken from YAML for display)
- `starting_balance` is outside 0–150
- a day has an unknown key, a duplicate `date`, a missing `date`, or a `date` that is not `YYYY-MM-DD`

On a valid file: never display a total above 150; a full stack means the Lego set is earned.

## Tests

Run in CI:

- Perfect day adds 21
- Starting 16 plus one perfect day is 37
- Total caps at 150
- Duplicate date / bad YAML / wrong chore list fail
- Renderer writes a 960×640 JPEG

## Success

Niko can see today's stars and a brick stack that grows toward the Lego set. Parents check off the six chores; points always match the rules.
