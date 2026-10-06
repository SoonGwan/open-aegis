# Release signing key

`publisher-ed25519-v1.pem` is the public Ed25519 key prepared for Open Aegis
release bundles. It is separate from the temporary keys used by tests. Check
[GitHub Releases](https://github.com/SoonGwan/open-aegis/releases) for signed assets.

SHA-256 of the DER SubjectPublicKeyInfo:

```text
7397518bca29defa1c665ae899bbb1592d0916bf79a8aca85308b74e77711176
```

Check the fingerprint with OpenSSL3:

```sh
openssl pkey -pubin -in publisher-ed25519-v1.pem -pubout -outform DER |
  openssl dgst -sha256
```

Obtain and trust this key through the repository's reviewed history before
checking a downloaded bundle. A key supplied inside an untrusted download is
not an independent trust anchor. GitHub account or repository compromise can
also compromise this delivery channel; the signature does not establish a
separate real-world identity or prove that code is secure.

The private key is outside the tracked project and Docker build context, in a
local ignored directory with mode0700 and a mode0600 key file. It is not an
encrypted or hardware-backed key. Offline backup, hardware storage and rotation
remain maintainer operations. Never commit the private key or upload it as a
release asset. If the key is lost or compromised, stop signing with it and
publish a revocation and replacement fingerprint through a trusted channel.
