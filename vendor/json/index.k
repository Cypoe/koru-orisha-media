// json — tiny parse + emit (not koru/yyjson, not Orisha).
//
// One-stem companion: this file + index.kz. No pkg-config / libyyjson.
// Request handlers do not import this module.
//
// Read events match koru/yyjson's test surface (parse / root / object.get /
// array.get / array.each / object.each / as.* / close) so the yyjson
// `basic.kz` / `features.kz` suites can run against this codec.
// Write stays Zig pub fns (emitJson / appendEscaped) used by src/json.

pub tor parse { text: string }
| ok *Doc
| err { code: i32, pos: usize, msg: string }

pub tor close { doc: *Doc }

pub tor root { doc: *Doc } -> *Value

pub tor object.get { doc: *Doc, v: *Value, key: string }
| found *Value
| not-found

pub tor array.get { doc: *Doc, v: *Value, index: i64 }
| found *Value
| out-of-range

pub tor array.each { doc: *Doc, v: *Value }
! item *Value
| done
| not-an-array

pub tor object.each { doc: *Doc, v: *Value }
! entry *Entry
| done
| not-an-object

pub tor as.string { doc: *Doc, v: *Value }
| ok string
| wrong-type

pub tor as.int { doc: *Doc, v: *Value }
| ok i64
| wrong-type

pub tor as.double { doc: *Doc, v: *Value }
| ok f64
| wrong-type

pub tor as.bool { doc: *Doc, v: *Value }
| ok bool
| wrong-type
