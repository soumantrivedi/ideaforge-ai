# Ingress Deployment Guide for IdeaForge AI on EKS

## Overview

This guide explains how to deploy an externally accessible ingress for IdeaForge AI on your EKS cluster. Two options are available:

1. **NGINX Ingress** (Recommended for quick setup) - Uses the platform domain pattern
2. **ALB Ingress** (For custom domains) - Requires AWS ACM certificate

## Current Cluster Analysis

Based on the cluster analysis:
- **Namespace**: `20890-ideaforge-ai-dev-58a50`
- **Services**: 
  - `backend` (port 8000)
  - `frontend` (port 3000)
- **Available Ingress Controllers**:
  - `nginx` (k8s.io/ingress-nginx) - ✅ Active and working
  - `alb` (eks.amazonaws.com/alb) - Available but requires certificate ARN
  - `acm-external` (k8s.io/acm-external-ingress-nginx)
  - `mtls-internal` (k8s.io/mtls-internal-ingress-nginx)

## Option 1: NGINX Ingress (Recommended)

### Why NGINX?
- ✅ Already working in the cluster (used by other apps)
- ✅ Automatic DNS via external-dns
- ✅ No certificate management required (handled by platform)
- ✅ Quick to deploy

### Configuration

File: `k8s/eks/ingress-nginx.yaml`

**Features:**
- Uses platform domain: `*.cf.platform.mckinsey.cloud`
- Automatic DNS record creation via external-dns
- SSL/TLS handled by the platform
- Matches pattern used by other applications in the cluster

**Hostnames:**
- Frontend: `ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud`
- Backend API: `api-ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud`

### Deployment Steps

```bash
# Set kubeconfig
export KUBECONFIG=/tmp/kubeconfig.lMC4po

# Deploy NGINX ingress
kubectl apply -f k8s/eks/ingress-nginx.yaml

# Verify deployment
kubectl get ingress ideaforge-ai-ingress-nginx -n 20890-ideaforge-ai-dev-58a50

# Check status (wait for ADDRESS to be populated)
kubectl describe ingress ideaforge-ai-ingress-nginx -n 20890-ideaforge-ai-dev-58a50
```

### Expected Output

After deployment, you should see:
```
NAME                          CLASS   HOSTS                                                                    ADDRESS
ideaforge-ai-ingress-nginx    nginx   ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud,...   k8s-ingressn-...elb.us-east-1.amazonaws.com
```

The ADDRESS will be an ELB hostname. DNS records will be automatically created by external-dns.

### Access URLs

Once DNS propagates (usually 1-5 minutes):
- Frontend: `https://ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud`
- Backend API: `https://api-ideaforge-ai-dev-58a50.cf.platform.mckinsey.cloud`

## Option 2: ALB Ingress (For Custom Domains)

### Why ALB?
- ✅ Use custom domains (e.g., `ideaforge.ai`)
- ✅ AWS-native load balancing
- ✅ Direct control over SSL certificates
- ⚠️ Requires AWS ACM certificate

### Prerequisites

1. **AWS ACM Certificate** for your domain:
   - Domain: `ideaforge.ai` and `*.ideaforge.ai` (or separate certificates)
   - Region: Must match your EKS cluster region (us-east-1)
   - Status: Must be validated and issued

2. **Get Certificate ARN**:
   ```bash
   aws acm list-certificates --region us-east-1 \
     --query 'CertificateSummaryList[?contains(DomainName, `ideaforge.ai`)].CertificateArn' \
     --output text
   ```

3. **DNS Configuration**:
   - Point `ideaforge.ai` and `api.ideaforge.ai` to the ALB (after deployment)

### Configuration

File: `k8s/eks/ingress-alb.yaml`

**Before deploying, update:**
1. Certificate ARN (line 15): Replace `ACCOUNT_ID` and `CERT_ID`
2. Optional: S3 bucket for access logs (if needed)
3. Optional: WAF ARN (if using AWS WAF)

### Deployment Steps

```bash
# Set kubeconfig
export KUBECONFIG=/tmp/kubeconfig.lMC4po

# 1. Update certificate ARN in ingress-alb.yaml
# Edit: alb.ingress.kubernetes.io/certificate-arn

# 2. Deploy ALB ingress
kubectl apply -f k8s/eks/ingress-alb.yaml

# 3. Verify deployment
kubectl get ingress ideaforge-ai-ingress-alb -n 20890-ideaforge-ai-dev-58a50

# 4. Wait for ALB creation (may take 2-5 minutes)
kubectl describe ingress ideaforge-ai-ingress-alb -n 20890-ideaforge-ai-dev-58a50

# 5. Get ALB hostname
kubectl get ingress ideaforge-ai-ingress-alb -n 20890-ideaforge-ai-dev-58a50 -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

### Expected Output

After deployment, you should see:
```
NAME                      CLASS   HOSTS                          ADDRESS
ideaforge-ai-ingress-alb  alb     ideaforge.ai,api.ideaforge.ai  k8s-...-...elb.amazonaws.com
```

### DNS Configuration

After ALB is created, update your DNS records:

```bash
# Get ALB hostname
ALB_HOSTNAME=$(kubectl get ingress ideaforge-ai-ingress-alb -n 20890-ideaforge-ai-dev-58a50 -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Get ALB IP (if needed for A record)
ALB_IP=$(dig +short $ALB_HOSTNAME | head -1)

echo "ALB Hostname: $ALB_HOSTNAME"
echo "ALB IP: $ALB_IP"
```

Then create DNS records:
- `ideaforge.ai` → CNAME to ALB hostname (or A record to ALB IP)
- `api.ideaforge.ai` → CNAME to ALB hostname (or A record to ALB IP)

### Access URLs

Once DNS propagates:
- Frontend: `https://ideaforge.ai`
- Backend API: `https://api.ideaforge.ai`

## Troubleshooting

### NGINX Ingress Issues

**Problem: No ADDRESS assigned**
```bash
# Check ingress controller pods
kubectl get pods -n kube-system | grep ingress-nginx

# Check ingress events
kubectl describe ingress ideaforge-ai-ingress-nginx -n 20890-ideaforge-ai-dev-58a50

# Check external-dns logs (if DNS not created)
kubectl logs -n kube-system -l app.kubernetes.io/name=external-dns
```

**Problem: 502 Bad Gateway**
```bash
# Check backend service
kubectl get svc backend -n 20890-ideaforge-ai-dev-58a50

# Check backend pods
kubectl get pods -n 20890-ideaforge-ai-dev-58a50 -l app=backend

# Check backend logs
kubectl logs -n 20890-ideaforge-ai-dev-58a50 -l app=backend
```

### ALB Ingress Issues

**Problem: No ADDRESS assigned**
```bash
# Check AWS Load Balancer Controller logs
kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller

# Check ingress events
kubectl describe ingress ideaforge-ai-ingress-alb -n 20890-ideaforge-ai-dev-58a50

# Verify certificate ARN is correct
aws acm describe-certificate --certificate-arn <YOUR_ARN> --region us-east-1
```

**Problem: Certificate not found**
- Ensure certificate is in the same region as your EKS cluster
- Verify certificate status: `aws acm list-certificates --region us-east-1`
- Check certificate validation status

**Problem: ALB not accessible**
- Check security groups allow traffic on ports 80/443
- Verify ALB is internet-facing (not internal)
- Check target group health checks

### General Issues

**Check Service Endpoints**
```bash
kubectl get endpoints -n 20890-ideaforge-ai-dev-58a50
```

**Test Service Connectivity**
```bash
# Port forward to test services directly
kubectl port-forward -n 20890-ideaforge-ai-dev-58a50 svc/backend 8000:8000
kubectl port-forward -n 20890-ideaforge-ai-dev-58a50 svc/frontend 3000:3000
```

**Check Ingress Controller**
```bash
# NGINX
kubectl get pods -n kube-system | grep ingress-nginx

# ALB
kubectl get pods -n kube-system | grep aws-load-balancer
```

## Switching Between Ingress Types

If you need to switch from one ingress type to another:

```bash
# Delete current ingress
kubectl delete ingress ideaforge-ai-ingress-nginx -n 20890-ideaforge-ai-dev-58a50
# OR
kubectl delete ingress ideaforge-ai-ingress-alb -n 20890-ideaforge-ai-dev-58a50

# Deploy new ingress
kubectl apply -f k8s/eks/ingress-nginx.yaml
# OR
kubectl apply -f k8s/eks/ingress-alb.yaml
```

## Current Ingress Status

The current ingress (`ideaforge-ai-ingress`) is configured for ALB but has placeholder certificate ARN, which is why it's not working. You can either:

1. **Update the existing ingress** with a valid certificate ARN
2. **Deploy one of the new configurations** (nginx or alb) and delete the old one

## Recommendations

1. **For Development/Testing**: Use NGINX ingress (Option 1) - quick and simple
2. **For Production with Custom Domain**: Use ALB ingress (Option 2) - more control
3. **Always test** with port-forwarding first before deploying ingress
4. **Monitor** ingress controller logs during deployment
5. **Verify** DNS propagation before testing external access

## Next Steps

1. Review the configuration files:
   - `k8s/eks/ingress-nginx.yaml` (Option 1)
   - `k8s/eks/ingress-alb.yaml` (Option 2)

2. Choose your preferred option

3. Update any required values (certificate ARN for ALB, hostnames if needed)

4. Deploy and verify

5. Update DNS if using custom domains (ALB option)

