#!/usr/bin/env bash
# Downloads the public raw sources of ScamGuard-IN-2026 into raw/ (not committed).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p raw
curl -fsSL -o raw/imc25_smishing.csv https://raw.githubusercontent.com/reportsmishing/Smishing-Dataset-IMC25/main/dataset/final_dataset_output.csv
curl -fsSL -o raw/india_spam_sms.csv https://raw.githubusercontent.com/junioralive/india-spam-sms-classification/main/dataset/spam_ham_india.csv
echo "Sources saved in raw/. Put team SMS exports (XML or TXT) in raw/team/ - they are never committed."
