// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/shared/utils.js
var e = Array.isArray, t = Array.prototype.indexOf, n = Array.prototype.includes, r = Array.from, i = Object.defineProperty, a = Object.getOwnPropertyDescriptor, o = Object.getOwnPropertyDescriptors, s = Object.prototype, c = Array.prototype, l = Object.getPrototypeOf, u = Object.isExtensible;
function d(e) {
	return typeof e == "function";
}
var f = () => {};
function p(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function m() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/constants.js
var h = 1 << 24, g = 1024, _ = 2048, v = 4096, y = 8192, b = 16384, x = 32768, S = 1 << 25, ee = 65536, C = 1 << 19, te = 1 << 20, ne = 1 << 25, re = 1 << 21, ie = 1 << 22, ae = 1 << 23, w = Symbol("$state"), oe = Symbol("component"), se = Symbol("legacy props"), ce = Symbol(""), le = Symbol("attributes"), ue = Symbol("class"), de = Symbol("style"), fe = Symbol("text"), pe = Symbol("form reset"), me = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), he = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml"), ge = {}, T = Symbol("uninitialized"), _e = "http://www.w3.org/1999/xhtml", ve = "http://www.w3.org/2000/svg", ye = "http://www.w3.org/1998/Math/MathML";
function be() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function xe(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Se() {
	console.warn("https://svelte.dev/e/select_multiple_invalid_value");
}
function Ce() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/hydration.js
var E = !1;
function D(e) {
	E = e;
}
var O;
function k(e) {
	if (e === null) throw xe(), ge;
	return O = e;
}
function A() {
	return k(/* @__PURE__ */ un(O));
}
function we(e) {
	if (E) {
		if (/* @__PURE__ */ un(O) !== null) throw xe(), ge;
		O = e;
	}
}
function Te(e = 1) {
	if (E) {
		for (var t = e, n = O; t--;) n = /* @__PURE__ */ un(n);
		O = n;
	}
}
function Ee(e = !0) {
	for (var t = 0, n = O;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ un(n);
		e && n.remove(), n = i;
	}
}
function De(e) {
	if (!e || e.nodeType !== 8) throw xe(), ge;
	return e.data;
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/reactivity/equality.js
function Oe(e) {
	return e === this.v;
}
function ke(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function Ae(e) {
	return !ke(e, this.v);
}
function je(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/errors.js
function Me() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function Ne(e, t, n) {
	throw Error("https://svelte.dev/e/each_key_duplicate");
}
function Pe(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Fe() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Ie(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Le() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Re(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function ze() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Be() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Ve() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function He() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/flags/index.js
var Ue = !1;
function We() {
	Ue = !0;
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/shared/clone.js
var Ge = [];
function Ke(e, t = !1, n = !1) {
	return qe(e, /* @__PURE__ */ new Map(), "", Ge, null, n);
}
function qe(t, n, r, i, a = null, o = !1) {
	if (typeof t == "object" && t) {
		var c = n.get(t);
		if (c !== void 0) return c;
		if (t instanceof Map) return new Map(t);
		if (t instanceof Set) return new Set(t);
		if (e(t)) {
			var u = Array(t.length);
			n.set(t, u), a !== null && n.set(a, u);
			for (var d = 0; d < t.length; d += 1) {
				var f = t[d];
				d in t && (u[d] = qe(f, n, r, i, null, o));
			}
			return u;
		}
		if (l(t) === s) {
			u = {}, n.set(t, u), a !== null && n.set(a, u);
			for (var p of Object.keys(t)) u[p] = qe(t[p], n, r, i, null, o);
			return u;
		}
		if (t instanceof Date) return t.getTime(), structuredClone(t);
		if (typeof t.toJSON == "function" && !o) return qe(t.toJSON(), n, r, i, t);
	}
	if (t instanceof EventTarget) return t;
	try {
		return structuredClone(t);
	} catch {
		return t;
	}
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/shared/context.js
function Je(e) {
	let t = e.p;
	for (; t !== null && t.c === null;) t = t.p;
	return t?.c ?? null;
}
function Ye(e, t) {
	return e === null && je(t), e.c ??= new Map(Je(e) || void 0);
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/context.js
var j = null;
function Xe(e) {
	j = e;
}
function Ze() {
	return Ye(j, "getAllContexts");
}
function Qe(e, t = !1, n) {
	j = {
		p: j,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: G,
		l: Ue && !t ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function $e(e) {
	var t = j, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) Dn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, j = t.p, et(e);
}
function et(e = {}) {
	return i(e, oe, { value: !0 }), e;
}
function tt() {
	return !Ue || j !== null && j.l === null;
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/task.js
var nt = [];
function rt() {
	var e = nt;
	nt = [], p(e);
}
function M(e) {
	if (nt.length === 0 && !At) {
		var t = nt;
		queueMicrotask(() => {
			t === nt && rt();
		});
	}
	nt.push(e);
}
function it() {
	for (; nt.length > 0;) rt();
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/reactivity/status.js
var at = ~(_ | v | g);
function N(e, t) {
	e.f = e.f & at | t;
}
function ot(e) {
	e.f & 512 || e.deps === null ? N(e, g) : N(e, v);
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/reactivity/utils.js
function st(e, t) {
	e.f & 2048 ? t.set(e, _) : e.f & 4096 && t.get(e) !== 2048 && t.set(e, v), N(e, g);
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/elements/misc.js
function ct(e, t) {
	if (t) {
		let t = document.body;
		e.autofocus = !0, M(() => {
			document.activeElement === t && e.focus();
		});
	}
}
var lt = !1;
function ut() {
	lt || (lt = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[pe]?.();
		});
	}, { capture: !0 }));
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function dt(e, t, n, r = !0) {
	r && n();
	for (var i of t) e.addEventListener(i, n);
	Tn(() => {
		for (var r of t) e.removeEventListener(r, n);
	});
}
function ft(e) {
	var t = H, n = G;
	W(null), K(null);
	try {
		return e();
	} finally {
		W(t), K(n);
	}
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/reactivity/async.js
function pt(e, t, n, r) {
	let i = tt() ? _t : xt;
	var a = e.filter((e) => !e.settled), o = t.map(i);
	if (n.length === 0 && a.length === 0) {
		r(o);
		return;
	}
	var s = G, c = mt(), l = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function u(e) {
		if (!(s.f & 16384)) {
			c();
			try {
				r([...o, ...e]);
			} catch (e) {
				bn(e, s);
			}
			ht();
		}
	}
	var d = gt();
	if (n.length === 0) {
		l.then(() => u([])).finally(d);
		return;
	}
	function f() {
		Promise.all(n.map((e) => /* @__PURE__ */ yt(e))).then(u).catch((e) => bn(e, s)).finally(d);
	}
	l ? l.then(() => {
		s.f & 16384 ? d() : (c(), f(), ht());
	}) : f();
}
function mt() {
	var e = G, t = H, n = j, r = P;
	return function(i = !0) {
		K(e), W(t), Xe(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function ht(e = !0) {
	K(null), W(null), Xe(null), e && P?.deactivate();
}
function gt() {
	var e = G, t = e.b, n = P, r = !!t?.is_rendered();
	return t?.update_pending_count(1, n), n.increment(r, e), () => {
		t?.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/*#__NO_SIDE_EFFECTS__*/
function _t(e) {
	var t = 2 | _;
	return G !== null && (G.f |= C), {
		ctx: j,
		deps: null,
		effects: null,
		equals: Oe,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: T,
		wv: 0,
		parent: G,
		ac: null
	};
}
var vt = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function yt(e, t, n) {
	let r = G;
	r === null && Me();
	var i = void 0, a = Kt(T), o = !H, s = /* @__PURE__ */ new Set();
	return An(() => {
		var t = G, n = m();
		i = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== me && n.reject(e);
			}).finally(ht);
		} catch (e) {
			n.reject(e), ht();
		}
		var c = P;
		if (o) {
			if (t.f & 32768) var l = gt();
			if (r.b?.is_rendered()) c.async_deriveds.get(t)?.reject(vt);
			else for (let e of s.values()) e.reject(vt);
			s.add(n), c.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), s.delete(n), t !== vt && (c.activate(), t ? (a.f |= ae, Zt(a, t)) : (a.f & 8388608 && (a.f ^= ae), Zt(a, e)), c.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), Tn(() => {
		for (let e of s) e.reject(vt);
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
function bt(e) {
	let t = /* @__PURE__ */ _t(e);
	return Jn(t), t;
}
/*#__NO_SIDE_EFFECTS__*/
function xt(e) {
	let t = /* @__PURE__ */ _t(e);
	return t.equals = Ae, t;
}
function St(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) V(t[n]);
	}
}
function Ct(e) {
	var t, n = G, r = e.parent;
	if (!Kn && r !== null && e.v !== T && r.f & 24576) return be(), e.v;
	K(r);
	try {
		St(e), t = rr(e);
	} finally {
		K(n);
	}
	return t;
}
function wt(e) {
	var t = Ct(e);
	!e.equals(t) && (e.wv = er(), (!P?.is_fork || e.deps === null) && (P === null ? e.v = t : (P.capture(e, t, !0), Ot?.capture(e, t, !0)), e.deps === null)) ? N(e, g) : Kn || (F === null ? ot(e) : (wn() || P?.is_fork) && F.set(e, t));
}
function Tt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac !== null && ft(() => {
		t.ac.abort(me), t.ac = null;
	}), t.fn !== null && (t.teardown = f), or(t, 0), In(t));
}
function Et(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && sr(t);
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/reactivity/batch.js
var Dt = null, P = null, Ot = null, F = null, kt = null, At = !1, jt = !1, Mt = null, Nt = null, Pt = 0, Ft = 1, It = class e {
	id = Ft++;
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
		Dt === null ? Dt = this : (Dt.next = this, this.prev = Dt), Dt = this;
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
			for (var r of n.d) N(r, _), t(r);
			for (r of n.m) N(r, v), t(r);
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
					t.f ^= g;
				}
			}
			n || e.push(t);
		}
		return this.#a = [], e;
	}
	#m() {
		this.started = !0;
		for (let [e, t] of this.#s) N(e, t), this.schedule(e);
		this.apply();
		for (var t = Mt = [], n = [], r = Nt = []; this.#a.length > 0;) {
			Pt++ > 1e3 && (this.#b(), Rt());
			for (let e of this.#p()) try {
				this.#h(e, t, n);
			} catch (t) {
				throw Ut(e), this.#d() || this.discard(), t;
			}
		}
		if (P = null, r.length > 0) {
			var i = e.ensure();
			for (let e of r) i.schedule(e);
		}
		if (Mt = null, Nt = null, this.#d()) {
			this.#y(n), this.#y(t);
			for (let [e, t] of this.#c) Ht(e, t);
			r.length > 0 && P.#m();
			return;
		}
		let a = this.#g();
		if (a) this.#y(n), this.#y(t), a.#v(this);
		else {
			this.#s.clear();
			for (let e of this.#e) e(this);
			this.#e.clear(), Ot = this, Bt(n), Bt(t), Ot = null, this.#i?.resolve();
			var o = P;
			this.#n === 0 && (this.#a.length === 0 || o !== null) && this.#b(), o !== null && (I.clear(), o.#m());
		}
	}
	#h(e, t, n) {
		e.f ^= g;
		for (var r = e.first; r !== null;) {
			var i = r.f, a = !!(i & 96);
			if (!(a && i & 1024 || i & 8192 || this.#c.has(r)) && r.fn !== null) {
				a ? r.f ^= g : i & 4 ? t.push(r) : tr(r) && (i & 16 && this.add_dirty_reaction(r, v), sr(r));
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
					r & 4194320 && !this.async_deriveds.has(i) && (this.#s.delete(i), N(i, _), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#b(), P = this, this.#m();
	}
	#y(e) {
		for (var t = 0; t < e.length; t += 1) st(e[t], this.#s);
	}
	capture(e, t, n = !1) {
		e.v !== T && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), F?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		P = this;
	}
	deactivate() {
		P = null, F = null;
	}
	flush() {
		try {
			jt = !0, P = this, this.#m();
		} finally {
			Pt = 0, kt = null, Mt = null, Nt = null, jt = !1, P = null, F = null, I.clear();
		}
	}
	discard() {
		for (let e of this.#t) e(this);
		this.#t.clear();
		for (let e of this.async_deriveds.values()) e.reject(vt);
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
		this.#u || (this.#u = !0, M(() => {
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
		return (this.#i ??= m()).promise;
	}
	static ensure() {
		if (P === null) {
			let t = P = new e();
			!jt && !At && M(() => {
				t.started || t.flush();
			});
		}
		return P;
	}
	apply() {
		F = null;
	}
	schedule(e) {
		kt = e, e.b?.is_pending && e.f & 16777228 && !(e.f & 32768) ? e.b.defer_effect(e) : this.#a.push(e);
	}
	#b() {
		if (this.linked) {
			var e = this.prev, t = this.next;
			e === null || (e.next = t), t === null ? Dt = e : t.prev = e, this.linked = !1;
		}
	}
};
function Lt(e) {
	var t = At, n = Ot;
	Ot = null, At = !0;
	try {
		var r;
		for (e && (Lt(), r = e());;) {
			if (it(), P === null) return r;
			P.flush();
		}
	} finally {
		At = t, Ot = n;
	}
}
function Rt() {
	try {
		Le();
	} catch (e) {
		bn(e, kt);
	}
}
var zt = null;
function Bt(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && tr(r) && (zt = /* @__PURE__ */ new Set(), sr(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && zn(r), zt?.size > 0)) {
				I.clear();
				for (let e of zt) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) zt.has(n) && (zt.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || sr(n);
					}
				}
				zt.clear();
			}
		}
		zt = null;
	}
}
function Vt(e) {
	P.schedule(e);
}
function Ht(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), N(e, g);
		for (var n = e.first; n !== null;) Ht(n, t), n = n.next;
	}
}
function Ut(e) {
	N(e, g);
	for (var t = e.first; t !== null;) Ut(t), t = t.next;
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/reactivity/sources.js
var Wt = /* @__PURE__ */ new Set(), I = /* @__PURE__ */ new Map(), Gt = !1;
function Kt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Oe,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function qt(e, t) {
	let n = Kt(e, t);
	return Jn(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function Jt(e, t = !1, n = !0) {
	let r = Kt(e);
	return t || (r.equals = Ae), Ue && n && j !== null && j.l !== null && (j.l.s ??= []).push(r), r;
}
function L(e, t, n = !1) {
	return H !== null && (!U || H.f & 131072) && tt() && H.f & 4325394 && (q === null || !q.has(e)) && Ve(), Zt(e, n ? tn(t) : t, Nt);
}
var Yt = null, Xt = 0;
function Zt(e, t, n = null) {
	if (!e.equals(t)) {
		Kn ? I.set(e, t) : I.has(e) || I.set(e, e.v);
		var r = It.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && Ct(t), F === null && ot(t);
		}
		e.wv = er(), Yt = null, Xt = 0, en(e, _, n), Yt = null, tt() && G !== null && G.f & 1024 && !(G.f & 96) && (X === null ? Yn([e]) : X.push(e)), !r.is_fork && Wt.size > 0 && !Gt && Qt();
	}
	return t;
}
function Qt() {
	Gt = !1;
	for (let e of Wt) {
		e.f & 1024 && N(e, v);
		let t;
		try {
			t = tr(e);
		} catch {
			t = !0;
		}
		t && sr(e);
	}
	Wt.clear();
}
function $t(e) {
	L(e, e.v + 1);
}
function en(e, t, n) {
	var r = e.reactions;
	if (r !== null) {
		var i = tt(), a = r.length;
		if (Xt += a, Xt > 1e5 && Yt === null && (Yt = /* @__PURE__ */ new Set()), Yt !== null) {
			if (Yt.has(e)) return;
			Yt.add(e);
		}
		for (var o = 0; o < a; o++) {
			var s = r[o], c = s.f;
			if (i || s !== G) {
				var l = (c & _) === 0;
				if (l && N(s, t), c & 131072) Wt.add(s);
				else if (c & 2) {
					var u = s;
					F?.delete(u), en(u, v, n);
				} else if (l) {
					var d = s;
					c & 16 && zt !== null && zt.add(d), n === null ? Vt(d) : n.push(d);
				}
			}
		}
	}
}
function tn(t) {
	if (typeof t != "object" || !t || w in t || oe in t) return t;
	let n = l(t);
	if (n !== s && n !== c) return t;
	var r = /* @__PURE__ */ new Map(), i = e(t), o = /* @__PURE__ */ qt(0), u = null, d = Qn, f = (e) => {
		if (Qn === d) return e();
		var t = H, n = Qn;
		W(null), $n(d);
		var r = e();
		return W(t), $n(n), r;
	};
	return i && r.set("length", /* @__PURE__ */ qt(t.length, u)), new Proxy(t, {
		defineProperty(e, t, n) {
			"value" in n && n.configurable !== !1 && n.enumerable !== !1 && n.writable !== !1 || ze();
			var i = r.get(t);
			return i === void 0 ? f(() => {
				var e = /* @__PURE__ */ qt(n.value, u);
				return r.set(t, e), e;
			}) : L(i, n.value, !0), !0;
		},
		deleteProperty(e, t) {
			var n = r.get(t);
			if (n === void 0) {
				if (t in e) {
					let e = f(() => /* @__PURE__ */ qt(T, u));
					r.set(t, e), $t(o);
				}
			} else L(n, T), $t(o);
			return !0;
		},
		get(e, n, i) {
			if (n === w) return t;
			var o = r.get(n), s = n in e;
			if (o === void 0 && (!s || a(e, n)?.writable) && (o = f(() => /* @__PURE__ */ qt(tn(s ? e[n] : T), u)), r.set(n, o)), o !== void 0) {
				var c = Z(o);
				return c === T ? void 0 : c;
			}
			return Reflect.get(e, n, i);
		},
		getOwnPropertyDescriptor(e, t) {
			this.has?.(e, t);
			var n = Reflect.getOwnPropertyDescriptor(e, t), i = r.get(t);
			if (i !== void 0) {
				var a = Z(i);
				if (a === T) return;
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
			if (t === w) return !0;
			var n = r.get(t), i = n !== void 0 && n.v !== T || Reflect.has(e, t);
			return (n !== void 0 || (G !== null || H !== null) && (!i || a(e, t)?.writable)) && (n === void 0 && (n = f(() => /* @__PURE__ */ qt(i ? tn(e[t]) : T, u)), r.set(t, n)), Z(n) === T) ? !1 : i;
		},
		set(e, t, n, s) {
			var c = r.get(t), l = t in e;
			if (i && t === "length") for (var d = n; d < c.v; d += 1) {
				var p = r.get(d + "");
				p === void 0 ? d in e && (p = f(() => /* @__PURE__ */ qt(T, u)), r.set(d + "", p)) : L(p, T);
			}
			if (c === void 0) (!l || a(e, t)?.writable) && (c = f(() => /* @__PURE__ */ qt(void 0, u)), L(c, tn(n)), r.set(t, c));
			else {
				l = c.v !== T;
				var m = f(() => tn(n));
				L(c, m);
			}
			var h = Reflect.getOwnPropertyDescriptor(e, t);
			if (h?.set && h.set.call(s, n), !l) {
				if (i && typeof t == "string") {
					var g = r.get("length"), _ = Number(t);
					Number.isInteger(_) && _ >= g.v && L(g, _ + 1);
				}
				$t(o);
			}
			return !0;
		},
		ownKeys(e) {
			Z(o);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = r.get(e);
				return t === void 0 || t.v !== T;
			});
			for (var [n, i] of r) i.v !== T && !(n in e) && t.push(n);
			return t;
		},
		setPrototypeOf() {
			Be();
		}
	});
}
function nn(e) {
	try {
		if (typeof e == "object" && e && w in e) return e[w];
	} catch {}
	return e;
}
function rn(e, t) {
	return Object.is(nn(e), nn(t));
}
var an, on, sn, cn;
function ln() {
	if (an === void 0) {
		an = window, on = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		sn = a(t, "firstChild").get, cn = a(t, "nextSibling").get, u(e) && (e[ue] = void 0, e[le] = null, e[de] = void 0, e.__e = void 0), u(n) && (n[fe] = void 0);
	}
}
function R(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function z(e) {
	return sn.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function un(e) {
	return cn.call(e);
}
function dn(e, t) {
	if (!E) return /* @__PURE__ */ z(e);
	var n = /* @__PURE__ */ z(O);
	if (n === null) n = O.appendChild(R());
	else if (t && n.nodeType !== 3) {
		var r = R();
		return n?.before(r), k(r), r;
	}
	return t && vn(n), k(n), n;
}
function fn(e, t = !1) {
	if (!E) {
		var n = /* @__PURE__ */ z(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ un(n) : n;
	}
	if (t) {
		if (O?.nodeType !== 3) {
			var r = R();
			return O?.before(r), k(r), r;
		}
		vn(O);
	}
	return O;
}
function pn(e, t = !1) {
	if (!E) return /* @__PURE__ */ z(e);
	var n = dn(e, t);
	return we(e), n;
}
function mn(e, t = 1, n = !1) {
	let r = E ? O : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ un(r);
	if (!E) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = R();
			return r === null ? i?.after(a) : r.before(a), k(a), a;
		}
		vn(r);
	}
	return k(r), r;
}
function hn(e) {
	e.textContent = "";
}
function gn() {
	return !1;
}
function _n(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function vn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
function yn(e) {
	var t = G;
	if (t === null) return H.f |= ae, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	bn(e, t);
}
function bn(e, t) {
	if (e === ge) throw e;
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
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/reactivity/effects.js
function xn(e) {
	G === null && (H === null && Ie(e), Fe()), Kn && Pe(e);
}
function Sn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function Cn(e, t) {
	var n = G;
	n !== null && n.f & 8192 && (e |= y);
	var r = {
		ctx: j,
		deps: null,
		nodes: null,
		f: e | _ | 512,
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
	P?.register_created_effect(r);
	var i = r;
	if (e & 4) Mt === null ? It.ensure().schedule(r) : Mt.push(r);
	else if (t !== null) {
		try {
			sr(r);
		} catch (e) {
			throw V(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= ee));
	}
	if (i !== null && (i.parent = n, n !== null && Sn(i, n), H !== null && H.f & 2 && !(e & 64))) {
		var a = H;
		(a.effects ??= []).push(i);
	}
	return r;
}
function wn() {
	return H !== null && !U;
}
function Tn(e) {
	let t = Cn(8, null);
	return N(t, g), t.teardown = e, t;
}
function En(e) {
	xn("$effect");
	var t = G.f;
	if (!H && t & 32 && j !== null && !j.i) {
		var n = j;
		(n.e ??= []).push(e);
	} else return Dn(e);
}
function Dn(e) {
	return Cn(4 | te, e);
}
function On(e) {
	It.ensure();
	let t = Cn(64 | C, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Bn(t, () => {
			V(t), n(void 0);
		}) : (V(t), n(void 0));
	});
}
function kn(e) {
	return Cn(4, e);
}
function An(e) {
	return Cn(ie | C, e);
}
function jn(e, t = 0) {
	return Cn(8 | t, e);
}
function Mn(e, t = [], n = [], r = []) {
	pt(r, t, n, (t) => {
		Cn(8, () => {
			e(...t.map(Z));
		});
	});
}
function Nn(e, t = 0) {
	return Cn(16 | t, e);
}
function Pn(e, t = 0) {
	return Cn(h | t, e);
}
function B(e) {
	return Cn(32 | C, e);
}
function Fn(e) {
	var t = e.teardown;
	if (t !== null) {
		let n = Kn, r = H;
		qn(!0), W(null);
		try {
			t.call(null);
		} catch (t) {
			bn(t, e.parent);
		} finally {
			qn(n), W(r);
		}
	}
}
function In(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && ft(() => {
			e.abort(me);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : V(n, t), n = r;
	}
}
function Ln(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || V(t), t = n;
	}
}
function V(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (Rn(e.nodes.start, e.nodes.end), n = !0), e.f |= S, In(e, t && !n), or(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	Fn(e), e.f ^= S, e.f |= b;
	var i = e.parent;
	i !== null && i.first !== null && zn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function Rn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ un(e);
		e.remove(), e = n;
	}
}
function zn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function Bn(e, t, n = !0) {
	var r = [];
	e.f |= 256, Vn(e, r, !0);
	var i = () => {
		n && V(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function Vn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= y;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = !!(i.f & 65536) || !!(i.f & 32) && !!(e.f & 16);
				Vn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function Hn(e) {
	e.f &= -257, Un(e, !0);
}
function Un(e, t) {
	if (!(e.f & 256) && e.f & 8192) {
		e.f ^= y, e.f & 1024 || (N(e, _), It.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = !!(n.f & 65536) || !!(n.f & 32);
			Un(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Wn(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ un(n);
		t.append(n), n = i;
	}
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/legacy.js
var Gn = null, Kn = !1;
function qn(e) {
	Kn = e;
}
var H = null, U = !1;
function W(e) {
	H = e;
}
var G = null;
function K(e) {
	G = e;
}
var q = null;
function Jn(e) {
	H !== null && (H.f & 2097152 || H.f & 2) && (q ??= /* @__PURE__ */ new Set()).add(e);
}
var J = null, Y = 0, X = null;
function Yn(e) {
	X = e;
}
var Xn = 1, Zn = 0, Qn = Zn;
function $n(e) {
	Qn = e;
}
function er() {
	return ++Xn;
}
function tr(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (tr(a) && wt(a), a.wv > e.wv) return !0;
		}
		t & 512 && F === null && N(e, g);
	}
	return !1;
}
function nr(e, t, n = !0) {
	var r = e.reactions;
	if (r !== null && !(q !== null && q.has(e))) for (var i = 0; i < r.length; i++) {
		var a = r[i];
		a.f & 2 ? nr(a, t, !1) : t === a && (n ? N(a, _) : a.f & 1024 && N(a, v), Vt(a));
	}
}
function rr(e) {
	var t = J, n = Y, r = X, i = H, a = q, o = j, s = U, c = Qn, l = e.f;
	J = null, Y = 0, X = null, H = l & 96 ? null : e, q = null, Xe(e.ctx), U = !1, Qn = ++Zn, e.ac !== null && (ft(() => {
		e.ac.abort(me);
	}), e.ac = null);
	try {
		e.f |= re;
		var u = e.fn, d = u();
		e.f |= x;
		var f = ir(e);
		if (tt() && X !== null && !U && f !== null && !(e.f & 6146)) for (var p = 0; p < X.length; p++) nr(X[p], e);
		if (i !== null && i !== e) {
			if (Zn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Zn;
			if (t !== null) for (let e of t) e.rv = Zn;
			X !== null && (r === null ? r = X : r.push(...X));
		}
		return e.f & 8388608 && (e.f ^= ae), d;
	} catch (t) {
		return ir(e), yn(t);
	} finally {
		e.f ^= re, J = t, Y = n, X = r, H = i, q = a, Xe(o), U = s, Qn = c;
	}
}
function ir(e) {
	var t = e.deps, n = P?.is_fork;
	if (J !== null) {
		var r;
		if (n || or(e, Y), t !== null && Y > 0) for (t.length = Y + J.length, r = 0; r < J.length; r++) t[Y + r] = J[r];
		else e.deps = t = J;
		if (wn() && e.f & 512) for (r = Y; r < t.length; r++) (t[r].reactions ??= []).push(e);
	} else !n && t !== null && Y < t.length && (or(e, Y), t.length = Y);
	return t;
}
function ar(e, r) {
	let i = r.reactions;
	if (i !== null) {
		var a = t.call(i, e);
		if (a !== -1) {
			var o = i.length - 1;
			o === 0 ? i = r.reactions = null : (i[a] = i[o], i.pop());
		}
	}
	if (i === null && r.f & 2 && (J === null || !n.call(J, r))) {
		var s = r;
		s.f & 512 && (s.f ^= 512), s.v !== T && ot(s), s.ac !== null && ft(() => {
			s.ac.abort(me), s.ac = null, N(s, _);
		}), Tt(s), or(s, 0);
	}
}
function or(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) ar(e, n[r]);
}
function sr(e) {
	var t = e.f;
	if (!(t & 16384)) {
		N(e, g);
		var n = G;
		G = e;
		try {
			t & 16777232 ? Ln(e) : In(e), Fn(e);
			var r = rr(e);
			e.teardown = typeof r == "function" ? r : null, e.wv = Xn;
		} finally {
			G = n;
		}
	}
}
async function cr() {
	await Promise.resolve(), Lt();
}
function Z(e) {
	var t = !!(e.f & 2);
	if (Gn?.add(e), H !== null && !U && !(G !== null && G.f & 16384) && (q === null || !q.has(e))) {
		var r = H.deps;
		if (H.f & 2097152) e.rv < Zn && (e.rv = Zn, J === null && r !== null && r[Y] === e ? Y++ : J === null ? J = [e] : J.push(e));
		else {
			H.deps ??= [], n.call(H.deps, e) || H.deps.push(e);
			var i = e.reactions;
			i === null ? e.reactions = [H] : n.call(i, H) || i.push(H);
		}
	}
	if (Kn && I.has(e)) return I.get(e);
	if (t) {
		var a = e;
		if (Kn) {
			var o = a.v;
			return (!(a.f & 1024) && a.reactions !== null || ur(a)) && (o = Ct(a)), I.set(a, o), o;
		}
		var s = !(a.f & 512) && !U && H !== null && !!(H.f & 512), c = (a.f & x) === 0;
		tr(a) && (s && (a.f |= 512), wt(a)), s && !c && (Et(a), lr(a));
	}
	if (F?.has(e)) return F.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function lr(e) {
	if (e.f |= 512, e.deps !== null) for (let r of e.deps) {
		var t = r.reactions;
		t === null ? r.reactions = [e] : n.call(t, e) || t.push(e), r.f & 2 && !(r.f & 512) && (Et(r), lr(r));
	}
}
function ur(e) {
	if (e.v === T) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (I.has(t) || t.f & 2 && ur(t)) return !0;
	return !1;
}
function dr(e) {
	var t = U;
	try {
		return U = !0, e();
	} finally {
		U = t;
	}
}
function fr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (w in e) pr(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && w in n && pr(n);
		}
	}
}
function pr(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			pr(e[n], t);
		} catch {}
		let n = l(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = o(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
function mr(e) {
	return e.endsWith("capture") && e !== "gotpointercapture" && e !== "lostpointercapture";
}
var hr = [
	"beforeinput",
	"click",
	"change",
	"dblclick",
	"contextmenu",
	"focusin",
	"focusout",
	"input",
	"keydown",
	"keyup",
	"mousedown",
	"mousemove",
	"mouseout",
	"mouseover",
	"mouseup",
	"pointerdown",
	"pointermove",
	"pointerout",
	"pointerover",
	"pointerup",
	"touchend",
	"touchmove",
	"touchstart"
];
function gr(e) {
	return hr.includes(e);
}
var _r = /* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split("."), vr = {
	formnovalidate: "formNoValidate",
	ismap: "isMap",
	nomodule: "noModule",
	playsinline: "playsInline",
	readonly: "readOnly",
	defaultvalue: "defaultValue",
	defaultchecked: "defaultChecked",
	srcobject: "srcObject",
	novalidate: "noValidate",
	allowfullscreen: "allowFullscreen",
	disablepictureinpicture: "disablePictureInPicture",
	disableremoteplayback: "disableRemotePlayback"
};
function yr(e) {
	return e = e.toLowerCase(), vr[e] ?? e;
}
[..._r];
var br = ["touchstart", "touchmove"];
function xr(e) {
	return br.includes(e);
}
var Sr = [
	"textarea",
	"script",
	"style",
	"title"
];
function Cr(e) {
	return Sr.includes(e);
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/elements/events.js
var wr = Symbol("events"), Tr = /* @__PURE__ */ new Set(), Er = /* @__PURE__ */ new Set();
function Dr(e) {
	if (!E) return;
	e.removeAttribute("onload"), e.removeAttribute("onerror");
	let t = e.__e;
	t !== void 0 && (e.__e = void 0, queueMicrotask(() => {
		e.isConnected && e.dispatchEvent(t);
	}));
}
function Or(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || Pr.call(t, e), !e.cancelBubble) return ft(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? (i.__removed = !1, M(() => {
		i.__removed || t.addEventListener(e, i, r);
	})) : t.addEventListener(e, i, r), i;
}
function kr(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = Or(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && Tn(() => {
		o.__removed = !0, t.removeEventListener(e, o, a);
	});
}
function Ar(e, t, n) {
	(t[wr] ??= {})[e] = n;
}
function jr(e) {
	for (var t = 0; t < e.length; t++) Tr.add(e[t]);
	for (var n of Er) n(e);
}
var Mr = null, Nr = !1;
function Pr(e) {
	var t = this, n = t.ownerDocument, r = e.type, a = e.composedPath?.() || [], o = a[0] || e.target;
	Mr = e, Nr || (Nr = !0, setTimeout(() => {
		Nr = !1, Mr = null;
	}));
	var s = 0, c = Mr === e && e[wr];
	if (c) {
		var l = a.indexOf(c);
		if (l !== -1 && (t === document || t === window)) {
			e[wr] = t;
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
		var d = H, f = G;
		W(null), K(null);
		try {
			for (var p, m = []; o !== null && o !== t;) {
				try {
					var h = o[wr]?.[r];
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
			e[wr] = t, delete e.currentTarget, W(d), K(f);
		}
	}
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/reconciler.js
var Fr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function Ir(e) {
	return Fr?.createHTML(e) ?? e;
}
function Lr(e) {
	var t = _n("template");
	return t.innerHTML = Ir(e.replaceAll("<!>", "<!---->")), t.content;
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/template.js
function Q(e, t) {
	var n = G;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function Rr(e, t) {
	var n = !!(t & 1), r = !!(t & 2), i, a = !e.startsWith("<!>");
	return () => {
		if (E) return Q(O, null), O;
		i === void 0 && (i = Lr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ z(i)));
		var t = r || on ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ z(t), s = t.lastChild;
			Q(o, s);
		} else Q(t, t);
		return t;
	};
}
/*#__NO_SIDE_EFFECTS__*/
function zr(e, t, n = "svg") {
	var r = !e.startsWith("<!>"), i = !!(t & 1), a = `<${n}>${r ? e : "<!>" + e}</${n}>`, o;
	return () => {
		if (E) return Q(O, null), O;
		if (!o) {
			var e = /* @__PURE__ */ z(Lr(a));
			if (i) for (o = document.createDocumentFragment(); /* @__PURE__ */ z(e);) o.appendChild(/* @__PURE__ */ z(e));
			else o = /* @__PURE__ */ z(e);
		}
		var t = o.cloneNode(!0);
		if (i) {
			var n = /* @__PURE__ */ z(t), r = t.lastChild;
			Q(n, r);
		} else Q(t, t);
		return t;
	};
}
/*#__NO_SIDE_EFFECTS__*/
function Br(e, t) {
	return /* @__PURE__ */ zr(e, t, "svg");
}
function Vr(e = "") {
	if (!E) {
		var t = R(e + "");
		return Q(t, t), t;
	}
	var n = O;
	return n.nodeType === 3 ? vn(n) : (n.before(n = R()), k(n)), Q(n, n), n;
}
function Hr() {
	if (E) return Q(O, null), O;
	var e = document.createDocumentFragment(), t = document.createComment(""), n = R();
	return e.append(t, n), Q(t, n), e;
}
function Ur(e, t) {
	if (E) {
		var n = G;
		n.f & 32768 && n.nodes.end !== null || (n.nodes.end = O), A();
	} else e !== null && e.before(t);
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/reactivity/create-subscriber.js
function Wr(e) {
	let t = 0, n = Kt(0), r;
	return () => {
		wn() && (Z(n), jn(() => (t === 0 && (r = dr(() => e(() => $t(n)))), t += 1, () => {
			M(() => {
				--t, t === 0 && (r?.(), r = void 0, $t(n));
			});
		})));
	};
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var Gr = ee | C;
function Kr(e, t, n, r) {
	new qr(e, t, n, r);
}
var qr = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = E ? O : null;
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
	#m = Wr(() => (this.#p = Kt(this.#l), () => {
		this.#p = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = G;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = G.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = Nn(() => {
			if (E) {
				let e = De(this.#t);
				A();
				let t = e === "[!";
				if (e.startsWith("[?")) {
					let t = JSON.parse(e.slice(2));
					this.#g(t);
				} else t ? this.#y() : this.#h();
			} else this.#b();
		}, Gr), E && (this.#e = O);
	}
	#h() {
		try {
			this.#a = B(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#g(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#_(e);
		M(r), t && (this.#s = B(() => {
			t(this.#e, () => e, () => n);
		}));
	}
	#_(e) {
		var t = !1, n = !1;
		let r = () => {
			this.#v() || (t ? Ce() : (t = !0, n && He(), this.#s !== null && Bn(this.#s, () => {
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
					bn(e, this.#i && this.#i.parent);
				}
			}
		};
	}
	#v() {
		return (this.#i.f & (b | S)) !== 0;
	}
	#y() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = B(() => e(this.#e)), M(() => {
			if (!this.#v()) {
				var e = this.#c = document.createDocumentFragment(), t = R(), n = !1;
				e.append(t), this.#a = this.#S(() => {
					try {
						return B(() => this.#r(t));
					} catch (e) {
						try {
							this.error(e), n = !0;
						} catch (e) {
							bn(e, this.#i.parent);
						}
						return null;
					}
				}), this.#a === null ? (this.#c = null, n && this.#x(P)) : this.#u === 0 && (this.#e.before(e), this.#c = null, Bn(this.#o, () => {
					this.#o = null;
				}), this.#x(P));
			}
		}));
	}
	#b() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = B(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Wn(this.#a, e);
				let t = this.#n.pending;
				this.#o = B(() => t(this.#e));
			} else this.#x(P);
		} catch (e) {
			this.error(e);
		}
	}
	#x(e) {
		this.is_pending = !1, e.transfer_reactions(this.#f);
	}
	defer_effect(e) {
		st(e, this.#f);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#S(e) {
		var t = G, n = H, r = j;
		K(this.#i), W(this.#i), Xe(this.#i.ctx);
		try {
			return It.ensure(), e();
		} finally {
			K(t), W(n), Xe(r);
		}
	}
	#C(e, t) {
		this.has_pending_snippet() ? (this.#u += e, this.#u === 0 && (this.#x(t), this.#o && Bn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null))) : this.parent && this.parent.#C(e, t);
	}
	update_pending_count(e, t) {
		this.#C(e, t), this.#l += e, !this.#p || this.#d || (this.#d = !0, M(() => {
			this.#d = !1, this.#p && Zt(this.#p, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#m(), Z(this.#p);
	}
	error(e) {
		if (e === ge || !this.#n.onerror && !this.#n.failed) throw e;
		P?.is_fork ? (this.#a && P.skip_effect(this.#a), this.#o && P.skip_effect(this.#o), this.#s && P.skip_effect(this.#s), P.oncommit(() => {
			this.#v() || this.#w(e);
		})) : this.#w(e);
	}
	#w(e) {
		this.#a &&= (V(this.#a), null), this.#o &&= (V(this.#o), null), this.#s &&= (V(this.#s), null), E && (k(this.#t), Te(), k(Ee()));
		let t = this.#n.failed, n = (e) => {
			if (this.#v()) return;
			let { reset: n, invoke_onerror: r } = this.#_(e);
			r(), t && !this.#v() && (this.#s = this.#S(() => {
				try {
					return B(() => {
						var r = G;
						r.b = this, r.f |= 128, t(this.#e, () => e, () => n);
					});
				} catch (e) {
					return bn(e, this.#i.parent), null;
				}
			}));
		};
		M(() => {
			if (!this.#v()) {
				var t;
				try {
					t = this.transform_error(e);
				} catch (e) {
					bn(e, this.#i && this.#i.parent);
					return;
				}
				typeof t == "object" && t && typeof t.then == "function" ? t.then(n, (e) => bn(e, this.#i && this.#i.parent)) : n(t);
			}
		});
	}
}, Jr = !0;
function Yr(e) {
	Jr = e;
}
function Xr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[fe] ??= e.nodeValue) && (e[fe] = n, e.nodeValue = `${n}`);
}
function Zr(e, t) {
	return $r(e, t);
}
var Qr = /* @__PURE__ */ new Map();
function $r(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	ln();
	var l = void 0, u = On(() => {
		var u = n ?? t.appendChild(R());
		Kr(u, { pending: () => {} }, (t) => {
			Qe({});
			var n = j;
			if (o && (n.c = o), a && (i.$$events = a), E && Q(t, null), Jr = s, l = e(t, i) || et(), Jr = !0, E && (G.nodes.end = O, O === null || O.nodeType !== 8 || O.data !== "]")) throw xe(), ge;
			$e();
		}, c);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = xr(r);
					for (let e of [t, document]) {
						var a = Qr.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), Qr.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, Pr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(r(Tr)), Er.add(f), () => {
			for (var e of d) for (let n of [t, document]) {
				var r = Qr.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, Pr), r.delete(e), r.size === 0 && Qr.delete(n)) : r.set(e, i);
			}
			Er.delete(f), u !== n && u.parentNode?.removeChild(u);
		};
	});
	return ei.set(l, u), l;
}
var ei = /* @__PURE__ */ new WeakMap();
function ti(e, t) {
	let n = ei.get(e);
	return n ? (ei.delete(e), n(t)) : Promise.resolve();
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/blocks/branches.js
var ni = class {
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
			if (n) Hn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (Hn(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (V(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						Wn(r, t), t.append(R()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else V(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Bn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (V(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = P, r = gn();
		if (t && !this.#t.has(e) && !this.#n.has(e)) {
			if (r) {
				var i = document.createDocumentFragment(), a = R();
				i.append(a), this.#n.set(e, {
					effect: B(() => t(a)),
					fragment: i
				});
			} else this.#t.set(e, B(() => t(this.anchor)));
		}
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else E && (this.anchor = O), this.#a(n);
	}
};
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/blocks/if.js
function ri(e, t, n = !1) {
	var r;
	E && (r = O, A());
	var i = new ni(e), a = n ? ee : 0;
	function o(e, t) {
		if (E) {
			var n = De(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Ee();
				k(a), i.anchor = a, D(!1), i.ensure(e, t), D(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	Nn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/blocks/each.js
function ii(e, t) {
	return t;
}
function ai(e, t, n) {
	for (var i = [], a = t.length, o, s = t.length, c = 0; c < a; c++) {
		let n = t[c];
		Bn(n, () => {
			if (o) {
				if (o.pending.delete(n), o.done.add(n), o.pending.size === 0) {
					var t = e.outrogroups;
					oi(e, r(o.done)), t.delete(o), t.size === 0 && (e.outrogroups = null);
				}
			} else --s;
		}, !1);
	}
	if (s === 0) {
		var l = i.length === 0 && n !== null && e.pending.size === 0;
		if (l) {
			var u = n, d = u.parentNode;
			hn(d), d.append(u), e.items.clear();
		}
		oi(e, t, !l);
	} else o = {
		pending: new Set(t),
		done: /* @__PURE__ */ new Set()
	}, (e.outrogroups ??= /* @__PURE__ */ new Set()).add(o);
}
function oi(e, t, n = !0) {
	var r;
	if (e.pending.size > 0) {
		r = /* @__PURE__ */ new Set();
		for (let t of e.pending.values()) for (let n of t) r.add(e.items.get(n).e);
	}
	for (var i = 0; i < t.length; i++) {
		var a = t[i];
		r?.has(a) ? (a.f |= ne, Wn(a, document.createDocumentFragment())) : V(t[i], n);
	}
}
var si;
function ci(t, n, i, a, o, s = null) {
	var c = t, l = /* @__PURE__ */ new Map();
	if (n & 4) {
		var u = t;
		c = E ? k(/* @__PURE__ */ z(u)) : u.appendChild(R());
	}
	E && A();
	var d = null, f = /* @__PURE__ */ xt(() => {
		var t = i();
		return e(t) ? t : t == null ? [] : r(t);
	}), p = /* @__PURE__ */ new Map(), m = !0;
	function h(e) {
		if (!(_.effect.f & 16384)) {
			_.pending.delete(e);
			var t = Z(f);
			_.fallback = d, ui(_, t, c, n, a), d !== null && (t.length === 0 ? d.f & 33554432 ? (d.f ^= ne, fi(d, null, c)) : Hn(d) : Bn(d, () => {
				d = null;
			}));
		}
	}
	function g(e) {
		_.pending.delete(e);
	}
	var _ = {
		effect: Nn(() => {
			var e = Z(f), t = e.length;
			let r = !1;
			E && De(c) === "[!" != (t === 0) && (c = Ee(), k(c), D(!1), r = !0);
			for (var u = /* @__PURE__ */ new Set(), _ = P, v = gn(), y = 0; y < t; y += 1) {
				E && O.nodeType === 8 && O.data === "]" && (c = O, r = !0, D(!1));
				var b = e[y], x = a(b, y), S = m ? null : l.get(x);
				S ? (S.v && Zt(S.v, b), S.i && Zt(S.i, y), v && _.unskip_effect(S.e)) : (S = di(l, m ? c : si ??= R(), b, x, y, o, n, i), m || (S.e.f |= ne), l.set(x, S)), u.add(x);
			}
			if (t === 0 && s && !d && (m ? d = B(() => s(c)) : (d = B(() => s(si ??= R())), d.f |= ne)), t > u.size && Ne("", "", ""), E && t > 0 && k(Ee()), !m) {
				if (p.set(_, u), v) {
					for (let [e, t] of l) u.has(e) || _.skip_effect(t.e);
					_.oncommit(h), _.ondiscard(g);
				} else h(_);
			}
			r && D(!0), Z(f);
		}),
		flags: n,
		items: l,
		pending: p,
		outrogroups: null,
		fallback: d
	};
	m = !1, E && (c = O);
}
function li(e) {
	for (; e !== null && !(e.f & 32);) e = e.next;
	return e;
}
function ui(e, t, n, i, a) {
	var o = !!(i & 8), s = t.length, c = e.items, l = li(e.effect.first), u, d = null, f, p = [], m = [], h, g, _, v;
	if (o) for (v = 0; v < s; v += 1) h = t[v], g = a(h, v), _ = c.get(g).e, _.f & 33554432 || (_.nodes?.a?.measure(), (f ??= /* @__PURE__ */ new Set()).add(_));
	for (v = 0; v < s; v += 1) {
		if (h = t[v], g = a(h, v), _ = c.get(g).e, e.outrogroups !== null) for (let t of e.outrogroups) t.pending.delete(_), t.done.delete(_);
		if (_.f & 8192 && (Hn(_), o && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) {
			if (_.f ^= ne, _ === l) fi(_, null, n);
			else {
				var y = d ? d.next : l;
				_ === e.effect.last && (e.effect.last = _.prev), _.prev && (_.prev.next = _.next), _.next && (_.next.prev = _.prev), pi(e, d, _), pi(e, _, y), fi(_, y, n), d = _, p = [], m = [], l = li(d.next);
				continue;
			}
		}
		if (_ !== l) {
			if (u !== void 0 && u.has(_)) {
				if (p.length < m.length) {
					var b = m[0], x;
					d = b.prev;
					var S = p[0], ee = p[p.length - 1];
					for (x = 0; x < p.length; x += 1) fi(p[x], b, n);
					for (x = 0; x < m.length; x += 1) u.delete(m[x]);
					pi(e, S.prev, ee.next), pi(e, d, S), pi(e, ee, b), l = b, d = ee, --v, p = [], m = [];
				} else u.delete(_), fi(_, l, n), pi(e, _.prev, _.next), pi(e, _, d === null ? e.effect.first : d.next), pi(e, d, _), d = _;
				continue;
			}
			for (p = [], m = []; l !== null && l !== _;) (u ??= /* @__PURE__ */ new Set()).add(l), m.push(l), l = li(l.next);
			if (l === null) continue;
		}
		_.f & 33554432 || p.push(_), d = _, l = li(_.next);
	}
	if (e.outrogroups !== null) {
		for (let t of e.outrogroups) t.pending.size === 0 && (oi(e, r(t.done)), e.outrogroups?.delete(t));
		e.outrogroups.size === 0 && (e.outrogroups = null);
	}
	if (l !== null || u !== void 0) {
		var C = [];
		if (u !== void 0) for (_ of u) _.f & 8192 || C.push(_);
		for (; l !== null;) !(l.f & 8192) && l !== e.fallback && C.push(l), l = li(l.next);
		var te = C.length;
		if (te > 0) {
			var re = i & 4 && s === 0 ? n : null;
			if (o) {
				for (v = 0; v < te; v += 1) C[v].nodes?.a?.measure();
				for (v = 0; v < te; v += 1) C[v].nodes?.a?.fix();
			}
			ai(e, C, re);
		}
	}
	o && M(() => {
		if (f !== void 0) for (_ of f) _.nodes?.a?.apply();
	});
}
function di(e, t, n, r, i, a, o, s) {
	var c = o & 1 ? o & 16 ? Kt(n) : /* @__PURE__ */ Jt(n, !1, !1) : null, l = o & 2 ? Kt(i) : null;
	return {
		v: c,
		i: l,
		e: B(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function fi(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ un(r);
		if (a.before(r), r === i) return;
		r = o;
	}
}
function pi(e, t, n) {
	t === null ? e.effect.first = n : t.next = n, n === null ? e.effect.last = t : n.prev = t;
}
function mi(e, t, n = !1, r = !1, i = !1, a = !1) {
	var o = e, s = "";
	if (n) {
		var c = e;
		E && (o = k(/* @__PURE__ */ z(c)));
	}
	Mn(() => {
		var e = G;
		if (s === (s = t() ?? "")) E && A();
		else if (n && !E) e.nodes = null, c.innerHTML = s, s !== "" && Q(/* @__PURE__ */ z(c), c.lastChild);
		else if (e.nodes !== null && (Rn(e.nodes.start, e.nodes.end), e.nodes = null), s !== "") {
			if (E) {
				for (var a = O.data, l = A(), u = l; l !== null && (l.nodeType !== 8 || l.data !== "");) u = l, l = /* @__PURE__ */ un(l);
				if (l === null) throw xe(), ge;
				Q(O, u), o = k(l);
			} else {
				var d = _n(r ? "svg" : i ? "math" : "template", r ? ve : i ? ye : void 0);
				d.innerHTML = s;
				var f = r || i ? d : d.content;
				if (Q(/* @__PURE__ */ z(f), f.lastChild), r || i) for (; /* @__PURE__ */ z(f);) o.before(/* @__PURE__ */ z(f));
				else o.before(f);
			}
		}
	});
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/blocks/snippet.js
function hi(e, t, ...n) {
	var r = new ni(e);
	Nn(() => {
		let e = t() ?? null;
		r.ensure(e, e && ((t) => e(t, ...n)));
	}, ee);
}
function gi(e) {
	return (t, ...n) => {
		var r = e(...n), i;
		E ? (i = O, A()) : (i = /* @__PURE__ */ z(Lr(r.render().trim())), t.before(i));
		let a = r.setup?.(i);
		Q(i, i), typeof a == "function" && Tn(a);
	};
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/blocks/svelte-component.js
function _i(e, t, n) {
	var r;
	E && (r = O, A());
	var i = new ni(e);
	Nn(() => {
		var e = t() ?? null;
		if (E && De(r) === "[" != (e !== null)) {
			var a = Ee();
			k(a), i.anchor = a, D(!1), i.ensure(e, e && ((t) => n(t, e))), D(!0);
		} else i.ensure(e, e && ((t) => n(t, e)));
	}, ee);
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/timing.js
var vi = () => performance.now(), $ = {
	tick: (e) => requestAnimationFrame(e),
	now: () => vi(),
	tasks: /* @__PURE__ */ new Set()
};
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/loop.js
function yi() {
	let e = $.now();
	$.tasks.forEach((t) => {
		t.c(e) || ($.tasks.delete(t), t.f());
	}), $.tasks.size !== 0 && $.tick(yi);
}
function bi(e) {
	let t;
	return $.tasks.size === 0 && $.tick(yi), {
		promise: new Promise((n) => {
			$.tasks.add(t = {
				c: e,
				f: n
			});
		}),
		abort() {
			$.tasks.delete(t);
		}
	};
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/elements/transitions.js
function xi(e, t) {
	ft(() => {
		e.dispatchEvent(new CustomEvent(t));
	});
}
function Si(e) {
	if (e === "float") return "cssFloat";
	if (e === "offset") return "cssOffset";
	if (e.startsWith("--")) return e;
	let t = e.split("-");
	return t.length === 1 ? t[0] : t[0] + t.slice(1).map((e) => e[0].toUpperCase() + e.slice(1)).join("");
}
function Ci(e) {
	let t = {}, n = e.split(";");
	for (let e of n) {
		let [n, r] = e.split(":");
		if (!n || r === void 0) break;
		let i = Si(n.trim());
		t[i] = r.trim();
	}
	return t;
}
var wi = (e) => e;
function Ti(e, t, n, r) {
	var i = !!(e & 1), a = !!(e & 2), o = i && a, s = !!(e & 4), c = o ? "both" : i ? "in" : "out", l, u = t.inert, d = t.style.overflow, f, p;
	function m() {
		return ft(() => l ??= n()(t, r?.() ?? {}, { direction: c }));
	}
	var h = {
		is_global: s,
		in() {
			t.inert = u, i ? (a || f?.abort(), f = Ei(t, m(), p, 1, () => {
				xi(t, "introstart");
			}, () => {
				xi(t, "introend"), f?.abort(), f = l = void 0, t.style.overflow = d;
			})) : (p?.abort(), p?.reset?.());
		},
		out(e) {
			a ? (t.inert = !0, p = Ei(t, m(), f, 0, () => {
				xi(t, "outrostart");
			}, () => {
				xi(t, "outroend"), e?.();
			})) : (e?.(), l = void 0);
		},
		stop: () => {
			f?.abort(), p?.abort();
		}
	}, g = G;
	if ((g.nodes.t ??= []).push(h), i && Jr) {
		var _ = s;
		if (!_) {
			for (var v = g.parent; v && v.f & 65536;) for (; (v = v.parent) && !(v.f & 16););
			_ = !v || !!(v.f & 32768);
		}
		_ && kn(() => {
			dr(() => h.in());
		});
	}
}
function Ei(e, t, n, r, i, a) {
	var o = r === 1, s = !1;
	if (d(t)) {
		var c;
		return M(() => {
			s || (c = Ei(e, t({ direction: o ? "in" : "out" }), n, r, i, a));
		}), {
			abort: () => {
				s = !0, c?.abort();
			},
			deactivate: () => c?.deactivate(),
			reset: () => c?.reset(),
			t: () => c?.t() ?? 1 - r
		};
	}
	if (n?.deactivate(), !t?.duration && !t?.delay) return i(), a(), {
		abort: f,
		deactivate: f,
		reset: f,
		t: () => r
	};
	let { delay: l = 0, css: u, tick: p, easing: m = wi } = t;
	var h, g = () => 1 - r;
	return M(() => {
		if (!s) {
			var c = [];
			if (o && n === void 0 && (p && p(0, 1), u)) {
				var d = Ci(u(0, 1));
				c.push(d, d);
			}
			h = e.animate(c, {
				duration: l,
				fill: "forwards"
			}), h.onfinish = () => {
				h.cancel(), i();
				var o = n?.t() ?? 1 - r;
				n?.abort();
				var s = r - o, c = t.duration * Math.abs(s), l = [];
				if (c > 0) {
					var d = !1;
					if (u) for (var f = Math.ceil(c / (1e3 / 60)), _ = 0; _ <= f; _ += 1) {
						var v = o + s * m(_ / f), y = Ci(u(v, 1 - v));
						l.push(y), d ||= y.overflow === "hidden";
					}
					d && (e.style.overflow = "hidden"), g = () => {
						var e = h.currentTime;
						return o + s * m(e / c);
					}, p && bi(() => {
						if (h.playState !== "running") return !1;
						var e = g();
						return p(e, 1 - e), !0;
					});
				}
				h = e.animate(l, {
					duration: c,
					fill: "forwards"
				}), h.onfinish = () => {
					g = () => r, p?.(r, 1 - r), a();
				};
			};
		}
	}), {
		abort: () => {
			s = !0, h && (h.cancel(), h.effect = null, h.onfinish = f);
		},
		deactivate: () => {
			a = f;
		},
		reset: () => {
			r === 0 && p?.(1, 0);
		},
		t: () => g()
	};
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/blocks/svelte-element.js
function Di(e, t, n, r, i, a) {
	let o = E;
	E && A();
	var s = null;
	E && O.nodeType === 1 && (s = O, A());
	var c = E ? O : e, l = new ni(c, !1);
	Nn(() => {
		let e = t() || null;
		var a = i ? i() : n || e === "svg" ? ve : void 0;
		if (e === null) l.ensure(null, null), Yr(!0);
		else return l.ensure(e, (t) => {
			if (e) {
				var n = E;
				if (s = E ? s : _n(e, a), Q(s, s), r) {
					var i = null;
					E && Cr(e) && s.append(i = document.createComment(""));
					var o = E ? /* @__PURE__ */ z(s) : s.appendChild(R());
					E && (o === null ? D(!1) : k(o)), r(s, o), i?.remove();
				}
				G.nodes.end = s, n || t.before(s);
			}
			E && k(t);
		}), Yr(!0), () => {
			e && Yr(!1);
		};
	}, ee), Tn(() => {
		Yr(!0);
	}), o && (D(!0), k(c));
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/elements/actions.js
function Oi(e, t, n) {
	kn(() => {
		var r = dr(() => t(e, n?.()) || {});
		if (n && r?.update) {
			var i = !1, a = {};
			jn(() => {
				var e = n();
				fr(e), i && ke(a, e) && (a = e, r.update(e));
			}), i = !0;
		}
		if (r?.destroy) return () => r.destroy();
	});
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/elements/attachments.js
function ki(e, t) {
	var n = void 0, r;
	Pn(() => {
		n !== (n = t()) && (r &&= (V(r), null), n && (r = B(() => {
			kn(() => n(e));
		})));
	});
}
// ../slime-card-gallery-template/frontend/node_modules/clsx/dist/clsx.mjs
function Ai(e) {
	var t, n, r = "";
	if (typeof e == "string" || typeof e == "number") r += e;
	else if (typeof e == "object") {
		if (Array.isArray(e)) {
			var i = e.length;
			for (t = 0; t < i; t++) e[t] && (n = Ai(e[t])) && (r && (r += " "), r += n);
		} else for (n in e) e[n] && (r && (r += " "), r += n);
	}
	return r;
}
function ji() {
	for (var e, t, n = 0, r = "", i = arguments.length; n < i; n++) (e = arguments[n]) && (t = Ai(e)) && (r && (r += " "), r += t);
	return r;
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/shared/attributes.js
function Mi(e) {
	return typeof e == "object" ? ji(e) : e ?? "";
}
var Ni = [..." 	\n\r\f\xA0\v﻿"];
function Pi(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || Ni.includes(r[o - 1])) && (s === r.length || Ni.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
function Fi(e, t = !1) {
	var n = t ? " !important;" : ";", r = "";
	for (var i of Object.keys(e)) {
		var a = e[i];
		a != null && a !== "" && (r += " " + i + ": " + a + n);
	}
	return r;
}
function Ii(e) {
	return e[0] !== "-" || e[1] !== "-" ? e.toLowerCase() : e;
}
function Li(e, t) {
	if (t) {
		var n = "", r, i;
		if (Array.isArray(t) ? (r = t[0], i = t[1]) : r = t, e) {
			e = String(e).replaceAll(/\/\*.*?\*\//g, "").trim();
			var a = !1, o = 0, s = !1, c = [];
			r && c.push(...Object.keys(r).map(Ii)), i && c.push(...Object.keys(i).map(Ii));
			var l = 0, u = -1;
			let t = e.length;
			for (var d = 0; d < t; d++) {
				var f = e[d];
				if (s ? f === "/" && e[d - 1] === "*" && (s = !1) : a ? a === f && (a = !1) : f === "/" && e[d + 1] === "*" ? s = !0 : f === "\"" || f === "'" ? a = f : f === "(" ? o++ : f === ")" && o--, !s && a === !1 && o === 0) {
					if (f === ":" && u === -1) u = d;
					else if (f === ";" || d === t - 1) {
						if (u !== -1) {
							var p = Ii(e.substring(l, u).trim());
							if (!c.includes(p)) {
								f !== ";" && d++;
								var m = e.substring(l, d).trim();
								n += " " + m + ";";
							}
						}
						l = d + 1, u = -1;
					}
				}
			}
		}
		return r && (n += Fi(r)), i && (n += Fi(i, !0)), n = n.trim(), n === "" ? null : n;
	}
	return e == null ? null : String(e);
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/elements/class.js
function Ri(e, t, n, r, i, a) {
	var o = e[ue];
	if (E || o !== n || o === void 0) {
		var s = Pi(n, r, a);
		E && s === e.getAttribute("class") || (s == null ? e.removeAttribute("class") : t ? e.className = s : e.setAttribute("class", s)), e[ue] = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && e.classList.toggle(c, l);
	}
	return a;
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/elements/style.js
function zi(e, t = {}, n, r) {
	for (var i in n) {
		var a = n[i];
		t[i] !== a && (n[i] == null ? e.style.removeProperty(i) : e.style.setProperty(i, a, r));
	}
}
function Bi(e, t, n, r) {
	var i = e[de];
	if (E || i !== t) {
		var a = Li(t, r);
		E && a === e.getAttribute("style") || (a == null ? e.removeAttribute("style") : e.style.cssText = a), e[de] = t;
	} else r && (Array.isArray(r) ? (zi(e, n?.[0], r[0]), zi(e, n?.[1], r[1], "important")) : zi(e, n, r));
	return r;
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/elements/bindings/select.js
function Vi(e, t) {
	t ? e.hasAttribute("selected") || e.setAttribute("selected", "") : e.removeAttribute("selected");
}
function Hi(e, t) {
	var n = !("__defaultValue" in e);
	(n || e.__defaultValue !== t) && (e.__defaultValue = t, Ui(e, !n || "__value" in e));
}
function Ui(t, n) {
	var r = t.__defaultValue, i = t.multiple, a = i ? r ?? [] : null;
	if (!i || e(a)) {
		var o = t.selectedIndex, s = n && i ? new Set(t.selectedOptions) : null;
		for (var c of t.options) {
			var l = Ki(c);
			Vi(c, i ? a.includes(l) : rn(l, r));
		}
		if (n) {
			if (s !== null) for (c of t.options) {
				var u = s.has(c);
				c.selected !== u && (c.selected = u);
			}
			else t.selectedIndex !== o && (t.selectedIndex = o);
		}
	}
}
function Wi(t, n, r = !1) {
	if (t.multiple) {
		if (n == null) return;
		if (!e(n)) return Se();
		for (var i of t.options) i.selected = n.includes(Ki(i));
	} else {
		for (i of t.options) if (rn(Ki(i), n)) {
			i.selected = !0;
			return;
		}
		r && n === void 0 || (t.selectedIndex = -1);
	}
}
function Gi(e) {
	var t = new MutationObserver((t) => {
		t.every(qi) || ("__defaultValue" in e && Ui(e, !1), "__value" in e && Wi(e, e.__value));
	});
	t.observe(e, {
		childList: !0,
		subtree: !0,
		attributes: !0,
		attributeFilter: ["value"]
	}), Tn(() => {
		t.disconnect();
	});
}
function Ki(e) {
	return "__value" in e ? e.__value : e.value;
}
function qi(e) {
	if (e.target.closest("selectedcontent") !== null) return !0;
	if (e.type === "childList") {
		var t = [...e.addedNodes, ...e.removedNodes];
		return t.length > 0 && t.every((e) => e.nodeName === "SELECTEDCONTENT");
	}
	return !1;
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Ji = Symbol("class"), Yi = Symbol("style"), Xi = Symbol("is custom element"), Zi = Symbol("is html"), Qi = he ? "link" : "LINK", $i = he ? "input" : "INPUT", ea = he ? "option" : "OPTION", ta = he ? "select" : "SELECT", na = he ? "progress" : "PROGRESS";
function ra(e) {
	if (E) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					aa(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					aa(e, "checked", null), e.checked = r;
				}
			}
		};
		e[pe] = n, M(n), ut();
	}
}
function ia(e, t) {
	var n = ca(e);
	n.value !== (n.value = t ?? void 0) && (e.value !== t || t === 0 && e.nodeName === na) && (e.value = t ?? "");
}
function aa(e, t, n, r) {
	var i = ca(e);
	if (!(E && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Qi))) {
		var a = i[t];
		a !== (i[t] = n) && (t === "loading" && (e[ce] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && ua(e).has(t) ? e[t] = n : (!E || typeof n != "number" && typeof n != "boolean" || a !== String(n)) && e.setAttribute(t, n));
	}
}
function oa(e, t, n, r, i = !1, a = !1) {
	E && i && e.nodeName === $i && ("defaultValue" in n || "defaultChecked" in n || ra(e));
	var o = ca(e), s = o[Xi], c = !o[Zi];
	let l = E && s;
	l && D(!1);
	var u = t || {}, d = e.nodeName === ea, f = e.nodeName === ta;
	try {
		for (var p in t) !(p in n) && p[0] + p[1] !== "$$" && (n[p] = null);
		n.class ? n.class = Mi(n.class) : (r || n[Ji]) && (n.class = null), n[Yi] && (n.style ??= null);
		var m = ua(e);
		if (e.nodeName === $i && "type" in n && ("value" in n || "__value" in n)) {
			var h = n.type;
			(h !== u.type || h === void 0 && e.hasAttribute("type")) && (u.type = h, aa(e, "type", h, a));
		}
		for (let i in n) {
			let l = n[i];
			if (d && i === "value" && l == null) e.value = e.__value = "", u[i] = l;
			else if (i === "class") Ri(e, e.namespaceURI === "http://www.w3.org/1999/xhtml", l, r, t?.[Ji], n[Ji]), u[i] = l, u[Ji] = n[Ji];
			else if (i === "style") Bi(e, l, t?.[Yi], n[Yi]), u[i] = l, u[Yi] = n[Yi];
			else {
				var g = u[i];
				if (l !== g || l === void 0 && e.hasAttribute(i)) {
					u[i] = l;
					var _ = i[0] + i[1];
					if (_ !== "$$") {
						if (_ === "on") {
							let t = {}, n = "$$" + i, r = i.slice(2);
							var v = gr(r);
							if (mr(r) && (r = r.slice(0, -7), t.capture = !0), !v && g) {
								if (l != null) continue;
								e.removeEventListener(r, u[n], t), u[n] = null;
							}
							if (v) Ar(r, e, l), jr([r]);
							else if (l != null) {
								function a(e) {
									u[i].call(this, e);
								}
								u[n] = Or(r, e, a, t);
							}
						} else if (i === "style") aa(e, i, l);
						else if (i === "autofocus") ct(e, !!l);
						else if (!s && (i === "__value" || i === "value" && l != null)) e.__value = l, (g == null || e.value !== l || l === 0 && e.nodeName === na) && (e.value = l);
						else if (i === "selected" && d) Vi(e, l);
						else {
							var y = i;
							c || (y = yr(y));
							var b = y === "defaultValue" || y === "defaultChecked";
							if (f && y === "defaultValue") continue;
							if (l == null && !s && !b) {
								if (o[i] = null, y === "value" || y === "checked") {
									let n = e, r = t === void 0;
									if (y === "value") {
										let e = n.defaultValue;
										n.removeAttribute(y), n.defaultValue = e, n.value = n.__value = r ? e : null;
									} else {
										let e = n.defaultChecked;
										n.removeAttribute(y), n.defaultChecked = e, n.checked = r ? e : !1;
									}
								} else e.removeAttribute(i);
							} else b || (s || typeof l != "string") && m.has(y) ? (e[y] = l, y in o && (o[y] = T)) : typeof l != "function" && aa(e, y, l, a);
						}
					}
				}
			}
		}
	} finally {
		l && D(!0);
	}
	return u;
}
function sa(e, t, n = [], r = [], i = [], a, o = !1, s = !1) {
	pt(i, n, r, (n) => {
		var r = void 0, i = {}, c = e.nodeName === ta, l = !1;
		if (Pn(() => {
			var u = t(...n.map(Z)), d = oa(e, r, u, a, o, s);
			if (l && c) {
				var f = e;
				"defaultValue" in u && Hi(f, u.defaultValue), "value" in u && Wi(f, u.value);
			}
			for (let e of Object.getOwnPropertySymbols(i)) u[e] || V(i[e]);
			for (let t of Object.getOwnPropertySymbols(u)) {
				var p = u[t];
				t.description !== "@attach" || r && p === r[t] || (i[t] && V(i[t]), i[t] = B(() => ki(e, () => p))), d[t] = p;
			}
			r = d;
		}), c) {
			var u = e;
			kn(() => {
				var e = r;
				"defaultValue" in e && Hi(u, e.defaultValue), Wi(u, e.value, !0), Gi(u);
			});
		}
		l = !0;
	});
}
function ca(e) {
	return e[le] ??= {
		[Xi]: e.nodeName.includes("-"),
		[Zi]: e.namespaceURI === _e
	};
}
var la = /* @__PURE__ */ new Map();
function ua(e) {
	var t = e.getAttribute("is") || e.nodeName, n = la.get(t);
	if (n) return n;
	la.set(t, n = /* @__PURE__ */ new Set());
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var s in r = o(i), r) r[s].set && s !== "innerHTML" && s !== "textContent" && s !== "innerText" && n.add(s);
		i = l(i);
	}
	return n;
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/elements/bindings/media.js
function da(e, t, n = t) {
	var r, i, a = () => {
		cancelAnimationFrame(r), e.paused || (r = requestAnimationFrame(a));
		var t = e.currentTime;
		i !== t && n(i = t);
	};
	r = requestAnimationFrame(a), e.addEventListener("timeupdate", a), jn(() => {
		var n = Number(t());
		i !== n && !isNaN(n) && (e.currentTime = i = n);
	}), Tn(() => {
		cancelAnimationFrame(r), e.removeEventListener("timeupdate", a);
	});
}
function fa(e, t, n = t) {
	var r = t();
	dt(e, [
		"play",
		"pause",
		"canplay"
	], () => {
		r !== e.paused && n(r = e.paused);
	}, r == null), kn(() => {
		(r = !!t()) !== e.paused && (r ? e.pause() : e.play().catch((e) => {
			throw n(r = !0), e;
		}));
	});
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/elements/bindings/this.js
function pa(e, t) {
	return e === t || e?.[w] === t;
}
function ma(e = et(), t, n, r) {
	var i = j.r, a = G;
	return kn(() => {
		var o, s;
		return jn(() => {
			o = s, s = r?.() || [], dr(() => {
				pa(n(...s), e) || (t(e, ...s), o && pa(n(...o), e) && t(null, ...o));
			});
		}), () => {
			let r = a;
			for (; r !== i && r.parent !== null && r.parent.f & 33554432;) r = r.parent;
			let o = () => {
				s && pa(n(...s), e) && t(null, ...s);
			}, c = r.teardown;
			r.teardown = () => {
				o(), c?.();
			};
		};
	}), e;
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/elements/bindings/universal.js
function ha(e, t, n, r, i) {
	var a = () => {
		r(n[e]);
	};
	n.addEventListener(t, a), i ? jn(() => {
		n[e] = i();
	}) : a(), (n === document.body || n === window || n === document) && Tn(() => {
		n.removeEventListener(t, a);
	});
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/dom/elements/bindings/window.js
function ga(e, t) {
	dt(window, ["resize"], () => ft(() => t(window[e])));
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/store/utils.js
function _a(e, t, n) {
	if (e == null) return t(void 0), n && n(void 0), f;
	let r = dr(() => e.subscribe(t, n));
	return r.unsubscribe ? () => r.unsubscribe() : r;
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/store/shared/index.js
var va = [];
function ya(e, t = f) {
	let n = null, r = /* @__PURE__ */ new Set();
	function i(t) {
		if (ke(e, t) && (e = t, n)) {
			let t = !va.length;
			for (let t of r) t[1](), va.push(t, e);
			if (t) {
				for (let e = 0; e < va.length; e += 2) va[e][0](va[e + 1]);
				va.length = 0;
			}
		}
	}
	function a(t) {
		i(t(e));
	}
	function o(o, s = f) {
		let c = [o, s];
		return r.add(c), r.size === 1 && (n = t(i, a) || f), o(e), () => {
			r.delete(c), r.size === 0 && n && (n(), n = null);
		};
	}
	return {
		set: i,
		update: a,
		subscribe: o
	};
}
function ba(e) {
	let t;
	return _a(e, (e) => t = e)(), t;
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/reactivity/store.js
var xa = !1, Sa = Symbol("unmounted");
function Ca(e, t, n) {
	let r = n[t] ??= {
		store: null,
		source: /* @__PURE__ */ Jt(void 0),
		unsubscribe: f
	};
	if (r.store !== e && !(Sa in n)) {
		if (r.unsubscribe(), r.store = e ?? null, e == null) r.source.v = void 0, r.unsubscribe = f;
		else {
			var i = !0;
			r.unsubscribe = _a(e, (e) => {
				i ? r.source.v = e : L(r.source, e);
			}), i = !1;
		}
	}
	return e && Sa in n ? ba(e) : Z(r.source);
}
function wa() {
	let e = {};
	function t() {
		Tn(() => {
			for (var t in e) e[t].unsubscribe();
			i(e, Sa, {
				enumerable: !1,
				value: !0
			});
		});
	}
	return [e, t];
}
function Ta(e) {
	var t = xa;
	try {
		return xa = !1, [e(), xa];
	} finally {
		xa = t;
	}
}
// ../slime-card-gallery-template/frontend/node_modules/svelte/src/internal/client/reactivity/props.js
var Ea = {
	get(e, t) {
		if (!e.exclude.has(t)) return e.props[t];
	},
	set(e, t) {
		return !1;
	},
	getOwnPropertyDescriptor(e, t) {
		if (!e.exclude.has(t) && t in e.props) return {
			enumerable: !0,
			configurable: !0,
			value: e.props[t]
		};
	},
	has(e, t) {
		return !e.exclude.has(t) && t in e.props;
	},
	ownKeys(e) {
		return Reflect.ownKeys(e.props).filter((t) => !e.exclude.has(t));
	}
};
/*#__NO_SIDE_EFFECTS__*/
function Da(e, t, n) {
	return new Proxy({
		props: e,
		exclude: t
	}, Ea);
}
var Oa = {
	get(e, t) {
		let n = e.props.length;
		for (; n--;) {
			let r = e.props[n];
			if (d(r) && (r = r()), typeof r == "object" && r && t in r) return r[t];
		}
	},
	set(e, t, n) {
		let r = e.props.length;
		for (; r--;) {
			let i = e.props[r];
			d(i) && (i = i());
			let o = a(i, t);
			if (o && o.set) return o.set(n), !0;
		}
		return !1;
	},
	getOwnPropertyDescriptor(e, t) {
		let n = e.props.length;
		for (; n--;) {
			let r = e.props[n];
			if (d(r) && (r = r()), typeof r == "object" && r && t in r) {
				let e = a(r, t);
				return e && !e.configurable && (e.configurable = !0), e;
			}
		}
	},
	has(e, t) {
		if (t === w || t === se) return !1;
		for (let n of e.props) if (d(n) && (n = n()), n != null && t in n) return !0;
		return !1;
	},
	ownKeys(e) {
		let t = [];
		for (let n of e.props) if (d(n) && (n = n()), n) {
			for (let e in n) t.includes(e) || t.push(e);
			for (let e of Object.getOwnPropertySymbols(n)) t.includes(e) || t.push(e);
		}
		return t;
	}
};
function ka(...e) {
	return new Proxy({ props: e }, Oa);
}
function Aa(e, t, n, r) {
	var i = !Ue || !!(n & 2), o = !!(n & 8), s = !!(n & 16), c = r, l = !0, u = void 0, d = () => s && i ? (u ??= /* @__PURE__ */ _t(r), Z(u)) : (l && (l = !1, c = s ? dr(r) : r), c);
	let f;
	if (o) {
		var p = w in e || se in e;
		f = a(e, t)?.set ?? (p && t in e ? (n) => e[t] = n : void 0);
	}
	var m, h = !1;
	o ? [m, h] = Ta(() => e[t]) : m = e[t], m === void 0 && r !== void 0 && (m = d(), f && (i && Re(t), f(m)));
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
	var v = !1, y = (n & 1 ? _t : xt)(() => (v = !1, g()));
	o && Z(y);
	var b = G;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Z(y) : i && o ? tn(e) : e;
			return L(y, n), v = !0, c !== void 0 && (c = n), e;
		}
		return Kn && v || b.f & 16384 ? y.v : Z(y);
	});
}
function ja(e) {
	j === null && je("onMount"), Ue && j.l !== null ? Na(j).m.push(e) : En(() => {
		let t = dr(e);
		if (typeof t == "function") return t;
	});
}
function Ma(e) {
	j === null && je("onDestroy"), ja(() => () => dr(e));
}
function Na(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
export { wn as $, gi as A, Ur as B, Mi as C, bi as D, Ti as E, ri as F, jr as G, Rr as H, Zr as I, Dr as J, Ar as K, Xr as L, mi as M, ci as N, $ as O, ii as P, kn as Q, ti as R, Ri as S, Di as T, Br as U, Hr as V, Vr as W, cr as X, Z as Y, dr as Z, sa as _, f as _t, ka as a, mn as at, Vi as b, ba as c, qt as ct, ha as d, $e as dt, Mn as et, ma as f, Qe as ft, Yi as g, we as gt, Ji as h, Te as ht, Da as i, pn as it, hi as j, _i as k, ya as l, bt as lt, fa as m, We as mt, ja as n, dn as nt, wa as o, tn as ot, da as p, Ke as pt, kr as q, Aa as r, fn as rt, Ca as s, L as st, Ma as t, En as tt, ga as u, Ze as ut, aa as v, Oi as w, Bi as x, ia as y, Wr as z };
