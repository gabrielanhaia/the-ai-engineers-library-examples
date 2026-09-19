# ch03/run.sh
# SLOs for a token stream, in three parts, one engine at a time:
#   llama.sh     the SLO report and goodput on llama.cpp
#   vllm.sh      a request-rate ramp on vLLM's CPU backend, recorded
#                for replay, with its /metrics and two SLO queries
#   simulated.sh vllm bench serve against llm-d-inference-sim, at
#                rates no laptop could serve; SIMULATED numbers
. /lab/lib/lab.sh

bash llama.sh
bash vllm.sh
bash simulated.sh

step "done"
write_manifest
