# ch08/bound.py
"""The roofline-model upper bound on decode throughput vs batch.

Every decode step reads the weights once and each sequence's KV:
  bytes per step = W + B x L x k
  aggregate tok/s <= B x BW / (W + B x L x k)
  per-user tok/s  <= BW / (W + B x L x k)
As B grows the aggregate bound climbs toward BW / (L x k) and
never passes it; it is halfway there at B = W / (L x k). A bound,
not a prediction: real kernels reach a fraction of peak bandwidth.
Inputs are the datasheet and config values in inputs/.
"""
import argparse
import pathlib
import tomllib

INPUTS = pathlib.Path(__file__).resolve().parents[1] / "inputs"


def toml(name):
    with open(INPUTS / name, "rb") as f:
        return tomllib.load(f)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--gpu", default="H100")
    p.add_argument("--model", default="llama-3_1-8b")
    p.add_argument("--context", type=int, default=4096)
    p.add_argument("--bytes", type=float, default=2, help="BF16: 2")
    p.add_argument("--batches", default="1,2,4,8,16,30,64,128,256")
    a = p.parse_args(argv)
    gpu = toml("hardware.toml")[a.gpu]
    m = toml("models.toml")[a.model]
    bw = gpu["tb_s"] * 1e12
    w = m["params"] * a.bytes
    k = 2 * m["layers"] * m["kv_heads"] * m["head_dim"] * a.bytes
    seq = a.context * k
    print(f"{m['name']}, {a.bytes:g} B/value, on {a.gpu} "
          f"({gpu['tb_s']} TB/s), L = {a.context:,}")
    print(f"W = {w / 1e9:.2f} GB, KV = {k:,.0f} B/token, "
          f"{seq / 1e9:.3f} GB/sequence")
    print("DERIVED upper bounds (roofline model):")
    print("    B   step (ms)   aggregate tok/s   per-user tok/s")
    for b in map(int, a.batches.split(",")):
        step = (w + b * seq) / bw
        print(f"{b:5d}  {step * 1e3:10.2f}  {b / step:16,.0f}"
              f"  {1 / step:15,.0f}")
    print(f"ceiling BW / (L x k) = {bw / seq:,.0f} tok/s; half of "
          f"it at B = W / (L x k) = {w / seq:.0f}")


if __name__ == "__main__":
    main()
