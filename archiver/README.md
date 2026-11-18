# openNASR archiver

Downloads the current FAA NASR cycle, builds and validates the DuckDB database, and publishes
the zip, database, sidecar and manifest to an S3 bucket. The manifest is uploaded last and is the
"validated" marker. Keys never change once written.

```
openNASR-archiver run        # one pass (the timer runs this daily)
openNASR-archiver status     # validated builds in the bucket
openNASR-archiver publish D  # publish a cycle already in the local cache
openNASR-archiver rebuild [D]# rebuild a database from its archived zip and compare
```

Settings come from the environment or `--env-file` (see `deploy/archiver.env.example`).
A bucket outage loses nothing: the local cache is the staging area and the next pass publishes
from it. Alerts fire once when a problem starts and once when it clears.

Install on a host: create user `opennasr`, a venv at `/opt/openNASR/venv` with
`pip install openNASR ./contract "./archiver[s3]"`, copy the two `deploy/*.service|timer` files to
`/etc/systemd/system/`, put the env file at `/etc/openNASR/archiver.env`, then
`systemctl enable --now openNASR-archiver.timer`. The installer must pick a working DuckDB
version for the CPU (see REPLAN.md, "DuckDB version selection").

On proxopotamus use `deploy/proxmox/install.sh --role archiver` (see `deploy/`); it builds the container, picks a DuckDB that runs on the CPU, and installs the timer.
