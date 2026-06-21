#!/usr/bin/env bash
# End-to-end demo against the running control plane.
set -e
BASE=http://localhost:8080/api/assessments

echo "1) Submit a high-risk component for assessment..."
RESP=$(curl -s -X POST "$BASE" \
  -H "Content-Type: application/json" -H "X-Tenant-Id: acme-bank" \
  -d '{"componentDescription":"Legacy PaymentProcessor, Java/Spring, writes directly to the shared CORE_TXN database used by three other services, calls fraud/ledger/notification synchronously in sequence."}')
echo "$RESP"
CID=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['correlationId'])")

echo "2) High risk -> PENDING_APPROVAL. A named human approves..."
curl -s -X POST "$BASE/$CID/approve" -H "X-Approver-Id: vijay.architect" | python3 -m json.tool
