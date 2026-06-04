# Roadmap

## Backlog

- [ ] Corriger la configuration Raspberry Pi qui injecte `cgroup_disable=memory`, afin que Docker applique les limites memoire Compose (`api=40M`, `bot=35M`) et que `docker inspect ... HostConfig.Memory` ne retourne plus `0`. Voir aussi `pi-memory-limit-debug-notes.md`.
