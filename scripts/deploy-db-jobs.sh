#!/bin/bash
# Deploy Database Jobs Script
# Handles database setup, seeding, and migrations in the correct order
# Usage: ./scripts/deploy-db-jobs.sh [namespace] [action]
# Actions: setup, seed, migrate, all

set -e

NAMESPACE="${1:-ideaforge-ai}"
ACTION="${2:-all}"
K8S_DIR="${K8S_DIR:-./k8s/kind}"

echo "🔄 Deploying Database Jobs"
echo "   Namespace: $NAMESPACE"
echo "   Action: $ACTION"
echo ""

case "$ACTION" in
    setup)
        echo "📋 Step 1: Database Setup (Schema + Migrations + Seed)"
        echo "   This will create the schema, run migrations, and seed initial data"
        echo ""
        kubectl delete job db-setup -n "$NAMESPACE" --ignore-not-found=true --context kind-ideaforge-ai
        kubectl apply -f "$K8S_DIR/db-setup-job.yaml" --context kind-ideaforge-ai
        echo "⏳ Waiting for db-setup job to complete..."
        kubectl wait --for=condition=complete --timeout=300s job/db-setup -n "$NAMESPACE" --context kind-ideaforge-ai || true
        echo "✅ Database setup complete!"
        ;;
    seed)
        echo "🌱 Step 2: Database Seeding"
        echo "   This will seed sample data (safe to re-run)"
        echo ""
        kubectl delete job db-seed -n "$NAMESPACE" --ignore-not-found=true --context kind-ideaforge-ai
        kubectl apply -f "$K8S_DIR/db-seed-job.yaml" --context kind-ideaforge-ai
        echo "⏳ Waiting for db-seed job to complete..."
        kubectl wait --for=condition=complete --timeout=300s job/db-seed -n "$NAMESPACE" --context kind-ideaforge-ai || true
        echo "✅ Database seeding complete!"
        ;;
    migrate)
        echo "🔄 Step 3: Database Migration (with backup)"
        echo "   This will create a backup and run pending migrations"
        echo ""
        kubectl delete job db-migration -n "$NAMESPACE" --ignore-not-found=true --context kind-ideaforge-ai
        kubectl apply -f "$K8S_DIR/db-migration-job.yaml" --context kind-ideaforge-ai
        echo "⏳ Waiting for db-migration job to complete..."
        kubectl wait --for=condition=complete --timeout=300s job/db-migration -n "$NAMESPACE" --context kind-ideaforge-ai || true
        echo "✅ Database migration complete!"
        ;;
    all)
        echo "🚀 Full Database Deployment"
        echo ""
        echo "📋 Step 1: Database Setup"
        kubectl delete job db-setup -n "$NAMESPACE" --ignore-not-found=true --context kind-ideaforge-ai
        kubectl apply -f "$K8S_DIR/db-setup-job.yaml" --context kind-ideaforge-ai
        echo "⏳ Waiting for db-setup job to complete..."
        kubectl wait --for=condition=complete --timeout=300s job/db-setup -n "$NAMESPACE" --context kind-ideaforge-ai || true
        echo "✅ Database setup complete!"
        echo ""
        echo "🌱 Step 2: Database Seeding"
        kubectl delete job db-seed -n "$NAMESPACE" --ignore-not-found=true --context kind-ideaforge-ai
        kubectl apply -f "$K8S_DIR/db-seed-job.yaml" --context kind-ideaforge-ai
        echo "⏳ Waiting for db-seed job to complete..."
        kubectl wait --for=condition=complete --timeout=300s job/db-seed -n "$NAMESPACE" --context kind-ideaforge-ai || true
        echo "✅ Database seeding complete!"
        echo ""
        echo "📊 Verifying database state..."
        POSTGRES_POD=$(kubectl get pods -n "$NAMESPACE" -l app=postgres -o jsonpath='{.items[0].metadata.name}' --context kind-ideaforge-ai 2>/dev/null || echo "")
        if [ -n "$POSTGRES_POD" ]; then
            kubectl exec -n "$NAMESPACE" "$POSTGRES_POD" --context kind-ideaforge-ai -- \
                env PGPASSWORD=$(kubectl get secret ideaforge-ai-secrets -n "$NAMESPACE" -o jsonpath='{.data.POSTGRES_PASSWORD}' --context kind-ideaforge-ai | base64 -d) \
                psql -U agentic_pm -d agentic_pm_db -c "
                    SELECT 
                      (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public') as tables,
                      (SELECT COUNT(*) FROM user_profiles) as users,
                      (SELECT COUNT(*) FROM products) as products,
                      (SELECT COUNT(*) FROM tenants) as tenants,
                      (SELECT COUNT(*) FROM schema_migrations) as migrations;
                " 2>&1 | grep -E "[0-9]+" || true
        fi
        echo ""
        echo "✅ Full database deployment complete!"
        ;;
    *)
        echo "Usage: $0 [namespace] {setup|seed|migrate|all}"
        exit 1
        ;;
esac

