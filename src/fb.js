// Firebase 연결부. 앱 본문(app.src.html)은 window.SGFB 만 사용한다.
import { initializeApp } from 'firebase/app';
import {
  getAuth, GoogleAuthProvider, signInWithPopup, signInWithRedirect, getRedirectResult,
  onAuthStateChanged, signOut, deleteUser, reauthenticateWithPopup, reauthenticateWithRedirect
} from 'firebase/auth';
import {
  initializeFirestore, getFirestore, persistentLocalCache, persistentMultipleTabManager,
  collection, doc, onSnapshot, setDoc, deleteDoc, getDoc, query, where, writeBatch
} from 'firebase/firestore';

var CFG = {
  apiKey: 'AIzaSyDyInetAAvkaMw6aSaKPBhSvHmkvVGwT2s',
  authDomain: 'sogang-hanbakwi.firebaseapp.com',
  projectId: 'sogang-hanbakwi',
  storageBucket: 'sogang-hanbakwi.firebasestorage.app',
  messagingSenderId: '892368943864',
  appId: '1:892368943864:web:124dfb892af7922dff190d'
};
// 관리자 이메일. firestore.rules 의 isAdmin() 과 반드시 같아야 한다.
var ADMINS = ['hyosanshin927@gmail.com'];

// 앱을 호스팅하는 도메인이 Firebase 기본 도메인이면 그 도메인을 로그인 도메인으로 쓴다(리다이렉트 로그인 안정성).
try { if (/\.(web\.app|firebaseapp\.com)$/.test(location.hostname)) CFG.authDomain = location.hostname; } catch (e) {}

var app = initializeApp(CFG);
var auth = getAuth(app);
auth.languageCode = 'ko';
var db;
try {
  db = initializeFirestore(app, { localCache: persistentLocalCache({ tabManager: persistentMultipleTabManager() }) });
} catch (e) { db = getFirestore(app); }

function plain(u) { return u ? { uid: u.uid, email: u.email || '', name: u.displayName || '', photo: u.photoURL || '' } : null; }
function isStandalone() {
  try { return !!(navigator.standalone || (window.matchMedia && matchMedia('(display-mode: standalone)').matches)); } catch (e) { return false; }
}
function mapDocs(snap) { return snap.docs.map(function (d) { return { id: d.id, data: d.data() }; }); }
function newId() { return doc(collection(db, 'shops')).id; }

var redirectErr = null;
getRedirectResult(auth).catch(function (e) { redirectErr = e; });

window.SGFB = {
  isAdmin: function (u) { return !!(u && u.email && ADMINS.indexOf(u.email.toLowerCase()) !== -1); },
  onAuth: function (cb) { return onAuthStateChanged(auth, function (u) { cb(plain(u)); }); },
  login: function () {
    var p = new GoogleAuthProvider(); p.setCustomParameters({ prompt: 'select_account' });
    if (isStandalone()) return signInWithRedirect(auth, p);
    return signInWithPopup(auth, p).catch(function (e) {
      if (e && (e.code === 'auth/popup-blocked' || e.code === 'auth/operation-not-supported-in-this-environment')) return signInWithRedirect(auth, p);
      throw e;
    });
  },
  logout: function () { return signOut(auth); },
  // 계정 삭제: 즐겨찾기 문서를 지운 뒤 인증 계정을 지운다. 최근 로그인이 필요하면 다시 로그인시킨다.
  deleteAccount: function () {
    var u = auth.currentUser; if (!u) return Promise.reject({ code: 'auth/no-user' });
    var run = function () { return deleteDoc(doc(db, 'users', u.uid)).then(function () { return deleteUser(u); }); };
    return run().catch(function (e) {
      if (e && e.code === 'auth/requires-recent-login') {
        var p = new GoogleAuthProvider();
        if (isStandalone()) return reauthenticateWithRedirect(u, p);
        return reauthenticateWithPopup(u, p).then(run);
      }
      throw e;
    });
  },
  // 가게: 배포본(스냅샷) 이후에 바뀐 문서만 구독한다.
  watchDelta: function (sinceISO, cb, eb) {
    return onSnapshot(query(collection(db, 'shops'), where('updatedAt', '>', sinceISO)), function (s) { cb(mapDocs(s)); }, eb);
  },
  watchAll: function (cb, eb) { return onSnapshot(collection(db, 'shops'), function (s) { cb(mapDocs(s)); }, eb); },
  newId: newId,
  saveShop: function (id, data) { return setDoc(doc(db, 'shops', id), data).then(function () { return id; }); },
  // 삭제는 표식(deleted)을 남기는 방식이다. 이렇게 해야 배포본에 들어 있는 가게도 사용자 화면에서 사라진다.
  removeShop: function (id, name) {
    return setDoc(doc(db, 'shops', id), { deleted: true, name: String(name || ''), category: '', updatedAt: new Date().toISOString() });
  },
  importShops: function (list, onProgress) {
    var i = 0, done = 0;
    function next() {
      if (i >= list.length) return Promise.resolve(done);
      var b = writeBatch(db), part = list.slice(i, i + 400);
      part.forEach(function (r) { b.set(doc(db, 'shops', r.id), r.data); });
      i += 400;
      return b.commit().then(function () { done += part.length; if (onProgress) onProgress(done, list.length); return next(); });
    }
    return next();
  },
  // 즐겨찾기: users/{uid} 문서 하나에 id 배열로 보관한다.
  watchFavs: function (uid, cb, eb) {
    return onSnapshot(doc(db, 'users', uid), function (s) { cb(s.exists() && Array.isArray(s.data().favs) ? s.data().favs : null); }, eb);
  },
  setFavs: function (uid, arr) { return setDoc(doc(db, 'users', uid), { favs: arr, updatedAt: new Date().toISOString() }); },
  redirectError: function () { return redirectErr; }
};
