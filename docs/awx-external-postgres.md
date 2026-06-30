# AWX External PostgreSQL

AWX's database runs outside the Kubernetes cluster, on a dedicated Proxmox LXC container. This document explains why, how it's set up, and how to manage it.

## Background

AWX originally ran with an in-cluster Postgres StatefulSet (`awx-postgres-15`) backed by a `local-path` PersistentVolumeClaim. `local-path` stores PV data directly on the Kubernetes node's local disk. After an unclean power loss to the Proxmox host, the Postgres data directory was found empty on restart, and `initdb` silently re-initialized a fresh, empty database — wiping all AWX data (job templates, inventories, credentials, projects). This happened more than once.

Local-path PVs are not resilient to node-level disk/power issues in this homelab. Rather than introduce more complex in-cluster storage (Longhorn, NFS-backed PVs, etc.) for a single database, AWX's Postgres was moved to a dedicated LXC container managed directly by Proxmox — independent of Kubernetes node lifecycle, with its own ZFS-backed storage pool for additional data integrity protection.

## Infrastructure

| Item | Value |
|---|---|
| Container | `awx-postgres.atlas.local` |
| LXC ID | 105 (Proxmox node `proxmox`) |
| IP | `192.168.20.12` (Atlas Lab VLAN 20, alongside the Talos cluster nodes) |
| OS | Alpine Linux 3.23 |
| PostgreSQL version | 16 |
| Storage | `CRUCIAL_SSD_512GB` (ZFS pool) |
| Container protection | Enabled (must be disabled before `pct destroy`) |
| Provisioned via | [community-scripts ProxmoxVE](https://github.com/community-scripts/ProxmoxVE) `alpine-postgresql.sh` |

Pods in the Kubernetes cluster can reach `192.168.20.12` directly — both Talos nodes (`talos-cp`, `talos-worker-01`) are tagged VLAN 20, so pod traffic routes out through the node's tagged interface to any host on `192.168.20.0/24`, no Kubernetes Service or extra networking config needed.

## Database Setup

A dedicated role and database were created for AWX (not using the Postgres superuser):

```sql
CREATE USER awx WITH PASSWORD '<generated>';
CREATE DATABASE awx OWNER awx;
```

`pg_hba.conf` was updated to allow password-authenticated connections from the cluster's subnet only (not open to the world):

```
host    awx             awx             192.168.20.0/24         scram-sha-256
```

All other connections (e.g. from `local-path`/loopback) remain `trust`-authenticated as set by the install script — those are only reachable from inside the container itself.

## AWX Configuration

AWX points at the external database via a Kubernetes secret (`awx-postgres-configuration` in the `awx` namespace) instead of letting the AWX operator manage an in-cluster Postgres instance:

```bash
kubectl create secret generic awx-postgres-configuration -n awx \
  --from-literal=host="192.168.20.12" \
  --from-literal=port="5432" \
  --from-literal=database="awx" \
  --from-literal=username="awx" \
  --from-literal=password="<generated>" \
  --from-literal=sslmode="prefer" \
  --from-literal=type="unmanaged"
```

The `type: unmanaged` key tells the AWX operator not to provision or manage a Postgres StatefulSet itself. The [awx-instance.yaml](../platform/awx/awx-instance.yaml) manifest references this secret via `postgres_configuration_secret` and no longer carries any `postgres_storage_requirements` / `postgres_data_volume_init` settings (those only apply when AWX manages its own database).

## Credentials

- **LXC root password** (SSH/console access to the container OS): stored locally at `~/.proxmox-awx-postgres-credentials`
- **Postgres `awx` user password**: stored only in the `awx-postgres-configuration` Kubernetes secret — not written to disk anywhere else

## Migrating Schema After a Database Reset

If this database is ever reset or recreated, AWX's migration job needs to be re-run, same as the original in-cluster recovery process:

```bash
kubectl delete job awx-migration-<version> -n awx
kubectl annotate awx awx -n awx awx.ansible.com/force-reconcile="$(date +%s)" --overwrite
```

The AWX operator will recreate the migration job, which applies the full Django schema (~300 migrations) to a fresh database.

## Why This Is More Resilient

- Container lifecycle is fully decoupled from Kubernetes node restarts — a Talos node reboot or rebuild no longer touches this data
- ZFS-backed storage provides checksums and protects against silent corruption, unlike the `local-path` ext4/xfs setup used before
- Container protection prevents accidental `pct destroy`
- Still a single point of failure for power loss to the Proxmox host itself — consider periodic `pg_dump` backups if this matters for archival purposes, since this setup protects against *Kubernetes*-level disruption, not Proxmox host failure
