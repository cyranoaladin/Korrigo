# Porte 6I - Docker cleanup plan, dry-run only

This plan is preparatory only. No cleanup is authorized until Porte 6H-C returns `POST_REPAIR_24H_OBSERVATION_DONE`.

## Objective

Clean only obsolete Korrigo Docker images after final automatic post-repair observation is clean.

## Permanent Interdictions

- No `docker system prune`.
- No `docker volume prune`.
- No `docker network prune`.
- No `docker compose down`.
- No `down -v`.
- No volume deletion.
- No backup deletion.
- No DB or Redis deletion.
- No non-Korrigo image deletion.
- No network deletion.
- No container deletion unless explicitly stopped, Korrigo-only, and separately approved.

## Images To Protect

Active runtime:

- `korrigo-backend:korrigo-direct-c38a586`
- `korrigo-nginx:korrigo-direct-f793f0c`

Immediate rollback:

- `korrigo-backend:korrigo-direct-f793f0c`
- `korrigo-backend:korrigo-lot0g-direct-1fc58d1`
- `korrigo-nginx:korrigo-lot0g-direct-1fc58d1`

Base data service images:

- `postgres:15-alpine`
- `redis:7-alpine`

## Volumes To Protect

- `docker_postgres_data`
- `docker_media_volume`
- `docker_backup_volume`

## Principle

The future cleanup must:

1. list Korrigo images;
2. identify images not used by running containers;
3. exclude active images;
4. exclude rollback images;
5. exclude DB/Redis images;
6. exclude all non-Korrigo images;
7. generate a candidate list;
8. perform a dry-run review;
9. request explicit human validation;
10. remove only explicitly listed image IDs in a later approved gate;
11. recheck production health;
12. never touch volumes, networks, backups, DB, Redis, or non-Korrigo projects.

## Future Evidence Required

Before any deletion, collect:

- production health;
- latest automatic backup after repair;
- backup checksums;
- StorageBox dry-run at zero;
- protected image list;
- running container images;
- candidate image IDs;
- protected volumes present.

## Current Status

Cleanup remains blocked until Porte 6H-C is fully clean after the automatic backup and sync cycle.
