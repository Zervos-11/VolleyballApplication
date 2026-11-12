# Honours project completion audit

The [earlier-work reuse note](HONOURS_PREVIOUS_WORK_REUSE.md) inventories the five pilot rallies. This audit counts only the frozen sample and now includes all newly saved annotations.

This [source-bound audit](../data/processed/honours_completion_audit.json) checks the frozen 18-point ProVolley–UTS sample against the signed contract's spatial-analysis requirements. It separately counts saved annotation work and validated metric evidence; automatic detector boxes and the [R2 provisional calculation](HONOURS_R2_PROVISIONAL_METRICS.md) are excluded from final metrics.

| Gate | Current evidence |
| --- | ---: |
| Score-linked point winners | 18/18 |
| Annotator-complete point boundaries | 2/18 |
| Points with linked player annotations | 18/18 |
| Saved annotator-complete player frames | 61/61 |
| Validated six-player metric frames | 0 |
| Points with a validated team metric | 0/18 |
| Outcome association estimable | No |

| Set | Point | Winner | Saved point boundary | Linked player labels | Best navigation frame | Max detector proposals | Final metric frames |
| ---: | ---: | --- | --- | --- | ---: | ---: | ---: |
| 1 | 2 | UTS | yes | 1 saved (1 complete) | 8643 | 5 | 0 |
| 1 | 7 | ProVolley | no | 3 saved (3 complete) | 15000 | 6 | 0 |
| 1 | 9 | ProVolley | no | 3 saved (3 complete) | 19345 | 7 | 0 |
| 1 | 23 | ProVolley | no | 3 saved (3 complete) | 36366 | 7 | 0 |
| 1 | 32 | UTS | no | 3 saved (3 complete) | 54811 | 8 | 0 |
| 1 | 39 | UTS | no | 3 saved (3 complete) | 65656 | 6 | 0 |
| 2 | 2 | ProVolley | yes | 12 saved (12 complete) | 78000 | 8 | 0 |
| 2 | 8 | UTS | no | 3 saved (3 complete) | 85383 | 5 | 0 |
| 2 | 12 | UTS | no | 3 saved (3 complete) | 89826 | 7 | 0 |
| 2 | 14 | ProVolley | no | 3 saved (3 complete) | 92615 | 6 | 0 |
| 2 | 21 | UTS | no | 3 saved (3 complete) | 102259 | 7 | 0 |
| 2 | 33 | ProVolley | no | 3 saved (3 complete) | 126023 | 6 | 0 |
| 3 | 5 | ProVolley | no | 3 saved (3 complete) | 155544 | 6 | 0 |
| 3 | 11 | UTS | no | 3 saved (3 complete) | 162471 | 6 | 0 |
| 3 | 21 | ProVolley | no | 3 saved (3 complete) | 177778 | 7 | 0 |
| 3 | 27 | ProVolley | no | 3 saved (3 complete) | 187701 | 6 | 0 |
| 3 | 37 | UTS | no | 3 saved (3 complete) | 204000 | 5 | 0 |
| 3 | 38 | UTS | no | 3 saved (3 complete) | 205154 | 5 | 0 |

All scheduled player frames are saved and marked annotator-complete. The [detailed annotation audit](HONOURS_COMPLETED_SAMPLE_AUDIT.md) checks visible floor contacts and staged projections without changing labels. The two saved point boundaries are set 1 point 2 and R2; the other 16 point intervals are still navigation windows. Saved boxes and complete checkboxes do not by themselves validate identity, floor clicks or metre-scale geometry.

**Completion decision:** Score and scheduled annotation work are complete. The contract's validated court-coordinate dataset, three rally-level team metrics and metric–outcome comparison remain incomplete. The next work is source-phase and floor-contact QC, court calibration and a feasibility decision based on the sparse eligible-frame denominator. No player redrawing is presumed necessary.
