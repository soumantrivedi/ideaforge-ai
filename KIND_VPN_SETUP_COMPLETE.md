# Kind Cluster VPN Networking - Setup Complete ✅

## Summary

The Kind cluster has been configured to leverage the Docker host's VPN connectivity. The configuration allows pods to resolve VPN-accessible hostnames like `ai-gateway.quantumblack.com`.

## What Was Done

1. **CoreDNS Configuration**: Updated CoreDNS to forward DNS queries directly to the host's DNS servers:
   - `10.20.137.30`
   - `10.109.134.15`
   - `10.109.133.4`

2. **Database Backup/Restore Scripts**: Created scripts to backup and restore the database when recreating clusters:
   - `scripts/backup-database.sh`
   - `scripts/restore-database.sh`

3. **VPN Networking Configuration Script**: Created a script to configure existing clusters:
   - `scripts/configure-kind-vpn-networking.sh`

4. **Make Targets**: Added new make targets for VPN networking:
   - `make kind-configure-vpn-networking` - Configure existing cluster
   - `make kind-backup-database` - Backup database
   - `make kind-restore-database BACKUP_FILE=...` - Restore database
   - `make kind-recreate-with-vpn` - Recreate cluster with backup/restore

## Current Status

✅ **CoreDNS Configured**: DNS forwarding to host DNS servers is active
⚠️ **DNS Resolution**: Requires VPN to be connected on the host machine

## Usage

### For Existing Clusters

```bash
# Configure VPN networking
make kind-configure-vpn-networking

# Verify DNS
make kind-verify-dns

# Test AI Gateway connectivity
make kind-test-ai-gateway-connectivity
```

### For New Clusters

```bash
# Create cluster (automatically configures VPN networking)
make kind-create

# Or recreate with database backup
make kind-recreate-with-vpn
```

### Database Operations

```bash
# Backup before recreating
make kind-backup-database

# Restore after recreating
make kind-restore-database BACKUP_FILE=./backups/ideaforge-ai-backup-YYYYMMDD_HHMMSS.sql
```

## Verification

Once VPN is connected on the host:

```bash
# Test DNS resolution from backend pod
BACKEND_POD=$(kubectl get pods -n ideaforge-ai -l app=backend --context kind-ideaforge-ai -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n ideaforge-ai $BACKEND_POD --context kind-ideaforge-ai -- \
  python -c "import socket; print(socket.gethostbyname('ai-gateway.quantumblack.com'))"
```

Expected output: An IP address (e.g., `10.x.x.x`)

## Troubleshooting

### DNS Still Not Working

1. **Ensure VPN is connected** on the host machine
2. **Reconfigure DNS**:
   ```bash
   make kind-configure-vpn-networking
   ```
3. **Restart backend pods**:
   ```bash
   make kind-restart-backend
   ```

### CoreDNS Pods Crashing

If CoreDNS pods are in CrashLoopBackOff:
```bash
# Check logs
kubectl logs -n kube-system <coredns-pod> --context kind-ideaforge-ai

# Delete crashing pods (they will be recreated)
kubectl delete pod -n kube-system <coredns-pod> --context kind-ideaforge-ai
```

## Next Steps

1. **Connect VPN** on the host machine
2. **Verify DNS resolution**:
   ```bash
   make kind-verify-dns
   ```
3. **Test AI Gateway connectivity**:
   ```bash
   make kind-test-ai-gateway-connectivity
   ```
4. **Verify AI Gateway integration**:
   ```bash
   make kind-validate-ai-gateway
   ```

## Documentation

- **Setup Guide**: `KIND_VPN_NETWORKING_SETUP.md`
- **AI Gateway Integration**: `AI_GATEWAY_PRODUCTION_READY.md`
- **DNS Configuration**: `DNS_CONFIGURATION_GUIDE.md`

