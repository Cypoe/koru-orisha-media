# Vendored Orisha lib

Copied from `W:\src\orisha\lib` (`521a4d7`).

This tree must stay a **verbatim** upstream `lib/`. App HTTP (Range, STREAM:v1,
run-accept-loop) lives in [`vendor/http`](../http/). Refresh with:

    bash scripts/vendor-orisha.sh

Do not edit index.kz here to add STREAM — that would fork Orisha again.
