#!/bin/bash
# Verify DNS configuration in Kind cluster

set -e

NAMESPACE=${K8S_NAMESPACE:-ideaforge-ai}
CONTEXT=${KUBECTL_CONTEXT:-kind-ideaforge-ai}
CLUSTER_NAME=${KIND_CLUSTER_NAME:-ideaforge-ai}

echo "🔍 Verifying DNS Configuration in Kind Cluster"
echo "=============================================="
echo ""

# Check if CoreDNS is configured correctly
echo "1️⃣  Checking CoreDNS configuration..."
COREDNS_POD=$(kubectl get pods -n kube-system -l k8s-app=kube-dns --context $CONTEXT -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -z "$COREDNS_POD" ]; then
    echo "   ❌ CoreDNS pod not found"
    exit 1
fi

echo "   CoreDNS pod: $COREDNS_POD"

# Check CoreDNS ConfigMap
COREFILE=$(kubectl get configmap coredns -n kube-system --context $CONTEXT -o jsonpath='{.data.Corefile}' 2>/dev/null)
if echo "$COREFILE" | grep -q "forward . /etc/resolv.conf"; then
    echo "   ✅ CoreDNS is configured to forward to host resolver"
else
    echo "   ⚠️  CoreDNS may not be configured for host resolver forwarding"
    echo "   Run 'make kind-configure-dns' to fix this"
fi

# Test DNS resolution from CoreDNS pod
echo ""
echo "2️⃣  Testing DNS resolution from CoreDNS pod..."
if kubectl exec -n kube-system $COREDNS_POD --context $CONTEXT -- nslookup google.com 2>&1 | grep -q "Name:"; then
    echo "   ✅ CoreDNS can resolve external hostnames"
else
    echo "   ⚠️  CoreDNS DNS resolution test failed"
fi

# Test DNS resolution from a backend pod (if available)
echo ""
echo "3️⃣  Testing DNS resolution from application pod..."
BACKEND_POD=$(kubectl get pods -n $NAMESPACE -l app=backend --context $CONTEXT -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$BACKEND_POD" ]; then
    echo "   Using backend pod: $BACKEND_POD"
    if kubectl exec -n $NAMESPACE $BACKEND_POD --context $CONTEXT -- python -c "import socket; socket.gethostbyname('google.com'); print('✅ DNS resolution successful')" 2>&1 | grep -q "✅"; then
        echo "   ✅ Application pods can resolve external hostnames"
    else
        echo "   ⚠️  Application pod DNS resolution test failed"
    fi
    
    # Test VPN-accessible hostname if VPN is connected
    echo ""
    echo "4️⃣  Testing VPN-accessible hostname resolution..."
    if kubectl exec -n $NAMESPACE $BACKEND_POD --context $CONTEXT -- python -c "import socket; socket.gethostbyname('ai-gateway.quantumblack.com'); print('✅ VPN hostname resolution successful')" 2>&1 | grep -q "✅"; then
        echo "   ✅ Can resolve ai-gateway.quantumblack.com (VPN is working)"
    else
        echo "   ⚠️  Cannot resolve ai-gateway.quantumblack.com"
        echo "   This is expected if VPN is not connected"
        echo "   Ensure VPN is connected and run 'make kind-configure-dns' if needed"
    fi
else
    echo "   ⚠️  Backend pod not found - skipping application DNS test"
fi

echo ""
echo "✅ DNS Configuration Verification Complete!"
echo ""
echo "📝 Notes:"
echo "   - DNS configuration persists while the cluster is running"
echo "   - If DNS stops working, run 'make kind-configure-dns' to reconfigure"
echo "   - VPN-accessible hostnames require VPN connection on the host machine"

