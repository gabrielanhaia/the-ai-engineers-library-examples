# ch18/broken_template.py
"""Write the model's own chat template and a broken copy of it.

The broken copy ignores add_generation_prompt, so the prompt ends
without the assistant's turn header: the flag vLLM's team found
silently not passed when it chased Kimi K2's tool-call failures.
Nothing about the weights changes.

    python3 broken_template.py MODEL_DIR OUT_DIR
"""
import json
import pathlib
import re
import sys

model, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
cfg = json.loads((model / "tokenizer_config.json").read_text())
good = cfg["chat_template"]
broken = re.sub(r"\{% if add_generation_prompt %\}.*?\{% endif %\}",
                "", good, flags=re.S)
if broken == good:
    sys.exit("no add_generation_prompt block in this template")
(out / "good.jinja").write_text(good)
(out / "broken.jinja").write_text(broken)
