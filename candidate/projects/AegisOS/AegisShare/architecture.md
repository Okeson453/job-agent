# AegisShare — Architecture: Zero-Knowledge Design

Every file undergoes four client-side transforms before any byte
reaches the network:

1. **DEK generation** — unique 256-bit AES-GCM key per file, via
   `window.crypto.subtle`; never leaves the browser in plaintext
2. **File encryption** — 64KB chunks, AES-256-GCM, 96-bit nonce,
   128-bit auth tag (streaming, no memory exhaustion on large files)
3. **Integrity** — SHA-256 hash of plaintext computed pre-encryption,
   re-verified client-side on download (catches server-side tampering
   even if ciphertext auth passes)
4. **ECIES key wrapping** — DEK wrapped per authorized recipient with
   their secp256k1 public key + a per-wrap ephemeral key pair; perfect
   forward secrecy on revocation (delete the wrapped-DEK reference; the
   recipient's private key can never decrypt future wraps)

A complete backend compromise (DB, object storage, app servers) yields
only ciphertext — no key material exists server-side.

**Deployment:** microservices monorepo, Kubernetes orchestration, Rust
workspace of 9 services over mTLS-authenticated gRPC, NGINX ingress with
TLS termination, TypeScript gateway as the sole public endpoint.
