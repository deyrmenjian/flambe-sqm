#!/bin/bash
. /opt/pakfire/lib/functions.sh

if [ -x /usr/local/bin/sqmctrl ]; then
	/usr/local/bin/sqmctrl stop >/dev/null 2>&1 || true
fi

make_backup ${NAME}
remove_files

rm -f /etc/init.d/sqm
rm -f /etc/sqm/*.iface.conf
rm -rf /run/sqm
