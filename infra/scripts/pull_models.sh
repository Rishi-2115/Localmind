#!/bin/bash
# Ollama Model Auto-Pull Script
# Runs as init container to pre-fetch LLM and embedding models
# This ensures models are available before API/Worker services start

set -e

OLLAMA_ENDPOINT="${OLLAMA_BASE_URL:-http://ollama:11434}"
MAX_RETRIES=60
RETRY_DELAY=2

# Models to pull
GENERATION_MODEL="llama3.2:3b"      # ~2 GB
EMBEDDING_MODEL="nomic-embed-text"  # ~275 MB
QWEN_MODEL="qwen2.5:7b"             # ~4 GB (optional backup)

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

wait_for_ollama() {
    log "Waiting for Ollama at $OLLAMA_ENDPOINT..."
    for i in $(seq 1 $MAX_RETRIES); do
        if curl -s "$OLLAMA_ENDPOINT/api/tags" > /dev/null 2>&1; then
            log "✓ Ollama is ready"
            return 0
        fi
        if [ $((i % 10)) -eq 0 ]; then
            log "Still waiting... (attempt $i/$MAX_RETRIES)"
        fi
        sleep $RETRY_DELAY
    done
    log "✗ Ollama failed to start after $((MAX_RETRIES * RETRY_DELAY)) seconds"
    return 1
}

pull_model() {
    local model=$1
    log "Pulling model: $model"
    
    # Check if model already exists
    if curl -s "$OLLAMA_ENDPOINT/api/tags" | grep -q "\"name\":\"$model\""; then
        log "✓ Model already available: $model"
        return 0
    fi
    
    log "Downloading $model (this may take several minutes)..."
    if curl -X POST "$OLLAMA_ENDPOINT/api/pull" \
        -H "Content-Type: application/json" \
        -d "{\"name\":\"$model\",\"stream\":false}" \
        -s -o /dev/null -w "%{http_code}\n" | grep -q "200"; then
        log "✓ Successfully pulled: $model"
        return 0
    else
        log "✗ Failed to pull: $model"
        return 1
    fi
}

validate_embedding_dims() {
    local model=$1
    local expected_dim=$2
    
    log "Validating $model dimensions (expecting $expected_dim)..."
    
    response=$(curl -s -X POST "$OLLAMA_ENDPOINT/api/embeddings" \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"$model\",\"prompt\":\"test validation\"}")
    
    # Extract embedding array and count dimensions
    actual_dim=$(echo "$response" | grep -o '"embedding":\[[^]]*\]' | tr ',' '\n' | wc -l)
    
    if [ "$actual_dim" -ge "$((expected_dim - 1))" ]; then
        log "✓ $model produces ~$actual_dim-dimensional vectors (correct)"
        return 0
    else
        log "⚠ $model produces ~$actual_dim dims (expected $expected_dim) - may cause FAISS failures"
        return 1
    fi
}

main() {
    log "========== Ollama Model Initialization =========="
    log "Endpoint: $OLLAMA_ENDPOINT"
    log ""
    
    # Wait for Ollama to start
    if ! wait_for_ollama; then
        log "FATAL: Ollama is unreachable - cannot proceed"
        exit 1
    fi
    
    # Pull generation model (critical)
    log ""
    log "--- Step 1: Generation Model ---"
    if ! pull_model "$GENERATION_MODEL"; then
        log "FATAL: Generation model required"
        exit 1
    fi
    
    # Pull embedding model (critical)
    log ""
    log "--- Step 2: Embedding Model ---"
    if ! pull_model "$EMBEDDING_MODEL"; then
        log "FATAL: Embedding model required"
        exit 1
    fi
    
    # Validate embedding dimensions
    if ! validate_embedding_dims "$EMBEDDING_MODEL" 768; then
        log "WARNING: Embedding dimensions mismatch - this will likely cause failures"
    fi
    
    # Pull qwen model (optional - nice to have)
    log ""
    log "--- Step 3: Backup Model (Optional) ---"
    if pull_model "$QWEN_MODEL"; then
        log "✓ Backup model available"
    else
        log "⚠ Backup model skipped (non-critical)"
    fi
    
    log ""
    log "========== Initialization Complete =========="
    log "Ready to serve:"
    log "  ✓ Generation:  $GENERATION_MODEL"
    log "  ✓ Embedding:   $EMBEDDING_MODEL"
    log ""
    
    exit 0
}

main "$@"
    echo "[init] Attempt $i/60 — Ollama not ready yet, retrying in 2 s …"
    sleep 2
done

# Pull each model (idempotent — skips if already present)
for MODEL in "${MODELS[@]}"; do
    echo "[init] Pulling model: $MODEL"
    curl -sf "$OLLAMA_HOST/api/pull" -d "{\"name\":\"$MODEL\"}" | while IFS= read -r line; do
        STATUS=$(echo "$line" | grep -o '"status":"[^"]*"' | head -1)
        echo "  $MODEL — $STATUS"
    done
    echo "[init] $MODEL ready."
done

echo "[init] All models pulled. Exiting."
