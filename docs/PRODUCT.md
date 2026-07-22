# PRODUCT — Smart Fridge Inventory (one-pager)

Companion to HANDOFF.md (tech spec). This is the strategy: what problem we're
solving, what could kill it, and the smallest test that proves it's real.

## Problem (the job-to-be-done)

> "When I'm shopping or making the list, I want to know what we're low on,
> so we don't run out of staples or buy duplicates."

The job happens AT THE STORE / LIST TIME, not at the fridge. The fridge is
just where the data lives.

**The incumbent we're competing with:** open the fridge, look, text your
partner. Free, instant, ~80% good. We only win on its failures:
- Fill levels you can't see (ketchup, creamer, condiment jars)
- The shopper isn't home to look
- Chronically forgotten items
- Consumption *rate* ("2 days of milk left") — nothing else provides this

## What weight uniquely gives us

Cameras see presence; barcodes see purchases. Only weight sees
**quantity remaining** and **consumption rate** (slope of weight-over-days
from the event history). Rate → time-to-empty → "buy milk before Thursday."
That's the product. Nobody wants grams.

## Riskiest assumption (name it, test it, don't skip it)

| Assumption | Risk |
|---|---|
| Load cell weighs accurately | LOW — proven on bench this week |
| App computes "amount left" from grams | LOW — arithmetic + item profiles |
| **Household members weigh items every time, forever** | **EXISTENTIAL — untested** |
| "Low on X" alerts actually change shopping behavior | MEDIUM — untested |

Every extra step at the fridge door fights laziness, and laziness wins.
A weigh-everything ritual has food-logging-app retention: great week one,
dead by week four. Strategic consequence:

> The product must converge toward ZERO user effort. A **dedicated bay**
> (scale lives under the milk; weighing is a side effect of putting it back)
> has opposite adoption physics from a **weigh station** (weighing is a chore).
> Same electronics. Different product.

## Discovery plan (this week, ~zero cost)

1. **Diary study** (both households, 7 days): log every ran-out /
   double-bought incident and the item. Output: the real pain-item list and
   frequency. Short, staple-heavy list = the wedge and the bay lineup.
2. **Concierge MVP**: a human texts "you're low on X" twice a week (by
   looking in the fridge). If a perfect hand-made signal doesn't change
   shopping behavior, sensors won't either.
3. **Behavior probe**: calibrated pad by the fridge, "weigh things on
   return" rule, 7 days. Metric: weigh-events/day, day 1 vs day 7.
   The decay curve is the most valuable data this project can produce.

**Kill/pivot criteria (agreed in advance):** if weigh events decay >50% by
day 7, kill "weigh everything"; go all-in on dedicated bays for the top 3
diary-study items.

## MVP: the Milk Bay

One 5 kg cell pad INSIDE the fridge where the milk jug always lives.

- Zero behavior change — identity is automatic (only milk goes there)
- One alert: "≈2 days of milk left" (time-to-empty from consumption slope)
- One app screen: Running Low → [add all to list]
- Stack: existing Pico firmware + event schema (HANDOFF.md §6) → HTTPS POST
  → partner's Vercel API route → DB → alert
- Scope: 1 item, 1 household, 4 weeks

**Success =** the alert prevents a run-out or an extra trip, twice, in 4
weeks. **Failure info is success too** — it tells us alerts don't move
behavior before we've built inventory management for a whole fridge.

## Metrics that matter (in order)

1. Weigh/bay events per day at week 4 vs week 1 (retention of the behavior)
2. Prevented incidents (run-outs / duplicates avoided — ask weekly)
3. Alert → action rate (was the item bought after an alert?)
4. NOT grams precision. ±5 g is irrelevant to "buy milk Tuesday."

## Roadmap logic (each step gated by the previous)

1. Milk Bay MVP (dedicated, passive)          ← we are here
2. +2 more bays from diary-study top items
3. General weigh-pad for long-tail items (only if probe retention was good)
4. Multi-household beta → then talk about camera/barcode intake, sharing,
   auto-ordering

## Division of labor

- Hardware/firmware (Phillip): calibrated events over HTTPS per HANDOFF.md.
  Frozen JSON contract — partner builds against it without waiting.
- App (partner, Vercel): /api/weigh-event ingest → DB → time-to-empty model
  → one Running Low screen + push alert. Item profiles (empty/full/serving
  weights) can be hardcoded for milk in the MVP.
