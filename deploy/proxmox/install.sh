#!/usr/bin/env bash
# Run on the Proxmox host. Creates an unprivileged Debian 13 LXC for one openNASR
# role, installs the packages from local wheels, and starts the service.
#
#   install.sh --role api --ctid 125 --hostname opennasr-api --ip 10.10.20.125/24 \
#              --wheels /root/opennasr-wheels --env-file /root/api.env [--yes]
#
# Defaults match proxopotamus (VLAN 20 on vmbr2, md1200-0, Debian 13 template).
set -euo pipefail
export LC_ALL=C LANG=C

ROLE=""; CTID=""; NAME=""; IP=""; WHEELS=""; ENVFILE=""; FORCE_DUCKDB=""; YES=0
GATEWAY=10.10.20.1; DNS=10.10.20.1; BRIDGE=vmbr2; VLAN=20; STORAGE=md1200-0
TEMPLATE=debian-13-standard_13.6-1_amd64.tar.zst
CORES=2; MEMORY=""; SWAP=512; DISK=""
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"

usage() { sed -n '2,9p' "$0"; exit "${1:-2}"; }
while [ $# -gt 0 ]; do
  case "$1" in
    --role) ROLE="$2"; shift 2 ;;       --ctid) CTID="$2"; shift 2 ;;
    --hostname) NAME="$2"; shift 2 ;;   --ip) IP="$2"; shift 2 ;;
    --gateway) GATEWAY="$2"; shift 2 ;; --dns) DNS="$2"; shift 2 ;;
    --bridge) BRIDGE="$2"; shift 2 ;;   --vlan) VLAN="$2"; shift 2 ;;
    --storage) STORAGE="$2"; shift 2 ;; --template) TEMPLATE="$2"; shift 2 ;;
    --cores) CORES="$2"; shift 2 ;;     --memory) MEMORY="$2"; shift 2 ;;
    --disk) DISK="$2"; shift 2 ;;       --wheels) WHEELS="$2"; shift 2 ;;
    --env-file) ENVFILE="$2"; shift 2 ;; --duckdb-version) FORCE_DUCKDB="$2"; shift 2 ;;
    --yes) YES=1; shift ;;              -h|--help) usage 0 ;;
    *) echo "unknown argument: $1" >&2; usage ;;
  esac
done
case "$ROLE" in archiver|api) ;; *) echo "--role archiver|api is required" >&2; usage ;; esac
[ -n "$CTID" ] && [ -n "$NAME" ] && [ -n "$IP" ] && [ -n "$WHEELS" ] && [ -n "$ENVFILE" ] || usage
[ -n "$MEMORY" ] || { [ "$ROLE" = api ] && MEMORY=3072 || MEMORY=2048; }
[ -n "$DISK" ] || { [ "$ROLE" = api ] && DISK=8 || DISK=24; }   # archiver stages ~2 cycles

command -v pct >/dev/null || { echo "run this on the Proxmox host" >&2; exit 1; }
! pct status "$CTID" >/dev/null 2>&1 || { echo "container $CTID already exists" >&2; exit 1; }
[ -f "/var/lib/vz/template/cache/$TEMPLATE" ] || { echo "template $TEMPLATE not found" >&2; exit 1; }
ls "$WHEELS"/*.whl >/dev/null 2>&1 || { echo "no wheels in $WHEELS" >&2; exit 1; }
[ -f "$ENVFILE" ] || { echo "env file $ENVFILE not found" >&2; exit 1; }
for f in "$HERE/../guest/guest-setup.sh"; do [ -f "$f" ] || { echo "missing $f" >&2; exit 1; }; done

cat <<PLAN
Create LXC $CTID '$NAME' ($ROLE): $CORES cores, ${MEMORY} MB, ${DISK} G on $STORAGE,
  net $BRIDGE vlan $VLAN, $IP via $GATEWAY, dns $DNS
PLAN
if [ "$YES" -ne 1 ]; then read -r -p "Continue? [y/N] " a; [ "$a" = y ] || exit 1; fi

pct create "$CTID" "local:vztmpl/$TEMPLATE" \
  --hostname "$NAME" --cores "$CORES" --memory "$MEMORY" --swap "$SWAP" \
  --rootfs "$STORAGE:$DISK" --unprivileged 1 --features nesting=1 --ostype debian \
  --onboot 1 --tags opennasr \
  --net0 "name=eth0,bridge=$BRIDGE,tag=$VLAN,ip=$IP,gw=$GATEWAY" --nameserver "$DNS"
pct start "$CTID"

echo "waiting for the network"
for _ in $(seq 1 30); do
  pct exec "$CTID" -- getent hosts deb.debian.org >/dev/null 2>&1 && break
  sleep 2
done
pct exec "$CTID" -- getent hosts deb.debian.org >/dev/null || { echo "no network in the container" >&2; exit 1; }

pct exec "$CTID" -- mkdir -p /root/wheels /root/deploy /etc/openNASR
for wheel in "$WHEELS"/*.whl; do pct push "$CTID" "$wheel" "/root/wheels/$(basename "$wheel")"; done
pct push "$CTID" "$HERE/../guest/guest-setup.sh" /root/guest-setup.sh --perms 700
for unit in "$REPO"/archiver/deploy/*.service "$REPO"/archiver/deploy/*.timer "$REPO"/api/deploy/*.service; do
  pct push "$CTID" "$unit" "/root/deploy/$(basename "$unit")"
done
pct push "$CTID" "$ENVFILE" "/etc/openNASR/$ROLE.env" --perms 600

ARGS=(--role "$ROLE"); [ -z "$FORCE_DUCKDB" ] || ARGS+=(--duckdb-version "$FORCE_DUCKDB")
pct exec "$CTID" -- /root/guest-setup.sh "${ARGS[@]}"
echo "Container $CTID ($NAME) is up at ${IP%/*}. Remove $ENVFILE from this host when done."
