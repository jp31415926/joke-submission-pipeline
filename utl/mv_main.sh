#!/usr/bin/env bash

set -euo pipefail

# ---- Stage → Directory map ----
declare -A STAGE_MAP=(
  [parse]="01_parse"
  [dedup]="02_dedup"
  [clean_check]="03_clean_check"
  [format]="04_format"
  [categorize]="05_categorize"
  [title]="06_title"
  [ready_for_review]="08_ready_for_review"
  [rejected_parse]="50_rejected_parse"
  [rejected_dedup]="51_rejected_dedup"
  [rejected_clean_check]="52_rejected_clean_check"
  [rejected_format]="53_rejected_format"
  [rejected_categorize]="54_rejected_categorize"
  [rejected_title]="55_rejected_title"
)

usage() {
  echo "Usage: $0 <src-stage> <dst-stage> <item-id>" >&2
  echo >&2
  echo "Valid stages:" >&2
  for stage in "${!STAGE_MAP[@]}"; do
    echo "  - $stage" >&2
  done
  exit 1
}

# ---- Validate args ----
[[ $# -eq 3 ]] || usage

src_stage="$1"
dst_stage="$2"
item_id="$3"

# ---- Validate stages ----
[[ -n "${STAGE_MAP[$src_stage]:-}" ]] || {
  echo "Error: Invalid source stage '$src_stage'" >&2
  exit 1
}

[[ -n "${STAGE_MAP[$dst_stage]:-}" ]] || {
  echo "Error: Invalid destination stage '$dst_stage'" >&2
  exit 1
}

src_dir="pipeline-main/${STAGE_MAP[$src_stage]}"
dst_dir="pipeline-main/${STAGE_MAP[$dst_stage]}"

# ---- Normalize filename ----
filename="$(basename -- "$item_id")"

if [[ "$filename" != *.txt ]]; then
  filename="${filename}.txt"
fi

src_path="${src_dir}/${filename}"
dst_path="${dst_dir}/${filename}"

# ---- Validate directories ----
if [[ ! -d "$src_dir" ]]; then
  echo "Error: Source directory does not exist: $src_dir" >&2
  exit 1
fi

if [[ ! -d "$dst_dir" ]]; then
  echo "Error: Destination directory does not exist: $dst_dir" >&2
  exit 1
fi

# ---- Validate files ----
if [[ ! -f "$src_path" ]]; then
  echo "Error: Source file does not exist: $src_path" >&2
  exit 1
fi

if [[ -e "$dst_path" ]]; then
  echo "Error: Destination file already exists: $dst_path" >&2
  exit 1
fi

# ---- Move file ----
mv -- "$src_path" "$dst_path"

echo "Moved: $src_path → $dst_path"