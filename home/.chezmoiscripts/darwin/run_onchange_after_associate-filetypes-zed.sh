#!/bin/bash

set -eufo pipefail

# Associate common text/code filetypes with Zed
for ext in txt json yaml sh xml sql go py js zsh rb; do
  duti -s dev.zed.Zed ."$ext" all
done
