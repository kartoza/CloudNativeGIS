# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Repository layout

Two independent parts live here:

- **`django_project/`** - the Cloud Native GIS Django platform (layers, styles,
  Maputnik editor), also installable as the `cloud_native_gis` Django app.
  Run through docker compose in `deployment/`; see the root `Makefile` /
  `justfile` (`just dev`, `just test`, `just lint`) and `README.md`.
- **`processing/`** - CloudNativeGIS Processing ("Lite"): a standalone,
  database-free FastAPI service converting shapefile/GeoPackage -> PMTiles
  (+ GeoParquet) and TIFF -> COG. Used by CloudBench
  (`kartoza-cloudbench`, `apps/s3/cng_lite.py`). Its own `Makefile`, `.env`
  and `README.md`.

## processing/ (CloudNativeGIS Processing)

- `app/main.py` - FastAPI app; routers in `app/routers/` (`pmtiles`, `cog`,
  `gpkg`, `jobs`), conversion logic in `app/services/`, helpers in `app/utils/`.
- Conversions are background jobs: `POST /api/v1/pmtiles|cog` -> `job_id`,
  poll `GET /api/v1/jobs/{id}`, download `GET /api/v1/jobs/{id}/result/{file}`.
  `POST /api/v1/gpkg/layers` inspects a GeoPackage synchronously.
- Auth: `Authorization: Bearer <LITE_API_TOKEN>` on every route except
  `/health`. **An empty `LITE_API_TOKEN` disables auth entirely** - keep that
  in mind anywhere the service is exposed.
- Settings are env vars (`app/config.py`), documented in `.env.template`.
- `make build | up | run | logs | shell | smoke-test` (docker compose).
- Released as `ghcr.io/kartoza/cloudnativegis-processing:<X.Y.Z>` by pushing a
  `vX.Y.Z-processing` tag (`.github/workflows/release-processing.yaml`).

## processing/hetzner/ (on-demand servers on Hetzner Cloud)

Runs Processing on throwaway Hetzner Cloud servers started from a snapshot.
Everything is driven from its own `Makefile`, with settings in
`processing/hetzner/.env` (from `.env.template`, git-ignored; holds
`HCLOUD_TOKEN`).

```bash
cd processing/hetzner
make generate-snapshot [VERSION=0.0.3]   # Packer: temp server -> snapshot
make spin-up [server_name=...]           # server from the snapshot
make delete server_name=...              # delete it again
```

- `cng-lite.pkr.hcl` - Packer (hcloud plugin) build: Ubuntu + Docker, pulls the
  processing image into the snapshot, installs `cng-lite.service`. Snapshot
  labels: `app=cng-lite`, `version=<VERSION>`. Needs the `packer` binary
  (HashiCorp, not the PyPI package).
- `cng-lite.service` - systemd unit, **installed but not enabled**: it only
  starts once `/etc/cng-lite/env` holds a non-empty `LITE_API_TOKEN`
  (fail closed, see the auth note above).
- `hetzner.py` - `HetznerClient` (standard library only, no pip installs):
  - `spin_up(server_name="")` finds the newest snapshot (optionally by
    `version`), creates the server with a fresh per-server token injected via
    cloud-init `user_data`, waits for `/health`, then verifies the token
    (404 with it, 401 without). Returns `{id, name, ip, url, token, created,
    env_file}` and saves them to `.servers/<name>.env` (git-ignored, mode 600).
    A server that fails to come up is deleted unless `keep_on_failure`.
  - `delete(server_name)` deletes by name - only servers labelled
    `role=cng-lite`, `managed-by=spin-up-from-snapshot` (don't rename these
    labels while such servers exist).
  - Errors raise `HetznerError`; the CLI (`hetzner.py spin-up|delete`) wraps it.

Hetzner facts that shape this design:

- A server is billed per **started hour from its `created` time until it is
  deleted** - powering off doesn't stop billing. Always delete servers when
  done; `spin-up` prints a "delete before" time (created + 55 min).
- Snapshots are billed per GB/month while they exist; delete old ones.
- Packer's `SERVER_TYPE` is the build server: keep it the smallest x86 type,
  since a snapshot only fits server types with at least its disk size (and the
  same architecture). `SPINUP_SERVER_TYPE` may be larger.
- `LOCATION` codes: `fsn1` Falkenstein, `nbg1` Nuremberg, `hel1` Helsinki,
  `ash` Ashburn, `hil` Hillsboro, `sin` Singapore.
- Servers expose port 8000 over plain HTTP on a public IP; use `FIREWALL_ID`
  to restrict it to the caller outside of testing.

Not built yet: CloudBench calling `HetznerClient` per conversion (instead of a
fixed `CLOUDNATIVEGIS_URL`), and a reaper for orphaned servers.
