#!/bin/sh
# Copy this overlay onto a live IPFire (or DESTDIR). Run as root on the firewall.
# Usage: ./scripts/install-overlay.sh [DESTDIR]
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
DEST=${1:-}

install_file() {
	mode=$1
	src=$2
	dst=$3
	mkdir -p "$(dirname "$DEST$dst")"
	install -m "$mode" "$ROOT/$src" "$DEST$dst"
}

install_file 644 etc/sqm/sqm.conf /etc/sqm/sqm.conf
install_file 644 etc/sqm/default.conf /etc/sqm/default.conf
install_file 754 etc/rc.d/init.d/sqm /etc/rc.d/init.d/sqm
install_file 754 etc/rc.d/init.d/networking/red.up/25-RS-sqm \
	/etc/rc.d/init.d/networking/red.up/25-RS-sqm
install_file 754 etc/rc.d/init.d/networking/red.down/25-RS-sqm \
	/etc/rc.d/init.d/networking/red.down/25-RS-sqm
mkdir -p "$DEST/usr/lib/sqm"
for f in "$ROOT"/usr/lib/sqm/*; do
	bn=$(basename "$f")
	case "$bn" in
		start-sqm|stop-sqm|update-available-qdiscs|sqmctrl.sh)
			install -m 755 "$f" "$DEST/usr/lib/sqm/$bn"
			;;
		*)
			install -m 644 "$f" "$DEST/usr/lib/sqm/$bn"
			;;
	esac
done

# qosctrl is -rwsr-x--- root:nobody; Linux ignores setuid on scripts, so
# /usr/local/bin/sqmctrl is a small binary that execs sqmctrl.sh as root.
install_file 755 usr/local/bin/sqmctrl /usr/local/bin/sqmctrl
if [ -z "$DEST" ] || [ "$DEST" = "/" ]; then
	chown root:nobody "$DEST/usr/local/bin/sqmctrl"
	chmod 4750 "$DEST/usr/local/bin/sqmctrl"
fi

mkdir -p "$DEST/var/ipfire/sqm"
if [ ! -f "$DEST/var/ipfire/sqm/settings" ]; then
	install -m 644 "$ROOT/var/ipfire/sqm/settings" "$DEST/var/ipfire/sqm/settings"
fi
# WUI CGIs run as nobody (uid 99); writehash dies on root:root 0644.
if [ -z "$DEST" ] || [ "$DEST" = "/" ]; then
	chown nobody:nobody "$DEST/var/ipfire/sqm" "$DEST/var/ipfire/sqm/settings" 2>/dev/null || \
		chown 99:99 "$DEST/var/ipfire/sqm" "$DEST/var/ipfire/sqm/settings"
	chmod 755 "$DEST/var/ipfire/sqm"
	chmod 644 "$DEST/var/ipfire/sqm/settings"
fi

install_file 755 html/cgi-bin/sqm.cgi /srv/web/ipfire/cgi-bin/sqm.cgi
install_file 644 langs/en/cgi-bin/sqm.en.pl /var/ipfire/addon-lang/sqm.en.pl
install_file 644 var/ipfire/menu.d/41-sqm.menu /var/ipfire/menu.d/41-sqm.menu

if [ -d "$DEST/etc/init.d" ] || [ -z "$DEST" ]; then
	ln -sfn ../rc.d/init.d/sqm "$DEST/etc/init.d/sqm" 2>/dev/null || true
fi

echo "Installed SQM overlay into ${DEST:-/}"
echo "WUI: https://<ipfire>:444/cgi-bin/sqm.cgi"
echo "CLI: sqmctrl status|start|stop"
