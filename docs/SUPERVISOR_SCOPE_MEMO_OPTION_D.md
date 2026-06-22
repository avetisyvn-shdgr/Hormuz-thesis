# Supervisor scope memo — proposed thesis direction (Option D)

**To:** Prof. Li
**From:** Mher Avetisyan
**Date:** 2026-06-22
**Revised:** 2026-06-22 — added Section 5 (data-coverage status) after running the
by-source coverage probe; the panel is not yet sourceable at the required
granularity, so approval is requested for the *direction*, contingent on closing
that gap.
**Re:** Confirming the scope and estimand for the Hormuz thesis before I freeze the
design and begin estimation.
**Supersedes (for scope):** the earlier freight-rate / ton-mile memo
(`SUPERVISOR_DECISION_MEMO.md`).

## 1. One-paragraph summary

Proprietary freight data (Bloomberg/Spark) remains unavailable, so I built a
public-data pipeline that is now a working foundation. I propose to elevate it
from a descriptive "how much did Hormuz traffic fall" study into a
**heterogeneous-vulnerability event study**: which energy importers were most hurt
by the 2026 disruption, and which structural factors — pre-shock Gulf exposure and
adaptive capacity — explain why. This keeps a defensible causal claim on public
data only — though, as Section 5 documents honestly, the importer panel is not yet
sourceable at the granularity the design needs; closing that coverage gap is the
binding precondition before any estimation.

## 2. What changed from the proposal

| Original proposal | Proposed now (Option D) |
|---|---|
| Outcome: LNG **spot freight rates** | Outcome: importer-level **Gulf-sourced import** share/volume (public) |
| Identify a causal **ton-mile / fleet-vacuum** channel via mediation + causal discovery | Estimate the **differential** vulnerability across importers by pre-shock exposure and flexibility |
| Needs proprietary freight + AIS | Needs only public data (Comtrade, Eurostat, PPAC, MOF, GFW, PortWatch) |

## 3. Research question and estimand

**RQ:** How did the 2026 Strait of Hormuz disruption propagate through global
energy-import systems, and which importer-level exposure and adaptive-capacity
factors explain heterogeneous vulnerability?

**Estimand (panel interaction difference-in-differences):**
`Y_it = α_i + δ_t + β(Post_t × Exposure_i) + γ(Post_t × Flexibility_i) + X_it'θ + ε_it`.

`β` and `γ` identify the **differential** post-shock response of more- vs
less-captive importers. The common global shock is absorbed by the time effect
`δ_t`.

## 4. The honesty boundary I want to confirm with you

This design **does not** claim the average causal effect of the closure on world
energy supply — one event cannot identify that, and I will not assert it. It
claims a **differential** ("disruption-associated") response across importers who
differed in pre-shock captivity. I believe this is the strongest claim the data
honestly support, and it is harder to dismiss than a single-series level effect.
I want to confirm you are comfortable with this framing before I freeze it.

## 5. Current data-coverage status (the honest precondition)

Before asking you to bless the design, I ran a by-source coverage probe against my
frozen public data and applied an explicit admission rule: an importer needs an
official monthly **total** series, an official **by-source** series (for the
predetermined exposure measure), ≥12 contiguous pre-treatment months, and ≥3
post-treatment months; the panel needs ≥10 such importers.

**Result: 0 of 10 importers currently clear the rule.** Specifically:

- **EU27** (Eurostat) and **Japan** (Comtrade) have the by-source series but only
  2 and 1 post-shock months respectively — partly a *timing* problem, since the
  disruption onset is 2026-03 and official data are only published through ~2026-04.
- **India** (PPAC) has a long monthly history but **total volume only** — no
  origin split, so it cannot anchor the exposure outcome.
- **South Korea, China, Taiwan, Pakistan, Bangladesh** have **no frozen official
  national source** yet.

So today the data honestly support only a **descriptive** EU27/Japan/India
comparison, **not** the confirmatory cross-importer model. I am **not** imputing
missing countries and **not** promoting the GFW vessel proxy to an official
outcome. Two paths can close the gap: (a) freezing additional national-statistics
sources (KR/CN/TW/PK), and (b) waiting for further post-shock months to publish.
Whether GFW terminal-arrival reconstruction is an *acceptable* fill where official
by-source data are absent is a methodological judgement I want your view on (§6.5).

## 6. Decisions I am requesting

1. **Scope pivot** — approve moving from the freight-rate ATT to the importer
   captivity event study **as the target direction**, understanding from §5 that
   estimation is gated on closing the coverage gap? (Recommended: yes.)
2. **Estimand framing** — approve the differential, explicitly non-ATT estimand and
   its limitation as stated in §4? (Recommended: yes.)
3. **Primary outcome** — approve Gulf-sourced import share/volume as primary, with
   total volume, substitution intensity, and a composite vulnerability index as
   secondary outcomes? (Recommended: yes.)
4. **Fallback if coverage cannot close** — if too few importers ever clear the rule,
   are you comfortable with a smaller-N or descriptive-comparative version as the
   contingency, rather than forcing the panel? (I will not estimate a confirmatory
   model the data cannot support.)
5. **GFW reconstruction** — is GFW terminal-arrival reconstruction an acceptable
   source where official by-source data are missing, or must exposure rest on
   official statistics only?
6. **Any constraints** — methods, data sources, or scope limits you want imposed
   before I freeze the pre-registration spec?

## 7. Recommended default and next step

**Recommended default:** approve §6(1)–(3) as stated, with the §5 coverage gap
disclosed. On approval I will pursue the V-layer sourcing to close coverage, and
freeze the
design specification (`CAPTIVITY_EVENT_STUDY_DESIGN.md`) and begin variable
construction, with no estimator fit until the spec is frozen (pre-registration
discipline against specification-searching, which matters given the modest number
of importer units). Full design, identification threats and defenses, and the
falsification plan are in `CAPTIVITY_EVENT_STUDY_DESIGN.md`; the gap analysis is in
`GAP_VALIDATION.md`.
