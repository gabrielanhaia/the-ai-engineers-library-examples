# ch19: the decision worksheet

The book's capstone: one plan file in, a written plan out. It runs
chapter 7's capacity count, chapter 5's cost at the utilization you
reach and chapter 6's API comparison (importing their calculators), on
rates and prices from `inputs/`, then prints the levers, engine and
rollout gate the plan names, and the numbers that should make you
reopen the decision. No laptop rate is priced.

## What it does

Two worked plans, both labeled hypotheticals; every workload figure in
their plan files is an assumption, every rate and price comes from
`inputs/`:

1. `chat.toml`, an internal chat assistant: 20 requests/s on average,
   the conversation traffic shape, MLPerf's gpt-oss-120b request shape
   and Server bound, 30% headroom at the peak, a fleet that holds the
   peak with one node down, half an engineer. Against Together and
   Baseten.
2. `batch.toml`, a nightly summarization batch: 2.5 million documents
   of the same shape due in 10 hours, at MLPerf's Offline rate (no
   latency bound), no spare node, half an engineer. Against Fireworks'
   batch price.

Each plan prints eight sections (workload, SLO, capacity, cost,
comparison and verdict, levers, engine, gate) and the break-even that
would reopen it. `derived.py` records the plans' numbers in
`measured/ch19/derived.json`.

## Run it

```sh
docker compose run --rm inference-in-production ch19
```

Pure Python on the runner, a few seconds. For your own plan, copy one
of the two plan files, change the assumptions, and pass it:

```sh
docker compose run --rm inference-in-production ch19 my-plan.toml
```

## Expected output

Recorded on the reference laptop (Apple M2 Pro, 16 GB, OrbStack,
linux/arm64). This block is
[`../measured/ch19/output.txt`](../measured/ch19/output.txt):

```

== two worked plans
plan: internal chat assistant (a hypothetical)
1 workload  20 requests/s average; conversation: peak x 1.7
2 SLO       p99 TTFT <= 3,000 ms, TPOT <= 80 ms: 12.5 tokens/s
3 capacity  peak 34 requests/s = 42,500 output tokens/s
            42,500 / (0.70 x 11,232.0) = 5.41 -> 6 GPUs
            = 1 node of 8; 2 so it fits with one down
4 cost      2 x 8 B200: $114.40 an hour, 13.9% busy
            $0.1768 / 0.139 = $1.27 per million output tokens
5 compare   52.6M requests a month of 5,000 in / 1,250 out
            serve           $83,512 + staff $5,666 = $89,178
            together        $0.00150 x 52.6M = $78,840
            baseten         $0.001125 x 52.6M = $59,130
  verdict   buy from baseten: $30,048 a month less than serving
6 levers    prefix caching (ch 10): shifts the frontier; skips
              the shared system prompt's prefill; watch hit rate
            autoscaling (ch 16): raises utilization in the
              valley; watch cold starts
            batch what can wait (ch 6, ch 8): raises utilization,
              or pays half the API's price
7 engine    buying: the provider's. Pin provider, model, version;
            an endpoint is not the weights (ch 17). Serving: the
            engine the rate was measured on, or measure yours (ch 4)
8 gate      ch 17's verifier on the endpoint before any switch;
            ch 18's quality gate; an alert on the SLO (ch 15)
  reopen    when a price moves, a GPU or model ships, or
            above 22.6 requests/s (together)
            above 30.2 requests/s (baseten)

plan: nightly summarization batch (a hypothetical)
1 workload  2,500,000 documents a night, due in 10 h
2 SLO       none per token: the window is the bound
3 capacity  88,491.0 output tokens/s a node, Offline
            2,500,000 x 1,250 / 88,491.0 = 9.81 h -> 1 node
4 cost      1 x 8 B200: $57.20 an hour, 40.9% busy
            $0.1796 / 0.409 = $0.439 per million output tokens
5 compare   76.0M requests a month of 5,000 in / 1,250 out
            serve           $41,756 + staff $5,666 = $47,422
            fireworks batch $0.00075 x 76.0M = $57,031
  verdict   serve: $9,609 a month less than fireworks batch
6 levers    the Offline corner (ch 8): along the frontier; no
              bound, yet Offline is within 2% of Server here
            fill the idle hours (ch 6): raises utilization; the
              node is paid for all day
            prefix caching (ch 10): shifts the frontier, if the
              documents share a prompt
7 engine    the stack the rate was measured on (TensorRT-LLM with
            Dynamo); any other is measured at this shape (ch 4)
8 gate      ch 18's performance gate at 5,000 in / 1,250 out,
            failing on a throughput drop; ch 11's eval on a sample
  reopen    when a price moves, a GPU or model ships, or
            above 2.08M documents a night (fireworks batch)

== the plans' numbers
18 numbers, recomputed from inputs/: measured/ch19/derived.json

== done
manifest: measured/ch19/machine.json
```

## What the test asserts

`test ch19` runs the lab, then checks that each plan is consistent,
never its numbers: all eight sections are present; the verdict is the
cheapest option; utilization is between 0 and 1; the interactive fleet
still holds its peak at the full rate with one node down; the batch
fits its window. The numbers themselves are checked by the
`derived-data` CI job (`scripts/check_derived.py`).

## Files

- `worksheet.py`: the worksheet.
- `chat.toml`, `batch.toml`: the two worked plans.
- `derived.py`: the plans' numbers, as JSON.
- `run.sh`, `test.sh`: the lab and its test.
