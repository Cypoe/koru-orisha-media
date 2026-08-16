# Vendored Orisha lib

Verbatim `lib/` from the Orisha git checkout, after `git pull`.

App HTTP (Range, STREAM:v1, run-accept-loop) lives in [`vendor/http`](../http/).
Refresh with:

    bash scripts/vendor-orisha.sh

Do not edit index.kz here to add STREAM — that would fork Orisha again.
