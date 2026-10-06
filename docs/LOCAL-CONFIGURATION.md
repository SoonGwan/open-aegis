# Local launch configuration

`./start.sh` runs `scripts/run.py`, which reads the repository's `.env` as literal
configuration. Existing exported environment values take precedence. The file is
never sourced by a shell; dollar signs, command substitutions and backticks remain
literal. Matching outer single or double quotes are removed once. Multiline values,
shell `export`, interpolation and inline comments are not supported.

The launcher loads `AEGIS_` settings, then the names explicitly referenced by the
effective integration definitions:

| Definition | Named fields |
| --- | --- |
| `AEGIS_MODEL_DESTINATIONS` | `base_env`, `key_env` |
| `AEGIS_NOTIFICATION_DESTINATIONS` | `endpoint_env`, `token_env` |
| `AEGIS_SCOPESENTRY_SOURCES` | `token_env` |
| `AEGIS_MCP_CONNECTIONS` | `token_env` |
| `AEGIS_MCP_EXECUTORS` | `scope_key_env` |

For example, `CLAUDE_MODEL_BASE` and `CLAUDE_MODEL_KEY` in `.env` are loaded when
the model destination references those names. Exported definitions control which
names are loaded even if `.env` contains different definitions. Unreferenced
non-`AEGIS_` entries are ignored. Standard process settings (`HOME`, `PATH`,
`SHELL`, `USER`, `LOGNAME`, `TMPDIR`, `VIRTUAL_ENV`, `PYTHON*`, `LD_*`, `DYLD_*`)
are not replaced from referenced file entries; use dedicated integration names.

Invalid integration definitions are still validated by the application and do not
cause the launcher to treat arbitrary file entries as credentials. Configuration
loading does not connect to providers, approve tasks or execute a shell command.
Direct `python -m aegis` and maintenance commands use exported environment values
and do not automatically read `.env`. Docker Compose has its own
[file and precedence contract](COMPOSE-CONFIGURATION.md).
