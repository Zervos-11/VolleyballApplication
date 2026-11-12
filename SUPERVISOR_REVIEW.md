# Supervisor review guide

The thesis manuscript is supplied separately. This repository provides the implementation and source-linked numerical evidence. Start with the [primary feasibility result](DELIVERABLES/HONOURS_U5_PRIMARY_FEASIBILITY_RESULT.md), [reported-live interval result](DELIVERABLES/HONOURS_U5_S3P34_REPORTED_LIVE_INTERVAL_RESULT.md), [transfer review](DELIVERABLES/HONOURS_ELEVATED_TRANSFER_REVIEW_STATUS_2026-11-06.md), and [research handoff](DELIVERABLES/HONOURS_SHAREABLE_RESEARCH_HANDOFF_2026-11-11.md). Older result reports are retained as research history and may use earlier denominators.

Run `python scripts/check_honours_evidence_package.py --code-review-snapshot` for the included primary-match numerical records. The full 93-test suite passed in the local source workspace; some tests require source images intentionally omitted here. Run `python -m unittest discover -s tests -p 'test_honours_team_metrics.py' -q` for a four-test code-only smoke check. Research dependencies are in `requirements-research.txt`; the handoff records the actual environment.

This snapshot contains code, numerical annotations and report figures. It omits source videos, identifiable frame images, model weights and local caches. Some historical report links point to omitted source images or separately supplied manuscripts and cannot open here. Reproducing detection runs requires the exact source video and model weights identified by hash in the handoff. Do not overwrite manual review records.

The repository should remain private pending a documented ethics and source-use decision. The student must confirm the AI-use disclosure and final thesis text before submission. This snapshot is for supervisor review, not a final university submission.
