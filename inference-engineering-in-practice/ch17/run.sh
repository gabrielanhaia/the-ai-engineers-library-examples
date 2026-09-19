# ch17/run.sh
# A mini vendor verifier: the same 40 requests (cases.py) against
# llama.cpp and the vLLM CPU backend, serving the same model with
# the same chat template, and the schema-valid rate of each.
. /lab/lib/lab.sh

GGUF=/models/gguf/SmolLM2-360M-Instruct-f16.gguf
HF=/models/hf/SmolLM2-360M-Instruct
T=/scratch/ch17/template.jinja

step "models and the chat template"
need_models smollm2-360m-gguf smollm2-360m-hf
mkdir -p /scratch/ch17 && cp template.jinja "$T"
echo " engine     kind         requests  valid   rate  right tool" \
  > "$MEASURED/summary.txt"

step "llama.cpp (build b10964), F16 GGUF"
start_llama ch17-llama -m "$GGUF" --ctx-size 4096 --jinja \
  --chat-template-file "$T"
wait_ready ch17-llama http://ch17-llama:8080/health
python3 verify.py llama.cpp http://ch17-llama:8080 "$MEASURED" \
  | tee -a "$MEASURED/summary.txt"
stop_server ch17-llama

step "vLLM 0.29.0 CPU backend, FP16, xLAM tool-call parser"
start_vllm ch17-vllm "$HF" --served-model-name smollm2-360m \
  --dtype float16 --max-model-len 4096 --chat-template "$T" \
  --enable-auto-tool-choice --tool-call-parser xlam
wait_ready ch17-vllm http://ch17-vllm:8000/health 600
python3 verify.py vllm http://ch17-vllm:8000 "$MEASURED" \
  | tee -a "$MEASURED/summary.txt"

step "schema-valid rates"
cat "$MEASURED/summary.txt"
echo
echo "the gate chapter 18 reuses (thresholds.json):"
python3 gate.py thresholds.json "$MEASURED" || true

step "done"
write_manifest
