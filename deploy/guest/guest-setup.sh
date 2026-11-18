#!/usr/bin/env bash
# Runs INSIDE the container (pushed and started by deploy/proxmox/install.sh).
# Installs the openNASR packages from local wheels, picks a DuckDB that actually
# runs on this CPU, installs the systemd units and starts the service.
set -euo pipefail
export LC_ALL=C LANG=C

ROLE=""; FORCE_DUCKDB=""
while [ $# -gt 0 ]; do
  case "$1" in
    --role) ROLE="$2"; shift 2 ;;
    --duckdb-version) FORCE_DUCKDB="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
case "$ROLE" in archiver|api) ;; *) echo "--role archiver|api required" >&2; exit 2 ;; esac

VENV=/opt/openNASR/venv
WHEELS=/root/wheels
export DEBIAN_FRONTEND=noninteractive

echo "== packages"
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip ca-certificates curl >/dev/null

id opennasr >/dev/null 2>&1 || useradd --system --create-home --home-dir "/var/lib/openNASR-$ROLE" opennasr
mkdir -p /opt/openNASR "/var/lib/openNASR-$ROLE" /etc/openNASR
chown opennasr:opennasr "/var/lib/openNASR-$ROLE"

echo "== virtualenv and packages"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
if [ "$ROLE" = archiver ]; then
  "$VENV/bin/pip" install --quiet --find-links "$WHEELS" openNASR "openNASR-contract[s3]" "openNASR-archiver[s3]"
else
  "$VENV/bin/pip" install --quiet --find-links "$WHEELS" openNASR "openNASR-contract[s3]" openNASR-api
fi

# DuckDB 2.x crashes ("Illegal instruction") on CPUs without AVX2, and a wheel
# that installs can still be unusable. So probe by running it, newest first.
# The core package currently requires duckdb<2, so 2.x is not a candidate yet.
probe() {
  "$VENV/bin/python" -c "import duckdb; c = duckdb.connect(); assert c.execute('select 1').fetchone() == (1,)" 2>/dev/null
}
echo "== choosing a DuckDB that runs on this CPU ($(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | xargs))"
chosen=""
if [ -n "$FORCE_DUCKDB" ]; then
  "$VENV/bin/pip" install --quiet "duckdb==$FORCE_DUCKDB"
  probe || { echo "forced duckdb==$FORCE_DUCKDB does not run on this CPU" >&2; exit 3; }
  chosen="$FORCE_DUCKDB"
else
  for spec in "" "==1.4.*" "==1.3.*" "==1.2.*"; do
    [ -n "$spec" ] && "$VENV/bin/pip" install --quiet "duckdb$spec" 2>/dev/null || true
    if probe; then
      chosen="$("$VENV/bin/python" -c 'import duckdb; print(duckdb.__version__)')"
      break
    fi
    echo "   duckdb ${spec:-latest 1.x} does not run here; trying the next"
  done
fi
[ -n "$chosen" ] || { echo "no DuckDB version runs on this CPU" >&2; exit 3; }
echo "   using duckdb $chosen"
echo "$chosen" > /etc/openNASR/duckdb-version

echo "== service files"
if [ "$ROLE" = archiver ]; then
  install -m 644 /root/deploy/openNASR-archiver.service /root/deploy/openNASR-archiver.timer /etc/systemd/system/
else
  install -m 644 /root/deploy/openNASR-api.service /etc/systemd/system/
fi
chown root:opennasr "/etc/openNASR/$ROLE.env"; chmod 640 "/etc/openNASR/$ROLE.env"
systemctl daemon-reload

if [ "$ROLE" = api ]; then
  systemctl enable --now openNASR-api.service
  for _ in $(seq 1 90); do
    curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1 && break
    sleep 2
  done
  curl -fsS http://127.0.0.1:8000/health; echo
else
  systemctl enable --now openNASR-archiver.timer
  echo "timer: $(systemctl list-timers openNASR-archiver.timer --no-legend | head -1)"
fi
echo "== done ($ROLE, duckdb $chosen)"
