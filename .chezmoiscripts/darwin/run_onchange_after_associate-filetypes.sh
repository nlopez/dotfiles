#!/bin/bash

set -eufo pipefail

# Associate common text/code filetypes with Zed
for uti in text plain-text source-code shell-script script; do
  duti -s dev.zed.Zed "public.${uti}" all
done
