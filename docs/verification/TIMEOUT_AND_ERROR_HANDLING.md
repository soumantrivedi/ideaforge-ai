# Timeout and Error Handling Verification

**Last Updated:** 2025-11-27  
**Purpose:** Comprehensive checklist for timeout configuration and error handling to catch issues early in local kind clusters before EKS production deployment.

---

## 1. AI Provider Timeout Configuration

### ✅ ConfigMap Configuration
- [ ] `AGENT_RESPONSE_TIMEOUT` exists in ConfigMap
- [ ] Value is set to `45.0` (leaves 15s buffer for Cloudflare 60s limit)
- [ ] ConfigMap is applied: `kubectl get configmap ideaforge-ai-config -o yaml | grep AGENT_RESPONSE_TIMEOUT`

**Command:**
```bash
kubectl get configmap ideaforge-ai-config -n <namespace> -o jsonpath='{.data.AGENT_RESPONSE_TIMEOUT}'
# Expected: 45.0
```

### ✅ Backend Deployment Configuration
- [ ] `backend.yaml` includes `AGENT_RESPONSE_TIMEOUT` env var from ConfigMap
- [ ] Environment variable is properly referenced: `configMapKeyRef.name: ideaforge-ai-config`
- [ ] Deployment applied: `kubectl get deployment backend -o yaml | grep AGENT_RESPONSE_TIMEOUT`

**Command:**
```bash
kubectl get deployment backend -n <namespace> -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="AGENT_RESPONSE_TIMEOUT")]}'
```

### ✅ Code Configuration
- [ ] `backend/config.py` reads from environment: `os.getenv("AGENT_RESPONSE_TIMEOUT", "50.0")`
- [ ] `backend/agents/agno_base_agent.py` uses `settings.agent_response_timeout`
- [ ] Timeout is applied in `asyncio.wait_for()` call

**Files to Check:**
- `backend/config.py:57`
- `backend/agents/agno_base_agent.py:304`

---

## 2. Ingress/NGINX Timeout Configuration

### ✅ Ingress Annotations
- [ ] `proxy-read-timeout: "600"` (10 minutes for long operations)
- [ ] `proxy-send-timeout: "600"`
- [ ] `proxy-connect-timeout: "60"`
- [ ] `proxy-next-upstream-timeout: "600"`
- [ ] Special endpoint `/api/multi-agent/process` has `proxy_read_timeout 1800s`

**Command:**
```bash
kubectl get ingress -n <namespace> -o yaml | grep -A 5 "proxy.*timeout"
```

**Files to Check:**
- `k8s/eks/ingress-nginx.yaml:17-28`
- `k8s/kind/ingress-nginx.yaml` (if exists)

### ✅ Frontend NGINX Configuration
- [ ] `nginx.conf` has timeout settings for `/api` location
- [ ] `proxy_read_timeout 600s`
- [ ] `proxy_send_timeout 600s`
- [ ] `proxy_connect_timeout 60s`

**Files to Check:**
- `nginx.conf` (frontend container)

---

## 3. Cloudflare Timeout Awareness

### ✅ Timeout Hierarchy Verification
```
Cloudflare: 60s (hard limit, cannot change)
  └─ AI Provider: 45s (ConfigMap: AGENT_RESPONSE_TIMEOUT)
      └─ Ingress: 600s (for most endpoints)
          └─ Special endpoint: 1800s (for /api/multi-agent/process)
```

**Verification:**
- [ ] AI timeout (45s) < Cloudflare timeout (60s) ✅
- [ ] Ingress timeout (600s) > AI timeout (45s) ✅
- [ ] Special endpoint timeout (1800s) > AI timeout (45s) ✅

### ✅ Cloudflare-Specific Considerations
- [ ] AI responses complete before 60s to avoid 504 errors
- [ ] Error messages guide users if timeout occurs
- [ ] Long operations use background tasks or polling pattern
- [ ] Direct API subdomain access documented (bypasses Cloudflare if needed)

**Note:** Cloudflare 60s timeout is a hard limit. If AI operations need > 60s:
1. Use background tasks with polling
2. Use direct API subdomain (if available)
3. Contact Cloudflare admin for timeout increase
4. Break operations into smaller chunks

---

## 4. Exception Handling Verification

### ✅ HTTPException Pattern
All endpoints must properly re-raise HTTPException:

```python
try:
    # ... code ...
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied")
except HTTPException:
    # Re-raise HTTPException - don't convert to 500
    raise
except Exception as e:
    # Only catch non-HTTP exceptions
    logger.error("error_description", error=str(e))
    raise HTTPException(status_code=500, detail=str(e))
```

### ✅ Files to Verify
- [ ] `backend/api/database.py` - All endpoints properly handle HTTPException
- [ ] `backend/api/products.py` - Product access checks
- [ ] `backend/api/integrations.py` - Integration endpoints
- [ ] `backend/api/export.py` - Export endpoints
- [ ] Any endpoint with access control logic

**Command:**
```bash
# Check for proper HTTPException handling
grep -r "except HTTPException:" backend/api/
grep -r "except Exception as e:" backend/api/ | grep -v "except HTTPException"
```

### ✅ Common Issues to Avoid
- [ ] ❌ Catching HTTPException and converting to 500
- [ ] ❌ Using generic `except Exception` that catches HTTPException
- [ ] ❌ Not re-raising HTTPException before generic exception handler

### ✅ Test Cases
- [ ] Test 403 errors return 403 (not 500)
- [ ] Test 404 errors return 404 (not 500)
- [ ] Test 500 errors only for actual server errors
- [ ] Test error messages are clear and actionable

---

## 5. Database Constraint Verification

### ✅ Provider Constraint Check
- [ ] `user_api_keys.provider` CHECK constraint includes all providers:
  - `'openai'`, `'anthropic'`, `'google'`, `'v0'`, `'lovable'`, `'github'`, `'atlassian'`
- [ ] Code uses exact same provider values
- [ ] Migration scripts updated for future deployments

**Command:**
```bash
# Check migration files
grep -r "provider.*CHECK" init-db/migrations/
grep -r "provider.*CHECK" supabase/migrations/
```

**Files to Check:**
- `init-db/migrations/20251124000003_user_api_keys.sql`
- `supabase/migrations/20251124000003_user_api_keys.sql`
- `supabase/migrations/20251124000002_user_api_keys.sql`

### ✅ Message Type Constraint Check
- [ ] `conversation_history.message_type` CHECK constraint matches code
- [ ] Code uses `'agent'` not `'assistant'` for agent messages
- [ ] Migration scripts updated if constraint changed

**Command:**
```bash
# Check code usage
grep -r "message_type.*assistant" backend/
grep -r "message_type.*agent" backend/
```

**Files to Check:**
- `backend/main.py` - Message type when saving conversation
- Database migration files

### ✅ Test Cases
- [ ] Test saving GitHub PAT (provider: 'github')
- [ ] Test saving Atlassian token (provider: 'atlassian')
- [ ] Test saving conversation with agent message (type: 'agent')
- [ ] Verify no constraint violation errors

---

## 6. Product Access Verification

### ✅ Access Check Pattern
All product-related endpoints must:
1. Verify product exists
2. Verify user is owner OR product is shared with user
3. Verify tenant matches (for multi-tenant)
4. Raise 403 with clear message if access denied

### ✅ Files to Verify
- [ ] `backend/api/database.py` - Phase submissions, conversation history
- [ ] `backend/api/products.py` - Product operations
- [ ] `backend/api/export.py` - Export operations

### ✅ Test Cases
- [ ] Test with product owner (should work)
- [ ] Test with shared user (view permission) - GET should work, POST may need edit
- [ ] Test with shared user (edit permission) - GET and POST should work
- [ ] Test with non-shared user (should get 403)
- [ ] Test cross-tenant access (should get 403)
- [ ] Verify 403 errors return 403 (not 500)

---

## 7. Local Kind Cluster Verification (Before EKS)

### ✅ Complete Timeout Check
```bash
# 1. Check ConfigMap
kubectl get configmap ideaforge-ai-config -n ideaforge-ai --context kind-ideaforge-ai -o yaml | grep AGENT_RESPONSE_TIMEOUT

# 2. Check backend deployment
kubectl get deployment backend -n ideaforge-ai --context kind-ideaforge-ai -o yaml | grep AGENT_RESPONSE_TIMEOUT

# 3. Check ingress timeouts
kubectl get ingress -n ideaforge-ai --context kind-ideaforge-ai -o yaml | grep timeout

# 4. Test AI timeout behavior (should timeout at 45s, not 60s)
# Make a request that takes > 45s but < 60s
```

### ✅ Complete Exception Handling Check
```bash
# 1. Check for proper HTTPException handling
grep -r "except HTTPException:" backend/api/

# 2. Test 403 errors return 403
curl -X GET http://localhost:80/api/db/products/<non-existent-product-id>
# Should return 404 or 403, not 500

# 3. Check logs for exception handling
kubectl logs -n ideaforge-ai --context kind-ideaforge-ai deployment/backend --tail=100 | grep -i "error\|exception"
```

### ✅ Complete Database Constraint Check
```bash
# 1. Check migration files
grep -r "CHECK.*provider" init-db/migrations/
grep -r "CHECK.*message_type" init-db/migrations/

# 2. Test provider values
# Try saving GitHub PAT, Atlassian token in local cluster

# 3. Test message types
# Try saving conversation with agent message
```

### ✅ Complete Product Access Check
```bash
# 1. Test product access with different users
# 2. Test product sharing
# 3. Verify 403 errors return 403
```

---

## 8. EKS Production Deployment Checklist

### Before Deployment:
- [ ] All timeout configurations verified in local kind cluster
- [ ] All exception handling verified in local kind cluster
- [ ] All database constraints verified in local kind cluster
- [ ] All product access checks verified in local kind cluster
- [ ] ConfigMap updated with correct timeout values
- [ ] Backend deployment includes timeout env var
- [ ] Ingress timeouts configured correctly
- [ ] Migration scripts include all constraint updates

### After Deployment:
- [ ] Verify ConfigMap: `kubectl get configmap ideaforge-ai-config -n <namespace> -o yaml`
- [ ] Verify backend env vars: `kubectl get deployment backend -n <namespace> -o yaml | grep AGENT_RESPONSE_TIMEOUT`
- [ ] Verify ingress timeouts: `kubectl get ingress -n <namespace> -o yaml | grep timeout`
- [ ] Test AI timeout: Make request that should timeout at 45s
- [ ] Test exception handling: Verify 403/404 return correct status codes
- [ ] Test database constraints: Verify all provider values work
- [ ] Test product access: Verify access control works correctly
- [ ] Monitor logs for timeout errors: `kubectl logs -n <namespace> deployment/backend | grep -i timeout`
- [ ] Monitor logs for 500 errors: `kubectl logs -n <namespace> deployment/backend | grep "500"`

---

## 9. Common Issues and Solutions

### Issue: 504 Gateway Timeout from Cloudflare
**Cause:** AI response takes > 60s  
**Solution:**
1. Reduce `AGENT_RESPONSE_TIMEOUT` to 45s (ConfigMap)
2. Use background tasks with polling for long operations
3. Use direct API subdomain if available
4. Break operations into smaller chunks

### Issue: 500 Internal Server Error for 403 Access Denied
**Cause:** HTTPException not properly re-raised  
**Solution:**
1. Add `except HTTPException: raise` before generic exception handler
2. Verify all endpoints follow exception handling pattern
3. Test in local kind cluster before EKS deployment

### Issue: 500 Internal Server Error for Database Constraint Violation
**Cause:** Database CHECK constraint doesn't match code usage  
**Solution:**
1. Update migration scripts to include all constraint values
2. Update database constraint in production (temporary fix)
3. Verify code uses exact constraint values
4. Test in local kind cluster before EKS deployment

### Issue: Product Access Denied (403) but User Can View Product
**Cause:** Inconsistent access checks between GET and POST  
**Solution:**
1. Verify access check logic is consistent
2. Share product with appropriate permission (view/edit)
3. Verify tenant checks are correct
4. Test in local kind cluster before EKS deployment

---

## 10. Quick Verification Script

```bash
#!/bin/bash
# Quick verification script for timeout and error handling

NAMESPACE="${1:-ideaforge-ai}"
CONTEXT="${2:-kind-ideaforge-ai}"

echo "=== Timeout Configuration Check ==="
echo "1. ConfigMap timeout:"
kubectl get configmap ideaforge-ai-config -n $NAMESPACE --context $CONTEXT -o jsonpath='{.data.AGENT_RESPONSE_TIMEOUT}' && echo ""

echo "2. Backend deployment timeout:"
kubectl get deployment backend -n $NAMESPACE --context $CONTEXT -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="AGENT_RESPONSE_TIMEOUT")].valueFrom.configMapKeyRef.key}' && echo ""

echo "3. Ingress timeouts:"
kubectl get ingress -n $NAMESPACE --context $CONTEXT -o yaml | grep -E "proxy.*timeout|timeout.*:" | head -5

echo ""
echo "=== Exception Handling Check ==="
echo "4. HTTPException handling:"
grep -r "except HTTPException:" backend/api/ | wc -l | xargs echo "Files with HTTPException handling:"

echo ""
echo "=== Database Constraint Check ==="
echo "5. Provider constraint:"
grep -r "provider.*CHECK" init-db/migrations/ supabase/migrations/ | grep -o "IN ([^)]*)" | head -1

echo ""
echo "✅ Verification complete"
```

---

## Summary

**Critical Checks Before EKS Deployment:**
1. ✅ AI timeout configured via ConfigMap (45s)
2. ✅ Backend deployment references ConfigMap timeout
3. ✅ Ingress timeouts > AI timeout
4. ✅ Exception handling properly re-raises HTTPException
5. ✅ Database constraints match code usage
6. ✅ Product access checks are consistent
7. ✅ All tests pass in local kind cluster

**Remember:** Catch issues early in local kind cluster to avoid production issues!

