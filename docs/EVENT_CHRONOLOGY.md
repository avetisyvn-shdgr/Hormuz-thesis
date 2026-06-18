# Event chronology — verification of the treatment-date candidates

**Status:** Phase-1 verification, completed 2026-06-14. Supersedes the
"PROVISIONAL placeholders" note in `config/settings.yaml`.

## Purpose

The four treatment-date candidates in `settings.yaml` were lifted from the
proposal text and never re-sourced. Identification (dose-response, donor-based
estimators) depends on the treatment date being right, so each candidate is
checked here against reputable reporting and **cross-checked against the AIS
transit collapse already in our own panel**.

## Method & caveats

- News is *media observation, not ground truth* (CLAUDE.md rule 6). Where
  possible the anchor is a primary statement (e.g. QatarEnergy's own notice) or
  a wire service (Reuters/AFP/NYT); the Wikipedia crisis article is used as a
  citation-indexed entry point, **not** as the citable source itself.
- Single-sourced or date-contested items are flagged, not smoothed over.
- The hardest internal check is our own data. Hormuz tanker transits in the
  panel: **Feb 26 = 53, Feb 27 = 53, Feb 28 = 44, Mar 1 = 7, Mar 2 = 2,
  Mar 3 = 2, Mar 4 = 0.** Any claimed trigger date must be consistent with this
  physical collapse beginning 28 Feb → 1 Mar.

## Verdict per candidate

| Slot | Provisional | Verified event | Verified date | Confidence | Action |
|---|---|---|---|---|---|
| `kinetic_trigger` | 2026-02-27 | US/Israel coordinated airstrikes on Iran; Supreme Leader killed; IRGC issues strait-closure warnings within hours; AIS traffic −70% | **2026-02-28** | High | **Corrected −1 day** |
| `closure_declaration` | 2026-03-02 | Senior IRGC official officially confirms the strait is closed; near-zero AIS broadcasts just after midnight 2 Mar | **2026-03-02** | High | **Confirmed** |
| `force_majeure` | 2026-03-04 | Mar 4 was the IRGC **"complete control"** claim — *not* a force majeure. QatarEnergy declared FM after Iranian strikes on Ras Laffan (18–19 Mar) knocked out ~17% of its LNG capacity | **2026-03-25/26** | High (event); Medium (exact day) | **Corrected ~+21 days; mislabel fixed** |
| `regime_consolidation` | 2026-03-10 | No documented "regime consolidation" event on 10 Mar. That day records mine-laying escalation + a US mine-removal ultimatum. The label is an analyst construct | — | Not supported | **DROPPED 2026-06-14** |

## Detail

**kinetic_trigger → 2026-02-28 (was 02-27).** On 28 February 2026 the US and
Israel launched coordinated airstrikes on Iran; within hours the IRGC
transmitted VHF warnings that no ships would pass, and ship-tracking first
showed a ~70% traffic reduction. Our AIS series is consistent: the first clear
dip is 28 Feb (53→44), collapsing 1–2 Mar. The proposal's 27 Feb is one day
early.

**closure_declaration → 2026-03-02 (confirmed).** A senior IRGC official
officially confirmed the closure on 2 March; just after midnight that day
effectively no tankers broadcast AIS. This matches our panel (transits = 2 on
2 Mar, 0 by 4 Mar). Note there are *later* formal markers too — 27 Mar (IRGC
bans vessels to/from US/Israel-allied ports, AFP) and 18 Apr (Iran's formal
closure statement) — if a strict legal-declaration anchor is preferred.

**force_majeure → 2026-03-25/26 (was 03-04, mislabelled).** Two distinct events
were conflated. **4 March** = the IRGC's "complete control" claim (a
control/closure milestone). **QatarEnergy's force majeure** followed the
**18–19 March** Iranian missile strikes on Ras Laffan (Pearl GTL + two LNG
trains, ~17% of Qatari LNG capacity), and was declared ~**25–26 March** on
long-term LNG contracts to South Korea, Belgium, China and Italy. Sources
differ by a day (25 vs 26); pin to a primary wire before citing. This is the
largest correction and the one most consequential for any LNG-supply mechanism
framing.

**regime_consolidation → DROPPED (decided 2026-06-14).** 10 March has no event
matching a "consolidation of the closure regime" — it records the first maritime
incident "in days," US intelligence reporting Iranian mine-laying, and Trump's
ultimatum. Because the closure's hardening was a *gradual* process, inventing a
single discrete "consolidation day" is artificial. Decision: **drop the slot**
and answer the persistence question with a **rolling post-period window** in the
modeling phase instead. Separately, **2026-04-18** (Iran's formal closure
statement) is **reserved as a placebo / falsification date** — it post-dates the
actual disruption by ~7 weeks, so a large estimated "effect" there would signal
a leaking design, making it more useful as a check than as a treatment.

## Implication for the figures

`make_event_study.py` draws these four markers. After the settings update below,
re-run it so the figures reflect verified dates (kinetic_trigger shifts +1 day;
force_majeure moves from inside the collapse to late March near the Ras Laffan
strikes).

## Pre-treatment confounder: the January 2026 Henry Hub record spike

Source verification (`scripts/verify_sources.py`) flagged two Henry Hub spot
values above the old plausibility band. Manual review (2026-06-14) confirms they
are **real EIA all-time daily records**, not data errors: **$30.72 on
2026-01-23** and **$30.57 on 2026-01-26**, driven by **Winter Storm Fern**
(NOAA reported −43 °F in Minnesota; EIA recorded a record 360 Bcf weekly storage
withdrawal; intraday trade reportedly reached $53.75). The series shows the
expected cold-snap shape: ~$4 (Jan 20) → $30.72 (Jan 23) → ~$9 (Jan 28).

Implication: this is a genuine energy-market shock roughly **five weeks before**
the 28 Feb Hormuz trigger. It must be retained (do **not** winsorise it) and
explicitly handled as an energy confounder, so its price effects are not later
mis-attributed to the Strait of Hormuz disruption. The verify-script band was
widened to (1.0, 60.0) with an inline note pointing here.

## Sources

- [2026 Strait of Hormuz crisis — Wikipedia (citation index)](https://en.wikipedia.org/wiki/2026_Strait_of_Hormuz_crisis)
- [2026 Iran war — Britannica](https://www.britannica.com/event/2026-Iran-war)
- [Strait of Hormuz flashpoint — International Crisis Group](https://www.crisisgroup.org/trigger-list/iran-usisrael-trigger-list/flashpoints/strait-hormuz)
- [From chokepoint to crisis — Brookings](https://www.brookings.edu/articles/from-chokepoint-to-crisis-the-strait-of-hormuz-and-global-oil-markets/)
- [QatarEnergy statement on missile attacks on its LNG facilities — QatarEnergy (primary)](https://x.com/qatarenergy/status/2034449492590653505)
- [Qatar says Iranian missile strikes cut LNG export capacity by 17% — Anadolu Agency](https://www.aa.com.tr/en/economy/qatar-says-iranian-missile-strikes-cut-lng-export-capacity-by-17-/3872423)
- [QatarEnergy declares force majeure after Ras Laffan strike — Fox Business](https://www.foxbusiness.com/economy/iranian-strikes-cut-17-qatar-lng-output-threatening-global-supply)
- [QatarEnergy declares force majeure on long-term LNG contracts — Industrial Info](https://www.industrialinfo.com/iirenergy/industry-news/article/qatarenergy-declares-force-majeure-on-long-term-lng-contracts--355444)
- [QatarEnergy extends force majeure until mid-June 2026 — LNG Industry](https://www.lngindustry.com/liquid-natural-gas/30032026/qatarenergy-extends-force-majeure-until-mid-june-2026/)
- [Severe winter weather, natural gas prices increasing — EIA Today in Energy](https://www.eia.gov/todayinenergy/detail.php?id=67046)
- [Henry Hub prices smash all-time records (Winter Storm Fern) — Natural Gas Intelligence](https://naturalgasintel.com/news/henry-hub-prices-smash-all-time-records-as-winter-storm-fern-lng-tag-team-to-tighten-balances/)

> Note: these are secondary/primary-statement entry points gathered via web
> search on 2026-06-14. For the thesis, cite the underlying wire reports
> (Reuters/AFP/NYT) and QatarEnergy's own notice directly.
