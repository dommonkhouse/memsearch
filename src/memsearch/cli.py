"""CLI interface for memsearch."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import click

from .config import (
    GLOBAL_CONFIG_PATH,
    PROJECT_CONFIG_PATH,
    ConfigEnvVarError,
    MemSearchConfig,
    config_to_dict,
    get_config_value,
    load_config_file,
    resolve_config,
    save_config,
    set_config_value,
)
from .io import read_utf8_text_replace

try:
    from pymilvus.exceptions import MilvusException
except ImportError:
    MilvusException = Exception


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


def _safe_resolve_config(overrides: dict | None = None):
    """Resolve config with user-friendly error for missing env vars."""
    try:
        return resolve_config(overrides)
    except ConfigEnvVarError as e:
        click.echo(f"Configuration error: {e}", err=True)
        raise SystemExit(1) from None


# -- CLI param name → dotted config key mapping --
_PARAM_MAP = {
    "provider": "embedding.provider",
    "model": "embedding.model",
    "batch_size": "embedding.batch_size",
    "base_url": "embedding.base_url",
    "api_key": "embedding.api_key",
    "collection": "milvus.collection",
    "milvus_uri": "milvus.uri",
    "milvus_token": "milvus.token",
    "llm_provider": "compact.llm_provider",
    "llm_model": "compact.llm_model",
    "prompt_file": "compact.prompt_file",
    "llm_base_url": "compact.base_url",
    "llm_api_key": "compact.api_key",
    "max_chunk_size": "chunking.max_chunk_size",
    "overlap_lines": "chunking.overlap_lines",
    "debounce_ms": "watch.debounce_ms",
    "reranker_model": "reranker.model",
}


def _build_cli_overrides(**kwargs) -> dict:
    """Map flat CLI params to a nested config override dict.

    Only non-None values are included (None means "not set by user").
    """
    result: dict = {}
    for param, dotted_key in _PARAM_MAP.items():
        val = kwargs.get(param)
        if val is None:
            continue
        section, field = dotted_key.split(".")
        result.setdefault(section, {})[field] = val
    return result


def _cfg_to_memsearch_kwargs(cfg: MemSearchConfig) -> dict:
    """Extract MemSearch constructor kwargs from a resolved config."""
    return {
        "embedding_provider": cfg.embedding.provider,
        "embedding_model": cfg.embedding.model or None,
        "embedding_batch_size": cfg.embedding.batch_size,
        "embedding_base_url": cfg.embedding.base_url or None,
        "embedding_api_key": cfg.embedding.api_key or None,
        "milvus_uri": cfg.milvus.uri,
        "milvus_token": cfg.milvus.token or None,
        "collection": cfg.milvus.collection,
        "max_chunk_size": cfg.chunking.max_chunk_size,
        "overlap_lines": cfg.chunking.overlap_lines,
        "reranker_model": cfg.reranker.model,
    }


def _graphiti_client_from_config(
    cfg: MemSearchConfig,
    *,
    endpoint: str | None = None,
    host_header: str | None = None,
    timeout_seconds: int | None = None,
):
    from .graphiti.client import GraphitiClient

    return GraphitiClient(
        endpoint or cfg.graphiti.endpoint,
        host_header=host_header if host_header is not None else cfg.graphiti.host_header,
        timeout_seconds=timeout_seconds or cfg.graphiti.request_timeout_seconds,
    )


def _search_curated_graph(client, query: str, *, group_id: str, limit: int) -> dict:
    from .graphiti.results import dedupe_graph_facts, select_graph_center_nodes, tune_graph_results

    nodes = client.search_nodes(query, group_id=group_id, limit=limit)
    raw_nodes = nodes.get("nodes", [])
    facts = client.search_memory_facts(query, group_id=group_id, limit=limit)
    raw_facts = list(facts.get("facts", []))
    for center_node in select_graph_center_nodes(query, raw_nodes, limit=2):
        centered = client.search_memory_facts(
            query,
            group_id=group_id,
            limit=limit,
            center_node_uuid=center_node["uuid"],
        )
        center_name = center_node.get("name") or center_node.get("uuid")
        raw_facts.extend({**fact, "graph_center_node": center_name} for fact in centered.get("facts", []))
    return tune_graph_results(
        query,
        dedupe_graph_facts(raw_facts),
        raw_nodes,
        limit=limit,
    )


def _load_graphiti_manifest(path: str) -> dict:
    manifest_path = Path(path).expanduser()
    if not manifest_path.is_file():
        return {"episodes": {}}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"episodes": {}}
    if not isinstance(data, dict):
        return {"episodes": {}}
    episodes = data.get("episodes")
    if not isinstance(episodes, dict):
        data["episodes"] = {}
    return data


def _save_graphiti_manifest(path: str, data: dict) -> None:
    manifest_path = Path(path).expanduser()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_compact_source(source: str | None) -> str | None:
    """Normalize compact --source paths to the absolute form used at index time.

    Relative and user-home paths are resolved to match the absolute `source`
    values stored during indexing. Non-path filters are left unchanged.
    """
    if not source:
        return None

    candidate = Path(source).expanduser()
    if candidate.is_absolute() or candidate.exists():
        return str(candidate.resolve())

    return source


def _plugin_summarize_config(cfg: MemSearchConfig, plugin: str) -> dict:
    """Return TOML-facing summarize config for a plugin platform."""
    plugins = config_to_dict(cfg).get("plugins", {})
    plugin_cfg = plugins.get(plugin)
    if not isinstance(plugin_cfg, dict):
        raise KeyError(f"Unknown plugin platform: {plugin}")
    summarize = plugin_cfg.get("summarize", {})
    if not isinstance(summarize, dict):
        return {}
    return summarize


def _load_plugin_summarize_prompt(cfg: MemSearchConfig, agent_name: str) -> str:
    """Load the plugin summarize prompt template."""
    if cfg.prompts.summarize:
        prompt_path = Path(cfg.prompts.summarize).expanduser()
        if prompt_path.is_file():
            return prompt_path.read_text(encoding="utf-8").replace("{{AGENT_NAME}}", agent_name)
    return (
        "You are a third-person note-taker. You will receive a transcript of ONE conversation turn "
        f"between User and {agent_name}.\n\n"
        "Record what happened as factual third-person notes. Output 2-10 bullet points, each starting with '- '. "
        "Use 'User' for the user. First bullet: what User asked or wanted. Remaining bullets: what was done, "
        f"found, changed, configured, tested, explained, decided, or could not be completed by {agent_name}. "
        "Mandatory language rule: write every bullet in the same primary language as the [User] text. "
        "If User mixes languages, use the dominant user-facing language. "
        "Be specific when useful: mention important files read or edited, searches or research performed, "
        "refactors, commands or tests run, key findings, and concrete outcomes. Prefer the final user-visible "
        "outcome over low-level transcript mechanics. Do NOT answer User's question yourself. Output ONLY "
        "bullet points."
    )


# -- Common CLI options --


def _common_options(f):
    """Shared options for commands that create a MemSearch instance."""
    f = click.option("--provider", "-p", default=None, help="Embedding provider.")(f)
    f = click.option("--model", "-m", default=None, help="Override embedding model.")(f)
    f = click.option("--batch-size", default=None, type=int, help="Embedding batch size (0 = provider default).")(f)
    f = click.option("--base-url", default=None, help="OpenAI-compatible API base URL.")(f)
    f = click.option("--api-key", default=None, help="API key for the embedding provider.")(f)
    f = click.option("--collection", "-c", default=None, help="Milvus collection name.")(f)
    f = click.option("--milvus-uri", default=None, help="Milvus connection URI.")(f)
    f = click.option("--milvus-token", default=None, help="Milvus auth token.")(f)
    return f


@click.group()
@click.version_option(package_name="memsearch")
def cli() -> None:
    """memsearch — semantic memory search for markdown knowledge bases."""


@cli.command()
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
@_common_options
@click.option("--force", is_flag=True, help="Re-index all files.")
@click.option("--no-prune", is_flag=True, help="Do not remove indexed sources outside PATHS.")
@click.option(
    "--max-chunk-size", default=None, type=click.IntRange(min=1), help="Max chunk size in characters (must be >= 1)."
)
@click.option("--description", default=None, help="Collection description (written on creation only).")
def index(
    paths: tuple[str, ...],
    provider: str | None,
    model: str | None,
    batch_size: int | None,
    base_url: str | None,
    api_key: str | None,
    collection: str | None,
    milvus_uri: str | None,
    milvus_token: str | None,
    force: bool,
    no_prune: bool,
    max_chunk_size: int | None,
    description: str | None,
) -> None:
    """Index markdown files from PATHS."""
    from .core import MemSearch

    cfg = _safe_resolve_config(
        _build_cli_overrides(
            provider=provider,
            model=model,
            batch_size=batch_size,
            base_url=base_url,
            api_key=api_key,
            collection=collection,
            milvus_uri=milvus_uri,
            milvus_token=milvus_token,
            max_chunk_size=max_chunk_size,
        )
    )
    ms = None
    try:
        ms = MemSearch(list(paths), **_cfg_to_memsearch_kwargs(cfg), description=description or "")
        n = _run(ms.index(force=force, prune=not no_prune))
        click.echo(f"Indexed {n} chunks.")
    except MilvusException as e:
        click.echo(f"Milvus error (code {e.code}): {e.message}", err=True)
        raise SystemExit(1) from None
    finally:
        if ms is not None:
            ms.close()


@cli.command()
@click.argument("query")
@click.option("--top-k", "-k", default=None, type=int, help="Number of results.")
@click.option(
    "--source-prefix",
    default=None,
    type=click.Path(),
    help="Only search chunks whose source path starts with this prefix.",
)
@_common_options
@click.option("--reranker-model", default=None, help="Cross-encoder model for reranking (empty string disables).")
@click.option(
    "--include-graph/--no-graph",
    default=True,
    help="Query the curated Graphiti sidecar, or disable it for vector-only search.",
)
@click.option("--graph-top-k", default=15, type=int, help="Number of graph facts and nodes to include.")
@click.option("--graph-group-id", default=None, help="Graphiti group ID for --include-graph.")
@click.option("--graph-endpoint", default=None, help="Graphiti MCP endpoint for --include-graph.")
@click.option("--graph-host-header", default=None, help="Override Host header for --include-graph.")
@click.option("--graph-timeout", "graph_timeout_seconds", default=None, type=int, help="Graph timeout in seconds.")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON.")
def search(
    query: str,
    top_k: int | None,
    source_prefix: str | None,
    provider: str | None,
    model: str | None,
    batch_size: int | None,
    base_url: str | None,
    api_key: str | None,
    collection: str | None,
    milvus_uri: str | None,
    milvus_token: str | None,
    reranker_model: str | None,
    include_graph: bool,
    graph_top_k: int,
    graph_group_id: str | None,
    graph_endpoint: str | None,
    graph_host_header: str | None,
    graph_timeout_seconds: int | None,
    json_output: bool,
) -> None:
    """Search indexed memory for QUERY."""
    from .core import MemSearch

    cfg = _safe_resolve_config(
        _build_cli_overrides(
            provider=provider,
            model=model,
            batch_size=batch_size,
            base_url=base_url,
            api_key=api_key,
            collection=collection,
            milvus_uri=milvus_uri,
            milvus_token=milvus_token,
            reranker_model=reranker_model,
        )
    )
    ms = None
    try:
        ms = MemSearch(**_cfg_to_memsearch_kwargs(cfg))
        results = _run(ms.search(query, top_k=top_k or 5, source_prefix=source_prefix))
        graph_result = None
        graph_error = None
        if include_graph:
            from .graphiti.client import GraphitiClientError
            from .graphiti.curated import CURATED_GROUP_ID

            try:
                client = _graphiti_client_from_config(
                    cfg,
                    endpoint=graph_endpoint,
                    host_header=graph_host_header,
                    timeout_seconds=graph_timeout_seconds,
                )
                effective_group_id = graph_group_id if graph_group_id is not None else CURATED_GROUP_ID
                graph_result = _search_curated_graph(
                    client,
                    query,
                    group_id=effective_group_id,
                    limit=graph_top_k,
                )
            except GraphitiClientError as e:
                graph_error = str(e)

        if json_output:
            if include_graph:
                output = {"vector": results, "graph": graph_result or {"facts": [], "nodes": []}}
                if graph_error:
                    output["graph_error"] = graph_error
                click.echo(json.dumps(output, indent=2, ensure_ascii=False))
            else:
                click.echo(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            if not results:
                click.echo("No results found.")
            else:
                for i, r in enumerate(results, 1):
                    score = r.get("score", 0)
                    source = r.get("source", "?")
                    heading = r.get("heading", "")
                    content = r.get("content", "")
                    click.echo(f"\n--- Result {i} (score: {score:.4f}) ---")
                    click.echo(f"Source: {source}")
                    if heading:
                        click.echo(f"Heading: {heading}")
                    if len(content) > 500:
                        click.echo(content[:500])
                        chunk_hash = r.get("chunk_hash", "")
                        click.echo(f"  ... [truncated, run 'memsearch expand {chunk_hash}' for full content]")
                    else:
                        click.echo(content)
            if include_graph:
                if graph_error:
                    click.echo(f"\nGraphiti unavailable; returned vector results only: {graph_error}", err=True)
                elif graph_result and (graph_result["facts"] or graph_result["nodes"]):
                    click.echo("\n--- Curated graph results ---")
                    if graph_result["facts"]:
                        click.echo("Facts:")
                        for fact in graph_result["facts"]:
                            click.echo(f"- {fact.get('fact') or fact.get('name') or fact.get('uuid')}")
                    if graph_result["nodes"]:
                        click.echo("Nodes:")
                        for node in graph_result["nodes"]:
                            summary = node.get("summary", "")
                            suffix = f" — {summary}" if summary else ""
                            click.echo(f"- {node.get('name') or node.get('uuid')}{suffix}")
    except MilvusException as e:
        click.echo(f"Milvus error (code {e.code}): {e.message}", err=True)
        raise SystemExit(1) from None
    finally:
        if ms is not None:
            ms.close()


@cli.command("graph-status")
@click.option("--endpoint", default=None, help="Graphiti MCP endpoint.")
@click.option("--host-header", default=None, help="Override Host header for localhost-protected Graphiti MCP routes.")
@click.option("--timeout", "timeout_seconds", default=None, type=int, help="Request timeout in seconds.")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON.")
def graph_status(
    endpoint: str | None,
    host_header: str | None,
    timeout_seconds: int | None,
    json_output: bool,
) -> None:
    """Check Graphiti MCP status."""
    from .graphiti.client import GraphitiClientError

    cfg = _safe_resolve_config()
    try:
        status = _graphiti_client_from_config(
            cfg,
            endpoint=endpoint,
            host_header=host_header,
            timeout_seconds=timeout_seconds,
        ).get_status()
    except GraphitiClientError as e:
        click.echo(f"Graphiti error: {e}", err=True)
        raise SystemExit(1) from None

    if json_output:
        click.echo(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        click.echo(status.get("message") or status.get("status") or json.dumps(status, ensure_ascii=False))


@cli.command("graph-search")
@click.argument("query")
@click.option("--top-k", "-k", default=5, type=int, help="Number of facts and nodes to return.")
@click.option("--group-id", default=None, help="Graphiti group ID.")
@click.option("--endpoint", default=None, help="Graphiti MCP endpoint.")
@click.option("--host-header", default=None, help="Override Host header for localhost-protected Graphiti MCP routes.")
@click.option("--timeout", "timeout_seconds", default=None, type=int, help="Request timeout in seconds.")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON.")
def graph_search(
    query: str,
    top_k: int,
    group_id: str | None,
    endpoint: str | None,
    host_header: str | None,
    timeout_seconds: int | None,
    json_output: bool,
) -> None:
    """Search Graphiti facts and nodes."""
    from .graphiti.client import GraphitiClientError

    cfg = _safe_resolve_config()
    client = _graphiti_client_from_config(
        cfg,
        endpoint=endpoint,
        host_header=host_header,
        timeout_seconds=timeout_seconds,
    )
    effective_group_id = group_id if group_id is not None else cfg.graphiti.group_id
    try:
        facts = client.search_memory_facts(query, group_id=effective_group_id, limit=top_k)
        nodes = client.search_nodes(query, group_id=effective_group_id, limit=top_k)
    except GraphitiClientError as e:
        click.echo(f"Graphiti error: {e}", err=True)
        raise SystemExit(1) from None

    result = {"facts": facts.get("facts", []), "nodes": nodes.get("nodes", [])}
    if json_output:
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if not result["facts"] and not result["nodes"]:
        click.echo("No graph results found.")
        return

    if result["facts"]:
        click.echo("Facts:")
        for fact in result["facts"]:
            click.echo(f"- {fact.get('fact') or fact.get('name') or fact.get('uuid')}")
    if result["nodes"]:
        click.echo("Nodes:")
        for node in result["nodes"]:
            summary = node.get("summary", "")
            suffix = f" — {summary}" if summary else ""
            click.echo(f"- {node.get('name') or node.get('uuid')}{suffix}")


@cli.command("graph-eval")
@click.option("--top-k", "-k", default=15, type=int, help="Number of vector and graph results per case.")
@click.option("--group-id", default=None, help="Graphiti group ID.")
@click.option("--endpoint", default=None, help="Graphiti MCP endpoint.")
@click.option("--host-header", default=None, help="Override Host header for localhost-protected Graphiti MCP routes.")
@click.option("--timeout", "timeout_seconds", default=None, type=int, help="Graph timeout in seconds.")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON.")
def graph_eval(
    top_k: int,
    group_id: str | None,
    endpoint: str | None,
    host_header: str | None,
    timeout_seconds: int | None,
    json_output: bool,
) -> None:
    """Run a small vector-vs-graph recall evaluation harness."""
    from .core import MemSearch
    from .graphiti.client import GraphitiClientError
    from .graphiti.curated import CURATED_GROUP_ID
    from .graphiti.evaluation import DEFAULT_GRAPH_EVALUATION_CASES, evaluate_payload

    cfg = _safe_resolve_config()
    ms = None
    evaluations = []
    try:
        ms = MemSearch(**_cfg_to_memsearch_kwargs(cfg))
        client = _graphiti_client_from_config(
            cfg,
            endpoint=endpoint,
            host_header=host_header,
            timeout_seconds=timeout_seconds,
        )
        effective_group_id = group_id if group_id is not None else CURATED_GROUP_ID
        for case in DEFAULT_GRAPH_EVALUATION_CASES:
            vector_results = _run(ms.search(case.query, top_k=top_k))
            payload: dict = {"vector": vector_results, "graph": {"facts": [], "nodes": []}}
            try:
                payload["graph"] = _search_curated_graph(
                    client,
                    case.query,
                    group_id=effective_group_id,
                    limit=top_k,
                )
            except GraphitiClientError as e:
                payload["graph_error"] = str(e)
            evaluations.append(evaluate_payload(case, payload))
    finally:
        if ms is not None:
            ms.close()

    passed = sum(1 for item in evaluations if item["passed"])
    output = {
        "passed": passed,
        "failed": len(evaluations) - passed,
        "cases": evaluations,
    }
    if json_output:
        click.echo(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        click.echo(f"Graph evaluation: {passed}/{len(evaluations)} passed")
        for item in evaluations:
            status = "PASS" if item["passed"] else "FAIL"
            click.echo(f"- {status} {item['name']}: {item['query']}")
            if item["graph_error"]:
                click.echo(f"  graph_error: {item['graph_error']}")
            if item["graph_unwanted_hits"]:
                click.echo(f"  unwanted graph hits: {', '.join(item['graph_unwanted_hits'])}")

    if passed != len(evaluations):
        raise SystemExit(1)


@cli.command("graph-index")
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--limit", default=None, type=int, help="Maximum number of new episodes to queue.")
@click.option("--group-id", default=None, help="Graphiti group ID.")
@click.option("--endpoint", default=None, help="Graphiti MCP endpoint.")
@click.option("--host-header", default=None, help="Override Host header for localhost-protected Graphiti MCP routes.")
@click.option("--timeout", "timeout_seconds", default=None, type=int, help="Request timeout in seconds.")
@click.option("--force", is_flag=True, help="Queue episodes even if their content hash is already in the manifest.")
@click.option("--dry-run", is_flag=True, help="Build episodes and show counts without calling Graphiti.")
def graph_index(
    paths: tuple[str, ...],
    limit: int | None,
    group_id: str | None,
    endpoint: str | None,
    host_header: str | None,
    timeout_seconds: int | None,
    force: bool,
    dry_run: bool,
) -> None:
    """Index markdown files into Graphiti as episodes."""
    from .graphiti.client import GraphitiClientError
    from .graphiti.episodes import build_episodes
    from .scanner import scan_paths

    cfg = _safe_resolve_config()
    files = scan_paths(list(paths))
    manifest = _load_graphiti_manifest(cfg.graphiti.manifest_path)
    seen = manifest["episodes"]
    episodes = list(build_episodes(file.path for file in files))
    pending = [episode for episode in episodes if force or episode.content_hash not in seen]
    if limit is not None:
        pending = pending[:limit]

    if dry_run:
        click.echo(f"Found {len(files)} markdown files, {len(episodes)} episodes, {len(pending)} pending.")
        return

    client = _graphiti_client_from_config(
        cfg,
        endpoint=endpoint,
        host_header=host_header,
        timeout_seconds=timeout_seconds,
    )
    effective_group_id = group_id if group_id is not None else cfg.graphiti.group_id
    queued = 0
    try:
        for episode in pending:
            client.add_memory(episode, group_id=effective_group_id)
            seen[episode.content_hash] = {
                "name": episode.name,
                "source": episode.metadata.get("source", ""),
                "group_id": effective_group_id,
                "queued_at": datetime.now(UTC).isoformat(),
            }
            queued += 1
    except GraphitiClientError as e:
        _save_graphiti_manifest(cfg.graphiti.manifest_path, manifest)
        click.echo(f"Graphiti error after queuing {queued} episode(s): {e}", err=True)
        raise SystemExit(1) from None

    _save_graphiti_manifest(cfg.graphiti.manifest_path, manifest)
    skipped = len(episodes) - len(pending) if not force else 0
    click.echo(f"Queued {queued} Graphiti episode(s). Skipped {skipped} unchanged episode(s).")


@cli.command("graph-index-curated")
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--limit", default=None, type=int, help="Maximum number of new curated episodes to queue.")
@click.option("--group-id", default=None, help="Graphiti group ID.")
@click.option("--manifest-path", default=None, help="Curated Graphiti manifest path.")
@click.option("--endpoint", default=None, help="Graphiti MCP endpoint.")
@click.option("--host-header", default=None, help="Override Host header for localhost-protected Graphiti MCP routes.")
@click.option("--timeout", "timeout_seconds", default=None, type=int, help="Request timeout in seconds.")
@click.option("--force", is_flag=True, help="Queue episodes even if their content hash is already in the manifest.")
@click.option("--dry-run", is_flag=True, help="Build curated episodes and show counts without calling Graphiti.")
def graph_index_curated(
    paths: tuple[str, ...],
    limit: int | None,
    group_id: str | None,
    manifest_path: str | None,
    endpoint: str | None,
    host_header: str | None,
    timeout_seconds: int | None,
    force: bool,
    dry_run: bool,
) -> None:
    """Index only curated durable memory sources into Graphiti."""
    from .graphiti.client import GraphitiClientError
    from .graphiti.curated import CURATED_GROUP_ID, CURATED_MANIFEST_PATH, build_curated_episodes
    from .scanner import scan_paths

    if not dry_run and limit is None:
        click.echo("Refusing uncapped curated Graphiti ingestion. Re-run with --dry-run first, then a --limit cap.", err=True)
        raise SystemExit(1) from None

    cfg = _safe_resolve_config()
    files = scan_paths(list(paths))
    episodes, selection = build_curated_episodes(file.path for file in files)
    effective_manifest_path = manifest_path or CURATED_MANIFEST_PATH
    manifest = _load_graphiti_manifest(effective_manifest_path)
    seen = manifest["episodes"]
    uncapped_pending = [episode for episode in episodes if force or episode.content_hash not in seen]
    pending = uncapped_pending
    if limit is not None:
        pending = pending[:limit]

    if dry_run:
        click.echo(
            "Curated Graphiti dry-run: "
            f"{len(files)} scanned, {len(selection.selected)} selected, {len(selection.excluded)} excluded, "
            f"{len(episodes)} episodes, {len(pending)} pending."
        )
        click.echo(f"Group: {group_id or CURATED_GROUP_ID}")
        click.echo(f"Manifest: {effective_manifest_path}")
        return

    client = _graphiti_client_from_config(
        cfg,
        endpoint=endpoint,
        host_header=host_header,
        timeout_seconds=timeout_seconds,
    )
    effective_group_id = group_id if group_id is not None else CURATED_GROUP_ID
    queued = 0
    try:
        for episode in pending:
            client.add_memory(episode, group_id=effective_group_id)
            seen[episode.content_hash] = {
                "name": episode.name,
                "source": episode.metadata.get("source", ""),
                "group_id": effective_group_id,
                "queued_at": datetime.now(UTC).isoformat(),
            }
            queued += 1
    except GraphitiClientError as e:
        _save_graphiti_manifest(effective_manifest_path, manifest)
        click.echo(f"Graphiti error after queuing {queued} curated episode(s): {e}", err=True)
        raise SystemExit(1) from None

    _save_graphiti_manifest(effective_manifest_path, manifest)
    skipped = len(episodes) - len(uncapped_pending) if not force else 0
    deferred = len(uncapped_pending) - len(pending)
    summary = f"Queued {queued} curated Graphiti episode(s). Skipped {skipped} unchanged episode(s)."
    if deferred:
        summary += f" Deferred {deferred} episode(s) by limit."
    click.echo(summary)
    click.echo(f"Group: {effective_group_id}")
    click.echo(f"Manifest: {effective_manifest_path}")


@cli.command("graph-watchdog")
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--execute", is_flag=True, default=False)
@click.option("--state-path", type=click.Path(path_type=Path), default=None)
@click.option("--json-output", is_flag=True, default=False)
def graph_watchdog(dry_run: bool, execute: bool, state_path: Path | None, json_output: bool) -> None:
    """Check Graphiti/FalkorDB health and optionally run narrow recovery."""
    from dataclasses import asdict

    from .graphiti import watchdog

    if dry_run and execute:
        raise click.ClickException("Use --dry-run or --execute, not both")

    checks = watchdog.collect_checks()
    decision = watchdog.decide_recovery(checks)
    previous_failures = _read_watchdog_failures(state_path)
    current_failures = 0 if decision.action == "noop" else previous_failures + 1
    alert_required = current_failures >= 3
    recovery_results: list[dict[str, object]] = []

    if execute and decision.commands:
        try:
            recovery_results = watchdog.run_recovery_commands(decision.commands) or []
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        failed_recovery = [item for item in recovery_results if item.get("returncode") != 0]
        if failed_recovery:
            _write_watchdog_state(state_path, current_failures, alert_required, decision)
            raise click.ClickException("Graphiti recovery command failed")

    payload = {
        "checks": [asdict(check) for check in checks],
        "decision": asdict(decision),
        "dry_run": dry_run or not execute,
        "executed": bool(execute and decision.commands),
        "recovery_results": recovery_results,
        "consecutive_failures": current_failures,
        "alert_required": alert_required,
    }
    if alert_required:
        payload["alert_reason"] = f"Graphiti watchdog has seen {current_failures} consecutive failure(s)"

    _write_watchdog_state(state_path, current_failures, alert_required, decision)

    if json_output:
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    click.echo(f"Graphiti watchdog: {decision.action} ({decision.reason})")
    if alert_required:
        click.echo(payload["alert_reason"])


@cli.command("graph-candidate-report")
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--output", type=click.Path(path_type=Path), required=True)
def graph_candidate_report(paths: tuple[Path, ...], output: Path) -> None:
    """Write a non-mutating reviewed-candidate report for Graphiti seeds."""
    from .graphiti.candidates import CandidateStatus, build_candidate_report, render_candidate_report

    report = build_candidate_report(paths)
    invalid_accepted = [
        item for item in report.accepted if item.status != CandidateStatus.ACCEPTED or item.classification != "current"
    ]
    if invalid_accepted:
        raise click.ClickException("accepted Graphiti candidates must be current and evidence-backed")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_candidate_report(report), encoding="utf-8")
    click.echo(f"Wrote Graphiti candidate report: {output}")


@cli.command("graph-clear-group")
@click.option("--group-id", required=True)
@click.option("--confirm-group-id", required=True)
@click.option("--execute", is_flag=True)
@click.option("--endpoint", default=None, help="Graphiti MCP endpoint.")
@click.option("--host-header", default=None, help="Override Host header for localhost-protected Graphiti MCP routes.")
@click.option("--timeout", "timeout_seconds", default=None, type=int, help="Request timeout in seconds.")
def graph_clear_group(
    group_id: str,
    confirm_group_id: str,
    execute: bool,
    endpoint: str | None,
    host_header: str | None,
    timeout_seconds: int | None,
) -> None:
    """Clear one explicitly confirmed Graphiti group."""
    if group_id.strip() in {"", "*", "all"}:
        raise click.ClickException("Refusing broad Graphiti group clear")
    if confirm_group_id != group_id:
        raise click.ClickException("Graphiti group confirmation does not match")

    cfg = _safe_resolve_config()
    effective_endpoint = endpoint or cfg.graphiti.endpoint
    click.echo(f"Endpoint: {effective_endpoint}")
    click.echo(f"Group: {group_id}")
    if not execute:
        click.echo("Dry-run only. Re-run with --execute to clear this group.")
        return

    client = _graphiti_client_from_config(
        cfg,
        endpoint=endpoint,
        host_header=host_header,
        timeout_seconds=timeout_seconds,
    )
    result = client.clear_graph(group_id=group_id)
    click.echo(json.dumps(result, indent=2, ensure_ascii=False))


@cli.command("graph-backup")
@click.option("--backup-root", type=click.Path(path_type=Path), default=Path("/Volumes/SSD/graphiti-mon316/backups"))
@click.option("--execute", is_flag=True)
@click.option("--retain-days", type=int, default=30)
@click.option("--prune-to-trash", is_flag=True)
def graph_backup(backup_root: Path, execute: bool, retain_days: int, prune_to_trash: bool) -> None:
    """Create a non-destructive FalkorDB backup for the Graphiti sidecar."""
    from .graphiti.backup import backup_dry_run, run_backup

    if not execute:
        click.echo(backup_dry_run(backup_root))
        return
    try:
        result = run_backup(root=backup_root, retain_days=retain_days, prune_to_trash=prune_to_trash)
    except (RuntimeError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Backup path: {result.path}")


def _read_watchdog_failures(state_path: Path | None) -> int:
    if state_path is None or not state_path.is_file():
        return 0
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    value = data.get("consecutive_failures")
    return value if isinstance(value, int) and value >= 0 else 0


def _write_watchdog_state(
    state_path: Path | None,
    consecutive_failures: int,
    alert_required: bool,
    decision,
) -> None:
    if state_path is None:
        return
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "consecutive_failures": consecutive_failures,
        "alert_required": alert_required,
        "decision": {
            "action": decision.action,
            "reason": decision.reason,
            "commands": list(decision.commands),
        },
        "updated_at": datetime.now(UTC).isoformat(),
    }
    if alert_required:
        state["alert_reason"] = f"Graphiti watchdog has seen {consecutive_failures} consecutive failure(s)"
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


# ======================================================================
# Expand command (progressive disclosure L2)
#
# Shows the full heading section around a chunk, used by the Claude Code
# plugin's progressive disclosure workflow:
#   L1: `search` returns chunk snippets
#   L2: `expand` shows the full heading section around a chunk
#
# Works with memsearch's anchor comments embedded in memory files:
#   <!-- session:UUID turn:UUID transcript:PATH -->
# ======================================================================


@cli.command()
@click.argument("chunk_hash")
@click.option("--section/--no-section", default=True, help="Show full heading section (default).")
@click.option("--lines", "-n", default=None, type=int, help="Show N lines before/after instead of full section.")
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON.")
@_common_options
def expand(
    chunk_hash: str,
    section: bool,
    lines: int | None,
    json_output: bool,
    provider: str | None,
    model: str | None,
    batch_size: int | None,
    base_url: str | None,
    api_key: str | None,
    collection: str | None,
    milvus_uri: str | None,
    milvus_token: str | None,
) -> None:
    """Expand a memory chunk to show full context. [Claude Code plugin: L2]

    Look up CHUNK_HASH in the index, then read the source markdown file
    to return the surrounding context (full heading section by default).

    Part of the progressive disclosure workflow (search -> expand -> transcript).
    """
    from .store import MilvusStore

    cfg = _safe_resolve_config(
        _build_cli_overrides(
            provider=provider,
            model=model,
            batch_size=batch_size,
            base_url=base_url,
            api_key=api_key,
            collection=collection,
            milvus_uri=milvus_uri,
            milvus_token=milvus_token,
        )
    )
    store = None
    try:
        store = MilvusStore(
            uri=cfg.milvus.uri,
            token=cfg.milvus.token or None,
            collection=cfg.milvus.collection,
            dimension=None,
        )
        chunks = store.query(filter_expr=f'chunk_hash == "{chunk_hash}"')
        if not chunks:
            click.echo(f"Chunk not found: {chunk_hash}", err=True)
            sys.exit(1)

        chunk = chunks[0]
        source = chunk["source"]
        start_line = chunk["start_line"]
        end_line = chunk["end_line"]
        heading = chunk.get("heading", "")
        heading_level = chunk.get("heading_level", 0)

        source_path = Path(source)
        if not source_path.exists():
            click.echo(f"Source file not found: {source}", err=True)
            sys.exit(1)

        all_lines = read_utf8_text_replace(source_path).splitlines()

        if lines is not None:
            # Show N lines before/after the chunk
            ctx_start = max(0, start_line - 1 - lines)
            ctx_end = min(len(all_lines), end_line + lines)
            expanded = "\n".join(all_lines[ctx_start:ctx_end])
            expanded_start = ctx_start + 1
            expanded_end = ctx_end
        else:
            # Show full section under the same heading
            expanded, expanded_start, expanded_end = _extract_section(
                all_lines,
                start_line,
                heading_level,
            )

        # Parse any anchor comments in the expanded text
        import re

        anchor_match = re.search(
            r"<!--\s*session:(\S+)\s+turn:(\S+)\s+transcript:(\S+)\s*-->",
            expanded,
        )
        anchor = {}
        if anchor_match:
            anchor = {
                "session": anchor_match.group(1),
                "turn": anchor_match.group(2),
                "transcript": anchor_match.group(3),
            }

        if json_output:
            result = {
                "chunk_hash": chunk_hash,
                "source": source,
                "heading": heading,
                "start_line": expanded_start,
                "end_line": expanded_end,
                "content": expanded,
            }
            if anchor:
                result["anchor"] = anchor
            click.echo(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            click.echo(f"Source: {source} (lines {expanded_start}-{expanded_end})")
            if heading:
                click.echo(f"Heading: {heading}")
            if anchor:
                click.echo(f"Session: {anchor['session']}  Turn: {anchor['turn']}")
                click.echo(f"Transcript: {anchor['transcript']}")
            click.echo(f"\n{expanded}")
    except MilvusException as e:
        click.echo(f"Milvus error (code {e.code}): {e.message}", err=True)
        raise SystemExit(1) from None
    finally:
        if store is not None:
            store.close()


def _extract_section(
    all_lines: list[str],
    start_line: int,
    heading_level: int,
) -> tuple[str, int, int]:
    """Extract the full section containing the chunk.

    Walks backward to find the section heading, then forward to the next
    heading of equal or higher level (or EOF).
    """
    # Find section start — walk backward to the heading
    section_start = start_line - 1  # 0-indexed
    if heading_level > 0:
        for i in range(start_line - 2, -1, -1):
            line = all_lines[i]
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                if level <= heading_level:
                    section_start = i
                    break

    # Find section end — walk forward to the next heading of same or higher level
    section_end = len(all_lines)
    if heading_level > 0:
        for i in range(start_line, len(all_lines)):
            line = all_lines[i]
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                if level <= heading_level:
                    section_end = i
                    break

    content = "\n".join(all_lines[section_start:section_end])
    return content, section_start + 1, section_end


@cli.command()
@click.argument("paths", nargs=-1, required=True, type=click.Path(exists=True))
@_common_options
@click.option("--debounce-ms", default=None, type=int, help="Debounce delay in ms.")
@click.option(
    "--max-chunk-size", default=None, type=click.IntRange(min=1), help="Max chunk size in characters (must be >= 1)."
)
@click.option("--description", default=None, help="Collection description (written on creation only).")
def watch(
    paths: tuple[str, ...],
    provider: str | None,
    model: str | None,
    batch_size: int | None,
    base_url: str | None,
    api_key: str | None,
    collection: str | None,
    milvus_uri: str | None,
    milvus_token: str | None,
    debounce_ms: int | None,
    max_chunk_size: int | None,
    description: str | None,
) -> None:
    """Watch PATHS for markdown changes and auto-index."""
    from .core import MemSearch

    cfg = _safe_resolve_config(
        _build_cli_overrides(
            provider=provider,
            model=model,
            batch_size=batch_size,
            base_url=base_url,
            api_key=api_key,
            collection=collection,
            milvus_uri=milvus_uri,
            milvus_token=milvus_token,
            debounce_ms=debounce_ms,
            max_chunk_size=max_chunk_size,
        )
    )
    ms = None
    watcher = None
    try:
        ms = MemSearch(list(paths), **_cfg_to_memsearch_kwargs(cfg), description=description or "")

        # Initial index: ensure existing files are indexed before watching
        n = _run(ms.index())
        if n:
            click.echo(f"Indexed {n} chunks.")

        def _on_event(event_type: str, summary: str, file_path) -> None:
            click.echo(summary)

        click.echo(f"Watching {len(paths)} path(s) for changes... (Ctrl+C to stop)")
        watcher = ms.watch(on_event=_on_event, debounce_ms=cfg.watch.debounce_ms)
        while True:
            import time

            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("\nStopping watcher.")
    except MilvusException as e:
        click.echo(f"Milvus error (code {e.code}): {e.message}", err=True)
        raise SystemExit(1) from None
    finally:
        if watcher is not None:
            watcher.stop()
        if ms is not None:
            ms.close()


@cli.command()
@click.option("--source", "-s", default=None, help="Only compact chunks from this source.")
@click.option(
    "--output-dir", "-o", default=None, type=click.Path(), help="Directory to write the compact summary into."
)
@click.option("--llm-provider", default=None, help="LLM for summarization.")
@click.option("--llm-model", default=None, help="Override LLM model.")
@click.option("--llm-base-url", default=None, help="OpenAI-compatible base URL for the LLM.")
@click.option("--llm-api-key", default=None, help="API key for the LLM provider.")
@click.option("--prompt", default=None, help="Custom prompt template (must contain {chunks}).")
@click.option("--prompt-file", default=None, type=click.Path(exists=True), help="Read prompt template from file.")
@_common_options
def compact(
    source: str | None,
    output_dir: str | None,
    llm_provider: str | None,
    llm_model: str | None,
    llm_base_url: str | None,
    llm_api_key: str | None,
    prompt: str | None,
    prompt_file: str | None,
    provider: str | None,
    model: str | None,
    batch_size: int | None,
    base_url: str | None,
    api_key: str | None,
    collection: str | None,
    milvus_uri: str | None,
    milvus_token: str | None,
) -> None:
    """Compress stored memories into a summary."""
    from .core import MemSearch

    cfg = _safe_resolve_config(
        _build_cli_overrides(
            provider=provider,
            model=model,
            batch_size=batch_size,
            base_url=base_url,
            api_key=api_key,
            collection=collection,
            milvus_uri=milvus_uri,
            milvus_token=milvus_token,
            llm_provider=llm_provider,
            llm_model=llm_model,
            prompt_file=prompt_file,
            llm_base_url=llm_base_url,
            llm_api_key=llm_api_key,
        )
    )

    prompt_template = prompt
    # Resolve prompt: CLI --prompt > prompts.compact > compact.prompt_file > built-in
    if not prompt_template and cfg.prompts.compact:
        prompt_template = Path(cfg.prompts.compact).expanduser().read_text(encoding="utf-8")
    if not prompt_template and cfg.compact.prompt_file:
        prompt_template = Path(cfg.compact.prompt_file).read_text(encoding="utf-8")

    # Resolve LLM settings: [llm] > [compact] (deprecated) > defaults
    eff_provider = cfg.llm.provider or cfg.compact.llm_provider
    eff_model = cfg.llm.model or cfg.compact.llm_model or None
    eff_base_url = cfg.llm.base_url or cfg.compact.base_url or None
    eff_api_key = cfg.llm.api_key or cfg.compact.api_key or None

    normalized_source = _normalize_compact_source(source)

    ms = None
    try:
        ms = MemSearch(**_cfg_to_memsearch_kwargs(cfg))
        summary = _run(
            ms.compact(
                source=normalized_source,
                llm_provider=eff_provider,
                llm_model=eff_model,
                prompt_template=prompt_template,
                output_dir=output_dir,
                llm_base_url=eff_base_url,
                llm_api_key=eff_api_key,
            )
        )
        if summary:
            click.echo("Compact complete. Summary:\n")
            click.echo(summary)
        elif normalized_source:
            click.echo(f"No chunks matched source: {normalized_source}")
        else:
            click.echo("No chunks to compact.")
    except MilvusException as e:
        click.echo(f"Milvus error (code {e.code}): {e.message}", err=True)
        raise SystemExit(1) from None
    finally:
        if ms is not None:
            ms.close()


@cli.command()
@click.option("--plugin", required=True, help="Plugin platform name (claude-code, codex, opencode, openclaw).")
@click.option("--agent-name", default="", help="Agent display name for the summarize prompt.")
def summarize(plugin: str, agent_name: str) -> None:
    """Summarize stdin using a configured memsearch-managed LLM provider."""
    from .compact import summarize_text

    cfg = _safe_resolve_config()
    summarize_cfg = _plugin_summarize_config(cfg, plugin)
    provider_name = str(summarize_cfg.get("provider") or "").strip()
    if not provider_name or provider_name == "native":
        click.echo(
            f"Plugin {plugin!r} is configured for native summarization; no memsearch-managed provider selected.",
            err=True,
        )
        raise SystemExit(2)

    provider_cfg = cfg.llm.providers.get(provider_name)
    if provider_cfg is None:
        click.echo(f"Unknown LLM provider {provider_name!r}. Configure [llm.providers.{provider_name}].", err=True)
        raise SystemExit(1)

    provider_type = provider_cfg.type or provider_name
    model = str(summarize_cfg.get("model") or provider_cfg.model or "").strip() or None
    transcript = sys.stdin.read()
    if not transcript.strip():
        return

    prompt_agent_name = agent_name or plugin
    system_prompt = _load_plugin_summarize_prompt(cfg, prompt_agent_name)
    prompt = f"{system_prompt}\n\nTranscript:\n{transcript}"
    try:
        summary = _run(
            summarize_text(
                prompt,
                llm_provider=provider_type,
                model=model,
                base_url=provider_cfg.base_url or None,
                api_key=provider_cfg.api_key or None,
            )
        )
    except (ConfigEnvVarError, ValueError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1) from None

    if summary:
        click.echo(summary)


@cli.command()
@click.option("--collection", "-c", default=None, help="Milvus collection name.")
@click.option("--milvus-uri", default=None, help="Milvus connection URI.")
@click.option("--milvus-token", default=None, help="Milvus auth token.")
def stats(
    collection: str | None,
    milvus_uri: str | None,
    milvus_token: str | None,
) -> None:
    """Show statistics about the index."""
    from .store import MilvusStore

    cfg = _safe_resolve_config(
        _build_cli_overrides(
            collection=collection,
            milvus_uri=milvus_uri,
            milvus_token=milvus_token,
        )
    )
    store = None
    try:
        store = MilvusStore(
            uri=cfg.milvus.uri,
            token=cfg.milvus.token or None,
            collection=cfg.milvus.collection,
            dimension=None,
        )
        count = store.count()
        click.echo(f"Total indexed chunks: {count}")
    except MilvusException as e:
        click.echo(f"Milvus error (code {e.code}): {e.message}", err=True)
        raise SystemExit(1) from None
    finally:
        if store is not None:
            store.close()


@cli.command()
@click.option("--collection", "-c", default=None, help="Milvus collection name.")
@click.option("--milvus-uri", default=None, help="Milvus connection URI.")
@click.option("--milvus-token", default=None, help="Milvus auth token.")
@click.confirmation_option(prompt="This will delete all indexed data. Continue?")
def reset(
    collection: str | None,
    milvus_uri: str | None,
    milvus_token: str | None,
) -> None:
    """Drop all indexed data."""
    from .store import MilvusStore

    cfg = _safe_resolve_config(
        _build_cli_overrides(
            collection=collection,
            milvus_uri=milvus_uri,
            milvus_token=milvus_token,
        )
    )
    store = None
    try:
        store = MilvusStore(
            uri=cfg.milvus.uri,
            token=cfg.milvus.token or None,
            collection=cfg.milvus.collection,
            dimension=None,
        )
        store.drop()
        click.echo("Dropped collection.")
    except MilvusException as e:
        click.echo(f"Milvus error (code {e.code}): {e.message}", err=True)
        raise SystemExit(1) from None
    finally:
        if store is not None:
            store.close()


# ======================================================================
# Config command group
# ======================================================================


@cli.group("config")
def config_group() -> None:
    """Manage memsearch configuration."""


@config_group.command("init")
@click.option("--project", is_flag=True, help="Write to .memsearch.toml (project-level) instead of global.")
def config_init(project: bool) -> None:
    """Interactive configuration wizard."""

    target = PROJECT_CONFIG_PATH if project else GLOBAL_CONFIG_PATH
    load_config_file(target)
    current = resolve_config()

    result: dict = {}

    click.echo("memsearch configuration wizard")
    click.echo(f"Writing to: {target}\n")

    # Milvus
    click.echo("── Milvus ──")
    result["milvus"] = {}
    result["milvus"]["uri"] = click.prompt(
        "  Milvus URI",
        default=current.milvus.uri,
    )
    result["milvus"]["token"] = click.prompt(
        "  Milvus token (empty for none)",
        default=current.milvus.token,
    )
    result["milvus"]["collection"] = click.prompt(
        "  Collection name",
        default=current.milvus.collection,
    )

    # Embedding
    click.echo("\n── Embedding ──")
    result["embedding"] = {}
    _embedding_defaults = {
        "openai": "text-embedding-3-small",
        "google": "gemini-embedding-001",
        "voyage": "voyage-3-lite",
        "jina": "jina-embeddings-v4",
        "mistral": "mistral-embed",
        "ollama": "nomic-embed-text",
        "local": "all-MiniLM-L6-v2",
        "onnx": "gpahal/bge-m3-onnx-int8",
    }
    result["embedding"]["provider"] = click.prompt(
        "  Provider (openai/google/voyage/jina/mistral/ollama/local/onnx)",
        default=current.embedding.provider,
    )
    _emb_provider = result["embedding"]["provider"]
    _emb_model_default = current.embedding.model or _embedding_defaults.get(_emb_provider, "")
    result["embedding"]["model"] = click.prompt(
        "  Model",
        default=_emb_model_default,
    )
    result["embedding"]["base_url"] = click.prompt(
        "  Base URL (empty for default, or env:VAR_NAME)",
        default=current.embedding.base_url,
    )
    result["embedding"]["api_key"] = click.prompt(
        "  API key (empty for env default, or env:VAR_NAME)",
        default=current.embedding.api_key,
    )

    # Chunking
    click.echo("\n── Chunking ──")
    result["chunking"] = {}
    result["chunking"]["max_chunk_size"] = click.prompt(
        "  Max chunk size (chars)",
        default=current.chunking.max_chunk_size,
        type=int,
    )
    result["chunking"]["overlap_lines"] = click.prompt(
        "  Overlap lines",
        default=current.chunking.overlap_lines,
        type=int,
    )

    # Watch
    click.echo("\n── Watch ──")
    result["watch"] = {}
    result["watch"]["debounce_ms"] = click.prompt(
        "  Debounce (ms)",
        default=current.watch.debounce_ms,
        type=int,
    )

    # LLM
    click.echo("\n── LLM (for memsearch compact) ──")
    click.echo("  Plugin summarization uses plugins.<platform>.summarize.model.")
    _llm_defaults = {
        "openai": "gpt-5-mini",
        "anthropic": "claude-sonnet-4-6",
        "gemini": "gemini-3-flash-preview",
    }
    result["llm"] = {}
    result["llm"]["provider"] = click.prompt(
        "  Provider (empty/openai/anthropic/gemini)",
        default=current.llm.provider,
    )
    _llm_provider = result["llm"]["provider"]
    _llm_model_default = current.llm.model or _llm_defaults.get(_llm_provider, "")
    result["llm"]["model"] = click.prompt(
        "  Model",
        default=_llm_model_default,
    )
    result["llm"]["base_url"] = click.prompt(
        "  Base URL (empty for default, or env:VAR_NAME)",
        default=current.llm.base_url,
    )
    result["llm"]["api_key"] = click.prompt(
        "  API key (empty for env default, or env:VAR_NAME)",
        default=current.llm.api_key,
    )

    # Plugin summarize model overrides
    click.echo("\n── Plugin summarize routing ──")
    click.echo("  Leave provider empty/native to keep each plugin's current native summarizer.")
    result["plugins"] = {
        "claude-code": {"summarize": {}, "project_review": {}, "user_profile": {}},
        "codex": {"summarize": {}, "project_review": {}, "user_profile": {}},
        "opencode": {"summarize": {}, "project_review": {}, "user_profile": {}},
        "openclaw": {"summarize": {}, "project_review": {}, "user_profile": {}},
    }
    result["plugins"]["claude-code"]["summarize"]["enabled"] = click.confirm(
        "  Claude Code automatic summaries enabled",
        default=current.plugins.claude_code.summarize.enabled,
    )
    result["plugins"]["claude-code"]["summarize"]["provider"] = click.prompt(
        "  Claude Code summarize provider",
        default=current.plugins.claude_code.summarize.provider,
    )
    result["plugins"]["claude-code"]["summarize"]["model"] = click.prompt(
        "  Claude Code summarize model",
        default=current.plugins.claude_code.summarize.model,
    )
    result["plugins"]["codex"]["summarize"]["enabled"] = click.confirm(
        "  Codex automatic summaries enabled",
        default=current.plugins.codex.summarize.enabled,
    )
    result["plugins"]["codex"]["summarize"]["provider"] = click.prompt(
        "  Codex summarize provider",
        default=current.plugins.codex.summarize.provider,
    )
    result["plugins"]["codex"]["summarize"]["model"] = click.prompt(
        "  Codex summarize model",
        default=current.plugins.codex.summarize.model,
    )
    result["plugins"]["opencode"]["summarize"]["enabled"] = click.confirm(
        "  OpenCode automatic summaries enabled",
        default=current.plugins.opencode.summarize.enabled,
    )
    result["plugins"]["opencode"]["summarize"]["provider"] = click.prompt(
        "  OpenCode summarize provider",
        default=current.plugins.opencode.summarize.provider,
    )
    result["plugins"]["opencode"]["summarize"]["model"] = click.prompt(
        "  OpenCode summarize model",
        default=current.plugins.opencode.summarize.model,
    )
    result["plugins"]["openclaw"]["summarize"]["enabled"] = click.confirm(
        "  OpenClaw automatic summaries enabled",
        default=current.plugins.openclaw.summarize.enabled,
    )
    result["plugins"]["openclaw"]["summarize"]["provider"] = click.prompt(
        "  OpenClaw summarize provider",
        default=current.plugins.openclaw.summarize.provider,
    )
    result["plugins"]["openclaw"]["summarize"]["model"] = click.prompt(
        "  OpenClaw summarize model",
        default=current.plugins.openclaw.summarize.model,
    )

    click.echo("\n── Advanced maintenance ──")
    click.echo("  Disabled by default. Configure provider/model if you enable these tasks.")
    for key, label, current_platform in [
        ("claude-code", "Claude Code", current.plugins.claude_code),
        ("codex", "Codex", current.plugins.codex),
        ("opencode", "OpenCode", current.plugins.opencode),
        ("openclaw", "OpenClaw", current.plugins.openclaw),
    ]:
        for task_name, task_label in [("project_review", "project review"), ("user_profile", "user profile")]:
            task = getattr(current_platform, task_name)
            section = result["plugins"][key][task_name]
            section["enabled"] = click.confirm(f"  {label} {task_label} enabled", default=task.enabled)
            section["provider"] = click.prompt(f"  {label} {task_label} provider", default=task.provider)
            section["model"] = click.prompt(f"  {label} {task_label} model", default=task.model)
            section["min_interval_hours"] = click.prompt(
                f"  {label} {task_label} min interval hours",
                default=task.min_interval_hours,
                type=int,
            )
            section["input_dir"] = click.prompt(f"  {label} {task_label} input dir", default=task.input_dir)
            section["output_file"] = click.prompt(f"  {label} {task_label} output file", default=task.output_file)

    # Prompts
    click.echo("\n── Prompts ──")
    click.echo("  Leave empty to use built-in defaults.")
    result["prompts"] = {}
    result["prompts"]["compact"] = click.prompt(
        "  Compact prompt file",
        default=current.prompts.compact,
    )
    result["prompts"]["summarize"] = click.prompt(
        "  Summarize prompt file (for plugin session notes)",
        default=current.prompts.summarize,
    )
    result["prompts"]["project_review"] = click.prompt(
        "  Project review prompt file",
        default=current.prompts.project_review,
    )
    result["prompts"]["user_profile"] = click.prompt(
        "  User profile prompt file",
        default=current.prompts.user_profile,
    )

    save_config(result, target)
    click.echo(f"\nConfig saved to {target}")


@config_group.command("set")
@click.argument("key")
@click.argument("value")
@click.option("--project", is_flag=True, help="Write to project config.")
def config_set(key: str, value: str, project: bool) -> None:
    """Set a config value (e.g. memsearch config set milvus.uri http://host:19530)."""
    try:
        set_config_value(key, value, project=project)
        target = PROJECT_CONFIG_PATH if project else GLOBAL_CONFIG_PATH
        click.echo(f"Set {key} = {value} in {target}")
    except (KeyError, ValueError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@config_group.command("get")
@click.argument("key")
def config_get(key: str) -> None:
    """Get a resolved config value (e.g. memsearch config get milvus.uri)."""
    try:
        val = get_config_value(key)
        click.echo(val)
    except KeyError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@config_group.command("list")
@click.option("--resolved", "mode", flag_value="resolved", default=True, help="Show fully resolved config (default).")
@click.option("--global", "mode", flag_value="global", help="Show global config file only.")
@click.option("--project", "mode", flag_value="project", help="Show project config file only.")
def config_list(mode: str) -> None:
    """Show configuration."""
    import tomli_w

    if mode == "global":
        data = load_config_file(GLOBAL_CONFIG_PATH)
        label = f"Global ({GLOBAL_CONFIG_PATH})"
    elif mode == "project":
        data = load_config_file(PROJECT_CONFIG_PATH)
        label = f"Project ({PROJECT_CONFIG_PATH})"
    else:
        cfg = resolve_config()
        data = config_to_dict(cfg)
        label = "Resolved (all sources merged)"

    click.echo(f"# {label}\n")
    if data:
        click.echo(tomli_w.dumps(data))
    else:
        click.echo("(empty)")
