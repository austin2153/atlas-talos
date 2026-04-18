# Architecture

This document describes the design decisions, infrastructure layout, and rationale behind the `atlas-talos` Terraform project.

## Overview

`atlas-talos` provisions a [Talos Linux](https://www.talos.dev/) Kubernetes cluster on a self-hosted [Proxmox VE](https://www.proxmox.com/) server using Terraform. Talos is a minimal, immutable, API-driven Linux distribution built specifically for Kubernetes — there is no SSH, no package manager, and no shell. All configuration is applied via its API.

## Tech Stack

| Component | Choice | Reason |
|---|---|---|
| Hypervisor | Proxmox VE 8.4.1 | Existing single-node homelab server |
| OS | Talos Linux (latest stable) | Immutable, Kubernetes-native, minimal attack surface |
| Terraform provider (Proxmox) | [`bpg/proxmox`](https://registry.terraform.io/providers/bpg/proxmox) | Best-maintained provider for PVE 8.x with full VM lifecycle support |
| Terraform provider (Talos) | [`siderolabs/talos`](https://registry.terraform.io/providers/siderolabs/talos) | Official provider for generating and applying Talos machine configs |
| CNI | Flannel | Simplest standard CNI; easy to migrate to Cilium later if needed |
| Terraform state backend | Terraform Cloud (local exec mode) | State versioned and locked in the cloud; plan/apply runs locally to reach Proxmox |

## Cluster Topology

```
┌─────────────────────────────────┐
│         Proxmox VE 8.4.1        │
│         (single node)           │
│                                 │
│  ┌──────────────────────────┐   │
│  │  talos-cp (VM 200)       │   │
│  │  Control Plane           │   │
│  │  192.168.20.10           │   │
│  │  2 vCPU / 4 GB / 50 GB  │   │
│  └──────────────────────────┘   │
│                                 │
│  ┌──────────────────────────┐   │
│  │  talos-worker-01 (VM 201)│   │
│  │  Worker                  │   │
│  │  192.168.20.11           │   │
│  │  2 vCPU / 4 GB / 50 GB  │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
```

Starting with 1 control plane and 1 worker. The worker count is designed to scale — adding a second worker means adding another IP reservation and a new entry in the `worker_ips` variable.

## Network Layout

| Parameter | Value |
|---|---|
| Network | Atlas Lab (VLAN 20) |
| Subnet | `192.168.20.0/24` |
| Gateway | `192.168.20.1` (Home Cloud Gateway) |
| DNS | `192.168.0.101` (atlas-pihole) |
| Proxmox bridge | `vmbr0`, VLAN tag `20` |
| Control plane | `talos-cp.atlas.local` → `192.168.20.10` |
| Worker 01 | `talos-worker-01.atlas.local` → `192.168.20.11` |

DNS entries are managed in Pi-hole (`atlas-pihole.atlas.local`). Static IPs are configured directly in the Talos machine configs rather than via DHCP reservations.

## VM Configuration

| Parameter | Value | Reason |
|---|---|---|
| BIOS | OVMF (UEFI) | Consistent with other VMs on this Proxmox host; Talos supports and recommends UEFI |
| EFI disk | 1M on `CRUCIAL_SSD_512GB` | Required for UEFI boot |
| Main disk | 50 GB on `CRUCIAL_SSD_512GB` | Adequate for homelab etcd + workloads |
| Network driver | VirtIO | Best performance on Proxmox |
| ISO storage | `local` | Where ISOs are stored on this Proxmox node |
| VM disk storage | `CRUCIAL_SSD_512GB` | Primary SSD storage pool on this Proxmox node |

The Talos ISO is downloaded directly from the [Talos Image Factory](https://factory.talos.dev/) into Proxmox `local` ISO storage by Terraform using `proxmox_virtual_environment_download_file`. No manual ISO upload is required. Talos boots from the ISO, receives its machine config via the Talos API, installs itself to disk, and reboots — after which the ISO is no longer used.

## Terraform State Strategy

Terraform Cloud is used in **Local execution mode**:

- `terraform plan` and `terraform apply` run on the **local machine**, which has network access to the Proxmox server and Talos API endpoints on VLAN 20
- State is stored in and locked by **Terraform Cloud**, providing state versioning, locking (prevents concurrent runs), and a remote backup

This avoids the main limitation of fully remote execution (Terraform Cloud runners cannot reach a private homelab network) while still getting the benefits of managed state.

## Terraform File Structure

| File | Responsibility |
|---|---|
| `providers.tf` | Terraform Cloud `cloud {}` backend block + `required_providers` with version pins for `bpg/proxmox` and `siderolabs/talos` |
| `variables.tf` | Declares all input variables: Proxmox endpoint, API token, node name, cluster name, IPs, gateway, DNS, VM sizing |
| `terraform.tfvars` | Actual secret/environment-specific values — gitignored, never committed |
| `locals.tf` | Computed values derived from variables (e.g., node map, CIDR notation) |
| `proxmox-image.tf` | Downloads the Talos metal ISO into Proxmox `local` ISO storage |
| `proxmox-vms.tf` | Defines the control plane and worker VMs (UEFI, EFI disk, VLAN 20 network, disk sizing) |
| `talos.tf` | Generates Talos machine secrets, renders machine configs, applies configs to nodes, bootstraps etcd |
| `outputs.tf` | Exports `talosconfig` and `kubeconfig` from Terraform state |

## Deployment Flow

```
terraform apply
     │
     ├── 1. Download Talos ISO → Proxmox local storage
     │
     ├── 2. Create VMs (talos-cp, talos-worker-01)
     │        Boot from ISO, waiting for Talos API
     │
     ├── 3. Generate Talos machine secrets (PKI, cluster ID, etc.)
     │
     ├── 4. Render + apply machine configs to each node
     │        Talos installs to disk → reboots → runs from disk
     │
     ├── 5. Bootstrap etcd on control plane
     │
     └── 6. Retrieve kubeconfig
              │
              └── kubectl apply flannel CNI
                       │
                       └── Nodes transition to Ready
```

## Future Considerations

- **Additional workers**: Add IPs to `worker_ips` variable and add Pi-hole DNS entries
- **CNI migration**: Flannel can be replaced with Cilium for eBPF-based networking and network policy support
- **Talos Image Factory extensions**: Consider adding the QEMU guest agent extension for better Proxmox integration
- **High availability**: Scaling to 3 control planes would require an external load balancer or virtual IP (e.g., kube-vip) in front of the API server
