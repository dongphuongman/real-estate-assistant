# Core scripts

This folder contains the main developer entrypoints for running the project.

## Windows (PowerShell)

Local:

```powershell
.\scripts\core\local\run.ps1
.\scripts\core\local\run-internet.ps1
```

Docker:

```powershell
.\scripts\core\docker\gpu.ps1
.\scripts\core\docker\gpu-internet.ps1
```

## Linux/Mac

```sh
./scripts/core/linux/start.sh --mode local
./scripts/core/linux/docker.sh gpu
```

## Layout

- `scripts/core/local/` local runs
- `scripts/core/docker/` docker runs
- `scripts/core/env/` setup/bootstrap wrappers
- `scripts/core/ci/` CI parity wrappers
- `scripts/core/linux/` Linux/Mac helpers

Full guide:

- `docs/SCRIPTS.md`
