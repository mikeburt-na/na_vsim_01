#!/usr/bin/env python3
import requests
import urllib3
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === CONFIGURATION ===
CLUSTER_IP = "Cluster1"
USERNAME = "admin"
PASSWORD = "Netapp1!"
# =====================

BASE_URL = f"https://{CLUSTER_IP}/api"
session = requests.Session()
session.auth = (USERNAME, PASSWORD)
session.verify = False
session.headers.update({"Accept": "application/json"})

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

def get(endpoint):
    url = f"{BASE_URL}{endpoint}"
    r = session.get(url)
    r.raise_for_status()
    return r.json().get("records", []) if "records" in r.json() else r.json()

def print_status(component, status, details=""):
    color = GREEN if status == "Good" else RED
    print(f"{color}{BOLD}{component:<20}: {status}{RESET} {details}")

try:
    # Get nodes with HA fields forced
    nodes = get("/cluster/nodes?fields=ha")

    node_count = len(nodes)

    # Node health - only bad if "state" exists and != "up"
    unhealthy_nodes = [n for n in nodes if n.get("state") and n["state"] != "up"]
    node_status = "Good" if not unhealthy_nodes else "Bad"

    # HA detection - check ha.enabled on any node (all nodes have the same value)
    ha_enabled = any(node.get("ha", {}).get("enabled", False) for node in nodes)

    if node_count == 2:
        ha_status = "Good" if ha_enabled else "Bad"
        ha_detail = "HA & Storage Failover ENABLED" if ha_enabled else "HA & Storage Failover DISABLED"
    else:
        ha_status = "Good" if not ha_enabled else "Bad"
        ha_detail = "HA correctly DISABLED" if not ha_enabled else "HA incorrectly ENABLED"

    # Rest of checks
    alerts = get("/private/support/alerts")
    critical_alerts = [a for a in alerts if a.get("severity", "").lower() in ["error", "emergency"]]
    alert_status = "Good" if not critical_alerts else "Bad"

    aggs = get("/storage/aggregates")
    offline_aggs = [a for a in aggs if a.get("state") != "online"]
    agg_status = "Good" if not offline_aggs else "Bad"
    # Tesing
    agg_state = [b for b in (aggs or {}).get("state", [])]

    vols = get("/storage/volumes")
    offline_vols = [v for v in vols if v.get("state") != "online"]
    vol_status = "Good" if not offline_vols else "Bad"

    disks = get("/storage/disks")
    broken_disks = [d for d in disks if d.get("state") in ["broken", "maintenance", "failed", "failing"]]
    disk_status = "Good" if not broken_disks else "Bad"

    shelves = get("/storage/shelves")
    bad_shelves = [s for s in shelves if s.get("state") != "online"]
    shelf_status = "Good" if not bad_shelves else "Bad"

    sensors = get("/cluster/sensors")
    bad_sensors = [s for s in sensors if s.get("state") != "normal"]
    sensor_status = "Good" if not bad_sensors else "Bad"

    all_statuses = [node_status, ha_status, alert_status, agg_status, vol_status, disk_status, shelf_status, sensor_status]
    overall = "Good" if all(s == "Good" for s in all_statuses) else "Bad"

    print(f"{BOLD}NetApp ONTAP Cluster Health Check - {CLUSTER_IP} (9.16.1){RESET}\n")

    print_status("Node Health", node_status)
    print_status("HA Configuration", ha_status, f"({node_count} nodes) – {ha_detail}")
    print_status("Critical Alerts", alert_status)
    print_status("Aggregates", agg_status)
    print_status("Volumes", vol_status)
    print_status("Disks", disk_status)
    print_status("Shelves", shelf_status)
    print_status("Sensors", sensor_status)
    print_status("Test01", aggs)

    print(f"\n{BOLD}Overall Cluster Health:", end=" ")
    if overall == "Good":
        print(f"{GREEN}{BOLD}GOOD{RESET}")
    else:
        print(f"{RED}{BOLD}BAD - ACTION REQUIRED{RESET}")
        sys.exit(1)

except Exception as e:
    print(f"{RED}Error: {e}{RESET}")
    sys.exit(1)