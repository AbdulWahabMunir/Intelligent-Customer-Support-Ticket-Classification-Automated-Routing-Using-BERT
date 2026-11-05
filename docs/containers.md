# Container setup

Two Docker build targets serve the existing application: a CPU model API and a smaller Streamlit dashboard without Torch. Model artifacts are mounted read-only from the existing `models` directory; model weights and runtime databases are excluded from build context. A named Docker volume stores SQLite data separately from local development databases.

## Current verification status

Windows was upgraded to build 26300. Docker Desktop 4.98.0, engine 29.9.2 and Compose 5.6.1 work with WSL 3.0.3. Both images built successfully, including CPU PyTorch installation. Container prediction, SQLite ticket/feedback storage, persistence across an API restart and dashboard health passed. See `reports/containers/runtime.json`. All 41 local tests passed.

Windows lockfiles are not used for Linux image installation. Direct package versions are pinned; transitive dependencies and the `python:3.14-slim` tag can change, so this is not a bit-for-bit reproducible release.

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

The dashboard waits for the API healthcheck and connects over the Compose network using `http://api:8000`. Different host ports avoid collisions with local services. Published ports bind to localhost. Hosted deployments additionally use API-key and reviewer-password access; ordinary local Compose is unauthenticated unless those variables are configured. Both images run as an unprivileged user.

Required artifacts: `models/distilbert/experiment.json` and the completed `models/distilbert/final` checkpoint/tokenizer files. They already exist locally but are ignored by Git. A fresh checkout must receive these trusted model artifacts before starting Compose. The API loads local weights only; startup never trains or downloads a model.

Stop services while preserving tickets:

```powershell
docker compose down
```

The named volume remains. Do not add `--volumes` unless you intend to delete stored container tickets and feedback. For backups, stop API writes and copy the database plus any WAL state consistently, or use SQLite's backup facility. Copying a live database file alone may omit recent WAL changes.

Design references: Docker's [build best practices](https://docs.docker.com/build/building/best-practices/) and [Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/).
