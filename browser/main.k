// Optional koru/dom keyed list (GOAL Step 9).
// Build: bash scripts/build-browser.sh → public/koru-dom-enhance.js
// Demo:  public/enhance-demo.html
//
// Shipping progressive enhance for the media UI remains public/enhance.js
// (resume + fragment). This module proves keyed insert / remove / reorder
// with stable store handles — the Step 9 browser identity requirement.

import std/store
import std/control
import koru/dom

koru/dom:component(LibRow) {
    <li data-row-id="{{ id:d }}">
        <span class="title">{{ title:s }}</span>
        <button type="button" data-action="7" aria-label="remove">remove</button>
    </li>
}

std/store:new(rows, capacity: 64) { id: i64, pos: i64, title: char[48] }
! inserted { id, title, [id]h } |> LibRow(parent: "#koru-list", key: h, id, title)
! removed { [id]h } |> koru/dom:drop(key: h) |> std/store:stored { cnt.n: cnt.n - 1 }
! cleared _ |> koru/dom:drop-all() |> std/store:stored { cnt.n: 0 }

std/store:new(seq) { next: 1[i64] }
std/store:new(cnt) { n: 0[i64] }
std/store:new(op) { code: 0[i64], a: 0[i64], b: 0[i64], ida: 0[i64], idb: 0[i64] }

pub tor make-title {} -> string
pub tor swap-rows { a: i64, b: i64 }

tor clear {}
clear = std/store:clear(rows)

tor seed { n: i64 }
seed = for(0..n)
! each _ |> make-title(): t |> std/store:insert(rows) { id: seq.next, pos: cnt.n, title: t }
    | row _ |> std/store:stored { seq.next: seq.next + 1 } |> std/store:stored { cnt.n: cnt.n + 1 }
    | full |> _

[name(ops)]std/store:rule(rows)
! row { [row]e, [id]h } |> if(op.code == 6)
    | then |> if(e.pos == op.a)
        | then |> std/store:stored { e.pos: op.b } |> std/store:stored { op.ida: h }
        | else |> if(e.pos == op.b)
            | then |> std/store:stored { e.pos: op.a } |> std/store:stored { op.idb: h }
            | else |> _
    | else |> if(op.code == 77)
            | then |> if(e.pos > op.b)
                | then |> std/store:stored { e.pos: e.pos - 1 }
                | else |> _
            | else |> _

koru/dom:run(title: "koru-orisha-media keyed list")
! click { action } when action == 1 |> clear() |> seed(n: 3)
! click { action } when action == 3 |> seed(n: 1)
! click { action } when action == 5 |> clear()
! click { action } when action == 6 |> if(cnt.n > 1)
    | then |> std/store:stored { op.code: 6 } |> std/store:stored { op.a: 0 } |> std/store:stored { op.b: 1 } |> std/store:stripe(rows) |> swap-rows(a: op.ida, b: op.idb) |> std/store:stored { op.code: 0 }
    | else |> _
! click { action, key } when action == 7 |> std/store:stored { op.b: rows[key].pos } |> std/store:take(rows[key])
    | item _ |> std/store:stored { op.code: 77 } |> std/store:stripe(rows) |> std/store:stored { op.code: 0 }
