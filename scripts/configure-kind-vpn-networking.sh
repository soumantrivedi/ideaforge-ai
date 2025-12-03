#!/bin/bash
# Configure existing Kind cluster for VPN networking access
# This script updates an existing cluster without recreating it

set -e

NAMESPACE=${K8S_NAMESPACE:-ideaforge-ai}
CONTEXT=${KUBECTL_CONTEXT:-kind-ideaforge-ai}
CLUSTER_NAME=${KIND_CLUSTER_NAME:-ideaforge-ai}

echo "🌐 Configuring Kind cluster for VPN networking access"
echo "====================================================="
echo ""

# Check if cluster exists
if ! kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    echo "❌ Cluster ${CLUSTER_NAME} does not exist"
    echo "   Run 'make kind-create' to create a new cluster"
    exit 1
fi

echo "✅ Cluster ${CLUSTER_NAME} found"
echo ""

# Step 1: Mount host resolv.conf into control plane node
echo "Step 1: Mounting host resolv.conf into control plane node..."
CONTROL_PLANE_CONTAINER="${CLUSTER_NAME}-control-plane"

# Check if resolv.conf.host is already mounted
if docker exec ${CONTROL_PLANE_CONTAINER} test -f /etc/resolv.conf.host 2>/dev/null; then
    echo "   ✅ Host resolv.conf already mounted"
else
    echo "   Mounting host resolv.conf..."
    # Create a bind mount from host resolv.conf
    docker exec ${CONTROL_PLANE_CONTAINER} sh -c "cp /etc/resolv.conf /etc/resolv.conf.original" || true
    # We'll configure CoreDNS to use the host's DNS servers directly
    echo "   ⚠️  Note: For existing clusters, DNS forwarding is configured via CoreDNS"
fi

# Step 2: Get host DNS servers
echo ""
echo "Step 2: Detecting host DNS configuration..."
HOST_DNS_SERVERS=$(cat /etc/resolv.conf | grep "^nameserver" | awk '{print $2}' | head -3 | tr '\n' ' ')
if [ -z "$HOST_DNS_SERVERS" ]; then
    HOST_DNS_SERVERS="8.8.8.8 8.8.4.4"
    echo "   ⚠️  Could not detect host DNS servers, using fallback: ${HOST_DNS_SERVERS}"
else
    echo "   ✅ Host DNS servers: ${HOST_DNS_SERVERS}"
fi

# Step 3: Configure CoreDNS to use host DNS
echo ""
echo "Step 3: Configuring CoreDNS to forward to host DNS servers..."
kubectl wait --for=condition=ready pod -l k8s-app=kube-dns -n kube-system --context ${CONTEXT} --timeout=60s || true

# Format DNS servers for CoreDNS (space-separated)
DNS_SERVERS_FORMATTED=$(echo ${HOST_DNS_SERVERS} | tr ' ' '\n' | grep -v '^$' | tr '\n' ' ' | sed 's/ $//')

echo "   Using DNS servers: ${DNS_SERVERS_FORMATTED}"

# Create CoreDNS configuration with host DNS servers
# Escape newlines and quotes for JSON
COREFILE=$(cat <<EOF
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
    forward . ${DNS_SERVERS_FORMATTED} {
       max_concurrent 1000
    }
    cache 30
    loop
    reload
    loadbalance
}
EOF
)

# Escape the Corefile for JSON
COREFILE_ESCAPED=$(echo "$COREFILE" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | tr '\n' 'n' | sed 's/n/\\n/g')

# Patch CoreDNS ConfigMap
kubectl patch configmap coredns -n kube-system --context ${CONTEXT} --type merge \
    -p "{\"data\":{\"Corefile\":\"${COREFILE_ESCAPED}\"}}" || {
    echo "   ⚠️  Patching failed, creating custom ConfigMap..."
    # Create a temporary file with the Corefile
    cat > /tmp/coredns-corefile.yaml <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
$(echo "$COREFILE" | sed 's/^/    /')
EOF
    kubectl apply -f /tmp/coredns-corefile.yaml --context ${CONTEXT} || true
    rm -f /tmp/coredns-corefile.yaml
}

# Step 4: Update CoreDNS deployment to use host network DNS
echo ""
echo "Step 4: Updating CoreDNS deployment..."
# Check if we need to add host network access
COREDNS_DEPLOYMENT=$(kubectl get deployment coredns -n kube-system --context ${CONTEXT} -o yaml)

# Restart CoreDNS to apply changes
kubectl rollout restart deployment/coredns -n kube-system --context ${CONTEXT} || true
echo "   Waiting for CoreDNS pods to restart..."
kubectl wait --for=condition=ready pod -l k8s-app=kube-dns -n kube-system --context ${CONTEXT} --timeout=120s || true

sleep 5

# Step 5: Verify configuration
echo ""
echo "Step 5: Verifying DNS configuration..."
COREDNS_POD=$(kubectl get pods -n kube-system -l k8s-app=kube-dns --context ${CONTEXT} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$COREDNS_POD" ]; then
    echo "   Testing DNS resolution from CoreDNS pod..."
    if kubectl exec -n kube-system ${COREDNS_POD} --context ${CONTEXT} -- nslookup google.com 2>&1 | grep -q "Name:"; then
        echo "   ✅ CoreDNS can resolve external hostnames"
    else
        echo "   ⚠️  CoreDNS DNS test inconclusive"
    fi
    
    # Test VPN hostname if VPN is connected
    echo "   Testing VPN hostname resolution..."
    if kubectl exec -n kube-system ${COREDNS_POD} --context ${CONTEXT} -- nslookup ai-gateway.quantumblack.com 2>&1 | grep -q "Name:"; then
        echo "   ✅ Can resolve ai-gateway.quantumblack.com (VPN is working)"
    else
        echo "   ⚠️  Cannot resolve ai-gateway.quantumblack.com"
        echo "      Ensure VPN is connected on the host machine"
    fi
fi

# Step 6: Test from application pod
echo ""
echo "Step 6: Testing DNS from application pod..."
BACKEND_POD=$(kubectl get pods -n ${NAMESPACE} -l app=backend --context ${CONTEXT} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$BACKEND_POD" ]; then
    echo "   Testing from backend pod: ${BACKEND_POD}"
    if kubectl exec -n ${NAMESPACE} ${BACKEND_POD} --context ${CONTEXT} -- python -c "import socket; socket.gethostbyname('ai-gateway.quantumblack.com'); print('✅ DNS resolution successful')" 2>&1 | grep -q "✅"; then
        echo "   ✅ Application pods can resolve VPN hostnames"
    else
        echo "   ⚠️  Application pod DNS test failed"
        echo "      This may be expected if VPN is not connected"
    fi
else
    echo "   ⚠️  Backend pod not found - deploy application first"
fi

echo ""
echo "✅ VPN networking configuration complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Ensure VPN is connected on the host machine"
echo "   2. Run 'make kind-verify-dns' to verify DNS resolution"
echo "   3. Run 'make kind-test-ai-gateway-connectivity' to test AI Gateway access"

