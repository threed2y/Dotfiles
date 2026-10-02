# Lite XL — Plugin Installation & Setup

## 1. Create the Lite XL directories

```bash
mkdir -p ~/.config/lite-xl/plugins
mkdir -p ~/.config/lite-xl/libraries
cd ~/.config/lite-xl
```

---

# 2. Install the main plugins

## LSP

```bash
git clone https://github.com/lite-xl/lite-xl-lsp ~/.config/lite-xl/plugins/lsp
```

## Widgets

LSP requires the widgets library:

```bash
git clone https://github.com/lite-xl/lite-xl-widgets ~/.config/lite-xl/libraries/widget
```

## LintPlus

```bash
git clone https://github.com/liquidev/lintplus ~/.config/lite-xl/plugins/lintplus
```

## Snippets

```bash
git clone https://github.com/lite-xl/lite-xl-snippets ~/.config/lite-xl/plugins/snippets
```

## LSP Snippets

```bash
git clone https://github.com/lite-xl/lite-xl-lsp-snippets ~/.config/lite-xl/plugins/lsp_snippets
```

---

# 3. Other plugins

Install the remaining plugins through Lite XL's plugin manager:

```text
Ctrl + Shift + P
```

Then search for:

```text
devicons
formatter
gitdiff_highlight
gitstatus
indentguide
minimap
open_ext
search_ui
selectionhighlight
settings
sticky_scroll
terminal
```

Install each plugin.

---

# 4. Language plugins

Your installation contains a very large collection of `language_*.lua` files.

These provide syntax highlighting and language support.

Examples from your installation:

```text
language_cmake.lua
language_csharp.lua
language_dart.lua
language_go.lua
language_java.lua
language_json.lua
language_jsx.lua
language_julia.lua
language_kotlin.lua
language_lua.lua
language_php.lua
language_py.lua
language_r.lua
language_rust.lua
language_sh.lua
language_ts.lua
language_tsx.lua
language_typst.lua
language_yaml.lua
language_zig.lua
```

You do **not** need to manually install every language plugin if they are already included in your Lite XL installation.

---

# 5. Install external language servers

The Lite XL `lsp` plugin communicates with external language servers.

### Python

```bash
sudo pacman -S pyright
```

### Ruff

```bash
sudo pacman -S python-ruff
```

### Rust

```bash
sudo pacman -S rust-analyzer
```

### C / C++

```bash
sudo pacman -S clang
```

This provides `clangd`.

### TypeScript / JavaScript

```bash
sudo pacman -S typescript-language-server
```

### Lua

```bash
sudo pacman -S lua-language-server
```

### YAML

```bash
sudo pacman -S yaml-language-server
```

---

# 6. Your LSP servers

The setup we configured was:

```text
Python       → pyright
Python lint  → ruff
Rust         → rust-analyzer
C/C++        → clangd
JavaScript   → typescript-language-server
TypeScript   → typescript-language-server
Lua          → lua-language-server
YAML         → yaml-language-server
```

R language-server support was checked but:

```text
r-languageserver
```

was not available through the package setup we were using.

---

# 7. Lite XL configuration

Your configuration is:

```text
~/.config/lite-xl/init.lua
```

The LSP JSON setting we used was:

```lua
config.plugins.lsp.prettify_json = true
```

The relevant configuration section should therefore contain:

```lua
local config = require "core.config"

config.plugins.lsp.prettify_json = true
```

---

# 8. Verify plugins

Run:

```bash
find ~/.config/lite-xl/plugins \
    -maxdepth 1 \
    -mindepth 1 \
    -printf '%f\n' | sort
```

You should see plugins such as:

```text
devicons.lua
formatter
gitdiff_highlight
gitstatus.lua
indentguide.lua
lintplus
lsp
lsp_snippets.lua
minimap.lua
open_ext.lua
search_ui.lua
selectionhighlight.lua
settings.lua
snippets.lua
sticky_scroll.lua
terminal
```

---

# 9. Verify language servers

Run:

```bash
which pyright
which ruff
which rust-analyzer
which clangd
which typescript-language-server
which lua-language-server
which yaml-language-server
```

Or:

```bash
command -v pyright
command -v ruff
command -v rust-analyzer
command -v clangd
command -v typescript-language-server
command -v lua-language-server
command -v yaml-language-server
```

---

# 10. Verify Lite XL configuration

```bash
ls ~/.config/lite-xl/
```

You should have:

```text
init.lua
plugins/
libraries/
```

---

# 11. Restart Lite XL

After installing or changing plugins:

```bash
pkill lite-xl
lite-xl
```

Or simply close and reopen Lite XL.

---

# 12. Complete plugin list from the current installation

These are the non-language plugins confirmed by your `find` output:

```text
devicons.lua
formatter
gitdiff_highlight
gitstatus.lua
indentguide.lua
lintplus
lsp
lsp_snippets.lua
minimap.lua
open_ext.lua
search_ui.lua
selectionhighlight.lua
settings.lua
snippets.lua
sticky_scroll.lua
terminal
```

Your installation additionally contains numerous:

```text
language_*.lua
```

files covering programming, scripting, configuration, markup, and other languages.

---

# Quick reinstall

For a fresh machine, the basic setup is:

```bash
sudo pacman -S lite-xl git pyright python-ruff rust-analyzer clang \
    typescript-language-server lua-language-server yaml-language-server

mkdir -p ~/.config/lite-xl/{plugins,libraries}

git clone https://github.com/lite-xl/lite-xl-lsp \
    ~/.config/lite-xl/plugins/lsp

git clone https://github.com/lite-xl/lite-xl-widgets \
    ~/.config/lite-xl/libraries/widget

git clone https://github.com/liquidev/lintplus \
    ~/.config/lite-xl/plugins/lintplus

git clone https://github.com/lite-xl/lite-xl-snippets \
    ~/.config/lite-xl/plugins/snippets
```

Then install the remaining plugins through Lite XL's plugin manager:

```text
devicons
formatter
gitdiff_highlight
gitstatus
indentguide
minimap
open_ext
search_ui
selectionhighlight
settings
sticky_scroll
terminal
```

Finally configure:

```lua
config.plugins.lsp.prettify_json = true
```

and restart Lite XL.

