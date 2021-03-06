#!/bin/bash
dir="$(dirname "$0")"

source testnet.sh

source ../../_virtualenv/bin/activate

# Allows keepers to bid different prices
MODEL=$1
# Outputs keeper logs to separate files
ID=$2

../../bin/auction-keeper \
    --rpc-host ${ETH_RPC_URL:?} \
    --rpc-timeout 30 \
    --eth-from ${ACCOUNT_ADDRESS?:} \
    --eth-key ${ACCOUNT_KEY?:} \
    --type surplus \
    --safe-engine-system-coin-target 300 \
    --keep-system-coin-in-safe-engine-on-exit \
    --model ${dir}/${MODEL} \
    2> >(tee -a ${LOGS_DIR?:}/auction-keeper-${ID}.log >&2)
