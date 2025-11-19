#!/usr/bin/env python3
import requests
import urllib3
import json

urllib3.disable_warnings()

CLUSTER_IP = "Cluster1"
USERNAME = "admin"
PASSWORD = "Netapp1!"

session = requests.Session()
session.auth = (USERNAME, PASSWORD)
session.verify = False

def get(endpoint):
    url = f"https://{CLUSTER_IP}/api{endpoint}"
    r = session.get(url)
    print(f"\n=== {endpoint} ===")
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print(json.dumps(r.json(), indent=2))
    elif r.status_code == 404:
        print("404 - Endpoint not found")
    else:
        print(r.text)

# Run these three - that's all we need
get("/storage/failover")
get("/cluster/nodes")
get("/cluster")

print("\nDone - copy/paste the full output back to me (especially the /storage/failover part)")