#!/usr/bin/env python3
"""Waybar custom module: live CPU history as a block-character sparkline.

Runs as a long-lived process (no "interval" in the module config): it prints
one JSON line every INTERVAL seconds and keeps the last SAMPLES readings in
memory, so the sparkline scrolls left as new samples arrive.

    {"text": "▁▁▂▅▃▂▇▄", "tooltip": "...", "class": "low|mid|high", "percentage": 23}

Bar height uses a square-root scale, so light load (5-20%) is still visible
instead of sitting on the lowest block; 100% is always a full block.

Exits by itself when Waybar goes away (its end of the pipe closes, so the next
write fails), so a Waybar reload never leaves an old copy running.
Needs nothing but Python 3 and /proc.
"""
import json
import math
import os
import sys
import time
from collections import deque

SAMPLES = int(os.environ.get("CPU_SPARK_SAMPLES", "8"))         # characters shown
INTERVAL = float(os.environ.get("CPU_SPARK_INTERVAL", "2"))     # seconds per sample
MID, HIGH = 60, 85                                              # % thresholds for CSS classes
BLOCKS = "▁▂▃▄▅▆▇█"


def read_cpu():
    """(total, idle) jiffies from the aggregate 'cpu' line of /proc/stat.

    Fields: user nice system idle iowait irq softirq steal. guest/guest_nice
    are already counted inside user/nice, so they are left out."""
    with open("/proc/stat") as f:
        fields = f.readline().split()[1:9]
    v = [int(x) for x in fields] + [0] * (8 - len(fields))
    return sum(v), v[3] + v[4]


def block(pct):
    return BLOCKS[min(len(BLOCKS) - 1, int(math.sqrt(max(0.0, pct) / 100.0) * len(BLOCKS)))]


def emit(hist):
    now = hist[-1]
    try:
        l1, l5, l15 = os.getloadavg()
    except OSError:
        l1 = l5 = l15 = 0.0
    window = int(SAMPLES * INTERVAL)
    tooltip = "CPU {:.0f}%  ·  peak {:.0f}% ({}s)\nload {:.2f} {:.2f} {:.2f}  ·  {} cores".format(
        now, max(hist), window, l1, l5, l15, os.cpu_count() or 1)
    cls = "high" if now >= HIGH else "mid" if now >= MID else "low"
    # ASCII-only JSON (▁ etc.): safe under any locale Waybar was started in
    print(json.dumps({"text": "".join(block(p) for p in hist), "tooltip": tooltip,
                      "class": cls, "percentage": round(now)}), flush=True)


def main():
    hist = deque([0.0] * SAMPLES, maxlen=SAMPLES)
    prev = read_cpu()
    try:
        emit(hist)                              # show something immediately
        time.sleep(min(INTERVAL, 0.5))          # short first interval, then the normal one
        while True:
            cur = read_cpu()
            d_total, d_idle = cur[0] - prev[0], cur[1] - prev[1]
            prev = cur
            hist.append(100.0 * (d_total - d_idle) / d_total if d_total > 0 else 0.0)
            emit(hist)
            time.sleep(INTERVAL)
    except (BrokenPipeError, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    try:
        main()
    finally:
        try:
            sys.stdout.close()
        except Exception:
            pass
