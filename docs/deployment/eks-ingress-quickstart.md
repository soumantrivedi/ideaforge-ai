# Quick Start: Deploy Ingress for IdeaForge AI

## Current Situation

- **Current Ingress**: `ideaforge-ai-ingress` (ALB) - Not working (missing certificate ARN)
- **Namespace**: `20890-ideaforge-ai-dev-58a50`
- **Services**: `backend:8000`, `frontend:3000`

## Quick Decision Guide

### Use NGINX Ingress if:
- ✅ You want quick deployment (no certificate needed)
- ✅ Platform domain (`*.cf.platform.mckinsey.cloud`) is acceptable
- ✅ You want automatic DNS management

### Use ALB Ingress if:
- ✅ You need custom domain (`ideaforge.ai`)
- ✅ You have AWS ACM certificate ready
- ✅ You want AWS-native load balancing

## Option 1: NGINX Ingress (5 minutes)

```bash
export KUBECONFIG=/tmp/kubeconfig.lMC4po

# Deploy
kubectl apply -f k8s/eks/ingress-nginx.yaml

# Check status
kubectl get ingress ideaforge-ai-ingress-nginx -n 20890-ideaforge-ai-dev-58a50

# Wait for ADDRESS (1-2 minutes)
watch kubectl get ingress ideaforge-ai-ingress-nginx -n 20890-ideaforge-ai-dev-58a50
```

**URLs** (after DNS propagation):
- Frontend: `https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud`
- API: `https://api-ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud`

## Option 2: ALB Ingress (10-15 minutes)

### Step 1: Get Certificate ARN

```bash
# List certificates
aws acm list-certificates --region us-east-1 \
  --query 'CertificateSummaryList[?contains(DomainName, `ideaforge.ai`)].{Domain:DomainName,ARN:CertificateArn}' \
  --output table
```

### Step 2: Update Configuration

Edit `k8s/eks/ingress-alb.yaml`:
- Line 15: Replace `ACCOUNT_ID` and `CERT_ID` with your certificate ARN

### Step 3: Deploy

```bash
export KUBECONFIG=/tmp/kubeconfig.lMC4po

# Deploy
kubectl apply -f k8s/eks/ingress-alb.yaml

# Check status (wait 2-5 minutes for ALB creation)
kubectl get ingress ideaforge-ai-ingress-alb -n 20890-ideaforge-ai-dev-58a50

# Get ALB hostname
kubectl get ingress ideaforge-ai-ingress-alb -n 20890-ideaforge-ai-dev-58a50 \
  -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

### Step 4: Configure DNS

Point your domain to the ALB hostname:
- `ideaforge.ai` → CNAME to ALB hostname
- `api.ideaforge.ai` → CNAME to ALB hostname

**URLs** (after DNS propagation):
- Frontend: `https://ideaforge.ai`
- API: `https://api.ideaforge.ai`

## Cleanup Old Ingress (Optional)

If you want to remove the non-working ingress:

```bash
kubectl delete ingress ideaforge-ai-ingress -n 20890-ideaforge-ai-dev-58a50
```

## Troubleshooting

### Check if services are running
```bash
kubectl get pods -n 20890-ideaforge-ai-dev-58a50
kubectl get svc -n 20890-ideaforge-ai-dev-58a50
```

### Test services directly (bypass ingress)
```bash
# Backend
kubectl port-forward -n 20890-ideaforge-ai-dev-58a50 svc/backend 8000:8000
# Then: curl http://localhost:8000/health

# Frontend
kubectl port-forward -n 20890-ideaforge-ai-dev-58a50 svc/frontend 3000:3000
# Then: open http://localhost:3000
```

### Check ingress events
```bash
kubectl describe ingress <ingress-name> -n 20890-ideaforge-ai-dev-58a50
```

## Files Created

1. `k8s/eks/ingress-nginx.yaml` - NGINX ingress configuration
2. `k8s/eks/ingress-alb.yaml` - ALB ingress configuration  
3. `k8s/eks/INGRESS_DEPLOYMENT_GUIDE.md` - Detailed guide
4. `k8s/eks/INGRESS_QUICK_START.md` - This file

## Next Steps

1. Review the configuration files
2. Choose NGINX (quick) or ALB (custom domain)
3. Deploy and verify
4. Test access

