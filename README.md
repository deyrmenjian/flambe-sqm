# flambe-sqm

A port of [OpenWrt SQM](https://openwrt.org/docs/guide-user/network/traffic-shaping/sqm) to [IPFire](https://www.ipfire.org/).

OpenWrt’s Smart Queue Management (from [sqm-scripts](https://github.com/tohojo/sqm-scripts)) shapes the WAN slightly below the ISP rate with CAKE and an IFB for download. That is what fixes bufferbloat. IPFire’s built-in QoS is a different system (HTB classes on IMQ). Do not run both; stop QoS before starting SQM.

WUI: **Services → SQM**. Set download/upload to about 90% of measured kbit/s, then Start.

```bash
./scripts/install-overlay.sh
sqmctrl status
```

Leave the interface blank to follow `/var/ipfire/red/iface` (including PPPoE). After a Core Update, re-run the installer if the menu, CGI, or `sqmctrl` went missing.

## Credits

The queue scripts in `usr/lib/sqm/` are **sqm-scripts**, GPL-2, from CeroWrt/OpenWrt. Copyright Michael D. Taht, Toke Høiland-Jørgensen, Sebastian Moeller, Eric Luehrsen, and other contributors. Pinned commit: [`usr/lib/sqm/VERSION`](usr/lib/sqm/VERSION).

This overlay’s IPFire glue is also GPL-2. See [LICENSE](LICENSE).
