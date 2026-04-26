import kratix_sdk as ks
import os
import requests
import logging
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)


PROXMOX_HOST = "https://192.168.0.100:8006"
PROXMOX_NODE = "proxmox"
PROXMOX_STORAGE = "CRUCIAL_SSD_512GB"
PROXMOX_ISO = "local:iso/Rocky-10.1-x86_64-minimal.iso"


def find_existing_vm(api_token, name):
    logging.info(f"Checking if VM '{name}' already exists in Proxmox")
    url = f"{PROXMOX_HOST}/api2/json/nodes/{PROXMOX_NODE}/qemu"
    headers = {"Authorization": f"PVEAPIToken={api_token}"}
    response = requests.get(url, headers=headers, verify=False, timeout=10)
    response.raise_for_status()
    vms = response.json().get("data", [])
    for vm in vms:
        if vm.get("name") == name:
            logging.info(f"VM '{name}' already exists with ID {vm['vmid']}")
            return vm
    logging.info(f"VM '{name}' does not exist — will create")
    return None


def get_next_vmid(api_token):
    logging.info("Fetching next available VM ID from Proxmox")
    url = f"{PROXMOX_HOST}/api2/json/cluster/nextid"
    headers = {"Authorization": f"PVEAPIToken={api_token}"}
    response = requests.get(url, headers=headers, verify=False, timeout=10)
    response.raise_for_status()
    vmid = int(response.json()["data"])
    logging.info(f"Next available VM ID: {vmid}")
    return vmid


def create_vm(api_token, name, cores, memory):
    vmid = get_next_vmid(api_token)
    logging.info(f"Calling Proxmox API to create VM '{name}' with ID {vmid}")
    url = f"{PROXMOX_HOST}/api2/json/nodes/{PROXMOX_NODE}/qemu"
    headers = {
        "Authorization": f"PVEAPIToken={api_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "vmid": vmid,
        "name": name,
        "cores": cores,
        "memory": memory,
        "ide2": f"{PROXMOX_ISO},media=cdrom",
        "scsi0": f"{PROXMOX_STORAGE}:10",
        "scsihw": "virtio-scsi-pci",
        "net0": "virtio,bridge=vmbr0,tag=20",
        "ostype": "l26",
        "boot": "order=ide2",
    }
    response = requests.post(url, headers=headers, json=payload, verify=False, timeout=10)
    response.raise_for_status()
    result = response.json()
    logging.info(f"Proxmox accepted VM creation — task ID: {result.get('data')}")
    return result


def main():
    logging.info("Pipeline started — reading resource request from Kratix")
    sdk = ks.KratixSDK()
    resource = sdk.read_resource_input()

    name = resource.get_name()
    cores = resource.get_value("spec.cores")
    memory = resource.get_value("spec.memory")
    logging.info(f"Resource request: name={name} cores={cores} memory={memory}")

    api_token = os.environ.get("PROXMOX_API_TOKEN")
    if not api_token:
        raise RuntimeError("PROXMOX_API_TOKEN environment variable not set")

    existing_vm = find_existing_vm(api_token, name)

    if existing_vm:
        logging.info(f"VM '{name}' already exists — skipping creation")
        status = ks.Status()
        status.set("vmId", str(existing_vm["vmid"]))
        status.set("vmName", name)
        status.set("message", "VM already exists")
        sdk.write_status(status)
    else:
        result = create_vm(api_token, name, cores, memory)
        task_id = result.get("data")
        logging.info("Writing status back to resource")
        status = ks.Status()
        status.set("taskId", task_id)
        status.set("vmName", name)
        status.set("message", "VM creation initiated")
        sdk.write_status(status)

    logging.info("Pipeline complete")


if __name__ == "__main__":
    main()
