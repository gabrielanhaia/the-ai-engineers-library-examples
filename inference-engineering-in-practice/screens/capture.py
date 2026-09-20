#!/usr/bin/env python3
"""Capture the book's screenshots, and a JSON sidecar for each one.

    python3 screens/capture.py S1 S2            # named shots
    python3 screens/capture.py --list

A shot is one entry in `screens/shots.json`. Two kinds:

`grafana`   one or two panels of a dashboard, each fetched through
            Grafana's `d-solo` route with an absolute from/to range,
            then stacked into one PNG. `screens/replay.sh` must already
            be serving that shot's data.
`page`      any other page: a local HTML report, an engine's own web
            UI. `steps` drives it before the shot is taken.

Both are sized for the book's 4.4-inch print column: a narrow CSS
viewport so the type inside the picture is large relative to its
width, and a device scale factor of 3 or 4 so the pixels are there.
Grafana draws axis ticks on a canvas at a fixed 12 CSS px, which is
why the viewport is narrow rather than the font large: at 520 px the
tick text is 2.3% of the image width, which prints at about 7.3 pt.

The sidecar beside each PNG records the tool versions, the image
digests, the data file's SHA-256 and the exact time range, so the
capture can be re-made from the repository.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHOTS = json.loads((ROOT / "screens/shots.json").read_text())
WORK = ROOT / ".work/screens"
GRAFANA = "http://127.0.0.1:3000"
PROM = "http://127.0.0.1:9090"
PRINT_WIDTH_IN = 4.4


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def env(name: str) -> str:
    """One pin out of images.env, digest and all."""
    for line in (ROOT / "images.env").read_text().splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    raise KeyError(name)


def tool(name: str) -> str:
    for line in (ROOT / "tools.env").read_text().splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip()
    raise KeyError(name)


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def dashboard_files() -> list[dict]:
    out = []
    for var, name in (
        ("VLLM_DASHBOARD", "grafana.json"),
        ("VLLM_DASHBOARD_PERF", "performance_statistics.json"),
        ("VLLM_DASHBOARD_QUERY", "query_statistics.json"),
    ):
        spec = tool(var)
        out.append({"file": name, "pin": spec})
    book = ROOT / "screens/dashboards/book-screens.json"
    out.append({"file": book.name, "sha256": sha256(book)})
    patches = WORK / "print-patches.json"
    if patches.exists():
        out.append(json.loads(patches.read_text()))
    return out


# --------------------------------------------------------------- browser


def browser_info(pw) -> dict:
    import playwright

    return {
        "playwright": getattr(playwright, "__version__", "unknown"),
        "chromium": pw.chromium.executable_path.rsplit("/", 1)[-1],
    }


CSS = """
/* Print legibility: raise every DOM string Grafana draws (panel title,
   legend, axis unit) well above its default, and keep the page white.
   Axis ticks are drawn on a canvas by uPlot at a fixed size and are
   not reachable from here; the viewport width is what sets those. */
body, html { background: #ffffff !important; }
[data-testid="header-container"], .navbar, .sidemenu { display: none !important; }
.panel-container, [data-testid="data-testid panel content"] {
  border: none !important; box-shadow: none !important; background: #fff !important;
}
h2.panel-title, .panel-title, [data-testid="data-testid Panel header"] h2,
[data-testid="data-testid Panel header"] h6 {
  font-size: %(title)spx !important; font-weight: 600 !important;
  letter-spacing: 0 !important; color: #1a1a1a !important;
}
[class*="VizLegend"] , [data-testid*="VizLegend"], .u-legend {
  font-size: %(legend)spx !important; color: #1a1a1a !important;
}
[class*="VizLegend"] button, [class*="VizLegend"] a { font-size: %(legend)spx !important; }
::-webkit-scrollbar { width: 0 !important; height: 0 !important; }
"""


# Grafana stamps an embedded panel with a "Powered by Grafana" badge in
# the top-right corner, over the plot. It is a watermark, not data, and
# it is the one piece of chrome that cannot be turned off from a URL or
# a setting in the OSS build, so it comes off here. Nothing else on the
# panel is touched.
STRIP_BADGE = """
() => {
  // The wordmark is an SVG, so the badge's text is just "Powered by".
  const badge = /^Powered by(\\s+Grafana)?$/;
  const txt = (el) => (el.textContent || '').replace(/\\s+/g, ' ').trim();
  let removed = 0;
  for (const el of Array.from(document.querySelectorAll('span, div, a'))) {
    if (!el.isConnected || !badge.test(txt(el))) continue;
    let node = el;
    while (node.parentElement && badge.test(txt(node.parentElement))) {
      node = node.parentElement;
    }
    node.remove();
    removed++;
  }
  return removed;
}
"""


def render(page, url: str, *, settle_ms: int, css: str) -> int:
    page.goto(url, wait_until="networkidle", timeout=90_000)
    page.add_style_tag(content=css)
    page.wait_for_timeout(settle_ms)
    return page.evaluate(STRIP_BADGE)


def assert_clean(page, shot_id: str) -> list[str]:
    """Refuse the obvious defects a reviewer would catch in the PNG."""
    problems = []
    text = page.inner_text("body")
    for bad in ("No data", "Query error", "Datasource error",
                "Templating", "Panel plugin not found"):
        if bad.lower() in text.lower():
            problems.append(f"page says {bad!r}")
    if page.locator(".panel-loading, [data-testid='Spinner']").count():
        problems.append("a loading spinner is still on the page")
    return problems


# --------------------------------------------------------------- shots


def stack(paths: list, out: pathlib.Path, gap: int, colour: str) -> None:
    """One PNG from one or more element captures, laid out vertically."""
    from PIL import Image

    imgs = [Image.open(p).convert("RGB") for p in paths]
    if len(imgs) == 1:
        imgs[0].save(out)
        return
    w = max(i.width for i in imgs)
    h = sum(i.height for i in imgs) + gap * (len(imgs) - 1)
    canvas = Image.new("RGB", (w, h), colour)
    y = 0
    for im in imgs:
        canvas.paste(im, ((w - im.width) // 2, y))
        y += im.height + gap
    canvas.save(out)


def solo_url(shot: dict, panel: dict) -> str:
    q = [
        f"orgId=1",
        f"panelId={panel['panelId']}",
        f"from={shot['from']}",
        f"to={shot['to']}",
        "theme=light",
        "timezone=utc",
        "__feature.dashboardSceneSolo=true",
    ]
    for k, v in (shot.get("vars") or {}).items():
        q.append(f"var-{k}={v}")
    return f"{GRAFANA}/d-solo/{panel['dashboard']}/x?" + "&".join(q)


def capture_grafana(shot: dict, out: pathlib.Path, pw, args) -> dict:
    from PIL import Image

    width = shot.get("width", 520)
    scale = shot.get("scale", 4)
    css = CSS % {"title": shot.get("titlePx", 17),
                 "legend": shot.get("legendPx", 15)}
    browser = pw.chromium.launch()
    shots, problems = [], []
    try:
        for i, panel in enumerate(shot["panels"]):
            h = panel.get("height", 320)
            ctx = browser.new_context(
                viewport={"width": width, "height": h},
                device_scale_factor=scale,
                color_scheme="light",
            )
            page = ctx.new_page()
            # Grafana's first render after a cold start can come back
            # "Prometheus plugin failed" over a "No data". Reload and
            # look again rather than shipping a picture of an error.
            bad: list[str] = []
            for attempt in range(4):
                stripped = render(page, solo_url(shot, panel),
                                  settle_ms=shot.get("settleMs", 2500),
                                  css=css)
                bad = assert_clean(page, shot["id"])
                if stripped != 1:
                    bad.append(f"removed {stripped} 'Powered by Grafana' "
                               f"badges, expected 1")
                if not bad:
                    break
                print(f"  .. panel {panel['panelId']} attempt {attempt + 1}: "
                      f"{'; '.join(bad)}", file=sys.stderr)
                page.wait_for_timeout(3000)
            problems += [f"panel {panel['panelId']}: {p}" for p in bad]
            tmp = WORK / f"out/{shot['id']}-p{i}.png"
            tmp.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(tmp))
            shots.append(tmp)
            ctx.close()
    finally:
        browser.close()

    stack(shots, out, int(shot.get("gapPx", 10) * scale),
          shot.get("gapColour", "white"))
    return {"panels": shot["panels"], "problems": problems,
            "composition": ("one d-solo panel" if len(shots) == 1 else
                            f"{len(shots)} d-solo panels stacked, "
                            f"{shot.get('gapPx', 10)} px apart")}


def capture_page(shot: dict, out: pathlib.Path, pw, args) -> dict:
    width = shot.get("width", 720)
    height = shot.get("height", 520)
    scale = shot.get("scale", 3)
    browser = pw.chromium.launch(args=shot.get("browserArgs", []))
    try:
        ctx = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=scale,
            color_scheme="light",
        )
        page = ctx.new_page()
        page.goto(shot["url"], wait_until=shot.get("waitUntil", "networkidle"),
                  timeout=120_000)
        if shot.get("css"):
            page.add_style_tag(content=shot["css"])
        for step in shot.get("steps", []):
            act = step["do"]
            if act == "click":
                page.click(step["selector"], timeout=step.get("timeout", 30_000))
            elif act == "fill":
                page.fill(step["selector"], step["text"])
            elif act == "press":
                page.press(step["selector"], step["key"])
            elif act == "wait":
                page.wait_for_timeout(step["ms"])
            elif act == "waitFor":
                page.wait_for_selector(step["selector"],
                                       timeout=step.get("timeout", 60_000))
            elif act == "eval":
                page.evaluate(step["script"])
            elif act == "evalFile":
                src = (ROOT / step["file"]).read_text()
                print("  ..", step["file"], "->", page.evaluate(src))
            elif act == "scroll":
                page.evaluate(f"window.scrollTo(0, {step['y']})")
        problems = []
        how = "one page capture"
        if shot.get("stream"):
            how, bad = capture_stream(page, shot["stream"], out)
            problems += bad
        elif shot.get("selectors"):
            parts = []
            for i, sel in enumerate(shot["selectors"]):
                tmp = WORK / f"out/{shot['id']}-e{i}.png"
                tmp.parent.mkdir(parents=True, exist_ok=True)
                page.locator(sel).first.screenshot(path=str(tmp))
                parts.append(tmp)
            stack(parts, out, int(shot.get("gapPx", 10) * scale),
                  shot.get("gapColour", "white"))
            how = (f"{len(parts)} element captures stacked, "
                   f"{shot.get('gapPx', 10)} px apart")
        elif shot.get("selector"):
            page.locator(shot["selector"]).first.screenshot(path=str(out))
            how = "one element capture"
        else:
            page.screenshot(path=str(out), clip=shot.get("clip"))
        if shot.get("checkClean"):
            problems += assert_clean(page, shot["id"])
        ctx.close()
    finally:
        browser.close()
    return {"url": shot["url"], "problems": problems, "composition": how}


def capture_stream(page, spec: dict, out: pathlib.Path) -> tuple[str, list]:
    """Shoot an engine's web UI while it is still streaming.

    A 135M model on a laptop CPU finishes a short answer in about a
    second, so waiting for a fixed delay either catches two tokens or
    misses the stream entirely. This polls, keeps overwriting the file
    while the stop control is up and enough of the answer has landed,
    and stops when the stream does -- so the file left behind is the
    last frame that was genuinely mid-stream.
    """
    import time

    stop_sel = spec["stopSelector"]
    deadline = time.time() + spec.get("timeoutMs", 60_000) / 1000
    shots, last = 0, 0
    while time.time() < deadline:
        streaming = page.locator(stop_sel).count() > 0
        chars = len(page.inner_text("body"))
        if streaming and chars >= spec.get("minChars", 400) and chars > last:
            page.screenshot(path=str(out))
            shots += 1
            last = chars
        if shots and not streaming:
            break
        page.wait_for_timeout(spec.get("pollMs", 40))
    if not shots:
        return "no frame captured", [
            "never saw the stream with enough of an answer on screen"
        ]
    return (f"the last of {shots} frames taken while the answer was "
            f"still streaming"), []


# --------------------------------------------------------------- driver


def run(shot: dict, args) -> pathlib.Path:
    from PIL import Image
    from playwright.sync_api import sync_playwright

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / f"{shot['id']}.png"

    with sync_playwright() as pw:
        info = browser_info(pw)
        if shot["kind"] == "grafana":
            extra = capture_grafana(shot, png, pw, args)
        else:
            extra = capture_page(shot, png, pw, args)

    im = Image.open(png)
    side = {
        "id": shot["id"],
        "figure": shot["figure"],
        "chapter": shot["chapter"],
        "what": shot["what"],
        "captured": dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "machine": shot.get("machine", MACHINE),
        "kind": shot["kind"],
        "data": [
            {"path": p, "sha256": sha256(ROOT / p)} for p in shot.get("data", [])
        ],
        "provenance": shot["provenance"],
        "tools": shot["tools"],
        "images": shot.get("images", []),
        "browser": info,
        "viewport": {
            "cssWidth": shot.get("width"),
            "deviceScaleFactor": shot.get("scale"),
            "colorScheme": "light",
        },
        "png": {
            "width": im.width,
            "height": im.height,
            "sha256": sha256(png),
            "bytes": png.stat().st_size,
        },
        "print": {
            "widthIn": PRINT_WIDTH_IN,
            "dpi": round(im.width / PRINT_WIDTH_IN),
        },
        "caption": shot["caption"],
        "notes": shot.get("notes", []),
    }
    side.update({k: v for k, v in extra.items() if k != "problems"})
    if shot["kind"] == "grafana":
        side["range"] = {
            "fromMs": shot["from"],
            "toMs": shot["to"],
            "fromUTC": dt.datetime.fromtimestamp(
                shot["from"] / 1000, dt.timezone.utc
            ).isoformat(),
            "toUTC": dt.datetime.fromtimestamp(
                shot["to"] / 1000, dt.timezone.utc
            ).isoformat(),
        }
        side["dashboards"] = dashboard_files()
        side["replayStack"] = {
            "prometheus": env("PROMETHEUS_IMAGE"),
            "grafana": env("GRAFANA_IMAGE"),
            "rebuild": f"bash screens/replay.sh {shot['replay']} "
                       + " ".join(shot.get("data", [])),
        }
    (out_dir / f"{shot['id']}.json").write_text(json.dumps(side, indent=2) + "\n")

    for p in extra.get("problems", []):
        print(f"  !! {p}", file=sys.stderr)
    print(f"  {png}  {im.width}x{im.height}  "
          f"{round(im.width / PRINT_WIDTH_IN)} dpi at {PRINT_WIDTH_IN} in")
    return png


MACHINE = "Apple M2 Pro, 16 GB, OrbStack 29.4.0 (linux/arm64 VM)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--list", action="store_true")
    ap.add_argument(
        "--out",
        default=str(
            pathlib.Path.home()
            / "WebstormProjects/book-inference-engineering/en/content/chapters/images"
        ),
    )
    args = ap.parse_args()
    if args.list:
        for s in SHOTS:
            print(f"{s['id']:24} ch{s['chapter']}  {s['kind']:8} {s['what']}")
        return 0
    todo = [s for s in SHOTS if not args.ids
            or s["id"] in args.ids
            or s["id"].split("-")[0] in args.ids]
    if not todo:
        print("no such shot", file=sys.stderr)
        return 1
    for s in todo:
        print(f"== {s['id']}")
        run(s, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
