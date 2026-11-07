CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/waybar-mpris"
mkdir -p "$CACHE"

player=""
for p in $(playerctl -l 2>/dev/null); do
    [ -z "$player" ] && player="$p"
    if [ "$(playerctl -p "$p" status 2>/dev/null)" = "Playing" ]; then
        player="$p"
        break
    fi
done
[ -z "$player" ] && exit 0

url="$(playerctl -p "$player" metadata mpris:artUrl 2>/dev/null)"
[ -z "$url" ] && exit 0

case "$url" in
    file://*)
        f="${url#file://}"
        f="$(printf '%b' "$(printf '%s' "$f" | sed 's/%\(..\)/\\x\1/g')")"
        [ -f "$f" ] && printf '%s\n' "$f"
        ;;
    http://*|https://*)
        f="$CACHE/$(printf '%s' "$url" | sha1sum | cut -d' ' -f1)"
        if [ ! -s "$f" ]; then
            if curl -sfL --max-time 5 -o "$f.tmp" "$url"; then
                mv "$f.tmp" "$f"
            else
                rm -f "$f.tmp"
            fi
            find "$CACHE" -type f -mmin +1440 -delete 2>/dev/null
        fi
        [ -s "$f" ] && printf '%s\n' "$f"
        ;;
esac
exit 0
