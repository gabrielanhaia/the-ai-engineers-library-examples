# ch18/broken_template.py
"""Write a chat template and a broken copy of it.

The broken copy ignores add_generation_prompt, so the prompt ends
without the assistant's turn header: the flag vLLM's team found
silently not passed when it chased Kimi K2's tool-call failures.
Nothing about the weights changes.

    python3 broken_template.py TEMPLATE OUT_DIR

TEMPLATE is the candidate stack's chat template; the lab hands it
chapter 17's, so one injected regression meets both the task eval
and the contract verifier.
"""
import pathlib
import re
import sys

good = pathlib.Path(sys.argv[1]).read_text()
out = pathlib.Path(sys.argv[2])
broken = re.sub(r"\{%-?\s*if add_generation_prompt\s*-?%\}.*?"
                r"\{%-?\s*endif\s*-?%\}", "", good, flags=re.S)
if broken == good:
    sys.exit("no add_generation_prompt block in this template")
(out / "good.jinja").write_text(good)
(out / "broken.jinja").write_text(broken)
