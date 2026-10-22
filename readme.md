<div align="center">

# ✦ Dotfiles ✦

**A wallpaper-driven Arch Linux desktop**
Niri · Waybar · Alacritty · tmux · Starship · Matugen · Everforest

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightblue.svg?style=flat-square)](https://creativecommons.org/licenses/by/4.0/)
[![Arch Linux](https://img.shields.io/badge/Arch-Linux-1793D1?style=flat-square&logo=arch-linux&logoColor=white)](https://archlinux.org/)

</div>

Change the wallpaper and the whole desktop follows. A minimal Wayland setup that stays fast and looks cohesive.

## 📸 Preview

| Desktop | Overview | Firefox |
| :---: | :---: | :---: |
| ![Desktop](./Preview/1.png) | ![Overview](./Preview/2.png) | ![Firefox](./Preview/3.png) |

## 🧰 What's inside

| | |
| --- | --- |
| **Compositor** | [Niri](https://github.com/YaLTeR/niri) (scrollable tiling) |
| **Bar / launcher / notifications** | Waybar · fuzzel · mako |
| **Terminal / multiplexer** | Alacritty + tmux (auto-started) |
| **Shell / prompt** | Zsh · Starship |
| **Editor** | Lite XL |
| **Colors** | [Matugen](https://github.com/InioX/matugen) from the wallpaper, Everforest as base |
| **Wallpaper** | [awww](https://codeberg.org/LGFae/awww) |

Extras (optional): Kitty, Ghostty, Foot, Sublime Text, Fastfetch.

## 🚀 Install

You need Arch Linux, `git`, and an AUR helper such as `yay`.

**1. Clone**

```bash
git clone https://github.com/threed2y/Dotfiles.git ~/Dotfiles
cd ~/Dotfiles
```

**2. Install packages**

```bash
yay -S --needed - < Packages.txt
```

Or just the essentials:

```bash
yay -S --needed niri waybar alacritty fuzzel mako swaylock wlogout \
  awww matugen cliphist wl-clipboard tmux starship fzf zsh \
  lite-xl firefox nautilus ttf-jetbrains-mono-nerd
```

**3. Copy the configs**

Folder names in the repo are capitalized, so each one is renamed on copy.

```bash
mkdir -p ~/.config/{mako,matugen,alacritty,tmux}

cp -r Niri      ~/.config/niri
cp -r Waybar    ~/.config/waybar
cp -r fuzzel    ~/.config/fuzzel
cp -r Swaylock  ~/.config/swaylock
cp -r Wlogout   ~/.config/wlogout
cp mako/config  ~/.config/mako/config
cp -r Matugen/config.toml Matugen/templates ~/.config/matugen/

cp Terminals/Alacritty/*.toml ~/.config/alacritty/
cp Terminals/tmux/tmux.conf   ~/.config/tmux/tmux.conf
cp Terminals/starship/starship.toml ~/.config/starship.toml
```

> In `alacritty.toml`, change `/home/ethan` in the `import` line to your own home directory.

**4. Zsh (optional)**

Install [Oh My Zsh](https://ohmyz.sh/) and the `fzf-tab`, `zsh-autosuggestions` and `zsh-syntax-highlighting` plugins, then:

```bash
cp ~/.zshrc ~/.zshrc.bak
cp zshr/zsh ~/.zshrc
```

> Remove the line that sources `~/Downloads/VENV/LA-311/bin/activate`. It points to a personal virtualenv.

**5. Wallpapers and start**

```bash
mkdir -p ~/Pictures/Wallpapers
cp Wallpaper/* ~/Pictures/Wallpapers/
niri-session
```

Waybar, mako and the other helpers start automatically from `spawn-at-startup` in `Niri/config.kdl`.

## ⌨️ Keybindings

`Mod` is the Super key.

| Keys | Action |
| --- | --- |
| `Mod` + `Return` | Terminal |
| `Alt` + `Space` | App launcher |
| `Mod` + `B` | Browser |
| `Mod` + `F` | File manager |
| `Mod` + `V` | Clipboard history |
| `Mod` + `Alt` + `L` | Lock screen |
| `Mod` + `Alt` + `Space` | Power menu |
| `Mod` + `Shift` + `/` | Show all Niri binds |

New to tmux? See the [tmux cheat sheet](./docs/tmux.md).

## 🎨 Change the theme

```bash
awww-daemon &                                  # once per session
awww img ~/Pictures/Wallpapers/<image>.jpg     # set wallpaper
matugen image ~/Pictures/Wallpapers/<image>.jpg  # regenerate colors
```

Alacritty and tmux reload on their own. Reload Waybar and mako to pick up new colors.

## 🛠️ Troubleshooting

| Problem | Fix |
| --- | --- |
| Black screen or Niri won't start | Start with `niri-session`, not `niri`. Check the config with `niri validate` |
| `Mod + V` shows nothing | Make sure `wl-paste --watch cliphist store` is in `spawn-at-startup` |
| Wallpaper won't change | Start `awww-daemon` first |
| Broken icons or glyphs | Install a Nerd Font, e.g. `ttf-jetbrains-mono-nerd` |
| Alacritty opens without tmux | Check that `which tmux` matches the path in `alacritty.toml` |
| Can't copy in tmux | Drag to select, then `Ctrl+Shift+C` / `Ctrl+Shift+V` |

## 📜 License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Share and adapt with credit to **threed2y**.

<div align="center">

*i use arch, btw.*

</div>
