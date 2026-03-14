#!/usr/bin/env bash
# deploy.sh — One-command production deployment for roundZero
# Usage: ./deploy.sh [--backend-only | --frontend-only]
set -euo pipefail

PROJECT_ID="roundzero-488704"
REGION="us-central1"
SERVICE="roundzero-backend"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; exit 1; }

# ─── Git commit & push ───────────────────────────────────────────────────────
deploy_git() {
  echo ""
  echo "═══════════════════════════════════════════"
  echo " 📦 Git: Commit & Push to main"
  echo "═══════════════════════════════════════════"
  cd "$ROOT_DIR"

  # Clean stale lock files
  find .git -name "*.lock" -delete 2>/dev/null || true

  if [[ -n "$(git status --porcelain)" ]]; then
    git add -A
    git commit -m "deploy: production update $(date +%Y-%m-%dT%H:%M:%S)"
    git push origin main
    log "Pushed to GitHub (triggers Vercel auto-deploy)"
  else
    warn "No changes to commit"
  fi
}

# ─── Backend: Cloud Run ──────────────────────────────────────────────────────
deploy_backend() {
  echo ""
  echo "═══════════════════════════════════════════"
  echo " 🚀 Backend: Cloud Build → Cloud Run"
  echo "═══════════════════════════════════════════"
  cd "$ROOT_DIR/backend"

  gcloud builds submit \
    --config cloudbuild.yaml \
    --project="$PROJECT_ID" \
    --quiet

  log "Backend deployed to Cloud Run ($REGION)"

  # Ensure public access
  gcloud run services add-iam-policy-binding "$SERVICE" \
    --region="$REGION" \
    --member=allUsers \
    --role=roles/run.invoker \
    --project="$PROJECT_ID" \
    --quiet 2>/dev/null || true

  # Quick health check
  URL="https://${SERVICE}-543685349875.${REGION}.run.app/health"
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL" --max-time 10)
  if [[ "$HTTP_CODE" == "200" ]]; then
    log "Health check passed: $URL"
  else
    warn "Health check returned $HTTP_CODE (may still be starting)"
  fi
}

# ─── Frontend: Vercel (auto via git push) ────────────────────────────────────
deploy_frontend_info() {
  echo ""
  echo "═══════════════════════════════════════════"
  echo " 🌐 Frontend: Vercel (auto-deployed)"
  echo "═══════════════════════════════════════════"
  log "Vercel auto-deploys from GitHub push to main"
  log "Dashboard: https://vercel.com/rahul-pandeys-projects-799aa6db/roundzero"
  log "Live: https://roundzero-xi.vercel.app"
}

# ─── Main ────────────────────────────────────────────────────────────────────
echo "🎯 roundZero Production Deploy"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

case "${1:-all}" in
  --backend-only)
    deploy_git
    deploy_backend
    ;;
  --frontend-only)
    deploy_git
    deploy_frontend_info
    ;;
  all|*)
    deploy_git
    deploy_backend
    deploy_frontend_info
    ;;
esac

echo ""
log "🎉 Deployment complete!"
