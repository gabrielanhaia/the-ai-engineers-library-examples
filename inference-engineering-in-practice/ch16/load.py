# ch16/load.py
"""Open-loop load in phases for the ch16 lab, and the timeline.

Each phase is RATE:SECONDS. Requests start on a fixed schedule
whatever the server is doing (an open loop), each on a new
connection so the Service can spread them over new replicas. Every
2 s a watcher records the queue (Prometheus) and the replicas
(HPA and Deployment), so the scale-out can be read off one file.
"""
import argparse
import http.client
import json
import subprocess
import threading
import time
import urllib.parse

BODY = json.dumps({
    "model": "smollm2-360m", "max_tokens": 100, "ignore_eos": True,
    "stream": True,
    "messages": [{"role": "user", "content": "Tell me a story."}]})


def request(host, port, t0, phase, out, lock):
    sent = time.monotonic()
    rec = {"t": round(sent - t0, 3), "phase": phase, "ttft": None}
    try:
        conn = http.client.HTTPConnection(host, port, timeout=600)
        conn.request("POST", "/v1/chat/completions", BODY,
                     {"Content-Type": "application/json"})
        resp = conn.getresponse()
        rec["status"] = resp.status
        for line in resp:
            if rec["ttft"] is None and b'"content"' in line:
                rec["ttft"] = round(time.monotonic() - sent, 3)
        conn.close()
    except OSError as e:
        rec["status"], rec["error"] = 0, str(e)
    rec["e2e"] = round(time.monotonic() - sent, 3)
    with lock:
        out.write(json.dumps(rec) + "\n")


def kubectl_json(*args):
    out = subprocess.run(["kubectl", *args, "-o", "json"],
                         capture_output=True, text=True)
    return json.loads(out.stdout) if out.returncode == 0 else {}


def prom(query):
    path = ("/api/v1/namespaces/default/services/prometheus:9090"
            "/proxy/api/v1/query?query=" + urllib.parse.quote(query))
    out = subprocess.run(["kubectl", "get", "--raw", path],
                         capture_output=True, text=True)
    try:
        res = json.loads(out.stdout)["data"]["result"]
        return float(res[0]["value"][1]) if res else 0.0
    except (ValueError, KeyError):
        return None


def watch(t0, stop, path):
    with open(path, "w") as f:
        f.write("ts,t,waiting,running,desired,replicas,ready\n")
        while not stop.is_set():
            t = time.monotonic() - t0
            hpa = kubectl_json("get", "hpa", "keda-hpa-smollm2-sim")
            dep = kubectl_json("get", "deploy", "smollm2-sim")
            row = [f"{time.time():.1f}", f"{t:.1f}",
                   prom("sum(vllm:num_requests_waiting)"),
                   prom("sum(vllm:num_requests_running)"),
                   hpa.get("status", {}).get("desiredReplicas"),
                   dep.get("spec", {}).get("replicas"),
                   dep.get("status", {}).get("readyReplicas", 0)]
            f.write(",".join("" if v is None else str(v)
                             for v in row) + "\n")
            f.flush()
            stop.wait(2)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="ch16-control-plane:30080")
    p.add_argument("--phases", default="1:30,4:120,0.5:90")
    p.add_argument("--out", required=True)
    p.add_argument("--timeline", required=True)
    a = p.parse_args()
    host, port = a.url.split(":")
    phases = [tuple(map(float, x.split(":")))
              for x in a.phases.split(",")]

    t0, lock = time.monotonic(), threading.Lock()
    stop = threading.Event()
    w = threading.Thread(target=watch, args=(t0, stop, a.timeline))
    w.start()
    threads, start = [], 0.0
    with open(a.out, "w") as out:
        for i, (rate, secs) in enumerate(phases):
            n = int(rate * secs)
            for k in range(n):
                at = start + k / rate
                time.sleep(max(0.0, t0 + at - time.monotonic()))
                th = threading.Thread(
                    target=request,
                    args=(host, int(port), t0, i, out, lock))
                th.start()
                threads.append(th)
            start += secs
            time.sleep(max(0.0, t0 + start - time.monotonic()))
        for th in threads:
            th.join()
        time.sleep(30)     # watch the scale-in after the last reply
    stop.set()
    w.join()


if __name__ == "__main__":
    main()
