import json, subprocess, time, sys, os, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'public')
stub = open(os.path.join(ROOT, 'tools/stub_fb.js'), encoding='utf8').read()

class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=PUB, **k)
    def log_message(self, *a): pass
    def translate_path(self, path):
        p = super().translate_path(path)
        if os.path.isdir(p) and not path.endswith('/'): pass
        return p
srv = socketserver.TCPServer(('127.0.0.1', 0), H); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = 'http://127.0.0.1:%d' % port
fails = []
def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + (' ' + str(extra) if extra else ''))
    if not cond: fails.append(name)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium', args=['--no-sandbox'])
    def newpage(init=''):
        ctx = b.new_context(viewport={'width': 400, 'height': 860}, locale='ko-KR', service_workers='block')
        pg = ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' else None)
        # fb.<hash>.js 를 가짜로 교체
        pg.route('**/assets/fb.*.js', lambda r: r.fulfill(status=200, content_type='application/javascript', body=init + stub))
        pg.route('https://fonts.googleapis.com/**', lambda r: r.abort()); pg.route('https://fonts.gstatic.com/**', lambda r: r.abort())
        return pg, errs

    # ---- 공개 페이지 ----
    pg, errs = newpage()
    pg.goto(BASE + '/'); pg.wait_for_timeout(600)
    check('공개: 제목', '서강 한 바퀴' in pg.title(), pg.title())
    n = pg.evaluate("window.__SHOPS__.length")
    check('공개: 배포본 가게 수 167', n == 167, n)
    check('공개: 델타 구독이 SINCE로 호출됨', pg.evaluate("window.__calls.filter(c=>c[0]==='watchDelta').length") == 1)
    check('공개: 델타 기준 시각이 고정값(재배포해도 관리자 수정이 사라지지 않음)', pg.evaluate("window.__calls.filter(c=>c[0]==='watchDelta')[0][1]") == '2026-10-05T00:00:00.000Z', pg.evaluate("window.__SINCE__"))
    pg.screenshot(path='/tmp/shot_home.png')
    # 즐겨찾기 탭 (로그아웃 상태)
    pg.get_by_role('button', name='즐겨찾기').click(); pg.wait_for_timeout(200)
    txt = pg.inner_text('#main')
    check('공개: 즐겨찾기에 로그인 유도', 'Google로 로그인' in txt and '이 기기에만' in txt, txt[:80])
    pg.screenshot(path='/tmp/shot_fav_out.png')
    # 더보기
    pg.get_by_role('button', name='더보기').click(); pg.wait_for_timeout(200)
    txt = pg.inner_text('#main')
    check('공개: 더보기에 홈 화면 추가 안내', '홈 화면에 추가' in txt and 'iPhone' in txt and 'Android' in txt)
    check('공개: 더보기에 계정/방침', '계정' in txt and '개인정보 처리방침' in txt)
    pg.screenshot(path='/tmp/shot_more.png', full_page=True)
    # 로그인 전 로컬 즐겨찾기 두 개 -> 로그인 후 병합/동기화
    pg.evaluate("localStorage.setItem('sg-fav', JSON.stringify(['back-10','cafe-18']))"); pg.reload(); pg.wait_for_timeout(500)
    pg.get_by_role('button', name='더보기').click(); pg.wait_for_timeout(100)
    pg.get_by_role('button', name='Google로 로그인').first.click(); pg.wait_for_timeout(500)
    calls = pg.evaluate("window.__calls")
    check('공개: 로그인 호출', ['login'] in calls)
    sf = [c for c in calls if c[0] == 'setFavs']
    check('공개: 로그인 시 로컬 즐겨찾기 2개가 서버로 병합', sf and sorted(sf[-1][2]) == ['back-10', 'cafe-18'], sf)
    txt = pg.inner_text('#main'); check('공개: 로그인 후 계정 표시', '테스터' in txt and '로그아웃' in txt and '계정 삭제' in txt)
    # 별 토글 -> setFavs 호출
    pg.evaluate("window.__calls.length=0")
    pg.get_by_role('button', name='즐겨찾기').click(); pg.wait_for_timeout(200)
    rows = pg.locator('.rows [data-fav]').count(); check('공개: 즐겨찾기 화면에 2곳', rows == 2, rows)
    pg.locator('.rows [data-fav]').first.click(); pg.wait_for_timeout(900)
    sf = pg.evaluate("window.__calls.filter(c=>c[0]==='setFavs')")
    check('공개: 별 해제 시 서버 갱신', sf and len(sf[-1][2]) == 1, sf)
    pg.screenshot(path='/tmp/shot_fav_in.png')
    # 델타: 수정 + 삭제 반영
    first = pg.evaluate("window.__SHOPS__[0][0]"); firstName = pg.evaluate("window.__SHOPS__[0][1].name")
    pg.get_by_role('button', name='홈').click(); pg.wait_for_timeout(100)
    pg.evaluate("""(a)=>{ window.__stub.emitDelta([{id:a[0], data:{deleted:true,name:a[1],category:'',updatedAt:'2026-10-06T00:00:00.000Z'}},{id:'zz-new', data:{name:'신규테스트가게',category:'cafe',food:'커피',updatedAt:'2026-10-06T00:00:00.000Z',kinds:[],menus:[]}}]) }""", [first, firstName])
    pg.wait_for_timeout(300)
    names = pg.evaluate("""()=>{ var t=document.body.innerText; return t }""")
    # 목록 화면에서 확인: 검색
    pg.goto(BASE + '/'); pg.wait_for_timeout(300)
    check('공개: 에러 로그 없음', not [e for e in errs if 'fonts' not in e and 'ERR_FAILED' not in e], errs[:3])
    # 로그아웃
    pg.get_by_role('button', name='더보기').click(); pg.wait_for_timeout(100)
    # ---- 홈 화면: 이미 저장된 계정 병합 플래그 + 원격 우선 ----
    pg.close()

    # 두 번째 기기: 원격 즐겨찾기가 있고 로컬은 비어 있음 -> 원격을 가져온다
    pg2, errs2 = newpage("window.__remoteFavs=['main-01','main-02','main-03'];")
    pg2.goto(BASE + '/'); pg2.wait_for_timeout(400)
    pg2.get_by_role('button', name='더보기').click(); pg2.get_by_role('button', name='Google로 로그인').first.click(); pg2.wait_for_timeout(500)
    fav = pg2.evaluate("JSON.parse(localStorage.getItem('sg-fav'))")
    check('기기2: 서버 즐겨찾기를 불러옴', sorted(fav) == ['main-01', 'main-02', 'main-03'], fav)
    # 계정 삭제 2단계
    pg2.evaluate("window.__calls.length=0")
    pg2.get_by_role('button', name='계정 삭제').click(); pg2.wait_for_timeout(100)
    check('기기2: 삭제는 한 번에 실행되지 않음', pg2.evaluate("window.__calls.filter(c=>c[0]==='deleteAccount').length") == 0)
    pg2.get_by_role('button', name='한 번 더 눌러 계정 삭제').click(); pg2.wait_for_timeout(300)
    check('기기2: 두 번째 클릭에서 삭제 호출', pg2.evaluate("window.__calls.filter(c=>c[0]==='deleteAccount').length") == 1)
    pg2.close()

    # ---- 같은 브라우저에서 계정 전환: A의 즐겨찾기가 B에게 새면 안 된다 ----
    def loginas(pg, uid):
        pg.evaluate("(u)=>{ window.__loginAs={uid:u,email:u+'@x.com',name:u,photo:''} }", uid)
        pg.get_by_role('button', name='더보기').click(); pg.wait_for_timeout(100)
        pg.get_by_role('button', name='Google로 로그인').first.click(); pg.wait_for_timeout(500)
    def logout(pg):
        pg.get_by_role('button', name='더보기').click(); pg.wait_for_timeout(100)
        pg.get_by_role('button', name='로그아웃').first.click(); pg.wait_for_timeout(400)
    def lsfav(pg): return pg.evaluate("JSON.parse(localStorage.getItem('sg-fav')||'[]')")
    def remote(pg, uid): return pg.evaluate("(u)=>window.__remoteByUid[u]||null", uid)

    pg3, errs3 = newpage("window.__remoteByUid={};")
    pg3.goto(BASE + '/'); pg3.wait_for_timeout(300)
    pg3.evaluate("localStorage.setItem('sg-fav', JSON.stringify(['anon-1']))"); pg3.reload(); pg3.wait_for_timeout(500)
    check('전환: 로그인 전 로컬 즐겨찾기는 로그아웃 상태에서 지워지지 않음', lsfav(pg3) == ['anon-1'], lsfav(pg3))
    loginas(pg3, 'uA')
    check('전환: A 로그인 시 로그인 전 즐겨찾기가 A 계정에 합쳐짐', remote(pg3, 'uA') == ['anon-1'], remote(pg3, 'uA'))
    pg3.evaluate("window.__remoteByUid.uA=['anon-1','fa-2']; window.__stub.emitFavs(['anon-1','fa-2'])"); pg3.wait_for_timeout(200)
    check('전환: A의 즐겨찾기 사본이 로컬에 있음', sorted(lsfav(pg3)) == ['anon-1', 'fa-2'], lsfav(pg3))
    logout(pg3)
    check('전환: 로그아웃하면 로컬 즐겨찾기 사본이 비워짐', lsfav(pg3) == [], lsfav(pg3))
    pg3.get_by_role('button', name='즐겨찾기').click(); pg3.wait_for_timeout(200)
    check('전환: 로그아웃 후 즐겨찾기 화면이 비어 있음', pg3.locator('.rows [data-fav]').count() == 0, pg3.inner_text('#main')[:60])
    loginas(pg3, 'uB')
    check('전환: B에게 A의 즐겨찾기가 보이지 않음(로컬)', lsfav(pg3) == [], lsfav(pg3))
    check('전환: B 계정에 A의 즐겨찾기가 저장되지 않음(서버)', 'anon-1' not in (remote(pg3, 'uB') or []) and 'fa-2' not in (remote(pg3, 'uB') or []), remote(pg3, 'uB'))
    pg3.evaluate("window.__remoteByUid.uB=['b-1']; window.__stub.emitFavs(['b-1'])"); pg3.wait_for_timeout(200)
    logout(pg3)
    loginas(pg3, 'uA')
    check('전환: A로 다시 로그인하면 A의 즐겨찾기가 서버에서 복원됨', sorted(lsfav(pg3)) == ['anon-1', 'fa-2'], lsfav(pg3))
    check('전환: A로 돌아와도 B의 즐겨찾기가 섞이지 않음', 'b-1' not in lsfav(pg3) and remote(pg3, 'uB') == ['b-1'], (lsfav(pg3), remote(pg3, 'uB')))
    check('전환: 에러 로그 없음', not [e for e in errs3 if 'fonts' not in e and 'ERR_FAILED' not in e], errs3[:3])
    pg3.close()

    # ---- 이전 버전에서 로그인한 적 있는 기기(업데이트 직후) ----
    pg4, errs4 = newpage("window.__remoteByUid={};")
    pg4.goto(BASE + '/'); pg4.wait_for_timeout(300)
    pg4.evaluate("localStorage.removeItem('sg-fav-owner'); localStorage.setItem('sg-fav', JSON.stringify(['old-A'])); localStorage.setItem('sg-fav-m-uA','1')"); pg4.reload(); pg4.wait_for_timeout(500)
    loginas(pg4, 'uB')
    check('업데이트 직후: 이전 계정이 남긴 로컬 목록이 B에게 합쳐지지 않음', 'old-A' not in lsfav(pg4) and 'old-A' not in (remote(pg4, 'uB') or []), (lsfav(pg4), remote(pg4, 'uB')))
    pg4.close()

    # ---- 관리 페이지 ----
    pa, ea = newpage("window.__allDocs=[{id:'x1',data:{name:'테스트집',category:'decent',food:'국밥',kinds:['한식'],menus:[],updatedAt:'2026-10-05T00:00:00.000Z'}},{id:'x2',data:{name:'대기집',category:'',food:'?',kinds:[],menus:[],updatedAt:'2026-10-05T00:00:00.000Z'}}];")
    pa.goto(BASE + '/admin/'); pa.wait_for_timeout(500)
    txt = pa.inner_text('#main'); check('관리: 로그인 전에는 잠금 화면', '관리자 계정으로 로그인' in txt and pa.locator('#tabbar button').count() == 0, txt[:60])
    pa.screenshot(path='/tmp/shot_admin_gate.png')
    # 일반 계정 로그인 -> 권한 없음
    pa.evaluate("window.__loginAs={uid:'u9',email:'other@x.com',name:'다른',photo:''}")
    pa.get_by_role('button', name='Google로 로그인').click(); pa.wait_for_timeout(400)
    txt = pa.inner_text('#main'); check('관리: 일반 계정은 권한 없음', '관리자 권한이 없습니다' in txt, txt[:80])
    pa.get_by_role('button', name='로그아웃').click(); pa.wait_for_timeout(200)
    pa.evaluate("window.__loginAs={uid:'u1',email:'hyosanshin927@gmail.com',name:'효산',photo:''}")
    pa.get_by_role('button', name='Google로 로그인').click(); pa.wait_for_timeout(500)
    check('관리: 관리자 로그인 후 탭에 입력/분류', pa.locator('#tabbar').inner_text().count('입력') == 1 and '분류' in pa.locator('#tabbar').inner_text())
    pa.get_by_role('button', name='입력').click(); pa.wait_for_timeout(300)
    pa.fill('#f-name', '새가게'); pa.select_option('#f-category', 'cafe'); pa.fill('#f-food', '커피'); pa.click('#save'); pa.wait_for_timeout(400)
    sv = pa.evaluate("window.__calls.filter(c=>c[0]==='saveShop')")
    check('관리: 저장이 SGFB.saveShop(newid1)로 전달', sv and sv[-1][1] == 'newid1' and sv[-1][2]['name'] == '새가게' and sv[-1][2]['category'] == 'cafe' and sv[-1][2]['updatedAt'], sv)
    # 가져오기
    print('TAB:', pa.locator('#tabbar').inner_text(), '| view', pa.evaluate("document.querySelector('.view').dataset.view"), '| status', pa.inner_text('#status'))
    open('/tmp/imp.json', 'w').write(json.dumps({'shops': [{'id': 'a', 'data': {'name': 'A', 'updatedAt': 'x'}}]}))
    pa.set_input_files('#imp-file', '/tmp/imp.json'); pa.click('#imp-btn'); pa.wait_for_timeout(400)
    check('관리: 가져오기 호출', pa.evaluate("window.__calls.filter(c=>c[0]==='importShops').length") == 1 and '완료' in pa.inner_text('#imp-status'), pa.inner_text('#imp-status'))
    with pa.expect_download() as dl: pa.click('#exp-btn')
    path = dl.value.path(); ex = json.load(open(path, encoding='utf8'))
    check('관리: 내보내기 파일에 가게가 들어 있음', len(ex['shops']) == 2 and ex['shops'][0]['id'] in ('x1','x2') and 'name' in ex['shops'][0]['data'], len(ex['shops']))
    pa.screenshot(path='/tmp/shot_admin_dev.png')
    check('관리: 에러 로그 없음', not [e for e in ea if 'fonts' not in e and 'ERR_FAILED' not in e], ea[:3])
    b.close()
srv.shutdown()
print('FAILS:', fails)
sys.exit(1 if fails else 0)
