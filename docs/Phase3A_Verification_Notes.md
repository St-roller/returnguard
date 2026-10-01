# Phase 3A verification notes

The original GitHub Actions execution package (run 36836532341, artifact 11149452837) contains 289 files and has ZIP SHA-256 `795c21d177ce3c82953cf7940a163e3e306f430555f848ff8fc3a7a390780bd0`. Every archived file was copied byte-for-byte; existing committed config/projection/lock bytes matched before extraction. The original runtime handoff and artifact hash map remain unchanged. These notes supplement them.

Offline verification replayed all 90 stored extractions through unchanged validation, derived facts, Policy v1 and acceptance aggregation. All candidate fields matched. The full 10-point threshold table was also checked by a separate direct enumeration using exact rational 9/10 feasibility; it selected 0.86, 57 accepted and 57 correct. Scored predictions, support diagnostic and deterministic baseline predictions/metrics matched recomputation. No additional model call was made.

The 57 auto candidates were all correct. The selected threshold accepts every valid auto candidate; there are zero low-confidence abstentions. Score bins contain 1 case at 0.70–0.89 and 56 at 0.90–1.00, with no candidate-route errors in either occupied bin. There is no incorrect auto-candidate class, so correctness AUROC and incorrect-score median are unavailable, and error capture is N/A (0 candidate errors). These results cannot demonstrate that the score separates errors or that thresholding caught errors. Scores remain uncalibrated self-assessments.

Three route errors are conservative over-abstentions: dev_030 (gold eligible, candidate manual) and dev_049/dev_060 (gold ineligible, candidate manual). Field mismatches occur in dev_030/dev_043 for use_beyond_inspection and dev_049/dev_060 for return_reason. This is descriptive dev analysis only; no case, label, prompt, model, baseline or threshold was repaired or retuned.

ReturnGuard dev coverage is 57/90 (63.33%), selective accuracy 57/57 (100%), manual recall 30/30 (100%). The locked baseline covers 24/90 (26.67%), with 24/24 correct auto routes and 30/30 manual recall. These are development results; no held-out coverage, superiority or final project success is claimed. Dev Wilson intervals remain descriptive and optimistic with respect to selecting on the same data. The baseline patterns were committed and locked before inference; they remain fixed.

Reported usage is 91,690 input and 15,368 output tokens, with direct usage costs available for all 90 responses. The reported sum is USD 0.03834265 (the stored floating-point sum retains its full precision). Upstream-provider metadata was not exposed in these responses; returned model identity was openai/gpt-5.6-luna throughout, with no immutable underlying revision exposed.

The legacy PR validation workflow initially used shallow checkout and could not inspect the historical freeze commits. Commit a2c537ce8db6d9f18f18f14167e55ec290322023 changes only that CI checkout to fetch-depth 0. It changes no evaluated source, config, prompt, baseline or result. The subsequent PR CI run 36836904502 passed. The formal dev workflow had already fetched full history and passed all 83 tests, the blueprint check and the frozen/config/prompt/baseline preflight before its first call.

The designated branch still originates at 35ea848; main subsequently changed README only. No source conflict affects the frozen experiment. Prior review-stage pending-approval markers remain historical records; the dataset approval and freeze manifest continue to govern dataset status.

Gate 3A is ready for design review. No held-out test outputs, baseline test outputs or test_authorization.json exist. Work stops here.
