# Affected-Importer Findings — Did the Hormuz Disruption Propagate to Destinations?

**Date:** 2026-06-21 · **Status:** Preliminary, descriptive, exploratory. All numbers
re-derivable from frozen snapshots (`data/raw/backup_pathway_probe_20260621/`) and
`data/processed/affected_importer_exposure_loss.csv`. **Not causal; not an ATT.**

## Question

The locked primary estimate measures the disruption **at the strait** (Hormuz tanker
throughput ≈ −95%). This note asks: **did that collapse propagate to the importing
countries that depend on Gulf LNG?**

## Headline finding

**The disruption propagated into SOURCE COMPOSITION, not total volume. Importers'
total LNG intake was defended by substitution; their *Gulf-sourced* intake dropped
sharply. The effect is invisible in aggregate volume and only appears when imports are
decomposed by origin.** Two large importers show it independently, in two independent
official statistics:

| Importer | Source | Total LNG (post) | **Gulf-sourced LNG (post)** |
|---|---|---|---|
| **EU27** | Eurostat `nrg_ti_gasm` | **+10% (rose)** | Qatar −163 MIO_M³ avg; **April Qatar 0.0** |
| **Japan** | UN Comtrade `271111` by-partner | **+14% YoY (Mar26)** | **−27% YoY / −35% vs pre-onset**; Qatar 0.31→0.14 Mt (−55%), **UAE→0** |

The cross-source agreement (Eurostat + Comtrade, no calibration, same qualitative
pattern) mirrors the repo's strongest existing result (WTO≈GFW −98.6%/−93%).

## Why "total volume" and the GFW proxy are the wrong lens

An exposure-vs-*total-loss* table looks uncorrelated — and that is the point, not a
failure:

| Country | Hormuz exposure (pre) | GFW capacity Δ | Real total-volume Δ |
|---|---:|---:|---|
| Pakistan | 100.0% | −93.7% | thin (15 voy, suppressed) |
| Bangladesh | 85.2% | −0.7% | — |
| India | 66.8% | −22.0% | **−8% YoY (total, PPAC)** |
| Japan | 5.1% | −32.6% | **+14% YoY total / −27% YoY Gulf-source** |
| South Korea | 5.6% | −37.0% | — |

- The biggest **GFW** drops (Japan, Korea) are the *least* Hormuz-exposed → those are
  Pacific demand/coverage artifacts, **not** the disruption. The GFW capacity column is
  inferred-capacity, country-level **suppressed** (<5 post voyages); indicative only.
- **Total** import volume is defended by substitution everywhere, so it too hides the
  signal. Japan's total rose +14% YoY while its Gulf intake fell a third.
- The correct dependent variable is **Gulf-sourced volume**, which *does* fall for the
  exposed importers — exactly where the by-source data exists to see it.

## The two real-data cases

**Japan (Comtrade 271111, by-partner, real kg):** total Mar-2026 imports **+14% YoY**,
but Gulf-sourced (Qatar+UAE+Oman) **−27% YoY / −35% vs the Dec-Feb pre-onset average**;
Gulf share fell 13%→8%. Mechanistically precise: **Qatar −55%, UAE→0** (both Hormuz-
captive), while **Oman flat** (Sohar's geography is more ambiguous). Backfill came from
Australia/Malaysia. This is the substitution mechanism caught in real customs data.

**India (PPAC/DGCIS, real, total only — no by-source):** total imports deseasonalized
YoY: pre-onset trend **+5.2%** → **March −9.7%, April −6.5%** (mean −8.1%). A real break
off trend, modest, within historical noise. India is ~67% Hormuz-exposed; lacking a
by-source split, its Gulf-specific cut is not directly observed but is consistent with a
larger underlying Gulf drop masked by substitution (as in Japan/EU).

## Interpretation

A **−95% collapse at the chokepoint** coincided with **defended total importer volumes
but a sharp contraction of Gulf-specific supply**, backfilled by Atlantic/Pacific
substitution. This is:
- the demand-side analogue of the repo's supply-side result ("**contraction +
  substitution, not a ton-mile multiplier**");
- cross-validated across EU (Eurostat) and Japan (Comtrade) with independent data;
- a clean scale contrast for the thesis: **the strait shut, Gulf flows to importers
  fell a third, but total energy intake held — the system absorbed the shock by
  re-sourcing.** *Resilience through reallocation.*

## Caveats (load-bearing)
- Only **~1–2 post-onset months** of national data (today 2026-06-21). Import effects
  lag the chokepoint by voyage time + inventory; a larger or longer bite may still
  emerge. **Re-pull PPAC + Comtrade Japan in July** for a 3–4 month post-window. A
  press-reported India −21% May figure is not yet in the PPAC file.
- Comtrade 271111 = LNG-specific, but only **USA + Japan** report 2026 monthly;
  Korea/China/India/Qatar are blank → no by-source for the other captives yet.
- India PPAC is **total only** (no origin split); the Gulf cut is inferred there.
- Russia/Algeria gains in EU/Japan substitution overlap non-Hormuz dynamics (confound);
  the clean signal is the **Gulf-source contraction**, not which backfill won.

## Next actions
- [ ] July re-pull: extend Japan + India post-window to 3–4 months; revisit India May.
- [ ] Add Korea/Taiwan customs by-source if a 2026 feed exists; GIIGNL annual as a
      structural exposure check.
- [ ] Foreground "strait collapse vs defended totals vs Gulf-source contraction" as the
      headline scale/composition contrast.
