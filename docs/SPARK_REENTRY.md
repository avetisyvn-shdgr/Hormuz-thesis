# Spark Secondary-Outcome Re-entry

**Status:** dormant optional extension. Spark is not a dependency or blocker for
the PortWatch working primary.

The adapter, access probe, registry entries, and secondary-outcome configuration
are intentionally isolated. Do not copy Spark logic into core model scripts.

## Activation gate

1. Put `SPARK_CLIENT_ID` and `SPARK_CLIENT_SECRET` in `.env`; never commit them.
2. Run:

   ```bash
   .venv/bin/python scripts/verify_spark_target.py \
     --report-json data/processed/spark_access_report.json
   ```

3. Activate only if both Spark25S and Spark30S receive
   `usable_coverage: true` for the configured study window. Inspect missing-day
   diagnostics and confirm thesis-use/publication rights separately.
4. In `config/sources.yaml`, change both Spark target statuses from
   `unavailable` to `primary`.
5. In `config/settings.yaml`, move both names from
   `dormant_secondary_outcomes` to `active_secondary_outcomes`.
6. Rebuild the panel and rerun validation, counterfactual, interval, and placebo
   scripts. The PortWatch primary and robustness outcomes remain unchanged.

## Non-negotiable guards

- Freight rates enter as secondary outcomes; they do not silently replace the
  locked working primary.
- Truncated trial history is a failed gate, not permission to shorten the
  pre-period after seeing results.
- Do not commit licensed raw prices unless the license explicitly permits it.
- Preserve `data/processed/spark_access_report.json`, including blocked or failed
  states, as the audit record.
