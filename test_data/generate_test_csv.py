"""
Generate a realistic mobile network performance CSV with:
- 2 superfluous header lines before actual CSV headers
- NODE_NAME, TIMESTAMP, NETWORK, MOID dimensional columns
- Performance counters with daily/weekly seasonality
- "--" null values scattered in
- Anomalies injected at known times
- Overnight low-volume periods
- 5-minute intervals over ~2 weeks
"""

import csv
import math
import random
from datetime import datetime, timedelta

random.seed(42)

# Config
START = datetime(2025, 1, 6, 0, 0)  # Monday
DURATION_DAYS = 14
INTERVAL_MINUTES = 5
NODES = ["NodeA_East", "NodeA_West", "NodeB_Central"]
NETWORKS = ["4G", "5G"]

# Total points per node/network combo
total_points = (DURATION_DAYS * 24 * 60) // INTERVAL_MINUTES  # 4032


def daily_pattern(hour: float) -> float:
    """Realistic daily traffic pattern: low overnight, peak morning/evening."""
    # Two peaks: morning rush ~9am, evening ~7pm
    morning = math.exp(-((hour - 9) ** 2) / 8)
    evening = math.exp(-((hour - 19) ** 2) / 10)
    overnight = 0.08  # baseline
    return overnight + 0.6 * morning + 0.4 * evening


def weekly_factor(weekday: int) -> float:
    """Weekday vs weekend: weekdays busier."""
    if weekday < 5:  # Mon-Fri
        return 1.0
    return 0.65  # Sat-Sun


def generate_row(ts: datetime, node: str, network: str, point_idx: int) -> dict:
    hour = ts.hour + ts.minute / 60.0
    weekday = ts.weekday()

    base_volume = daily_pattern(hour) * weekly_factor(weekday)

    # Node-specific scaling
    node_scale = {"NodeA_East": 1.0, "NodeA_West": 0.8, "NodeB_Central": 1.3}[node]
    net_scale = {"4G": 1.0, "5G": 0.6}[network]

    scale = base_volume * node_scale * net_scale

    # Connection Attempts: base ~50000 at peak, ~4000 overnight
    conn_attempts = max(0, int(50000 * scale + random.gauss(0, 500 * scale)))

    # Connection Successes: ~99.2% success rate normally
    success_rate = 0.992 + random.gauss(0, 0.002)
    # Overnight: slightly worse due to low volume noise
    if base_volume < 0.15:
        success_rate -= random.uniform(0, 0.015)
    success_rate = max(0.95, min(1.0, success_rate))
    conn_successes = int(conn_attempts * success_rate)
    conn_fails = conn_attempts - conn_successes

    # Handover Attempts
    ho_attempts = max(0, int(12000 * scale + random.gauss(0, 200 * scale)))
    ho_success_rate = 0.985 + random.gauss(0, 0.003)
    if base_volume < 0.15:
        ho_success_rate -= random.uniform(0, 0.02)
    ho_success_rate = max(0.93, min(1.0, ho_success_rate))
    ho_successes = int(ho_attempts * ho_success_rate)

    # Data Volume (GB)
    data_volume_gb = round(max(0, 150 * scale + random.gauss(0, 10 * scale)), 2)

    # Average Throughput (Mbps)
    avg_throughput = round(max(0.1, 85 * (0.7 + 0.3 * base_volume) + random.gauss(0, 5)), 1)
    if network == "5G":
        avg_throughput *= 2.5

    # Drop Rate (%)
    drop_rate = round(max(0, 0.8 + random.gauss(0, 0.2) - 0.3 * base_volume), 3)
    if base_volume < 0.15:
        drop_rate += random.uniform(0, 0.5)

    return {
        "NODE_NAME": node,
        "TIMESTAMP": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "NETWORK": network,
        "MOID": f"{node}_{network}_Cell1",
        "CONN_ATTEMPTS": conn_attempts,
        "CONN_SUCCESSES": conn_successes,
        "CONN_FAILS": conn_fails,
        "HO_ATTEMPTS": ho_attempts,
        "HO_SUCCESSES": ho_successes,
        "DATA_VOLUME_GB": data_volume_gb,
        "AVG_THROUGHPUT_MBPS": avg_throughput,
        "DROP_RATE_PCT": drop_rate,
    }


def inject_anomalies(rows: list[dict]) -> list[dict]:
    """Inject known anomalies at specific times."""
    anomaly_log = []

    for row in rows:
        ts = datetime.strptime(row["TIMESTAMP"], "%Y-%m-%d %H:%M:%S")

        # ANOMALY 1: Jan 9 14:00-16:00 — sudden spike in connection failures on NodeA_East/4G
        if (row["NODE_NAME"] == "NodeA_East" and row["NETWORK"] == "4G"
                and ts >= datetime(2025, 1, 9, 14, 0) and ts <= datetime(2025, 1, 9, 16, 0)):
            row["CONN_FAILS"] = int(row["CONN_FAILS"] * 8 + random.randint(500, 2000))
            row["CONN_SUCCESSES"] = row["CONN_ATTEMPTS"] - row["CONN_FAILS"]
            row["DROP_RATE_PCT"] = round(row["DROP_RATE_PCT"] * 4, 3)

        # ANOMALY 2: Jan 12 10:00-11:30 — throughput collapse across all NodeB_Central
        if (row["NODE_NAME"] == "NodeB_Central"
                and ts >= datetime(2025, 1, 12, 10, 0) and ts <= datetime(2025, 1, 12, 11, 30)):
            row["AVG_THROUGHPUT_MBPS"] = round(row["AVG_THROUGHPUT_MBPS"] * 0.15, 1)
            row["DATA_VOLUME_GB"] = round(row["DATA_VOLUME_GB"] * 0.3, 2)

        # ANOMALY 3: Jan 15 08:00-09:00 — handover failures spike on 5G nodes
        if (row["NETWORK"] == "5G"
                and ts >= datetime(2025, 1, 15, 8, 0) and ts <= datetime(2025, 1, 15, 9, 0)):
            row["HO_SUCCESSES"] = int(row["HO_ATTEMPTS"] * 0.7)  # 30% failure rate vs normal 1.5%

        # ANOMALY 4: Jan 17 20:00-22:00 — volume anomaly: unexpected traffic surge
        if (ts >= datetime(2025, 1, 17, 20, 0) and ts <= datetime(2025, 1, 17, 22, 0)):
            row["CONN_ATTEMPTS"] = int(row["CONN_ATTEMPTS"] * 3.5)
            row["CONN_SUCCESSES"] = int(row["CONN_ATTEMPTS"] * 0.98)
            row["CONN_FAILS"] = row["CONN_ATTEMPTS"] - row["CONN_SUCCESSES"]
            row["DATA_VOLUME_GB"] = round(row["DATA_VOLUME_GB"] * 3, 2)

    return rows


def add_null_values(rows: list[dict], null_rate: float = 0.003) -> list[dict]:
    """Scatter '--' null values randomly."""
    metric_cols = ["CONN_ATTEMPTS", "CONN_SUCCESSES", "CONN_FAILS",
                   "HO_ATTEMPTS", "HO_SUCCESSES", "DATA_VOLUME_GB",
                   "AVG_THROUGHPUT_MBPS", "DROP_RATE_PCT"]
    for row in rows:
        for col in metric_cols:
            if random.random() < null_rate:
                row[col] = "--"
    return rows


def main():
    rows = []
    ts = START
    for _ in range(total_points):
        for node in NODES:
            for network in NETWORKS:
                row = generate_row(ts, node, network, len(rows))
                rows.append(row)
        ts += timedelta(minutes=INTERVAL_MINUTES)

    rows = inject_anomalies(rows)
    rows = add_null_values(rows)

    output_path = "/Users/matthewroxburgh/Development/timeseries-anomaly/test_data/network_perf_jan2025.csv"

    with open(output_path, "w", newline="") as f:
        # Write 2 superfluous header lines (common in CSB exports)
        f.write("Export from OSS-RC | Network Performance Management | Generated 2025-01-20 03:00:00 UTC\n")
        f.write("Report: Cell_KPI_5min | Period: 2025-01-06 to 2025-01-19 | Granularity: 5 min\n")

        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {len(rows)} rows ({len(rows) // (len(NODES) * len(NETWORKS))} timestamps)")
    print(f"File: {output_path}")

    # Print file size
    import os
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Size: {size_mb:.1f} MB")

    print("\nInjected anomalies:")
    print("  1. Jan 9  14:00-16:00 — Connection failure spike (NodeA_East/4G)")
    print("  2. Jan 12 10:00-11:30 — Throughput collapse (NodeB_Central)")
    print("  3. Jan 15 08:00-09:00 — Handover failure spike (5G nodes)")
    print("  4. Jan 17 20:00-22:00 — Unexpected traffic surge (all nodes)")


if __name__ == "__main__":
    main()
