# Deployment preparation

Local container acceptance is recorded in [container.json](qa-evidence/container.json). It verifies the real complete-catalogue image, recovery with the worker offline, private-path404 responses, unchanged catalogue hash and session/observation persistence across restart. This is not a hosted acceptance result.

## Build and run

Build the catalogue and frontend using the README, then run `scripts/build_image.sh`. It uses lockfiles, an official Python3.12 image pinned by digest and a local frontend build. Docker Hub returned403 on this network; the official ECR mirror worked, and Liara's mirror returned the same digest. The final image is private because it contains the complete contest catalogue. Do not push it to a public image registry.

`docker compose up -d` runs one app with a persistent named volume. Put newly generated runtime `SESSION_SECRET`, `MODEL_WORKER_TOKEN` and the exact `PUBLIC_ORIGIN=http://127.0.0.1:8652` into a private environment file; do not reuse another environment's session signing key. The local dev environment uses8651, so deliberately change the origin for Compose. The local Codex worker remains a separate process and must target that same application URL. No authentication file is mounted into the application container.

`python scripts/package_deployment.py` creates `data/deployment.tar.gz` from an explicit allowlist: Dockerfile, hashed Python requirements, backend source, compiled frontend and validated catalogue. It excludes state, private environment files, personal source paths and Codex authentication. The archive is mode0600 and Git-ignored. Build/package again after final fixes before deployment; the manifest records the actual SHA-256 and members.

## Concrete Liara proposal — not provisioned

Verified22October2026 through the signed-in creation wizard: Nova Prime team still has2,000,000toman credit and no application. Proposed new application name: `torob-plan-b-2026`; Docker, one replica, port8000, base Earth plan512MB/0.5vCPU/5GB included disk. The console shows750,000toman/month and1,040toman/hour before VAT; the public pricing page rounds the hourly value to1,041. Forty-eight hours at the console figure is49,920toman before VAT. These are quoted prices, not incurred charges or a promise about tax/credit treatment. No app, disk, API key, deployment or paid resource has been created.

Local measured peak process RSS was59,980kB in the smoke workload. This supports beginning with512MB, not a production capacity guarantee. Mount a persistent disk at `/data`; ephemeral image storage is unsuitable for sessions/jobs. Keep the catalogue in the private image. Confirm the exact disk allocation/mount and effective invoice quote when provisioning. Use the chosen HTTPS app hostname as PUBLIC_ORIGIN, runtime-only secrets, one process, and no Codex credential on Liara.

The implementation plan explicitly requires concrete approval before paid provisioning. Complete approval for the new app/disk and local-worker target is still pending. Once approved: create the new resource without overwriting an existing name, upload the allowlisted artifact, verify readiness and cookie isolation, then run the actual hosted Persian need/reply, disconnect/search/recovery and reconnect checks. These remain open in the kanban. Existing source/UI tests do not close hosted acceptance.

Sources: [Docker deployment](https://docs.liara.ir/paas/docker/how-tos/deploy-app/), [persistent disks](https://docs.liara.ir/paas/docker/how-tos/use-disk/), [public pricing](https://liara.ir/pricing/), [official Liara Docker mirror](https://liara.ir/mirrors/docker/). Console creation wizard was inspected only through resource selection, then closed without creating anything.
