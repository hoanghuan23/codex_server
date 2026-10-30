#!/usr/bin/env python3
"""Kiểm tra đầu ra web hoặc cấu hình JSON của skill thematic-map-designer.

Cách dùng (chạy từ thư mục skill hoặc dùng đường dẫn đầy đủ):
  python scripts/validate.py --format web --mode analysis --result output_directory
  python scripts/validate.py --mode analysis      --input profile.json --result out.json
  python scripts/validate.py --mode text_analysis --input text.json    --result out.json
  python scripts/validate.py --mode composition   --input layers.json  --result out.json
  python scripts/validate.py --mode layer_order   --input layers.json  --result out.json

--input   : payload ứng dụng giao (tùy chọn với analysis/text_analysis, bắt buộc với
            composition/layer_order). analysis nhận {"profile":..., "supportedCharts":...}
            hoặc chính profile.
--charts  : file supportedCharts do ứng dụng giao (mặc định schemas/supported-charts.json).
--no-schema: bỏ qua bước kiểm JSON Schema (chỉ khi không cài được jsonschema).
--format  : web kiểm thư mục HTML/JS/CSS; json kiểm cấu hình (mặc định json để
            tương thích các lời gọi validator cũ; skill web luôn truyền --format web).

Mã thoát: 0 = hợp lệ (có thể kèm cảnh báo), 1 = có lỗi cần sửa, 2 = sai tham số/không đọc được file.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCHEMA_DIR = SKILL_DIR / "schemas"

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
TITLES = {
    "choropleth": "Bản đồ Polygon",
    "map_line": "Bản đồ Line",
    "point": "Bản đồ Point",
    "arc_flow": "Bản đồ Arc Flow 3D",
}
ARC_SLOTS = ["source", "target", "sourceLat", "sourceLng", "targetLat", "targetLng", "value"]
SCHEMA_NAMES = {
    "analysis": "analysis",
    "text_analysis": "text-analysis",
    "composition": "composition",
    "layer_order": "layer-order",
}
LAYER_ORDER_FALLBACK = {
    "type": "object",
    "additionalProperties": False,
    "required": ["orderedLayerIds", "explanation"],
    "properties": {
        "orderedLayerIds": {"type": "array", "items": {"type": "string"}},
        "explanation": {"type": "string"},
    },
}


class Report:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.notes = []

    def err(self, path, msg):
        self.errors.append("%s: %s" % (path, msg))

    def warn(self, path, msg):
        self.warnings.append("%s: %s" % (path, msg))

    def note(self, msg):
        self.notes.append(msg)

    def finish(self):
        for n in self.notes:
            print("GHI CHÚ   " + n)
        for w in self.warnings:
            print("CẢNH BÁO  " + w)
        for e in self.errors:
            print("LỖI       " + e)
        if self.errors:
            print("KẾT QUẢ: CÓ %d LỖI, %d cảnh báo" % (len(self.errors), len(self.warnings)))
            return 1
        print("KẾT QUẢ: HỢP LỆ (%d cảnh báo)" % len(self.warnings))
        return 0


def load_json(path, what, exit_code):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Không tìm thấy %s: %s" % (what, path))
    except json.JSONDecodeError as e:
        print("%s không phải JSON hợp lệ (%s): %s" % (what, e, path))
    sys.exit(exit_code)


# ---------------------------------------------------------------- JSON Schema
def find_schema(name):
    for suffix in (".schema.json", "_schema.json"):
        p = SCHEMA_DIR / (name + suffix)
        if p.exists():
            return p
    return None


def schema_check(rep, mode, data):
    """Trả True nếu schema hợp lệ (hoặc không kiểm tra được)."""
    name = SCHEMA_NAMES[mode]
    p = find_schema(name)
    if p is not None:
        schema = load_json(p, "schema", 2)
    elif mode == "layer_order":
        schema = LAYER_ORDER_FALLBACK
    else:
        rep.note("Không tìm thấy schema %s trong %s; bỏ qua bước kiểm schema." % (name, SCHEMA_DIR))
        return True
    try:
        import jsonschema
        from jsonschema.exceptions import best_match
    except ImportError:
        rep.note("Chưa cài jsonschema (pip install jsonschema) nên CHƯA kiểm schema; mới chỉ kiểm ràng buộc ngữ nghĩa.")
        return True
    validator = jsonschema.validators.validator_for(schema)(schema)
    errs = sorted(validator.iter_errors(data), key=lambda e: list(map(str, e.absolute_path)))
    for e in errs[:30]:
        sub = best_match(e.context) if e.context else e
        path = "/".join(str(x) for x in e.absolute_path) or "(gốc)"
        rep.err("schema " + path, sub.message[:220])
    if len(errs) > 30:
        rep.err("schema", "còn %d lỗi schema nữa, sửa các lỗi trên trước." % (len(errs) - 30))
    return not errs


# ------------------------------------------------------------------- Legend
def check_legend(rep, path, lg):
    t, mode = lg.get("type"), lg.get("mode")
    if len(lg.get("title", "")) > 160:
        rep.err(path + ".title", "dài quá 160 ký tự")
    if len(lg.get("reason", "")) > 800:
        rep.err(path + ".reason", "dài quá 800 ký tự")
    stops = lg.get("stops", [])
    for i, s in enumerate(stops):
        if not HEX.match(str(s.get("color", ""))):
            rep.err("%s.stops[%d].color" % (path, i), "phải là HEX #RRGGBB")
    if t in ("continuous", "diverging"):
        dom = lg.get("domain") or [0, 0]
        vals = [s["value"] for s in stops]
        if not dom[0] < dom[1]:
            rep.err(path + ".domain", "phải tăng nghiêm ngặt")
        if any(b <= a for a, b in zip(vals, vals[1:])):
            rep.err(path + ".stops", "value của stops phải tăng nghiêm ngặt")
        if vals and (vals[0] != dom[0] or vals[-1] != dom[1]):
            rep.err(path + ".stops", "hai stop biên phải trùng domain")
        if t == "continuous" and mode == "auto" and list(dom) != [0, 1]:
            rep.err(path + ".domain", "mode auto phải có domain [0, 1]")
        if t == "diverging":
            c = lg.get("center")
            if c is None or not dom[0] < c < dom[1]:
                rep.err(path + ".center", "phải nằm giữa domain")
            else:
                if c not in vals:
                    rep.err(path + ".stops", "phải có một stop đúng tại center")
                if not any(v < c for v in vals) or not any(v > c for v in vals):
                    rep.err(path + ".stops", "cần ít nhất một stop mỗi phía của center")
    elif t == "categorical":
        vals = [s["value"] for s in stops]
        if len(set(vals)) != len(vals):
            rep.err(path + ".stops", "giá trị category bị trùng")
        colors = [str(s["color"]).lower() for s in stops]
        combos = lg.get("combinations", [])
        seen = set()
        for i, c in enumerate(combos):
            cv = c.get("values", [])
            if len(set(cv)) != len(cv):
                rep.err("%s.combinations[%d]" % (path, i), "values bị lặp")
            if not set(cv) <= set(vals):
                rep.err("%s.combinations[%d]" % (path, i), "values phải thuộc stops")
            key = frozenset(cv)
            if key in seen:
                rep.err("%s.combinations[%d]" % (path, i), "tổ hợp trùng (kể cả đảo thứ tự)")
            seen.add(key)
            colors.append(str(c.get("color", "")).lower())
        if len(set(colors)) != len(colors):
            rep.err(path, "mỗi giá trị đơn và mỗi tổ hợp phải có một màu riêng, khác nhau")


# ----------------------------------------------------------------- Analysis
def check_analysis(rep, A, charts, expected_names=None, native_geometry=False, profile_cols=None, prefix=""):
    P = prefix
    cols = A["columns"]
    names = [c["name"] for c in cols]
    colmap = {c["name"]: c for c in cols}
    if len(colmap) != len(names):
        rep.err(P + "columns", "tên cột bị trùng")
    if expected_names is not None:
        miss = [n for n in expected_names if n not in colmap]
        extra = [n for n in names if n not in expected_names]
        if miss:
            rep.err(P + "columns", "thiếu cột đầu vào: %s" % miss[:10])
        if extra:
            rep.err(P + "columns", "cột không có trong đầu vào: %s" % extra[:10])

    def need_col(path, name):
        if name not in colmap:
            rep.err(path, "cột '%s' không có trong columns" % name)
            return None
        return colmap[name]

    # --- columns
    for c in cols:
        p = "%scolumns[%s]" % (P, c["name"])
        if c["unit"] is None and c["unitSource"] != "unknown":
            rep.err(p, "unit null thì unitSource phải là unknown")
        if c["unit"] is not None and c["unitSource"] == "unknown":
            rep.err(p, "đã có unit thì unitSource phải là explicit/inferred")
        if c["geoLevel"] and c["role"] != "geo":
            rep.err(p, "có geoLevel thì role phải là geo")
        if (c["timeParse"] or c["granularity"]) and c["role"] != "time":
            rep.err(p, "timeParse/granularity chỉ dành cho cột role time")
        if c["semanticType"] and c["role"] != "measure":
            rep.warn(p, "semanticType chỉ nên đặt cho measure")
        if c["aggDefault"] and c["role"] != "measure":
            rep.warn(p, "aggDefault chỉ nên đặt cho measure")
        lg = c["legend"]
        if lg is not None:
            if c["role"] not in ("measure", "category"):
                rep.err(p + ".legend", "chỉ measure/category mới có legend")
            if c["role"] == "measure" and lg["type"] == "categorical":
                rep.warn(p + ".legend", "measure thường dùng continuous/diverging")
            if c["role"] == "category" and lg["type"] != "categorical":
                rep.warn(p + ".legend", "category nên dùng legend categorical")
            check_legend(rep, p + ".legend", lg)
            if lg["type"] != "categorical":
                if lg["aggregation"] != c["aggDefault"]:
                    rep.err(p + ".legend.aggregation", "phải khớp aggDefault (%r)" % c["aggDefault"])
                want = "bản ghi" if c["aggDefault"] == "count" else c["unit"]
                if lg["unit"] != want:
                    rep.warn(p + ".legend.unit", "nên khớp đơn vị cột (%r)" % want)

    # --- suggestions
    sugs = A["suggestions"]
    seen_types, seen_ids, prev = set(), set(), None
    pc = A["popupContent"]
    has_time = any(c["role"] == "time" for c in cols)
    for i, s in enumerate(sugs):
        p = "%ssuggestions[%d]" % (P, i)
        ct, b = s["chartType"], s["bindings"]
        if ct in seen_types:
            rep.err(p, "mỗi chartType chỉ một suggestion")
        seen_types.add(ct)
        if s["id"] in seen_ids:
            rep.err(p + ".id", "id bị trùng")
        seen_ids.add(s["id"])
        if prev is not None and s["confidence"] > prev:
            rep.err(p + ".confidence", "suggestions phải xếp giảm dần theo confidence")
        prev = s["confidence"]
        if ct not in charts:
            rep.err(p + ".chartType", "%s không có trong supportedCharts" % ct)
        if s["title"] != TITLES.get(ct):
            rep.err(p + ".title", "phải là '%s'" % TITLES.get(ct))
        slots = charts.get(ct, {}).get("slots", {})
        for slot, v in b.items():
            if v is None:
                continue
            if slot not in slots:
                rep.err("%s.bindings.%s" % (p, slot), "slot không thuộc %s, phải là null" % ct)
                continue
            col = need_col("%s.bindings.%s" % (p, slot), v)
            if col and col["role"] not in slots[slot]:
                rep.err("%s.bindings.%s" % (p, slot),
                        "cột '%s' có role %s, slot yêu cầu %s" % (v, col["role"], slots[slot]))
        # slot bắt buộc
        if ct == "point":
            for k in ("lat", "lng"):
                if not b.get(k):
                    rep.err("%s.bindings.%s" % (p, k), "point bắt buộc có cột tọa độ")
        elif ct == "arc_flow":
            used = [b.get(k) for k in ARC_SLOTS]
            for k in ARC_SLOTS:
                if not b.get(k):
                    rep.err("%s.bindings.%s" % (p, k), "arc_flow bắt buộc")
            if len([u for u in used if u]) != len(set(u for u in used if u)):
                rep.err(p + ".bindings", "bảy binding bắt buộc của arc_flow phải là bảy cột khác nhau")
        elif ct == "choropleth":
            if not b.get("region") and not native_geometry:
                rep.warn(p + ".bindings.region", "region null chỉ hợp lệ với geometry area gốc")
        elif ct == "map_line":
            if not b.get("region") and not (b.get("lat") and b.get("lng")) and not native_geometry:
                rep.err(p + ".bindings", "map_line cần region (tên/mã tuyến) hoặc lat+lng, trừ geometry line gốc")
        # tọa độ không bị đảo
        for slot in ("lat", "sourceLat", "targetLat"):
            if b.get(slot) in colmap and colmap[b[slot]]["geoLevel"] == "point_lng":
                rep.err("%s.bindings.%s" % (p, slot), "cột là point_lng nhưng đặt vào slot lat")
        for slot in ("lng", "sourceLng", "targetLng"):
            if b.get(slot) in colmap and colmap[b[slot]]["geoLevel"] == "point_lat":
                rep.err("%s.bindings.%s" % (p, slot), "cột là point_lat nhưng đặt vào slot lng")
        if ct == "arc_flow" and b.get("value") in colmap and colmap[b["value"]]["geoLevel"] in ("point_lat", "point_lng"):
            rep.err(p + ".bindings.value", "value không được là cột tọa độ")

        # agg + legend
        vcol = colmap.get(b.get("value")) if b.get("value") else None
        if ct in ("point", "arc_flow"):
            if s["legend"] is not None:
                rep.err(p + ".legend", "%s phải có legend null" % ct)
        if ct in ("choropleth", "map_line"):
            if not b.get("value"):
                if s["agg"] is not None or s["legend"] is not None or s["metricButtons"]:
                    rep.err(p, "value null thì agg, legend phải null và metricButtons []")
            elif vcol is not None:
                if s["legend"] is None:
                    if s["agg"] != vcol["aggDefault"] and vcol["role"] == "measure":
                        rep.warn(p + ".agg", "khác aggDefault của cột nhưng không có legend riêng")
                else:
                    check_legend(rep, p + ".legend", s["legend"])
                    if s["legend"]["type"] != "categorical" and s["legend"]["aggregation"] != s["agg"]:
                        rep.err(p + ".legend.aggregation", "phải khớp suggestion.agg")
                    if s["agg"] == vcol["aggDefault"]:
                        rep.warn(p + ".legend", "agg trùng aggDefault: nên để null và dùng legend của cột")

        # metricButtons
        mb = s["metricButtons"]
        if ct == "arc_flow" and mb:
            rep.err(p + ".metricButtons", "arc_flow phải là []")
        if len(mb) == 1:
            rep.err(p + ".metricButtons", "cần ít nhất hai nút, nếu ít hơn thì []")
        fields = [m["field"] for m in mb]
        if len(set(fields)) != len(fields):
            rep.err(p + ".metricButtons", "field bị lặp")
        reserved = {v for k, v in b.items() if v and k != "value"}
        for m in mb:
            col = need_col(p + ".metricButtons.field", m["field"])
            if not col:
                continue
            allowed = ("measure",) if ct == "point" else ("measure", "category")
            if col["role"] not in allowed:
                rep.err(p + ".metricButtons", "'%s' có role %s, chỉ cho phép %s" % (m["field"], col["role"], allowed))
            if m["field"] in reserved:
                rep.err(p + ".metricButtons", "'%s' là cột binding khác (region/tọa độ/...), không dùng làm nút" % m["field"])
        if mb and ct in ("choropleth", "map_line") and b.get("value") and b["value"] not in fields:
            rep.err(p + ".metricButtons", "phải bao gồm cột value mặc định '%s'" % b["value"])

        # popupSuggestions
        ps = s["popupSuggestions"]
        pn = [x["name"] for x in ps]
        if len(set(pn)) != len(pn):
            rep.err(p + ".popupSuggestions", "name bị trùng")
        pconf = [x["confidence"] for x in ps]
        if any(b2 > a for a, b2 in zip(pconf, pconf[1:])):
            rep.err(p + ".popupSuggestions", "phải xếp giảm dần theo confidence")
        if ct == "arc_flow" and pn != ["info"]:
            rep.err(p + ".popupSuggestions", "arc_flow chỉ đề xuất ['info']")
        if "info_image" in pn and not pc["imageFields"]:
            rep.warn(p + ".popupSuggestions", "có info_image nhưng popupContent.imageFields rỗng")
        if "line" in pn and not has_time:
            rep.warn(p + ".popupSuggestions", "có line nhưng không có cột role time")

        # geographicScopes
        gs = s["geographicScopes"]
        if ct != "choropleth" and gs:
            rep.err(p + ".geographicScopes", "chỉ choropleth dùng geographicScopes, loại khác phải []")
        sv = [g["sourceValue"] for g in gs]
        if len(set(sv)) != len(sv):
            rep.err(p + ".geographicScopes", "sourceValue bị lặp (tối đa một mục cho mỗi giá trị)")
        dv = None
        if profile_cols and b.get("region") in profile_cols:
            dv = profile_cols[b["region"]].get("distinctValues")
        for j, g in enumerate(gs):
            gp = "%s.geographicScopes[%d]" % (p, j)
            if g["render"] == "boundary" and (g["targetName"] is None or g["geoLevel"] is None):
                rep.err(gp, "boundary cần targetName và geoLevel")
            if g["render"] == "marker" and g["targetName"] is None:
                rep.err(gp, "marker cần targetName làm mốc")
            if g["render"] == "unresolved" and (g["targetName"] is not None or g["geoLevel"] is not None):
                rep.err(gp, "unresolved phải có targetName và geoLevel null")
            if not g["label"].strip() or not g["reason"].strip():
                rep.err(gp, "label và reason không được rỗng")
            if dv and g["sourceValue"] not in {str(x) for x in dv}:
                rep.warn(gp + ".sourceValue", "không khớp nguyên văn giá trị nào trong distinctValues của cột region")

    # --- search / navigation / popupContent
    sf = A["search_fields"]
    if A["search_bar"] and not sf:
        rep.err(P + "search_fields", "search_bar true thì cần search_fields")
    for f in sf:
        col = need_col(P + "search_fields", f)
        if col and (col["role"] in ("measure", "time") or col["geoLevel"] in ("point_lat", "point_lng")):
            rep.err(P + "search_fields", "'%s' (measure/time/tọa độ) không được dùng để tìm kiếm" % f)
    rn = A["regionNavigation"]
    if rn:
        col = need_col(P + "regionNavigation.countryField", rn["countryField"])
        if col and not (col["role"] == "geo" and col["geoLevel"] == "country"):
            rep.err(P + "regionNavigation.countryField", "phải là cột role geo, geoLevel country")
        if len(set(rn["regions"])) != len(rn["regions"]):
            rep.err(P + "regionNavigation.regions", "ID khu vực bị lặp")
    check_popup_content(rep, P + "popupContent", pc, colmap)


def check_popup_content(rep, path, pc, colmap):
    if pc["titleField"] is not None and pc["titleField"] not in colmap:
        rep.err(path + ".titleField", "cột '%s' không tồn tại" % pc["titleField"])
    for k in ("imageFields", "descriptionFields", "addressFields", "linkFields"):
        for f in pc[k]:
            if f not in colmap:
                rep.err("%s.%s" % (path, k), "cột '%s' không tồn tại" % f)
    both = set(pc["imageFields"]) & set(pc["linkFields"])
    if both:
        rep.err(path, "cột ảnh phải khác cột liên kết trang web: %s" % sorted(both))


def check_analysis_mode(rep, R, payload, charts_path):
    payload = payload or {}
    profile = payload.get("profile") if "profile" in payload else (payload if "columns" in payload else None)
    charts = payload.get("supportedCharts") or load_json(charts_path, "supportedCharts", 2)
    expected, native, pcols = None, False, None
    if profile:
        expected = [c["name"] for c in profile.get("columns", [])]
        native = bool((profile.get("spatial") or {}).get("nativeGeometry"))
        pcols = {c["name"]: c for c in profile.get("columns", [])}
    else:
        rep.note("Không có profile đầu vào: chỉ kiểm tính nhất quán nội bộ của kết quả.")
    check_analysis(rep, R, charts, expected, native, pcols)


# ------------------------------------------------------------ Text analysis
def check_text_mode(rep, R, payload, charts_path):
    charts = (payload or {}).get("supportedCharts") or load_json(charts_path, "supportedCharts", 2)
    fields, rows, A = R["fields"], R["rows"], R["analysis"]
    if len(set(fields)) != len(fields):
        rep.err("fields", "tên cột bị trùng")
    if any(not str(f).strip() for f in fields):
        rep.err("fields", "có tên cột rỗng")
    for i, r in enumerate(rows):
        if len(r) != len(fields):
            rep.err("rows[%d]" % i, "có %d ô, cần đúng %d ô theo fields" % (len(r), len(fields)))
    seen = set()
    for i, r in enumerate(rows):
        key = json.dumps(r, ensure_ascii=False)
        if key in seen:
            rep.warn("rows[%d]" % i, "trùng hệt một dòng trước đó; mỗi quan sát chỉ nên xuất hiện một lần")
        seen.add(key)
    if not rows:
        ok = (not fields and not A["columns"] and not A["suggestions"] and not A["search_fields"]
              and A["search_bar"] is False and A["regionNavigation"] is None
              and A["popupContent"]["titleField"] is None
              and not any(A["popupContent"][k] for k in ("imageFields", "descriptionFields", "addressFields", "linkFields")))
        if not ok:
            rep.err("analysis", "không có quan sát: fields/rows/columns/suggestions/search_fields phải rỗng, "
                                "search_bar false, regionNavigation null, popupContent rỗng")
        return
    check_analysis(rep, A, charts, expected_names=fields, prefix="analysis.")
    # định dạng kỳ
    idx = {f: i for i, f in enumerate(fields)}
    pat = {"month": r"^\d{4}-\d{2}$", "day": r"^\d{4}-\d{2}-\d{2}$", "year": r"^\d{4}$"}
    for c in A["columns"]:
        if c["role"] == "time" and c["timeParse"] == "iso" and c["granularity"] in pat and c["name"] in idx:
            bad = [r[idx[c["name"]]] for r in rows
                   if r[idx[c["name"]]] is not None and not re.match(pat[c["granularity"]], str(r[idx[c["name"]]]))]
            if bad:
                rep.warn("rows", "cột '%s' (%s) có giá trị sai định dạng, ví dụ %r" % (c["name"], c["granularity"], bad[0]))


# -------------------------------------------------------------- Composition
def check_composition_mode(rep, R, P):
    layers = {l["id"]: l for l in P.get("layers", [])}
    groups = {g["id"]: g for g in P.get("groups", [])}
    new_ids = P.get("newLayerIds", [])
    decs = R["decisions"]
    if [d["layerId"] for d in decs] != new_ids:
        rep.err("decisions", "phải có đúng một decision cho mỗi newLayerIds, cùng thứ tự: %s" % new_ids)
    keys = {}
    for i, d in enumerate(decs):
        p = "decisions[%d]" % i
        l = layers.get(d["layerId"])
        if l is None:
            rep.err(p + ".layerId", "ID không có trong layers")
            continue
        act = d["action"]
        if (l.get("available") is False or l.get("sourceKind") == "attribute") and act != "undetermined":
            rep.err(p, "lớp available=false hoặc nguồn attribute phải là undetermined")
        if act == "append_to_group":
            if d["targetGroupId"] not in groups:
                rep.err(p + ".targetGroupId", "phải là ID nhóm đã có trong đầu vào")
            if d["newGroupKey"] is not None:
                rep.err(p + ".newGroupKey", "append_to_group phải để null")
        elif act == "create_group":
            if d["targetGroupId"] is not None:
                rep.err(p + ".targetGroupId", "create_group phải để null")
            keys.setdefault(d["newGroupKey"], []).append(d)
        else:
            if d["targetGroupId"] is not None or d["newGroupKey"] is not None:
                rep.err(p, "undetermined phải có targetGroupId và newGroupKey null")
    for k, ds in keys.items():
        if k is None:
            continue
        if len(ds) < 2:
            rep.warn("decisions", "newGroupKey '%s' chỉ dùng cho một lớp: lớp riêng nên để null" % k)
        if len({d["groupTitle"] for d in ds}) > 1:
            rep.warn("decisions", "các lớp cùng newGroupKey '%s' nên có cùng groupTitle" % k)

    # tìm kiếm
    def valid_search(l):
        names = {c.get("name") for c in l.get("columns", [])}
        return (l.get("sourceKind") != "attribute" and l.get("search_bar") is True
                and any(f in names for f in l.get("search_fields") or []))
    expected = {i for i, l in layers.items() if valid_search(l)}
    got = R["searchLayerIds"]
    if len(set(got)) != len(got):
        rep.err("searchLayerIds", "ID bị lặp")
    for i in got:
        if i not in expected:
            rep.err("searchLayerIds", "'%s' không phải lớp spatial có search_bar true và search_fields hợp lệ" % i)
    miss = sorted(expected - set(got))
    if miss:
        rep.warn("searchLayerIds", "thiếu lớp đủ điều kiện tìm kiếm: %s" % miss)

    # attributeJoins
    seen = set()
    for i, j in enumerate(R["attributeJoins"]):
        p = "attributeJoins[%d]" % i
        src, tgt = layers.get(j["sourceId"]), layers.get(j["targetLayerId"])
        if src is None or src.get("sourceKind") != "attribute":
            rep.err(p + ".sourceId", "phải là ID của nguồn attribute")
        if tgt is None or tgt.get("sourceKind") != "spatial" or tgt.get("available") is False:
            rep.err(p + ".targetLayerId", "phải là lớp spatial available")
        pair = (j["sourceId"], j["targetLayerId"])
        if pair in seen:
            rep.err(p, "mỗi cặp source/target chỉ một đề xuất")
        seen.add(pair)
        sn = {c.get("name") for c in (src or {}).get("columns", [])}
        tn = {c.get("name") for c in (tgt or {}).get("columns", [])}
        sf = [k["sourceField"] for k in j["keyPairs"]]
        tf = [k["targetField"] for k in j["keyPairs"]]
        if len(set(sf)) != len(sf) or len(set(tf)) != len(tf):
            rep.err(p + ".keyPairs", "không lặp cột trong cùng một phía")
        for f in sf:
            if src and f not in sn:
                rep.err(p + ".keyPairs", "sourceField '%s' không có trong cột nguồn" % f)
        for f in tf:
            if tgt and f not in tn:
                rep.err(p + ".keyPairs", "targetField '%s' không có trong cột lớp đích" % f)
        pc = j["popupContent"]
        for k in ("imageFields", "descriptionFields", "addressFields", "linkFields"):
            for f in pc[k]:
                if src and f not in sn:
                    rep.err("%s.popupContent.%s" % (p, k), "'%s' phải là cột của nguồn attribute" % f)
        if pc["titleField"] and src and pc["titleField"] not in sn:
            rep.err(p + ".popupContent.titleField", "phải là cột của nguồn attribute")
        if set(pc["imageFields"]) & set(pc["linkFields"]):
            rep.err(p + ".popupContent", "cột ảnh phải khác cột liên kết")
        pn = [x["name"] for x in j["popupSuggestions"]]
        pconf = [x["confidence"] for x in j["popupSuggestions"]]
        if len(set(pn)) != len(pn):
            rep.err(p + ".popupSuggestions", "name bị trùng")
        if any(b > a for a, b in zip(pconf, pconf[1:])):
            rep.err(p + ".popupSuggestions", "phải xếp giảm dần theo confidence")
        if "info_image" in pn and not pc["imageFields"]:
            rep.warn(p + ".popupSuggestions", "có info_image nhưng imageFields rỗng")


# --------------------------------------------------------------- Layer order
def check_layer_order_mode(rep, R, P):
    layers = P if isinstance(P, list) else P.get("layers", [])
    ids = [l["id"] for l in layers]
    got = R["orderedLayerIds"]
    if len(set(got)) != len(got):
        rep.err("orderedLayerIds", "ID bị lặp")
    miss = [i for i in ids if i not in got]
    extra = [i for i in got if i not in ids]
    if miss:
        rep.err("orderedLayerIds", "thiếu ID: %s" % miss)
    if extra:
        rep.err("orderedLayerIds", "ID không có trong đầu vào: %s" % extra)
    if not 2 <= len(ids) <= 50:
        rep.warn("layers", "số lớp đầu vào nằm ngoài 2–50")
    rank_of = {"area": 0, "line": 1, "point": 2}
    names_vi = ["vùng", "đường", "điểm"]
    rank = {}
    for l in layers:
        kinds = set(l.get("geometryKinds") or [])
        if len(kinds) == 1 and next(iter(kinds)) in rank_of:
            rank[l["id"]] = rank_of[next(iter(kinds))]
    pos = {i: n for n, i in enumerate(got)}
    shown = 0
    for a in rank:
        for b in rank:
            if a in pos and b in pos and rank[a] > rank[b] and pos[a] < pos[b] and shown < 5:
                rep.warn("orderedLayerIds", "'%s' (%s) đang nằm dưới '%s' (%s); thứ tự thường là vùng → đường → điểm từ dưới lên"
                         % (a, names_vi[rank[a]], b, names_vi[rank[b]]))
                shown += 1


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", required=True, choices=list(SCHEMA_NAMES))
    ap.add_argument("--format", choices=("web", "json"), default="json")
    ap.add_argument("--result", required=True, help="thư mục web hoặc file JSON cần kiểm tra")
    ap.add_argument("--input", help="payload đầu vào ứng dụng giao")
    ap.add_argument("--charts", default=str(SCHEMA_DIR / "supported-charts.json"))
    ap.add_argument("--no-schema", action="store_true", help="bỏ qua kiểm JSON Schema")
    a = ap.parse_args()

    if a.format == "web":
        from web_output import validate_web
        rep = Report()
        validate_web(rep, a.result)
        sys.exit(rep.finish())

    if a.mode in ("composition", "layer_order") and not a.input:
        print("Mode %s cần --input (payload lớp)." % a.mode)
        sys.exit(2)
    payload = load_json(a.input, "input", 2) if a.input else None

    try:
        with open(a.result, encoding="utf-8") as f:
            result = json.load(f)
    except FileNotFoundError:
        print("Không tìm thấy file kết quả: %s" % a.result)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print("LỖI       file kết quả không phải JSON hợp lệ (%s). Chỉ ghi một JSON object, không Markdown." % e)
        sys.exit(1)

    rep = Report()
    if not isinstance(result, dict):
        rep.err("(gốc)", "kết quả phải là một JSON object")
        sys.exit(rep.finish())
    shape_ok = True if a.no_schema else schema_check(rep, a.mode, result)
    if not shape_ok:
        sys.exit(rep.finish())  # sửa lỗi hình dạng trước, rồi mới kiểm ngữ nghĩa
    try:
        if a.mode == "analysis":
            check_analysis_mode(rep, result, payload, a.charts)
        elif a.mode == "text_analysis":
            check_text_mode(rep, result, payload, a.charts)
        elif a.mode == "composition":
            check_composition_mode(rep, result, payload)
        else:
            check_layer_order_mode(rep, result, payload)
    except (KeyError, TypeError, IndexError, AttributeError) as e:
        rep.err("(cấu trúc)", "thiếu trường hoặc sai kiểu nên không kiểm được ngữ nghĩa: %r" % (e,))
    sys.exit(rep.finish())


if __name__ == "__main__":
    main()
