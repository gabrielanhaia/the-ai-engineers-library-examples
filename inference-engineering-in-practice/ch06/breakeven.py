# ch06/breakeven.py
"""Self-host or API: the break-even for one request shape.

Every input comes from inputs/example-a.toml: MLPerf's rate for
the node, dated list prices, the request shape. No laptop rate
enters; a laptop's tokens per second price nothing but a laptop.
"""
import pathlib
import tomllib

HOURS = 730  # a month: 365 x 24 / 12
INPUTS = pathlib.Path(__file__).resolve().parents[1] / "inputs"


def load():
    with open(INPUTS / "example-a.toml", "rb") as f:
        return tomllib.load(f)


def api_request(api, n_in, n_out, scale=1.0):
    """API $ per request: in x in-price + out x out-price, / 10^6."""
    return scale * (n_in * api["input"] + n_out * api["output"]) / 1e6


def per_million(usd_per_hour, tok_s):
    """The node's $ per million output tokens at 100% busy."""
    return usd_per_hour / (tok_s * 3600 / 1e6)


def breakeven(fleet_month, node_requests, api_usd):
    """Break-even U, and requests a month, against one API.

    U is the fleet's cost per request (at one node's capacity)
    over the API's price per request: the ratio of two prices.
    """
    requests = fleet_month / api_usd
    return requests / node_requests, requests


def usd(x):
    s = f"{x:.7f}".rstrip("0")
    return "$" + s.ljust(len(s.split(".")[0]) + 6, "0")


def main():
    ex = load()
    n_in = ex["shape"]["input_tokens"]
    n_out = ex["shape"]["output_tokens"]
    node_h = ex["nebius"][ex["node"]["gpu"]] * ex["node"]["gpus"]
    tok_s = ex["node"]["server"]
    at_100 = per_million(node_h, tok_s)
    node_requests = tok_s * 3600 * HOURS / n_out
    engineer = ex["staff"]["usd_per_year"] / 12
    print(f"request  {ex['node']['model']}, {n_in:,} in / "
          f"{n_out:,} out")
    print(f"node     {ex['node']['gpus']} x {ex['node']['gpu']}, "
          f"${node_h:.2f} an hour, ${node_h * HOURS:,.0f} a month")
    print(f"         {tok_s:,.1f} output tokens/s, MLPerf Server")
    print(f"         at 100%: ${at_100:.4f} per million output "
          f"tokens,")
    print(f"         {usd(n_out * at_100 / 1e6)} per request, "
          f"{node_requests / 1e6:.1f}M requests a month")
    scenarios = [
        ("base: one node, list prices", 1, 0, 1.0),
        ("API price halved", 1, 0, 0.5),
        ("two nodes + half an engineer", 2, 0.5, 1.0)]
    print(f"\n{'':12}{'API':>13}{'break-even':>13}"
          f"{'requests':>12}{'per s':>8}")
    print(f"{'':12}{'per request':>13}{'U, 1 node':>13}"
          f"{'a month':>12}")
    for title, nodes, staff, scale in scenarios:
        fleet = nodes * node_h * HOURS + staff * engineer
        print(f"{title} (${fleet:,.0f} a month)")
        for name in ("together", "baseten"):
            api = api_request(ex[name], n_in, n_out, scale)
            u, requests = breakeven(fleet, node_requests, api)
            print(f"  {name:10}{usd(api):>13}{u:>13.1%}"
                  f"{requests / 1e6:>11.1f}M"
                  f"{requests / (HOURS * 3600):>8.1f}")


if __name__ == "__main__":
    main()
