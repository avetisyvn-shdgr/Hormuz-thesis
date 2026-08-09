# Bloomberg market-layer implementation plan

**Status:** Phases 0-6 implemented on 2026-08-08 under a
`provenance_limited_secondary` designation authorized by the thesis author.
Strict source admission remains blocked, so Phase 7 activation is deliberately
not performed. This does not alter the formal proposal, the locked PortWatch
working primary, or the treatment cutoff.

## 1. Methodological justification

The existing thesis measures the disruption through a PortWatch
counterfactual and then documents an LNG reallocation mechanism using the
open-data vessel and importer branches. The proposed extension adds downstream
market evidence without replacing either completed layer:

1. **LNG freight-market outcomes:** Fearnleys East-of-Suez and West-of-Suez
   spot assessments, plus the one-year LNG carrier time-charter assessment.
2. **Market context:** Netherlands TTF day-ahead gas and Singapore VLSFO bunker
   fuel assessments.

The freight assessments can test whether the physical disruption and
reallocation evidence coincided with unusual LNG carrier-market pricing. The
two basin spot series distinguish geographic responses; the one-year charter
series distinguishes immediate spot dislocation from persistent vessel-scarcity
expectations. TTF and VLSFO document, respectively, the European gas-market and
ship-operating-cost environments.

These additions are secondary evidence. They do not convert forecasting
deviations into an ATT, identify a structural freight-price effect, or establish
formal mediation.

## 2. Locked design decisions

- The PortWatch working primary and robustness outcomes remain unchanged.
- The operational-onset cutoff remains `2026-02-28`.
- All training and model selection remain strictly before the cutoff.
- Freight assessments remain secondary outcomes and are never silently
  substituted for Spark25S or Spark30S.
- The Fearnleys spot assessments and one-year time charter are separate
  constructs and are never pooled into one dependent variable.
- TTF and VLSFO are not headline post-treatment controls. They may themselves
  lie on the treatment pathway.
- The workbooks supplied through chat are transcription/export artifacts, not
  automatically verified Bloomberg source payloads.
- Licensed raw values are not committed unless the applicable licence
  explicitly permits it.
- The default free-data pipeline must still run when the licensed files are
  absent.

The permitted reporting term for the new forecasting results is
**disruption-associated counterfactual deviation in the assessed rate**.
Prohibited labels include `ATT`, `causal freight effect`, `observed market
loss`, and `identified mediation effect`.

## 3. Candidate series and initial disposition

| Logical series | Frequency / unit | Initial role | Initial disposition |
|---|---|---|---|
| Fearnleys LNG tanker East of Suez, 155-165k cbm spot rate | Weekly, USD/day | Secondary freight outcome | Admit first if all gates pass |
| Fearnleys LNG tanker West of Suez, 155-165k cbm spot rate | Weekly, USD/day | Secondary freight outcome | Admit first if all gates pass |
| Fearnleys LNG tanker one-year time charter, 155-165k cbm | Weekly, USD/day | Persistent freight-market outcome | Admit separately if all gates pass |
| Netherlands TTF natural-gas forward day-ahead | Daily, EUR/MWh | Market context / potential mediator | Context layer only |
| ClearLynx VLSFO Singapore | Daily, USD/metric tonne | Shipping-cost context / potential mediator | Context layer only |
| UK NBP day-ahead | Daily, unit to be verified | Reserve context series | Do not code initially |
| Henry Hub and Brent Bloomberg copies | Daily | Cross-check only | Keep existing EIA sources as active data |
| JLC, VLCC, Dubai crude, gasoil, and crack spread | Mixed | Broad context | Exclude from the first implementation |

## 4. Phase-by-phase implementation

No phase begins until the previous phase has produced its declared audit
artifact and passed the stop/go decision.

### Phase 0 — source admission and licence gate

**Purpose:** establish that each candidate is a reproducible, consistently
defined research input before writing modelling code.

Create a machine-readable manifest for each candidate containing:

- exact Bloomberg ticker or security identifier;
- displayed series name and original assessment provider;
- assessment methodology and any known methodology changes;
- route/basin definition, vessel-size basis, propulsion basis where available;
- native unit, currency, frequency, price field, and timezone/date convention;
- extraction date and terminal/export procedure;
- missing-value convention, including whether zero is a genuine assessment;
- licence, retention, thesis-publication, and derived-results rights;
- local filename and SHA-256 checksum.

Implement one read-only admission command that produces:

- `data/processed/bloomberg_export_admission.csv`;
- `data/processed/bloomberg_export_admission.json`.

Admission criteria for each freight series:

- at least 52 pre-treatment and 12 post-treatment weekly observations inside
  the configured study window;
- no duplicate dates;
- no more than 10% missing observations against its documented assessment
  calendar;
- one stable and documented definition across the comparison window, or an
  explicit break that can be handled without outcome-driven choices;
- confirmed USD/day unit and confirmed treatment of zeros;
- reproducible local extraction and acceptable thesis-use rights.

**Stop/go:** a failed metadata or licence gate keeps the series out of all
model scripts. A coverage failure may permit a clearly labelled descriptive
appendix, but not counterfactual estimation.

### Phase 1 — registry-controlled ingestion

**Purpose:** bring admitted data into the existing provenance architecture.

Implement a local licensed-export provider with the standard `(date, value)`
contract. It should read from an environment-configured directory such as
`BLOOMBERG_EXPORT_DIR`; it must not embed a user-specific absolute path.

Planned code changes:

- add `src/lngfreight/sources/bloomberg_export.py`;
- register `bloomberg_export` in `src/lngfreight/sources/__init__.py`;
- add the five candidate logical variables to `config/sources.yaml`, initially
  gated rather than active;
- add source-contract, parsing, date-filter, duplicate, and missing-file tests;
- ensure every analytical load occurs through `registry.get_variable()` and
  records provenance.

The provider must preserve the supplied values. It may parse decimal commas and
dates, but it may not interpolate, smooth, winsorize, or silently translate
blank values into zero.

**Stop/go:** proceed only when all admitted series can be loaded through the
registry and the complete test suite remains green without the proprietary
files present.

### Phase 2 — temporal QA and weekly analysis frame

**Purpose:** construct an auditable analysis frame without introducing timing
leakage.

For the three Fearnleys assessments:

- preserve native assessment dates;
- map observations to a documented Friday week-ending convention only for
  cross-series alignment;
- treat `2026-03-06` as the first expected post-cutoff weekly assessment when
  the cutoff falls on Saturday `2026-02-28`;
- never expand weekly rates to fabricated daily observations;
- never carry a rate across a missing assessment week;
- retain the full extracted history in the source audit but filter the primary
  comparison to the configured study window.

Produce:

- `data/processed/lng_freight_weekly_panel.csv`;
- `data/processed/lng_freight_weekly_quality.csv`;
- `data/processed/lng_freight_weekly_manifest.json`.

QA must report expected/observed weeks, nulls, duplicate dates, longest gap,
zero observations, extreme week-to-week changes, date coverage, unit, and
checksum. Suspect values are flagged, never automatically corrected.

**Stop/go:** unexplained zeros, broken dates, or a material definition change
pause modelling and return the exact rows requiring source verification.

### Phase 3 — descriptive freight-market layer

**Purpose:** establish what the assessments show before fitting a
counterfactual.

Create pre/post descriptive tables and event-aligned figures for:

- East-of-Suez spot rate;
- West-of-Suez spot rate;
- East-minus-West spot-rate spread;
- one-year time-charter rate;
- spot versus one-year charter behaviour, without pooling their levels.

Figures should show the operational cutoff and later milestones as annotations,
not alternative training cutoffs. Report native USD/day levels and a common
pre-period index for visual comparison. Do not use percentage changes when a
zero or near-zero denominator makes them unstable.

**Stop/go:** inspect the figures and QA tables before declaring the model set.
No anomaly is interpreted as a disruption effect at this phase.

### Phase 4 — pre-treatment validation and freight counterfactuals

**Purpose:** estimate transparent secondary-outcome counterfactual deviations.

Use a weekly, pre-treatment-only rolling-origin design separate from the daily
PortWatch model:

- minimum initial training window: 104 weeks;
- validation horizon: 4 weeks;
- validation step: 4 weeks;
- fixed candidate set: last-observation naive, 52-week seasonal naive where
  supported, and parsimonious autoregressions using predeclared weekly lags;
- choose the primary specification only from pre-treatment validation, with the
  simpler model winning materially indistinguishable comparisons;
- forecast the post period recursively without using observed post outcomes as
  lagged inputs;
- construct uncertainty from pre-treatment residuals using a declared weekly
  block/bootstrap or conformal procedure;
- run pre-treatment pseudo-cutoff placebos using the same pipeline.

The primary summaries are the average and cumulative level deviations in
USD/day-equivalent assessment units, interval coverage/exceedance, and the
time path of observed versus counterfactual assessments. Any standardized
comparison is secondary to the native-unit result.

Planned outputs:

- `data/processed/lng_freight_validation_scores.csv`;
- `data/processed/lng_freight_counterfactual_weekly.csv`;
- `data/processed/lng_freight_counterfactual_summary.csv`;
- `data/processed/lng_freight_time_placebos.csv`;
- corresponding figures under `reports/figures/`.

**Stop/go:** if no candidate beats or matches the naive benchmark credibly, or
if interval diagnostics fail, retain the series as descriptive evidence only.
Do not change the pre-period or model set after viewing post-treatment results.

### Phase 5 — TTF and VLSFO context layer

**Purpose:** document concurrent gas-price and vessel-cost conditions without
conditioning away the hypothesized treatment path.

Add TTF and VLSFO to a separate context panel. Preserve native units and do not
average TTF across providers. Plot native levels and pre-period standardized
indices beside the freight results.

Headline freight models remain univariate. Observed post-treatment TTF and
VLSFO values do not enter them as ordinary controls. A future conditional model
would require a separate precommitted specification explaining whether
covariate paths are forecast or observed and why the resulting estimand is only
conditional/descriptive.

Planned outputs:

- `data/processed/freight_market_context.csv`;
- `data/processed/freight_market_context_quality.csv`;
- `reports/figures/freight_market_context.*`.

### Phase 6 — mechanism-chain integration

**Purpose:** connect the new monetary assessments to the completed physical
evidence without claiming identified mediation.

Aggregate the relevant PortWatch/WTO measures to the same weekly calendar and
present a synchronized evidence panel:

1. Hormuz throughput counterfactual shortfall;
2. LNG outbound-volume and vessel/reallocation evidence;
3. East/West LNG spot-rate and one-year-charter deviations;
4. TTF and VLSFO market context.

Any lead/lag correlation is exploratory and reported with the short-post-period
and common-shock caveats. Freight series are not used as donors for the
PortWatch primary, and oil-tanker rates are not used as LNG substitutes.

Produce one thesis-facing summary table and one figure, with every number linked
to an artifact path.

### Phase 7 — activation, reporting, and freeze

Only after Phases 0-6 pass:

- move the admitted Fearnleys series into `active_secondary_outcomes` while
  leaving PortWatch as the primary outcome;
- keep Spark25S and Spark30S dormant and preferred if like-for-like access is
  later obtained;
- add the licensed branch to the orchestrated pipeline as an explicit opt-in,
  not a default requirement;
- update inference notes, data-source documentation, decision log, and thesis
  drafts using generated artifacts only;
- freeze code, configuration, manifests, and derived outputs while respecting
  the raw-data licence.

## 5. Expected limitations

- Fearnleys basin assessments are not the route-specific Spark estimands and
  may represent broader market judgement rather than executed fixtures.
- The three freight series share an assessment provider and are not independent
  replications.
- Weekly frequency reduces effective post-treatment sample size.
- The one-year charter is deliberately slow-moving and may respond to expected
  utilization, financing, and fleet supply beyond the disruption.
- TTF and VLSFO may be consequences or mediators of the same disruption.
- Bloomberg exports supplied through manual copying may contain transcription
  breaks that require comparison with terminal metadata or an original export.
- A common global energy shock can move freight, fuel, gas prices, and trade
  simultaneously; synchronized movement is not by itself causal proof.

## 6. First coding increment

The first implementation increment is **Phase 0 only**:

1. define the licensed-export manifest schema;
2. implement the read-only workbook admission audit;
3. test decimal-comma parsing, date extraction, coverage, missingness,
   duplicates, and zero-value reporting;
4. generate the admission CSV/JSON;
5. stop and review the gate before implementing the provider or any model.

This ordering prevents modelling effort from legitimizing a source whose
definition, transcription quality, or licence has not yet been established.

## 7. Phase 0 implementation result — 2026-08-08

Phase 0 is implemented and its declared artifacts have been generated:

- versioned schema: `config/bloomberg_export_manifest.schema.json`;
- candidate manifest: `config/bloomberg_exports.yaml`;
- read-only audit logic: `src/lngfreight/bloomberg_admission.py`;
- command: `scripts/audit_bloomberg_exports.py`;
- outputs: `data/processed/bloomberg_export_admission.csv` and
  `data/processed/bloomberg_export_admission.json`;
- focused tests: `tests/test_bloomberg_admission.py`.

## 8. Implemented limited-use branch — 2026-08-08

The author confirmed that the supplied files are the complete evidence
available and authorized implementation of a provenance-limited secondary
branch. That authorization permits reproducible internal analysis; it does not
fill the missing Bloomberg ticker, extraction receipt, provider methodology,
definition-history, or licence fields. Consequently, the strict Phase 0 result
remains **0 admitted / 5 blocked**, raw values must not be published, and the
three freight outcomes remain dormant.

Completed increments:

1. **Registry ingestion:** all five checksum-pinned workbooks load only through
   `registry.get_variable()` when `BLOOMBERG_EXPORT_DIR` is set. The free-data
   default remains independent.
2. **Weekly QA:** 235 expected Friday weeks, 230 observed for each freight
   series, five unfilled gaps, no duplicate dates, and 18 complete post-cutoff
   assessment weeks. The two West-of-Suez zeros are preserved in raw columns
   and masked only in separately named analysis columns.
3. **Descriptives:** native levels, the East-minus-West spread, and a common
   12-week pre-event index are generated without interpolation.
4. **Counterfactuals:** fixed naive and parsimonious AR candidates are scored in
   4-week rolling-origin folds after a 104-week initial window. The
   last-observation benchmark is selected for all three outcomes. Post forecasts
   are recursive and never use observed post-event lags.
5. **Context:** TTF and VLSFO remain a separate native-frequency context panel;
   they are excluded from headline freight models.
6. **Integration:** PortWatch, WTO LNG, freight, TTF, and VLSFO are synchronized
   for 18 complete Friday-ending weeks. Evidence roles remain separate and no
   mediation estimator is fitted.
7. **Freeze/orchestration:** `scripts/freeze_bloomberg_layer.py` pins derived
   artifacts. The main pipeline includes this branch only when both
   `ENABLE_BLOOMBERG_LAYER=1` and `BLOOMBERG_EXPORT_DIR` are supplied.

The implementation result supports use as secondary descriptive market evidence
and as a clearly caveated supplementary forecast-deviation branch. It does not
support an ATT, a structural freight-rate effect, an identified mediation claim,
or publication of the raw assessment history.

Applying the Phase 4 stop/go rule to the generated diagnostics: only the
East-of-Suez spot deviation (horizon-matched placebo rank 0.043) qualifies as
supplementary forecast-deviation evidence; the West-of-Suez spot and
one-year-charter deviations (ranks 0.091 and 0.087) are retained as
descriptive evidence only. The 90% conformal band is calibrated on
1-to-4-week-ahead validation residuals but applied out to 18 weeks, so its
uniform exceedance overstates precision and does not upgrade any series past
this disposition. See `docs/INFERENCE_NOTES.md` for the full reasoning.

The numerical coverage gate passes for all three weekly Fearnleys candidates:
each contains 212 pre-treatment and 18 post-treatment observations inside the
locked study window, no duplicate dates, and 2.13% missing assessment weeks
under the provisional Friday-week audit calendar. The West-of-Suez workbook
contains two zero-valued observations, whose meaning remains unverified.

The overall gate is **NO_GO**. All five candidates remain blocked because the
supplied files identify themselves as structured transcriptions rather than
original terminal exports, exact Bloomberg identifiers and price fields are
missing, extraction/publication conventions and assessment methodologies are
not documented, definition stability is not confirmed, and licence/retention/
thesis-publication rights remain unverified. The freight workbooks also disclose
two reconstructed chat-boundary rows each. These are audit disclosures, not
permission to treat the reconstructed workbooks as original payloads.

To state the two tracks without ambiguity:

- **The strict Phases 1-7 activation path has not begun.** The planned
  `bloomberg_export` provider for verified original terminal exports does not
  exist, no Bloomberg series has `status: active` or enters the locked working
  specification, and the default free-data pipeline neither requires nor reads
  any of these files.
- **The separately authorized limited-use branch described above is
  implemented and does process the transcribed values.** A
  `bloomberg_transcription` provider is registered, the five series carry
  `status: restricted` in `config/sources.yaml`, and the transcribed values
  enter this branch's dormant secondary artifacts (weekly panel, descriptives,
  supplementary counterfactual deviations, context, integration). An earlier
  draft of this section stated that "no proprietary values enter modelling";
  that wording was wrong for the limited-use branch and is corrected here. The
  values enter no other part of the thesis pipeline.

Re-run Phase 0 after replacing the transcriptions with original exports and
completing the manifest metadata and rights fields; only that upgrade can admit
the series into the strict activation path.

## 9. Artifact retention and publication boundary — 2026-08-09

Because every `rights` field in `config/bloomberg_exports.yaml` remains null,
derived artifacts are split into two retention classes:

- **Local-only (gitignored, guarded by `tests/test_bloomberg_quarantine.py`):**
  `data/processed/lng_freight_weekly_panel.csv`,
  `data/processed/lng_freight_descriptive_weekly.csv`, and
  `data/processed/freight_market_context.csv` embed the verbatim licensed
  assessment histories and stay out of version control until redistribution
  rights are confirmed. The `.work/` workbook-inspection screenshots are
  quarantined for the same reason. These files are still pinned by
  `scripts/freeze_bloomberg_layer.py`, so local integrity checks continue to
  cover them.
- **Version-controlled:** aggregate summaries, QA tables, validation scores,
  manifests, and post-period derived artifacts (the 18 post-cutoff weeks in
  the counterfactual and mechanism tables). These are analysis outputs rather
  than the assessment history, and are retained to keep the reported numbers
  auditable.

The full-history descriptive figure
(`reports/figures/lng_freight_market_descriptive.*`) traces the licensed
series closely; do not reproduce it in the published thesis until
Bloomberg/Fearnleys chart-redistribution rights are confirmed. Event-window
figures restricted to the post period plus the confirmation checklist in
`docs/BLOOMBERG_EXTRACTION_CHECKLIST.md` are the path to lifting this
boundary.
