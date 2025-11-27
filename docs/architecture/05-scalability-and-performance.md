# Scalability and Performance Architecture

## Overview

IdeaForge AI is designed to support **200+ concurrent users** with horizontal pod autoscaling capabilities to scale effectively without impacting performance.

## Architecture Components

### 1. Horizontal Pod Autoscaling (HPA)

#### Backend HPA Configuration
- **Min Replicas**: 3 (for high availability)
- **Max Replicas**: 20 (supports 200+ concurrent users)
- **Scaling Metrics**:
  - CPU: Scale up when average utilization exceeds 70%
  - Memory: Scale up when average utilization exceeds 80%
- **Scale-Up Policy**: Aggressive (up to 4 pods per 30 seconds)
- **Scale-Down Policy**: Conservative (max 2 pods per 60 seconds, 5-minute stabilization window)

#### Frontend HPA Configuration
- **Min Replicas**: 3 (for high availability)
- **Max Replicas**: 15 (less CPU-intensive than backend)
- **Scaling Metrics**: Same as backend
- **Scale-Up Policy**: Up to 3 pods per 30 seconds
- **Scale-Down Policy**: Same as backend

### 2. Resource Configuration

#### Backend Pod Resources
- **Requests**: 512Mi memory, 250m CPU (allows better pod density)
- **Limits**: 2Gi memory, 2000m CPU (for AI processing and peak load)
- **Capacity per Pod**: ~10-15 concurrent users (with AI processing)
- **Total Capacity**: 3-20 pods = 30-300 concurrent users

#### Frontend Pod Resources
- **Requests**: 256Mi memory, 100m CPU
- **Limits**: 512Mi memory, 500m CPU
- **Capacity per Pod**: ~20-30 concurrent users (static content serving)
- **Total Capacity**: 3-15 pods = 60-450 concurrent users

### 3. Database Connection Pooling

#### PostgreSQL Configuration
- **Max Connections**: 500 (supports 20 backend pods * 25 connections each)
- **Shared Buffers**: 512MB
- **Effective Cache Size**: 1536MB
- **Work Memory**: 4MB per connection
- **Connection Pool per Backend Pod**:
  - Base pool size: 15 connections
  - Max overflow: 25 connections
  - Total per pod: 40 connections max
  - With 20 pods: Up to 800 connections (but limited by PostgreSQL max_connections=500)

#### Connection Pool Strategy
- **Pool Size**: 15 connections per pod (increased from 10)
- **Max Overflow**: 25 connections per pod (increased from 20)
- **Pool Recycle**: 3600 seconds (1 hour)
- **Pool Timeout**: 30 seconds
- **Pool Pre-Ping**: Enabled (verify connections before use)

### 4. Redis Token Storage

#### Redis Configuration
- **Memory Limit**: 1GB (increased for token storage)
- **Eviction Policy**: allkeys-lru (evict least recently used keys)
- **Persistence**: AOF (Append-Only File) enabled
- **Resources**:
  - Requests: 512Mi memory, 200m CPU
  - Limits: 2Gi memory, 1000m CPU

#### Token Storage Strategy
- Tokens stored in Redis for distributed access across backend pods
- Fallback to in-memory storage if Redis unavailable
- Token expiration: 7 days
- Supports 200+ concurrent sessions

### 5. Load Distribution

#### Service Configuration
- **Backend Service**: ClusterIP with 3-20 pods
- **Frontend Service**: ClusterIP with 3-15 pods
- **Ingress**: NGINX Ingress Controller with load balancing
- **Session Affinity**: None (stateless design with Redis token storage)

### 6. Performance Optimizations

#### Database Optimizations
- Connection pooling with pre-ping verification
- Connection recycling to prevent stale connections
- Optimized PostgreSQL settings for concurrent connections
- Indexed queries for fast lookups

#### Application Optimizations
- Async/await for non-blocking I/O
- Redis for distributed token storage
- Efficient connection management
- Resource limits to prevent pod starvation

#### Scaling Strategy
1. **Start**: 3 backend pods, 3 frontend pods
2. **Scale Up**: When CPU > 70% or Memory > 80% average across pods
3. **Scale Down**: After 5 minutes of low utilization
4. **Peak Load**: Up to 20 backend pods, 15 frontend pods

## Capacity Planning

### For 200 Concurrent Users

#### Backend Requirements
- **Average Load**: ~7-10 pods (200 users / 20-30 users per pod)
- **Peak Load**: ~10-15 pods (with AI processing overhead)
- **Database Connections**: ~150-200 connections (10 pods * 15-20 connections)

#### Frontend Requirements
- **Average Load**: ~7-10 pods (200 users / 20-30 users per pod)
- **Peak Load**: ~10 pods
- **Memory**: ~2.5-5GB total (10 pods * 256-512Mi)

#### Database Requirements
- **Connections**: 500 max connections configured
- **Memory**: 2GB limit (sufficient for 200 concurrent users)
- **Storage**: 20GB PVC (adjustable based on data growth)

#### Redis Requirements
- **Memory**: 1GB limit (sufficient for 200+ active sessions)
- **CPU**: 200m-1000m (minimal CPU usage for token storage)

## Monitoring and Metrics

### Key Metrics to Monitor
1. **Pod Count**: Current replicas vs. min/max
2. **CPU Utilization**: Average across all pods
3. **Memory Utilization**: Average across all pods
4. **Request Rate**: Requests per second
5. **Response Time**: P50, P95, P99 latencies
6. **Database Connections**: Active connections vs. max
7. **Redis Memory**: Used memory vs. max memory
8. **Error Rate**: 4xx and 5xx errors

### HPA Status
```bash
kubectl get hpa -n ideaforge-ai
kubectl describe hpa backend-hpa -n ideaforge-ai
kubectl describe hpa frontend-hpa -n ideaforge-ai
```

## Testing Scalability

### Load Testing Commands
```bash
# Test concurrent logins
for i in {1..200}; do
  curl -X POST http://localhost:8080/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@ideaforge.ai","password":"password123"}' &
done
wait

# Monitor HPA scaling
watch kubectl get hpa -n ideaforge-ai
```

## Notes

- **Kind Cluster Limitation**: HPA requires metrics-server. Kind clusters may need metrics-server installed separately.
- **Production Recommendations**: 
  - Use managed Kubernetes (EKS, GKE, AKS) with built-in metrics-server
  - Consider using managed PostgreSQL and Redis services
  - Implement request rate limiting
  - Add monitoring and alerting (Prometheus, Grafana)
  - Use CDN for static assets
  - Implement caching layers

