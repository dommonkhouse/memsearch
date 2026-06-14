# Capped batch 019 correction: probe and rollback anchors

Reviewed on 2026-06-14 for MON-316 capped Graphiti relationship tuning.

Graphiti probe safety uses a temporary probe group.
Graphiti probe safety uses group IDs shaped like `ms_memsearch_probe_<timestamp>`.
Graphiti probe cleanup clears only the temporary probe group.
Graphiti probe cleanup must not clear non-probe graph data.
Graphiti probe cleanup must verify that scoped `get_episodes` returns no probe episodes.

Graphiti rollback safety stops only Graphiti user agents and the Graphiti Compose runtime.
Graphiti rollback safety preserves Markdown memory files.
Graphiti rollback safety preserves Milvus data.
Graphiti rollback safety preserves `.memsearch/memory`.
Graphiti rollback safety preserves the Graphiti manifest.
Graphiti rollback safety must not run `docker compose down -v`.
Graphiti rollback safety must not delete default Colima or Milvus.
Graphiti rollback safety must not delete `/Volumes/SSD/graphiti-mon316` without explicit approval.

