# Source-only fixed-window selection for the frozen U5 sample

The [machine-readable protocol](../data/matches/yt_u5HnY2aNW14/screening/source_only_fixed_window_protocol.json) applies one deterministic rule to all 18 score-frozen points. It uses the earlier source-only conservative live-looking interior, not detector availability. Each eligible window has 25 consecutive 30-fps frames (0.8 seconds from first to last) and five planned metric samples six frames apart.

**Selection result:** 17/18 points have a 25-frame interior. The remaining point is S3 P23 (19 frames). These points remain in the denominator.

This selection was frozen after previous detector screens of these points existed; it is rule-based and does not read those screens, but it is not prospectively blinded. The conservative intervals are navigation evidence only. Exact serve/end events, live phase at each sampled instant, jersey identities, grounded positions and court mapping for metric use must still be source-reviewed. Every window remains unapproved.

The first additional source review target was S1 P6, the first eligible frozen point after the two previously deeply audited points (S1 P5 and S3 P34). Its [completed diagnostic](HONOURS_U5_S1P6_FIXED_WINDOW_SOURCE_RESULT.md) retains all five planned samples, including an airborne final frame and a grounded player missed by the detector at the first frame. This review order is an efficiency choice, not a change to the all-point selection rule or an outcome sample.

Reproduce only by verifying the frozen JSON against its two input hashes; the script refuses to overwrite an existing protocol.
