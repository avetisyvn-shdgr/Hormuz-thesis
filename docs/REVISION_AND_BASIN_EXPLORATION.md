# What the data revision uncovered: three descriptive findings

**Run:** 2026-08-09 · `scripts/run_revision_and_basin_exploration.py`
**Outputs:** `data/processed/revision_by_chokepoint.csv`,
`data/processed/country_haul_gradient.csv`
**Status:** Exploratory and descriptive. Nothing here identifies a causal
effect. One finding is reported as a **null**.

This started as follow-up to the PortWatch vintage problem
(`PORTWATCH_VINTAGE_SENSITIVITY_RESULTS.md`) and turned up two results worth
carrying into the thesis plus one hypothesis that does not survive checking.

---

## Finding 1: the mean-level revision is overwhelmingly localized to Hormuz

PortWatch's changelog attributes the July and August 2026 revisions to
AIS-spoofing and incomplete-transit checks, which reads as a global
methodology change. At the level of period means, its material effect is
overwhelmingly concentrated at Hormuz. Across all 28 chokepoints and every
vessel class, the mean-level change is:

| Chokepoint | tanker | cargo | container | dry bulk | total |
|---|---:|---:|---:|---:|---:|
| **Strait of Hormuz** | **−16.9%** | **−17.6%** | **−15.3%** | **−19.6%** | **−17.2%** |
| Magellan Strait | −0.04% | −0.01% | 0.00% | 0.00% | −0.02% |
| Suez Canal | −0.00% | −0.02% | −0.02% | −0.01% | −0.01% |
| Bab el-Mandeb | 0.00% | −0.00% | −0.00% | −0.01% | −0.00% |
| *(all 27 others)* | |≤0.04% in absolute value| | | |

Every non-Hormuz count-class mean moved by less than 0.1%. Hormuz moved
15–20%. This is not literal file-level exclusivity: 18 other chokepoints have
at least one revised `n_tanker` day and 26 have at least one revised `n_total`
day.

**What this supports.** It is not a material fleet-wide mean-level
re-estimation, and the Hormuz mean shift is not concentrated in tankers. The
similar class-level proportions are consistent with a Hormuz counting-geometry
change, but do not identify its cause or rule out smaller revisions elsewhere.

**What it means for the thesis.** The chokepoint the thesis is *about* is the
single chokepoint whose measurement was rebuilt. Donor chokepoints in the
synthetic-control and spatial-placebo pools are effectively unrevised, so the
treated unit and the donor pool are now on subtly different measurement
bases. Worth one sentence in Limitations. It does not affect the within-unit
AR primary, which compares Hormuz against its own history in a single vintage.

## Finding 2: annual mean scaling is stable; daily scaling is not uniform

The vintage-to-pinned ratio of annual mean Hormuz tanker transits is similar
across seven years:

| Year | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|---:|---:|
| ratio | 0.843 | 0.848 | 0.842 | 0.827 | 0.825 | 0.818 | 0.826 |

That annual pattern must not be mistaken for a uniform daily multiplier. On
positive-denominator pre-cutoff days, the daily ratio's 5th–95th percentile
range is about 0.72–0.93, and only 49.6% of days lie within ±5% of the fitted
0.831 ratio. The mean post-period ratio (about 0.757) also differs from the
configured pre-period mean ratio (about 0.823).

In this case the **raw relative decline** moves little even though the
absolute decline moves materially:

| Vintage | Pre-period mean | Post-period mean | Collapse | Absolute drop |
|---|---:|---:|---:|---:|
| Pinned | 57.093 | 4.069 | **92.873%** | 53.024/day |
| 2026-08-09 | 47.001 | 3.085 | **93.437%** | 43.916/day |

The percentage decline differs by 0.56 percentage points. The per-day figure
differs by 9.1 transits, about a sixth. Because post-period means are near zero,
this percentage stability is partly floor arithmetic; it is not evidence that
the same scaling law holds before and after the cutoff.

**Recommendation.** Report the raw percentage decline and the model-based
shortfall as distinct quantities, always naming the vintage, dates, and
denominator. The roughly 93% raw decline is similar in these two vintages, but
that does not guarantee invariance to a future revision. The absolute daily
shortfall is explicitly vintage-specific.

*(2026 monthly ratios are noisier, 0.58 to 0.84, because the closure-period
denominators are 1–5 transits/day. Do not read those as trend.)*

## Finding 3: the freight stress sat in the *other* basin

The disruption is at Hormuz, east of Suez. The freight repricing was larger
**west** of Suez.

Against each series' own 12 months before the onset (restricted Fearnleys
assessments; derived aggregates only, no raw values published):

| Series | Rise vs own pre-onset mean | Peak vs pre-onset mean |
|---|---:|---:|
| West of Suez spot | **+220%** | 7.65× |
| East of Suez spot | +146% | 4.45× |
| One-year time charter | +124% | 2.43× |

The West/East ratio makes the shift starker. The two basins sat at parity for
four years, then inverted:

| Window | n (weeks) | mean W/E | median W/E |
|---|---:|---:|---:|
| 2022–2025 | 201 | 0.998 | 1.000 |
| Jan–Feb 2026 | 9 | 0.792 | 0.667 |
| Post-onset | 18 | 1.419 | 1.472 |

**Reading, carefully.** This is the pattern a ton-mile/fleet-vacuum mechanism
would produce: Gulf loadings stop, so east-of-Suez tonnage has less to carry,
while replacement cargo must come from Atlantic-basin sources over longer
voyages, tightening west-of-Suez tonnage. The 2026-03-06 week, immediately
after the 03-04 force majeure and the 03-05 war-risk insurance withdrawal,
is the single most extreme observation in the whole West series.

**Second-order detail worth a sentence.** Prompt tonnage repriced far more
than term tonnage (spot peaks 4.5× and 7.7× versus 2.4× for the one-year
charter). Markets priced the shock as severe but not permanent.

**On insurance specifically.** There is no insurance series in this project
and war-risk premia are proprietary (Lloyd's). Freight assessments embed
war-risk cost rather than isolating it, so the above is a *proxy for regional
risk pricing*, not an insurance measurement. Presenting it as an insurance
finding would overclaim.

**Boundaries.** Restricted, provenance-limited data whose permitted uses
exclude ATT, causal freight effects, and identified mediation
(`DATA_SOURCES.md`). Descriptive coincidence with the onset, not
identification. n = 18 post weeks. The West series carries documented quality
flags (two masked unverified zeros, reconstructed transcription boundaries).
Red Sea and Suez routing disruption independently affects west-of-Suez
pricing and is not separated here. The series ends 2026-07-03, so the
2026-07-29 Damietta attack is **outside** this data and cannot be tested with
it.

## Finding 4 (NULL): no country-level haul gradient

Finding 3 suggests an obvious country-level prediction: importers that were
more Gulf-dependent before the shock should have had to haul from further
away afterwards. Using the frozen GFW importer exposure summary, average haul
per m³ shipped, 13 countries with at least 15 resolved voyages each side:

Pearson r = **+0.709**, which looks supportive. It does not survive.

- Spearman (rank) r = **+0.231**
- Drop India: Pearson r = **−0.112**
- Drop any other single country: r stays between +0.699 and +0.819

The entire association is one observation. India has 66.8% pre-shock exposure
and a +104% haul increase; remove it and the relationship vanishes. Taiwan is
the direct counterexample: 37.3% exposure, haul change −1.2%.

**Report this as a null.** The country-level ton-mile gradient is not
supported by the available data. This is consistent with the project's
existing conclusion that the demand-side response was **contraction and
substitution rather than a multiplier**
(`CAPTIVITY_EVENT_STUDY_DESIGN.md` H3), so it corroborates the current
framing instead of contradicting it. It also illustrates why the design
pre-commits to leave-one-out: the raw correlation alone would have supported
a thesis claim that is not there.

---

## Suggested placement

1. Finding 2 into the Results framing: quote the percentage as headline,
   the per-day figure with vintage named.
2. Finding 1 into Limitations, one sentence on treated-unit versus donor-pool
   measurement bases.
3. Finding 3 into the mechanism chapter as supporting descriptive evidence,
   with the restricted-data boundaries stated inline.
4. Finding 4 into the falsification cascade as a reported null.
