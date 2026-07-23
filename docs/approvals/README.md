# Approval evidence register

This directory contains primary artifacts used to support thesis-governance
claims. The artifacts may contain personal information and institutional email
addresses. Treat them as confidential governance records and do not redistribute
them outside the thesis-review context.

## `GOV_02_Evidence.pdf`

- **Received from:** Mher Avetisyan, supplied directly on 2026-07-23.
- **Artifact type:** Five-page Safari/macOS print export of the complete email
  thread, “Re: Thesis scope confirmation and formal writing requirements.”
- **PDF creation time:** 2026-07-23 19:23:59 CEST.
- **SHA-256:** `debdef3651f10aaf3f97d3de14d1ab1866b03a1d86a37e0eea7097d803bdcbad`
- **Supports:** Zhenyu Wang wrote on 2026-07-23 that the revised title, research
  question, estimand, claim strength, and completed empirical scope were
  acceptable for the Bachelor’s thesis. The thread also supports using the
  supplied LaTeX template and the guidance that introduction plus related work
  should be at most 30% of the main text.
- **Does not support:** Direct Prof. Li ratification or a statement that Zhenyu
  held delegated authority to approve the formal proposal change.
- **Technical limitation:** The print export displays a shortened OWA item URL
  but does not preserve a complete RFC `Message-ID`. A raw `.eml` export would
  provide stronger transport-level metadata if it later becomes available.

Verification:

```bash
shasum -a 256 docs/approvals/GOV_02_Evidence.pdf
pdfinfo docs/approvals/GOV_02_Evidence.pdf
```
