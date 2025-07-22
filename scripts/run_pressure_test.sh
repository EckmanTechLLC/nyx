#!/bin/bash

# NYX Pressure Test Runner
# Usage: ./scripts/run_pressure_test.sh [duration_minutes]

set -e

DURATION=${1:-3}  # Default 3 minutes if not specified

echo "🚀 Starting NYX Autonomous Pressure Test"
echo "Duration: ${DURATION} minutes"
echo "======================================"

# Run the pressure test in Docker
docker-compose run --rm nyx python tests/scripts/test_nyx_pressure_demo.py --duration ${DURATION} --verbose

echo ""
echo "✅ Pressure test completed!"
echo "Check the logs above to see NYX's autonomous operation in action."