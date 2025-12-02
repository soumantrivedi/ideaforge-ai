# DNS Configuration for Kind Cluster - VPN Access

## Overview

The Kind cluster DNS is now automatically configured during cluster creation to forward DNS queries to the host resolver. This allows pods to resolve VPN-accessible hostnames (like `ai-gateway.quantumblack.com`) while the cluster is running.

## Automatic Configuration

When you run `make kind-create`, the DNS configuration is automatically applied:

1. **CoreDNS ConfigMap is patched** to forward queries to `/etc/resolv.conf` (host resolver)
2. **CoreDNS pods are restarted** to apply the configuration
3. **Configuration is verified** to ensure it's working
4. **Configuration persists** while the cluster is running

## Manual Configuration

If you need to reconfigure DNS (e.g., after VPN reconnection), run:

```bash
make kind-configure-dns
```

This will:
- Patch the CoreDNS ConfigMap with host resolver forwarding
- Restart CoreDNS pods
- Verify the configuration
- Ensure it persists

## Verification

To verify DNS configuration is working:

```bash
make kind-verify-dns
```

This script checks:
1. ✅ CoreDNS configuration (forward directive present)
2. ✅ DNS resolution from CoreDNS pod
3. ✅ DNS resolution from application pods
4. ✅ VPN-accessible hostname resolution (if VPN is connected)

## How It Works

1. **CoreDNS Forward Directive**: The CoreDNS ConfigMap is patched to include:
   ```
   forward . /etc/resolv.conf {
      max_concurrent 1000
   }
   ```
   This forwards all DNS queries to the host's resolver.

2. **Host Resolver**: The host's `/etc/resolv.conf` contains DNS servers that can resolve VPN-accessible hostnames when VPN is connected.

3. **Persistence**: The ConfigMap change persists while the cluster is running. If CoreDNS pods restart, they will use the updated configuration.

## Troubleshooting

### DNS Resolution Fails

1. **Check VPN Connection**:
   ```bash
   # Test from host machine
   nslookup ai-gateway.quantumblack.com
   ```

2. **Reconfigure DNS**:
   ```bash
   make kind-configure-dns
   ```

3. **Verify Configuration**:
   ```bash
   make kind-verify-dns
   ```

### DNS Stops Working After Pod Restart

The DNS configuration is stored in the CoreDNS ConfigMap, which persists across pod restarts. If DNS stops working:

1. Check if CoreDNS ConfigMap still has the forward directive:
   ```bash
   kubectl get configmap coredns -n kube-system --context kind-ideaforge-ai -o yaml | grep forward
   ```

2. Reconfigure if needed:
   ```bash
   make kind-configure-dns
   ```

### VPN Reconnection

If you reconnect VPN, the DNS configuration should continue working. However, if you experience issues:

1. Reconfigure DNS:
   ```bash
   make kind-configure-dns
   ```

2. Restart application pods to pick up DNS changes:
   ```bash
   make kind-restart-backend
   ```

## Make Targets

- **`make kind-create`**: Creates cluster and automatically configures DNS
- **`make kind-configure-dns`**: Manually configure/reconfigure DNS
- **`make kind-verify-dns`**: Verify DNS configuration is working
- **`make kind-test-ai-gateway-connectivity`**: Test AI Gateway connectivity (includes DNS test)

## Technical Details

### CoreDNS Configuration

The CoreDNS ConfigMap is patched with:
```yaml
data:
  Corefile: |
    .:53 {
        errors
        health {
           lameduck 5s
        }
        ready
        kubernetes cluster.local in-addr.arpa ip6.arpa {
           pods insecure
           fallthrough in-addr.arpa ip6.arpa
           ttl 30
        }
        prometheus :9153
        forward . /etc/resolv.conf {
           max_concurrent 1000
        }
        cache 30
        loop
        reload
        loadbalance
    }
```

### Persistence

- The ConfigMap change is persistent (stored in etcd)
- CoreDNS pods read the ConfigMap on startup
- Pod restarts will use the updated configuration
- Cluster deletion removes the configuration (recreated on next `kind-create`)

## Status

✅ **DNS configuration is automatic** - runs during `make kind-create`
✅ **Configuration persists** - remains active while cluster is running
✅ **Verification available** - use `make kind-verify-dns` to check
✅ **Reconfiguration supported** - run `make kind-configure-dns` anytime

The DNS configuration ensures pods can resolve VPN-accessible hostnames as long as:
1. VPN is connected on the host machine
2. The CoreDNS ConfigMap has the forward directive
3. The cluster is running

