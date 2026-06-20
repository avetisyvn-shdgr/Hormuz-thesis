# LNG vessel benchmark roster guide

## Purpose

The benchmark roster defines which known LNG carriers are used to measure Global
Fishing Watch identity and port-visit coverage. It is a feasibility sample, not a
claim that these vessels carried Qatari LNG during the disruption.

## Locked sampling design

The working benchmark is the complete 31-vessel Q-Flex class shown in Nakilat's
public fleet list. A full class census is used instead of selecting 30 convenient
matches after querying GFW. Q-Flex vessels are directly relevant to the study
because they are Qatar-linked LNG carriers used on long-term Qatar LNG trades.

Vessel names and nominal capacities come from Nakilat's fleet list. Stable IMO
numbers are cross-referenced to Appendix 3 of the International Gas Union's 2025
World LNG Report. The roster was frozen before GFW identity matching, so API
availability cannot influence which vessels enter the denominator.

Sources:

- [Nakilat fleet list](https://www.nakilat.com/wp-content/uploads/2018/07/Fleet-List-3-2018.pdf)
- [IGU 2025 World LNG Report](https://www.igu.org/igu-reports/2025-world-lng-report)

Copy the header structure from `docs/templates/lng_vessel_benchmark_template.csv`
into `data/raw/gfw/lng_vessel_benchmark.csv` and add only sourced records. The
raw-data location is ignored by Git; its provenance must still be documented.

## Required columns

| Column | Meaning | Validation rule |
|---|---|---|
| `imo` | Permanent seven-digit IMO ship number | Valid IMO checksum and unique |
| `vessel_name` | Vessel name shown by the cited source | Nonblank; names may change |
| `lng_capacity_m3` | Nominal LNG carrying capacity in cubic metres | Numeric and greater than zero |
| `source` | URL or full bibliographic reference supporting the row | Nonblank and traceable |

The audit requires at least 30 unique valid IMO numbers; the locked roster has
31. IMO is the identifier;
vessel name alone is insufficient because names and flags can change.

## Source discipline

Prefer an owner/operator fleet page, class or flag registry, recognized vessel
database, or another source that explicitly supports both identity and vessel
type. Record the capacity source when it differs from the identity source. Do
not infer capacity from a similar vessel or fill missing values with a fleet
average.

The current four-column schema allows one combined citation per row. If identity
and capacity come from different sources, include both references in `source`,
separated by `;`.

## What the validator proves

The local feasibility audit checks minimum size, missing values, duplicate IMO
numbers, the IMO checksum, and positive nominal capacity. Passing these checks
only means the roster is ready to query. It does not establish GFW match rates,
voyage coverage, actual cargo quantity, or laden/ballast status.

Run the audit from the repository root:

```bash
.venv/bin/python scripts/run_vessel_data_feasibility.py
```

The diagnostics are written to
`data/processed/vessel_data_feasibility.json` under
`gfw.required_local_inputs.gfw_lng_vessel_benchmark_csv`.
