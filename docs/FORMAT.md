# The `.lck` v2 container format

## Layout

```
offset  size        field
0       8           magic:  "FZIPLCK" + version byte (0x02)
8       4           header_len: uint32, big-endian
12      header_len  header: JSON, UTF-8
12+H    ...         body: chunk[0] .. chunk[n-1]
```

Each chunk:

```
chunk[i] = AES-256-GCM(key, nonce, plaintext[i], aad) || tag
    nonce = nonce_base (8 bytes) || uint32_be(i)      -> 12 bytes
    aad   = the header bytes, verbatim as stored
    tag   = 16 bytes
```

Every chunk but the last carries exactly `chunk_size` plaintext bytes. The
final chunk carries `size - (chunks - 1) * chunk_size`, which may be zero.

## Header

```json
{
  "v": 2,
  "cipher": "AES-256-GCM",
  "kdf": {
    "alg": "argon2id",
    "salt": "<base64, 16 bytes>",
    "t": 3,
    "m": 65536,
    "p": 4
  },
  "chunk_size": 1048576,
  "nonce_base": "<base64, 8 bytes>",
  "chunks": 3,
  "size": 2621440,
  "owner": "<uuid of the account that created it>",
  "created": "2026-07-29T19:36:40.791427+00:00"
}
```

Serialised with sorted keys and no whitespace, so the encoding is
deterministic. On read, the **stored bytes** are used as AAD rather than a
re-serialisation of the parsed object — re-encoding would risk a mismatch if
key order or separators ever differed.

| Field | Purpose |
|---|---|
| `v` | Container version. Refuse anything unrecognised. |
| `kdf` | Argon2id parameters. Travelling in the file is what lets the cost be raised later without breaking existing archives. |
| `chunk_size` | Plaintext bytes per chunk. |
| `nonce_base` | Random per file. Combined with the chunk index to give each chunk a unique nonce. |
| `chunks` | Total chunk count. Authenticated, so truncation is detectable. |
| `size` | Total plaintext length. Pins the final chunk's exact length, so appended bytes are rejected structurally. |
| `owner` | Account UUID. Advisory — see [SECURITY.md](SECURITY.md) §6. |
| `created` | Informational. Authenticated like everything else. |

## Why it is built this way

**Argon2id, not a static key.** The 2022 format used one AES key committed to
this repository, identical for every user. The key now comes from the archive
password, with a per-file salt, and never leaves the machine.

**GCM, not OFB.** OFB provides confidentiality only. An attacker who cannot
read a file can still flip arbitrary plaintext bits by flipping ciphertext
bits, and the recipient has no way to notice. GCM is an AEAD: any modification
fails verification.

**Chunked.** Multi-gigabyte archives stream through constant memory. The cost
is 16 bytes of tag per megabyte — about 0.0015% expansion.

**Header as AAD.** The chunk count, payload size, KDF parameters and owner tag
are all covered by every chunk's tag. Editing any of them — including lowering
`chunks` to truncate the file — fails.

**Nonce includes the chunk index.** Chunks cannot be reordered, duplicated, or
spliced in from another archive.

**No inner ZIP encryption.** The 2022 format nested a ZipCrypto-protected ZIP
inside its AES layer. ZipCrypto is broken, and with a password-derived outer
AEAD the inner layer adds nothing. The payload is now a plain deflate ZIP, and
`pyminizip` is gone along with its C build step.

## Hostile-input bounds

A `.lck` file is untrusted input. These are checked *before* any key derivation:

| Field | Accepted range | Why |
|---|---|---|
| `header_len` | 1 .. 65536 | A claimed 4 GiB header would exhaust memory on open |
| `kdf.alg` | `argon2id` only | — |
| `kdf.salt` | 16 .. 64 bytes | — |
| `kdf.t` | 1 .. 16 | Unbounded cost is a denial of service |
| `kdf.m` | 8192 .. 1048576 KiB | A request for 1 TiB of RAM must be refused |
| `kdf.p` | 1 .. 16 | — |
| `chunk_size` | 1024 .. 64 MiB | — |
| `chunks` | 1 .. 2³²−1 | Bounded by the 4-byte nonce counter |
| `size` | ≥ 0, and `chunks == max(1, ceil(size / chunk_size))` | A hand-edited header is rejected structurally |

## Reading a container

1. Verify the 8 magic bytes; reject unknown versions.
2. Read `header_len`, bounds-check it, read the header bytes, parse and
   validate.
3. Optionally compare `owner` against the signed-in account for a clearer
   error message.
4. Derive the key with the header's KDF parameters.
5. For each chunk `i`, read its exact expected length and decrypt with nonce
   `nonce_base || uint32_be(i)` and the header bytes as AAD.
6. After the final chunk, confirm there is no trailing data.

A failure at step 5 is reported as a single "wrong password, or tampered"
error. The two cases are deliberately not distinguished: both are
authentication failures, and separating them would tell an attacker probing a
stolen archive which of the two they had achieved.

**Extraction only begins once the whole payload authenticates.** Writing files
as chunks decrypt would scatter attacker-controlled data across the disk before
the final tag revealed the archive had been modified.
