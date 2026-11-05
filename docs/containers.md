# Container setup

Two Docker build targets serve the existing application: a CPU model API and a smaller Streamlit dashboard without Torch. Model artifacts are mounted read-only from the existing `models` directory; model weights and runtime databases are excluded from build context. A named Docker volume stores SQLite data separately from local development databases.

## Current verification status

Docker Desktop 4.98.0 installed successfully; CLI 29.9.2 and Compose 5.6.1 are verified. Both required Windows features were enabled and reported a restart requirement. The Linux engine remained unavailable in this session. Compose passed the official JSON schema and installed CLI validation, and required model files are present. Image builds, Linux dependency resolution and container HTTP smoke tests are **not** verified yet. See `docs/project_status.md` for the Windows build compatibility limit and exact restart/resume steps.

The official [CPU wheel index](https://download.pytorch.org/whl/cpu/torch/) lists Python 3.14 Linux wheels for the pinned PyTorch 2.15.0 release. That verifies availability, not installation inside the proposed image. Windows lockfiles are not used for Linux image installation. Direct package versions are pinned; transitive dependencies and the `python:3.14-slim` tag can change, so this is not a bit-for-bit reproducible release.

## Run when Docker is available

Use a Docker installation configured for Linux containers. From the project root:

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose logs api
```

- Container dashboard: http://127.0.0.1:8502
- Container API docs: http://127.0.0.1:8002/docs
- Existing local Python services remain on ports 8501 and 8000.

The dashboard waits for the API healthcheck and connects over the Compose network using `http://api:8000`. The different host ports avoid collisions with the running local application. Published ports bind to localhost because application authentication remains unimplemented. Both images run as an unprivileged user.

Required artifacts: `models/distilbert/experiment.json` and the completed `models/distilbert/final` checkpoint/tokenizer files. They already exist locally but are ignored by Git. A fresh checkout must receive these trusted model artifacts before starting Compose. The API loads local weights only; startup never trains or downloads a model.

Stop services while preserving tickets:

```powershell
docker compose down
```

The named volume remains. Do not add `--volumes` unless you intend to delete stored container tickets and feedback. For backups, stop API writes and copy the database plus any WAL state consistently, or use SQLite's backup facility. Copying a live database file alone may omit recent WAL changes.

Design references: Docker's [build best practices](https://docs.docker.com/build/building/best-practices/) and [Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/).
