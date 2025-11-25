# Accessing IdeaForge AI in Kind Cluster

## Quick Access Methods

### Method 1: Direct Access via Ingress Port (Recommended)

The kind cluster maps the ingress controller to a host port. Check which port is being used:

```bash
docker ps --filter "name=ideaforge-ai-control-plane" --format "{{.Ports}}" | grep "->80"
```

Then access:
- **Frontend**: http://localhost:80/ (or http://localhost:8080/ if configured)
- **Backend API**: http://localhost:80/api/
- **Backend Health**: http://localhost:80/health

The ingress is configured to allow access without host headers for these paths.

### Method 2: Port Forward (Easiest for Development)

```bash
# Frontend
kubectl port-forward -n ideaforge-ai service/frontend 3001:3000 --context kind-ideaforge-ai

# Backend API
kubectl port-forward -n ideaforge-ai service/backend 8000:8000 --context kind-ideaforge-ai
```

Then access:
- Frontend: http://localhost:3001
- Backend: http://localhost:8000

### Method 2: Via Ingress (with /etc/hosts)

1. Add to `/etc/hosts`:
```bash
sudo sh -c 'echo "127.0.0.1 ideaforge.local api.ideaforge.local" >> /etc/hosts'
```

2. Access via:
- Frontend: http://ideaforge.local
- Backend API: http://api.ideaforge.local

### Method 3: Direct NodePort Access

The ingress controller exposes services on NodePort. Find the port:

```bash
kubectl get svc -n ingress-nginx ingress-nginx-controller --context kind-ideaforge-ai
```

Then access with Host header:
```bash
# Frontend
curl -H "Host: ideaforge.local" http://localhost:31944

# Backend
curl -H "Host: api.ideaforge.local" http://localhost:31944
```

### Method 4: Direct Access via Ingress Port (No Host Header Required)

The ingress is configured to allow access without host headers. The kind cluster maps the ingress controller to a host port.

**Check which port is mapped:**
```bash
docker ps --filter "name=ideaforge-ai-control-plane" --format "{{.Ports}}" | grep "->80"
```

**Access URLs:**
- **Frontend**: http://localhost:80/ (or http://localhost:8080/ if cluster was created with port 8080)
- **Backend API**: http://localhost:80/api/
- **Backend Health**: http://localhost:80/health

**Note**: If your cluster was created with the default configuration, it uses port **80**, not 8080. To use port 8080, you need to recreate the cluster:
```bash
make kind-delete
make kind-create  # Will now use port 8080
make kind-deploy-internal
```

## Troubleshooting

### Check Ingress Status
```bash
kubectl get ingress -n ideaforge-ai --context kind-ideaforge-ai
kubectl describe ingress ideaforge-ai-ingress -n ideaforge-ai --context kind-ideaforge-ai
```

### Check Services
```bash
kubectl get svc -n ideaforge-ai --context kind-ideaforge-ai
```

### Check Pods
```bash
kubectl get pods -n ideaforge-ai --context kind-ideaforge-ai
```

### Check Ingress Controller
```bash
kubectl get pods -n ingress-nginx --context kind-ideaforge-ai
kubectl get svc -n ingress-nginx --context kind-ideaforge-ai
```

### Test Backend Directly
```bash
kubectl port-forward -n ideaforge-ai service/backend 8000:8000 --context kind-ideaforge-ai
curl http://localhost:8000/health
```

### Test Frontend Directly
```bash
kubectl port-forward -n ideaforge-ai service/frontend 3001:3000 --context kind-ideaforge-ai
curl http://localhost:3001
```

## Make Targets

Use these make targets for easier access:

```bash
# Port forward both services
make kind-port-forward

# Check ingress status
make kind-status

# View ingress logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller --context kind-ideaforge-ai
```

