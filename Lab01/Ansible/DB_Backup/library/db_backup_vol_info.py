from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r'''
---
module: db_backup_vol_info

short_description: This is my test module

# If this is part of a collection, you need to use semantic versioning,
# i.e. the version is of the form "2.5.0" and not "2.4".
version_added: "1.0.0"

description: This is my longer description explaining my test module.

options:
    name:
        description: This is the message to send to the test module.
        required: true
        type: str
    new:
        description:
            - Control to demo if the result of this module is changed or not.
            - Parameter description can be a list as well.
        required: false
        type: bool
# Specify this value according to your collection
# in format of namespace.collection.doc_fragment_name
# extends_documentation_fragment:
#     - my_namespace.my_collection.my_doc_fragment_name

author:
    - Your Name (@yourGitHubHandle)
'''

EXAMPLES = r'''
# Pass in a message
- name: Test with a message
  my_namespace.my_collection.my_test:
    name: hello world

# pass in a message and have changed true
- name: Test with a message and changed output
  my_namespace.my_collection.my_test:
    name: hello world
    new: true

# fail the module
- name: Test failure of the module
  my_namespace.my_collection.my_test:
    name: fail me
'''

RETURN = r'''
# These are examples of possible return values, and in general should use other names for return values.
original_message:
    description: The original name param that was passed in.
    type: str
    returned: always
    sample: 'hello world'
message:
    description: The output message that the test module generates.
    type: str
    returned: always
    sample: 'goodbye'
'''

from ansible.module_utils.basic import AnsibleModule

def db_backup_vol_size(db_size,max_vol_size) -> None:
    """Ingest Database Size and Maximum volume size to provision"""
    """Create a varibles for the IMG and LOG volume sizes that includes multipliers related to function"""
    """IMG multiplier is 1.2 and LOG multiplier is 0.5"""
    db_size_img = db_size * 1.2
    db_size_log = db_size * 0.5

    """IMG Volume calculations"""
    vol_cnt_img_int = int(0)
    vol_size_img = int(0)

    vol_cnt_img_float = db_size_img / max_vol_size

    if vol_cnt_img_float <= 1:
        vol_cnt_img_int = int(1)
    else:
        while vol_cnt_img_float > 0:
            vol_cnt_img_int = vol_cnt_img_int + 1
            vol_cnt_img_float = vol_cnt_img_float - 1

    vol_size_img = db_size_img / vol_cnt_img_int

    vol_size_img_int = int(vol_size_img)

    """LOG Volume calculations"""
    vol_cnt_log_int = int(0)
    vol_size_log = int(0)

    vol_cnt_log_float = db_size_log / max_vol_size

    if vol_cnt_log_float <= 1:
        vol_cnt_log_int = int(1)
    else:
        while vol_cnt_log_float > 0:
            vol_cnt_log_int = vol_cnt_log_int + 1
            vol_cnt_log_float = vol_cnt_log_float - 1

    vol_size_log = db_size_log / vol_cnt_log_int

    vol_size_log_int = int(vol_size_log)

    result = {
        'volume_size_img': vol_size_img_int,
        'volume_count_img': vol_cnt_img_int,
        'volume_size_log': vol_size_log_int,
        'volume_count_log': vol_cnt_log_int
    }

    return result

def run_module():
    module_args = dict(
        DB_SIZE=dict(type='int', required=True),
        MAX_VOL_SIZE=dict(type='int', required=True)
    )

    output = dict(changed=False, message="")

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    parameters = module.params
    db_size = parameters["DB_SIZE"]
    max_vol_size = parameters["MAX_VOL_SIZE"]

    result = db_backup_vol_size(db_size, max_vol_size)

    module.exit_json(**result)

def main():
    run_module()

# start
if __name__ == "__main__":
    run_module()