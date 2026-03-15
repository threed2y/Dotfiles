<div align="center">

# ✦ threed2y / Dotfiles ✦

**A curated aesthetic setup for Arch Linux — Fastfetch · Sublime Text · Terminal themes · Custom wallpapers**

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightblue.svg?style=flat-square)](https://creativecommons.org/licenses/by/4.0/)
[![Arch Linux](https://img.shields.io/badge/Arch-Linux-1793D1?style=flat-square&logo=arch-linux&logoColor=white)](https://archlinux.org/)
[![COSMIC DE](https://img.shields.io/badge/COSMIC-Epoch%201-blueviolet?style=flat-square)](https://github.com/pop-os/cosmic-epoch)
[![Sublime Text](https://img.shields.io/badge/Sublime%20Text-config-orange?style=flat-square&logo=sublime-text&logoColor=white)](https://www.sublimetext.com/)

</div>

---

## 📸 Preview

> Screenshots are located in the [`Preview/`](./Preview) folder of this repository.

| Desktop | Terminal | Sublime Text |
|:---------:|:--------:|:------------:|
| ![Desktop preview](./Preview/1.png) | ![Terminal preview](./Preview/2.png) | ![Sublime preview](./Preview/3.png) |


---

## 📂 Repository Structure

```
Dotfiles/
├── Fastftech/          # Fastfetch configuration & presets
├── Preview/            # Screenshots of the setup
├── Sublime-Text/       # Sublime Text preferences & color schemes
├── Terminals/          # Terminal emulator configurations
├── Themes/             # GTK / icon / cursor themes
├── Wallpaper/          # Wallpaper collection
├── zshr/               # zshrc configuration
└── Packages.txt        # Full list of installed packages
```

---

## 🧰 What's Inside

| Component | Details |
|-----------|---------|
| **OS** | Arch Linux (rolling) |
| **DE** | COSMIC Epoch 1 |
| **Fastfetch** | Custom preset in `Fastftech/` |
| **Editor** | Sublime Text (config in `Sublime-Text/`) |
| **Terminals** | Custom themes in `Terminals/` |
| **Themes** | GTK / icon themes in `Themes/` |
| **Wallpaper** | Curated wallpapers in `Wallpaper/` |

---

## 🚀 Replicating This Setup on Arch Linux + COSMIC DE

Follow these steps **in order** to get an identical environment.

---

### Step 1 — Install Arch Linux

If you don't have Arch installed, use the guided installer:

```bash
archinstall
```

During setup, choose:
- **Profile**: Minimal (no DE yet — we'll add COSMIC manually)
- **Filesystem**: ext4 or btrfs
- **Bootloader**: systemd-boot or GRUB

---

### Step 2 — Post-install: Update & Install Base Tools

After first boot, log in and run:

```bash
sudo pacman -Syu
sudo pacman -S --needed base-devel git curl wget
```

---

### Step 3 — Install an AUR Helper (yay)

```bash
git clone https://aur.archlinux.org/yay-bin.git
cd yay-bin
makepkg -si
cd ..
rm -rf yay-bin
```

---

### Step 4 — Install COSMIC Desktop Environment

COSMIC is available in the official Arch `extra` repository as of Epoch 1.

**Option A — Full install (recommended for new users):**

```bash
sudo pacman -S cosmic
```

This installs the entire `cosmic` package group including the file manager, terminal, text editor, app store, and all applets.

**Option B — Minimal install:**

```bash
sudo pacman -S cosmic-session
```

Installs only the core session; you add individual components later.

---

### Step 5 — Enable the COSMIC Display Manager

```bash
sudo systemctl enable cosmic-greeter.service
```

> If you already have another display manager (GDM, SDDM, LightDM) enabled, disable it first:
> ```bash
> sudo systemctl disable gdm  # or sddm / lightdm
> ```

---

### Step 6 — Install Optional but Recommended Components

```bash
sudo pacman -S \
  power-profiles-daemon \
  gnome-keyring \
  packagekit \
  pipewire wireplumber \
  networkmanager
```

Enable them:

```bash
sudo systemctl enable NetworkManager
sudo systemctl enable power-profiles-daemon
```

---

### Step 7 — Reboot into COSMIC

```bash
reboot
```

At the login screen, select **COSMIC** from the session menu (bottom-right gear icon).

---

### Step 8 — Clone This Dotfiles Repository

```bash
git clone https://github.com/threed2y/Dotfiles.git ~/Dotfiles
cd ~/Dotfiles
```

---

### Step 9 — Install Fastfetch & Apply Config

```bash
sudo pacman -S fastfetch
```

Copy the custom preset:

```bash
mkdir -p ~/.config/fastfetch
cp -r ~/Dotfiles/Fastftech/* ~/.config/fastfetch/
```

Test it:

```bash
fastfetch
```

---

### Step 10 — Apply Terminal Themes

Copy the terminal configuration files:

```bash
cp -r ~/Dotfiles/Terminals/* ~/.config/
```

> Check inside `Terminals/` to see which terminal emulator is configured (e.g., COSMIC Terminal, Kitty, Alacritty) and install it accordingly.

For **COSMIC Terminal** (included with the `cosmic` group):

```bash
# Already installed — configuration lands at:
~/.config/cosmic/com.system76.CosmicTerm/
```

---

### Step 11 — Install Sublime Text & Apply Config

```bash
# Install from AUR
yay -S sublime-text-4
```

Copy the configuration:

```bash
mkdir -p ~/.config/sublime-text/Packages/User
cp -r ~/Dotfiles/Sublime-Text/* ~/.config/sublime-text/Packages/User/
```

---

### Step 12 — Apply GTK Themes & Icons

Copy themes to the correct locations:

```bash
mkdir -p ~/.themes ~/.icons ~/.local/share/icons

cp -r ~/Dotfiles/Themes/gtk/* ~/.themes/         # if present
cp -r ~/Dotfiles/Themes/icons/* ~/.icons/         # if present
```

Apply in COSMIC Settings → **Appearance**.

---

### Step 13 — Set Wallpaper

Copy wallpapers:

```bash
mkdir -p ~/Pictures/Wallpapers
cp ~/Dotfiles/Wallpaper/* ~/Pictures/Wallpapers/
```

Set in COSMIC Settings → **Wallpaper**, then browse to `~/Pictures/Wallpapers/`.

---

### Step 14 — Install Remaining Packages

Restore all packages from the list:

```bash
# Review the list first
cat ~/Dotfiles/Packages.txt

# Install with pacman (for official repo packages)
sudo pacman -S --needed $(cat ~/Dotfiles/Packages.txt)

# If some packages are AUR-only, use yay instead:
yay -S --needed $(cat ~/Dotfiles/Packages.txt)
```

---

### Step 15 — Final Reboot

```bash
reboot
```

Your setup should now match the screenshots in the `Preview/` folder.

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---------|-----|
| App Center not working | Install `packagekit`: `sudo pacman -S packagekit` |
| Battery % not showing | Install `power-profiles-daemon`: `sudo pacman -S power-profiles-daemon && sudo systemctl enable power-profiles-daemon` |
| No password/keyring | Install `gnome-keyring`: `sudo pacman -S gnome-keyring` |
| COSMIC doesn't appear at login | Make sure `cosmic-greeter.service` is enabled and no other DM conflicts |
| Fastfetch wrong config path | Check with `fastfetch --config-help`; default is `~/.config/fastfetch/config.jsonc` |

---

## 📜 License

<a rel="license" href="https://creativecommons.org/licenses/by/4.0/">
  <img alt="Creative Commons License" src="https://i.creativecommons.org/l/by/4.0/88x31.png" />
</a>

This work is licensed under a **[Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/)**.

You are free to:
- **Share** — copy and redistribute the material in any medium or format
- **Adapt** — remix, transform, and build upon the material for any purpose, even commercially

Under the following terms:
- **Attribution** — You must give appropriate credit to **threed2y**, provide a link to the license, and indicate if changes were made.

---

## 🙏 Acknowledgements

- [Arch Linux](https://archlinux.org/) — the base
- [System76 / COSMIC](https://github.com/pop-os/cosmic-epoch) — for the next-gen desktop
- [Fastfetch](https://github.com/fastfetch-cli/fastfetch) — the fetch tool
- [Sublime Text](https://www.sublimetext.com/) — the editor
- The r/unixporn & dotfiles community for endless inspiration

---

<div align="center">

*i use arch, btw.*

</div>
