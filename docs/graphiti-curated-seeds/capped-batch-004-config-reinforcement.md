<!--
MON-316 capped Graphiti relationship seed batch 004 configuration reinforcement.
Reviewed on 2026-06-13.
Source map: docs/graphiti-curated-seeds/capped-batch-004-sources.md
-->

# MemSearch configuration priority chain

MemSearch Configuration Priority Chain is a configuration concept.
MemSearch Configuration Priority Chain includes built-in defaults.
MemSearch Configuration Priority Chain includes global config file.
The global config file is `~/.memsearch/config.toml`.
MemSearch Configuration Priority Chain includes project config file.
The project config file is `.memsearch.toml`.
MemSearch Configuration Priority Chain includes CLI flags.
CLI flags override project config file.
Project config file overrides global config file.
Global config file overrides built-in defaults.

# MemSearch API key policy

MemSearch API key policy reads API keys from environment variables.
MemSearch API key policy never writes API keys to config files.
MemSearch API key policy keeps API keys out of `~/.memsearch/config.toml`.
MemSearch API key policy keeps API keys out of `.memsearch.toml`.

# MemSearch source of truth policy

MemSearch source of truth is Markdown.
MemSearch source of truth is not Milvus.
Milvus is a derived index for MemSearch.
Milvus can be rebuilt from Markdown.
