// json-publish — usage of vendor/json (not the codec).
//
//   bin/json-publish                 pretty {entries:[…]} fixture
//   bin/json-publish emit-projections
//   bin/json-publish parse           stdin → compact JSON (exit 1 on error)
//
// Library: vendor/json (import json). Schema fixtures stay here.
// Branch arms at column 0: indented arms after a leading-`|>` continuation
// are swallowed (koru-libs/yyjson README Finding 3).

import json
import std/io

pub tor emit {} -> string

emit(): body |> std/io:print.ln("{{ body:s }}")
