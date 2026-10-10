#!/bin/sh
# Control SQM on IPFire (analogous to qosctrl).
#
# Usage: sqmctrl start|stop|restart|status|generate
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2.

set -u

# CGI PATH often lacks /sbin; tc/ip live there on IPFire.
PATH=/usr/sbin:/sbin:/usr/bin:/bin
export PATH

. /etc/sqm/sqm.conf
. /usr/lib/sqm/ipfire.sh

ACTION="${1:-}"

usage() {
	echo "Usage: $0 start|stop|restart|status|generate" >&2
	exit 1
}

[ "$(id -u)" -eq 0 ] || {
	echo "This script must be run as root." >&2
	exit 1
}

mkdir -p /etc/sqm "$SQM_STATE_DIR" /var/ipfire/sqm

sqm_prepare

run_with_iface_env() {
	iface="$1"
	shift
	# Isolate start-sqm/stop-sqm; those scripts call exit.
	(
		if [ -f "${SQM_STATE_DIR}/${iface}.state" ]; then
			# shellcheck disable=SC1090
			. "${SQM_STATE_DIR}/${iface}.state"
		fi
		if [ -f "/etc/sqm/${iface}.iface.conf" ]; then
			# shellcheck disable=SC1090
			. "/etc/sqm/${iface}.iface.conf"
		fi
		IFACE="$iface"
		export IFACE SCRIPT UPLINK DOWNLINK QDISC ENABLED LINKLAYER OVERHEAD \
			STAB_MPU ZERO_DSCP_INGRESS IGNORE_DSCP_INGRESS IQDISC_OPTS EQDISC_OPTS \
			SQM_DEBUG CLEANUP
		"$@"
	)
}

stop_iface() {
	iface="$1"
	if [ -f "${SQM_STATE_DIR}/${iface}.state" ] || [ -f "/etc/sqm/${iface}.iface.conf" ]; then
		run_with_iface_env "$iface" "${SQM_LIB_DIR}/stop-sqm" || true
	fi
	# Best-effort teardown if state was lost or stop-sqm failed.
	tc qdisc del dev "$iface" root >/dev/null 2>&1 || true
	tc qdisc del dev "$iface" ingress >/dev/null 2>&1 || true
	ifb=$(echo "ifb4${iface}" | cut -c1-15)
	ip link del "$ifb" >/dev/null 2>&1 || true
	rm -f "${SQM_STATE_DIR}/${iface}.state"
	sqm_restore_aqm "$iface"
}

stop_all() {
	stopped=0
	if [ -d "$SQM_STATE_DIR" ]; then
		for f in "$SQM_STATE_DIR"/*.state; do
			[ -f "$f" ] || continue
			iface=$(basename "$f" .state)
			stop_iface "$iface"
			stopped=1
		done
	fi
	# Also stop the configured/RED iface if no state files exist.
	if [ "$stopped" -eq 0 ]; then
		iface=$(sqm_resolve_iface 2>/dev/null || true)
		[ -n "${iface:-}" ] && stop_iface "$iface"
	fi
	return 0
}

generate() {
	iface=$(sqm_resolve_iface) || return 1
	sqm_write_iface_conf "$iface" >/dev/null
	sqm_ipfire_log "Wrote /etc/sqm/${iface}.iface.conf"
}

start_sqm() {
	if sqm_qos_enabled; then
		sqm_ipfire_log "Refusing to start: IPFire QoS is enabled. Stop Quality of Service first."
		return 1
	fi

	if [ "$ENABLED" != "on" ]; then
		sqm_ipfire_log "SQM is disabled in /var/ipfire/sqm/settings"
		return 0
	fi

	iface=$(sqm_resolve_iface) || return 1

	if [ "$iface" = "imq0" ] || echo "$iface" | grep -q '^imq'; then
		sqm_ipfire_log "Refusing to attach SQM to IMQ ($iface)"
		return 1
	fi

	if ! sqm_red_is_up "$iface"; then
		if [ ! -d "/sys/class/net/${iface}" ]; then
			sqm_ipfire_log "Interface $iface is not present; waiting for RED-up"
			return 0
		fi
		sqm_ipfire_log "Interface $iface exists but RED is not marked active; starting anyway"
	fi

	sqm_load_modules
	sqm_write_iface_conf "$iface" >/dev/null

	# Replace any leftover root qdisc (fq_codel from network-aqm).
	if [ -f "${SQM_STATE_DIR}/${iface}.state" ]; then
		stop_iface "$iface"
		sqm_prepare
		sqm_write_iface_conf "$iface" >/dev/null
	fi

	if ! run_with_iface_env "$iface" "${SQM_LIB_DIR}/start-sqm"; then
		sqm_ipfire_log "start-sqm failed on $iface"
		return 1
	fi
	if [ ! -f "${SQM_STATE_DIR}/${iface}.state" ]; then
		sqm_ipfire_log "start-sqm did not create a state file for $iface"
		return 1
	fi
}

status_sqm() {
	iface=$(sqm_resolve_iface 2>/dev/null || true)
	echo "SQM settings: $SQM_SETTINGS"
	echo "ENABLED=${ENABLED:-off} SCRIPT=${SCRIPT:-} QDISC=${QDISC:-}"
	echo "DOWNLOAD=${DOWNLOAD:-} kbit  UPLOAD=${UPLOAD:-} kbit"
	if sqm_qos_enabled; then
		echo "WARNING: IPFire QoS is enabled (mutually exclusive with SQM)"
	fi
	if [ -z "${iface:-}" ]; then
		echo "No interface resolved (is RED up?)"
		return 0
	fi
	echo "Interface: $iface"
	ifb=$(echo "ifb4${iface}" | cut -c1-15)
	echo
	echo "=== tc qdisc $iface ==="
	tc -s qdisc show dev "$iface" 2>/dev/null || echo "(none)"
	echo
	echo "=== tc qdisc $ifb ==="
	if [ -d "/sys/class/net/${ifb}" ]; then
		tc -s qdisc show dev "$ifb" 2>/dev/null || echo "(none)"
	else
		echo "(IFB $ifb not present)"
	fi
	echo
	if [ -f "${SQM_STATE_DIR}/${iface}.state" ]; then
		echo "State: running (${SQM_STATE_DIR}/${iface}.state)"
	else
		echo "State: not running"
	fi
}

case "$ACTION" in
	start)
		start_sqm
		;;
	stop)
		stop_all
		;;
	restart)
		stop_all
		sqm_prepare
		start_sqm
		;;
	status)
		status_sqm
		;;
	generate)
		generate
		;;
	*)
		usage
		;;
esac
