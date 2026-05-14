#!/bin/bash
jq -r '[
  (.model.display_name // "unknown"),
  (.effort.level // "medium"),
  ((.context_window.total_input_tokens // 0 | tostring)
    + "/"
    + (.context_window.context_window_size // 200000 | tostring)
    + " ("
    + (.context_window.used_percentage // 0 | tostring)
    + "%)")
] | join(" | ")'
