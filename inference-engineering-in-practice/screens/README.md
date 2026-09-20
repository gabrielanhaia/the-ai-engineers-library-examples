# screens/ — the book's screenshots

Nine of the book's figures are screenshots rather than drawings. They are
made here, from data this repository commits, so any of them can be
re-made from a clean checkout.

Three kinds:

| Kind | Shots | How |
|---|---|---|
| Replayed | S1, S2, S3, S4, S5, S6 | a `measured/chNN/*.om` file rebuilt into a fresh Prometheus, read by Grafana, captured panel by panel |
| Replayed + a recording rule | S12 | the same, with `ch15/cost.yml` backfilled over the series |
| Live | S10, S11 | a report on disk, and llama.cpp's own web UI while it answers |

Every PNG ships with a JSON sidecar beside it carrying the tool versions,
the image digests, the SHA-256 of the data file, the exact time range and
the caption, so a reader (or a later edition) can tell where the picture
came from.

## Run them

```sh
python3 -m venv .work/screens/venv
.work/screens/venv/bin/pip install playwright pillow
.work/screens/venv/bin/playwright install chromium

bash screens/shoot.sh                 # S1-S6, each from its committed data
bash screens/cost-replay.sh           # S12
bash screens/shoot-live.sh            # S11 and S10
```

`OUT=<dir>` sends the PNGs somewhere other than the manuscript's image
folder. `bash screens/replay.sh --down` stops the stack.

## The pieces

- `shots.json` — one entry per screenshot: the data, the panels, the time
  range, the viewport, the caption and the honesty notes. It is the brief.
- `replay.sh NAME FILE…` — `promtool tsdb create-blocks-from openmetrics`
  into a fresh TSDB, then Prometheus and Grafana on top of it. `SCRAPE`
  is the lab's own scrape interval and matters: left at Grafana's 15-second
  default, a lab that scrapes every second is drawn at one point in fifteen
  and its peaks disappear.
- `capture.py` — Playwright. Sized for the book's 4.4-inch column: a narrow
  CSS viewport, because Grafana draws axis ticks on a canvas at a fixed 12
  px and the viewport width is what sets their size on paper.
- `patch_dashboards.py` — print patches for vLLM's own dashboards: a line
  style, a width and a fixed colour per series, because the paperback is
  black on white and Grafana's default palette prints as two pale greys.
  No query, unit, axis or title is touched.
- `make_dashboards.py` → `dashboards/book-screens.json` — the panels vLLM
  does not ship: the preemption counter, a prefix-cache hit ratio, a
  per-replica version of it, queue-against-replicas, and the cost rule.
- `guidellm-print.js` — the same idea for GuideLLM's HTML report.
- `cost_pacer.py`, `cost-sim.sh`, `cost-replay.sh` — S12: drive the
  simulator at chapter 5's CITED per-node token rate, record the counter,
  then backfill `ch15/cost.yml` over it. No laptop token is ever priced.
- `live-servers.sh` — a fresh llama-server for S11. Fresh matters:
  llama.cpp caches prompts, and a second run of the same question reports a
  one-token prefill at two tokens a second.

## Notes from making them

**Grafana's embed watermark.** A `d-solo` panel carries a "Powered by
Grafana" badge over the plot that no URL parameter or OSS setting turns
off. `capture.py` removes that one element and asserts it removed exactly
one.

**The datasource and the plugin both need waiting for.** Grafana answers
`/api/health` before the provisioned Prometheus datasource can serve a
query, and its Prometheus datasource runs as a plugin process that can
still be starting after that. A panel that asks too early renders
"Prometheus plugin failed" over "No data" and stays that way.
`replay.sh` waits for both, and `capture.py` reloads and looks again
rather than shipping a picture of an error.

**`$__interval` is not `$__rate_interval`.** vLLM's Performance Statistics
dashboard uses `rate(...[$__interval])`, so a datasource step equal to the
lab's scrape interval puts one sample in the window and the panels return
nothing. S3 sets the step to 15 s, the same step the lab's own queries use.

**vLLM 0.29.0's CPU backend can be profiled, but not with the old
variable.** `VLLM_TORCH_PROFILER_DIR` no longer exists: the server logs
`Unknown vLLM environment variable detected` and registers no profiling
routes. The flags are

```sh
--profiler-config.profiler=torch \
--profiler-config.torch_profiler_dir=/prof \
--profiler-config.torch_profiler_with_stack=false
```

and with them `/start_profile` and `/stop_profile` appear and
`vllm/v1/worker/cpu_worker.py` writes a real trace: one wide
`execute_context_1(161)_generation_0(0)` slice (the prefill, 156 ms for 161
prompt tokens on the reference laptop) followed by the decode steps.
`torch_profiler_with_stack=false` matters — with stacks on, the trace is
buried under Python frames. The book does not print that trace: at 4.4
inches a Perfetto view leaves its slice labels at about 5 pt and its op
rows as an undifferentiated smear, and `fig-02-prefill-decode` makes the
same point legibly.
