// frontend/node_modules/svelte/src/internal/shared/utils.js
var e = Array.isArray, t = Array.prototype.indexOf, n = Array.prototype.includes, r = Array.from, i = Object.defineProperty, a = Object.getOwnPropertyDescriptor, o = Object.getOwnPropertyDescriptors, s = Object.prototype, c = Array.prototype, l = Object.getPrototypeOf, u = Object.isExtensible, d = () => {};
function f(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function p() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var m = 1024, h = 2048, g = 4096, _ = 8192, v = 16384, y = 32768, b = 1 << 25, x = 65536, S = 1 << 19, ee = 1 << 20, te = 1 << 25, C = 1 << 21, ne = 1 << 22, re = 1 << 23, ie = Symbol("$state"), ae = Symbol("component"), oe = Symbol("legacy props"), se = Symbol(""), ce = Symbol("attributes"), le = Symbol("class"), ue = Symbol("style"), de = Symbol("text"), fe = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), pe = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml"), me = {}, w = Symbol("uninitialized"), he = "http://www.w3.org/1999/xhtml";
function ge() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function _e(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function ve() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
// frontend/node_modules/svelte/src/internal/client/dom/hydration.js
var T = !1;
function ye(e) {
	T = e;
}
var E;
function D(e) {
	if (e === null) throw _e(), me;
	return E = e;
}
function be() {
	return D(/* @__PURE__ */ R(E));
}
function xe(e) {
	if (T) {
		if (/* @__PURE__ */ R(E) !== null) throw _e(), me;
		E = e;
	}
}
function Se(e = 1) {
	if (T) {
		for (var t = e, n = E; t--;) n = /* @__PURE__ */ R(n);
		E = n;
	}
}
function Ce(e = !0) {
	for (var t = 0, n = E;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ R(n);
		e && n.remove(), n = i;
	}
}
function we(e) {
	if (!e || e.nodeType !== 8) throw _e(), me;
	return e.data;
}
// frontend/node_modules/svelte/src/internal/client/reactivity/equality.js
function Te(e) {
	return e === this.v;
}
function Ee(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function De(e) {
	return !Ee(e, this.v);
}
function Oe(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
// frontend/node_modules/svelte/src/internal/client/errors.js
function ke() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function Ae(e, t, n) {
	throw Error("https://svelte.dev/e/each_key_duplicate");
}
function je() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Me(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Ne() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Pe() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Fe() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Ie() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
// frontend/node_modules/svelte/src/internal/shared/context.js
function Le(e) {
	let t = e.p;
	for (; t !== null && t.c === null;) t = t.p;
	return t?.c ?? null;
}
function Re(e, t) {
	return e === null && Oe(t), e.c ??= new Map(Le(e) || void 0);
}
// frontend/node_modules/svelte/src/internal/client/context.js
var O = null;
function ze(e) {
	O = e;
}
function Be() {
	return Re(O, "getAllContexts");
}
function Ve(e, t = !1, n) {
	O = {
		p: O,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: q,
		l: null
	};
}
function He(e) {
	var t = O, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) en(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, O = t.p, Ue(e);
}
function Ue(e = {}) {
	return i(e, ae, { value: !0 }), e;
}
function We() {
	return !0;
}
// frontend/node_modules/svelte/src/internal/client/dom/task.js
var Ge = [];
function Ke() {
	var e = Ge;
	Ge = [], f(e);
}
function qe(e) {
	if (Ge.length === 0 && !mt) {
		var t = Ge;
		queueMicrotask(() => {
			t === Ge && Ke();
		});
	}
	Ge.push(e);
}
// frontend/node_modules/svelte/src/internal/client/reactivity/status.js
var Je = ~(h | g | m);
function k(e, t) {
	e.f = e.f & Je | t;
}
function Ye(e) {
	e.f & 512 || e.deps === null ? k(e, m) : k(e, g);
}
// frontend/node_modules/svelte/src/internal/client/reactivity/utils.js
function Xe(e, t) {
	e.f & 2048 ? t.set(e, h) : e.f & 4096 && t.get(e) !== 2048 && t.set(e, g), k(e, m);
}
// frontend/node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function Ze(e) {
	var t = W, n = q;
	K(null), J(null);
	try {
		return e();
	} finally {
		K(t), J(n);
	}
}
// frontend/node_modules/svelte/src/internal/client/reactivity/async.js
function Qe(e, t, n, r) {
	let i = We() ? nt : at;
	var a = e.filter((e) => !e.settled), o = t.map(i);
	if (n.length === 0 && a.length === 0) {
		r(o);
		return;
	}
	var s = q, c = $e(), l = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function u(e) {
		if (!(s.f & 16384)) {
			c();
			try {
				r([...o, ...e]);
			} catch (e) {
				z(e, s);
			}
			et();
		}
	}
	var d = tt();
	if (n.length === 0) {
		l.then(() => u([])).finally(d);
		return;
	}
	function f() {
		Promise.all(n.map((e) => /* @__PURE__ */ it(e))).then(u).catch((e) => z(e, s)).finally(d);
	}
	l ? l.then(() => {
		s.f & 16384 ? d() : (c(), f(), et());
	}) : f();
}
function $e() {
	var e = q, t = W, n = O, r = A;
	return function(i = !0) {
		J(e), K(t), ze(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function et(e = !0) {
	J(null), K(null), ze(null), e && A?.deactivate();
}
function tt() {
	var e = q, t = e.b, n = A, r = !!t?.is_rendered();
	return t?.update_pending_count(1, n), n.increment(r, e), () => {
		t?.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/*#__NO_SIDE_EFFECTS__*/
function nt(e) {
	var t = 2 | h;
	return q !== null && (q.f |= S), {
		ctx: O,
		deps: null,
		effects: null,
		equals: Te,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: w,
		wv: 0,
		parent: q,
		ac: null
	};
}
var rt = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function it(e, t, n) {
	let r = q;
	r === null && ke();
	var i = void 0, a = Ot(w), o = !W, s = /* @__PURE__ */ new Set();
	return nn(() => {
		var t = q, n = p();
		i = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== fe && n.reject(e);
			}).finally(et);
		} catch (e) {
			n.reject(e), et();
		}
		var c = A;
		if (o) {
			if (t.f & 32768) var l = tt();
			if (r.b?.is_rendered()) c.async_deriveds.get(t)?.reject(rt);
			else for (let e of s.values()) e.reject(rt);
			s.add(n), c.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), s.delete(n), t !== rt && (c.activate(), t ? (a.f |= re, Mt(a, t)) : (a.f & 8388608 && (a.f ^= re), Mt(a, e)), c.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), $t(() => {
		for (let e of s) e.reject(rt);
	}), new Promise((e) => {
		function t(n) {
			function r() {
				n === i ? e(a) : t(i);
			}
			n.then(r, r);
		}
		t(i);
	});
}
/*#__NO_SIDE_EFFECTS__*/
function at(e) {
	let t = /* @__PURE__ */ nt(e);
	return t.equals = De, t;
}
function ot(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) H(t[n]);
	}
}
function st(e) {
	var t, n = q, r = e.parent;
	if (!U && r !== null && e.v !== w && r.f & 24576) return ge(), e.v;
	J(r);
	try {
		ot(e), t = On(e);
	} finally {
		J(n);
	}
	return t;
}
function ct(e) {
	var t = st(e);
	!e.equals(t) && (e.wv = Tn(), (!A?.is_fork || e.deps === null) && (A === null ? e.v = t : (A.capture(e, t, !0), ft?.capture(e, t, !0)), e.deps === null)) ? k(e, m) : U || (j === null ? Ye(e) : (Qt() || A?.is_fork) && j.set(e, t));
}
function lt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac !== null && Ze(() => {
		t.ac.abort(fe), t.ac = null;
	}), t.fn !== null && (t.teardown = d), jn(t, 0), cn(t));
}
function ut(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && Mn(t);
}
// frontend/node_modules/svelte/src/internal/client/reactivity/batch.js
var dt = null, A = null, ft = null, j = null, pt = null, mt = !1, ht = !1, gt = null, _t = null, vt = 0, yt = 1, bt = class e {
	id = yt++;
	started = !1;
	linked = !0;
	prev = null;
	next = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	#e = /* @__PURE__ */ new Set();
	#t = /* @__PURE__ */ new Set();
	#n = 0;
	#r = /* @__PURE__ */ new Map();
	#i = null;
	#a = [];
	#o = [];
	#s = /* @__PURE__ */ new Map();
	#c = /* @__PURE__ */ new Map();
	#l = /* @__PURE__ */ new Set();
	is_fork = !1;
	#u = !1;
	constructor() {
		dt === null ? dt = this : (dt.next = this, this.prev = dt), dt = this;
	}
	#d() {
		if (this.is_fork) return !0;
		for (let e of this.#r.keys()) if (!this.#f(e)) return !0;
		return !1;
	}
	#f(e) {
		for (var t = e; t !== null; t = t.parent) if (this.#c.has(t)) return !0;
		return !1;
	}
	skip_effect(e) {
		this.#c.has(e) || this.#c.set(e, {
			d: [],
			m: []
		}), this.#l.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#c.get(e);
		if (n) {
			this.#c.delete(e);
			for (var r of n.d) k(r, h), t(r);
			for (r of n.m) k(r, g), t(r);
		}
		this.#l.add(e);
	}
	#p() {
		var e = [];
		for (let i of this.#a) if (!(i.f & 16384 || !(i.f & 6144))) {
			for (var t = i, n = !1; t.parent !== null;) {
				t = t.parent;
				var r = t.f;
				if (r & 96) {
					if (!(r & 1024)) {
						n = !0;
						break;
					}
					t.f ^= m;
				}
			}
			n || e.push(t);
		}
		return this.#a = [], e;
	}
	#m() {
		this.started = !0;
		for (let [e, t] of this.#s) k(e, t), this.schedule(e);
		this.apply();
		for (var t = gt = [], n = [], r = _t = []; this.#a.length > 0;) {
			vt++ > 1e3 && (this.#b(), xt());
			for (let e of this.#p()) try {
				this.#h(e, t, n);
			} catch (t) {
				throw Tt(e), this.#d() || this.discard(), t;
			}
		}
		if (A = null, r.length > 0) {
			var i = e.ensure();
			for (let e of r) i.schedule(e);
		}
		if (gt = null, _t = null, this.#d()) {
			this.#y(n), this.#y(t);
			for (let [e, t] of this.#c) wt(e, t);
			r.length > 0 && A.#m();
			return;
		}
		let a = this.#g();
		if (a) this.#y(n), this.#y(t), a.#v(this);
		else {
			this.#s.clear();
			for (let e of this.#e) e(this);
			this.#e.clear(), ft = this, St(n), St(t), ft = null, this.#i?.resolve();
			var o = A;
			this.#n === 0 && (this.#a.length === 0 || o !== null) && this.#b(), o !== null && (N.clear(), o.#m());
		}
	}
	#h(e, t, n) {
		e.f ^= m;
		for (var r = e.first; r !== null;) {
			var i = r.f, a = !!(i & 96);
			if (!(a && i & 1024 || i & 8192 || this.#c.has(r)) && r.fn !== null) {
				a ? r.f ^= m : i & 4 ? t.push(r) : En(r) && (i & 16 && this.add_dirty_reaction(r, g), Mn(r));
				var o = r.first;
				if (o !== null) {
					r = o;
					continue;
				}
			}
			for (; r !== null;) {
				var s = r.next;
				if (s !== null) {
					r = s;
					break;
				}
				r = r.parent;
			}
		}
	}
	#g() {
		for (var e = this.prev; e !== null; e = e.prev) if (!e.is_fork && this.#_(e)) return e;
		return null;
	}
	#_(e) {
		for (let [t, [, n]] of this.current) if (!n && e.current.has(t)) return !0;
		return !1;
	}
	#v(e) {
		for (let [t, n] of e.current) !this.previous.has(t) && e.previous.has(t) && this.previous.set(t, e.previous.get(t)), this.current.set(t, n);
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && n.promise.then(e.resolve).catch(e.reject);
		}
		e.async_deriveds.clear(), this.transfer_reactions(e.#s);
		let t = (e) => {
			var n = e.reactions;
			if (n !== null && !(e.f & 2 && !(e.f & 6144))) for (let e of n) {
				var r = e.f;
				if (r & 2) t(e);
				else {
					var i = e;
					r & 4194320 && !this.async_deriveds.has(i) && (this.#s.delete(i), k(i, h), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#b(), A = this, this.#m();
	}
	#y(e) {
		for (var t = 0; t < e.length; t += 1) Xe(e[t], this.#s);
	}
	capture(e, t, n = !1) {
		e.v !== w && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), j?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		A = this;
	}
	deactivate() {
		A = null, j = null;
	}
	flush() {
		try {
			ht = !0, A = this, this.#m();
		} finally {
			vt = 0, pt = null, gt = null, _t = null, ht = !1, A = null, j = null, N.clear();
		}
	}
	discard() {
		for (let e of this.#t) e(this);
		this.#t.clear();
		for (let e of this.async_deriveds.values()) e.reject(rt);
		this.#b(), this.#i?.resolve();
	}
	register_created_effect(e) {
		this.#o.push(e);
	}
	increment(e, t) {
		if (this.#n += 1, e) {
			let e = this.#r.get(t) ?? 0;
			this.#r.set(t, e + 1);
		}
	}
	decrement(e, t) {
		if (--this.#n, e) {
			let e = this.#r.get(t) ?? 0;
			e === 1 ? this.#r.delete(t) : this.#r.set(t, e - 1);
		}
		this.#u || (this.#u = !0, qe(() => {
			this.#u = !1, this.linked && this.flush();
		}));
	}
	transfer_reactions(e) {
		for (let [t, n] of e) this.add_dirty_reaction(t, n);
		e.clear();
	}
	add_dirty_reaction(e, t) {
		(t === 2048 || this.#s.get(e) !== 2048) && this.#s.set(e, t);
	}
	oncommit(e) {
		this.#e.add(e);
	}
	ondiscard(e) {
		this.#t.add(e);
	}
	settled() {
		return (this.#i ??= p()).promise;
	}
	static ensure() {
		if (A === null) {
			let t = A = new e();
			!ht && qe(() => {
				t.started || t.flush();
			});
		}
		return A;
	}
	apply() {
		j = null;
	}
	schedule(e) {
		pt = e, e.b?.is_pending && e.f & 16777228 && !(e.f & 32768) ? e.b.defer_effect(e) : this.#a.push(e);
	}
	#b() {
		if (this.linked) {
			var e = this.prev, t = this.next;
			e === null || (e.next = t), t === null ? dt = e : t.prev = e, this.linked = !1;
		}
	}
};
function xt() {
	try {
		je();
	} catch (e) {
		z(e, pt);
	}
}
var M = null;
function St(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && En(r) && (M = /* @__PURE__ */ new Set(), Mn(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && dn(r), M?.size > 0)) {
				N.clear();
				for (let e of M) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) M.has(n) && (M.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || Mn(n);
					}
				}
				M.clear();
			}
		}
		M = null;
	}
}
function Ct(e) {
	A.schedule(e);
}
function wt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), k(e, m);
		for (var n = e.first; n !== null;) wt(n, t), n = n.next;
	}
}
function Tt(e) {
	k(e, m);
	for (var t = e.first; t !== null;) Tt(t), t = t.next;
}
// frontend/node_modules/svelte/src/internal/client/reactivity/sources.js
var Et = /* @__PURE__ */ new Set(), N = /* @__PURE__ */ new Map(), Dt = !1;
function Ot(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Te,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function P(e, t) {
	let n = Ot(e, t);
	return yn(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function kt(e, t = !1, n = !0) {
	let r = Ot(e);
	return t || (r.equals = De), r;
}
function F(e, t, n = !1) {
	return W !== null && (!G || W.f & 131072) && We() && W.f & 4325394 && (Y === null || !Y.has(e)) && Fe(), Mt(e, n ? It(t) : t, _t);
}
var At = null, jt = 0;
function Mt(e, t, n = null) {
	if (!e.equals(t)) {
		U ? N.set(e, t) : N.has(e) || N.set(e, e.v);
		var r = bt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && st(t), j === null && Ye(t);
		}
		e.wv = Tn(), At = null, jt = 0, Ft(e, h, n), At = null, We() && q !== null && q.f & 1024 && !(q.f & 96) && (Q === null ? bn([e]) : Q.push(e)), !r.is_fork && Et.size > 0 && !Dt && Nt();
	}
	return t;
}
function Nt() {
	Dt = !1;
	for (let e of Et) {
		e.f & 1024 && k(e, g);
		let t;
		try {
			t = En(e);
		} catch {
			t = !0;
		}
		t && Mn(e);
	}
	Et.clear();
}
function Pt(e) {
	F(e, e.v + 1);
}
function Ft(e, t, n) {
	var r = e.reactions;
	if (r !== null) {
		var i = We(), a = r.length;
		if (jt += a, jt > 1e5 && At === null && (At = /* @__PURE__ */ new Set()), At !== null) {
			if (At.has(e)) return;
			At.add(e);
		}
		for (var o = 0; o < a; o++) {
			var s = r[o], c = s.f;
			if (i || s !== q) {
				var l = (c & h) === 0;
				if (l && k(s, t), c & 131072) Et.add(s);
				else if (c & 2) {
					var u = s;
					j?.delete(u), Ft(u, g, n);
				} else if (l) {
					var d = s;
					c & 16 && M !== null && M.add(d), n === null ? Ct(d) : n.push(d);
				}
			}
		}
	}
}
function It(t) {
	if (typeof t != "object" || !t || ie in t || ae in t) return t;
	let n = l(t);
	if (n !== s && n !== c) return t;
	var r = /* @__PURE__ */ new Map(), i = e(t), o = /* @__PURE__ */ P(0), u = null, d = Cn, f = (e) => {
		if (Cn === d) return e();
		var t = W, n = Cn;
		K(null), wn(d);
		var r = e();
		return K(t), wn(n), r;
	};
	return i && r.set("length", /* @__PURE__ */ P(t.length, u)), new Proxy(t, {
		defineProperty(e, t, n) {
			"value" in n && n.configurable !== !1 && n.enumerable !== !1 && n.writable !== !1 || Ne();
			var i = r.get(t);
			return i === void 0 ? f(() => {
				var e = /* @__PURE__ */ P(n.value, u);
				return r.set(t, e), e;
			}) : F(i, n.value, !0), !0;
		},
		deleteProperty(e, t) {
			var n = r.get(t);
			if (n === void 0) {
				if (t in e) {
					let e = f(() => /* @__PURE__ */ P(w, u));
					r.set(t, e), Pt(o);
				}
			} else F(n, w), Pt(o);
			return !0;
		},
		get(e, n, i) {
			if (n === ie) return t;
			var o = r.get(n), s = n in e;
			if (o === void 0 && (!s || a(e, n)?.writable) && (o = f(() => /* @__PURE__ */ P(It(s ? e[n] : w), u)), r.set(n, o)), o !== void 0) {
				var c = $(o);
				return c === w ? void 0 : c;
			}
			return Reflect.get(e, n, i);
		},
		getOwnPropertyDescriptor(e, t) {
			this.has?.(e, t);
			var n = Reflect.getOwnPropertyDescriptor(e, t), i = r.get(t);
			if (i !== void 0) {
				var a = $(i);
				if (a === w) return;
				if (n && "value" in n) n.value = a;
				else return {
					enumerable: !0,
					configurable: !0,
					value: a,
					writable: !0
				};
			}
			return n;
		},
		has(e, t) {
			if (t === ie) return !0;
			var n = r.get(t), i = n !== void 0 && n.v !== w || Reflect.has(e, t);
			return (n !== void 0 || (q !== null || W !== null) && (!i || a(e, t)?.writable)) && (n === void 0 && (n = f(() => /* @__PURE__ */ P(i ? It(e[t]) : w, u)), r.set(t, n)), $(n) === w) ? !1 : i;
		},
		set(e, t, n, s) {
			var c = r.get(t), l = t in e;
			if (i && t === "length") for (var d = n; d < c.v; d += 1) {
				var p = r.get(d + "");
				p === void 0 ? d in e && (p = f(() => /* @__PURE__ */ P(w, u)), r.set(d + "", p)) : F(p, w);
			}
			if (c === void 0) (!l || a(e, t)?.writable) && (c = f(() => /* @__PURE__ */ P(void 0, u)), F(c, It(n)), r.set(t, c));
			else {
				l = c.v !== w;
				var m = f(() => It(n));
				F(c, m);
			}
			var h = Reflect.getOwnPropertyDescriptor(e, t);
			if (h?.set && h.set.call(s, n), !l) {
				if (i && typeof t == "string") {
					var g = r.get("length"), _ = Number(t);
					Number.isInteger(_) && _ >= g.v && F(g, _ + 1);
				}
				Pt(o);
			}
			return !0;
		},
		ownKeys(e) {
			$(o);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = r.get(e);
				return t === void 0 || t.v !== w;
			});
			for (var [n, i] of r) i.v !== w && !(n in e) && t.push(n);
			return t;
		},
		setPrototypeOf() {
			Pe();
		}
	});
}
var Lt, Rt, zt, Bt;
function Vt() {
	if (Lt === void 0) {
		Lt = window, Rt = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		zt = a(t, "firstChild").get, Bt = a(t, "nextSibling").get, u(e) && (e[le] = void 0, e[ce] = null, e[ue] = void 0, e.__e = void 0), u(n) && (n[de] = void 0);
	}
}
function I(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function L(e) {
	return zt.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function R(e) {
	return Bt.call(e);
}
function Ht(e, t) {
	if (!T) return /* @__PURE__ */ L(e);
	var n = /* @__PURE__ */ L(E);
	if (n === null) n = E.appendChild(I());
	else if (t && n.nodeType !== 3) {
		var r = I();
		return n?.before(r), D(r), r;
	}
	return t && Yt(n), D(n), n;
}
function Ut(e, t = !1) {
	if (!T) {
		var n = /* @__PURE__ */ L(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ R(n) : n;
	}
	if (t) {
		if (E?.nodeType !== 3) {
			var r = I();
			return E?.before(r), D(r), r;
		}
		Yt(E);
	}
	return E;
}
function Wt(e, t = !1) {
	if (!T) return /* @__PURE__ */ L(e);
	var n = Ht(e, t);
	return xe(e), n;
}
function Gt(e, t = 1, n = !1) {
	let r = T ? E : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ R(r);
	if (!T) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = I();
			return r === null ? i?.after(a) : r.before(a), D(a), a;
		}
		Yt(r);
	}
	return D(r), r;
}
function Kt(e) {
	e.textContent = "";
}
function qt() {
	return !1;
}
function Jt(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function Yt(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
function Xt(e) {
	var t = q;
	if (t === null) return W.f |= re, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	z(e, t);
}
function z(e, t) {
	if (e === me) throw e;
	if (!(t !== null && t.f & 16384)) {
		for (; t !== null;) {
			if (t.f & 128 && !(t.f & 33570816)) {
				if (!(t.f & 32768)) throw e;
				try {
					t.b.error(e);
					return;
				} catch (t) {
					e = t;
				}
			}
			t = t.parent;
		}
		throw e;
	}
}
// frontend/node_modules/svelte/src/internal/client/reactivity/effects.js
function Zt(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function B(e, t) {
	var n = q;
	n !== null && n.f & 8192 && (e |= _);
	var r = {
		ctx: O,
		deps: null,
		nodes: null,
		f: e | h | 512,
		first: null,
		fn: t,
		last: null,
		next: null,
		parent: n,
		b: n && n.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null
	};
	A?.register_created_effect(r);
	var i = r;
	if (e & 4) gt === null ? bt.ensure().schedule(r) : gt.push(r);
	else if (t !== null) {
		try {
			Mn(r);
		} catch (e) {
			throw H(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= x));
	}
	if (i !== null && (i.parent = n, n !== null && Zt(i, n), W !== null && W.f & 2 && !(e & 64))) {
		var a = W;
		(a.effects ??= []).push(i);
	}
	return r;
}
function Qt() {
	return W !== null && !G;
}
function $t(e) {
	let t = B(8, null);
	return k(t, m), t.teardown = e, t;
}
function en(e) {
	return B(4 | ee, e);
}
function tn(e) {
	bt.ensure();
	let t = B(64 | S, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? fn(t, () => {
			H(t), n(void 0);
		}) : (H(t), n(void 0));
	});
}
function nn(e) {
	return B(ne | S, e);
}
function rn(e, t = 0) {
	return B(8 | t, e);
}
function an(e, t = [], n = [], r = []) {
	Qe(r, t, n, (t) => {
		B(8, () => {
			e(...t.map($));
		});
	});
}
function on(e, t = 0) {
	return B(16 | t, e);
}
function V(e) {
	return B(32 | S, e);
}
function sn(e) {
	var t = e.teardown;
	if (t !== null) {
		let n = U, r = W;
		vn(!0), K(null);
		try {
			t.call(null);
		} catch (t) {
			z(t, e.parent);
		} finally {
			vn(n), K(r);
		}
	}
}
function cn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && Ze(() => {
			e.abort(fe);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : H(n, t), n = r;
	}
}
function ln(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || H(t), t = n;
	}
}
function H(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (un(e.nodes.start, e.nodes.end), n = !0), e.f |= b, cn(e, t && !n), jn(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	sn(e), e.f ^= b, e.f |= v;
	var i = e.parent;
	i !== null && i.first !== null && dn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function un(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ R(e);
		e.remove(), e = n;
	}
}
function dn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function fn(e, t, n = !0) {
	var r = [];
	e.f |= 256, pn(e, r, !0);
	var i = () => {
		n && H(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function pn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= _;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = !!(i.f & 65536) || !!(i.f & 32) && !!(e.f & 16);
				pn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function mn(e) {
	e.f &= -257, hn(e, !0);
}
function hn(e, t) {
	if (!(e.f & 256) && e.f & 8192) {
		e.f ^= _, e.f & 1024 || (k(e, h), bt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = !!(n.f & 65536) || !!(n.f & 32);
			hn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function gn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ R(n);
		t.append(n), n = i;
	}
}
// frontend/node_modules/svelte/src/internal/client/legacy.js
var _n = null, U = !1;
function vn(e) {
	U = e;
}
var W = null, G = !1;
function K(e) {
	W = e;
}
var q = null;
function J(e) {
	q = e;
}
var Y = null;
function yn(e) {
	W !== null && (W.f & 2097152 || W.f & 2) && (Y ??= /* @__PURE__ */ new Set()).add(e);
}
var X = null, Z = 0, Q = null;
function bn(e) {
	Q = e;
}
var xn = 1, Sn = 0, Cn = Sn;
function wn(e) {
	Cn = e;
}
function Tn() {
	return ++xn;
}
function En(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (En(a) && ct(a), a.wv > e.wv) return !0;
		}
		t & 512 && j === null && k(e, m);
	}
	return !1;
}
function Dn(e, t, n = !0) {
	var r = e.reactions;
	if (r !== null && !(Y !== null && Y.has(e))) for (var i = 0; i < r.length; i++) {
		var a = r[i];
		a.f & 2 ? Dn(a, t, !1) : t === a && (n ? k(a, h) : a.f & 1024 && k(a, g), Ct(a));
	}
}
function On(e) {
	var t = X, n = Z, r = Q, i = W, a = Y, o = O, s = G, c = Cn, l = e.f;
	X = null, Z = 0, Q = null, W = l & 96 ? null : e, Y = null, ze(e.ctx), G = !1, Cn = ++Sn, e.ac !== null && (Ze(() => {
		e.ac.abort(fe);
	}), e.ac = null);
	try {
		e.f |= C;
		var u = e.fn, d = u();
		e.f |= y;
		var f = kn(e);
		if (We() && Q !== null && !G && f !== null && !(e.f & 6146)) for (var p = 0; p < Q.length; p++) Dn(Q[p], e);
		if (i !== null && i !== e) {
			if (Sn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Sn;
			if (t !== null) for (let e of t) e.rv = Sn;
			Q !== null && (r === null ? r = Q : r.push(...Q));
		}
		return e.f & 8388608 && (e.f ^= re), d;
	} catch (t) {
		return kn(e), Xt(t);
	} finally {
		e.f ^= C, X = t, Z = n, Q = r, W = i, Y = a, ze(o), G = s, Cn = c;
	}
}
function kn(e) {
	var t = e.deps, n = A?.is_fork;
	if (X !== null) {
		var r;
		if (n || jn(e, Z), t !== null && Z > 0) for (t.length = Z + X.length, r = 0; r < X.length; r++) t[Z + r] = X[r];
		else e.deps = t = X;
		if (Qt() && e.f & 512) for (r = Z; r < t.length; r++) (t[r].reactions ??= []).push(e);
	} else !n && t !== null && Z < t.length && (jn(e, Z), t.length = Z);
	return t;
}
function An(e, r) {
	let i = r.reactions;
	if (i !== null) {
		var a = t.call(i, e);
		if (a !== -1) {
			var o = i.length - 1;
			o === 0 ? i = r.reactions = null : (i[a] = i[o], i.pop());
		}
	}
	if (i === null && r.f & 2 && (X === null || !n.call(X, r))) {
		var s = r;
		s.f & 512 && (s.f ^= 512), s.v !== w && Ye(s), s.ac !== null && Ze(() => {
			s.ac.abort(fe), s.ac = null, k(s, h);
		}), lt(s), jn(s, 0);
	}
}
function jn(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) An(e, n[r]);
}
function Mn(e) {
	var t = e.f;
	if (!(t & 16384)) {
		k(e, m);
		var n = q;
		q = e;
		try {
			t & 16777232 ? ln(e) : cn(e), sn(e);
			var r = On(e);
			e.teardown = typeof r == "function" ? r : null, e.wv = xn;
		} finally {
			q = n;
		}
	}
}
function $(e) {
	var t = !!(e.f & 2);
	if (_n?.add(e), W !== null && !G && !(q !== null && q.f & 16384) && (Y === null || !Y.has(e))) {
		var r = W.deps;
		if (W.f & 2097152) e.rv < Sn && (e.rv = Sn, X === null && r !== null && r[Z] === e ? Z++ : X === null ? X = [e] : X.push(e));
		else {
			W.deps ??= [], n.call(W.deps, e) || W.deps.push(e);
			var i = e.reactions;
			i === null ? e.reactions = [W] : n.call(i, W) || i.push(W);
		}
	}
	if (U && N.has(e)) return N.get(e);
	if (t) {
		var a = e;
		if (U) {
			var o = a.v;
			return (!(a.f & 1024) && a.reactions !== null || Pn(a)) && (o = st(a)), N.set(a, o), o;
		}
		var s = !(a.f & 512) && !G && W !== null && !!(W.f & 512), c = (a.f & y) === 0;
		En(a) && (s && (a.f |= 512), ct(a)), s && !c && (ut(a), Nn(a));
	}
	if (j?.has(e)) return j.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function Nn(e) {
	if (e.f |= 512, e.deps !== null) for (let r of e.deps) {
		var t = r.reactions;
		t === null ? r.reactions = [e] : n.call(t, e) || t.push(e), r.f & 2 && !(r.f & 512) && (ut(r), Nn(r));
	}
}
function Pn(e) {
	if (e.v === w) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (N.has(t) || t.f & 2 && Pn(t)) return !0;
	return !1;
}
function Fn(e) {
	var t = G;
	try {
		return G = !0, e();
	} finally {
		G = t;
	}
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var In = ["touchstart", "touchmove"];
function Ln(e) {
	return In.includes(e);
}
// frontend/node_modules/svelte/src/internal/client/dom/elements/events.js
var Rn = Symbol("events"), zn = /* @__PURE__ */ new Set(), Bn = /* @__PURE__ */ new Set(), Vn = null, Hn = !1;
function Un(e) {
	var t = this, n = t.ownerDocument, r = e.type, a = e.composedPath?.() || [], o = a[0] || e.target;
	Vn = e, Hn || (Hn = !0, setTimeout(() => {
		Hn = !1, Vn = null;
	}));
	var s = 0, c = Vn === e && e[Rn];
	if (c) {
		var l = a.indexOf(c);
		if (l !== -1 && (t === document || t === window)) {
			e[Rn] = t;
			return;
		}
		var u = a.indexOf(t);
		if (u === -1) return;
		l <= u && (s = l);
	}
	if (o = a[s] || e.target, o !== t) {
		i(e, "currentTarget", {
			configurable: !0,
			get() {
				return o || n;
			}
		});
		var d = W, f = q;
		K(null), J(null);
		try {
			for (var p, m = []; o !== null && o !== t;) {
				try {
					var h = o[Rn]?.[r];
					h == null || o.disabled && e.target !== o || h.call(o, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble) break;
				s++, o = s < a.length ? a[s] : null;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[Rn] = t, delete e.currentTarget, K(d), J(f);
		}
	}
}
// frontend/node_modules/svelte/src/internal/client/dom/reconciler.js
var Wn = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function Gn(e) {
	return Wn?.createHTML(e) ?? e;
}
function Kn(e) {
	var t = Jt("template");
	return t.innerHTML = Gn(e.replaceAll("<!>", "<!---->")), t.content;
}
// frontend/node_modules/svelte/src/internal/client/dom/template.js
function qn(e, t) {
	var n = q;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function Jn(e, t) {
	var n = !!(t & 1), r = !!(t & 2), i, a = !e.startsWith("<!>");
	return () => {
		if (T) return qn(E, null), E;
		i === void 0 && (i = Kn(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ L(i)));
		var t = r || Rt ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ L(t), s = t.lastChild;
			qn(o, s);
		} else qn(t, t);
		return t;
	};
}
function Yn() {
	if (T) return qn(E, null), E;
	var e = document.createDocumentFragment(), t = document.createComment(""), n = I();
	return e.append(t, n), qn(t, n), e;
}
function Xn(e, t) {
	if (T) {
		var n = q;
		n.f & 32768 && n.nodes.end !== null || (n.nodes.end = E), be();
	} else e !== null && e.before(t);
}
// frontend/node_modules/svelte/src/reactivity/create-subscriber.js
function Zn(e) {
	let t = 0, n = Ot(0), r;
	return () => {
		Qt() && ($(n), rn(() => (t === 0 && (r = Fn(() => e(() => Pt(n)))), t += 1, () => {
			qe(() => {
				--t, t === 0 && (r?.(), r = void 0, Pt(n));
			});
		})));
	};
}
// frontend/node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var Qn = x | S;
function $n(e, t, n, r) {
	new er(e, t, n, r);
}
var er = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = T ? E : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = 0;
	#d = !1;
	#f = /* @__PURE__ */ new Map();
	#p = null;
	#m = Zn(() => (this.#p = Ot(this.#l), () => {
		this.#p = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = q;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = q.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = on(() => {
			if (T) {
				let e = we(this.#t);
				be();
				let t = e === "[!";
				if (e.startsWith("[?")) {
					let t = JSON.parse(e.slice(2));
					this.#g(t);
				} else t ? this.#y() : this.#h();
			} else this.#b();
		}, Qn), T && (this.#e = E);
	}
	#h() {
		try {
			this.#a = V(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#g(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#_(e);
		qe(r), t && (this.#s = V(() => {
			t(this.#e, () => e, () => n);
		}));
	}
	#_(e) {
		var t = !1, n = !1;
		let r = () => {
			this.#v() || (t ? ve() : (t = !0, n && Ie(), this.#s !== null && fn(this.#s, () => {
				this.#s = null;
			}), this.#S(() => {
				this.#b();
			})));
		};
		return {
			reset: r,
			invoke_onerror: () => {
				if (!this.#v()) try {
					n = !0, this.#n.onerror?.(e, r), n = !1;
				} catch (e) {
					z(e, this.#i && this.#i.parent);
				}
			}
		};
	}
	#v() {
		return (this.#i.f & (v | b)) !== 0;
	}
	#y() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = V(() => e(this.#e)), qe(() => {
			if (!this.#v()) {
				var e = this.#c = document.createDocumentFragment(), t = I(), n = !1;
				e.append(t), this.#a = this.#S(() => {
					try {
						return V(() => this.#r(t));
					} catch (e) {
						try {
							this.error(e), n = !0;
						} catch (e) {
							z(e, this.#i.parent);
						}
						return null;
					}
				}), this.#a === null ? (this.#c = null, n && this.#x(A)) : this.#u === 0 && (this.#e.before(e), this.#c = null, fn(this.#o, () => {
					this.#o = null;
				}), this.#x(A));
			}
		}));
	}
	#b() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = V(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				gn(this.#a, e);
				let t = this.#n.pending;
				this.#o = V(() => t(this.#e));
			} else this.#x(A);
		} catch (e) {
			this.error(e);
		}
	}
	#x(e) {
		this.is_pending = !1, e.transfer_reactions(this.#f);
	}
	defer_effect(e) {
		Xe(e, this.#f);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#S(e) {
		var t = q, n = W, r = O;
		J(this.#i), K(this.#i), ze(this.#i.ctx);
		try {
			return bt.ensure(), e();
		} finally {
			J(t), K(n), ze(r);
		}
	}
	#C(e, t) {
		this.has_pending_snippet() ? (this.#u += e, this.#u === 0 && (this.#x(t), this.#o && fn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null))) : this.parent && this.parent.#C(e, t);
	}
	update_pending_count(e, t) {
		this.#C(e, t), this.#l += e, !this.#p || this.#d || (this.#d = !0, qe(() => {
			this.#d = !1, this.#p && Mt(this.#p, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#m(), $(this.#p);
	}
	error(e) {
		if (e === me || !this.#n.onerror && !this.#n.failed) throw e;
		A?.is_fork ? (this.#a && A.skip_effect(this.#a), this.#o && A.skip_effect(this.#o), this.#s && A.skip_effect(this.#s), A.oncommit(() => {
			this.#v() || this.#w(e);
		})) : this.#w(e);
	}
	#w(e) {
		this.#a &&= (H(this.#a), null), this.#o &&= (H(this.#o), null), this.#s &&= (H(this.#s), null), T && (D(this.#t), Se(), D(Ce()));
		let t = this.#n.failed, n = (e) => {
			if (this.#v()) return;
			let { reset: n, invoke_onerror: r } = this.#_(e);
			r(), t && !this.#v() && (this.#s = this.#S(() => {
				try {
					return V(() => {
						var r = q;
						r.b = this, r.f |= 128, t(this.#e, () => e, () => n);
					});
				} catch (e) {
					return z(e, this.#i.parent), null;
				}
			}));
		};
		qe(() => {
			if (!this.#v()) {
				var t;
				try {
					t = this.transform_error(e);
				} catch (e) {
					z(e, this.#i && this.#i.parent);
					return;
				}
				typeof t == "object" && t && typeof t.then == "function" ? t.then(n, (e) => z(e, this.#i && this.#i.parent)) : n(t);
			}
		});
	}
};
function tr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[de] ??= e.nodeValue) && (e[de] = n, e.nodeValue = `${n}`);
}
function nr(e, t) {
	return ir(e, t);
}
var rr = /* @__PURE__ */ new Map();
function ir(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	Vt();
	var l = void 0, u = tn(() => {
		var s = n ?? t.appendChild(I());
		$n(s, { pending: () => {} }, (t) => {
			Ve({});
			var n = O;
			if (o && (n.c = o), a && (i.$$events = a), T && qn(t, null), l = e(t, i) || Ue(), T && (q.nodes.end = E, E === null || E.nodeType !== 8 || E.data !== "]")) throw _e(), me;
			He();
		}, c);
		var u = /* @__PURE__ */ new Set(), d = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!u.has(r)) {
					u.add(r);
					var i = Ln(r);
					for (let e of [t, document]) {
						var a = rr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), rr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, Un, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return d(r(zn)), Bn.add(d), () => {
			for (var e of u) for (let n of [t, document]) {
				var r = rr.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, Un), r.delete(e), r.size === 0 && rr.delete(n)) : r.set(e, i);
			}
			Bn.delete(d), s !== n && s.parentNode?.removeChild(s);
		};
	});
	return ar.set(l, u), l;
}
var ar = /* @__PURE__ */ new WeakMap();
function or(e, t) {
	let n = ar.get(e);
	return n ? (ar.delete(e), n(t)) : Promise.resolve();
}
// frontend/node_modules/svelte/src/internal/client/dom/blocks/branches.js
var sr = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t;
	}
	#a = (e) => {
		if (this.#e.has(e)) {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) mn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (mn(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (H(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						gn(r, t), t.append(I()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else H(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), fn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (H(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = A, r = qt();
		if (t && !this.#t.has(e) && !this.#n.has(e)) {
			if (r) {
				var i = document.createDocumentFragment(), a = I();
				i.append(a), this.#n.set(e, {
					effect: V(() => t(a)),
					fragment: i
				});
			} else this.#t.set(e, V(() => t(this.anchor)));
		}
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else T && (this.anchor = E), this.#a(n);
	}
};
// frontend/node_modules/svelte/src/internal/client/dom/blocks/if.js
function cr(e, t, n = !1) {
	var r;
	T && (r = E, be());
	var i = new sr(e), a = n ? x : 0;
	function o(e, t) {
		if (T) {
			var n = we(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Ce();
				D(a), i.anchor = a, ye(!1), i.ensure(e, t), ye(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	on(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
// frontend/node_modules/svelte/src/internal/client/dom/blocks/each.js
function lr(e, t) {
	return t;
}
function ur(e, t, n) {
	for (var i = [], a = t.length, o, s = t.length, c = 0; c < a; c++) {
		let n = t[c];
		fn(n, () => {
			if (o) {
				if (o.pending.delete(n), o.done.add(n), o.pending.size === 0) {
					var t = e.outrogroups;
					dr(e, r(o.done)), t.delete(o), t.size === 0 && (e.outrogroups = null);
				}
			} else --s;
		}, !1);
	}
	if (s === 0) {
		var l = i.length === 0 && n !== null && e.pending.size === 0;
		if (l) {
			var u = n, d = u.parentNode;
			Kt(d), d.append(u), e.items.clear();
		}
		dr(e, t, !l);
	} else o = {
		pending: new Set(t),
		done: /* @__PURE__ */ new Set()
	}, (e.outrogroups ??= /* @__PURE__ */ new Set()).add(o);
}
function dr(e, t, n = !0) {
	var r;
	if (e.pending.size > 0) {
		r = /* @__PURE__ */ new Set();
		for (let t of e.pending.values()) for (let n of t) r.add(e.items.get(n).e);
	}
	for (var i = 0; i < t.length; i++) {
		var a = t[i];
		r?.has(a) ? (a.f |= te, gn(a, document.createDocumentFragment())) : H(t[i], n);
	}
}
var fr;
function pr(t, n, i, a, o, s = null) {
	var c = t, l = /* @__PURE__ */ new Map();
	if (n & 4) {
		var u = t;
		c = T ? D(/* @__PURE__ */ L(u)) : u.appendChild(I());
	}
	T && be();
	var d = null, f = /* @__PURE__ */ at(() => {
		var t = i();
		return e(t) ? t : t == null ? [] : r(t);
	}), p = /* @__PURE__ */ new Map(), m = !0;
	function h(e) {
		if (!(_.effect.f & 16384)) {
			_.pending.delete(e);
			var t = $(f);
			_.fallback = d, hr(_, t, c, n, a), d !== null && (t.length === 0 ? d.f & 33554432 ? (d.f ^= te, _r(d, null, c)) : mn(d) : fn(d, () => {
				d = null;
			}));
		}
	}
	function g(e) {
		_.pending.delete(e);
	}
	var _ = {
		effect: on(() => {
			var e = $(f), t = e.length;
			let r = !1;
			T && we(c) === "[!" != (t === 0) && (c = Ce(), D(c), ye(!1), r = !0);
			for (var u = /* @__PURE__ */ new Set(), _ = A, v = qt(), y = 0; y < t; y += 1) {
				T && E.nodeType === 8 && E.data === "]" && (c = E, r = !0, ye(!1));
				var b = e[y], x = a(b, y), S = m ? null : l.get(x);
				S ? (S.v && Mt(S.v, b), S.i && Mt(S.i, y), v && _.unskip_effect(S.e)) : (S = gr(l, m ? c : fr ??= I(), b, x, y, o, n, i), m || (S.e.f |= te), l.set(x, S)), u.add(x);
			}
			if (t === 0 && s && !d && (m ? d = V(() => s(c)) : (d = V(() => s(fr ??= I())), d.f |= te)), t > u.size && Ae("", "", ""), T && t > 0 && D(Ce()), !m) {
				if (p.set(_, u), v) {
					for (let [e, t] of l) u.has(e) || _.skip_effect(t.e);
					_.oncommit(h), _.ondiscard(g);
				} else h(_);
			}
			r && ye(!0), $(f);
		}),
		flags: n,
		items: l,
		pending: p,
		outrogroups: null,
		fallback: d
	};
	m = !1, T && (c = E);
}
function mr(e) {
	for (; e !== null && !(e.f & 32);) e = e.next;
	return e;
}
function hr(e, t, n, i, a) {
	var o = !!(i & 8), s = t.length, c = e.items, l = mr(e.effect.first), u, d = null, f, p = [], m = [], h, g, _, v;
	if (o) for (v = 0; v < s; v += 1) h = t[v], g = a(h, v), _ = c.get(g).e, _.f & 33554432 || (_.nodes?.a?.measure(), (f ??= /* @__PURE__ */ new Set()).add(_));
	for (v = 0; v < s; v += 1) {
		if (h = t[v], g = a(h, v), _ = c.get(g).e, e.outrogroups !== null) for (let t of e.outrogroups) t.pending.delete(_), t.done.delete(_);
		if (_.f & 8192 && (mn(_), o && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) {
			if (_.f ^= te, _ === l) _r(_, null, n);
			else {
				var y = d ? d.next : l;
				_ === e.effect.last && (e.effect.last = _.prev), _.prev && (_.prev.next = _.next), _.next && (_.next.prev = _.prev), vr(e, d, _), vr(e, _, y), _r(_, y, n), d = _, p = [], m = [], l = mr(d.next);
				continue;
			}
		}
		if (_ !== l) {
			if (u !== void 0 && u.has(_)) {
				if (p.length < m.length) {
					var b = m[0], x;
					d = b.prev;
					var S = p[0], ee = p[p.length - 1];
					for (x = 0; x < p.length; x += 1) _r(p[x], b, n);
					for (x = 0; x < m.length; x += 1) u.delete(m[x]);
					vr(e, S.prev, ee.next), vr(e, d, S), vr(e, ee, b), l = b, d = ee, --v, p = [], m = [];
				} else u.delete(_), _r(_, l, n), vr(e, _.prev, _.next), vr(e, _, d === null ? e.effect.first : d.next), vr(e, d, _), d = _;
				continue;
			}
			for (p = [], m = []; l !== null && l !== _;) (u ??= /* @__PURE__ */ new Set()).add(l), m.push(l), l = mr(l.next);
			if (l === null) continue;
		}
		_.f & 33554432 || p.push(_), d = _, l = mr(_.next);
	}
	if (e.outrogroups !== null) {
		for (let t of e.outrogroups) t.pending.size === 0 && (dr(e, r(t.done)), e.outrogroups?.delete(t));
		e.outrogroups.size === 0 && (e.outrogroups = null);
	}
	if (l !== null || u !== void 0) {
		var C = [];
		if (u !== void 0) for (_ of u) _.f & 8192 || C.push(_);
		for (; l !== null;) !(l.f & 8192) && l !== e.fallback && C.push(l), l = mr(l.next);
		var ne = C.length;
		if (ne > 0) {
			var re = i & 4 && s === 0 ? n : null;
			if (o) {
				for (v = 0; v < ne; v += 1) C[v].nodes?.a?.measure();
				for (v = 0; v < ne; v += 1) C[v].nodes?.a?.fix();
			}
			ur(e, C, re);
		}
	}
	o && qe(() => {
		if (f !== void 0) for (_ of f) _.nodes?.a?.apply();
	});
}
function gr(e, t, n, r, i, a, o, s) {
	var c = o & 1 ? o & 16 ? Ot(n) : /* @__PURE__ */ kt(n, !1, !1) : null, l = o & 2 ? Ot(i) : null;
	return {
		v: c,
		i: l,
		e: V(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function _r(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ R(r);
		if (a.before(r), r === i) return;
		r = o;
	}
}
function vr(e, t, n) {
	t === null ? e.effect.first = n : t.next = n, n === null ? e.effect.last = t : n.prev = t;
}
// frontend/node_modules/svelte/src/internal/client/dom/blocks/snippet.js
function yr(e) {
	return (t, ...n) => {
		var r = e(...n), i;
		T ? (i = E, be()) : (i = /* @__PURE__ */ L(Kn(r.render().trim())), t.before(i));
		let a = r.setup?.(i);
		qn(i, i), typeof a == "function" && $t(a);
	};
}
// frontend/node_modules/svelte/src/internal/shared/attributes.js
var br = [..." 	\n\r\f\xA0\v﻿"];
function xr(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || br.includes(r[o - 1])) && (s === r.length || br.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
// frontend/node_modules/svelte/src/internal/client/dom/elements/class.js
function Sr(e, t, n, r, i, a) {
	var o = e[le];
	if (T || o !== n || o === void 0) {
		var s = xr(n, r, a);
		T && s === e.getAttribute("class") || (s == null ? e.removeAttribute("class") : t ? e.className = s : e.setAttribute("class", s)), e[le] = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && e.classList.toggle(c, l);
	}
	return a;
}
// frontend/node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Cr = Symbol("is custom element"), wr = Symbol("is html"), Tr = pe ? "link" : "LINK";
function Er(e, t, n, r) {
	var i = Dr(e);
	if (!(T && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Tr))) {
		var a = i[t];
		a !== (i[t] = n) && (t === "loading" && (e[se] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && kr(e).has(t) ? e[t] = n : (!T || typeof n != "number" && typeof n != "boolean" || a !== String(n)) && e.setAttribute(t, n));
	}
}
function Dr(e) {
	return e[ce] ??= {
		[Cr]: e.nodeName.includes("-"),
		[wr]: e.namespaceURI === he
	};
}
var Or = /* @__PURE__ */ new Map();
function kr(e) {
	var t = e.getAttribute("is") || e.nodeName, n = Or.get(t);
	if (n) return n;
	Or.set(t, n = /* @__PURE__ */ new Set());
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var s in r = o(i), r) r[s].set && s !== "innerHTML" && s !== "textContent" && s !== "innerText" && n.add(s);
		i = l(i);
	}
	return n;
}
// frontend/node_modules/svelte/src/internal/client/reactivity/store.js
var Ar = !1;
function jr(e) {
	var t = Ar;
	try {
		return Ar = !1, [e(), Ar];
	} finally {
		Ar = t;
	}
}
// frontend/node_modules/svelte/src/internal/client/reactivity/props.js
function Mr(e, t, n, r) {
	var i = !0, o = !!(n & 8), s = !!(n & 16), c = r, l = !0, u = void 0, d = () => s && i ? (u ??= /* @__PURE__ */ nt(r), $(u)) : (l && (l = !1, c = s ? Fn(r) : r), c);
	let f;
	if (o) {
		var p = ie in e || oe in e;
		f = a(e, t)?.set ?? (p && t in e ? (n) => e[t] = n : void 0);
	}
	var m, h = !1;
	o ? [m, h] = jr(() => e[t]) : m = e[t], m === void 0 && r !== void 0 && (m = d(), f && (i && Me(t), f(m)));
	var g = i ? () => {
		var n = e[t];
		return n === void 0 ? d() : (l = !0, n);
	} : () => {
		var n = e[t];
		return n !== void 0 && (c = void 0), n === void 0 ? c : n;
	};
	if (i && !(n & 4)) return g;
	if (f) {
		var _ = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!i || !t || _ || h) && f(t ? g() : e), e) : g();
		});
	}
	var v = !1, y = (n & 1 ? nt : at)(() => (v = !1, g()));
	o && $(y);
	var b = q;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? $(y) : i && o ? It(e) : e;
			return F(y, n), v = !0, c !== void 0 && (c = n), e;
		}
		return U && v || b.f & 16384 ? y.v : $(y);
	});
}
export { xe as C, Ve as S, Ut as _, pr as a, Be as b, nr as c, Xn as d, Yn as f, Ht as g, an as h, yr as i, tr as l, $ as m, Er as n, lr as o, Jn as p, Sr as r, cr as s, Mr as t, or as u, Wt as v, He as x, Gt as y };
