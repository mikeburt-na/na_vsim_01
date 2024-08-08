#!/usr/bin/python

# Copyright: (c) 2020, Mirko Van Colen mirko@netapp.com
# Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
import re
import requests
import sys
import urllib3

# Disable SSL certificate warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

summary = []
message = []
volume_exists = False  # important check, we don't want to trigger a vol move on a re-run

# convert bytes to megabytes
def b2m(bytes_value, decimal_places=2):
    megabytes_value = bytes_value / (1024 * 1024)
    return round(megabytes_value, decimal_places)

# Get aggregates using REST API
def get_aggregates_rest(cluster_mgmt_ip, username, password):
    url = f"https://{cluster_mgmt_ip}/api/storage/aggregates?fields=space.block_storage,volume_count,node.name"
    response = requests.get(url, auth=(username, password), verify=False)
    response_json = response.json()
    return response_json.get("records", [])

# Get volumes using REST API
def get_volumes_rest(cluster_mgmt_ip, username, password):
    url = f"https://{cluster_mgmt_ip}/api/storage/volumes?maxRecords=5000&fields=space.size,svm.name,aggregates"
    response = requests.get(url, auth=(username, password), verify=False)
    response_json = response.json()
    return response_json.get("records", [])

# Get existing volume information using REST API
def get_existing_volume_rest(cluster_mgmt_ip, username, password, volume_name, svm_name):
    url = f"https://{cluster_mgmt_ip}/api/storage/volumes?fields=aggregates&name={volume_name}&svm.name={svm_name}"
    response = requests.get(url, auth=(username, password), verify=False)
    response_json = response.json()
    return response_json.get("records", [])

# logging
def log(t):
    global summary
    summary.append(t)

# get aggregates
def get_aggregates(cluster_mgmt_ip, username, password, requested_size_mb, requested_volume_count=1, volume_name="", svm_name=""):
    result = []
    if volume_name and svm_name:
        existing_volume = get_existing_volume_rest(cluster_mgmt_ip, username, password, volume_name, svm_name)
        if existing_volume:
            o = existing_volume[0]["aggregates"][0]
            o["final_score"] = 0
            result.append(o)
            existing_aggregate = o["name"]
            log("Volume '{}' for svm '{}' already exists, returning aggregate '{}'".format(volume_name, svm_name, existing_aggregate))
            global volume_exists
            volume_exists = True
            return result

    aggregates = get_aggregates_rest(cluster_mgmt_ip, username, password)
    volumes = get_volumes_rest(cluster_mgmt_ip, username, password)
    if aggregates:
        for aggregate in aggregates:
            name = aggregate["name"]
            node = aggregate["node"]["name"]
            space = aggregate["space"]["block_storage"]
            volumes_for_aggregate = [
                volume
                for volume in volumes
                if volume["aggregates"][0]["name"] == name
            ]
            volume_count = len(volumes_for_aggregate)
            size_mb = b2m(space["size"])
            used_mb = b2m(space["used"]) + requested_size_mb
            available_mb = b2m(space["available"]) - requested_size_mb
            physical_used_mb = b2m(space["physical_used"]) + requested_size_mb
            provisioned_size_mb = b2m(sum(v["space"]["size"] for v in volumes_for_aggregate)) + requested_size_mb
            o = dict(
                name=name,
                node=node,
                size_mb=size_mb,
                available_mb=available_mb,
                used_mb=used_mb,
                used_pct=round(used_mb / size_mb * 100),
                physical_used_mb=physical_used_mb,
                physical_used_pct=round(physical_used_mb / size_mb * 100),
                volume_count=volume_count + requested_volume_count,
                provisioned_size_mb=provisioned_size_mb,
                provisioned_pct=round(provisioned_size_mb / size_mb * 100)
            )
            result.append(o)
        return result

# Function to rank and normalize ranks for each property with given weights and sort orders
def rank_normalize_sort(data_list, properties, weights, thresholds, sort_orders):
    for property_name, weight, threshold, sort_order in zip(properties, weights, thresholds, sort_orders):
        sorted_data = sorted(data_list, key=lambda x: x[property_name], reverse=not sort_order)
        for order, item in enumerate(sorted_data, start=1):
            item["weighted_rank_" + property_name] = order / len(data_list) * weight
            if item[property_name] > threshold if sort_order else item[property_name] <= threshold:
                item["excluded_by_threshold_on_" + property_name] = True

    filtered_data_list = []
    for item in data_list:
        item["final_score"] = sum(item.get("weighted_rank_" + prop, 0) for prop in properties)
        exclude = False
        for key, value in item.items():
            m = re.match("excluded_by_threshold_on_(.*)", key)
            if m:
                log("Excluded aggregate '{}' by threshold on '{}'".format(item["name"], m.group(1)))
                exclude = True
                break
        if not exclude:
            filtered_data_list.append(item)

    return sorted(filtered_data_list, key=lambda x: x["final_score"])

# filter by name and node using includes and excludes
def filter_data_list(data_list, exclude_name_regex="", include_name_regex="",
                     exclude_node_regex="", include_node_regex="",
                     names_to_exclude=[], nodes_to_exclude=[]):
    filtered_data_list = []
    for item in data_list:
        if (not exclude_name_regex or not re.match(exclude_name_regex, item["name"])) and \
                (not include_name_regex or re.match(include_name_regex, item["name"])) and \
                (not exclude_node_regex or not re.match(exclude_node_regex, item["node"])) and \
                (not include_node_regex or re.match(include_node_regex, item["node"])) and \
                item["name"] not in names_to_exclude and item["node"] not in nodes_to_exclude:
            filtered_data_list.append(item)
        else:
            log("Excluded aggregate '{}' on node '{}'".format(item["name"], item["node"]))
    return filtered_data_list

# main code
def run_module():
    module_args = dict(
        hostname=dict(type='str', required=True),
        username=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        debug=dict(type='bool', required=False, default=False),
        https=dict(type='bool', required=False),
        validate_certs=dict(type='bool', required=False),
        volume_name=dict(type='str', required=False, default=''),
        svm_name=dict(type='str', required=False, default=''),
        size_mb=dict(type='int', required=False, default=0),
        weight_volume_count=dict(type='float', required=False, default=0),
        weight_used_pct=dict(type='float', required=False, default=0),
        weight_provisioned_pct=dict(type='float', required=False, default=0),
        weight_available_space=dict(type='float', required=False, default=1),
        threshold_volume_count=dict(type='int', required=False, default=5000),
        threshold_used_pct=dict(type='int', required=False, default=100000000000),
        threshold_provisioned_pct=dict(type='int', required=False, default=100000000000),
        threshold_available_space=dict(type='int', required=False, default=-1000000000000),
        exclude_name_regex=dict(type='str', required=False, default=''),
        include_name_regex=dict(type='str', required=False, default=''),
        exclude_node_regex=dict(type='str', required=False, default=''),
        include_node_regex=dict(type='str', required=False, default=''),
        names_to_exclude=dict(type='str', required=False, default=[]),
        nodes_to_exclude=dict(type='str', required=False, default=[])
    )

    result = dict()
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    global summary
    global message
    err = None
    aggregates = []
    best_candidate = None

    hostname = module.params['hostname']
    username = module.params['username']
    password = module.params['password']
    debug = module.params['debug']
    requested_size_mb = module.params['size_mb']
    volume_name = module.params['volume_name']
    svm_name = module.params['svm_name']
    weight_volume_count = module.params['weight_volume_count']
    weight_used_pct = module.params['weight_used_pct']
    weight_provisioned_pct = module.params['weight_provisioned_pct']
    weight_available_space = module.params['weight_available_space']
    threshold_volume_count = module.params['threshold_volume_count']
    threshold_used_pct = module.params['threshold_used_pct']
    threshold_provisioned_pct = module.params['threshold_provisioned_pct']
    threshold_available_space = module.params['threshold_available_space']
    exclude_name_regex = module.params['exclude_name_regex']
    include_name_regex = module.params['include_name_regex']
    exclude_node_regex = module.params['exclude_node_regex']
    include_node_regex = module.params['include_node_regex']
    names_to_exclude = module.params['names_to_exclude']
    nodes_to_exclude = module.params['nodes_to_exclude']

    properties_to_rank = ["volume_count", "used_pct", "provisioned_pct", "available_mb"]
    weights = [weight_volume_count, weight_used_pct, weight_provisioned_pct, weight_available_space]
    sort_orders = [True, True, True, False]
    thresholds = [threshold_volume_count, threshold_used_pct, threshold_provisioned_pct, threshold_available_space]

    try:
        if exclude_name_regex and include_name_regex:
            raise AttributeError("'include_name_regex' and 'include_name_regex' are mutually exclusive")
        if exclude_node_regex and include_node_regex:
            raise AttributeError("'include_node_regex' and 'include_node_regex' are mutually exclusive")
        if exclude_name_regex and names_to_exclude:
            raise AttributeError("'exclude_name_regex' and 'names_to_exclude' are mutually exclusive")
        if exclude_node_regex and nodes_to_exclude:
            raise AttributeError("'exclude_node_regex' and 'nodes_to_exclude' are mutually exclusive")

        aggregates = get_aggregates(hostname, username, password, requested_size_mb, 1, volume_name, svm_name)
        result["all_aggregates"] = aggregates
        print(*message, file=sys.stdout)

        global volume_exists
        if not volume_exists:
            aggregates = filter_data_list(aggregates, exclude_name_regex, include_name_regex, exclude_node_regex,
                                          include_node_regex, names_to_exclude, nodes_to_exclude)
            aggregates = rank_normalize_sort(aggregates, properties_to_rank, weights, thresholds, sort_orders)
        else:
            pass

        result["valid_candidates"] = aggregates

        if aggregates:
            best_candidate = aggregates[0]
            log("aggregate '{}' is our best choice".format(best_candidate["name"]))
            log("scores : ")
            for item in aggregates:
                log("- {} -> {}".format(item["name"], item["final_score"]))
            result["aggregate"] = best_candidate
        else:
            raise LookupError("No suitable aggregates found")

    except Exception as e:
        log(repr(e))
        err = str(e)

    result["summary"] = summary

    if err:
        module.fail_json(err, **result)
    else:
        module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
