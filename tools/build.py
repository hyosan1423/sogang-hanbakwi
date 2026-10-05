import json, glob, os, re, hashlib, html, datetime, shutil, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SITE = 'https://sogang-hanbakwi.web.app'
FEEDBACK = 'https://forms.gle/kK7rjXnV9Hz3MDnt8'
# 검색 등록용 소유 확인 값. 비어 있으면 태그를 넣지 않는다.
GOOGLE_VERIFY = '60eFcTldm0WVROOPICvUrPbqgNCQkcjDa4y9pVpwiCU'
NAVER_VERIFY = '9c21d84ff26c4a57e5045995c1ba367475b5117d'
NOW = datetime.datetime.now(datetime.timezone.utc)
TODAY = NOW.strftime('%Y-%m-%d')

# ---------- 데이터 ----------
KEEP = ['name','food','features','category','price','verifiedAt','distanceM','lat','lon','zone','address','mapUrl','hours','solo','kinds','menus']
docs = {}
for f in sorted(glob.glob('data/shops/*.json')):
    d = json.load(open(f, encoding='utf8')); d = d.get('data', d)
    docs[os.path.basename(f)[:-5]] = d
rows = []
for i, d in docs.items():
    if d.get('deleted') or not d.get('category'): continue
    rows.append([i, {k: d[k] for k in KEEP if k in d}])
CAT = {'value': '가성비 맛집', 'decent': '적당한 맛집', 'regular': '자주 갈 맛집', 'cafe': '카페', 'bar': '술집', 'lounge': '바'}

# 배포본(data/shops)은 서버로 가져온 파일(shops_import.json)과 같은 시점의 스냅샷이다.
# 가져온 문서의 updatedAt 은 모두 BASELINE 이고, 사용자 화면은 "updatedAt > SINCE" 인 문서
# (= 가져온 뒤 관리자가 고치거나 지운 것)만 서버에서 받아 배포본 위에 덮는다. 비교가 엄격한 '>' 라서
# BASELINE 과 같은 문서는 읽지 않는다(읽기 한도 절약).
# SINCE 를 "빌드한 시각"으로 정하면 재배포할 때마다 그 사이에 관리자가 고친 내용이 사용자에게서 사라지므로 고정한다.
# data/shops 를 관리 페이지 '전체 내보내기' 파일로 교체해 다시 구운 경우에만, 내보낸 문서의 최대 updatedAt 을
# 환경변수 SG_SINCE 로 넘긴다(예: SG_SINCE=2026-11-01T03:00:00.000Z npm run build).
BASELINE = '2026-10-05T00:00:00.000Z'
SINCE = os.environ.get('SG_SINCE', BASELINE)

# ---------- 자산(해시 이름) ----------
os.makedirs('public/assets', exist_ok=True)
for old in glob.glob('public/assets/shops.*.js') + glob.glob('public/assets/fb.*.js'):
    if os.path.basename(old) != 'fb.js': os.remove(old)
fb = open('public/assets/fb.js', 'rb').read()
fbname = 'fb.%s.js' % hashlib.sha256(fb).hexdigest()[:10]
open('public/assets/' + fbname, 'wb').write(fb)
os.remove('public/assets/fb.js')
blob = json.dumps(rows, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
shops_js = 'window.__SHOPS__=%s;' % blob
shname = 'shops.%s.js' % hashlib.sha256(shops_js.encode()).hexdigest()[:10]
open('public/assets/' + shname, 'w', encoding='utf8').write(shops_js)

# ---------- 앱 본문 ----------
src = open('src/app.src.html', encoding='utf8').read()
parse = re.sub(r"if \(typeof module.*\n?", "", open('src/parse.js', encoding='utf8').read())
src = src.replace('/*PARSE*/', parse)
cfg = {'url': FEEDBACK, 'shopTpl': ''}
src = re.sub(r'/\*FEEDBACK_CFG\*/.*?/\*END\*/', lambda m: json.dumps(cfg, ensure_ascii=False), src)
i = src.index('<div id="app">')
head_src, body_src = src[:i], src[i:]
head_src = re.sub(r'<title>.*?</title>\n?', '', head_src)

def page(title, desc, public, body, extra_head='', extra_body=''):
    h = ['<!doctype html>', '<html lang="ko">', '<head>', '<meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
         '<title>%s</title>' % html.escape(title),
         '<meta name="description" content="%s">' % html.escape(desc, quote=True),
         '<meta name="theme-color" content="#FFFFFF" media="(prefers-color-scheme: light)">',
         '<meta name="theme-color" content="#121316" media="(prefers-color-scheme: dark)">',
         '<link rel="icon" type="image/png" href="/favicon.png">',
         '<link rel="apple-touch-icon" href="/icons/apple-touch-icon.png">']
    if public:
        h += ['<link rel="manifest" href="/manifest.webmanifest">',
              '<meta name="mobile-web-app-capable" content="yes">',
              '<meta name="apple-mobile-web-app-capable" content="yes">',
              '<meta name="apple-mobile-web-app-title" content="서강 한 바퀴">',
              '<meta name="apple-mobile-web-app-status-bar-style" content="default">',
              '<link rel="canonical" href="%s/">' % SITE,
              '<meta property="og:type" content="website">', '<meta property="og:locale" content="ko_KR">',
              '<meta property="og:site_name" content="서강 한 바퀴">',
              '<meta property="og:title" content="%s">' % html.escape(title, quote=True),
              '<meta property="og:description" content="%s">' % html.escape(desc, quote=True),
              '<meta property="og:url" content="%s/">' % SITE,
              '<meta property="og:image" content="%s/og.png">' % SITE,
              '<meta property="og:image:width" content="1200">', '<meta property="og:image:height" content="630">',
              '<meta name="twitter:card" content="summary_large_image">']
        if GOOGLE_VERIFY: h.append('<meta name="google-site-verification" content="%s">' % html.escape(GOOGLE_VERIFY, quote=True))
        if NAVER_VERIFY: h.append('<meta name="naver-site-verification" content="%s">' % html.escape(NAVER_VERIFY, quote=True))
    else:
        h += ['<meta name="robots" content="noindex, nofollow">']
    h += [extra_head, head_src.strip(), '</head>', '<body>', body, extra_body, '</body>', '</html>']
    return '\n'.join(x for x in h if x)

# ---------- 공개 페이지 ----------
pub_body = re.sub(r'<template id="tpl-dev">.*?</template>\n?', '', body_src, flags=re.S)
by = {}
for i_, d in rows: by.setdefault(d['category'], []).append(d)
nos = ['<noscript><div style="max-width:480px;margin:0 auto;padding:16px;font-family:sans-serif"><h1>서강 한 바퀴</h1><p>서강대 주변 맛집, 카페, 술집 목록입니다. 목록을 보려면 JavaScript를 켜 주세요.</p>']
for k in ['value', 'decent', 'regular', 'cafe', 'bar', 'lounge']:
    if k not in by: continue
    nos.append('<h2>%s</h2><ul>' % CAT[k])
    for d in sorted(by[k], key=lambda x: x['name']):
        meta = ' · '.join(x for x in [' '.join(d.get('kinds', [])), d.get('address', '')] if x)
        nos.append('<li>%s%s</li>' % (html.escape(d['name']), (' — ' + html.escape(meta)) if meta else ''))
    nos.append('</ul>')
nos.append('</div></noscript>')
ld = {'@context': 'https://schema.org', '@type': 'WebSite', 'name': '서강 한 바퀴', 'alternateName': ['서강한바퀴', 'Sogang Hanbakwi'],
      'url': SITE + '/', 'inLanguage': 'ko', 'description': '서강대 주변 맛집, 카페, 술집을 직접 가 보고 모은 목록'}
scripts = ('<script>window.__SINCE__="%s";window.__BUILT__="%s";</script>\n' % (SINCE, TODAY.replace('-', '.')) +
           '<script src="/assets/%s"></script>\n<script defer src="/assets/%s"></script>\n' % (shname, fbname) +
           '<script>if("serviceWorker"in navigator){addEventListener("load",function(){navigator.serviceWorker.register("/sw.js").catch(function(){})})}</script>')
# 본문 스크립트는 body_src 끝에 있으므로, 데이터 스크립트를 그 앞에 둔다.
j = pub_body.index('<script>\n(function () {')
pub_body = pub_body[:j] + scripts + '\n' + pub_body[j:]
pub = page('서강 한 바퀴 | 서강대 주변 맛집·카페·술집', '서강대 주변 맛집, 카페, 술집을 직접 가 보고 모은 목록. 가격·영업시간·메뉴를 확인하고 내 주변 가게를 찾아보세요.', True,
           '\n'.join(nos) + '\n' + pub_body, '<script type="application/ld+json">%s</script>' % json.dumps(ld, ensure_ascii=False))
open('public/index.html', 'w', encoding='utf8').write(pub)

# ---------- 관리 페이지 ----------
adm_body = body_src
j = adm_body.index('<script>\n(function () {')
adm_body = adm_body[:j] + '<script>window.__ADMIN__=true;</script>\n<script defer src="/assets/%s"></script>\n' % fbname + adm_body[j:]
os.makedirs('public/admin', exist_ok=True)
open('public/admin/index.html', 'w', encoding='utf8').write(page('서강 한 바퀴 관리', '관리자 전용', False, adm_body))

# ---------- 개인정보 처리방침 ----------
priv = '''<main style="max-width:640px;margin:0 auto;padding:24px 16px 64px;font-family:var(--font);line-height:1.7;color:var(--ink)">
<p><a href="/" style="color:var(--accent-ink)">← 서강 한 바퀴로 돌아가기</a></p>
<h1 style="font-size:26px">개인정보 처리방침</h1>
<p style="color:var(--muted)">시행일 %s</p>
<p>'서강 한 바퀴'(이하 "서비스")는 이용자의 개인정보를 아래와 같이 처리합니다. 로그인하지 않아도 가게 정보는 모두 볼 수 있으며, 로그인하는 경우에만 아래 정보가 처리됩니다.</p>
<h2>1. 처리하는 개인정보 항목</h2>
<ul>
<li>Google 계정으로 로그인할 때 Google이 제공하는 계정 식별자(UID), 이메일 주소, 이름, 프로필 사진 주소</li>
<li>이용자가 즐겨찾기한 가게 목록</li>
</ul>
<p>서비스는 광고나 이용 분석을 위한 추적 도구를 사용하지 않습니다. '내 주변' 기능에서 위치 권한을 허용하면 위치는 이용자의 기기 안에서 거리를 계산하는 데에만 쓰이고 서버로 보내지 않습니다.</p>
<h2>2. 처리 목적</h2>
<p>로그인 상태의 확인, 즐겨찾기를 계정에 저장하고 다른 기기에서 불러오기 위한 것입니다.</p>
<h2>3. 보유 및 이용 기간</h2>
<p>계정을 삭제할 때까지 보유하며, 이용자가 '더보기 &gt; 계정 삭제'를 누르면 서버에 저장된 즐겨찾기와 로그인 계정이 지체 없이 삭제됩니다. 이용자의 기기(브라우저)에 저장된 즐겨찾기는 계정 삭제와 별개이며 브라우저 데이터를 지우면 사라집니다.</p>
<h2>4. 처리 위탁 및 국외 처리</h2>
<p>서비스는 로그인과 데이터 저장에 Google LLC의 Firebase(Authentication, Cloud Firestore, Hosting)를 이용합니다. Google은 서비스 제공을 위해 위 정보를 처리하며, 일부 정보는 대한민국 밖의 서버에서 처리될 수 있습니다. 이 외에 개인정보를 제3자에게 제공하지 않습니다.</p>
<h2>5. 이용자의 권리</h2>
<p>이용자는 언제든지 계정을 삭제할 수 있고, 로그아웃하면 서비스는 계정 정보를 더 이상 사용하지 않습니다.</p>
<h2>6. 문의</h2>
<p>개인정보 관련 문의와 삭제 요청은 <a href="%s" style="color:var(--accent-ink)">의견 남기기 양식</a>으로 보내 주세요.</p>
<h2>7. 방침의 변경</h2>
<p>이 방침이 바뀌면 이 페이지에 시행일과 함께 알립니다.</p>
</main>''' % (TODAY.replace('-', '.'), FEEDBACK)
open('public/privacy.html', 'w', encoding='utf8').write(page('개인정보 처리방침 | 서강 한 바퀴', '서강 한 바퀴의 개인정보 처리방침', True, priv).replace('<link rel="manifest" href="/manifest.webmanifest">', '<link rel="manifest" href="/manifest.webmanifest">').replace('<link rel="canonical" href="%s/">' % SITE, '<link rel="canonical" href="%s/privacy">' % SITE))

# ---------- 서비스 워커, robots, sitemap ----------
ver = hashlib.sha256((shname + fbname + TODAY).encode()).hexdigest()[:8]
sw = '''const V = 'sg-%s';
self.addEventListener('install', function (e) { self.skipWaiting(); });
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (ks) { return Promise.all(ks.filter(function (k) { return k !== V; }).map(function (k) { return caches.delete(k); })); }).then(function () { return self.clients.claim(); }));
});
self.addEventListener('fetch', function (e) {
  var r = e.request; if (r.method !== 'GET') return;
  var u = new URL(r.url);
  if (u.origin !== location.origin || u.pathname.indexOf('/__/') === 0 || u.pathname.indexOf('/admin') === 0) return;
  if (u.pathname.indexOf('/assets/') === 0 || u.pathname.indexOf('/icons/') === 0) {
    e.respondWith(caches.open(V).then(function (c) { return c.match(r).then(function (hit) { return hit || fetch(r).then(function (res) { if (res.ok) c.put(r, res.clone()); return res; }); }); }));
    return;
  }
  if (r.mode === 'navigate' || (r.headers.get('accept') || '').indexOf('text/html') !== -1) {
    e.respondWith(fetch(r).then(function (res) { var cp = res.clone(); caches.open(V).then(function (c) { c.put(r, cp); }); return res; }).catch(function () { return caches.match(r).then(function (m) { return m || caches.match('/'); }); }));
  }
});
''' % ver
open('public/sw.js', 'w', encoding='utf8').write(sw)
open('public/robots.txt', 'w').write('User-agent: *\nAllow: /\nDisallow: /admin/\n\nSitemap: %s/sitemap.xml\n' % SITE)
open('public/sitemap.xml', 'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n<url><loc>%s/</loc><lastmod>%s</lastmod><changefreq>weekly</changefreq><priority>1.0</priority></url>\n<url><loc>%s/privacy</loc><lastmod>%s</lastmod><priority>0.2</priority></url>\n</urlset>\n' % (SITE, TODAY, SITE, TODAY))

# ---------- 관리 화면에서 한 번 올릴 가져오기 파일 ----------
imp = []
for i_, d in sorted(docs.items()):
    dd = dict(d); dd['updatedAt'] = BASELINE; imp.append({'id': i_, 'data': dd})
json.dump({'shops': imp}, open('shops_import.json', 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
print('shops(public)=%d docs=%d since=%s' % (len(rows), len(docs), SINCE))
for p in ['public/index.html', 'public/admin/index.html', 'public/assets/' + shname, 'public/assets/' + fbname]: print(p, os.path.getsize(p))
