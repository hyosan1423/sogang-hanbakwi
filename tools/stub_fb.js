// 테스트용 가짜 SGFB: 실제 Firebase 없이 화면 동작만 확인한다.
(function () {
  var listeners = { auth: [], delta: [], all: [], favs: [] }, user = null, calls = [];
  window.__calls = calls; window.__stub = {
    setUser: function (u) { user = u; listeners.auth.forEach(function (f) { f(user); }); },
    emitDelta: function (docs) { listeners.delta.forEach(function (f) { f(docs); }); },
    emitFavs: function (arr) { listeners.favs.forEach(function (f) { f(arr); }); }
  };
  var remoteFavs = window.__remoteFavs || null;
  window.SGFB = {
    isAdmin: function (u) { return !!(u && u.email === 'hyosanshin927@gmail.com'); },
    onAuth: function (cb) { listeners.auth.push(cb); setTimeout(function () { cb(user); }, 20); return function () {}; },
    login: function () { calls.push(['login']); return new Promise(function (res) { setTimeout(function () { window.__stub.setUser(window.__loginAs || { uid: 'u1', email: 'a@x.com', name: '테스터', photo: '' }); res(); }, 30); }); },
    logout: function () { calls.push(['logout']); return Promise.resolve().then(function () { window.__stub.setUser(null); }); },
    deleteAccount: function () { calls.push(['deleteAccount']); return Promise.resolve().then(function () { window.__stub.setUser(null); }); },
    watchDelta: function (since, cb) { calls.push(['watchDelta', since]); listeners.delta.push(cb); return function () {}; },
    watchAll: function (cb) { calls.push(['watchAll']); listeners.all.push(cb); setTimeout(function () { cb(window.__allDocs || []); }, 30); return function () {}; },
    newId: function () { return 'newid1'; },
    saveShop: function (id, data) { calls.push(['saveShop', id, data]); return Promise.resolve(id); },
    removeShop: function (id, name) { calls.push(['removeShop', id, name]); return Promise.resolve(); },
    importShops: function (list, prog) { calls.push(['importShops', list.length]); prog && prog(list.length, list.length); return Promise.resolve(list.length); },
    watchFavs: function (uid, cb) { calls.push(['watchFavs', uid]); listeners.favs.push(cb); setTimeout(function () { var m = window.__remoteByUid; cb(m ? (uid in m ? m[uid].slice() : null) : remoteFavs); }, 20); return function () {}; },
    setFavs: function (uid, arr) { calls.push(['setFavs', uid, arr.slice()]); if (window.__remoteByUid) window.__remoteByUid[uid] = arr.slice(); return Promise.resolve(); },
    redirectError: function () { return null; }
  };
})();
