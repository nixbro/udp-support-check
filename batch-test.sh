#!/bin/bash
# Batch UDP testing script for proxy lists
# Author: nixnode

set -e

if [ $# -lt 1 ]; then
    echo "Usage: $0 <proxy-list-file> [username] [password]"
    echo ""
    echo "Proxy list format (one per line):"
    echo "  host:port"
    echo "  203.0.113.10:1080"
    echo "  proxy.example.com:1080"
    exit 1
fi

PROXY_LIST="$1"
USERNAME="${2:-}"
PASSWORD="${3:-}"
RESULTS_FILE="udp-test-results-$(date +%Y%m%d-%H%M%S).txt"

if [ ! -f "$PROXY_LIST" ]; then
    echo "Error: File not found: $PROXY_LIST"
    exit 1
fi

TOTAL=0
PASSED=0
FAILED=0

echo "UDP Batch Testing" | tee "$RESULTS_FILE"
echo "Started: $(date)" | tee -a "$RESULTS_FILE"
echo "============================================================" | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"

while IFS= read -r line; do
    [ -z "$line" ] && continue
    [[ "$line" =~ ^#.* ]] && continue

    HOST=$(echo "$line" | cut -d: -f1)
    PORT=$(echo "$line" | cut -d: -f2)

    ((TOTAL++))

    echo -n "Testing $HOST:$PORT ... " | tee -a "$RESULTS_FILE"

    if [ -n "$USERNAME" ] && [ -n "$PASSWORD" ]; then
        if python3 udp-check.py "$HOST" "$PORT" -u "$USERNAME" -p "$PASSWORD" -q 2>/dev/null; then
            echo "✓ PASS" | tee -a "$RESULTS_FILE"
            ((PASSED++))
        else
            echo "✗ FAIL" | tee -a "$RESULTS_FILE"
            ((FAILED++))
        fi
    else
        if python3 udp-check.py "$HOST" "$PORT" -q 2>/dev/null; then
            echo "✓ PASS" | tee -a "$RESULTS_FILE"
            ((PASSED++))
        else
            echo "✗ FAIL" | tee -a "$RESULTS_FILE"
            ((FAILED++))
        fi
    fi
done < "$PROXY_LIST"

echo "" | tee -a "$RESULTS_FILE"
echo "============================================================" | tee -a "$RESULTS_FILE"
echo "Summary:" | tee -a "$RESULTS_FILE"
echo "  Total:  $TOTAL" | tee -a "$RESULTS_FILE"
echo "  Passed: $PASSED" | tee -a "$RESULTS_FILE"
echo "  Failed: $FAILED" | tee -a "$RESULTS_FILE"
echo "============================================================" | tee -a "$RESULTS_FILE"
echo "Completed: $(date)" | tee -a "$RESULTS_FILE"
echo "" | tee -a "$RESULTS_FILE"
echo "Results saved to: $RESULTS_FILE"

[ $FAILED -eq 0 ]
