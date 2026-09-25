# Plane staging

Staging Helmfile for self-hosted [Plane](https://plane.so) CE on **Docker Desktop**,
images from **Docker Hub**.

|              |                                                        |
| ------------ | ------------------------------------------------------ |
| Namespace    | `NAMESPACE` in `.env` (default local: `plane-staging`) |
| Kube context | `KUBE_CONTEXT` in `.env` (typically `docker-desktop`)  |
| Registry     | `DOCKERHUB_REGISTRY` in `.env` (Docker Hub org/user)   |
| Chart        | `plane/plane-ce` 1.6.2 (https://helm.plane.so)         |
| Database     | dedicated CNPG `Cluster` (`plane-db-staging`)          |
| Redis        | dedicated `StatefulSet` (`plane-redis-master`)         |
| Uploads      | MinIO in-cluster                                       |
| Backups      | disabled                                               |

Helm release name stays `plane` so chart Deployments remain `plane-api-wl` etc.

## Environment

Sensitive / env-specific values live in `.env` (gitignored):

```bash
cp .env.example .env
# set KUBE_CONTEXT=docker-desktop, NAMESPACE=plane-staging,
# DOCKERHUB_REGISTRY=<hub-org>, STORAGE_CLASS, etc.
```

```bash
set -a && source .env && set +a
helmfile sync
```

Same keys can move to GitHub Actions **secrets** later. Ingress host/class/issuer
are optional env placeholders until local ingress is wired.

## First-time setup (secrets)

In-cluster secrets (`plane-app-secret`, `plane-live-secret`, redis, db) are **not**
created by `helmfile sync`. Create them separately before the first apply.
No AWS Secrets Manager / ESO / ECR on this path.

## Deploy / Upgrade

```bash
set -a && source .env && set +a
helmfile -l name=plane-db-staging sync
helmfile sync
```

Manifests that use `${NAMESPACE}` / `${STORAGE_CLASS}` are applied via `envsubst`
in helmfile hooks. Patches use `{{ requiredEnv "NAMESPACE" }}`.

## Notes

- Beat worker must stay at 1 replica (Celery beat).
- Public Docker Hub images need no imagePullSecret; private Hub repos need a
  pull secret added separately (not included here).
