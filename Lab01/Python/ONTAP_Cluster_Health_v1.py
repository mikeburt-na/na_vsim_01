#!/usr/bin/env python3
import requests
import urllib3
import sys
from pprint import pprint

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === CONFIGURATION ===
CLUSTER_IP = "Cluster1"          # Change to your cluster management IP or hostname
USERNAME = "admin"               # Change or use input()
PASSWORD = "Netapp1!"            # Change or use getpass()
# =====================

BASE_URL = f"https://{CLUSTER_IP}/api"
session = requests.Session()
session.auth = (USERNAME, PASSWORD)
session.verify = False
session.headers.update({"Accept": "application/json"})

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
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
    # 1. Node Health
    nodes = get("/cluster/nodes")
    unhealthy_nodes = [n for n in nodes if n.get("state", "").lower() != "up"]
    node_status = "Good" if not unhealthy_nodes else "Bad"

    # 2. HA State Detection (works when HA is disabled — no ha field)
    ha_capable = any("ha" in node for node in nodes)
    ha_status_actual = "enabled" if ha_capable else "disabled"
    node_count = len(nodes)

    if node_count == 2:
        ha_status = "Good" if ha_status_actual == "enabled" else "Bad"
        ha_detail = "HA must be ENABLED" if ha_status == "Bad" else "HA is ENABLED"
    else:
        ha_status = "Good" if ha_status_actual == "disabled" else "Bad"
        ha_detail = "HA must be DISABLED" if ha_status == "Bad" else "HA is DISABLED"

    # 3. Critical Alerts
    alerts = get("/private/support/alerts")
    critical_alerts = [a for a in alerts if a.get("severity") in ["error", "emergency"]]
    alert_status = "Good" if not critical_alerts else "Bad"

    # 4. Aggregates
    aggs = get("/storage/aggregates")
    offline_aggs = [a for a in aggs if a.get("state") != "online"]
    agg_status = "Good" if not offline_aggs else "Bad"

    # 5. Volumes
    vols = get("/storage/volumes")
    offline_vols = [v for v in vols if v.get("state") != "online"]
    vol_status = "Good" if not offline_vols else "Bad"

    # 6. Disks
    disks = get("/storage/disks")
    broken_disks = [d for d in disks if d.get("state") in ["broken", "maintenance", "failed"]]
    disk_status = "Good" if not broken_disks else "Bad"

    # 7. Shelves
    shelves = get("/storage/shelves")
    bad_shelves = [s for s in shelves if s.get("state") != "online"]
    shelf_status = "Good" if not bad_shelves else "Bad"

    # 8. Sensors (environmental)
    sensors = get("/cluster/sensors")
    bad_sensors = [s for s in sensors if s.get("state") != "normal"]
    sensor_status = "Good" if not bad_sensors else "Bad"

    # Overall
    all_statuses = [node_status, ha_status, alert_status, agg_status, vol_status, disk_status, shelf_status, sensor_status]
    overall = "Good" if all(s == "Good" for s in all_statuses) else "Bad"

    # === OUTPUT ===
    print(f"{BOLD}NetApp ONTAP Cluster Health Check - {CLUSTER_IP}{RESET}\n")

    print_status("Node Health", node_status, f"({len(unhealthy_nodes)} unhealthy)" if unhealthy_nodes else "")
    print_status("HA Configuration", ha_status, f"({node_count} nodes) – {ha_detail}")
    print_status("Critical Alerts", alert_status, f"({len(critical_alerts)} critical)" if critical_alerts else "")
    print_status("Aggregates", agg_status, f"({len(offline_aggs)} offline)" if offline_aggs else "")
    print_status("Volumes", vol_status, f"({len(offline_vols)} offline)" if offline_vols else "")
    print_status("Disks", disk_status, f"({len(broken_disks)} failed)" if broken_disks else "")
    print_status("Shelves", shelf_status, f"({len(bad_shelves)} bad)" if bad_shelves else "")
    print_status("Sensors", sensor_status, f"({len(bad_sensors)} faulty)" if bad_sensors else "")

    print(f"\n{BOLD}Overall Cluster Health: ", end="")
    print(f"{GREEN}{BOLD}GOOD{RESET}" if overall == "Good" else f"{RED}{BOLD}BAD - ACTION REQUIRED{RESET}")

    if overall == "Bad":
        sys.exit(1)

except Exception as e:
    print(f"{RED}Failed to connect or query cluster: {e}{RESET}")
    sys.exit(1)