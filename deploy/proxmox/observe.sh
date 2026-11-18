#!/usr/bin/env bash
# Read-only Phase 7 check of the production deployment. Changes nothing.
#
#   observe.sh [--proxmox root@100.100.10.10] [--url https://nasr.xds-lab.com]
#              [--archiver-ct 124] [--api-ct 125] [--route "KABQ.DOOKK3.TXO..KTYR"]
#              [--env-file .env] [--zips]
#
# Needs ssh to the Proxmox host and (for the bucket check) the repo's read-only
# bucket settings. Prints PASS / WARN / FAIL lines; exit 1 if anything FAILs.
set -uo pipefail
export LC_ALL=C

PROXMOX=root@100.100.10.10; URL=https://nasr.xds-lab.com
ARCHIVER=124; API=125; ROUTE="KABQ.DOOKK3.TXO..KTYR"; ENVFILE=""; ZIPS=""
HERE="$(cd "$(dirname "$0")" && pwd)"; REPO="$(cd "$HERE/../.." && pwd)"
while [ $# -gt 0 ]; do
  case "$1" in
    --proxmox) PROXMOX="$2"; shift 2 ;;  --url) URL="$2"; shift 2 ;;
    --archiver-ct) ARCHIVER="$2"; shift 2 ;; --api-ct) API="$2"; shift 2 ;;
    --route) ROUTE="$2"; shift 2 ;;      --env-file) ENVFILE="$2"; shift 2 ;;
    --zips) ZIPS="--zips"; shift ;;      -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

FAILS=0
pass() { echo "PASS  $*"; }
warn() { echo "WARN  $*"; }
fail() { echo "FAIL  $*"; FAILS=$((FAILS + 1)); }
ct() { ssh -o BatchMode=yes -o ConnectTimeout=10 "$PROXMOX" "pct exec $1 -- bash -c '$2'" 2>/dev/null; }

echo "== API ($URL)"
ready="$(curl -s --max-time 15 "$URL/ready")"
case "$ready" in *'"status":"ready"'*) pass "ready: $ready" ;; *) fail "/ready: ${ready:-no answer}" ;; esac
cycles="$(curl -s --max-time 15 "$URL/v1/cycles")"
python3 - "$cycles" <<'PY' || fail "/v1/cycles unreadable"
import json, sys
d = json.loads(sys.argv[1])
print("PASS  default cycle", d["default"], "| cycles:",
      ", ".join(f'{c["effective_date"]}{"" if c["in_effect"] else " (upcoming)"}' for c in d["cycles"]))
PY
for date in $(python3 -c "import json,sys;print(' '.join(c['effective_date'] for c in json.loads(sys.argv[1])['cycles']))" "$cycles" 2>/dev/null); do
  out="$(curl -s --max-time 40 -X POST "$URL/v1/route/resolve" -H 'content-type: application/json' \
        -d "{\"route\":\"$ROUTE\",\"cycle\":\"$date\"}" | python3 -c "
import json,sys; d=json.load(sys.stdin); print(d['complete'], len(d['points']))" 2>/dev/null)"
  [ "$out" = "True 8" ] && pass "route resolves completely on $date ($out points)" || warn "route on $date: ${out:-no answer}"
done

echo "== archiver (CT $ARCHIVER)"
ct "$ARCHIVER" "systemctl show openNASR-archiver.timer -p LastTriggerUSec -p NextElapseUSecRealtime --no-pager" | sed 's/^/      /'
last="$(ct "$ARCHIVER" "systemctl show openNASR-archiver.timer -p LastTriggerUSec --value")"
if [ -z "$last" ] || [ "$last" = "n/a" ]; then warn "the timer has not fired yet"; else pass "timer last fired: $last"; fi
res="$(ct "$ARCHIVER" "systemctl show openNASR-archiver.service -p Result -p ExecMainStatus --value | tr \"\\n\" \" \"")"
case "$res" in "success 0"*|"success 0 ") pass "last service run: success, exit 0" ;; *) warn "last service run: ${res:-unknown}" ;; esac
ct "$ARCHIVER" "journalctl -u openNASR-archiver --no-pager -n 3 -o cat | cut -c1-150" | sed 's/^/      /'
state="$(ct "$ARCHIVER" "cat /var/lib/openNASR-archiver/state.json | tr -d \"\\n \"")"
case "$state" in *'"active":{}'*) pass "no active alerts ($state)" ;; *) fail "active alerts: $state" ;; esac
echo "      release: $(ct "$ARCHIVER" "systemctl show openNASR-archiver -p ExecStart --value | grep -o \"path=[^ ]*\" | head -1")"

echo "== API container (CT $API)"
echo "      release: $(ct "$API" "systemctl show openNASR-api -p ExecStart --value | grep -o \"path=[^ ]*\" | head -1")"
echo "      disk: $(ct "$API" "df -h / | tail -1" | awk '{print $3" used of "$2" ("$5")"}')"

echo "== monitoring (Gatus)"
g="$(curl -s --max-time 10 http://10.10.20.80:8080/api/v1/endpoints/statuses | python3 -c "
import json,sys
for e in json.load(sys.stdin):
    if 'opennasr' in e['key']: print('ok' if e['results'][-1]['success'] else 'failing')" 2>/dev/null)"
[ "$g" = ok ] && pass "Gatus openNASR API check is green" || warn "Gatus: ${g:-not reachable from here}"

echo "== bucket integrity (hashes against the manifests)"
PY="${PYTHON:-python3}"
if [ -n "$ENVFILE" ]; then
  "$PY" "$REPO/tools/verify_bucket.py" --env-file "$ENVFILE" $ZIPS || fail "bucket verification found problems"
else
  warn "skipped (give --env-file with the read-only bucket settings; add --zips to check the archives too)"
fi

echo
[ "$FAILS" -eq 0 ] && echo "No failures." || echo "$FAILS failure(s)."
exit $([ "$FAILS" -eq 0 ] && echo 0 || echo 1)
