# flambe-sqm

A port of [CeroWrt Smart Queue Management](https://www.bufferbloat.net/projects/cerowrt/wiki/Smart_Queue_Management/) to [IPFire](https://www.ipfire.org/).

That means [sqm-scripts](https://github.com/tohojo/sqm-scripts): shape the WAN slightly below the ISP rate, with CAKE and an IFB for download. OpenWrt later shipped the same scripts; this is not OpenWrt’s older qos-scripts, and it is not IPFire’s built-in QoS. Stop QoS before starting SQM.

WUI: **Services → SQM**. Set download/upload to about 90% of measured kbit/s, then Start.

```bash
./scripts/install-overlay.sh
sqmctrl status
```

Leave the interface blank to follow `/var/ipfire/red/iface` (including PPPoE). After a Core Update, re-run the installer if the menu, CGI, or `sqmctrl` went missing.

## Credits

The queue scripts in `usr/lib/sqm/` are **sqm-scripts** from the CeroWrt / Bufferbloat project, GPL-2. Copyright Michael D. Taht, Toke Høiland-Jørgensen, Sebastian Moeller, Eric Luehrsen, and other contributors. Pinned commit: [`usr/lib/sqm/VERSION`](usr/lib/sqm/VERSION).

This overlay’s IPFire glue is also GPL-2. See [LICENSE](LICENSE).
