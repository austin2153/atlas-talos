locals {
  # Map of worker hostname → attributes, derived from the worker_ips list.
  # Workers are named talos-worker-01, talos-worker-02, etc.
  # VMIDs start at 201 (control plane is 200).
  workers = {
    for idx, ip in var.worker_ips :
    format("talos-worker-%02d", idx + 1) => {
      ip   = ip
      cidr = "${ip}/${var.subnet_prefix}"
      vmid = 201 + idx
    }
  }

  # Talos Image Factory ISO URL for the configured schematic + version
  talos_iso_url = "https://factory.talos.dev/image/${var.talos_schematic_id}/${var.talos_version}/metal-amd64.iso"
}
