#!/bin/bash
. /opt/pakfire/lib/functions.sh

extract_files
restore_backup ${NAME}

mkdir -p /etc/sqm /run/sqm /var/ipfire/sqm /var/ipfire/addon-lang
chown nobody:nobody /var/ipfire/sqm /var/ipfire/sqm/settings 2>/dev/null || \
	chown 99:99 /var/ipfire/sqm /var/ipfire/sqm/settings
chmod 755 /var/ipfire/sqm
chmod 644 /var/ipfire/sqm/settings

chown root:nobody /usr/local/bin/sqmctrl
chmod 4750 /usr/local/bin/sqmctrl
chmod 755 /usr/lib/sqm/sqmctrl.sh /usr/lib/sqm/start-sqm /usr/lib/sqm/stop-sqm \
	/usr/lib/sqm/update-available-qdiscs /etc/rc.d/init.d/sqm \
	/etc/rc.d/init.d/networking/red.up/25-RS-sqm \
	/etc/rc.d/init.d/networking/red.down/25-RS-sqm \
	/srv/web/ipfire/cgi-bin/sqm.cgi 2>/dev/null || true

if [ ! -e /etc/init.d/sqm ] && [ -e /etc/rc.d/init.d/sqm ]; then
	ln -sfn ../rc.d/init.d/sqm /etc/init.d/sqm
fi

if [ -x /usr/local/bin/update-lang-cache ]; then
	/usr/local/bin/update-lang-cache >/dev/null 2>&1 || true
fi

# Do not autostart until the administrator enables SQM in the WUI.
