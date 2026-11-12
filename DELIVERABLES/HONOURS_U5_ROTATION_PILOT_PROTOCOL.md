# Serve-reception rotation pilot: feasibility and review rule

**Status:** proposed bounded extension, 6 November 2026. No rotation labels or rotation–outcome results have been accepted. The current thesis must continue to say rotation was not measured until source review and checks below are complete.

## Why this can be a small addition

The user suggested identifying rotation from the six near-side players' starting positions when the opponent serves. This is a practical way to study a **serve-reception rotation state** without demanding six grounded floor positions at every frame of a rally. It directly addresses part of RQ2 and the word “rotation” in the thesis title. It is not necessary for the signed research-prototype success criteria, so it should be treated as a contained pilot rather than a reason to reopen the main outcome analysis near submission.

The [FIVB Official Volleyball Rules 2025–2028](https://www.fivb.com/wp-content/uploads/2025/01/FIVB-Volleyball_Rules2025_2028-EN.pdf), rules 7.4 and 7.6, provide the general model: the receiving side follows rotational order at the serve, positions 4/3/2 are front and 5/6/1 are back, and a team rotates clockwise when it wins service back. The precise rule set for the recorded US college match should be checked before asserting any legal positional fault. This pilot classifies *team rotation state*; it does not adjudicate legality from a broadcast image. The rule's foot-based positional relations also mean that a single box bottom or midpoint between shoes is insufficient to prove an overlap call.

## Two labels that must stay separate

1. **Observed serve-receive arrangement:** named on-court player in each apparent front/back and left/centre/right relation in one source-reviewed pre-serve frame. This can be ambiguous when players crowd, overlap or obscure shoes. Record `uncertain`, never force a slot.
2. **Rotation state:** six legal lineup slots 1–6, anchored by a known set lineup or service order and advanced one step when the team wins back service. A receiver's visual arrangement alone is a candidate, not proof of the full lineup history. A libero's visible jersey occupies an underlying back-row player's rotation slot; preserve both `visible_jersey` and `underlying_slot_player` when identifiable.

The existing tracker labels 1–6 are *internal player-slot IDs*, not volleyball rotation positions 1–6. Do not reuse one set of numbers as the other.

## Minimal pilot on the existing material

1. **Choose source-only serve events first.** The existing [event-transition review index](../data/matches/yt_u5HnY2aNW14/screening/event_transition_review/index.json) has six-frame-spaced serve-navigation sheets for all 18 frozen points. It has **not** certified exact serve contact or which side served. Start with [S1 P5's serve sheet](../data/matches/yt_u5HnY2aNW14/screening/event_transition_review/s1_p05_serve_1.jpg), frames 1345–1417, because it shows six near-side UCLA players in a receive-like arrangement. The serving side and contact timing still require source-video review. Do not choose a frame on detector success.
2. **Review the source video around the candidate serve.** Record set/point, pre-serve frame number, `serving_team`, `receiving_team`, confidence in the timing, six visible jersey IDs, source-visible feet and any substitution/libero state. If the opponent is not serving, move to the next source-only candidate; keep the skipped point in the screening denominator.
3. **Assign relative order before reading tracker boxes.** For each receiving player, record front/back and left/centre/right only where visible. Use `uncertain` for obscured feet or overlap. This is a source observation, not a court-homography accuracy check.
4. **Anchor and cross-check the six rotation slots.** Obtain the set lineup or an independently readable server/service-order sequence. Use score changes to determine when the receiving team wins back service, then advance the rotation once. Compare the expected slot order with a second opponent-serve frame from the same set. Record any substitution and the libero's underlying slot explicitly. A visual disagreement or incomplete sequence stays unresolved.
5. **Freeze a small diagnostic result.** Report how many of the 18 selected points were opponent serves, how many had an identifiable pre-serve frame, and how many had an unambiguous six-slot state. Show one or two source-linked examples. Do not calculate a rotation–winner effect unless enough independently selected, correctly timed and comparable points exist in each rotation/outcome cell.

## Proposed record for each reviewed serve

| Field | Meaning |
| --- | --- |
| `set`, `point_number`, `source_frame`, `source_sha256` | Provenance; source frame is before or at the serve action, with timing status |
| `near_team`, `serving_team`, `receiving_team` | Opponent-serve eligibility for near-side rotation review |
| `serve_timing_status` | `exact_contact`, `bracketed`, or `uncertain` |
| `visible_jersey` and `internal_player_id` | Human source ID kept distinct from tracker ID |
| `front_back`, `lateral_relation`, `feet_visible` | Pre-serve source observation, with `uncertain` allowed |
| `rotation_slot_1_to_6` | Accepted only when supported by lineup/service-order cross-check |
| `underlying_slot_player`, `libero_replacement` | Distinguish the libero's visible jersey from the rotation slot occupied |
| `reviewer`, `review_timing`, `notes` | Single-reviewer provenance and any previous exposure to tracker output |

## Decision for the thesis

Add a **short descriptive rotation subsection** only if the pilot produces at least one source-timed, internally cross-checked rotation state. State its denominator and uncertainty. A single example can show methodological feasibility for RQ2 but cannot support RQ3. If the serve moment, identities or lineup anchor remain ambiguous, leave rotation in future work. The current title can remain as the research topic, provided the abstract and conclusion accurately state what was and was not measured; a narrower title is also reasonable at final author/supervisor review.
