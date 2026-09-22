#!/usr/bin/env bash
# Collier's Vibe Editing — set up a new Mac in one command.
#   No Homebrew and no admin password needed: everything installs into your home folder
#   (~/.local/bin and ~/.local/share/vibe-tools). Safe to re-run; it skips what's already there.
#
#   Run it from the repo folder:   ./setup-mac.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
PLUG="$DIR/plugins/vibe-editing"
BIN="$HOME/.local/bin"
SHARE="$HOME/.local/share/vibe-tools"
mkdir -p "$BIN" "$SHARE"
export PATH="$BIN:$PATH"
say() { printf '\n== %s\n' "$*"; }

say "PATH"
if ! grep -qs 'HOME/.local/bin' "$HOME/.zshrc"; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"; echo "added ~/.local/bin to ~/.zshrc"
else echo "ok"; fi

say "uv (Python manager)"
if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$BIN" INSTALLER_NO_MODIFY_PATH=1 sh
fi
uv --version

say "ffmpeg + ffprobe (with libass for captions)"
if ! ffmpeg -hide_banner -filters 2>/dev/null | grep -q ' subtitles '; then
  for t in ffmpeg ffprobe; do
    curl -fsSL -o "/tmp/$t.zip" "https://evermeet.cx/ffmpeg/getrelease/$t/zip"
    unzip -o -q "/tmp/$t.zip" -d "$BIN"; chmod +x "$BIN/$t"
    xattr -d com.apple.quarantine "$BIN/$t" 2>/dev/null || true
  done
fi
# evermeet builds are Intel; Apple-silicon Macs run them through Rosetta.
if [ "$(uname -m)" = "arm64" ] && ! arch -x86_64 /usr/bin/true 2>/dev/null; then
  echo "Installing Rosetta (lets the Intel ffmpeg run on Apple silicon)..."
  softwareupdate --install-rosetta --agree-to-license || {
    echo "!! Rosetta install needs approval. Open Terminal, run:  softwareupdate --install-rosetta --agree-to-license"; }
fi
ffmpeg -hide_banner -version | head -1

say "tesseract (caption OCR check) + poppler (PDF reading)"
MM="$SHARE/mamba/bin/micromamba"
if [ ! -x "$MM" ]; then
  mkdir -p "$SHARE/mamba"
  arch_tag=$([ "$(uname -m)" = "arm64" ] && echo osx-arm64 || echo osx-64)
  curl -fsSL "https://micro.mamba.pm/api/micromamba/$arch_tag/latest" | tar -xj -C "$SHARE/mamba" bin/micromamba
fi
export MAMBA_ROOT_PREFIX="$SHARE/mamba"
[ -x "$SHARE/ocr/bin/tesseract" ]     || "$MM" create -y -q -p "$SHARE/ocr" -c conda-forge tesseract
[ -x "$SHARE/poppler/bin/pdftotext" ] || "$MM" create -y -q -p "$SHARE/poppler" -c conda-forge poppler
cat > "$BIN/tesseract" <<EOF
#!/bin/sh
# Vibe Editing — tesseract OCR (installed for the caption audit gate)
export TESSDATA_PREFIX="$SHARE/ocr/share/tessdata"
exec "$SHARE/ocr/bin/tesseract" "\$@"
EOF
chmod +x "$BIN/tesseract"
ln -sf "$SHARE/poppler/bin/pdftotext" "$BIN/pdftotext"; ln -sf "$SHARE/poppler/bin/pdftoppm" "$BIN/pdftoppm"
tesseract --version 2>&1 | head -1

say "Python 3.12 environment + packages (pinned to the versions used on the original Mac)"
uv python install 3.12
[ -x "$PLUG/.venv/bin/python" ] || uv venv --python 3.12 "$PLUG/.venv"
uv pip install --python "$PLUG/.venv/bin/python" -q -r "$PLUG/requirements.lock.txt" \
  || uv pip install --python "$PLUG/.venv/bin/python" -q -r "$PLUG/requirements.txt" fonttools
ln -sf "$PLUG/.venv/bin/yt-dlp" "$BIN/yt-dlp"

say "API keys"
if [ ! -f "$PLUG/config/keys.env" ]; then
  cp "$PLUG/config/keys.env.example" "$PLUG/config/keys.env"
  echo "Created plugins/vibe-editing/config/keys.env — paste your Groq key into it (console.groq.com → API Keys)."
else echo "keys.env already present (not overwritten)"; fi
grep -q '^GROQ_API_KEY=.\+' "$PLUG/config/keys.env" && echo "Groq key: set" || echo "Groq key: EMPTY — transcription will use slower local whisper until you add one"

say "Folders"
mkdir -p "$DIR/00_INBOX" "$DIR/projects"

say "Health check"
"$PLUG/.venv/bin/python" "$PLUG/doctor.py" || true

cat <<'EOF'

Done. Last step, inside Claude Code (the Claude desktop app → Code, opened on this folder):
    /plugin marketplace add <this folder's full path>
    /plugin install vibe-editing@vibe-editing-marketplace
Then drop a video in 00_INBOX and ask Claude to clip it.
EOF
