# Downloads the Talos metal ISO from the Image Factory directly into Proxmox
# local ISO storage. No manual upload required.
#
# The ISO is built from the schematic defined in var.talos_schematic_id.
# To add Proxmox QEMU guest agent or other extensions, generate a new schematic
# at https://factory.talos.dev and update var.talos_schematic_id.

resource "proxmox_download_file" "talos_iso" {
  content_type = "iso"
  datastore_id = var.iso_storage
  node_name    = var.proxmox_node

  url       = local.talos_iso_url
  file_name = "talos-${var.talos_version}-metal-amd64.iso"

  overwrite      = false
  upload_timeout = 600
}
