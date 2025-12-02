# Kind Cluster VPN Networking Setup

## Overview

This guide explains how to configure a Kind cluster to access VPN-accessible services like the AI Gateway. The Docker host has VPN connectivity, and we need to ensure the Kind cluster can leverage this.

## Problem

By default, Kind clusters run in Docker containers with their own network namespace. This means:
- Pods cannot directly access VPN-accessible hostnames
- DNS resolution fails for internal services like `ai-gateway.quantumblack.com`
- The cluster needs to use the host's DNS servers (which have VPN access)

## Solution

We configure CoreDNS (the Kubernetes DNS service) to forward DNS queries directly to the host's DNS servers. This allows pods to resolve VPN-accessible hostnames.

## Methods

### Method 1: Configure Existing Cluster (Recommended)

If you already have a Kind cluster running:

```bash
make kind-configure-vpn-networking
```

This script:
1. Detects the host's DNS servers from `/etc/resolv.conf`
2. Updates CoreDNS ConfigMap to forward to those DNS servers
3. Restarts CoreDNS pods
4. Verifies the configuration

### Method 2: Create New Cluster with VPN Support

For new clusters, the `kind-create` target automatically:
1. Mounts the host's `/etc/resolv.conf` into the control plane node
2. Configures CoreDNS to use host DNS servers
3. Sets up proper networking

```bash
make kind-create
```

### Method 3: Recreate Cluster with Database Backup

If you need to recreate the cluster but preserve data:

```bash
# Step 1: Backup database
make kind-backup-database

# Step 2: Recreate cluster with VPN networking
make kind-recreate-with-vpn

# Step 3: Restore database (after cluster is ready)
make kind-restore-database BACKUP_FILE=./backups/ideaforge-ai-backup-YYYYMMDD_HHMMSS.sql
```

## Verification

### Check DNS Resolution

```bash
# From CoreDNS pod
COREDNS_POD=$(kubectl get pods -n kube-system -l k8s-app=kube-dns --context kind-ideaforge-ai -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n kube-system $COREDNS_POD --context kind-ideaforge-ai -- nslookup ai-gateway.quantumblack.com

# From application pod
BACKEND_POD=$(kubectl get pods -n ideaforge-ai -l app=backend --context kind-ideaforge-ai -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n ideaforge-ai $BACKEND_POD --context kind-ideaforge-ai -- python -c "import socket; print(socket.gethostbyname('ai-gateway.quantumblack.com'))"
```

### Test AI Gateway Connectivity

```bash
make kind-test-ai-gateway-connectivity
```

### Verify DNS Configuration

```bash
make kind-verify-dns
```

## How It Works

1. **Host DNS Detection**: The script reads `/etc/resolv.conf` to find DNS servers configured on the host (including VPN-provided DNS servers).

2. **CoreDNS Configuration**: CoreDNS is configured to forward all DNS queries to the host's DNS servers:
   ```
   forward . 10.20.137.30 10.109.134.15 {
      max_concurrent 1000
   }
   ```

3. **Persistence**: The CoreDNS ConfigMap change persists while the cluster is running. CoreDNS pods are restarted to apply the configuration.

4. **VPN Access**: When VPN is connected on the host, the host's DNS servers can resolve VPN-accessible hostnames, and CoreDNS forwards those queries, allowing pods to resolve them.

## Troubleshooting

### DNS Resolution Still Fails

1. **Check VPN Connection**:
   ```bash
   # Test from host
   nslookup ai-gateway.quantumblack.com
   ```

2. **Verify CoreDNS Configuration**:
   ```bash
   kubectl get configmap coredns -n kube-system --context kind-ideaforge-ai -o yaml | grep -A 5 "forward"
   ```

3. **Check CoreDNS Logs**:
   ```bash
   COREDNS_POD=$(kubectl get pods -n kube-system -l k8s-app=kube-dns --context kind-ideaforge-ai -o jsonpath='{.items[0].metadata.name}')
   kubectl logs -n kube-system $COREDNS_POD --context kind-ideaforge-ai
   ```

4. **Reconfigure DNS**:
   ```bash
   make kind-configure-vpn-networking
   ```

### Application Pods Can't Resolve

1. **Restart Application Pods**:
   ```bash
   kubectl rollout restart deployment/backend -n ideaforge-ai --context kind-ideaforge-ai
   ```

2. **Check Pod DNS Configuration**:
   ```bash
   BACKEND_POD=$(kubectl get pods -n ideaforge-ai -l app=backend --context kind-ideaforge-ai -o jsonpath='{.items[0].metadata.name}')
   kubectl exec -n ideaforge-ai $BACKEND_POD --context kind-ideaforge-ai -- cat /etc/resolv.conf
   ```

### VPN Reconnected

If VPN is reconnected after cluster creation:
```bash
make kind-configure-vpn-networking
```

This updates CoreDNS with the new DNS servers.

## Database Backup and Restore

### Backup Database

```bash
make kind-backup-database
```

Backups are saved to `./backups/ideaforge-ai-backup-YYYYMMDD_HHMMSS.sql`

### Restore Database

```bash
make kind-restore-database BACKUP_FILE=./backups/ideaforge-ai-backup-YYYYMMDD_HHMMSS.sql
```

## Make Targets

- `make kind-configure-vpn-networking` - Configure existing cluster for VPN networking
- `make kind-create` - Create new cluster with VPN support
- `make kind-recreate-with-vpn` - Recreate cluster with database backup/restore
- `make kind-backup-database` - Backup database from cluster
- `make kind-restore-database BACKUP_FILE=...` - Restore database to cluster
- `make kind-verify-dns` - Verify DNS configuration
- `make kind-test-ai-gateway-connectivity` - Test AI Gateway connectivity

## Notes

- VPN must be connected on the host machine for DNS resolution to work
- The configuration persists while the cluster is running
- If VPN is disconnected and reconnected, run `make kind-configure-vpn-networking` again
- Database backups are stored in `./backups/` directory

