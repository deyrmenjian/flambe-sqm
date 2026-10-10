# SQM on IPFire — verification

Run these checks on a real IPFire box (this overlay cannot exercise `tc` here).

## Kernel modules

```
modprobe ifb
modprobe sch_cake
modprobe act_mirred
modprobe sch_ingress
modprobe cls_u32
modinfo ifb sch_cake act_mirred
```

If `ifb` is missing from the IPFire kernel, ingress (download) shaping cannot be installed. Egress (upload) CAKE on RED can still work with download set to 0.

## Mutex with QoS

1. Enable Quality of Service in the WUI, then try **Start** on SQM — it must refuse.
2. Stop QoS, start SQM.
3. Confirm `tc qdisc show dev $(cat /var/ipfire/red/iface)` shows `cake bandwidth …`, not `htb`.
4. Confirm there is **no** `imq0` used by SQM. Download uses `ifb4<iface>` (name truncated to 15 characters).

## Runtime shape

```
/usr/local/bin/sqmctrl status
tc -s qdisc show
ip link show type ifb
```

Expected:

- Root CAKE (or HTB if using `simple.qos`) on the RED iface with a **non-zero** `bandwidth`.
- Ingress qdisc on RED plus CAKE on `ifb4…`.
- After `sqmctrl stop`, `/lib/udev/network-aqm` has restored fq_codel (or the CU default) on RED.

## Bufferbloat

1. Measure idle latency (Cloudflare speed test or Waveform bufferbloat).
2. Repeat under load (speed test saturating up and down).
3. With SQM on and rates at ~90% of measured goodput, loaded latency should stay close to idle. Without SQM, loaded latency usually jumps into tens or hundreds of milliseconds.

## PPPoE

Disconnect and reconnect the RED/PPPoE link. SQM must follow `/var/ipfire/red/iface` (often `ppp0`), not the Ethernet underlay. `red.up/25-RS-sqm` starts SQM; `red.down/25-RS-sqm` stops it.

## IPsec / OpenVPN

Traffic that does not leave via RED is not shaped. Do not point SQM at `imq0` to catch it.

## Logs

```
grep sqm /var/log/messages
```

With **Debug logging** enabled, start/stop logs are under `/run/sqm/`.
