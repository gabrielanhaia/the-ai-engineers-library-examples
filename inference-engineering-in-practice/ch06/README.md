# ch06: the break-even calculator

Chapter 6's self-host-or-API decision for one request shape: the
utilization your node must reach to beat an API's price per request,
and the monthly volume that means, in three scenarios. Every input is
a row of `inputs/example-a.toml`, dated and sourced; no laptop rate
enters.

## What it does

1. Prices one request of MLPerf's gpt-oss-120b shape (5,000 in / 1,250
   out) on two serverless APIs (Together, Baseten): input tokens times
   the input price plus output tokens times the output price.
2. Prices the same request on Nebius's 8 x B200 node at MLPerf v6.1's
   Server rate: the node's $ per million output tokens at 100% busy,
   times the request's output tokens.
3. Break-even U is the ratio of the two per-request prices; break-even
   volume is the fleet's monthly cost over the API's price per request.
4. Repeats it for three scenarios: the base case, the API price
   halved, and two nodes plus half an engineer's wage.
5. Recomputes every DERIVED number chapter 6 prints into
   `measured/ch06/derived.json` (`derived.py`).

## Run it

```sh
docker compose run --rm inference-engineering-in-practice ch06
```

Pure Python on the runner, a few seconds. To try your own numbers,
change them in `inputs/example-a.toml` (each with its source and date)
and run it again.

## Expected output

Recorded on the reference laptop (Apple M2 Pro, 16 GB, OrbStack,
linux/arm64). This block is
[`../measured/ch06/output.txt`](../measured/ch06/output.txt):

```

== break-even, three scenarios
request  gpt-oss-120b, 5,000 in / 1,250 out
node     8 x B200, $57.20 an hour, $41,756 a month
         89,856.3 output tokens/s, MLPerf Server
         at 100%: $0.1768 per million output tokens,
         $0.000221 per request, 188.9M requests a month

                      API   break-even    requests   per s
              per request    U, 1 node     a month
base: one node, list prices ($41,756 a month)
  together       $0.00150        14.7%       27.8M    10.6
  baseten       $0.001125        19.6%       37.1M    14.1
API price halved ($41,756 a month)
  together       $0.00075        29.5%       55.7M    21.2
  baseten      $0.0005625        39.3%       74.2M    28.2
two nodes + half an engineer ($89,178 a month)
  together       $0.00150        31.5%       59.5M    22.6
  baseten       $0.001125        42.0%       79.3M    30.2

== every DERIVED number in chapter 6
61 numbers, recomputed from inputs/: measured/ch06/derived.json

== done
manifest: measured/ch06/machine.json
```

## What the test asserts

`test ch06` runs the lab, then checks invariants, never a price:
break-even U equals the self-hosted price per request over the API's
and is below one; break-even requests times the API's price equals the
fleet's month; halving the API price exactly doubles both; a second
node and staff time move the break-even up. The numbers themselves are
checked by the `derived-data` CI job (`scripts/check_derived.py`).

## Files

- `breakeven.py`: the calculator (printed in chapter 6).
- `derived.py`: every DERIVED number chapter 6 prints, as JSON.
- `run.sh`, `test.sh`: the lab and its test.
- Inputs: `../inputs/example-a.toml` (printed in chapter 6).
