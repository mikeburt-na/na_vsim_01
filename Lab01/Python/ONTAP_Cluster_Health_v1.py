#!/usr/bin/env python3
import requests
import urllib3
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === CONFIGURATION ===
CLUSTER_IP = "Cluster1"          # Change to your cluster IP/hostname
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
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

def get(endpoint, required=False):
    url = f"{BASE_URL}{endpoint}"
    r = session.get(url)
    if r.status_code == 404 and not required:
        return []
    r.raise_for_status()
    return r.json().get("records", []) if "records" in r.json() else r.json()

def print_status(component, status, details=""):
    color = GREEN if status == "Good" else RED
    print(f"{color}{BOLD}{component:<20}: {status}{RESET} {details}")

try:
    nodes = get("/cluster/nodes")
    node_count = len(nodes)

    # === CORRECT HA DETECTION THAT WORKS ON ALL ONTAP VERSIONS ===
    ha_enabled = False
    try:
        failover = get("/storage/failover")
        ha_enabled = any(node.get("enabled", False) for node in failover)
    except:
        # Fallback: check node HA fields (works on older versions and vsim)
        ha_enabled = any("ha" in node and node["ha"].get("enabled", False) for node in nodes)

    if node_count == 2:
        ha_status = "Good" if ha_enabled else "Bad"
        ha_detail = "HA & Storage Failover ENABLED" if ha_enabled else "HA & Storage Failover DISABLED (expected ENABLED)"
    else:
        ha_status = "Good" if not ha_enabled else "Bad"
        ha_detail = "HA correctly DISABLED" if not ha_enabled else "HA incorrectly ENABLED"

    # === Rest of checks ===
    unhealthy_nodes = [n for n in nodes if n.get("state") != "up"]
    node_status = "Good" if not unhealthy_nodes else "Bad"

    alerts = get("/private/support/alerts")
    critical_alerts = [a for a in alerts if a.get("severity", "").lower() in ["error", "emergency"]]
    alert_status = "Good" if not critical_alerts else "Bad"

    aggs = get("/storage/aggregates")
    offline_aggs = [a for a in aggs if a.get("state") != "online"]
    agg_status = "Good" if not offline_aggs else "Bad"

    vols = get("/storage/volumes")
    offline_vols = [v for v in vols if v.get("state") != "online"]
    vol_status = "Good" if not offline_vols else "Bad"

    disks = get("/storage/disks")
    broken_disks = [d for d in disks if d.get("state") in ["broken", "maintenance", "failed"]]
    disk_status = "Good" if not broken_disks else "Bad"

    shelves = get("/storage/shelves")
    bad_shelves = [s for s in shelves if s.get("state") != "online"]
    shelf_status = "Good" if not bad_shelves else "Bad"

    sensors = get("/cluster/sensors")
    bad_sensors = [s for s in sensors if s.get("state") != "normal"]
    sensor_status = "Good" if not bad_sensors else "Bad"

    # Overall
    all_statuses = [node_status, ha_status, alert_status, agg_status, vol_status, disk_status, shelf_status, sensor_status]
    overall = "Good" if all(s == "Good" for s in all_statuses) else "Bad"

    print(f"{BOLD}NetApp ONTAP Cluster Health Check - {CLUSTER_IP}{RESET}\n")

    print_status("Node Health", node_status, f"({len(unhealthy_nodes)} unhealthy)" if unhealthy_nodes else "")
    print_status("HA Configuration", ha_status, f"({node_count} nodes) – {ha_detail}")
    print_status("Critical Alerts", alert_status, f"({len(critical_alerts)} found)" if critical_alerts else "")
    print_status("Aggregates", agg_status, f"({len(offline_aggs)} offline)" if offline_aggs else "")
    print_status("Volumes", vol_status, f"({len(offline_vols)} offline)" if offline_vols else "")
    print_status("Disks", disk_status, f"({len(broken_disks)} failed)" if broken_disks else "")
    print_status("Shelves", shelf_status, f"({len(bad_shelves)} bad)" if bad_shelves else "")
    print_status("Sensors", sensor_status, f"({len(bad_sensors)} faulty)" if bad_sensors else "")

    print(f"\n{BOLD}Overall Cluster Health:", end=" ")
    if overall == "Good":
        print(f"{GREEN}{BOLD}GOOD{RESET}")
    else:
        print(f"{RED}{BOLD}BAD - ACTION REQUIRED{RESET}")
        sys.exit(1)

except Exception as e:
    print(f"{RED}Error: {e}{RESET}")
    sys.exit(1)