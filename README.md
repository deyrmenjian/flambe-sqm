# IPFire SQM addon

OpenWrt **Smart Queue Management** ([sqm-scripts](https://github.com/tohojo/sqm-scripts), GPL-2) packaged for IPFire. It is a Pakfire-style overlay: it does **not** replace IPFire’s class-based QoS.

## SQM vs IPFire QoS

IPFire Quality of Service (since CU163) puts **HTB classes** on RED (upload) and **IMQ** (download), with CAKE as *unlimited* leaf qdiscs and iptables marks for ports/TOS/L7.

SQM puts **CAKE (or HTB+fq_codel) as the shaper** on the WAN device, slightly below the ISP rate, and redirects download through an **IFB** (`ifb4<iface>`). That is what actually fights bufferbloat.

Do not run both. SQM refuses to start while QoS is enabled (`ENABLED=on` in `/var/ipfire/qos/settings`). Stop SQM before starting QoS. SQM never attaches to `imq0`.

## What is installed

| Path | Role |
| --- | --- |
| `/usr/lib/sqm/` | Vendored sqm-scripts plus `ipfire.sh` |
| `/usr/local/bin/sqmctrl` | Start/stop/status/generate (like `qosctrl`) |
| `/etc/sqm/sqm.conf` | Library and state paths |
| `/var/ipfire/sqm/settings` | WUI hash (`General::readhash`) |
| `/etc/rc.d/init.d/sqm` | SysV service |
| `/etc/rc.d/init.d/networking/red.up/25-RS-sqm` | Start on RED-up |
| `/etc/rc.d/init.d/networking/red.down/25-RS-sqm` | Stop on RED-down |
| `/srv/web/ipfire/cgi-bin/sqm.cgi` | WUI |
| `/var/ipfire/menu.d/41-sqm.menu` | Services → SQM |

Upstream commit is pinned in [`usr/lib/sqm/VERSION`](usr/lib/sqm/VERSION).

## Configure

WUI: **Services → SQM** (`/cgi-bin/sqm.cgi`). The menu file is [`var/ipfire/menu.d/41-sqm.menu`](var/ipfire/menu.d/41-sqm.menu).

CLI:

```
sqmctrl generate
sqmctrl start
sqmctrl status
sqmctrl stop
```

Defaults match typical OpenWrt LuCI SQM:

- Script: `piece_of_cake.qos` (optional `layer_cake.qos` or `simple.qos`)
- Empty interface → `/var/ipfire/red/iface` (follows PPPoE)
- Cake: `nat` + `dual-srchost` (up) / `dual-dsthost ingress` (down)
- Wash DSCP on ingress
- Ethernet overhead 18, MPU 64 (change for PPPoE/DOCSIS/ATM)

Set download/upload to about 85–95% of measured kbit/s. `0` disables that direction.

### Link-layer starting points

| Link | Link layer | Overhead | MPU |
| --- | --- | --- | --- |
| Ethernet / DHCP | ethernet | 18 | 64 |
| Ethernet + VLAN | ethernet | 22 | 64 |
| PPPoE | ethernet | 34 | 68 |
| DOCSIS | ethernet | 22 | 64 |
| ADSL ATM | atm | 44 | 96 |

## Kernel modules

Required for download shaping: `ifb`, `sch_ingress`, `act_mirred`, `cls_u32`, `sch_cake`. Upload-only CAKE needs `sch_cake`. `simple.qos` also needs `sch_htb`, `sch_fq_codel`, and **nftables** (IPFire 2.x is still iptables-first; prefer cake recipes unless you have nft).

## PPPoE, IPsec, OpenVPN

- PPPoE: leave the interface field empty so SQM tracks `red/iface`.
- IPsec/OpenVPN: only traffic that egresses RED is shaped. This addon does not divert tunnel traffic via IMQ.

## Build / install

**Live overlay** (root on the firewall, from this tree):

```
./scripts/install-overlay.sh
```

**ipfire-2.x tree:** copy this overlay into the IPFire source root, add `lfsmake2 sqm` to `make.sh` (`make.sh.inc`), and build the `sqm` Pakfire package (`lfs/sqm`, `src/paks/sqm/`).

Pakfire install does not autostart SQM. Enable it in the WUI or set `ENABLED=on` and run `sqmctrl start`.

## Core updates

This is an overlay, not an official Pakfire package, so **it is not guaranteed** across Core Updates.

Usually **kept** (files the update never ships): `/usr/lib/sqm/`, `/usr/local/bin/sqmctrl`, `/var/ipfire/sqm/settings`, `/srv/web/ipfire/cgi-bin/sqm.cgi`, `red.up/down/25-RS-sqm`, `/etc/rc.d/init.d/sqm`, `/var/ipfire/menu.d/41-sqm.menu`.

**At risk:** a Core Update that replaces the whole `menu.d` directory, `cgi-bin`, or networking hook directory; a new kernel without `ifb`/`sch_cake`; anything that restores `sqmctrl` permissions (needs `-rwsr-x--- root:nobody`). Settings under `/var/ipfire/sqm/` are your config — back them up with the rest of IPFire.

After an update: `ls /srv/web/ipfire/cgi-bin/sqm.cgi /var/ipfire/menu.d/41-sqm.menu /usr/local/bin/sqmctrl` and `sqmctrl status`. Re-run `./scripts/install-overlay.sh` from this tree if anything is missing. Do not enable built-in QoS at the same time.

## Tests

See [docs/TESTING.md](docs/TESTING.md).

## License

sqm-scripts and this glue are **GPL-2.0**.
