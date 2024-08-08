from __future__ import absolute_import, division, print_function

__metaclass__ = type

from pyVmomi import vim
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common_vmware_utils import connect, get_obj, wait_for_tasks


def delete_virtual_disk(si, vm_obj, disk_uuid):
    """Deletes virtual Disk based on disk number
    :param si: Service Instance
    :param vm_obj: Virtual Machine Object
    :return: True if success
    """

    virtual_hdd_device = None
    for dev in vm_obj.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualDisk):
            if hasattr(dev.backing, "deviceName"):
                temp_hdd_device = dev
                if temp_hdd_device.backing.deviceName == disk_uuid:
                    virtual_hdd_device = temp_hdd_device
            else:
                continue

    if not virtual_hdd_device:
        return f"RDM not present to delete."

    virtual_hdd_spec = vim.vm.device.VirtualDeviceSpec()
    virtual_hdd_spec.fileOperation = (
        vim.vm.device.VirtualDeviceSpec.FileOperation.destroy
    )
    virtual_hdd_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
    virtual_hdd_spec.device = virtual_hdd_device

    spec = vim.vm.ConfigSpec()
    spec.deviceChange = [virtual_hdd_spec]
    task = vm_obj.ReconfigVM_Task(spec=spec)
    wait_for_tasks(si=si, tasks=[task])
    return f"VM HDD {disk_uuid} deleted successfully."


def run_module():

    module_args = dict(
        VM_NAME=dict(required=True, type="str"),
        HOST_NAME=dict(required=True, type="str"),
        USER_NAME=dict(required=True, type="str"),
        PASSWORD=dict(required=True, type="str"),
        PORT=dict(required=False, type="int", default=443),
        DISK_UUID=dict(required=True, type="str"),
    )

    output = dict(changed=False, message="")

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    parameters = module.params
    host_name = parameters["HOST_NAME"]
    username = parameters["USER_NAME"]
    password = parameters["PASSWORD"]
    vm_name = parameters["VM_NAME"]
    port = parameters["PORT"]
    disk_uuid = parameters["DISK_UUID"]

    si = connect(host_name, username, password, port)
    content = si.RetrieveContent()
    vm_obj = get_obj(content, [vim.VirtualMachine], vm_name)

    if vm_obj:
        result = delete_virtual_disk(si, vm_obj, disk_uuid)
        output["changed"] = True
        output["message"] = result
        module.exit_json(**output)
    else:
        output["message"] = "VM not found"
        module.fail_json(msg=output["message"], **output)


# start
if __name__ == "__main__":
    run_module()