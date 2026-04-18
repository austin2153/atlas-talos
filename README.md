# atlas-talos

Terraform code to deploy a [Talos Linux](https://www.talos.dev/) Kubernetes cluster on a Proxmox VE server.

See [docs/architecture.md](docs/architecture.md) for design decisions, network layout, and rationale.

## Cluster Overview

| Role | Hostname | IP |
|---|---|---|
| Control Plane | `talos-cp.atlas.local` | `192.168.20.10` |
| Worker | `talos-worker-01.atlas.local` | `192.168.20.11` |

## Prerequisites

### Tools

Install the following on your local machine:

```bash
brew install terraform talosctl kubectl
```

### Accounts & Access

- **Proxmox API token**: Datacenter → Permissions → API Tokens → create token for a user with VM provisioning permissions
- **Terraform Cloud account**: [app.terraform.io](https://app.terraform.io) — workspace must be set to **Local** execution mode (Settings → General → Execution Mode)

### Authenticate Terraform CLI to Terraform Cloud

```bash
terraform login
```

## Repository Structure

```
atlas-talos/
├── README.md
├── .gitignore
├── docs/
│   └── architecture.md     # Design decisions and architecture overview
└── terraform/
    ├── providers.tf         # TF Cloud backend + provider version pins
    ├── variables.tf         # All input variables
    ├── terraform.tfvars     # Your actual values (gitignored — never commit this)
    ├── locals.tf            # Computed locals
    ├── proxmox-image.tf     # Download Talos ISO to Proxmox storage
    ├── proxmox-vms.tf       # Control plane + worker VM resources
    ├── talos.tf             # Talos config generation, apply, and bootstrap
    └── outputs.tf           # talosconfig + kubeconfig outputs
```

## Configuration

Copy and fill in your values:

```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
```

### Key Variables

| Variable | Description | Example |
|---|---|---|
| `proxmox_endpoint` | Proxmox API URL | `https://192.168.0.100:8006` |
| `proxmox_api_token` | Proxmox API token | `terraform@pve!mytoken=...` |
| `proxmox_node` | Proxmox node name | `proxmox` |
| `cluster_name` | Talos cluster name | `atlas` |
| `control_plane_ip` | Control plane static IP | `192.168.20.10` |
| `worker_ips` | List of worker static IPs | `["192.168.20.11"]` |
| `gateway` | VLAN 20 gateway | `192.168.20.1` |
| `dns_server` | DNS server IP | `192.168.0.101` |

## Deployment

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

After a successful apply, save credentials and merge into your default kubeconfig:

```bash
terraform output -raw kubeconfig > ~/.kube/atlas-talos.kubeconfig
terraform output -raw talosconfig > ~/.talos/atlas-talos.talosconfig
# Remove stale entries (required on rebuild — new cluster has new certificates)
kubectl config delete-context admin@atlas 2>/dev/null; kubectl config delete-cluster atlas 2>/dev/null; kubectl config delete-user admin@atlas 2>/dev/null; true
# Merge and switch
KUBECONFIG=~/.kube/config:~/.kube/atlas-talos.kubeconfig kubectl config view --flatten > ~/.kube/config-merged && mv ~/.kube/config-merged ~/.kube/config
kubectl config use-context admin@atlas
kubectl get nodes
```

> **Rebuilding the cluster?** The VMs use pinned MAC addresses (`BC:24:11:00:02:00` for the control plane, `BC:24:11:00:02:01` for worker-01, etc.), so your DHCP reservations in UniFi remain valid across destroys. After `terraform apply`, re-run all the commands above — the delete step clears stale certificates from the previous cluster.

## Teardown

```bash
cd terraform
terraform destroy
```
