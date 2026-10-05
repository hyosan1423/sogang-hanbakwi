// 요일 인덱스: 0=월 … 6=일. week[i]: {open,close,bt?,sus?} | null(휴무) | undefined(미확인)
var DAYS = ['월','화','수','목','금','토','일'];
function parseHours(h) {
  var res = { week: [undefined,undefined,undefined,undefined,undefined,undefined,undefined], notes: [], fail: [], missing: [], sus: false, ok: false };
  if (!h) return res;
  var T = function (a, b, c, d) { return [+a * 60 + +b, +c * 60 + +d]; };
  h.split(' / ').forEach(function (seg) {
    var s = seg.trim(), brk = null;
    (s.match(/\([^)]*\)/g) || []).forEach(function (p) {
      var bm = p.match(/브레이크\s*(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})/);
      if (bm) brk = T(bm[1], bm[2], bm[3], bm[4]);
      else if (!/정기휴무|매주/.test(p)) res.notes.push(p.replace(/^\(|\)$/g, ''));
    });
    s = s.replace(/\([^)]*\)/g, '').trim();
    var m = s.match(/^(매일|[월화수목금토일](?:\s*[-,]\s*[월화수목금토일])*)\s*(.*)$/);
    if (!m) { res.notes.push(s); return; }
    var idx = [];
    if (m[1] === '매일') idx = [0,1,2,3,4,5,6];
    else m[1].split(',').forEach(function (part) {
      part = part.trim();
      var r = part.match(/^([월화수목금토일])\s*-\s*([월화수목금토일])$/);
      if (r) { var a = DAYS.indexOf(r[1]), b = DAYS.indexOf(r[2]); for (var i = a; ; i = (i + 1) % 7) { idx.push(i); if (i === b) break; } }
      else idx.push(DAYS.indexOf(part));
    });
    var rest = m[2], val;
    var t = rest.match(/(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})/);
    if (!t) { if (/휴무/.test(rest)) val = null; else { res.fail.push(seg); return; } }
    else {
      var tt = T(t[1], t[2], t[3], t[4]), op = tt[0], cl = tt[1];
      if (cl <= op) cl += 1440;
      var bt = rest.match(/BT\s*(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})/);
      val = { open: op, close: cl };
      var b = bt ? T(bt[1], bt[2], bt[3], bt[4]) : brk; if (b) val.bt = b;
      if (cl - op > 20 * 60 && !(op === 0 && cl === 1440)) { val.sus = true; res.sus = true; }
    }
    idx.forEach(function (i) { res.week[i] = val; });
  });
  for (var i = 0; i < 7; i++) if (res.week[i] === undefined) res.missing.push(DAYS[i]);
  res.ok = !res.fail.length && !res.missing.length;
  return res;
}
if (typeof module !== 'undefined') module.exports = { parseHours: parseHours };
