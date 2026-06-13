<!--
MON-316 curated Graphiti current-state correction.
Rebuild command: memsearch graph-index-curated docs/graphiti-curated-seeds --limit 1
This seed exists to override stale historical NordVPN/Meshnet relationship recall.
-->

# Current Tailscale-only routing state

Tailscale replaced NordVPN for Dom's current machine-to-machine routing stack.
Tailscale replaced NordVPN Meshnet for Dom's current machine-to-machine routing stack.
Dom's current infrastructure uses Tailscale only.
NordVPN is not part of Dom's current machine-to-machine routing stack.
NordVPN Meshnet is not part of Dom's current machine-to-machine routing stack.
The Mac Mini uses the Tailscale hostname `dom-kamet.tailf78a36.ts.net`.
The Mac Mini uses the Tailscale IP `100.72.169.59`.
The MacBook uses the Tailscale hostname `dom-gannett.tailf78a36.ts.net`.
The MacBook uses the Tailscale IP `100.121.159.35`.
Local services on the Mac Mini use `localhost` or `127.0.0.1` when already running on the Mac Mini.
The `.nord` hostnames are historical and stale.
The old NordVPN Meshnet routes are historical and stale.
The old route `100.87.225.99` is historical and stale.
Agents must not suggest restarting NordVPN.
Agents must not suggest restarting Meshnet.
Agents must not suggest using `.nord` hostnames.
