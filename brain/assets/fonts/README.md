# Provisioned fonts (not vendored)

This directory holds fonts **downloaded on demand** by
[`brain/common/ka_font.py`](../../common/ka_font.py) — they are **not** committed
to the repo (see `.gitignore`). Only this provenance note is tracked.

## Why download instead of commit?

A ~400KB binary in git is opaque (you cannot diff or audit it). Instead we pin a
**URL + SHA256** and verify every download against the checksum. A corrupted or
tampered download fails loudly (`FontProvisionError`) — it never silently draws
tofu boxes the family would mistake for real Georgian text. The pin **is** the
provenance.

## NotoSansGeorgian-Regular.ttf

- **Font:** Noto Sans Georgian (Google Noto), license **OFL 1.1**.
- **Default mirror:** `notofonts/georgian` (raw GitHub). Override with
  `ALEKSANDRA_KA_FONT_URL` if the mirror moves.
- **Checksum:** set `ALEKSANDRA_KA_FONT_SHA256` to pin (enforced, constant-time).
  Until pinned, the first download logs its computed sha256 (trust-on-first-use)
  so you can paste it in to harden.

## One-time hardening (optional)

```bash
# Print the sha256 of the live mirror, then pin it via env/secret:
python -m brain.common.ka_font --print-hash
```

Air-gapped builds: set `ALEKSANDRA_FONT_DOWNLOAD=0` and drop the `.ttf` here
manually; the checksum (if pinned) is still verified.
