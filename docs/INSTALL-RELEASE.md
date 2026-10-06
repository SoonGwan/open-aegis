# Install a signed release bundle

The 1.0.0 candidate has not been published as an official release yet. The steps
below describe installing its verified bundle once publication is complete.
Source installation with `./start.sh` and Docker Compose remain alternatives.

Use Linux or macOS, Python3.11+ and OpenSSL3. Choose a new private directory for
the extracted bundle. Extract only a release you intend to trust; archives and
their checksums are not an independent authenticity check.

Before installing the wheel, verify the bundle using the verifier from a source
checkout you already trust. Obtain the publisher key independently of the bundle
and compare its [documented fingerprint](release-keys/README.md). Run from that
trusted checkout, using the actual absolute bundle location:

```sh
python3 -S -m aegis.cli.release verify \
  --bundle /absolute/path/to/extracted/bundle \
  --public-key docs/release-keys/publisher-ed25519-v1.pem
```

The verifier uses the Python standard library and OpenSSL3; it does not install
or execute the downloaded wheel. A missing/mismatched key, signature or payload
fails verification. Preserve the verified directory against later modification.

For a new SQLite workspace, keep the verified bundle separate from the installation
and data. Replace the absolute path with your verified bundle directory:

```sh
mkdir open-aegis-instance
cd open-aegis-instance
release_bundle=/absolute/path/to/extracted/bundle
python3 -m venv .venv
.venv/bin/python -m pip install -r "$release_bundle/requirements.lock"
.venv/bin/python -m pip install --no-index --no-deps "$release_bundle/runtime/open_aegis-1.0.0-py3-none-any.whl"
.venv/bin/python -m pip check
AEGIS_WEB_DIR="$release_bundle/web" AEGIS_DATA_DIR="$PWD/data" \
  AEGIS_HOST=127.0.0.1 AEGIS_PORT=8787 .venv/bin/python -m aegis
```

Open `http://127.0.0.1:8787` and set the first administrator password. There is no
default password. This direct command uses exported environment values; it does
not read `.env`. Node.js is unnecessary because the bundle includes built UI.

For PostgreSQL, install the signed `requirements-postgres.lock` into the same
environment and follow [database/schema setup](POSTGRES-STORAGE.md). Keep the DSN
in an environment variable. Do not put credentials in command arguments or publish
the workspace data. External hosting needs its own TLS, authentication and network
configuration; the loopback example is not a public hosting configuration.

An update is a different operation: stop the existing service and follow
[signed preflight and rollback](RELEASES.md) before changing its installation.
Do not overwrite an existing workspace with this new-install example.
