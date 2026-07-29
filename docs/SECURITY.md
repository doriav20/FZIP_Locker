# Security notes

What this system protects, what it does not, and why the 2022 implementation
was replaced rather than patched.

---

## 1. The core property

**The server cannot decrypt your archives.** Not "does not" — cannot. Archive
keys are derived on your machine from a password that is never transmitted:

```
key = Argon2id(archive_password, random_16_byte_salt, t=3, m=64 MiB, p=4)
```

An attacker with root on the server, a full database dump, and the ability to
read all traffic still gets nothing but ciphertext, because no copy of the key
or the password ever reaches it.

This is why the 2022 design needed a shared secret and this one does not: back
then encryption was symmetric *with the server in the loop*, so a key had to be
distributed to every client. Remove that requirement and the shared key
disappears with it.

## 2. Encryption at a glance

| Data | Where | Protection | Key source |
|---|---|---|---|
| **Your files** | `.lck` on your disk | AES-256-GCM, chunked, header-bound | Argon2id(archive password) — **never leaves your machine** |
| Account password | Mongo | Argon2id **hash** (one-way) | — |
| Face embeddings | Mongo | AES-256-GCM, per-record nonce, bound to owner | `FZIP_BIOMETRIC_KEY` (env, not DB) |
| Refresh tokens | Mongo | SHA-256 digest | — |
| Refresh token | Your disk | OS keyring (DPAPI / Keychain / libsecret) | OS user credentials |
| Access token | Client memory | Never persisted | — |
| API traffic | Network | TLS 1.3 via Caddy | Caddy local CA |
| Mongo traffic | Network | Private Compose network, no published port | — |

A fast hash (SHA-256) for refresh tokens is deliberate: they are 256 bits of
random data, so there is no dictionary to attack and Argon2 would only add
latency to every refresh.

## 3. What a full database dump yields

| Field | Stored as | An attacker gets |
|---|---|---|
| `email` | plaintext | the address (needed for lookup; accepted) |
| `password_hash` | Argon2id | nothing usable at reasonable password strength |
| `embeddings[]` | AES-256-GCM + nonce + `key_version` | nothing — the key is in the environment, not the database |
| `refresh_tokens[].hash` | SHA-256 | nothing — not reversible into a presentable token |
| `created_at`, `_id` | plaintext | metadata only, and critically **no longer key material** |
| your files | **absent** | nothing. They never reach the server. |

Compare 2022: a dump gave you every password in recoverable form — the
decryption key was `pickle.dumps(creation_time)[7:39]`, and `creation_time` was
stored in plaintext in the same document — plus a directly reusable LBPH face
model per user.

Face embeddings are additionally bound to their owner through the AEAD's
associated data (`fzip-embedding:{user_id}:{key_version}`). Without that, an
attacker with database *write* access could copy Alice's encrypted embedding
into Bob's document and authenticate as Bob using Alice's face, without ever
breaking the encryption.

## 4. Key management

| Key | Origin | Lives | Rotation |
|---|---|---|---|
| Archive key | Argon2id from your password + per-file salt | Derived on demand; never stored or sent | Per file. Parameters travel in the header, so the cost can be raised without breaking old archives. |
| `FZIP_BIOMETRIC_KEY` | `scripts/gen_secrets.py`, 32 random bytes | `.env` → container env | `key_version` per record enables incremental rewrap |
| JWT signing key | Ed25519 keypair | `.env` | `kid` header supports a rollover window |
| Refresh tokens | `secrets.token_urlsafe(32)` | Keyring locally; SHA-256 in Mongo | Rotated every use, with reuse detection |
| Mongo app credentials | `scripts/gen_secrets.py` | `.env` | Manual |
| Caddy local CA | Generated on first run | Named volume; exported to `./certs/` | Per environment |

`gen_secrets.py` prints to stdout and never writes a file — precisely so it
cannot create something a later `git add -A` would sweep up.

Derived key material is held in `bytearray` and overwritten after use.
**This is defence in depth, not a guarantee:** CPython may already have copied
the bytes during allocation or garbage collection, and those copies are
unreachable. It shortens the window; it does not close it.

## 5. Attacks specifically addressed

| Attack | Defence |
|---|---|
| Remote code execution via `pickle` | Pickle is absent. Every payload is validated by Pydantic. |
| Password recovery from a DB dump | Argon2id hashing, no reversible storage |
| Offline brute force of an archive | Argon2id at 64 MiB, 12-character minimum |
| Ciphertext tampering | AES-GCM; any modification fails the tag |
| Archive truncation / chunk splicing | Chunk count *and* payload size are authenticated in the AAD; nonces include the chunk index |
| Hostile `.lck` causing resource exhaustion | KDF parameters bounded before use; header size capped at 64 KiB |
| Zip-slip on extraction | Every entry's resolved path validated; absolute paths and symlinks refused |
| Face replay | Single-use server nonce, consumed atomically via `find_one_and_update` |
| Static-image "liveness" | Multi-frame head-turn challenge in a server-chosen direction |
| Token confusion (face token used as access token) | `typ` claim, checked on decode |
| JWT `alg: none` / algorithm confusion | Algorithms pinned to `["EdDSA"]`; asymmetric key |
| Refresh token theft | Rotation on every use; replay revokes the whole family |
| Online password guessing | Argon2id cost + per-IP and per-account lockout |
| Account enumeration | Uniform status, slug and detail on login failure; dummy hash burns equal CPU time when the account does not exist |
| Threshold hill-climbing | Similarity rounded to 2 dp before it leaves the server; liveness diagnostics logged, never returned |
| Privilege escalation from an app bug | Mongo app user has `readWrite` on one database; the API container runs as UID 1001 with `no-new-privileges` |
| HTML injection into welcome mail | Username HTML-escaped before interpolation |

## 6. Known limitations

**Read this section.** The following are real gaps, stated plainly rather than
papered over.

### Face recognition is not presentation-attack detection

The head-turn challenge defeats **replay of a captured payload** — which is
what the 2022 protocol allowed, indefinitely. It does **not** defeat a
determined presentation attack:

- a video of you replayed on a phone screen will likely pass
- a printed photo moved by hand may pass
- a sufficiently good mask will pass

Real PAD needs depth sensing, infrared, or a trained anti-spoofing model, none
of which are here. **Treat the face factor as a convenience check, not a
security boundary.** The archive password is the control that actually protects
your files.

### The `.lck` owner tag is advisory

`owner` in the header lets the UI say "this belongs to another account" instead
of a bare decryption failure. It is *inside* the AEAD, so it cannot be edited
without breaking the tag — but an attacker holding the archive and its password
can simply ignore the client. **The password is the access control.**

### No account recovery

Forgetting your archive password means the data is gone. That is the direct,
unavoidable cost of the server not holding a key. There is no reset flow, and
adding one honestly would require escrowing keys — which would destroy the
property in section 1.

### Other gaps

- **No account password reset.** Not implemented.
- **`X-Forwarded-For` is trusted.** Correct behind the bundled Caddy on a
  private network; exposing the API directly would let a caller forge it and
  bypass per-IP limits.
- **Rate limiting is per-instance state in Mongo** with a fixed window, not a
  sliding one. Adequate for slowing online guessing; not a DDoS defence.
- **Email addresses are stored in plaintext.** Required for login lookup.
- **A plaintext ZIP briefly exists** in a private temp directory during lock and
  unlock, removed even on failure. It is not written to the destination folder,
  which the 2022 version did.
- **No 2FA beyond the face factor**, and no audit log surfaced to users.

## 7. The committed key

`key.key` — a 32-byte AES-256 key — was committed to this repository in 2022
and exists in **three blob versions** in git history. It is public and always
will be.

Any `.lck` file produced by the 2022 client should be considered **already
compromised**: that key was the outer encryption layer, and the inner layer was
ZipCrypto, broken by known-plaintext attack since the 1990s.

No history rewrite is proposed. The value is inert — nothing in the current
design uses a shared key, and no v1 archives exist. Recording the fact is more
useful than hiding it. `git filter-repo` remains available if you want the blob
gone, but it is cosmetic.

**Also in history:** the Atlas hostname `cluster0.04r8shb.mongodb.net` and the
usernames `admin` / `fziplockerproject`. The cluster should be decommissioned;
the current stack runs its own Mongo. The SMTP and database *passwords* were
never committed — they were empty strings in every version, across every path
those files lived at.

## 8. Reporting

This is a personal portfolio project with no production deployment and no
security SLA. Open an issue for anything you find.
