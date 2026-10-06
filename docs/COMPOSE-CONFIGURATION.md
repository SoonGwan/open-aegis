# Compose integration configuration

Compose uses `.env` as an optional container environment file as well as its
existing explicit application settings. This forwards named model recipients,
notification endpoints, ScopeSentry/MCP configuration and the environment-variable
names referenced by those configurations. Host environment variables with arbitrary
names are not automatically inherited. The application does not copy this private
file into an image; `.dockerignore` excludes `.env` and other private env files.

When using a different private file, use the same path for both configuration
interpolation and container forwarding:

```sh
AEGIS_CONFIG_ENV_FILE=/private/path/aegis.env docker compose --env-file /private/path/aegis.env up --build -d
```

Without an env file, existing exported setup-token configuration still works; the
missing optional file adds no named integration credentials. The supplied Compose
service fixes its internal port to8787, data path to`/app/data`, UI path to
`/app/web/dist` and bind address to`0.0.0.0`. Local `start.sh` paths/ports in `.env`
do not overwrite those container values. The host published port remains loopback.

Use single quotes around values containing `$` to preserve them literally.
See the[official Compose environment-file rules](https://docs.docker.com/reference/compose-file/services/#env_file).
`environment` entries take precedence over `env_file` values. The existing explicit
settings retain their documented precedence. Compose>=2.24.4 is required for the
real container review (including optional env-file mappings and ports overrides).
Secrets remain container environment values visible to the Docker administrator;
application API configuration exposes availability and names rather than keys.

The daemon-free `scripts/review_compose_configuration.py` checks the real Compose
model with owned temporary files: default `.env`, explicitly selected file, legacy
exported setup token, named integration variables, literal dollars and fixed
container paths/loopback publication. It never loads the user's `.env` and does not
start a container or contact a provider. Rendered config escapes dollar signs for
round trips; that representation is normalized for model comparisons.
The real `scripts/review_compose.py` separately checks exact variables inside the
running container, model/notification configuration availability, both storage
backends, persistence, backup/restore and cleanup. Hosted container verification
is required before declaring the environment-forwarding fix accepted.
