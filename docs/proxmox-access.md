# Proxmox Access

This document describes how Claude connects to the Proxmox VE server for reviewing and managing the homelab hypervisor.

## Credentials File

The Proxmox API token is stored locally at `~/.proxmox-credentials` (not committed to git) as a single value in the format `user@realm!tokenid=secret`:

```
<user@realm!tokenid=secret>
```

Restrict permissions so only your user can read it:

```bash
chmod 600 ~/.proxmox-credentials
```

## Connecting

Claude reads the API token from `~/.proxmox-credentials` and authenticates against the Proxmox REST API. The cluster has two nodes: `proxmox` and `proxmox-cgrater`.

### Example — list nodes

```bash
PROXMOX_TOKEN=$(cat ~/.proxmox-credentials)
curl -sk "https://<proxmox-ip>:8006/api2/json/nodes" \
  -H "Authorization: PVEAPIToken=$PROXMOX_TOKEN" | python3 -m json.tool
```

### Example — list VMs on a node

```bash
curl -sk "https://<proxmox-ip>:8006/api2/json/nodes/proxmox/qemu" \
  -H "Authorization: PVEAPIToken=$PROXMOX_TOKEN" | python3 -m json.tool
```

## SSH Access

For tasks the REST API can't do (e.g. running community LXC install scripts, `pct` commands), Claude connects to the Proxmox host directly via SSH using a dedicated key — separate from the API token, so it can be revoked independently.

```bash
ssh-keygen -t ed25519 -f ~/.ssh/proxmox-claude -N "" -C "claude-code-proxmox"
```

The public key (`~/.ssh/proxmox-claude.pub`) is added to `root`'s `~/.ssh/authorized_keys` on the Proxmox host. Connect with:

```bash
ssh -i ~/.ssh/proxmox-claude root@<proxmox-ip>
```

LXC containers can be managed from the host via `pct` (e.g. `pct list`, `pct exec <vmid> -- <command>`).

## Notes

- Proxmox VE is a single-node homelab server on the local network
- TLS verification is disabled (`-sk`) due to the self-signed certificate
- Always source credentials from `~/.proxmox-credentials` — never hardcode or echo secrets in the terminal
- Per-LXC root passwords (e.g. for `awx-postgres.atlas.local`) are stored in their own credentials files, like `~/.proxmox-awx-postgres-credentials`
