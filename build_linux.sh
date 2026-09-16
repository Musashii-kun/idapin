#!/usr/bin/env bash
# Build Linux tools and copy the finished libraries beside this script.
set -euo pipefail

usage() {
    echo "Usage: PIN_ROOT=/path/to/linux-pin-kit $0 [all|ia32|intel64]" >&2
    echo "Set DEBUG=1 for unoptimized builds; defaults to optimized builds with symbols." >&2
}

if (( $# > 1 )); then
    usage
    exit 2
fi
case "${1:-all}" in
    all) targets=(ia32 intel64) ;;
    ia32|intel64) targets=("$1") ;;
    *) usage; exit 2 ;;
esac
if [[ -z "${PIN_ROOT:-}" || ! -f "$PIN_ROOT/source/tools/Config/makefile.config" ]]; then
    echo "Set PIN_ROOT to an extracted Linux PIN kit." >&2
    usage
    exit 2
fi
# Resolve relative kit paths before changing to the source directory.
PIN_ROOT=$(cd -- "$PIN_ROOT" && pwd -P)
export PIN_ROOT
case "${DEBUG:-0}" in
    0) config=release ;;
    1) config=debug ;;
    *) echo "DEBUG must be 0 or 1." >&2; exit 2 ;;
esac
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
cd -- "$script_dir"

# Complete all requested builds before replacing previously copied libraries.
for target in "${targets[@]}"; do
    "${MAKE:-make}" PIN_ROOT="$PIN_ROOT" TARGET="$target" DEBUG="${DEBUG:-0}" \
        OBJDIR="obj-$target-$config/" tools
done
for target in "${targets[@]}"; do
    library=idadbg.so
    [[ "$target" != intel64 ]] || library=idadbg64.so
    cp -- "obj-$target-$config/$library" "$library"
    echo "Built $library ($target, $config)"
done
