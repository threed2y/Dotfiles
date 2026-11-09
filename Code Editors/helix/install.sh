#!/bin/sh
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cfg="$HOME/.config/helix"
mkdir -p "$cfg/themes" "$HOME/.config/matugen/templates" "$HOME/.local/share/applications"

if command -v xbps-install >/dev/null 2>&1; then
  sudo xbps-install -y helix ruff ripgrep wl-clipboard xdg-utils desktop-file-utils
fi
if command -v uv >/dev/null 2>&1; then
  uv tool install ty
else
  echo "uv not found: install it, then run: uv tool install ty"
fi

link() {
  if [ -e "$2" ] && [ ! -L "$2" ]; then mv "$2" "$2.bak"; fi
  ln -sfn "$1" "$2"
}
link "$here/config/config.toml"    "$cfg/config.toml"
link "$here/config/languages.toml" "$cfg/languages.toml"
link "$here/matugen/helix.toml"    "$HOME/.config/matugen/templates/helix.toml"

cp "$here/applications/helix-alacritty.desktop" "$HOME/.local/share/applications/"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
for m in text/plain text/markdown text/x-python text/x-shellscript text/csv \
         text/x-log application/json application/x-yaml application/toml \
         application/xml application/x-shellscript; do
  xdg-mime default helix-alacritty.desktop "$m"
done

mcfg="$HOME/.config/matugen/config.toml"
if ! grep -q 'templates.helix' "$mcfg" 2>/dev/null; then
  cat >> "$mcfg" <<'TOML'

[templates.helix]
input_path  = "~/.config/matugen/templates/helix.toml"
output_path = "~/.config/helix/themes/matugen.toml"
TOML
fi

echo "done. generate the theme with: setwall \"\$(cat ~/.cache/current-wall)\""
echo "then check: hx --health python"
INSTALL
chmod +x install.sh
