#!/usr/bin/env bash
# Bootstrap the repo-local CAD toolchain (build123d, code-CAD) with no sudo.
#
#   scripts/cad-setup.sh
#
# Creates .venv/ (Python 3.11-3.14), installs cad/requirements.txt, and stages the
# couple of system GL/X libraries the OpenCASCADE kernel links against but that a
# headless box often lacks. It is idempotent - safe to re-run.
#
# Why a local venv: nothing here needs root, and .venv/ is gitignored, so the repo
# stays source-only while any agent on any host can reproduce the exact toolchain.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"
VENV="$REPO/.venv"
GLLIB="$VENV/gl-libs"

say() { printf 'cad-setup: %s\n' "$*"; }

# --- uv (fast, no-sudo Python/venv manager) --------------------------------
if ! command -v uv >/dev/null 2>&1; then
    export PATH="$HOME/.local/bin:$PATH"
fi
if ! command -v uv >/dev/null 2>&1; then
    say "installing uv to ~/.local/bin"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# --- virtualenv + Python packages -------------------------------------------
if [ ! -x "$VENV/bin/python" ]; then
    say "creating virtualenv at .venv"
    uv venv --python 3.13 "$VENV"
fi
say "installing cad/requirements.txt"
uv pip install --python "$VENV/bin/python" -r "$REPO/cad/requirements.txt"

# --- headless GL/X runtime for OpenCASCADE ----------------------------------
# OCP (the OCCT binding behind build123d) links libGL.so.1, which pulls libGLX ->
# libX11. A headless CI box has none of them. Download the Debian/Ubuntu packages
# and unpack them locally - no root, no system change.
if [ ! -e "$GLLIB/usr/lib/x86_64-linux-gnu/libGL.so.1" ]; then
    say "staging headless GL/X libraries into .venv/gl-libs"
    tmp="$(mktemp -d)"
    ( cd "$tmp"
      for pkg in libgl1 libglvnd0 libglx0 libx11-6 libxcb1 libxau6 libxdmcp6 libbsd0; do
          apt-get download "$pkg" >/dev/null 2>&1 || say "warn: could not fetch $pkg"
      done )
    for deb in "$tmp"/*.deb; do [ -e "$deb" ] && dpkg-deb -x "$deb" "$GLLIB"; done
    rm -rf "$tmp"
else
    say "GL/X libraries already staged"
fi

"$VENV/bin/python" - <<'PY'
import build123d  # noqa: F401
print("cad-setup: build123d", build123d.__version__, "imports OK (via scripts/cad-run.sh)")
PY
say "done - run 'scripts/cad-run.sh --help'"
