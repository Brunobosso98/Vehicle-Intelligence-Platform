# Phase 11 provider caveats

Normal Phase 11 validation uses the existing deterministic provider with zero paid
calls. It validates the engineering harness and selected code paths only. It does
not show how OpenAI or another stochastic provider behaves on the final SHA.

Real-provider reliability is `NOT_EVALUATED_ON_FINAL_SHA`. Paid evaluation is not
implemented as an enabled command in the current iteration. Phase 7D's historical
120 slots have PASS observations across multiple rounds, but were not jointly
rerun on one exact final source SHA. That historical record remains separate from
Phase 11 deterministic engineering evidence.
