# Proxmox / LXC Multicast Notes

Why Sonos SSDP discovery may fail in LXC containers, and what to do about it.

## Why This Matters

Sonos speakers are discovered via SSDP (Simple Service Discovery Protocol), which uses UDP multicast on port 1900.

When the daemon runs inside a Proxmox LXC container, it uses `network_mode: host` — sharing the host's network stack. However, multicast traffic is not always forwarded across the Linux bridge (typically `vmbr0`) into LXC network namespaces by default.

When SSDP fails, the daemon logs

```
[SONOS] No speakers found via SSDP. Check firewall (allow UDP 1900 multicast) and Proxmox bridge multicast forwarding. Set SONOS_SPEAKER_IPS as a fallback.
```

## Fix: Enable Multicast Bridge Forwarding

Enable multicast forwarding on the Proxmox host bridge. The exact steps depend on your Proxmox version and bridge configuration.

See the official Proxmox documentation for network configuration options:
[https://pve.proxmox.com/wiki/Network_Configuration](https://pve.proxmox.com/wiki/Network_Configuration)

## Escape Hatch: SONOS_SPEAKER_IPS

If configuring bridge multicast is not possible, bypass SSDP entirely by setting speaker IPs directly in `.env`:

```
SONOS_SPEAKER_IPS=Dining Room=192.168.1.50,Living Room=192.168.1.51
```

Use the exact room names as Spotify reports them. Find speaker IPs in the Sonos app: **Settings -> System -> [Room] -> About [Room]**.

When `SONOS_SPEAKER_IPS` is set, SSDP discovery is skipped entirely.
