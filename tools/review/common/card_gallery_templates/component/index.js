import { $ as e, B as t, C as n, D as r, E as i, F as a, G as o, H as s, J as c, K as l, L as u, M as d, N as f, O as p, P as m, Q as h, S as g, T as _, U as v, V as y, W as b, X as x, Y as S, Z as C, _ as w, _t as T, a as E, at as D, b as O, c as k, ct as A, d as j, dt as M, et as N, f as ee, ft as P, g as te, gt as F, h as ne, ht as re, i as ie, it as I, j as ae, k as oe, l as se, lt as L, m as ce, mt as le, n as ue, nt as R, o as de, ot as fe, p as pe, pt as me, q as he, r as z, rt as B, s as ge, st as V, t as _e, tt as ve, u as ye, v as be, w as xe, x as Se, y as H, z as Ce } from "./index-client-Do0qPkI9.js";
// frontend/node_modules/@gradio/atoms/dist/src/Block.svelte
var we = v("<svg class=\"resize-handle svelte-1stq1b1\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 10 10\"><line x1=\"1\" y1=\"9\" x2=\"9\" y2=\"1\" stroke=\"gray\" stroke-width=\"0.5\" class=\"svelte-1stq1b1\"></line><line x1=\"5\" y1=\"9\" x2=\"9\" y2=\"5\" stroke=\"gray\" stroke-width=\"0.5\" class=\"svelte-1stq1b1\"></line></svg>"), Te = s("<!> <!>", 1), Ee = s("<div class=\"placeholder svelte-1stq1b1\"></div>");
function De(e, n) {
	P(n, !0);
	let r = z(n, "height", 3, void 0), i = z(n, "min_height", 3, void 0), o = z(n, "max_height", 3, void 0), s = z(n, "width", 3, void 0), c = z(n, "elem_id", 3, ""), u = z(n, "elem_classes", 19, () => []), d = z(n, "variant", 3, "solid"), f = z(n, "border_mode", 3, "base"), p = z(n, "padding", 3, !0), m = z(n, "type", 3, "normal"), h = z(n, "test_id", 3, void 0), g = z(n, "explicit_call", 3, !1), v = z(n, "container", 3, !0), b = z(n, "visible", 3, !0), x = z(n, "allow_overflow", 3, !0), C = z(n, "overflow_behavior", 3, "auto"), E = z(n, "scale", 3, null), O = z(n, "min_width", 3, 0), k = z(n, "flex", 3, !1), j = z(n, "resizable", 3, !1), F = z(n, "rtl", 3, !1), re = z(n, "fullscreen", 15, !1), ie = z(n, "label", 3, void 0), I = re(), oe = A(void 0), se = L(() => m() === "fieldset" ? "fieldset" : "div"), ce = L(() => b() ? k() : !1), le = A(0), ue = A(0), R = A(null), de = null, fe = null, pe = null;
	function me(e) {
		re() && e.key === "Escape" && re(!1);
	}
	function he(e) {
		let t = e.getRootNode();
		return e.closest(".gradio-container") ?? (t instanceof ShadowRoot ? t : document.body);
	}
	function ge(e) {
		let t = document.createElement("div");
		t.style.cssText = "position: fixed; top: 0; left: 0; width: 100%; height: 100%; visibility: hidden; pointer-events: none;", e.appendChild(t);
		let n = t.getBoundingClientRect();
		return t.remove(), n;
	}
	function _e(e, t) {
		let n = e.parentNode;
		if (!n || n === t) return !1;
		let r = ge(n), i = ge(t);
		return Math.abs(r.top - i.top) > 1 || Math.abs(r.left - i.left) > 1 || Math.abs(r.width - i.width) > 1 || Math.abs(r.height - i.height) > 1;
	}
	function ye(e, t) {
		e.parentNode && e.parentNode !== t && (de = e.parentNode, pe = e, fe = document.createComment("fullscreen block"), de.insertBefore(fe, e), t.appendChild(e));
	}
	function be() {
		if (!de || !pe) return;
		let e = fe && fe.parentNode === de ? fe : null;
		de.insertBefore(pe, e), e?.remove(), de = null, fe = null, pe = null;
	}
	ve(() => {
		let e = S(oe);
		if (re() !== I && e) {
			if (I = re(), re()) {
				V(R, e.getBoundingClientRect(), !0), V(le, e.offsetHeight, !0), V(ue, e.offsetWidth, !0);
				let t = he(e);
				_e(e, t) && ye(e, t), window.addEventListener("keydown", me);
			} else be(), V(R, null), window.removeEventListener("keydown", me);
		}
	}), ve(() => () => {
		window.removeEventListener("keydown", me), be();
	});
	let xe = (e) => {
		if (e !== void 0) {
			if (typeof e == "number") return e + "px";
			if (typeof e == "string") return e;
		}
	}, H = (e) => {
		let t = S(oe);
		if (!t) return;
		let n = e.clientY, r = (e) => {
			let r = e.clientY - n;
			n = e.clientY, t.style.height = `${t.offsetHeight + r}px`;
		}, i = () => {
			window.removeEventListener("mousemove", r), window.removeEventListener("mouseup", i);
		};
		window.addEventListener("mousemove", r), window.addEventListener("mouseup", i);
	};
	var Ce = y(), De = B(Ce), Oe = (e) => {
		var m = Te(), y = B(m);
		_(y, () => S(se), !1, (e, m) => {
			ee(e, (e) => V(oe, e, !0), () => S(oe)), w(e, (e, t, n, r, i) => ({
				"data-testid": h(),
				id: c(),
				class: `block ${e ?? ""}`,
				dir: F() ? "rtl" : "ltr",
				"aria-label": ie(),
				style: "",
				[ne]: {
					hidden: b() === "hidden",
					padded: p(),
					flex: S(ce),
					border_focus: f() === "focus",
					border_contrast: f() === "contrast",
					"hide-container": !g() && !v(),
					fullscreen: re(),
					animating: re() && S(R) !== null,
					"auto-margin": E() === null
				},
				[te]: {
					height: t,
					"min-height": n,
					"max-height": r,
					"--start-top": S(R) ? `${S(R).top}px` : "0px",
					"--start-left": S(R) ? `${S(R).left}px` : "0px",
					"--start-width": S(R) ? `${S(R).width}px` : "0px",
					"--start-height": S(R) ? `${S(R).height}px` : "0px",
					width: i,
					"border-style": d(),
					overflow: x() ? C() : "hidden",
					"flex-grow": E(),
					"min-width": `calc(min(${O()}px, 100%))`
				}
			}), [
				() => u()?.join(" ") || "",
				() => re() ? void 0 : xe(r()),
				() => re() ? void 0 : xe(i()),
				() => re() ? void 0 : xe(o()),
				() => re() ? void 0 : typeof s() == "number" ? `calc(min(${s()}px, 100%))` : xe(s())
			], void 0, void 0, "svelte-1stq1b1");
			var _ = Te(), y = B(_);
			ae(y, () => n.children ?? T);
			var k = D(y, 2), A = (e) => {
				var n = we();
				l("mousedown", n, H), t(e, n);
			};
			a(k, (e) => {
				j() && e(A);
			}), t(m, _);
		});
		var k = D(y, 2), A = (e) => {
			var n = Ee();
			let r;
			N(() => r = Se(n, "", r, {
				height: S(le) + "px",
				width: S(ue) + "px"
			})), t(e, n);
		};
		a(k, (e) => {
			re() && e(A);
		}), t(e, m);
	};
	a(De, (e) => {
		(b() === !0 || b() === "hidden") && e(Oe);
	}), t(e, Ce), M();
}
o(["mousedown"]);
// frontend/node_modules/@gradio/atoms/dist/src/BlockLabel.svelte
var Oe = s("<label data-testid=\"block-label\"><span class=\"svelte-1fzogyz\"><!></span> </label>");
function ke(e, n) {
	let r = z(n, "label", 3, null), i = z(n, "show_label", 3, !0), a = z(n, "disable", 3, !1), o = z(n, "float", 3, !0), s = z(n, "rtl", 3, !1);
	var c = Oe();
	let l;
	var d = R(c), f = R(d);
	oe(f, () => n.Icon, (e, t) => {
		t(e, {});
	}), F(d);
	var p = D(d);
	F(c), N(() => {
		be(c, "dir", s() ? "rtl" : "ltr"), l = g(c, 1, "svelte-1fzogyz", null, l, {
			hide: !i(),
			"sr-only": !i(),
			float: o(),
			"hide-label": a()
		}), u(p, ` ${r() ?? ""}`), c.dir = c.dir;
	}), t(e, c);
}
// frontend/node_modules/@gradio/atoms/dist/src/DownloadLink.svelte
var Ae = /* @__PURE__ */ new Set([
	"$$slots",
	"$$events",
	"$$legacy"
]), je = s("<a><!></a>");
function Me(e, n) {
	P(n, !0);
	var r = this && this.__rest || function(e, t) {
		var n = {};
		for (var r in e) Object.prototype.hasOwnProperty.call(e, r) && t.indexOf(r) < 0 && (n[r] = e[r]);
		if (e != null && typeof Object.getOwnPropertySymbols == "function") for (var i = 0, r = Object.getOwnPropertySymbols(e); i < r.length; i++) t.indexOf(r[i]) < 0 && Object.prototype.propertyIsEnumerable.call(e, r[i]) && (n[r[i]] = e[r[i]]);
		return n;
	};
	let i = ie(n, Ae), { href: a = void 0, download: o = void 0, children: s } = i, c = r(i, [
		"href",
		"download",
		"children"
	]);
	var l = je();
	w(l, () => ({
		class: "download-link",
		"data-testid": "download-link",
		href: a,
		target: typeof window < "u" && window.__is_colab__ ? "_blank" : null,
		rel: "noopener noreferrer",
		download: o,
		...c,
		[te]: { position: "relative" }
	}), void 0, void 0, void 0, "svelte-q1286o");
	var u = R(l);
	s?.(u), F(l), t(e, l), M();
}
// frontend/node_modules/@gradio/atoms/dist/src/IconButton.svelte
var Ne = s("<span class=\"svelte-vvirtv\"> </span>"), Pe = s("<button><!> <div><!> <!></div></button>");
function Fe(e, n) {
	let r = z(n, "label", 3, ""), i = z(n, "show_label", 3, !1), o = z(n, "pending", 3, !1), s = z(n, "size", 3, "small"), c = z(n, "padded", 3, !0), d = z(n, "highlight", 3, !1), f = z(n, "disabled", 3, !1), p = z(n, "hasPopup", 3, !1), m = z(n, "color", 3, "var(--block-label-text-color)"), h = z(n, "transparent", 3, !1), _ = z(n, "background", 3, "var(--block-background-fill)"), v = z(n, "border", 3, "transparent"), b = L(() => d() ? "var(--color-accent)" : m());
	var x = Pe();
	let C, w;
	var T = R(x), E = (e) => {
		var n = Ne(), i = I(n, !0);
		N(() => u(i, r())), t(e, n);
	};
	a(T, (e) => {
		i() && e(E);
	});
	var O = D(T, 2);
	let k;
	var A = R(O);
	oe(A, () => n.Icon, (e, t) => {
		t(e, {});
	});
	var j = D(A, 2), M = (e) => {
		var r = y(), i = B(r);
		ae(i, () => n.children), t(e, r);
	};
	a(j, (e) => {
		n.children && e(M);
	}), F(O), F(x), N(() => {
		C = g(x, 1, "icon-button svelte-vvirtv", null, C, {
			pending: o(),
			padded: c(),
			highlight: d(),
			transparent: h()
		}), x.disabled = f(), be(x, "aria-label", r()), be(x, "aria-haspopup", p()), be(x, "title", r()), w = Se(x, "", w, {
			"--border-color": v(),
			color: !f() && S(b) ? S(b) : "var(--block-label-text-color)",
			"--bg-color": f() ? "auto" : _()
		}), k = g(O, 1, "svelte-vvirtv", null, k, {
			"x-small": s() === "x-small",
			small: s() === "small",
			large: s() === "large",
			medium: s() === "medium"
		});
	}), l("click", x, function(...e) {
		n.onclick?.apply(this, e);
	}), t(e, x);
}
o(["click"]);
// frontend/node_modules/@gradio/atoms/dist/src/Empty.svelte
var Ie = s("<div aria-label=\"Empty value\"><div class=\"icon svelte-1xcwp1t\"><!></div></div>");
function Le(e, n) {
	let r = z(n, "size", 3, "small"), i = z(n, "unpadded_box", 3, !1), a = A(void 0), o = L(() => s(S(a)));
	function s(e) {
		if (!e) return !1;
		let { height: t } = e.getBoundingClientRect(), { height: n } = e.parentElement?.getBoundingClientRect() || { height: t };
		return t > n + 2;
	}
	var c = Ie();
	let l;
	var u = R(c), d = R(u);
	ae(d, () => n.children ?? T), F(u), F(c), ee(c, (e) => V(a, e), () => S(a)), N(() => l = g(c, 1, "empty svelte-1xcwp1t", null, l, {
		small: r() === "small",
		large: r() === "large",
		unpadded_box: i(),
		small_parent: S(o)
	})), t(e, c);
}
// frontend/node_modules/svelte/src/internal/flags/legacy.js
le();
// frontend/node_modules/@gradio/icons/dist/src/Camera.svelte
var Re = v("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100%\" height=\"100%\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"feather feather-camera\"><path d=\"M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z\"></path><circle cx=\"12\" cy=\"13\" r=\"4\"></circle></svg>");
function ze(e) {
	var n = Re();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/Circle.svelte
var U = v("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100%\" height=\"100%\" viewBox=\"0 0 24 24\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"feather feather-circle\"><circle cx=\"12\" cy=\"12\" r=\"10\"></circle></svg>");
function Be(e) {
	var n = U();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/Clear.svelte
var Ve = v("<svg width=\"100%\" height=\"100%\" viewBox=\"0 0 24 24\" version=\"1.1\" xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" xml:space=\"preserve\" stroke=\"currentColor\" style=\"fill-rule:evenodd;clip-rule:evenodd;stroke-linecap:round;stroke-linejoin:round;\"><g transform=\"matrix(1.14096,-0.140958,-0.140958,1.14096,-0.0559523,0.0559523)\"><path d=\"M18,6L6.087,17.913\" style=\"fill:none;fill-rule:nonzero;stroke-width:2px;\"></path></g><path d=\"M4.364,4.364L19.636,19.636\" style=\"fill:none;fill-rule:nonzero;stroke-width:2px;\"></path></svg>");
function He(e) {
	var n = Ve();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/Community.svelte
var Ue = v("<svg id=\"icon\" xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 32 32\" width=\"100%\" height=\"100%\"><path d=\"M23,20a5,5,0,0,0-3.89,1.89L11.8,17.32a4.46,4.46,0,0,0,0-2.64l7.31-4.57A5,5,0,1,0,18,7a4.79,4.79,0,0,0,.2,1.32l-7.31,4.57a5,5,0,1,0,0,6.22l7.31,4.57A4.79,4.79,0,0,0,18,25a5,5,0,1,0,5-5ZM23,4a3,3,0,1,1-3,3A3,3,0,0,1,23,4ZM7,19a3,3,0,1,1,3-3A3,3,0,0,1,7,19Zm16,9a3,3,0,1,1,3-3A3,3,0,0,1,23,28Z\" fill=\"currentColor\"></path></svg>");
function We(e) {
	var n = Ue();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/Download.svelte
var Ge = v("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100%\" height=\"100%\" viewBox=\"0 0 32 32\"><path fill=\"currentColor\" d=\"M26 24v4H6v-4H4v4a2 2 0 0 0 2 2h20a2 2 0 0 0 2-2v-4zm0-10l-1.41-1.41L17 20.17V2h-2v18.17l-7.59-7.58L6 14l10 10l10-10z\"></path></svg>");
function Ke(e) {
	var n = Ge();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/DownloadAll.svelte
var qe = v("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100%\" height=\"100%\" viewBox=\"0 0 32 32\" aria-hidden=\"true\"><path fill=\"currentColor\" d=\"M24 4H10a2 2 0 0 0-2 2v2H6a2 2 0 0 0-2 2v12h2V10h14v4h2V10a2 2 0 0 0-2-2H10V6h14v8h2V6a2 2 0 0 0-2-2Z\"></path><path fill=\"currentColor\" d=\"M27.59 20.59L22 26.17V16h-2v10.17l-5.59-5.58L13 22l8 8l8-8l-1.41-1.41Z\"></path><path fill=\"currentColor\" d=\"M10 26H4v-2h6v2Zm4 4H6a2 2 0 0 1-2-2h10v2Z\"></path></svg>");
function Je(e) {
	var n = qe();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/DropdownArrow.svelte
var Ye = v("<svg class=\"dropdown-arrow svelte-gtiaeq\" xmlns=\"http://www.w3.org/2000/svg\" width=\"100%\" height=\"100%\" viewBox=\"0 0 18 18\"><path d=\"M5 8l4 4 4-4z\"></path></svg>");
function Xe(e) {
	var n = Ye();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/Edit.svelte
var Ze = v("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100%\" height=\"100%\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"feather feather-edit-2\"><path d=\"M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z\"></path></svg>");
function Qe(e) {
	var n = Ze();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/File.svelte
var $e = v("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100%\" height=\"100%\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"feather feather-file\"><path d=\"M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z\"></path><polyline points=\"13 2 13 9 20 9\"></polyline></svg>");
function et(e) {
	var n = $e();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/Image.svelte
var tt = v("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100%\" height=\"100%\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"feather feather-image\"><rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"2\" ry=\"2\"></rect><circle cx=\"8.5\" cy=\"8.5\" r=\"1.5\"></circle><polyline points=\"21 15 16 10 5 21\"></polyline></svg>");
function nt(e) {
	var n = tt();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/ImagePaste.svelte
var rt = v("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100%\" height=\"100%\" viewBox=\"0 0 256 256\"><path fill=\"currentColor\" d=\"M200 32h-36.26a47.92 47.92 0 0 0-71.48 0H56a16 16 0 0 0-16 16v168a16 16 0 0 0 16 16h144a16 16 0 0 0 16-16V48a16 16 0 0 0-16-16m-72 0a32 32 0 0 1 32 32H96a32 32 0 0 1 32-32m72 184H56V48h26.75A47.9 47.9 0 0 0 80 64v8a8 8 0 0 0 8 8h80a8 8 0 0 0 8-8v-8a47.9 47.9 0 0 0-2.75-16H200Z\"></path></svg>");
function it(e) {
	var n = rt();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/Maximize.svelte
var at = v("<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"feather feather-maximize\" width=\"100%\" height=\"100%\"><path d=\"M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3\"></path></svg>");
function ot(e) {
	var n = at();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/Microphone.svelte
var st = v("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100%\" height=\"100%\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"feather feather-mic\"><path d=\"M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z\"></path><path d=\"M19 10v2a7 7 0 0 1-14 0v-2\"></path><line x1=\"12\" y1=\"19\" x2=\"12\" y2=\"23\"></line><line x1=\"8\" y1=\"23\" x2=\"16\" y2=\"23\"></line></svg>");
function ct(e) {
	var n = st();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/Minimize.svelte
var lt = v("<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"feather feather-minimize\" width=\"100%\" height=\"100%\"><path d=\"M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3\"></path></svg>");
function ut(e) {
	var n = lt();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/Play.svelte
var dt = v("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100%\" height=\"100%\" viewBox=\"0 0 24 24\" fill=\"currentColor\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><polygon points=\"5 3 19 12 5 21 5 3\"></polygon></svg>");
function ft(e) {
	var n = dt();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/Square.svelte
var pt = v("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100%\" height=\"100%\" viewBox=\"0 0 24 24\" stroke=\"currentColor\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"feather feather-square\"><rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"2\" ry=\"2\"></rect></svg>");
function mt(e, n) {
	let r = z(n, "fill", 8, "currentColor"), i = z(n, "stroke_width", 8, 1.5);
	var a = pt();
	N(() => {
		be(a, "fill", r()), be(a, "stroke-width", `${i()}`);
	}), t(e, a);
}
// frontend/node_modules/@gradio/icons/dist/src/Undo.svelte
var ht = v("<svg aria-label=\"undo\" xmlns=\"http://www.w3.org/2000/svg\" width=\"100%\" height=\"100%\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"feather feather-rotate-ccw\"><polyline points=\"1 4 1 10 7 10\"></polyline><path d=\"M3.51 15a9 9 0 1 0 2.13-9.36L1 10\"></path></svg>");
function gt(e) {
	var n = ht();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/Upload.svelte
var _t = v("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"90%\" height=\"90%\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"feather feather-upload\"><path d=\"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4\"></path><polyline points=\"17 8 12 3 7 8\"></polyline><line x1=\"12\" y1=\"3\" x2=\"12\" y2=\"15\"></line></svg>");
function vt(e) {
	var n = _t();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/Video.svelte
var yt = v("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100%\" height=\"100%\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.5\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"feather feather-video\"><polygon points=\"23 7 16 12 23 17 23 7\"></polygon><rect x=\"1\" y=\"5\" width=\"15\" height=\"14\" rx=\"2\" ry=\"2\"></rect></svg>");
function bt(e) {
	var n = yt();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/Webcam.svelte
var xt = v("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100%\" height=\"100%\" viewBox=\"0 0 24 24\"><path fill=\"currentColor\" d=\"M12 2c-4.963 0-9 4.038-9 9c0 3.328 1.82 6.232 4.513 7.79l-2.067 1.378A1 1 0 0 0 6 22h12a1 1 0 0 0 .555-1.832l-2.067-1.378C19.18 17.232 21 14.328 21 11c0-4.962-4.037-9-9-9zm0 16c-3.859 0-7-3.141-7-7c0-3.86 3.141-7 7-7s7 3.14 7 7c0 3.859-3.141 7-7 7z\"></path><path fill=\"currentColor\" d=\"M12 6c-2.757 0-5 2.243-5 5s2.243 5 5 5s5-2.243 5-5s-2.243-5-5-5zm0 8c-1.654 0-3-1.346-3-3s1.346-3 3-3s3 1.346 3 3s-1.346 3-3 3z\"></path></svg>");
function St(e) {
	var n = xt();
	t(e, n);
}
// frontend/node_modules/@gradio/icons/dist/src/Spinner.svelte
var Ct = v("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100%\" height=\"100%\" viewBox=\"0 0 50 50\" class=\"svelte-3g80w1\"><circle cx=\"25\" cy=\"25\" r=\"20\" fill=\"none\" stroke-width=\"3.0\" stroke-linecap=\"round\" stroke-dasharray=\"94.2477796076938 94.2477796076938\" stroke-dashoffset=\"0\" class=\"svelte-3g80w1\"><animateTransform attributeName=\"transform\" type=\"rotate\" from=\"0 25 25\" to=\"360 25 25\" repeatCount=\"indefinite\" class=\"svelte-3g80w1\"></animateTransform></circle></svg>");
function wt(e) {
	var n = Ct();
	t(e, n);
}
// frontend/node_modules/@gradio/theme/dist/src/colors.js
var Tt = [
	{
		color: "red",
		primary: 600,
		secondary: 100
	},
	{
		color: "green",
		primary: 600,
		secondary: 100
	},
	{
		color: "blue",
		primary: 600,
		secondary: 100
	},
	{
		color: "yellow",
		primary: 500,
		secondary: 100
	},
	{
		color: "purple",
		primary: 600,
		secondary: 100
	},
	{
		color: "teal",
		primary: 600,
		secondary: 100
	},
	{
		color: "orange",
		primary: 600,
		secondary: 100
	},
	{
		color: "cyan",
		primary: 600,
		secondary: 100
	},
	{
		color: "lime",
		primary: 500,
		secondary: 100
	},
	{
		color: "pink",
		primary: 600,
		secondary: 100
	}
], Et = {
	inherit: "inherit",
	current: "currentColor",
	transparent: "transparent",
	black: "#000",
	white: "#fff",
	slate: {
		50: "#f8fafc",
		100: "#f1f5f9",
		200: "#e2e8f0",
		300: "#cbd5e1",
		400: "#94a3b8",
		500: "#64748b",
		600: "#475569",
		700: "#334155",
		800: "#1e293b",
		900: "#0f172a",
		950: "#020617"
	},
	gray: {
		50: "#f9fafb",
		100: "#f3f4f6",
		200: "#e5e7eb",
		300: "#d1d5db",
		400: "#9ca3af",
		500: "#6b7280",
		600: "#4b5563",
		700: "#374151",
		800: "#1f2937",
		900: "#111827",
		950: "#030712"
	},
	zinc: {
		50: "#fafafa",
		100: "#f4f4f5",
		200: "#e4e4e7",
		300: "#d4d4d8",
		400: "#a1a1aa",
		500: "#71717a",
		600: "#52525b",
		700: "#3f3f46",
		800: "#27272a",
		900: "#18181b",
		950: "#09090b"
	},
	neutral: {
		50: "#fafafa",
		100: "#f5f5f5",
		200: "#e5e5e5",
		300: "#d4d4d4",
		400: "#a3a3a3",
		500: "#737373",
		600: "#525252",
		700: "#404040",
		800: "#262626",
		900: "#171717",
		950: "#0a0a0a"
	},
	stone: {
		50: "#fafaf9",
		100: "#f5f5f4",
		200: "#e7e5e4",
		300: "#d6d3d1",
		400: "#a8a29e",
		500: "#78716c",
		600: "#57534e",
		700: "#44403c",
		800: "#292524",
		900: "#1c1917",
		950: "#0c0a09"
	},
	red: {
		50: "#fef2f2",
		100: "#fee2e2",
		200: "#fecaca",
		300: "#fca5a5",
		400: "#f87171",
		500: "#ef4444",
		600: "#dc2626",
		700: "#b91c1c",
		800: "#991b1b",
		900: "#7f1d1d",
		950: "#450a0a"
	},
	orange: {
		50: "#fff7ed",
		100: "#ffedd5",
		200: "#fed7aa",
		300: "#fdba74",
		400: "#fb923c",
		500: "#f97316",
		600: "#ea580c",
		700: "#c2410c",
		800: "#9a3412",
		900: "#7c2d12",
		950: "#431407"
	},
	amber: {
		50: "#fffbeb",
		100: "#fef3c7",
		200: "#fde68a",
		300: "#fcd34d",
		400: "#fbbf24",
		500: "#f59e0b",
		600: "#d97706",
		700: "#b45309",
		800: "#92400e",
		900: "#78350f",
		950: "#451a03"
	},
	yellow: {
		50: "#fefce8",
		100: "#fef9c3",
		200: "#fef08a",
		300: "#fde047",
		400: "#facc15",
		500: "#eab308",
		600: "#ca8a04",
		700: "#a16207",
		800: "#854d0e",
		900: "#713f12",
		950: "#422006"
	},
	lime: {
		50: "#f7fee7",
		100: "#ecfccb",
		200: "#d9f99d",
		300: "#bef264",
		400: "#a3e635",
		500: "#84cc16",
		600: "#65a30d",
		700: "#4d7c0f",
		800: "#3f6212",
		900: "#365314",
		950: "#1a2e05"
	},
	green: {
		50: "#f0fdf4",
		100: "#dcfce7",
		200: "#bbf7d0",
		300: "#86efac",
		400: "#4ade80",
		500: "#22c55e",
		600: "#16a34a",
		700: "#15803d",
		800: "#166534",
		900: "#14532d",
		950: "#052e16"
	},
	emerald: {
		50: "#ecfdf5",
		100: "#d1fae5",
		200: "#a7f3d0",
		300: "#6ee7b7",
		400: "#34d399",
		500: "#10b981",
		600: "#059669",
		700: "#047857",
		800: "#065f46",
		900: "#064e3b",
		950: "#022c22"
	},
	teal: {
		50: "#f0fdfa",
		100: "#ccfbf1",
		200: "#99f6e4",
		300: "#5eead4",
		400: "#2dd4bf",
		500: "#14b8a6",
		600: "#0d9488",
		700: "#0f766e",
		800: "#115e59",
		900: "#134e4a",
		950: "#042f2e"
	},
	cyan: {
		50: "#ecfeff",
		100: "#cffafe",
		200: "#a5f3fc",
		300: "#67e8f9",
		400: "#22d3ee",
		500: "#06b6d4",
		600: "#0891b2",
		700: "#0e7490",
		800: "#155e75",
		900: "#164e63",
		950: "#083344"
	},
	sky: {
		50: "#f0f9ff",
		100: "#e0f2fe",
		200: "#bae6fd",
		300: "#7dd3fc",
		400: "#38bdf8",
		500: "#0ea5e9",
		600: "#0284c7",
		700: "#0369a1",
		800: "#075985",
		900: "#0c4a6e",
		950: "#082f49"
	},
	blue: {
		50: "#eff6ff",
		100: "#dbeafe",
		200: "#bfdbfe",
		300: "#93c5fd",
		400: "#60a5fa",
		500: "#3b82f6",
		600: "#2563eb",
		700: "#1d4ed8",
		800: "#1e40af",
		900: "#1e3a8a",
		950: "#172554"
	},
	indigo: {
		50: "#eef2ff",
		100: "#e0e7ff",
		200: "#c7d2fe",
		300: "#a5b4fc",
		400: "#818cf8",
		500: "#6366f1",
		600: "#4f46e5",
		700: "#4338ca",
		800: "#3730a3",
		900: "#312e81",
		950: "#1e1b4b"
	},
	violet: {
		50: "#f5f3ff",
		100: "#ede9fe",
		200: "#ddd6fe",
		300: "#c4b5fd",
		400: "#a78bfa",
		500: "#8b5cf6",
		600: "#7c3aed",
		700: "#6d28d9",
		800: "#5b21b6",
		900: "#4c1d95",
		950: "#2e1065"
	},
	purple: {
		50: "#faf5ff",
		100: "#f3e8ff",
		200: "#e9d5ff",
		300: "#d8b4fe",
		400: "#c084fc",
		500: "#a855f7",
		600: "#9333ea",
		700: "#7e22ce",
		800: "#6b21a8",
		900: "#581c87",
		950: "#3b0764"
	},
	fuchsia: {
		50: "#fdf4ff",
		100: "#fae8ff",
		200: "#f5d0fe",
		300: "#f0abfc",
		400: "#e879f9",
		500: "#d946ef",
		600: "#c026d3",
		700: "#a21caf",
		800: "#86198f",
		900: "#701a75",
		950: "#4a044e"
	},
	pink: {
		50: "#fdf2f8",
		100: "#fce7f3",
		200: "#fbcfe8",
		300: "#f9a8d4",
		400: "#f472b6",
		500: "#ec4899",
		600: "#db2777",
		700: "#be185d",
		800: "#9d174d",
		900: "#831843",
		950: "#500724"
	},
	rose: {
		50: "#fff1f2",
		100: "#ffe4e6",
		200: "#fecdd3",
		300: "#fda4af",
		400: "#fb7185",
		500: "#f43f5e",
		600: "#e11d48",
		700: "#be123c",
		800: "#9f1239",
		900: "#881337",
		950: "#4c0519"
	}
};
Tt.reduce((e, { color: t, primary: n, secondary: r }) => ({
	...e,
	[t]: {
		primary: Et[t][n],
		secondary: Et[t][r]
	}
}), {});
// frontend/node_modules/@gradio/utils/dist/src/url.js
function Dt(e, t, n) {
	let r = n ?? (typeof window < "u" ? window.location.href : void 0), i = r ? new URL(e || "/", r) : new URL(e), a = r ? new URL(r) : null, o = i.pathname.replace(/\/$/, ""), s = t.startsWith("/") ? t : `/${t}`, c = n !== void 0 || typeof window < "u" && window.gradio_config !== void 0, l = a && i.hostname === a.hostname && c ? a.origin : i.origin;
	return new URL(`${o}${s}`, l);
}
// frontend/node_modules/svelte/src/store/index-client.js
function Ot(t) {
	let n, r = Ce((e) => {
		let r = !1, i = t.subscribe((t) => {
			n = t, r && e();
		});
		return r = !0, i;
	});
	function i() {
		return e() ? (r(), n) : k(t);
	}
	return "set" in t ? {
		get current() {
			return i();
		},
		set current(e) {
			t.set(e);
		}
	} : { get current() {
		return i();
	} };
}
var kt = [
	"label",
	"info",
	"placeholder",
	"description",
	"title",
	"value"
], At = class extends Error {
	constructor(e) {
		super(e), this.name = "ShareError";
	}
};
async function jt(e, t) {
	if (window.__gradio_space__ == null) throw new At("Must be on Spaces to share.");
	let n, r, i;
	if (t === "url") {
		let t;
		if (typeof e == "object" && e.url) t = e.url;
		else if (typeof e == "string") t = e;
		else throw Error("Invalid data format for URL type");
		let a = await fetch(t);
		n = await a.blob(), r = a.headers.get("content-type") || "", i = a.headers.get("content-disposition") || "";
	} else {
		let t;
		if (typeof e == "object" && e.path) t = e.path;
		else if (typeof e == "string") t = e;
		else throw Error("Invalid data format for base64 type");
		n = Mt(t), r = t.split(";")[0].split(":")[1], i = "file." + r.split("/")[1];
	}
	let a = new File([n], i, { type: r }), o = await fetch("https://huggingface.co/uploads", {
		method: "POST",
		body: a,
		headers: {
			"Content-Type": a.type,
			"X-Requested-With": "XMLHttpRequest"
		}
	});
	if (!o.ok) throw o.headers.get("content-type")?.includes("application/json") ? new At(`Upload failed: ${(await o.json()).error}`) : new At("Upload failed.");
	return await o.text();
}
function Mt(e) {
	for (var t = e.split(","), n = t[0].match(/:(.*?);/)[1], r = atob(t[1]), i = r.length, a = new Uint8Array(i); i--;) a[i] = r.charCodeAt(i);
	return new Blob([a], { type: n });
}
var Nt = (e) => {
	Promise.resolve(e.play()).catch((e) => {
		e?.name !== "AbortError" && e?.name !== "NotAllowedError" && console.warn("play() was rejected:", e);
	});
}, Pt = /* @__PURE__ */ "elem_id.elem_classes.visible.interactive.server_fns.server.id.target.theme_mode.version.root.autoscroll.max_file_size.formatter.client.load_component.scale.min_width.theme.padding.loading_status.label.show_label.validation_error.show_progress.api_prefix.container.attached_events.register_component.unregister_component.dispatcher".split(".");
function Ft(e) {
	return typeof e == "string" && e.includes("__i18n__");
}
var It = class {
	load_component;
	#e = A(fe({}));
	get shared() {
		return S(this.#e);
	}
	set shared(e) {
		V(this.#e, e, !0);
	}
	#t = A(fe({}));
	get props() {
		return S(this.#t);
	}
	set props(e) {
		V(this.#t, e, !0);
	}
	#n = A((e) => e);
	get i18n() {
		return S(this.#n);
	}
	set i18n(e) {
		V(this.#n, e, !0);
	}
	i18n_store;
	_i18n_from_store;
	translatable_props = {};
	dispatcher;
	last_update = null;
	shared_props = Pt;
	mounted = !1;
	old_value;
	register_component;
	unregister_component;
	set_data_callback;
	get_data_callback;
	registered_id = null;
	last_shared_props;
	last_props;
	constructor(e, t) {
		for (let t in e.shared_props) this.shared[t] = e.shared_props[t];
		for (let t in e.props) t !== "i18n_store" && (this.props[t] = e.props[t]);
		if (t) for (let e in t) this.props[e] === void 0 && (this.props[e] = t[e]);
		this.i18n = this.props.i18n ?? ((e) => e), this.i18n_store = e.props.i18n_store, this._i18n_from_store = this.i18n_store ? Ot(this.i18n_store) : void 0;
		for (let t of kt) this.shared[t] = this._translate_and_store("shared", t, e.shared_props[t]), this.props[t] = this._translate_and_store("props", t, e.props[t]);
		this.load_component = this.shared.load_component, this.register_component = this.shared.register_component || (() => {}), this.unregister_component = this.shared.unregister_component || (() => {}), this.dispatcher = this.shared.dispatcher || (() => {}), this.set_data_callback = this.set_data.bind(this), this.get_data_callback = this.get_data.bind(this), this.register_component(this.shared.id, this.set_data_callback, this.get_data_callback), this.registered_id = this.shared.id, this.last_shared_props = e.shared_props, this.last_props = e.props, ve(() => {
			let t = e.shared_props.id;
			if (this.last_shared_props !== e.shared_props) {
				for (let t in e.shared_props) {
					let n = e.shared_props[t];
					n !== void 0 && (this._is_i18n_managed(`shared.${t}`, n) || (this.shared[t] = n));
				}
				this.last_shared_props = e.shared_props;
			}
			if (this.last_props !== e.props) {
				for (let t in e.props) {
					if (t === "i18n_store") continue;
					let n = e.props[t];
					n !== void 0 && (this._is_i18n_managed(`props.${t}`, n) || (this.props[t] = n));
				}
				this.last_props = e.props;
			}
			this.registered_id !== null && this.registered_id !== t && this.unregister_component(this.registered_id, this.set_data_callback), this.register_component(t, this.set_data_callback, this.get_data_callback), this.registered_id = t, C(() => {
				this.shared.id = t;
			});
		}), ve(() => () => {
			this.registered_id !== null && this.unregister_component(this.registered_id, this.set_data_callback);
		}), ve(() => {
			if (this.i18n_store) return this.i18n_store.subscribe(() => {
				for (let [e, t] of Object.entries(this.translatable_props)) {
					let [n, r] = e.split("."), i = this.i18n(t);
					n === "shared" ? this.shared[r] = i : this.props[r] = i;
				}
			});
		});
	}
	_is_i18n_managed(e, t) {
		let n = this.translatable_props[e];
		return n ? t === n || (delete this.translatable_props[e], !1) : !1;
	}
	_translate_and_store(e, t, n) {
		if (typeof n != "string") return n;
		let r = this.i18n(n);
		return r !== n && (this.translatable_props[`${e}.${t}`] = n), r;
	}
	live_i18n = (e) => (this._i18n_from_store?.current, this.i18n(e));
	dispatch(e, t) {
		this.dispatcher(this.shared.id, e, t);
	}
	async get_data() {
		return me(this.props);
	}
	update(e) {
		this.set_data(e);
	}
	set_data(e) {
		for (let t in e) {
			let n = e[t], r = Ft(n) ? this._translate_and_store(this.shared_props.includes(t) ? "shared" : "props", t, n) : n;
			if (this.shared_props.includes(t)) {
				let e = t;
				this.shared[e] = r;
			} else this.props[t] = r;
		}
	}
	watch_for_change() {
		ve(() => {
			this.mounted ||= (this.old_value = this.props.value, !0), this.old_value != this.props.value && (this.old_value = this.props.value, this.dispatch("change"));
		});
	}
};
// frontend/node_modules/@gradio/atoms/dist/src/ShareButton.svelte
function Lt(e, t) {
	P(t, !0);
	let n = A(!1);
	{
		let r = L(() => t.i18n("common.share"));
		Fe(e, {
			get Icon() {
				return We;
			},
			get label() {
				return S(r);
			},
			get pending() {
				return S(n);
			},
			onclick: async () => {
				try {
					V(n, !0);
					let e = { description: await t.formatter(t.value) };
					t.onshare?.(e);
				} catch (e) {
					console.error(e);
					let n = e instanceof At ? e.message : "Share failed.";
					t.onerror?.(n);
				} finally {
					V(n, !1);
				}
			}
		});
	}
	M();
}
// frontend/node_modules/@gradio/atoms/dist/src/utils/parse_placeholder.js
var Rt = /^(#\s*)(.+)$/m;
function zt(e) {
	let t = e.trim(), n = t.match(Rt);
	if (!n) return [!1, t || !1];
	let [r, , i] = n, a = i.trim();
	if (t === r) return [a, !1];
	let o = n.index === void 0 ? 0 : n.index + r.length;
	return [a, t.substring(o).trim() || !1];
}
// frontend/node_modules/@gradio/atoms/dist/src/UploadText.svelte
var Bt = s("<h2 class=\"svelte-cmuu9m\"> </h2>"), Vt = s("<p class=\"svelte-cmuu9m\"> </p>"), Ht = s("<!> <!>", 1), Ut = s("<span class=\"or svelte-cmuu9m\"> </span> ", 1), Wt = s(" <!>", 1), Gt = s("<span class=\"or svelte-cmuu9m\"> </span> <span> </span>", 1), Kt = s("<span> </span> <!>", 1), qt = s("<div class=\"prompt svelte-cmuu9m\"><!></div>"), Jt = s("<div data-testid=\"upload-text\"><span data-testid=\"upload-icon\"><!></span> <!></div>");
function Yt(e, n) {
	P(n, !0);
	let r = z(n, "type", 3, "file"), i = z(n, "message", 3, void 0), o = z(n, "mode", 3, "full"), s = z(n, "hovered", 3, !1), c = z(n, "placeholder", 3, void 0), l = {
		image: "upload_text.drop_image",
		video: "upload_text.drop_video",
		audio: "upload_text.drop_audio",
		file: "upload_text.drop_file",
		csv: "upload_text.drop_csv",
		gallery: "upload_text.drop_gallery",
		clipboard: "upload_text.paste_clipboard"
	}, d = L(() => c() ? zt(c()) : [!1, !1]), f = L(() => S(d)[0]), p = L(() => S(d)[1]), m, h = A("full");
	function _(e) {
		e <= 0 || V(h, e <= 48 ? "minimal" : e <= 160 ? "compact" : "full", !0);
	}
	ve(() => {
		let e = m.closest(".block") ?? m;
		if (!e.style.height && !e.style.maxHeight) return;
		let t, n = new ResizeObserver(() => {
			cancelAnimationFrame(t), t = requestAnimationFrame(() => {
				_(e.getBoundingClientRect().height);
			});
		});
		return _(e.getBoundingClientRect().height), n.observe(e), () => {
			cancelAnimationFrame(t), n.disconnect();
		};
	});
	var v = Jt();
	let b;
	var x = R(v);
	let C;
	var w = R(x), T = (e) => {
		it(e, {});
	}, E = (e) => {
		vt(e, {});
	};
	a(w, (e) => {
		r() === "clipboard" ? e(T) : e(E, -1);
	}), F(x);
	var O = D(x, 2), k = (e) => {
		var s = y(), c = B(s), d = (e) => {
			var n = Ht(), r = B(n), i = (e) => {
				var n = Bt(), r = I(n, !0);
				N(() => u(r, S(f))), t(e, n);
			};
			a(r, (e) => {
				S(f) && e(i);
			});
			var o = D(r, 2), s = (e) => {
				var n = Vt(), r = I(n, !0);
				N(() => u(r, S(p))), t(e, n);
			};
			a(o, (e) => {
				S(p) && e(s);
			}), t(e, n);
		}, m = (e) => {
			var s = Wt(), c = B(s), d = D(c), f = (e) => {
				var r = Ut(), a = B(r), o = I(a), s = D(a);
				N((e, t) => {
					u(o, `- ${e ?? ""} -`), u(s, ` ${t ?? ""}`);
				}, [() => n.i18n("common.or"), () => i() || n.i18n("upload_text.click_to_upload")]), t(e, r);
			};
			a(d, (e) => {
				o() !== "short" && e(f);
			}), N((e) => u(c, `${e ?? ""} `), [() => n.i18n(l[r()] || l.file)]), t(e, s);
		};
		a(c, (e) => {
			S(f) || S(p) ? e(d) : e(m, -1);
		}), t(e, s);
	}, j = (e) => {
		var s = qt(), c = R(s), d = (e) => {
			var n = Ht(), r = B(n), i = (e) => {
				var n = Bt(), r = I(n, !0);
				N(() => u(r, S(f))), t(e, n);
			};
			a(r, (e) => {
				S(f) && e(i);
			});
			var o = D(r, 2), s = (e) => {
				var n = Vt(), r = I(n, !0);
				N(() => u(r, S(p))), t(e, n);
			};
			a(o, (e) => {
				S(p) && e(s);
			}), t(e, n);
		}, m = (e) => {
			var s = Kt(), c = B(s), d = I(c, !0), f = D(c);
			f.nodeValue = "  ";
			var p = D(f), m = (e) => {
				var r = Gt(), a = B(r), o = I(a, !0), s = D(a, 1, !0);
				s.nodeValue = " ";
				var c = D(s), l = I(c, !0);
				N((e, t) => {
					u(o, e), u(l, t);
				}, [() => n.i18n("common.or"), () => i() || n.i18n("upload_text.click_to_upload")]), t(e, r);
			};
			a(p, (e) => {
				o() !== "short" && e(m);
			}), N((e) => u(d, e), [() => n.i18n(l[r()] || l.file)]), t(e, s);
		};
		a(c, (e) => {
			S(f) || S(p) ? e(d) : e(m, -1);
		}), F(s), t(e, s);
	};
	a(O, (e) => {
		S(h) === "full" ? e(k) : e(j, -1);
	}), F(v), ee(v, (e) => m = e, () => m), N(() => {
		b = g(v, 1, "wrap svelte-cmuu9m", null, b, {
			compact: S(h) === "compact",
			minimal: S(h) === "minimal"
		}), be(v, "data-upload-density", S(h)), C = g(x, 1, "icon-wrap svelte-cmuu9m", null, C, { hovered: s() });
	}), t(e, v), M();
}
// frontend/node_modules/@gradio/atoms/dist/src/SelectSource.svelte
var Xt = s("<button aria-label=\"Upload file\"><!></button>"), Zt = s("<button aria-label=\"Record audio\"><!></button>"), Qt = s("<button aria-label=\"Capture from camera\"><!></button>"), $t = s("<button aria-label=\"Record video from camera\"><!></button>"), en = s("<button aria-label=\"Paste from clipboard\"><!></button>"), tn = s("<span class=\"source-selection svelte-5d261r\" data-testid=\"source-select\"><!> <!> <!> <!> <!></span>");
function nn(e, n) {
	P(n, !0);
	var r = this && this.__awaiter || function(e, t, n, r) {
		function i(e) {
			return e instanceof n ? e : new n(function(t) {
				t(e);
			});
		}
		return new (n ||= Promise)(function(n, a) {
			function o(e) {
				try {
					c(r.next(e));
				} catch (e) {
					a(e);
				}
			}
			function s(e) {
				try {
					c(r.throw(e));
				} catch (e) {
					a(e);
				}
			}
			function c(e) {
				e.done ? n(e.value) : i(e.value).then(o, s);
			}
			c((r = r.apply(e, t || [])).next());
		});
	};
	let i = z(n, "active_source", 15), o = z(n, "handle_clear", 3, () => {}), s = z(n, "handle_select", 3, () => {}), c = L(() => [...new Set(n.sources)]);
	function u(e) {
		return r(this, void 0, void 0, function* () {
			o()(), i(e), s()(e);
		});
	}
	var d = y(), f = B(d), p = (e) => {
		var r = tn(), o = R(r), s = (e) => {
			var n = Xt();
			let r;
			vt(R(n), {}), F(n), N(() => r = g(n, 1, "icon svelte-5d261r", null, r, { selected: i() === "upload" || !i() })), l("click", n, () => u("upload")), t(e, n);
		}, c = L(() => n.sources.includes("upload"));
		a(o, (e) => {
			S(c) && e(s);
		});
		var d = D(o, 2), f = (e) => {
			var n = Zt();
			let r;
			ct(R(n), {}), F(n), N(() => r = g(n, 1, "icon svelte-5d261r", null, r, { selected: i() === "microphone" })), l("click", n, () => u("microphone")), t(e, n);
		}, p = L(() => n.sources.includes("microphone"));
		a(d, (e) => {
			S(p) && e(f);
		});
		var m = D(d, 2), h = (e) => {
			var n = Qt();
			let r;
			St(R(n), {}), F(n), N(() => r = g(n, 1, "icon svelte-5d261r", null, r, { selected: i() === "webcam" })), l("click", n, () => u("webcam")), t(e, n);
		}, _ = L(() => n.sources.includes("webcam"));
		a(m, (e) => {
			S(_) && e(h);
		});
		var v = D(m, 2), y = (e) => {
			var n = $t();
			let r;
			bt(R(n), {}), F(n), N(() => r = g(n, 1, "icon svelte-5d261r", null, r, { selected: i() === "webcam-video" })), l("click", n, () => u("webcam-video")), t(e, n);
		}, b = L(() => n.sources.includes("webcam-video"));
		a(v, (e) => {
			S(b) && e(y);
		});
		var x = D(v, 2), C = (e) => {
			var n = en();
			let r;
			it(R(n), {}), F(n), N(() => r = g(n, 1, "icon svelte-5d261r", null, r, { selected: i() === "clipboard" })), l("click", n, () => u("clipboard")), t(e, n);
		}, w = L(() => n.sources.includes("clipboard"));
		a(x, (e) => {
			S(w) && e(C);
		}), F(r), t(e, r);
	}, m = L(() => S(c).length > 1 || n.sources.includes("clipboard"));
	a(f, (e) => {
		S(m) && e(p);
	}), t(e, d), M();
}
o(["click"]);
// frontend/node_modules/@gradio/atoms/dist/src/CustomButton.svelte
var rn = s("<span class=\"custom-button-label svelte-g7x491\"> </span>"), an = s("<button class=\"custom-button svelte-g7x491\"><!></button>");
function on(e, n) {
	P(n, !0);
	var r = an(), i = R(r), o = (e) => {
		var r = rn(), i = I(r, !0);
		N(() => u(i, n.button.value)), t(e, r);
	};
	a(i, (e) => {
		n.button.value && e(o);
	}), F(r), N(() => {
		be(r, "title", n.button.value || ""), be(r, "aria-label", n.button.value || "Custom action");
	}), l("click", r, () => n.on_click(n.button.id)), t(e, r), M();
}
o(["click"]);
// frontend/node_modules/@gradio/atoms/dist/src/IconButtonWrapper.svelte
var sn = s("<div><!> <!></div>");
function cn(e, n) {
	P(n, !0);
	let r = z(n, "top_panel", 3, !0), i = z(n, "display_top_corner", 3, !1), o = z(n, "show_background", 3, !0), s = z(n, "buttons", 3, null), c = z(n, "on_custom_button_click", 3, null);
	var l = sn(), u = R(l), d = (e) => {
		var r = y(), i = B(r);
		ae(i, () => n.children), t(e, r);
	};
	a(u, (e) => {
		n.children && e(d);
	});
	var p = D(u, 2), h = (e) => {
		var n = y(), r = B(n);
		f(r, 17, s, m, (e, n) => {
			var r = y(), i = B(r), o = (e) => {
				on(e, {
					get button() {
						return S(n);
					},
					on_click: (e) => {
						c() && c()(e);
					}
				});
			};
			a(i, (e) => {
				typeof S(n) != "string" && e(o);
			}), t(e, r);
		}), t(e, n);
	};
	a(p, (e) => {
		s() && e(h);
	}), F(l), N(() => g(l, 1, `icon-button-wrapper ${r() ? "top-panel" : ""} ${i() ? "display-top-corner" : "hide-top-corner"} ${o() ? "" : "no-background"}`, "svelte-1f7yqtk")), t(e, l), M();
}
// frontend/node_modules/@gradio/atoms/dist/src/FullscreenButton.svelte
function ln(e, n) {
	P(n, !0);
	var r = y(), i = B(r), o = (e) => {
		Fe(e, {
			get Icon() {
				return ut;
			},
			label: "Exit fullscreen mode",
			onclick: () => n.onclick(!1)
		});
	}, s = (e) => {
		Fe(e, {
			get Icon() {
				return ot;
			},
			label: "Fullscreen",
			onclick: () => n.onclick(!0)
		});
	};
	a(i, (e) => {
		n.fullscreen ? e(o) : e(s, -1);
	}), t(e, r), M();
}
// frontend/node_modules/@gradio/client/dist/browser.js
async function un(e, t) {
	return e.map((e) => new dn({
		path: e.name,
		orig_name: e.name,
		blob: e,
		size: e.size,
		mime_type: e.type,
		is_stream: t
	}));
}
var dn = class {
	path;
	url;
	orig_name;
	size;
	blob;
	is_stream;
	mime_type;
	alt_text;
	b64;
	meta = { _type: "gradio.FileData" };
	constructor({ path: e, url: t, orig_name: n, size: r, blob: i, is_stream: a, mime_type: o, alt_text: s, b64: c }) {
		this.path = e, this.url = t, this.orig_name = n, this.size = r, this.blob = t ? void 0 : i, this.is_stream = a, this.mime_type = o, this.alt_text = s, this.b64 = c;
	}
};
typeof process < "u" && process.versions && process.versions.node, TransformStream;
var fn = "gradio:run-history:";
`${fn}`, `${fn}`, `${fn}`;
// frontend/node_modules/@gradio/upload/dist/src/UploadProgress.svelte
var pn = s("<div class=\"file svelte-12marlv\"><span><div class=\"progress-bar svelte-12marlv\"><progress style=\"visibility:hidden;height:0;width:0;\" max=\"100\" class=\"svelte-12marlv\"> </progress></div></span> <span class=\"file-name svelte-12marlv\"> </span></div>"), mn = s("<div><span class=\"uploading svelte-12marlv\"> </span> <!></div>");
function hn(e, n) {
	P(n, !0);
	var r = this && this.__awaiter || function(e, t, n, r) {
		function i(e) {
			return e instanceof n ? e : new n(function(t) {
				t(e);
			});
		}
		return new (n ||= Promise)(function(n, a) {
			function o(e) {
				try {
					c(r.next(e));
				} catch (e) {
					a(e);
				}
			}
			function s(e) {
				try {
					c(r.throw(e));
				} catch (e) {
					a(e);
				}
			}
			function c(e) {
				e.done ? n(e.value) : i(e.value).then(o, s);
			}
			c((r = r.apply(e, t || [])).next());
		});
	};
	let i, o = A(!1), s = A(void 0), c = A(fe(n.files.map((e) => Object.assign(Object.assign({}, e), { progress: 0 })))), l = L(() => S(s) || S(c)[0]);
	function d(e, t) {
		V(c, S(c).map((n) => (n.orig_name === e && (n.progress += t), n)), !0);
	}
	function f(e) {
		return e.progress * 100 / (e.size || 0) || 0;
	}
	ue(() => r(void 0, void 0, void 0, function* () {
		let e = Dt(n.root, `/gradio_api/upload_progress?upload_id=${n.upload_id}`);
		if (i = yield n.stream_handler(e), i == null) throw Error("Event source is not defined");
		i.onmessage = function(e) {
			return r(this, void 0, void 0, function* () {
				let t = JSON.parse(e.data);
				S(o) || V(o, !0), t.msg === "done" ? (i?.close(), n.ondone === null || n.ondone === void 0 || n.ondone()) : (V(s, t, !0), d(t.orig_name, t.chunk_size));
			});
		};
	})), _e(() => {
		(i != null || i != null) && i.close();
	});
	function p(e) {
		let t = 0;
		return e.forEach((e) => {
			t += f(e);
		}), document.documentElement.style.setProperty("--upload-progress-width", (t / e.length).toFixed(2) + "%"), t / e.length;
	}
	ve(() => {
		p(S(c));
	});
	var m = mn();
	let h;
	var _ = R(m), v = I(_), y = D(_, 2), b = (e) => {
		var n = pn(), r = R(n), i = R(r), a = R(i), o = I(a, !0);
		F(i), F(r);
		var s = D(r, 2), c = I(s, !0);
		F(n), N((e, t) => {
			H(a, e), u(o, t), u(c, S(l).orig_name);
		}, [() => f(S(l)), () => f(S(l))]), t(e, n);
	};
	a(y, (e) => {
		S(l) && e(b);
	}), F(m), N(() => {
		h = g(m, 1, "wrap svelte-12marlv", null, h, { progress: S(o) }), u(v, `Uploading ${S(c).length ?? ""}
		${S(c).length > 1 ? "files" : "file"}...`);
	}), t(e, m), M();
}
// frontend/node_modules/@gradio/upload/dist/src/utils.js
function gn(e, t, n) {
	if (!e || e === "*" || e === "file/*" || Array.isArray(e) && e.some((e) => e === "*" || e === "file/*")) return !0;
	let r;
	if (typeof e == "string") r = e.split(",").map((e) => e.trim());
	else if (Array.isArray(e)) r = e;
	else return !1;
	let i = t.toLowerCase();
	return r.some((e) => {
		if (!e.startsWith(".")) return !1;
		let t = e.toLowerCase();
		return i.length > t.length && i.endsWith(t);
	}) || r.some((e) => {
		let [t] = e.split("/").map((e) => e.trim());
		return e.endsWith("/*") && n.startsWith(t + "/");
	});
}
function _n(e) {
	if (e == null) return;
	let t = Array.isArray(e) ? e : e.split(","), n = /* @__PURE__ */ new Set();
	for (let e of t) {
		let t = e.trim();
		if (!t) continue;
		n.add(t);
		let r = t.lastIndexOf(".");
		t.startsWith(".") && r > 0 && n.add(t.slice(r));
	}
	return Array.from(n).join(", ");
}
function vn() {
	let e, t;
	return {
		drag(n, r = {}) {
			t = r;
			function i() {
				e = document.createElement("input"), e.type = "file", e.style.display = "none", e.setAttribute("aria-label", "File upload"), e.setAttribute("data-testid", "file-upload");
				let r = _n(t.accepted_types ?? null);
				r && (e.accept = r), e.multiple = t.mode === "multiple" || !1, t.mode === "directory" && (e.webkitdirectory = !0, e.setAttribute("directory", ""), e.setAttribute("mozdirectory", "")), n.appendChild(e);
			}
			i();
			function a(e) {
				e.preventDefault(), e.stopPropagation();
			}
			let o = 0;
			function s(e) {
				e.preventDefault(), e.stopPropagation(), o++, o === 1 && t.on_drag_change?.(!0);
			}
			function c(e) {
				e.preventDefault(), e.stopPropagation(), o = Math.max(0, o - 1), o === 0 && t.on_drag_change?.(!1);
			}
			function l(e) {
				if (e.preventDefault(), e.stopPropagation(), o = 0, t.on_drag_change?.(!1), !e.dataTransfer?.files) return;
				let n = Array.from(e.dataTransfer.files);
				n.length > 0 && t.on_files?.(n);
			}
			function u(n) {
				let r = n.target, i = t.ignore_click_selector;
				t.disable_click || i && r instanceof Element && r.closest(i) !== null || (e.value = "", e.click());
			}
			function d() {
				if (e.files) {
					let n = Array.from(e.files);
					n.length > 0 && t.on_files?.(n);
				}
			}
			return n.addEventListener("drag", a), n.addEventListener("dragstart", a), n.addEventListener("dragend", a), n.addEventListener("dragover", a), n.addEventListener("dragenter", s), n.addEventListener("dragleave", c), n.addEventListener("drop", l), n.addEventListener("click", u), e.addEventListener("change", d), {
				update(n) {
					t = n, e.remove(), i(), e.addEventListener("change", d);
				},
				destroy() {
					n.removeEventListener("drag", a), n.removeEventListener("dragstart", a), n.removeEventListener("dragend", a), n.removeEventListener("dragover", a), n.removeEventListener("dragenter", s), n.removeEventListener("dragleave", c), n.removeEventListener("drop", l), n.removeEventListener("click", u), e.removeEventListener("change", d), e.remove();
				}
			};
		},
		open_file_upload() {
			e && (e.value = "", e.click());
		}
	};
}
var yn = 5;
function bn(e, t) {
	let n = e.slice(0, yn).map((e) => e.webkitRelativePath || e.name).join(", ");
	e.length > yn && (n += ` and ${e.length - yn} more`);
	let r = Array.isArray(t) ? t.join(", ") : t;
	return `Invalid file type${e.length > 1 ? "s" : ""}: ${n}. Only ${r} allowed.`;
}
// frontend/node_modules/@gradio/upload/dist/src/Upload.svelte
function xn(e, n) {
	P(n, !0);
	var r = this && this.__awaiter || function(e, t, n, r) {
		function i(e) {
			return e instanceof n ? e : new n(function(t) {
				t(e);
			});
		}
		return new (n ||= Promise)(function(n, a) {
			function o(e) {
				try {
					c(r.next(e));
				} catch (e) {
					a(e);
				}
			}
			function s(e) {
				try {
					c(r.throw(e));
				} catch (e) {
					a(e);
				}
			}
			function c(e) {
				e.done ? n(e.value) : i(e.value).then(o, s);
			}
			c((r = r.apply(e, t || [])).next());
		});
	};
	let { drag: i, open_file_upload: o } = vn(), s = z(n, "filetype", 3, null), c = z(n, "dragging", 15, !1), l = z(n, "boundedheight", 3, !0), u = z(n, "center", 3, !0), d = z(n, "flex", 3, !0), f = z(n, "file_count", 3, "single"), p = z(n, "disable_click", 3, !1), m = z(n, "hidden", 3, !1), h = z(n, "format", 3, "file"), g = z(n, "uploading", 15, !1), v = z(n, "show_progress", 3, !0), b = z(n, "max_file_size", 3, null), C = z(n, "icon_upload", 3, !1), T = z(n, "height", 3, void 0), E = z(n, "aria_label", 3, void 0), D = z(n, "tab_index", 3, 0), O = z(n, "container_element", 3, "button"), k = z(n, "upload_promise", 15);
	function j() {
		o();
	}
	let N = "", ee, F = A(null), re = null, ie = (() => {
		if (typeof navigator < "u") {
			let e = navigator.userAgent.toLowerCase();
			return e.indexOf("iphone") > -1 || e.indexOf("ipad") > -1;
		}
		return !1;
	})(), I = [
		"image",
		"video",
		"audio",
		"text",
		"file"
	], oe = (e) => ie && e.startsWith(".") ? (re = !0, e) : ie && e.includes("file/*") ? "*" : e.startsWith(".") || e.endsWith("/*") ? e : I.includes(e) ? e + "/*" : "." + e;
	ve(() => {
		if (s() == null) V(F, null);
		else if (typeof s() == "string") V(F, oe(s()), !0);
		else if (ie && s().includes("file/*")) V(F, "*");
		else {
			let e = s().map(oe);
			V(F, e.join(", "), !0);
		}
	});
	function se() {
		navigator.clipboard.read().then((e) => r(this, void 0, void 0, function* () {
			for (let t = 0; t < e.length; t++) {
				let n = e[t].types.find((e) => e.startsWith("image/"));
				if (n) {
					e[t].getType(n).then((e) => r(this, void 0, void 0, function* () {
						yield le([new File([e], `clipboard.${n.replace("image/", "")}`)]);
					}));
					break;
				}
			}
		}));
	}
	function L() {
		o();
	}
	function ce(e, t) {
		return r(this, void 0, void 0, function* () {
			return N = t || Math.random().toString(36).substring(2, 15), yield x(), g(!0), k(new Promise((t) => r(this, void 0, void 0, function* () {
				try {
					let r = (yield n.upload(e, n.root, N, b() !== null && b() !== void 0 ? b() : Infinity)) || [];
					f() === "single" ? r[0] !== void 0 && (n.onload === null || n.onload === void 0 || n.onload(r[0])) : n.onload === null || n.onload === void 0 || n.onload(r), t(r), g(!1);
				} catch (e) {
					n.onerror === null || n.onerror === void 0 || n.onerror(e.message), g(!1), t([]);
				}
			}))), k();
		});
	}
	function le(e, t) {
		return r(this, void 0, void 0, function* () {
			if (!e.length) return;
			let r = e.map((e) => new File([e], e instanceof File ? e.name : "file", { type: e.type }));
			if (ie && re) {
				let e = [];
				if (r = r.filter((t) => ue(t) ? !0 : (e.push(t), !1)), e.length && (n.onerror === null || n.onerror === void 0 || n.onerror(bn(e, s()))), r.length === 0) return [];
			}
			return ee = yield un(r), yield ce(ee, t);
		});
	}
	function ue(e) {
		return !s() || (Array.isArray(s()) ? s() : [s()]).some((t) => {
			let n = oe(t);
			if (n.startsWith(".")) return e.name.toLowerCase().endsWith(n.toLowerCase());
			if (n === "*") return !0;
			if (n.endsWith("/*")) {
				let [t] = n.split("/");
				return e.type.startsWith(t + "/");
			}
			return e.type === n;
		});
	}
	function R(e) {
		return r(this, void 0, void 0, function* () {
			let t = [], r = e.filter((e) => {
				let n = e.name.toLowerCase(), r = "." + n.split(".").pop();
				return gn(S(F), n, e.type) || (Array.isArray(s()) ? s().includes(r) : r === s()) ? !0 : (t.push(e), !1);
			});
			if (t.length && (n.onerror === null || n.onerror === void 0 || n.onerror(bn(t, s()))), h() != "blob") yield le(r);
			else {
				if (f() === "single") {
					n.onload === null || n.onload === void 0 || n.onload(r[0]);
					return;
				}
				n.onload === null || n.onload === void 0 || n.onload(r);
			}
		});
	}
	function de(e) {
		return r(this, void 0, void 0, function* () {
			if (c(!1), !e.dataTransfer?.files) return;
			let t = Array.from(e.dataTransfer.files).filter(ue);
			if (h() != "blob") yield le(t);
			else {
				if (f() === "single") {
					n.onload === null || n.onload === void 0 || n.onload(t[0]);
					return;
				}
				n.onload === null || n.onload === void 0 || n.onload(t);
			}
		});
	}
	var fe = {
		open_upload: j,
		paste_clipboard: se,
		open_file_upload: L,
		load_files: le,
		load_files_from_drop: de
	}, pe = y(), me = B(pe), he = (e) => {
		var r = y(), i = B(r);
		_(i, O, !1, (e, r) => {
			w(e, () => ({
				class: "upload-container",
				role: O() === "div" ? "none" : void 0,
				tabindex: O() === "button" ? m() ? -1 : D() : void 0,
				onclick: se,
				"aria-label": O() === "button" ? E() || "Paste from clipboard" : void 0,
				style: "",
				[ne]: {
					hidden: m(),
					center: u(),
					boundedheight: l(),
					flex: d(),
					"icon-mode": C()
				},
				[te]: { height: C() ? "" : T() ? typeof T() == "number" ? T() + "px" : T() : "100%" }
			}), void 0, void 0, void 0, "svelte-tgi0k0");
			var i = y(), o = B(i), s = (e) => {
				var r = y(), i = B(r);
				ae(i, () => n.children), t(e, r);
			};
			a(o, (e) => {
				n.children && e(s);
			}), t(r, i);
		}), t(e, r);
	}, ge = (e) => {
		var r = y(), i = B(r), o = (e) => {
			hn(e, {
				get root() {
					return n.root;
				},
				get upload_id() {
					return N;
				},
				get files() {
					return ee;
				},
				get stream_handler() {
					return n.stream_handler;
				}
			});
		};
		a(i, (e) => {
			m() || e(o);
		}), t(e, r);
	}, _e = (e) => {
		var r = y(), o = B(r);
		_(o, O, !1, (e, r) => {
			xe(e, (e, t) => i?.(e, t), () => ({
				on_drag_change: (e) => c(e),
				on_files: (e) => R(e),
				accepted_types: S(F),
				mode: f(),
				disable_click: p()
			})), w(e, () => ({
				class: "upload-container",
				role: O() === "div" ? "none" : void 0,
				tabindex: O() === "button" ? m() ? -1 : D() : void 0,
				"aria-label": O() === "button" ? E() || "Click to upload or drop files" : void 0,
				"aria-dropeffect": O() === "button" ? "copy" : void 0,
				style: "",
				[ne]: {
					hidden: m(),
					center: u(),
					boundedheight: l(),
					flex: d(),
					disable_click: p(),
					"icon-mode": C()
				},
				[te]: { height: C() ? "" : T() ? typeof T() == "number" ? T() + "px" : T() : "100%" }
			}), void 0, void 0, void 0, "svelte-tgi0k0");
			var o = y(), s = B(o), h = (e) => {
				var r = y(), i = B(r);
				ae(i, () => n.children), t(e, r);
			};
			a(s, (e) => {
				n.children && e(h);
			}), t(r, o);
		}), t(e, r);
	};
	return a(me, (e) => {
		s() === "clipboard" ? e(he) : g() && v() ? e(ge, 1) : e(_e, -1);
	}), t(e, pe), M(fe);
}
// frontend/node_modules/@gradio/upload/dist/src/ModifyUpload.svelte
var Sn = s("<!> <!> <!> <!> <!>", 1);
function Cn(e, n) {
	P(n, !0);
	let r = z(n, "editable", 3, !1), i = z(n, "undoable", 3, !1), o = z(n, "download", 3, null);
	cn(e, {
		children: (e, s) => {
			var c = Sn(), l = B(c), u = (e) => {
				{
					let t = L(() => n.i18n("common.edit"));
					Fe(e, {
						get Icon() {
							return Qe;
						},
						get label() {
							return S(t);
						},
						onclick: () => n.onedit?.()
					});
				}
			};
			a(l, (e) => {
				r() && e(u);
			});
			var d = D(l, 2), f = (e) => {
				{
					let t = L(() => n.i18n("common.undo"));
					Fe(e, {
						get Icon() {
							return gt;
						},
						get label() {
							return S(t);
						},
						onclick: () => n.onundo?.()
					});
				}
			};
			a(d, (e) => {
				i() && e(f);
			});
			var p = D(d, 2), m = (e) => {
				Me(e, {
					get href() {
						return o();
					},
					download: !0,
					children: (e, t) => {
						{
							let t = L(() => n.i18n("common.download"));
							Fe(e, {
								get Icon() {
									return Ke;
								},
								get label() {
									return S(t);
								}
							});
						}
					},
					$$slots: { default: !0 }
				});
			};
			a(p, (e) => {
				o() && e(m);
			});
			var h = D(p, 2), g = (e) => {
				var r = y(), i = B(r);
				ae(i, () => n.children), t(e, r);
			};
			a(h, (e) => {
				n.children && e(g);
			});
			var _ = D(h, 2);
			{
				let e = L(() => n.i18n("common.clear"));
				Fe(_, {
					get Icon() {
						return He;
					},
					get label() {
						return S(e);
					},
					onclick: (e) => {
						n.onclear?.(), e.stopPropagation();
					}
				});
			}
			t(e, c);
		},
		$$slots: { default: !0 }
	}), M();
}
// frontend/node_modules/@gradio/image/dist/shared/Image.svelte
var wn = /* @__PURE__ */ new Set([
	"$$slots",
	"$$events",
	"$$legacy"
]), Tn = s("<img/>");
function En(e, n) {
	P(n, !0);
	var r = this && this.__rest || function(e, t) {
		var n = {};
		for (var r in e) Object.prototype.hasOwnProperty.call(e, r) && t.indexOf(r) < 0 && (n[r] = e[r]);
		if (e != null && typeof Object.getOwnPropertySymbols == "function") for (var i = 0, r = Object.getOwnPropertySymbols(e); i < r.length; i++) t.indexOf(r[i]) < 0 && Object.prototype.propertyIsEnumerable.call(e, r[i]) && (n[r[i]] = e[r[i]]);
		return n;
	};
	let i = ie(n, wn), { src: a = "", restProps: o = {}, data_testid: s, class_names: l = [], onload: u } = i, d = r(i, [
		"src",
		"restProps",
		"data_testid",
		"class_names",
		"onload"
	]), f = (e) => {
		var { class: t } = e;
		return r(e, ["class"]);
	}, p = L(() => f(o)), m = L(() => f(d)), h = L(() => [
		l.join(" "),
		o.class,
		d.class
	].filter(Boolean).join(" "));
	var g = Tn();
	w(g, () => ({
		src: a,
		class: S(h),
		"data-testid": s,
		...S(p),
		...S(m),
		onload: u
	}), void 0, void 0, void 0, "svelte-5xcf1t"), c(g), t(e, g), M();
}
// frontend/node_modules/@gradio/image/dist/shared/ImagePreview.svelte
o(["click"]);
// frontend/node_modules/@ffmpeg/ffmpeg/dist/esm/const.js
var Dn;
(function(e) {
	e.LOAD = "LOAD", e.EXEC = "EXEC", e.FFPROBE = "FFPROBE", e.WRITE_FILE = "WRITE_FILE", e.READ_FILE = "READ_FILE", e.DELETE_FILE = "DELETE_FILE", e.RENAME = "RENAME", e.CREATE_DIR = "CREATE_DIR", e.LIST_DIR = "LIST_DIR", e.DELETE_DIR = "DELETE_DIR", e.ERROR = "ERROR", e.DOWNLOAD = "DOWNLOAD", e.PROGRESS = "PROGRESS", e.LOG = "LOG", e.MOUNT = "MOUNT", e.UNMOUNT = "UNMOUNT";
})(Dn ||= {});
// frontend/node_modules/@ffmpeg/ffmpeg/dist/esm/types.js
var On;
(function(e) {
	e.MEMFS = "MEMFS", e.NODEFS = "NODEFS", e.NODERAWFS = "NODERAWFS", e.IDBFS = "IDBFS", e.WORKERFS = "WORKERFS", e.PROXYFS = "PROXYFS";
})(On ||= {});
// frontend/node_modules/@gradio/video/dist/shared/utils.js
function kn(e, { autoplay: t }) {
	function n() {
		t && Nt(e);
	}
	return e.addEventListener("loadeddata", n), { destroy() {
		e.removeEventListener("loadeddata", n);
	} };
}
// frontend/node_modules/hls.js/dist/hls.mjs
var W = Number.isFinite || function(e) {
	return typeof e == "number" && isFinite(e);
}, An = Number.isSafeInteger || function(e) {
	return typeof e == "number" && Math.abs(e) <= jn;
}, jn = 2 ** 53 - 1 || 9007199254740991, G = /*#__PURE__*/ function(e) {
	return e.NETWORK_ERROR = "networkError", e.MEDIA_ERROR = "mediaError", e.KEY_SYSTEM_ERROR = "keySystemError", e.MUX_ERROR = "muxError", e.OTHER_ERROR = "otherError", e;
}({}), K = /*#__PURE__*/ function(e) {
	return e.KEY_SYSTEM_NO_KEYS = "keySystemNoKeys", e.KEY_SYSTEM_NO_ACCESS = "keySystemNoAccess", e.KEY_SYSTEM_NO_SESSION = "keySystemNoSession", e.KEY_SYSTEM_NO_CONFIGURED_LICENSE = "keySystemNoConfiguredLicense", e.KEY_SYSTEM_LICENSE_REQUEST_FAILED = "keySystemLicenseRequestFailed", e.KEY_SYSTEM_SERVER_CERTIFICATE_REQUEST_FAILED = "keySystemServerCertificateRequestFailed", e.KEY_SYSTEM_SERVER_CERTIFICATE_UPDATE_FAILED = "keySystemServerCertificateUpdateFailed", e.KEY_SYSTEM_SESSION_UPDATE_FAILED = "keySystemSessionUpdateFailed", e.KEY_SYSTEM_STATUS_OUTPUT_RESTRICTED = "keySystemStatusOutputRestricted", e.KEY_SYSTEM_STATUS_INTERNAL_ERROR = "keySystemStatusInternalError", e.KEY_SYSTEM_DESTROY_MEDIA_KEYS_ERROR = "keySystemDestroyMediaKeysError", e.KEY_SYSTEM_DESTROY_CLOSE_SESSION_ERROR = "keySystemDestroyCloseSessionError", e.KEY_SYSTEM_DESTROY_REMOVE_SESSION_ERROR = "keySystemDestroyRemoveSessionError", e.MANIFEST_LOAD_ERROR = "manifestLoadError", e.MANIFEST_LOAD_TIMEOUT = "manifestLoadTimeOut", e.MANIFEST_PARSING_ERROR = "manifestParsingError", e.MANIFEST_INCOMPATIBLE_CODECS_ERROR = "manifestIncompatibleCodecsError", e.LEVEL_EMPTY_ERROR = "levelEmptyError", e.LEVEL_LOAD_ERROR = "levelLoadError", e.LEVEL_LOAD_TIMEOUT = "levelLoadTimeOut", e.LEVEL_PARSING_ERROR = "levelParsingError", e.LEVEL_SWITCH_ERROR = "levelSwitchError", e.AUDIO_TRACK_LOAD_ERROR = "audioTrackLoadError", e.AUDIO_TRACK_LOAD_TIMEOUT = "audioTrackLoadTimeOut", e.SUBTITLE_LOAD_ERROR = "subtitleTrackLoadError", e.SUBTITLE_TRACK_LOAD_TIMEOUT = "subtitleTrackLoadTimeOut", e.FRAG_LOAD_ERROR = "fragLoadError", e.FRAG_LOAD_TIMEOUT = "fragLoadTimeOut", e.FRAG_DECRYPT_ERROR = "fragDecryptError", e.FRAG_PARSING_ERROR = "fragParsingError", e.FRAG_GAP = "fragGap", e.REMUX_ALLOC_ERROR = "remuxAllocError", e.KEY_LOAD_ERROR = "keyLoadError", e.KEY_LOAD_TIMEOUT = "keyLoadTimeOut", e.BUFFER_ADD_CODEC_ERROR = "bufferAddCodecError", e.BUFFER_INCOMPATIBLE_CODECS_ERROR = "bufferIncompatibleCodecsError", e.BUFFER_APPEND_ERROR = "bufferAppendError", e.BUFFER_APPENDING_ERROR = "bufferAppendingError", e.BUFFER_STALLED_ERROR = "bufferStalledError", e.BUFFER_FULL_ERROR = "bufferFullError", e.BUFFER_SEEK_OVER_HOLE = "bufferSeekOverHole", e.BUFFER_NUDGE_ON_STALL = "bufferNudgeOnStall", e.ASSET_LIST_LOAD_ERROR = "assetListLoadError", e.ASSET_LIST_LOAD_TIMEOUT = "assetListLoadTimeout", e.ASSET_LIST_PARSING_ERROR = "assetListParsingError", e.INTERSTITIAL_ASSET_ITEM_ERROR = "interstitialAssetItemError", e.INTERNAL_EXCEPTION = "internalException", e.INTERNAL_ABORTED = "aborted", e.ATTACH_MEDIA_ERROR = "attachMediaError", e.UNKNOWN = "unknown", e;
}({}), q = /*#__PURE__*/ function(e) {
	return e.MEDIA_ATTACHING = "hlsMediaAttaching", e.MEDIA_ATTACHED = "hlsMediaAttached", e.MEDIA_DETACHING = "hlsMediaDetaching", e.MEDIA_DETACHED = "hlsMediaDetached", e.MEDIA_ENDED = "hlsMediaEnded", e.STALL_RESOLVED = "hlsStallResolved", e.BUFFER_RESET = "hlsBufferReset", e.BUFFER_CODECS = "hlsBufferCodecs", e.BUFFER_CREATED = "hlsBufferCreated", e.BUFFER_APPENDING = "hlsBufferAppending", e.BUFFER_APPENDED = "hlsBufferAppended", e.BUFFER_EOS = "hlsBufferEos", e.BUFFERED_TO_END = "hlsBufferedToEnd", e.BUFFER_FLUSHING = "hlsBufferFlushing", e.BUFFER_FLUSHED = "hlsBufferFlushed", e.MANIFEST_LOADING = "hlsManifestLoading", e.MANIFEST_LOADED = "hlsManifestLoaded", e.MANIFEST_PARSED = "hlsManifestParsed", e.LEVEL_SWITCHING = "hlsLevelSwitching", e.LEVEL_SWITCHED = "hlsLevelSwitched", e.LEVEL_LOADING = "hlsLevelLoading", e.LEVEL_LOADED = "hlsLevelLoaded", e.LEVEL_UPDATED = "hlsLevelUpdated", e.LEVEL_PTS_UPDATED = "hlsLevelPtsUpdated", e.LEVELS_UPDATED = "hlsLevelsUpdated", e.AUDIO_TRACKS_UPDATED = "hlsAudioTracksUpdated", e.AUDIO_TRACK_SWITCHING = "hlsAudioTrackSwitching", e.AUDIO_TRACK_SWITCHED = "hlsAudioTrackSwitched", e.AUDIO_TRACK_LOADING = "hlsAudioTrackLoading", e.AUDIO_TRACK_LOADED = "hlsAudioTrackLoaded", e.AUDIO_TRACK_UPDATED = "hlsAudioTrackUpdated", e.SUBTITLE_TRACKS_UPDATED = "hlsSubtitleTracksUpdated", e.SUBTITLE_TRACKS_CLEARED = "hlsSubtitleTracksCleared", e.SUBTITLE_TRACK_SWITCH = "hlsSubtitleTrackSwitch", e.SUBTITLE_TRACK_LOADING = "hlsSubtitleTrackLoading", e.SUBTITLE_TRACK_LOADED = "hlsSubtitleTrackLoaded", e.SUBTITLE_TRACK_UPDATED = "hlsSubtitleTrackUpdated", e.SUBTITLE_FRAG_PROCESSED = "hlsSubtitleFragProcessed", e.CUES_PARSED = "hlsCuesParsed", e.NON_NATIVE_TEXT_TRACKS_FOUND = "hlsNonNativeTextTracksFound", e.INIT_PTS_FOUND = "hlsInitPtsFound", e.FRAG_LOADING = "hlsFragLoading", e.FRAG_LOAD_EMERGENCY_ABORTED = "hlsFragLoadEmergencyAborted", e.FRAG_LOADED = "hlsFragLoaded", e.FRAG_DECRYPTED = "hlsFragDecrypted", e.FRAG_PARSING_INIT_SEGMENT = "hlsFragParsingInitSegment", e.FRAG_PARSING_USERDATA = "hlsFragParsingUserdata", e.FRAG_PARSING_METADATA = "hlsFragParsingMetadata", e.FRAG_PARSED = "hlsFragParsed", e.FRAG_BUFFERED = "hlsFragBuffered", e.FRAG_CHANGED = "hlsFragChanged", e.FPS_DROP = "hlsFpsDrop", e.FPS_DROP_LEVEL_CAPPING = "hlsFpsDropLevelCapping", e.MAX_AUTO_LEVEL_UPDATED = "hlsMaxAutoLevelUpdated", e.ERROR = "hlsError", e.DESTROYING = "hlsDestroying", e.KEY_LOADING = "hlsKeyLoading", e.KEY_LOADED = "hlsKeyLoaded", e.LIVE_BACK_BUFFER_REACHED = "hlsLiveBackBufferReached", e.BACK_BUFFER_REACHED = "hlsBackBufferReached", e.STEERING_MANIFEST_LOADED = "hlsSteeringManifestLoaded", e.ASSET_LIST_LOADING = "hlsAssetListLoading", e.ASSET_LIST_LOADED = "hlsAssetListLoaded", e.INTERSTITIALS_UPDATED = "hlsInterstitialsUpdated", e.INTERSTITIALS_BUFFERED_TO_BOUNDARY = "hlsInterstitialsBufferedToBoundary", e.INTERSTITIAL_ASSET_PLAYER_CREATED = "hlsInterstitialAssetPlayerCreated", e.INTERSTITIAL_STARTED = "hlsInterstitialStarted", e.INTERSTITIAL_ASSET_STARTED = "hlsInterstitialAssetStarted", e.INTERSTITIAL_ASSET_ENDED = "hlsInterstitialAssetEnded", e.INTERSTITIAL_ASSET_ERROR = "hlsInterstitialAssetError", e.INTERSTITIAL_ENDED = "hlsInterstitialEnded", e.INTERSTITIALS_PRIMARY_RESUMED = "hlsInterstitialsPrimaryResumed", e.PLAYOUT_LIMIT_REACHED = "hlsPlayoutLimitReached", e.EVENT_CUE_ENTER = "hlsEventCueEnter", e;
}({}), J = {
	MANIFEST: "manifest",
	LEVEL: "level",
	AUDIO_TRACK: "audioTrack",
	SUBTITLE_TRACK: "subtitleTrack"
}, Y = {
	MAIN: "main",
	AUDIO: "audio",
	SUBTITLE: "subtitle"
}, Mn = class {
	constructor(e, t = 0, n = 0) {
		this.halfLife = void 0, this.alpha_ = void 0, this.estimate_ = void 0, this.totalWeight_ = void 0, this.halfLife = e, this.alpha_ = e ? Math.exp(Math.log(.5) / e) : 0, this.estimate_ = t, this.totalWeight_ = n;
	}
	sample(e, t) {
		let n = this.alpha_ ** +e;
		this.estimate_ = t * (1 - n) + n * this.estimate_, this.totalWeight_ += e;
	}
	getTotalWeight() {
		return this.totalWeight_;
	}
	getEstimate() {
		if (this.alpha_) {
			let e = 1 - this.alpha_ ** +this.totalWeight_;
			if (e) return this.estimate_ / e;
		}
		return this.estimate_;
	}
}, Nn = class {
	constructor(e, t, n, r = 100) {
		this.defaultEstimate_ = void 0, this.minWeight_ = void 0, this.minDelayMs_ = void 0, this.slow_ = void 0, this.fast_ = void 0, this.defaultTTFB_ = void 0, this.ttfb_ = void 0, this.defaultEstimate_ = n, this.minWeight_ = .001, this.minDelayMs_ = 50, this.slow_ = new Mn(e), this.fast_ = new Mn(t), this.defaultTTFB_ = r, this.ttfb_ = new Mn(e);
	}
	update(e, t) {
		let { slow_: n, fast_: r, ttfb_: i } = this;
		n.halfLife !== e && (this.slow_ = new Mn(e, n.getEstimate(), n.getTotalWeight())), r.halfLife !== t && (this.fast_ = new Mn(t, r.getEstimate(), r.getTotalWeight())), i.halfLife !== e && (this.ttfb_ = new Mn(e, i.getEstimate(), i.getTotalWeight()));
	}
	sample(e, t) {
		e = Math.max(e, this.minDelayMs_);
		let n = 8 * t, r = e / 1e3, i = n / r;
		this.fast_.sample(r, i), this.slow_.sample(r, i);
	}
	sampleTTFB(e) {
		let t = e / 1e3, n = Math.sqrt(2) * Math.exp(-(t ** 2) / 2);
		this.ttfb_.sample(n, Math.max(e, 5));
	}
	canEstimate() {
		return this.fast_.getTotalWeight() >= this.minWeight_;
	}
	getEstimate() {
		return this.canEstimate() ? Math.min(this.fast_.getEstimate(), this.slow_.getEstimate()) : this.defaultEstimate_;
	}
	getEstimateTTFB() {
		return this.ttfb_.getTotalWeight() >= this.minWeight_ ? this.ttfb_.getEstimate() : this.defaultTTFB_;
	}
	get defaultEstimate() {
		return this.defaultEstimate_;
	}
	destroy() {}
};
function Pn(e, t, n) {
	return (t = zn(t)) in e ? Object.defineProperty(e, t, {
		value: n,
		enumerable: !0,
		configurable: !0,
		writable: !0
	}) : e[t] = n, e;
}
function Fn() {
	return Fn = Object.assign ? Object.assign.bind() : function(e) {
		for (var t = 1; t < arguments.length; t++) {
			var n = arguments[t];
			for (var r in n) ({}).hasOwnProperty.call(n, r) && (e[r] = n[r]);
		}
		return e;
	}, Fn.apply(null, arguments);
}
function In(e, t) {
	var n = Object.keys(e);
	if (Object.getOwnPropertySymbols) {
		var r = Object.getOwnPropertySymbols(e);
		t && (r = r.filter(function(t) {
			return Object.getOwnPropertyDescriptor(e, t).enumerable;
		})), n.push.apply(n, r);
	}
	return n;
}
function Ln(e) {
	for (var t = 1; t < arguments.length; t++) {
		var n = arguments[t] == null ? {} : arguments[t];
		t % 2 ? In(Object(n), !0).forEach(function(t) {
			Pn(e, t, n[t]);
		}) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(n)) : In(Object(n)).forEach(function(t) {
			Object.defineProperty(e, t, Object.getOwnPropertyDescriptor(n, t));
		});
	}
	return e;
}
function Rn(e, t) {
	if (typeof e != "object" || !e) return e;
	var n = e[Symbol.toPrimitive];
	if (n !== void 0) {
		var r = n.call(e, t);
		if (typeof r != "object") return r;
		throw TypeError("@@toPrimitive must return a primitive value.");
	}
	return (t === "string" ? String : Number)(e);
}
function zn(e) {
	var t = Rn(e, "string");
	return typeof t == "symbol" ? t : t + "";
}
var Bn = class {
	constructor(e, t) {
		this.trace = void 0, this.debug = void 0, this.log = void 0, this.warn = void 0, this.info = void 0, this.error = void 0;
		let n = `[${e}]:`;
		this.trace = Vn, this.debug = t.debug.bind(null, n), this.log = t.log.bind(null, n), this.warn = t.warn.bind(null, n), this.info = t.info.bind(null, n), this.error = t.error.bind(null, n);
	}
}, Vn = function() {}, Hn = {
	trace: Vn,
	debug: Vn,
	log: Vn,
	warn: Vn,
	info: Vn,
	error: Vn
};
function Un() {
	return Fn({}, Hn);
}
function Wn(e, t) {
	let n = self.console[e];
	return n ? n.bind(self.console, `${t ? "[" + t + "] " : ""}[${e}] >`) : Vn;
}
function Gn(e, t, n) {
	return t[e] ? t[e].bind(t) : Wn(e, n);
}
var Kn = Un();
function qn(e, t, n) {
	let r = Un();
	if (typeof console == "object" && e === !0 || typeof e == "object") {
		let i = [
			"debug",
			"log",
			"info",
			"warn",
			"error"
		];
		i.forEach((t) => {
			r[t] = Gn(t, e, n);
		});
		try {
			r.log(`Debug logs enabled for "${t}" in hls.js version 1.6.15`);
		} catch {
			return Un();
		}
		i.forEach((t) => {
			Kn[t] = Gn(t, e);
		});
	} else Fn(Kn, r);
	return r;
}
var Jn = Kn;
function Yn(e = !0) {
	if (typeof self < "u") return (e || !self.MediaSource) && self.ManagedMediaSource || self.MediaSource || self.WebKitMediaSource;
}
function Xn(e) {
	return typeof self < "u" && e === self.ManagedMediaSource;
}
function Zn(e, t) {
	let n = Object.keys(e), r = Object.keys(t), i = n.length, a = r.length;
	return !i || !a || i === a && !n.some((e) => r.indexOf(e) === -1);
}
function Qn(e, t = !1) {
	if (typeof TextDecoder < "u") {
		let n = new TextDecoder("utf-8").decode(e);
		if (t) {
			let e = n.indexOf("\0");
			return e === -1 ? n : n.substring(0, e);
		}
		return n.replace(/\0/g, "");
	}
	let n = e.length, r, i, a, o = "", s = 0;
	for (; s < n;) {
		if (r = e[s++], r === 0 && t) return o;
		if (r !== 0 && r !== 3) switch (r >> 4) {
			case 0:
			case 1:
			case 2:
			case 3:
			case 4:
			case 5:
			case 6:
			case 7:
				o += String.fromCharCode(r);
				break;
			case 12:
			case 13:
				i = e[s++], o += String.fromCharCode((r & 31) << 6 | i & 63);
				break;
			case 14: i = e[s++], a = e[s++], o += String.fromCharCode((r & 15) << 12 | (i & 63) << 6 | a & 63);
		}
	}
	return o;
}
function $n(e) {
	let t = "";
	for (let n = 0; n < e.length; n++) {
		let r = e[n].toString(16);
		r.length < 2 && (r = "0" + r), t += r;
	}
	return t;
}
function er(e) {
	return Uint8Array.from(e.replace(/^0x/, "").replace(/([\da-fA-F]{2}) ?/g, "0x$1 ").replace(/ +$/, "").split(" ")).buffer;
}
function tr(e) {
	return e && e.__esModule && Object.prototype.hasOwnProperty.call(e, "default") ? e.default : e;
}
var nr = { exports: {} }, rr;
function ir() {
	return rr || (rr = 1, (function(e, t) {
		(function(t) {
			var n = /^(?=((?:[a-zA-Z0-9+\-.]+:)?))\1(?=((?:\/\/[^\/?#]*)?))\2(?=((?:(?:[^?#\/]*\/)*[^;?#\/]*)?))\3((?:;[^?#]*)?)(\?[^#]*)?(#[^]*)?$/, r = /^(?=([^\/?#]*))\1([^]*)$/, i = /(?:\/|^)\.(?=\/)/g, a = /(?:\/|^)\.\.\/(?!\.\.\/)[^\/]*(?=\/)/g, o = {
				buildAbsoluteURL: function(e, t, n) {
					if (n ||= {}, e = e.trim(), t = t.trim(), !t) {
						if (!n.alwaysNormalize) return e;
						var i = o.parseURL(e);
						if (!i) throw Error("Error trying to parse base URL.");
						return i.path = o.normalizePath(i.path), o.buildURLFromParts(i);
					}
					var a = o.parseURL(t);
					if (!a) throw Error("Error trying to parse relative URL.");
					if (a.scheme) return n.alwaysNormalize ? (a.path = o.normalizePath(a.path), o.buildURLFromParts(a)) : t;
					var s = o.parseURL(e);
					if (!s) throw Error("Error trying to parse base URL.");
					if (!s.netLoc && s.path && s.path[0] !== "/") {
						var c = r.exec(s.path);
						s.netLoc = c[1], s.path = c[2];
					}
					s.netLoc && !s.path && (s.path = "/");
					var l = {
						scheme: s.scheme,
						netLoc: a.netLoc,
						path: null,
						params: a.params,
						query: a.query,
						fragment: a.fragment
					};
					if (!a.netLoc && (l.netLoc = s.netLoc, a.path[0] !== "/")) {
						if (!a.path) l.path = s.path, a.params || (l.params = s.params, a.query || (l.query = s.query));
						else {
							var u = s.path, d = u.substring(0, u.lastIndexOf("/") + 1) + a.path;
							l.path = o.normalizePath(d);
						}
					}
					return l.path === null && (l.path = n.alwaysNormalize ? o.normalizePath(a.path) : a.path), o.buildURLFromParts(l);
				},
				parseURL: function(e) {
					var t = n.exec(e);
					return t ? {
						scheme: t[1] || "",
						netLoc: t[2] || "",
						path: t[3] || "",
						params: t[4] || "",
						query: t[5] || "",
						fragment: t[6] || ""
					} : null;
				},
				normalizePath: function(e) {
					for (e = e.split("").reverse().join("").replace(i, ""); e.length !== (e = e.replace(a, "")).length;);
					return e.split("").reverse().join("");
				},
				buildURLFromParts: function(e) {
					return e.scheme + e.netLoc + e.path + e.params + e.query + e.fragment;
				}
			};
			e.exports = o;
		})();
	})(nr)), nr.exports;
}
var ar = ir(), or = class {
	constructor() {
		this.aborted = !1, this.loaded = 0, this.retry = 0, this.total = 0, this.chunkCount = 0, this.bwEstimate = 0, this.loading = {
			start: 0,
			first: 0,
			end: 0
		}, this.parsing = {
			start: 0,
			end: 0
		}, this.buffering = {
			start: 0,
			first: 0,
			end: 0
		};
	}
}, sr = {
	AUDIO: "audio",
	VIDEO: "video",
	AUDIOVIDEO: "audiovideo"
}, cr = class {
	constructor(e) {
		this._byteRange = null, this._url = null, this._stats = null, this._streams = null, this.base = void 0, this.relurl = void 0, typeof e == "string" && (e = { url: e }), this.base = e, pr(this, "stats");
	}
	setByteRange(e, t) {
		let n = e.split("@", 2), r;
		r = n.length === 1 ? t?.byteRangeEndOffset || 0 : parseInt(n[1]), this._byteRange = [r, parseInt(n[0]) + r];
	}
	get baseurl() {
		return this.base.url;
	}
	get byteRange() {
		return this._byteRange === null ? [] : this._byteRange;
	}
	get byteRangeStartOffset() {
		return this.byteRange[0];
	}
	get byteRangeEndOffset() {
		return this.byteRange[1];
	}
	get elementaryStreams() {
		return this._streams === null && (this._streams = {
			[sr.AUDIO]: null,
			[sr.VIDEO]: null,
			[sr.AUDIOVIDEO]: null
		}), this._streams;
	}
	set elementaryStreams(e) {
		this._streams = e;
	}
	get hasStats() {
		return this._stats !== null;
	}
	get hasStreams() {
		return this._streams !== null;
	}
	get stats() {
		return this._stats === null && (this._stats = new or()), this._stats;
	}
	set stats(e) {
		this._stats = e;
	}
	get url() {
		return !this._url && this.baseurl && this.relurl && (this._url = ar.buildAbsoluteURL(this.baseurl, this.relurl, { alwaysNormalize: !0 })), this._url || "";
	}
	set url(e) {
		this._url = e;
	}
	clearElementaryStreamInfo() {
		let { elementaryStreams: e } = this;
		e[sr.AUDIO] = null, e[sr.VIDEO] = null, e[sr.AUDIOVIDEO] = null;
	}
};
function lr(e) {
	return e.sn !== "initSegment";
}
var ur = class extends cr {
	constructor(e, t) {
		super(t), this._decryptdata = null, this._programDateTime = null, this._ref = null, this._bitrate = void 0, this.rawProgramDateTime = null, this.tagList = [], this.duration = 0, this.sn = 0, this.levelkeys = void 0, this.type = void 0, this.loader = null, this.keyLoader = null, this.level = -1, this.cc = 0, this.startPTS = void 0, this.endPTS = void 0, this.startDTS = void 0, this.endDTS = void 0, this.start = 0, this.playlistOffset = 0, this.deltaPTS = void 0, this.maxStartPTS = void 0, this.minEndPTS = void 0, this.data = void 0, this.bitrateTest = !1, this.title = null, this.initSegment = null, this.endList = void 0, this.gap = void 0, this.urlId = 0, this.type = e;
	}
	get byteLength() {
		if (this.hasStats) {
			let e = this.stats.total;
			if (e) return e;
		}
		if (this.byteRange.length) {
			let e = this.byteRange[0], t = this.byteRange[1];
			if (W(e) && W(t)) return t - e;
		}
		return null;
	}
	get bitrate() {
		return this.byteLength ? this.byteLength * 8 / this.duration : this._bitrate ? this._bitrate : null;
	}
	set bitrate(e) {
		this._bitrate = e;
	}
	get decryptdata() {
		var e;
		let { levelkeys: t } = this;
		if (!t || t.NONE) return null;
		if (t.identity) this._decryptdata ||= t.identity.getDecryptData(this.sn);
		else if (!((e = this._decryptdata) != null && e.keyId)) {
			let e = Object.keys(t);
			if (e.length === 1) {
				let n = this._decryptdata = t[e[0]] || null;
				n && (this._decryptdata = n.getDecryptData(this.sn, t));
			}
		}
		return this._decryptdata;
	}
	get end() {
		return this.start + this.duration;
	}
	get endProgramDateTime() {
		if (this.programDateTime === null) return null;
		let e = W(this.duration) ? this.duration : 0;
		return this.programDateTime + e * 1e3;
	}
	get encrypted() {
		var e;
		if ((e = this._decryptdata) != null && e.encrypted) return !0;
		if (this.levelkeys) {
			var t;
			let e = Object.keys(this.levelkeys), n = e.length;
			if (n > 1 || n === 1 && (t = this.levelkeys[e[0]]) != null && t.encrypted) return !0;
		}
		return !1;
	}
	get programDateTime() {
		return this._programDateTime === null && this.rawProgramDateTime && (this.programDateTime = Date.parse(this.rawProgramDateTime)), this._programDateTime;
	}
	set programDateTime(e) {
		this._programDateTime = W(e) ? e : this.rawProgramDateTime = null;
	}
	get ref() {
		return lr(this) ? (this._ref ||= {
			base: this.base,
			start: this.start,
			duration: this.duration,
			sn: this.sn,
			programDateTime: this.programDateTime
		}, this._ref) : null;
	}
	addStart(e) {
		this.setStart(this.start + e);
	}
	setStart(e) {
		this.start = e, this._ref && (this._ref.start = e);
	}
	setDuration(e) {
		this.duration = e, this._ref && (this._ref.duration = e);
	}
	setKeyFormat(e) {
		let t = this.levelkeys;
		if (t) {
			var n;
			let r = t[e];
			r && !((n = this._decryptdata) != null && n.keyId) && (this._decryptdata = r.getDecryptData(this.sn, t));
		}
	}
	abortRequests() {
		var e, t;
		(e = this.loader) == null || e.abort(), (t = this.keyLoader) == null || t.abort();
	}
	setElementaryStreamInfo(e, t, n, r, i, a = !1) {
		let { elementaryStreams: o } = this, s = o[e];
		s ? (s.startPTS = Math.min(s.startPTS, t), s.endPTS = Math.max(s.endPTS, n), s.startDTS = Math.min(s.startDTS, r), s.endDTS = Math.max(s.endDTS, i)) : o[e] = {
			startPTS: t,
			endPTS: n,
			startDTS: r,
			endDTS: i,
			partial: a
		};
	}
}, dr = class extends cr {
	constructor(e, t, n, r, i) {
		super(n), this.fragOffset = 0, this.duration = 0, this.gap = !1, this.independent = !1, this.relurl = void 0, this.fragment = void 0, this.index = void 0, this.duration = e.decimalFloatingPoint("DURATION"), this.gap = e.bool("GAP"), this.independent = e.bool("INDEPENDENT"), this.relurl = e.enumeratedString("URI"), this.fragment = t, this.index = r;
		let a = e.enumeratedString("BYTERANGE");
		a && this.setByteRange(a, i), i && (this.fragOffset = i.fragOffset + i.duration);
	}
	get start() {
		return this.fragment.start + this.fragOffset;
	}
	get end() {
		return this.start + this.duration;
	}
	get loaded() {
		let { elementaryStreams: e } = this;
		return !!(e.audio || e.video || e.audiovideo);
	}
};
function fr(e, t) {
	let n = Object.getPrototypeOf(e);
	if (n) return Object.getOwnPropertyDescriptor(n, t) || fr(n, t);
}
function pr(e, t) {
	let n = fr(e, t);
	n && (n.enumerable = !0, Object.defineProperty(e, t, n));
}
var mr = 2 ** 32 - 1, hr = [].push, gr = {
	video: 1,
	audio: 2,
	id3: 3,
	text: 4
};
function _r(e) {
	return String.fromCharCode.apply(null, e);
}
function vr(e, t) {
	let n = e[t] << 8 | e[t + 1];
	return n < 0 ? 65536 + n : n;
}
function X(e, t) {
	let n = br(e, t);
	return n < 0 ? 4294967296 + n : n;
}
function yr(e, t) {
	let n = X(e, t);
	return n *= 2 ** 32, n += X(e, t + 4), n;
}
function br(e, t) {
	return e[t] << 24 | e[t + 1] << 16 | e[t + 2] << 8 | e[t + 3];
}
function xr(e) {
	let t = e.byteLength;
	for (let n = 0; n < t;) {
		let r = X(e, n);
		if (r > 8 && e[n + 4] === 109 && e[n + 5] === 111 && e[n + 6] === 111 && e[n + 7] === 102) return !0;
		n = r > 1 ? n + r : t;
	}
	return !1;
}
function Z(e, t) {
	let n = [];
	if (!t.length) return n;
	let r = e.byteLength;
	for (let i = 0; i < r;) {
		let a = X(e, i), o = _r(e.subarray(i + 4, i + 8)), s = a > 1 ? i + a : r;
		if (o === t[0]) {
			if (t.length === 1) n.push(e.subarray(i + 8, s));
			else {
				let r = Z(e.subarray(i + 8, s), t.slice(1));
				r.length && hr.apply(n, r);
			}
		}
		i = s;
	}
	return n;
}
function Sr(e) {
	let t = [], n = e[0], r = 8, i = X(e, r);
	r += 4;
	let a = 0, o = 0;
	n === 0 ? (a = X(e, r), o = X(e, r + 4), r += 8) : (a = yr(e, r), o = yr(e, r + 8), r += 16), r += 2;
	let s = e.length + o, c = vr(e, r);
	r += 2;
	for (let n = 0; n < c; n++) {
		let n = r, a = X(e, n);
		n += 4;
		let o = a & 2147483647;
		if ((a & 2147483648) >>> 31 == 1) return Jn.warn("SIDX has hierarchical references (not supported)"), null;
		let c = X(e, n);
		n += 4, t.push({
			referenceSize: o,
			subsegmentDuration: c,
			info: {
				duration: c / i,
				start: s,
				end: s + o - 1
			}
		}), s += o, n += 4, r = n;
	}
	return {
		earliestPresentationTime: a,
		timescale: i,
		version: n,
		referencesCount: c,
		references: t
	};
}
function Cr(e) {
	let t = [], n = Z(e, ["moov", "trak"]);
	for (let e = 0; e < n.length; e++) {
		let r = n[e], i = Z(r, ["tkhd"])[0];
		if (i) {
			let e = i[0], n = X(i, e === 0 ? 12 : 20), a = Z(r, ["mdia", "mdhd"])[0];
			if (a) {
				e = a[0];
				let i = X(a, e === 0 ? 12 : 20), o = Z(r, ["mdia", "hdlr"])[0];
				if (o) {
					let e = _r(o.subarray(8, 12)), a = {
						soun: sr.AUDIO,
						vide: sr.VIDEO
					}[e], s = Z(r, [
						"mdia",
						"minf",
						"stbl",
						"stsd"
					])[0], c = wr(s);
					a ? (t[n] = {
						timescale: i,
						type: a,
						stsd: c
					}, t[a] = Ln({
						timescale: i,
						id: n
					}, c)) : t[n] = {
						timescale: i,
						type: e,
						stsd: c
					};
				}
			}
		}
	}
	return Z(e, [
		"moov",
		"mvex",
		"trex"
	]).forEach((e) => {
		let n = X(e, 4), r = t[n];
		r && (r.default = {
			duration: X(e, 12),
			flags: X(e, 20)
		});
	}), t;
}
function wr(e) {
	let t = e.subarray(8), n = t.subarray(86), r = _r(t.subarray(4, 8)), i = r, a, o = r === "enca" || r === "encv";
	o && Z(Z(t, [r])[0].subarray(r === "enca" ? 28 : 78), ["sinf"]).forEach((e) => {
		let t = Z(e, ["schm"])[0];
		if (t) {
			let n = _r(t.subarray(4, 8));
			if (n === "cbcs" || n === "cenc") {
				let t = Z(e, ["frma"])[0];
				t && (i = _r(t));
			}
		}
	});
	let s = i;
	switch (i) {
		case "avc1":
		case "avc2":
		case "avc3":
		case "avc4": {
			let e = Z(n, ["avcC"])[0];
			e && e.length > 3 && (i += "." + Or(e[1]) + Or(e[2]) + Or(e[3]), a = Tr(s === "avc1" ? "dva1" : "dvav", n));
			break;
		}
		case "mp4a": {
			let e = Z(t, [r])[0], n = Z(e.subarray(28), ["esds"])[0];
			if (n && n.length > 7) {
				let e = 4;
				if (n[e++] !== 3) break;
				e = Dr(n, e), e += 2;
				let t = n[e++];
				if (t & 128 && (e += 2), t & 64 && (e += n[e++]), n[e++] !== 4) break;
				e = Dr(n, e);
				let r = n[e++];
				if (r === 64) i += "." + Or(r);
				else break;
				if (e += 12, n[e++] !== 5) break;
				e = Dr(n, e);
				let a = n[e++], o = (a & 248) >> 3;
				o === 31 && (o += 1 + ((a & 7) << 3) + ((n[e] & 224) >> 5)), i += "." + o;
			}
			break;
		}
		case "hvc1":
		case "hev1": {
			let e = Z(n, ["hvcC"])[0];
			if (e && e.length > 12) {
				let t = e[1], n = [
					"",
					"A",
					"B",
					"C"
				][t >> 6], r = t & 31, a = X(e, 2), o = (t & 32) >> 5 ? "H" : "L", s = e[12], c = e.subarray(6, 12);
				i += "." + n + r, i += "." + Er(a).toString(16).toUpperCase(), i += "." + o + s;
				let l = "";
				for (let e = c.length; e--;) {
					let t = c[e];
					(t || l) && (l = "." + t.toString(16).toUpperCase() + l);
				}
				i += l;
			}
			a = Tr(s == "hev1" ? "dvhe" : "dvh1", n);
			break;
		}
		case "dvh1":
		case "dvhe":
		case "dvav":
		case "dva1":
		case "dav1":
			i = Tr(i, n) || i;
			break;
		case "vp09": {
			let e = Z(n, ["vpcC"])[0];
			if (e && e.length > 6) {
				let t = e[4], n = e[5], r = e[6] >> 4 & 15;
				i += "." + kr(t) + "." + kr(n) + "." + kr(r);
			}
			break;
		}
		case "av01": {
			let e = Z(n, ["av1C"])[0];
			if (e && e.length > 2) {
				let t = e[1] >>> 5, r = e[1] & 31, o = e[2] >>> 7 ? "H" : "M", s = (e[2] & 64) >> 6, c = (e[2] & 32) >> 5, l = t === 2 && s ? c ? 12 : 10 : s ? 10 : 8, u = (e[2] & 16) >> 4, d = (e[2] & 8) >> 3, f = (e[2] & 4) >> 2, p = e[2] & 3;
				i += "." + t + "." + kr(r) + o + "." + kr(l) + "." + u + "." + d + f + p + "." + kr(1) + "." + kr(1) + "." + kr(1) + ".0", a = Tr("dav1", n);
			}
			break;
		}
	}
	return {
		codec: i,
		encrypted: o,
		supplemental: a
	};
}
function Tr(e, t) {
	let n = Z(t, ["dvvC"]), r = n.length ? n[0] : Z(t, ["dvcC"])[0];
	if (r) {
		let t = r[2] >> 1 & 127, n = r[2] << 5 & 32 | r[3] >> 3 & 31;
		return e + "." + kr(t) + "." + kr(n);
	}
}
function Er(e) {
	let t = 0;
	for (let n = 0; n < 32; n++) t |= (e >> n & 1) << 31 - n;
	return t >>> 0;
}
function Dr(e, t) {
	let n = t + 5;
	for (; e[t++] & 128 && t < n;);
	return t;
}
function Or(e) {
	return ("0" + e.toString(16).toUpperCase()).slice(-2);
}
function kr(e) {
	return (e < 10 ? "0" : "") + e;
}
function Ar(e, t) {
	if (!e || !t) return;
	let n = t.keyId;
	n && t.isCommonEncryption && Mr(e, (e, t) => {
		let r = e.subarray(8, 24);
		r.some((e) => e !== 0) || (Jn.log(`[eme] Patching keyId in 'enc${t ? "a" : "v"}>sinf>>tenc' box: ${$n(r)} -> ${$n(n)}`), e.set(n, 8));
	});
}
function jr(e) {
	let t = [];
	return Mr(e, (e) => t.push(e.subarray(8, 24))), t;
}
function Mr(e, t) {
	Z(e, ["moov", "trak"]).forEach((e) => {
		let n = Z(e, [
			"mdia",
			"minf",
			"stbl",
			"stsd"
		])[0];
		if (!n) return;
		let r = n.subarray(8), i = Z(r, ["enca"]), a = i.length > 0;
		a || (i = Z(r, ["encv"])), i.forEach((e) => {
			Z(a ? e.subarray(28) : e.subarray(78), ["sinf"]).forEach((e) => {
				let n = Nr(e);
				n && t(n, a);
			});
		});
	});
}
function Nr(e) {
	let t = Z(e, ["schm"])[0];
	if (t) {
		let n = _r(t.subarray(4, 8));
		if (n === "cbcs" || n === "cenc") {
			let t = Z(e, ["schi", "tenc"])[0];
			if (t) return t;
		}
	}
}
function Pr(e, t, n) {
	let r = {}, i = Z(e, ["moof", "traf"]);
	for (let e = 0; e < i.length; e++) {
		let a = i[e], o = Z(a, ["tfhd"])[0], s = X(o, 4), c = t[s];
		if (!c) continue;
		r[s] || (r[s] = {
			start: NaN,
			duration: 0,
			sampleCount: 0,
			timescale: c.timescale,
			type: c.type
		});
		let l = r[s], u = Z(a, ["tfdt"])[0];
		if (u) {
			let e = u[0], t = X(u, 4);
			e === 1 && (t === mr ? n.warn("[mp4-demuxer]: Ignoring assumed invalid signed 64-bit track fragment decode time") : (t *= mr + 1, t += X(u, 8))), W(t) && (!W(l.start) || t < l.start) && (l.start = t);
		}
		let d = c.default, f = X(o, 0) | d?.flags, p = d?.duration || 0;
		f & 8 && (p = f & 2 ? X(o, 12) : X(o, 8));
		let m = Z(a, ["trun"]), h = l.start || 0, g = 0, _ = p;
		for (let e = 0; e < m.length; e++) {
			let t = m[e], n = X(t, 4), r = l.sampleCount;
			l.sampleCount += n;
			let i = t[3] & 1, a = t[3] & 4, o = t[2] & 1, s = t[2] & 2, c = t[2] & 4, u = t[2] & 8, d = 8, f = n;
			for (i && (d += 4), a && n && (!(t[d + 1] & 1) && l.keyFrameIndex === void 0 && (l.keyFrameIndex = r), d += 4, o ? (_ = X(t, d), d += 4) : _ = p, s && (d += 4), u && (d += 4), h += _, g += _, f--); f--;) o ? (_ = X(t, d), d += 4) : _ = p, s && (d += 4), c && (t[d + 1] & 1 || l.keyFrameIndex === void 0 && (l.keyFrameIndex = l.sampleCount - (f + 1), l.keyFrameStart = h), d += 4), u && (d += 4), h += _, g += _;
			!g && p && (g += p * n);
		}
		l.duration += g;
	}
	if (!Object.keys(r).some((e) => r[e].duration)) {
		let t = Infinity, n = 0, i = Z(e, ["sidx"]);
		for (let e = 0; e < i.length; e++) {
			let r = Sr(i[e]);
			if (r != null && r.references) {
				t = Math.min(t, r.earliestPresentationTime / r.timescale);
				let e = r.references.reduce((e, t) => e + t.info.duration || 0, 0);
				n = Math.max(n, e + r.earliestPresentationTime / r.timescale);
			}
		}
		n && W(n) && Object.keys(r).forEach((e) => {
			r[e].duration || (r[e].duration = n * r[e].timescale - r[e].start);
		});
	}
	return r;
}
function Fr(e) {
	let t = {
		valid: null,
		remainder: null
	}, n = Z(e, ["moof"]);
	if (n.length < 2) return t.remainder = e, t;
	let r = n[n.length - 1];
	return t.valid = e.slice(0, r.byteOffset - 8), t.remainder = e.slice(r.byteOffset - 8), t;
}
function Ir(e, t) {
	let n = new Uint8Array(e.length + t.length);
	return n.set(e), n.set(t, e.length), n;
}
function Lr(e, t) {
	let n = [], r = t.samples, i = t.timescale, a = t.id, o = !1;
	return Z(r, ["moof"]).map((s) => {
		let c = s.byteOffset - 8;
		Z(s, ["traf"]).map((s) => {
			let l = Z(s, ["tfdt"]).map((e) => {
				let t = e[0], n = X(e, 4);
				return t === 1 && (n *= 2 ** 32, n += X(e, 8)), n / i;
			})[0];
			return l !== void 0 && (e = l), Z(s, ["tfhd"]).map((l) => {
				let u = X(l, 4), d = X(l, 0) & 16777215, f = !!(d & 1), p = !!(d & 2), m = !!(d & 8), h = 0, g = !!(d & 16), _ = 0, v = !!(d & 32), y = 8;
				u === a && (f && (y += 8), p && (y += 4), m && (h = X(l, y), y += 4), g && (_ = X(l, y), y += 4), v && (y += 4), t.type === "video" && (o = Rr(t.codec)), Z(s, ["trun"]).map((a) => {
					let s = a[0], l = X(a, 0) & 16777215, u = !!(l & 1), d = 0, f = !!(l & 4), p = !!(l & 256), m = 0, g = !!(l & 512), v = 0, y = !!(l & 1024), b = !!(l & 2048), x = 0, S = X(a, 4), C = 8;
					u && (d = X(a, C), C += 4), f && (C += 4);
					let w = d + c;
					for (let c = 0; c < S; c++) {
						if (p ? (m = X(a, C), C += 4) : m = h, g ? (v = X(a, C), C += 4) : v = _, y && (C += 4), b && (x = s === 0 ? X(a, C) : br(a, C), C += 4), t.type === sr.VIDEO) {
							let t = 0;
							for (; t < v;) {
								let a = X(r, w);
								w += 4, zr(o, r[w]) && Br(r.subarray(w, w + a), o ? 2 : 1, e + x / i, n), w += a, t += a + 4;
							}
						}
						e += m / i;
					}
				}));
			});
		});
	}), n;
}
function Rr(e) {
	if (!e) return !1;
	let t = e.substring(0, 4);
	return t === "hvc1" || t === "hev1" || t === "dvh1" || t === "dvhe";
}
function zr(e, t) {
	if (e) {
		let e = t >> 1 & 63;
		return e === 39 || e === 40;
	}
	return (t & 31) == 6;
}
function Br(e, t, n, r) {
	let i = Vr(e), a = 0;
	a += t;
	let o = 0, s = 0, c = 0;
	for (; a < i.length;) {
		o = 0;
		do {
			if (a >= i.length) break;
			c = i[a++], o += c;
		} while (c === 255);
		s = 0;
		do {
			if (a >= i.length) break;
			c = i[a++], s += c;
		} while (c === 255);
		let e = i.length - a, t = a;
		if (s < e) a += s;
		else if (s > e) {
			Jn.error(`Malformed SEI payload. ${s} is too small, only ${e} bytes left to parse.`);
			break;
		}
		if (o === 4) {
			if (i[t++] === 181) {
				let e = vr(i, t);
				if (t += 2, e === 49) {
					let e = X(i, t);
					if (t += 4, e === 1195456820) {
						let e = i[t++];
						if (e === 3) {
							let a = i[t++], s = 31 & a, c = 64 & a, l = c ? 2 + s * 3 : 0, u = new Uint8Array(l);
							if (c) {
								u[0] = a;
								for (let e = 1; e < l; e++) u[e] = i[t++];
							}
							r.push({
								type: e,
								payloadType: o,
								pts: n,
								bytes: u
							});
						}
					}
				}
			}
		} else if (o === 5 && s > 16) {
			let e = [];
			for (let n = 0; n < 16; n++) {
				let r = i[t++].toString(16);
				e.push(r.length == 1 ? "0" + r : r), (n === 3 || n === 5 || n === 7 || n === 9) && e.push("-");
			}
			let a = s - 16, c = new Uint8Array(a);
			for (let e = 0; e < a; e++) c[e] = i[t++];
			r.push({
				payloadType: o,
				pts: n,
				uuid: e.join(""),
				userData: Qn(c),
				userDataBytes: c
			});
		}
	}
}
function Vr(e) {
	let t = e.byteLength, n = [], r = 1;
	for (; r < t - 2;) e[r] === 0 && e[r + 1] === 0 && e[r + 2] === 3 ? (n.push(r + 2), r += 2) : r++;
	if (n.length === 0) return e;
	let i = t - n.length, a = new Uint8Array(i), o = 0;
	for (r = 0; r < i; o++, r++) o === n[0] && (o++, n.shift()), a[r] = e[o];
	return a;
}
function Hr(e) {
	let t = e[0], n = "", r = "", i = 0, a = 0, o = 0, s = 0, c = 0, l = 0;
	if (t === 0) {
		for (; _r(e.subarray(l, l + 1)) !== "\0";) n += _r(e.subarray(l, l + 1)), l += 1;
		for (n += _r(e.subarray(l, l + 1)), l += 1; _r(e.subarray(l, l + 1)) !== "\0";) r += _r(e.subarray(l, l + 1)), l += 1;
		r += _r(e.subarray(l, l + 1)), l += 1, i = X(e, 12), a = X(e, 16), s = X(e, 20), c = X(e, 24), l = 28;
	} else if (t === 1) {
		l += 4, i = X(e, l), l += 4;
		let t = X(e, l);
		l += 4;
		let a = X(e, l);
		for (l += 4, o = 2 ** 32 * t + a, An(o) || (o = 2 ** 53 - 1, Jn.warn("Presentation time exceeds safe integer limit and wrapped to max safe integer in parsing emsg box")), s = X(e, l), l += 4, c = X(e, l), l += 4; _r(e.subarray(l, l + 1)) !== "\0";) n += _r(e.subarray(l, l + 1)), l += 1;
		for (n += _r(e.subarray(l, l + 1)), l += 1; _r(e.subarray(l, l + 1)) !== "\0";) r += _r(e.subarray(l, l + 1)), l += 1;
		r += _r(e.subarray(l, l + 1)), l += 1;
	}
	let u = e.subarray(l, e.byteLength);
	return {
		schemeIdUri: n,
		value: r,
		timeScale: i,
		presentationTime: o,
		presentationTimeDelta: a,
		eventDuration: s,
		id: c,
		payload: u
	};
}
function Ur(e, ...t) {
	let n = t.length, r = 8, i = n;
	for (; i--;) r += t[i].byteLength;
	let a = new Uint8Array(r);
	for (a[0] = r >> 24 & 255, a[1] = r >> 16 & 255, a[2] = r >> 8 & 255, a[3] = r & 255, a.set(e, 4), i = 0, r = 8; i < n; i++) a.set(t[i], r), r += t[i].byteLength;
	return a;
}
function Wr(e, t, n) {
	if (e.byteLength !== 16) throw RangeError("Invalid system id");
	let r, i;
	r = 0, i = /* @__PURE__ */ new Uint8Array();
	let a;
	r > 0 ? (a = /* @__PURE__ */ new Uint8Array(4), t.length > 0 && new DataView(a.buffer).setUint32(0, t.length, !1)) : a = /* @__PURE__ */ new Uint8Array();
	let o = /* @__PURE__ */ new Uint8Array(4);
	return n.byteLength > 0 && new DataView(o.buffer).setUint32(0, n.byteLength, !1), Ur([
		112,
		115,
		115,
		104
	], new Uint8Array([
		r,
		0,
		0,
		0
	]), e, a, i, o, n);
}
function Gr(e) {
	let t = [];
	if (e instanceof ArrayBuffer) {
		let n = e.byteLength, r = 0;
		for (; r + 32 < n;) {
			let n = Kr(new DataView(e, r));
			t.push(n), r += n.size;
		}
	}
	return t;
}
function Kr(e) {
	let t = e.getUint32(0), n = e.byteOffset, r = e.byteLength;
	if (r < t) return {
		offset: n,
		size: r
	};
	if (e.getUint32(4) !== 1886614376) return {
		offset: n,
		size: t
	};
	let i = e.getUint32(8) >>> 24;
	if (i !== 0 && i !== 1) return {
		offset: n,
		size: t
	};
	let a = e.buffer, o = $n(new Uint8Array(a, n + 12, 16)), s = null, c = null, l = 0;
	if (i === 0) l = 28;
	else {
		let i = e.getUint32(28);
		if (!i || r < 32 + i * 16) return {
			offset: n,
			size: t
		};
		s = [];
		for (let e = 0; e < i; e++) s.push(new Uint8Array(a, n + 32 + e * 16, 16));
		l = 32 + i * 16;
	}
	if (!l) return {
		offset: n,
		size: t
	};
	let u = e.getUint32(l);
	return t - 32 < u ? {
		offset: n,
		size: t
	} : (c = new Uint8Array(a, n + l + 4, u), {
		version: i,
		systemId: o,
		kids: s,
		data: c,
		offset: n,
		size: t
	});
}
var qr = () => /\(Windows.+Firefox\//i.test(navigator.userAgent), Jr = {
	audio: {
		a3ds: 1,
		"ac-3": .95,
		"ac-4": 1,
		alac: .9,
		alaw: 1,
		dra1: 1,
		"dts+": 1,
		"dts-": 1,
		dtsc: 1,
		dtse: 1,
		dtsh: 1,
		"ec-3": .9,
		enca: 1,
		fLaC: .9,
		flac: .9,
		FLAC: .9,
		g719: 1,
		g726: 1,
		m4ae: 1,
		mha1: 1,
		mha2: 1,
		mhm1: 1,
		mhm2: 1,
		mlpa: 1,
		mp4a: 1,
		"raw ": 1,
		Opus: 1,
		opus: 1,
		samr: 1,
		sawb: 1,
		sawp: 1,
		sevc: 1,
		sqcp: 1,
		ssmv: 1,
		twos: 1,
		ulaw: 1
	},
	video: {
		avc1: 1,
		avc2: 1,
		avc3: 1,
		avc4: 1,
		avcp: 1,
		av01: .8,
		dav1: .8,
		drac: 1,
		dva1: 1,
		dvav: 1,
		dvh1: .7,
		dvhe: .7,
		encv: 1,
		hev1: .75,
		hvc1: .75,
		mjp2: 1,
		mp4v: 1,
		mvc1: 1,
		mvc2: 1,
		mvc3: 1,
		mvc4: 1,
		resv: 1,
		rv60: 1,
		s263: 1,
		svc1: 1,
		svc2: 1,
		"vc-1": 1,
		vp08: 1,
		vp09: .9
	},
	text: {
		stpp: 1,
		wvtt: 1
	}
};
function Yr(e, t) {
	let n = Jr[t];
	return !!n && !!n[e.slice(0, 4)];
}
function Xr(e, t, n = !0) {
	return !e.split(",").some((e) => !Zr(e, t, n));
}
function Zr(e, t, n = !0) {
	return Yn(n)?.isTypeSupported(Qr(e, t)) ?? !1;
}
function Qr(e, t) {
	return `${t}/mp4;codecs=${e}`;
}
function $r(e) {
	if (e) {
		let t = e.substring(0, 4);
		return Jr.video[t];
	}
	return 2;
}
function ei(e) {
	let t = qr();
	return e.split(",").reduce((e, n) => {
		let r = t && Rr(n) ? 9 : Jr.video[n];
		return r ? (r * 2 + e) / (e ? 3 : 2) : (Jr.audio[n] + e) / (e ? 2 : 1);
	}, 0);
}
var ti = {};
function ni(e, t = !0) {
	if (ti[e]) return ti[e];
	let n = {
		flac: [
			"flac",
			"fLaC",
			"FLAC"
		],
		opus: ["opus", "Opus"],
		"mp4a.40.34": ["mp3"]
	}[e];
	for (let i = 0; i < n.length; i++) {
		var r;
		if (Zr(n[i], "audio", t)) return ti[e] = n[i], n[i];
		if (n[i] === "mp3" && (r = Yn(t)) != null && r.isTypeSupported("audio/mpeg")) return "";
	}
	return e;
}
var ri = /flac|opus|mp4a\.40\.34/i;
function ii(e, t = !0) {
	return e.replace(ri, (e) => ni(e.toLowerCase(), t));
}
function ai(e, t) {
	let n = [];
	if (e) {
		let t = e.split(",");
		for (let e = 0; e < t.length; e++) Yr(t[e], "video") || n.push(t[e]);
	}
	return t && n.push(t), n.join(",");
}
function oi(e, t) {
	if (e && (e.length > 4 || [
		"ac-3",
		"ec-3",
		"alac",
		"fLaC",
		"Opus"
	].indexOf(e) !== -1) && (si(e, "audio") || si(e, "video"))) return e;
	if (t) {
		let n = t.split(",");
		if (n.length > 1) {
			if (e) {
				for (let t = n.length; t--;) if (n[t].substring(0, 4) === e.substring(0, 4)) return n[t];
			}
			return n[0];
		}
	}
	return t || e;
}
function si(e, t) {
	return Yr(e, t) && Zr(e, t);
}
function ci(e) {
	let t = e.split(",");
	for (let e = 0; e < t.length; e++) {
		let n = t[e].split(".");
		n.length > 2 && n[0] === "avc1" && (t[e] = `avc1.${parseInt(n[1]).toString(16)}${("000" + parseInt(n[2]).toString(16)).slice(-4)}`);
	}
	return t.join(",");
}
function li(e) {
	if (e.startsWith("av01.")) {
		let t = e.split("."), n = [
			"0",
			"111",
			"01",
			"01",
			"01",
			"0"
		];
		for (let e = t.length; e > 4 && e < 10; e++) t[e] = n[e - 4];
		return t.join(".");
	}
	return e;
}
function ui(e) {
	let t = Yn(e) || { isTypeSupported: () => !1 };
	return {
		mpeg: t.isTypeSupported("audio/mpeg"),
		mp3: t.isTypeSupported("audio/mp4; codecs=\"mp3\""),
		ac3: t.isTypeSupported("audio/mp4; codecs=\"ac-3\"")
	};
}
function di(e) {
	return e.replace(/^.+codecs=["']?([^"']+).*$/, "$1");
}
var fi = {
	supported: !0,
	powerEfficient: !0,
	smooth: !0
}, pi = {
	supported: !1,
	smooth: !1,
	powerEfficient: !1
}, mi = {
	supported: !0,
	configurations: [],
	decodingInfoResults: [fi]
};
function hi(e, t) {
	return {
		supported: !1,
		configurations: t,
		decodingInfoResults: [pi],
		error: e
	};
}
function gi(e, t, n, r, i, a) {
	let o = e.videoCodec, s = e.audioCodec ? e.audioGroups : null, c = a?.audioCodec, l = a?.channels, u = l ? parseInt(l) : c ? Infinity : 2, d = null;
	if (s != null && s.length) try {
		d = s.length === 1 && s[0] ? t.groups[s[0]].channels : s.reduce((e, n) => {
			if (n) {
				let r = t.groups[n];
				if (!r) throw Error(`Audio track group ${n} not found`);
				Object.keys(r.channels).forEach((t) => {
					e[t] = (e[t] || 0) + r.channels[t];
				});
			}
			return e;
		}, { 2: 0 });
	} catch {
		return !0;
	}
	return o !== void 0 && (o.split(",").some((e) => Rr(e)) || e.width > 1920 && e.height > 1088 || e.height > 1920 && e.width > 1088 || e.frameRate > Math.max(r, 30) || e.videoRange !== "SDR" && e.videoRange !== n || e.bitrate > Math.max(i, 8e6)) || !!d && W(u) && Object.keys(d).some((e) => parseInt(e) > u);
}
function _i(e, t, n, r = {}) {
	let i = e.videoCodec;
	if (!i && !e.audioCodec || !n) return Promise.resolve(mi);
	let a = [], o = vi(e), s = o.length, c = yi(e, t, s > 0), l = c.length;
	for (let e = s || 1 * l || 1; e--;) {
		let t = { type: "media-source" };
		if (s && (t.video = o[e % s]), l) {
			t.audio = c[e % l];
			let n = t.audio.bitrate;
			t.video && n && (t.video.bitrate -= n);
		}
		a.push(t);
	}
	if (i) {
		let e = navigator.userAgent;
		if (i.split(",").some((e) => Rr(e)) && qr()) return Promise.resolve(hi(/* @__PURE__ */ Error(`Overriding Windows Firefox HEVC MediaCapabilities result based on user-agent string: (${e})`), a));
	}
	return Promise.all(a.map((e) => {
		let t = Si(e);
		return r[t] || (r[t] = n.decodingInfo(e));
	})).then((e) => ({
		supported: !e.some((e) => !e.supported),
		configurations: a,
		decodingInfoResults: e
	})).catch((e) => ({
		supported: !1,
		configurations: a,
		decodingInfoResults: [],
		error: e
	}));
}
function vi(e) {
	let t = e.videoCodec?.split(","), n = xi(e), r = e.width || 640, i = e.height || 480, a = e.frameRate || 30, o = e.videoRange.toLowerCase();
	return t ? t.map((e) => {
		let t = {
			contentType: Qr(li(e), "video"),
			width: r,
			height: i,
			bitrate: n,
			framerate: a
		};
		return o !== "sdr" && (t.transferFunction = o), t;
	}) : [];
}
function yi(e, t, n) {
	let r = e.audioCodec?.split(","), i = xi(e);
	return r && e.audioGroups ? e.audioGroups.reduce((e, a) => {
		let o = a ? t.groups[a]?.tracks : null;
		return o ? o.reduce((e, t) => {
			if (t.groupId === a) {
				let a = parseFloat(t.channels || "");
				r.forEach((t) => {
					let r = {
						contentType: Qr(t, "audio"),
						bitrate: n ? bi(t, i) : i
					};
					a && (r.channels = "" + a), e.push(r);
				});
			}
			return e;
		}, e) : e;
	}, []) : [];
}
function bi(e, t) {
	if (t <= 1) return 1;
	let n = 128e3;
	return e === "ec-3" ? n = 768e3 : e === "ac-3" && (n = 64e4), Math.min(t / 2, n);
}
function xi(e) {
	return Math.ceil(Math.max(e.bitrate * .9, e.averageBitrate) / 1e3) * 1e3 || 1;
}
function Si(e) {
	let t = "", { audio: n, video: r } = e;
	if (r) {
		let e = di(r.contentType);
		t += `${e}_r${r.height}x${r.width}f${Math.ceil(r.framerate)}${r.transferFunction || "sd"}_${Math.ceil(r.bitrate / 1e5)}`;
	}
	if (n) {
		let e = di(n.contentType);
		t += `${r ? "_" : ""}${e}_c${n.channels}`;
	}
	return t;
}
var Ci = [
	"NONE",
	"TYPE-0",
	"TYPE-1",
	null
];
function wi(e) {
	return Ci.indexOf(e) > -1;
}
var Ti = [
	"SDR",
	"PQ",
	"HLG"
];
function Ei(e) {
	return !!e && Ti.indexOf(e) > -1;
}
var Di = {
	No: "",
	Yes: "YES",
	v2: "v2"
};
function Oi(e) {
	let { canSkipUntil: t, canSkipDateRanges: n, age: r } = e, i = r < t / 2;
	return t && i ? n ? Di.v2 : Di.Yes : Di.No;
}
var ki = class {
	constructor(e, t, n) {
		this.msn = void 0, this.part = void 0, this.skip = void 0, this.msn = e, this.part = t, this.skip = n;
	}
	addDirectives(e) {
		let t = new self.URL(e);
		return this.msn !== void 0 && t.searchParams.set("_HLS_msn", this.msn.toString()), this.part !== void 0 && t.searchParams.set("_HLS_part", this.part.toString()), this.skip && t.searchParams.set("_HLS_skip", this.skip), t.href;
	}
}, Ai = class {
	constructor(e) {
		if (this._attrs = void 0, this.audioCodec = void 0, this.bitrate = void 0, this.codecSet = void 0, this.url = void 0, this.frameRate = void 0, this.height = void 0, this.id = void 0, this.name = void 0, this.supplemental = void 0, this.videoCodec = void 0, this.width = void 0, this.details = void 0, this.fragmentError = 0, this.loadError = 0, this.loaded = void 0, this.realBitrate = 0, this.supportedPromise = void 0, this.supportedResult = void 0, this._avgBitrate = 0, this._audioGroups = void 0, this._subtitleGroups = void 0, this._urlId = 0, this.url = [e.url], this._attrs = [e.attrs], this.bitrate = e.bitrate, e.details && (this.details = e.details), this.id = e.id || 0, this.name = e.name, this.width = e.width || 0, this.height = e.height || 0, this.frameRate = e.attrs.optionalFloat("FRAME-RATE", 0), this._avgBitrate = e.attrs.decimalInteger("AVERAGE-BANDWIDTH"), this.audioCodec = e.audioCodec, this.videoCodec = e.videoCodec, this.codecSet = [e.videoCodec, e.audioCodec].filter((e) => !!e).map((e) => e.substring(0, 4)).join(","), "supplemental" in e) {
			this.supplemental = e.supplemental;
			let t = e.supplemental?.videoCodec;
			t && t !== e.videoCodec && (this.codecSet += `,${t.substring(0, 4)}`);
		}
		this.addGroupId("audio", e.attrs.AUDIO), this.addGroupId("text", e.attrs.SUBTITLES);
	}
	get maxBitrate() {
		return Math.max(this.realBitrate, this.bitrate);
	}
	get averageBitrate() {
		return this._avgBitrate || this.realBitrate || this.bitrate;
	}
	get attrs() {
		return this._attrs[0];
	}
	get codecs() {
		return this.attrs.CODECS || "";
	}
	get pathwayId() {
		return this.attrs["PATHWAY-ID"] || ".";
	}
	get videoRange() {
		return this.attrs["VIDEO-RANGE"] || "SDR";
	}
	get score() {
		return this.attrs.optionalFloat("SCORE", 0);
	}
	get uri() {
		return this.url[0] || "";
	}
	hasAudioGroup(e) {
		return ji(this._audioGroups, e);
	}
	hasSubtitleGroup(e) {
		return ji(this._subtitleGroups, e);
	}
	get audioGroups() {
		return this._audioGroups;
	}
	get subtitleGroups() {
		return this._subtitleGroups;
	}
	addGroupId(e, t) {
		if (t) {
			if (e === "audio") {
				let e = this._audioGroups;
				e ||= this._audioGroups = [], e.indexOf(t) === -1 && e.push(t);
			} else if (e === "text") {
				let e = this._subtitleGroups;
				e ||= this._subtitleGroups = [], e.indexOf(t) === -1 && e.push(t);
			}
		}
	}
	get urlId() {
		return 0;
	}
	set urlId(e) {}
	get audioGroupIds() {
		return this.audioGroups ? [this.audioGroupId] : void 0;
	}
	get textGroupIds() {
		return this.subtitleGroups ? [this.textGroupId] : void 0;
	}
	get audioGroupId() {
		return this.audioGroups?.[0];
	}
	get textGroupId() {
		return this.subtitleGroups?.[0];
	}
	addFallback() {}
};
function ji(e, t) {
	return !t || !e ? !1 : e.indexOf(t) !== -1;
}
function Mi() {
	if (typeof matchMedia == "function") {
		let e = matchMedia("(dynamic-range: high)"), t = matchMedia("bad query");
		if (e.media !== t.media) return e.matches === !0;
	}
	return !1;
}
function Ni(e, t) {
	let n = !1, r = [];
	if (e && (n = e !== "SDR", r = [e]), t) {
		r = t.allowedVideoRanges || Ti.slice(0);
		let e = r.join("") !== "SDR" && !t.videoCodec;
		n = t.preferHDR === void 0 ? e && Mi() : t.preferHDR, n || (r = ["SDR"]);
	}
	return {
		preferHDR: n,
		allowedVideoRanges: r
	};
}
var Pi = (e) => {
	let t = /* @__PURE__ */ new WeakSet();
	return (n, r) => {
		if (e && (r = e(n, r)), typeof r == "object" && r) {
			if (t.has(r)) return;
			t.add(r);
		}
		return r;
	};
}, Fi = (e, t) => JSON.stringify(e, Pi(t));
function Ii(e, t, n, r, i) {
	let a = Object.keys(e), o = r?.channels, s = r?.audioCodec, c = i?.videoCodec, l = o && parseInt(o) === 2, u = !1, d = !1, f = Infinity, p = Infinity, m = Infinity, h = Infinity, g = 0, _ = [], { preferHDR: v, allowedVideoRanges: y } = Ni(t, i);
	for (let t = a.length; t--;) {
		let n = e[a[t]];
		u ||= n.channels[2] > 0, f = Math.min(f, n.minHeight), p = Math.min(p, n.minFramerate), m = Math.min(m, n.minBitrate), y.filter((e) => n.videoRanges[e] > 0).length > 0 && (d = !0);
	}
	f = W(f) ? f : 0, p = W(p) ? p : 0;
	let b = Math.max(1080, f), x = Math.max(30, p);
	m = W(m) ? m : n, n = Math.max(m, n), d || (t = void 0);
	let S = a.length > 1;
	return {
		codecSet: a.reduce((t, r) => {
			let i = e[r];
			if (r === t) return t;
			if (_ = d ? y.filter((e) => i.videoRanges[e] > 0) : [], S) {
				if (i.minBitrate > n) return Li(r, `min bitrate of ${i.minBitrate} > current estimate of ${n}`), t;
				if (!i.hasDefaultAudio) return Li(r, "no renditions with default or auto-select sound found"), t;
				if (s && r.indexOf(s.substring(0, 4)) % 5 != 0) return Li(r, `audio codec preference "${s}" not found`), t;
				if (o && !l) {
					if (!i.channels[o]) return Li(r, `no renditions with ${o} channel sound found (channels options: ${Object.keys(i.channels)})`), t;
				} else if ((!s || l) && u && i.channels[2] === 0) return Li(r, "no renditions with stereo sound found"), t;
				if (i.minHeight > b) return Li(r, `min resolution of ${i.minHeight} > maximum of ${b}`), t;
				if (i.minFramerate > x) return Li(r, `min framerate of ${i.minFramerate} > maximum of ${x}`), t;
				if (!_.some((e) => i.videoRanges[e] > 0)) return Li(r, `no variants with VIDEO-RANGE of ${Fi(_)} found`), t;
				if (c && r.indexOf(c.substring(0, 4)) % 5 != 0) return Li(r, `video codec preference "${c}" not found`), t;
				if (i.maxScore < g) return Li(r, `max score of ${i.maxScore} < selected max of ${g}`), t;
			}
			return t && (ei(r) >= ei(t) || i.fragmentError > e[t].fragmentError) ? t : (h = i.minIndex, g = i.maxScore, r);
		}, void 0),
		videoRanges: _,
		preferHDR: v,
		minFramerate: p,
		minBitrate: m,
		minIndex: h
	};
}
function Li(e, t) {
	Jn.log(`[abr] start candidates with "${e}" ignored because ${t}`);
}
function Ri(e) {
	return e.reduce((e, t) => {
		let n = e.groups[t.groupId];
		n ||= e.groups[t.groupId] = {
			tracks: [],
			channels: { 2: 0 },
			hasDefault: !1,
			hasAutoSelect: !1
		}, n.tracks.push(t);
		let r = t.channels || "2";
		return n.channels[r] = (n.channels[r] || 0) + 1, n.hasDefault = n.hasDefault || t.default, n.hasAutoSelect = n.hasAutoSelect || t.autoselect, n.hasDefault && (e.hasDefaultAudio = !0), n.hasAutoSelect && (e.hasAutoSelectAudio = !0), e;
	}, {
		hasDefaultAudio: !1,
		hasAutoSelectAudio: !1,
		groups: {}
	});
}
function zi(e, t, n, r) {
	return e.slice(n, r + 1).reduce((e, n, r) => {
		if (!n.codecSet) return e;
		let i = n.audioGroups, a = e[n.codecSet];
		a || (e[n.codecSet] = a = {
			minBitrate: Infinity,
			minHeight: Infinity,
			minFramerate: Infinity,
			minIndex: r,
			maxScore: 0,
			videoRanges: { SDR: 0 },
			channels: { 2: 0 },
			hasDefaultAudio: !i,
			fragmentError: 0
		}), a.minBitrate = Math.min(a.minBitrate, n.bitrate);
		let o = Math.min(n.height, n.width);
		return a.minHeight = Math.min(a.minHeight, o), a.minFramerate = Math.min(a.minFramerate, n.frameRate), a.minIndex = Math.min(a.minIndex, r), a.maxScore = Math.max(a.maxScore, n.score), a.fragmentError += n.fragmentError, a.videoRanges[n.videoRange] = (a.videoRanges[n.videoRange] || 0) + 1, i && i.forEach((e) => {
			if (!e) return;
			let n = t.groups[e];
			n && (a.hasDefaultAudio = a.hasDefaultAudio || t.hasDefaultAudio ? n.hasDefault : n.hasAutoSelect || !t.hasDefaultAudio && !t.hasAutoSelectAudio, Object.keys(n.channels).forEach((e) => {
				a.channels[e] = (a.channels[e] || 0) + n.channels[e];
			}));
		}), e;
	}, {});
}
function Bi(e) {
	if (!e) return e;
	let { lang: t, assocLang: n, characteristics: r, channels: i, audioCodec: a } = e;
	return {
		lang: t,
		assocLang: n,
		characteristics: r,
		channels: i,
		audioCodec: a
	};
}
function Vi(e, t, n) {
	if ("attrs" in e) {
		let n = t.indexOf(e);
		if (n !== -1) return n;
	}
	for (let r = 0; r < t.length; r++) {
		let i = t[r];
		if (Hi(e, i, n)) return r;
	}
	return -1;
}
function Hi(e, t, n) {
	let { groupId: r, name: i, lang: a, assocLang: o, default: s } = e, c = e.forced;
	return (r === void 0 || t.groupId === r) && (i === void 0 || t.name === i) && (a === void 0 || Ui(a, t.lang)) && (a === void 0 || t.assocLang === o) && (s === void 0 || t.default === s) && (c === void 0 || t.forced === c) && (!("characteristics" in e) || Wi(e.characteristics || "", t.characteristics)) && (n === void 0 || n(e, t));
}
function Ui(e, t = "--") {
	return e.length === t.length ? e === t : e.startsWith(t) || t.startsWith(e);
}
function Wi(e, t = "") {
	let n = e.split(","), r = t.split(",");
	return n.length === r.length && !n.some((e) => r.indexOf(e) === -1);
}
function Gi(e, t) {
	let { audioCodec: n, channels: r } = e;
	return (n === void 0 || (t.audioCodec || "").substring(0, 4) === n.substring(0, 4)) && (r === void 0 || r === (t.channels || "2"));
}
function Ki(e, t, n, r, i) {
	let a = t[r], o = t.reduce((e, t, n) => {
		let r = t.uri;
		return (e[r] || (e[r] = [])).push(n), e;
	}, {})[a.uri];
	o.length > 1 && (r = Math.max.apply(Math, o));
	let s = a.videoRange, c = a.frameRate, l = a.codecSet.substring(0, 4), u = qi(t, r, (t) => {
		if (t.videoRange !== s || t.frameRate !== c || t.codecSet.substring(0, 4) !== l) return !1;
		let r = t.audioGroups;
		return Vi(e, n.filter((e) => !r || r.indexOf(e.groupId) !== -1), i) > -1;
	});
	return u > -1 ? u : qi(t, r, (t) => {
		let r = t.audioGroups;
		return Vi(e, n.filter((e) => !r || r.indexOf(e.groupId) !== -1), i) > -1;
	});
}
function qi(e, t, n) {
	for (let r = t; r > -1; r--) if (n(e[r])) return r;
	for (let r = t + 1; r < e.length; r++) if (n(e[r])) return r;
	return -1;
}
function Ji(e, t) {
	return !!e && e !== t.loadLevelObj?.uri;
}
var Yi = class extends Bn {
	constructor(e) {
		super("abr", e.logger), this.hls = void 0, this.lastLevelLoadSec = 0, this.lastLoadedFragLevel = -1, this.firstSelection = -1, this._nextAutoLevel = -1, this.nextAutoLevelKey = "", this.audioTracksByGroup = null, this.codecTiers = null, this.timer = -1, this.fragCurrent = null, this.partCurrent = null, this.bitrateTestDelay = 0, this.rebufferNotice = -1, this.supportedCache = {}, this.bwEstimator = void 0, this._abandonRulesCheck = (e) => {
			let { fragCurrent: t, partCurrent: n, hls: r } = this, { autoLevelEnabled: i, media: a } = r;
			if (!t || !a) return;
			let o = performance.now(), s = n ? n.stats : t.stats, c = n ? n.duration : t.duration, l = o - s.loading.start, u = r.minAutoLevel, d = t.level, f = this._nextAutoLevel;
			if (s.aborted || s.loaded && s.loaded === s.total || d <= u) {
				this.clearTimer(), this._nextAutoLevel = -1;
				return;
			}
			if (!i) return;
			let p = f > -1 && f !== d, m = !!e || p;
			if (!m && (a.paused || !a.playbackRate || !a.readyState)) return;
			let h = r.mainForwardBufferInfo;
			if (!m && h === null) return;
			let g = this.bwEstimator.getEstimateTTFB(), _ = Math.abs(a.playbackRate);
			if (l <= Math.max(g, 1e3 * (c / (_ * 2)))) return;
			let v = h ? h.len / _ : 0, y = s.loading.first ? s.loading.first - s.loading.start : -1, b = s.loaded && y > -1, x = this.getBwEstimate(), S = r.levels, C = S[d], w = Math.max(s.loaded, Math.round(c * (t.bitrate || C.averageBitrate) / 8)), T = b ? l - y : l;
			T < 1 && b && (T = Math.min(l, s.loaded * 8 / x));
			let E = b ? s.loaded * 1e3 / T : 0, D = g / 1e3, O = E ? (w - s.loaded) / E : w * 8 / x + D;
			if (O <= v) return;
			let k = E ? E * 8 : x, A = (e?.details || this.hls.latestLevelDetails)?.live === !0, j = this.hls.config.abrBandWidthUpFactor, M = Infinity, N;
			for (N = d - 1; N > u; N--) {
				let e = S[N].maxBitrate, t = !S[N].details || A;
				if (M = this.getTimeToLoadFrag(D, k, c * e, t), M < Math.min(v, c + D)) break;
			}
			if (M >= O || M > c * 10) return;
			b ? this.bwEstimator.sample(l - Math.min(g, y), s.loaded) : this.bwEstimator.sampleTTFB(l);
			let ee = S[N].maxBitrate;
			this.getBwEstimate() * j > ee && this.resetEstimator(ee);
			let P = this.findBestLevel(ee, u, N, 0, v, 1, 1);
			P > -1 && (N = P), this.warn(`Fragment ${t.sn}${n ? " part " + n.index : ""} of level ${d} is loading too slowly;
      Fragment duration: ${t.duration.toFixed(3)}
      Time to underbuffer: ${v.toFixed(3)} s
      Estimated load time for current fragment: ${O.toFixed(3)} s
      Estimated load time for down switch fragment: ${M.toFixed(3)} s
      TTFB estimate: ${y | 0} ms
      Current BW estimate: ${W(x) ? x | 0 : "Unknown"} bps
      New BW estimate: ${this.getBwEstimate() | 0} bps
      Switching to level ${N} @ ${ee | 0} bps`), r.nextLoadLevel = r.nextAutoLevel = N, this.clearTimer();
			let te = () => {
				if (this.clearTimer(), this.fragCurrent === t && this.hls.loadLevel === N && N > 0) {
					let e = this.getStarvationDelay();
					if (this.warn(`Aborting inflight request ${N > 0 ? "and switching down" : ""}
      Fragment duration: ${t.duration.toFixed(3)} s
      Time to underbuffer: ${e.toFixed(3)} s`), t.abortRequests(), this.fragCurrent = this.partCurrent = null, N > u) {
						let t = this.findBestLevel(this.hls.levels[u].bitrate, u, N, 0, e, 1, 1);
						t === -1 && (t = u), this.hls.nextLoadLevel = this.hls.nextAutoLevel = t, this.resetEstimator(this.hls.levels[t].bitrate);
					}
				}
			};
			p || O > M * 2 ? te() : this.timer = self.setInterval(te, M * 1e3), r.trigger(q.FRAG_LOAD_EMERGENCY_ABORTED, {
				frag: t,
				part: n,
				stats: s
			});
		}, this.hls = e, this.bwEstimator = this.initEstimator(), this.registerListeners();
	}
	resetEstimator(e) {
		e && (this.log(`setting initial bwe to ${e}`), this.hls.config.abrEwmaDefaultEstimate = e), this.firstSelection = -1, this.bwEstimator = this.initEstimator();
	}
	initEstimator() {
		let e = this.hls.config;
		return new Nn(e.abrEwmaSlowVoD, e.abrEwmaFastVoD, e.abrEwmaDefaultEstimate);
	}
	registerListeners() {
		let { hls: e } = this;
		e.on(q.MANIFEST_LOADING, this.onManifestLoading, this), e.on(q.FRAG_LOADING, this.onFragLoading, this), e.on(q.FRAG_LOADED, this.onFragLoaded, this), e.on(q.FRAG_BUFFERED, this.onFragBuffered, this), e.on(q.LEVEL_SWITCHING, this.onLevelSwitching, this), e.on(q.LEVEL_LOADED, this.onLevelLoaded, this), e.on(q.LEVELS_UPDATED, this.onLevelsUpdated, this), e.on(q.MAX_AUTO_LEVEL_UPDATED, this.onMaxAutoLevelUpdated, this), e.on(q.ERROR, this.onError, this);
	}
	unregisterListeners() {
		let { hls: e } = this;
		e && (e.off(q.MANIFEST_LOADING, this.onManifestLoading, this), e.off(q.FRAG_LOADING, this.onFragLoading, this), e.off(q.FRAG_LOADED, this.onFragLoaded, this), e.off(q.FRAG_BUFFERED, this.onFragBuffered, this), e.off(q.LEVEL_SWITCHING, this.onLevelSwitching, this), e.off(q.LEVEL_LOADED, this.onLevelLoaded, this), e.off(q.LEVELS_UPDATED, this.onLevelsUpdated, this), e.off(q.MAX_AUTO_LEVEL_UPDATED, this.onMaxAutoLevelUpdated, this), e.off(q.ERROR, this.onError, this));
	}
	destroy() {
		this.unregisterListeners(), this.clearTimer(), this.hls = this._abandonRulesCheck = this.supportedCache = null, this.fragCurrent = this.partCurrent = null;
	}
	onManifestLoading(e, t) {
		this.lastLoadedFragLevel = -1, this.firstSelection = -1, this.lastLevelLoadSec = 0, this.supportedCache = {}, this.fragCurrent = this.partCurrent = null, this.onLevelsUpdated(), this.clearTimer();
	}
	onLevelsUpdated() {
		this.lastLoadedFragLevel > -1 && this.fragCurrent && (this.lastLoadedFragLevel = this.fragCurrent.level), this._nextAutoLevel = -1, this.onMaxAutoLevelUpdated(), this.codecTiers = null, this.audioTracksByGroup = null;
	}
	onMaxAutoLevelUpdated() {
		this.firstSelection = -1, this.nextAutoLevelKey = "";
	}
	onFragLoading(e, t) {
		let n = t.frag;
		this.ignoreFragment(n) || (n.bitrateTest || (this.fragCurrent = n, this.partCurrent = t.part ?? null), this.clearTimer(), this.timer = self.setInterval(this._abandonRulesCheck, 100));
	}
	onLevelSwitching(e, t) {
		this.clearTimer();
	}
	onError(e, t) {
		if (!t.fatal) switch (t.details) {
			case K.BUFFER_ADD_CODEC_ERROR:
			case K.BUFFER_APPEND_ERROR:
				this.lastLoadedFragLevel = -1, this.firstSelection = -1;
				break;
			case K.FRAG_LOAD_TIMEOUT: {
				let e = t.frag, { fragCurrent: n, partCurrent: r } = this;
				if (e && n && e.sn === n.sn && e.level === n.level) {
					let t = performance.now(), n = r ? r.stats : e.stats, i = t - n.loading.start, a = n.loading.first ? n.loading.first - n.loading.start : -1;
					if (n.loaded && a > -1) {
						let e = this.bwEstimator.getEstimateTTFB();
						this.bwEstimator.sample(i - Math.min(e, a), n.loaded);
					} else this.bwEstimator.sampleTTFB(i);
				}
				break;
			}
		}
	}
	getTimeToLoadFrag(e, t, n, r) {
		return e + n / t + (r ? e + this.lastLevelLoadSec : 0);
	}
	onLevelLoaded(e, t) {
		let n = this.hls.config, { loading: r } = t.stats, i = r.end - r.first;
		W(i) && (this.lastLevelLoadSec = i / 1e3), t.details.live ? this.bwEstimator.update(n.abrEwmaSlowLive, n.abrEwmaFastLive) : this.bwEstimator.update(n.abrEwmaSlowVoD, n.abrEwmaFastVoD), this.timer > -1 && this._abandonRulesCheck(t.levelInfo);
	}
	onFragLoaded(e, { frag: t, part: n }) {
		let r = n ? n.stats : t.stats;
		if (t.type === Y.MAIN && this.bwEstimator.sampleTTFB(r.loading.first - r.loading.start), !this.ignoreFragment(t)) {
			if (this.clearTimer(), t.level === this._nextAutoLevel && (this._nextAutoLevel = -1), this.firstSelection = -1, this.hls.config.abrMaxWithRealBitrate) {
				let e = n ? n.duration : t.duration, i = this.hls.levels[t.level], a = (i.loaded ? i.loaded.bytes : 0) + r.loaded, o = (i.loaded ? i.loaded.duration : 0) + e;
				i.loaded = {
					bytes: a,
					duration: o
				}, i.realBitrate = Math.round(8 * a / o);
			}
			if (t.bitrateTest) {
				let e = {
					stats: r,
					frag: t,
					part: n,
					id: t.type
				};
				this.onFragBuffered(q.FRAG_BUFFERED, e), t.bitrateTest = !1;
			} else this.lastLoadedFragLevel = t.level;
		}
	}
	onFragBuffered(e, t) {
		let { frag: n, part: r } = t, i = r != null && r.stats.loaded ? r.stats : n.stats;
		if (i.aborted || this.ignoreFragment(n)) return;
		let a = i.parsing.end - i.loading.start - Math.min(i.loading.first - i.loading.start, this.bwEstimator.getEstimateTTFB());
		this.bwEstimator.sample(a, i.loaded), i.bwEstimate = this.getBwEstimate(), this.bitrateTestDelay = n.bitrateTest ? a / 1e3 : 0;
	}
	ignoreFragment(e) {
		return e.type !== Y.MAIN || e.sn === "initSegment";
	}
	clearTimer() {
		this.timer > -1 && (self.clearInterval(this.timer), this.timer = -1);
	}
	get firstAutoLevel() {
		let { maxAutoLevel: e, minAutoLevel: t } = this.hls, n = this.getBwEstimate(), r = this.hls.config.maxStarvationDelay, i = this.findBestLevel(n, t, e, 0, r, 1, 1);
		if (i > -1) return i;
		let a = this.hls.firstLevel, o = Math.min(Math.max(a, t), e);
		return this.warn(`Could not find best starting auto level. Defaulting to first in playlist ${a} clamped to ${o}`), o;
	}
	get forcedAutoLevel() {
		return this.nextAutoLevelKey ? -1 : this._nextAutoLevel;
	}
	get nextAutoLevel() {
		let e = this.forcedAutoLevel, t = this.bwEstimator.canEstimate(), n = this.lastLoadedFragLevel > -1;
		if (e !== -1 && (!t || !n || this.nextAutoLevelKey === this.getAutoLevelKey())) return e;
		let r = t && n ? this.getNextABRAutoLevel() : this.firstAutoLevel;
		if (e !== -1) {
			let t = this.hls.levels;
			if (t.length > Math.max(e, r) && t[e].loadError <= t[r].loadError) return e;
		}
		return this._nextAutoLevel = r, this.nextAutoLevelKey = this.getAutoLevelKey(), r;
	}
	getAutoLevelKey() {
		return `${this.getBwEstimate()}_${this.getStarvationDelay().toFixed(2)}`;
	}
	getNextABRAutoLevel() {
		let { fragCurrent: e, partCurrent: t, hls: n } = this;
		if (n.levels.length <= 1) return n.loadLevel;
		let { maxAutoLevel: r, config: i, minAutoLevel: a } = n, o = t ? t.duration : e ? e.duration : 0, s = this.getBwEstimate(), c = this.getStarvationDelay(), l = i.abrBandWidthFactor, u = i.abrBandWidthUpFactor;
		if (c) {
			let e = this.findBestLevel(s, a, r, c, 0, l, u);
			if (e >= 0) return this.rebufferNotice = -1, e;
		}
		let d = o ? Math.min(o, i.maxStarvationDelay) : i.maxStarvationDelay;
		if (!c) {
			let e = this.bitrateTestDelay;
			e && (d = (o ? Math.min(o, i.maxLoadingDelay) : i.maxLoadingDelay) - e, this.info(`bitrate test took ${Math.round(1e3 * e)}ms, set first fragment max fetchDuration to ${Math.round(1e3 * d)} ms`), l = u = 1);
		}
		let f = this.findBestLevel(s, a, r, c, d, l, u);
		if (this.rebufferNotice !== f && (this.rebufferNotice = f, this.info(`${c ? "rebuffering expected" : "buffer is empty"}, optimal quality level ${f}`)), f > -1) return f;
		let p = n.levels[a], m = n.loadLevelObj;
		return m && p?.bitrate < m.bitrate ? a : n.loadLevel;
	}
	getStarvationDelay() {
		let e = this.hls, t = e.media;
		if (!t) return Infinity;
		let n = t && t.playbackRate !== 0 ? Math.abs(t.playbackRate) : 1, r = e.mainForwardBufferInfo;
		return (r ? r.len : 0) / n;
	}
	getBwEstimate() {
		return this.bwEstimator.canEstimate() ? this.bwEstimator.getEstimate() : this.hls.config.abrEwmaDefaultEstimate;
	}
	findBestLevel(e, t, n, r, i, a, o) {
		var s;
		let c = r + i, l = this.lastLoadedFragLevel, u = l === -1 ? this.hls.firstLevel : l, { fragCurrent: d, partCurrent: f } = this, { levels: p, allAudioTracks: m, loadLevel: h, config: g } = this.hls;
		if (p.length === 1) return 0;
		let _ = p[u], v = !!((s = this.hls.latestLevelDetails) != null && s.live), y = h === -1 || l === -1, b, x = "SDR", S = _?.frameRate || 0, { audioPreference: C, videoPreference: w } = g, T = this.audioTracksByGroup ||= Ri(m), E = -1;
		if (y) {
			if (this.firstSelection !== -1) return this.firstSelection;
			let r = Ii(this.codecTiers ||= zi(p, T, t, n), x, e, C, w), { codecSet: i, videoRanges: a, minFramerate: o, minBitrate: s, minIndex: c, preferHDR: l } = r;
			E = c, b = i, x = l ? a[a.length - 1] : a[0], S = o, e = Math.max(e, s), this.log(`picked start tier ${Fi(r)}`);
		} else b = _?.codecSet, x = _?.videoRange;
		let D = f ? f.duration : d ? d.duration : 0, O = this.bwEstimator.getEstimateTTFB() / 1e3, k = [];
		for (let s = n; s >= t; s--) {
			var A;
			let t = p[s], d = s > u;
			if (!t) continue;
			if (g.useMediaCapabilities && !t.supportedResult && !t.supportedPromise) {
				let n = navigator.mediaCapabilities;
				typeof n?.decodingInfo == "function" && gi(t, T, x, S, e, C) ? (t.supportedPromise = _i(t, T, n, this.supportedCache), t.supportedPromise.then((e) => {
					if (!this.hls) return;
					t.supportedResult = e;
					let n = this.hls.levels, r = n.indexOf(t);
					e.error ? this.warn(`MediaCapabilities decodingInfo error: "${e.error}" for level ${r} ${Fi(e)}`) : e.supported ? e.decodingInfoResults.some((e) => e.smooth === !1 || e.powerEfficient === !1) && this.log(`MediaCapabilities decodingInfo for level ${r} not smooth or powerEfficient: ${Fi(e)}`) : (this.warn(`Unsupported MediaCapabilities decodingInfo result for level ${r} ${Fi(e)}`), r > -1 && n.length > 1 && (this.log(`Removing unsupported level ${r}`), this.hls.removeLevel(r), this.hls.loadLevel === -1 && (this.hls.nextLoadLevel = 0)));
				}).catch((e) => {
					this.warn(`Error handling MediaCapabilities decodingInfo: ${e}`);
				})) : t.supportedResult = mi;
			}
			if ((b && t.codecSet !== b || x && t.videoRange !== x || d && S > t.frameRate || !d && S > 0 && S < t.frameRate || (A = t.supportedResult) != null && (A = A.decodingInfoResults) != null && A.some((e) => e.smooth === !1)) && (!y || s !== E)) {
				k.push(s);
				continue;
			}
			let m = t.details, _ = (f ? m?.partTarget : m?.averagetargetduration) || D, w;
			w = d ? o * e : a * e;
			let j = D && r >= D * 2 && i === 0 ? t.averageBitrate : t.maxBitrate, M = this.getTimeToLoadFrag(O, w, j * _, m === void 0);
			if (w >= j && (s === l || t.loadError === 0 && t.fragmentError === 0) && (M <= O || !W(M) || v && !this.bitrateTestDelay || M < c)) {
				let e = this.forcedAutoLevel;
				return s !== h && (e === -1 || e !== h) && (k.length && this.trace(`Skipped level(s) ${k.join(",")} of ${n} max with CODECS and VIDEO-RANGE:"${p[k[0]].codecs}" ${p[k[0]].videoRange}; not compatible with "${b}" ${x}`), this.info(`switch candidate:${u}->${s} adjustedbw(${Math.round(w)})-bitrate=${Math.round(w - j)} ttfb:${O.toFixed(1)} avgDuration:${_.toFixed(1)} maxFetchDuration:${c.toFixed(1)} fetchDuration:${M.toFixed(1)} firstSelection:${y} codecSet:${t.codecSet} videoRange:${t.videoRange} hls.loadLevel:${h}`)), y && (this.firstSelection = s), s;
			}
		}
		return -1;
	}
	set nextAutoLevel(e) {
		let t = this.deriveNextAutoLevel(e);
		this._nextAutoLevel !== t && (this.nextAutoLevelKey = "", this._nextAutoLevel = t);
	}
	deriveNextAutoLevel(e) {
		let { maxAutoLevel: t, minAutoLevel: n } = this.hls;
		return Math.min(Math.max(e, n), t);
	}
}, Xi = { search: function(e, t) {
	let n = 0, r = e.length - 1, i = null, a = null;
	for (; n <= r;) {
		i = (n + r) / 2 | 0, a = e[i];
		let o = t(a);
		if (o > 0) n = i + 1;
		else if (o < 0) r = i - 1;
		else return a;
	}
	return null;
} };
function Zi(e, t, n) {
	if (t === null || !Array.isArray(e) || !e.length || !W(t) || t < (e[0].programDateTime || 0) || t >= (e[e.length - 1].endProgramDateTime || 0)) return null;
	for (let r = 0; r < e.length; ++r) {
		let i = e[r];
		if (ta(t, n, i)) return i;
	}
	return null;
}
function Qi(e, t, n = 0, r = 0, i = .005) {
	let a = null;
	if (e) {
		a = t[1 + e.sn - t[0].sn] || null;
		let r = e.endDTS - n;
		r > 0 && r < 15e-7 && (n += 15e-7), a && e.level !== a.level && a.end <= e.end && (a = t[2 + e.sn - t[0].sn] || null);
	} else n === 0 && t[0].start === 0 && (a = t[0]);
	if (a && ((!e || e.level === a.level) && ea(n, r, a) === 0 || $i(a, e, Math.min(i, r)))) return a;
	let o = Xi.search(t, ea.bind(null, n, r));
	return o && (o !== e || !a) ? o : a;
}
function $i(e, t, n) {
	if (t && t.start === 0 && t.level < e.level && (t.endPTS || 0) > 0) {
		let r = t.tagList.reduce((e, t) => (t[0] === "INF" && (e += parseFloat(t[1])), e), n);
		return e.start <= r;
	}
	return !1;
}
function ea(e = 0, t = 0, n) {
	if (n.start <= e && n.start + n.duration > e) return 0;
	let r = Math.min(t, n.duration + (n.deltaPTS ? n.deltaPTS : 0));
	return n.start + n.duration - r <= e ? 1 : n.start - r > e && n.start ? -1 : 0;
}
function ta(e, t, n) {
	let r = Math.min(t, n.duration + (n.deltaPTS ? n.deltaPTS : 0)) * 1e3;
	return (n.endProgramDateTime || 0) - r > e;
}
function na(e, t, n) {
	if (e && e.startCC <= t && e.endCC >= t) {
		let r = e.fragments, { fragmentHint: i } = e;
		i && (r = r.concat(i));
		let a;
		return Xi.search(r, (e) => e.cc < t ? 1 : e.cc > t ? -1 : (a = e, e.end <= n ? 1 : e.start > n ? -1 : 0)), a || null;
	}
	return null;
}
function ra(e) {
	switch (e.details) {
		case K.FRAG_LOAD_TIMEOUT:
		case K.KEY_LOAD_TIMEOUT:
		case K.LEVEL_LOAD_TIMEOUT:
		case K.MANIFEST_LOAD_TIMEOUT: return !0;
	}
	return !1;
}
function ia(e) {
	return e.details.startsWith("key");
}
function aa(e) {
	return ia(e) && !!e.frag && !e.frag.decryptdata;
}
function oa(e, t) {
	let n = ra(t);
	return e.default[`${n ? "timeout" : "error"}Retry`];
}
function sa(e, t) {
	let n = e.backoff === "linear" ? 1 : 2 ** t;
	return Math.min(n * e.retryDelayMs, e.maxRetryDelayMs);
}
function ca(e) {
	return Ln(Ln({}, e), {
		errorRetry: null,
		timeoutRetry: null
	});
}
function la(e, t, n, r) {
	if (!e) return !1;
	let i = r?.code, a = t < e.maxNumRetry && (ua(i) || !!n);
	return e.shouldRetry ? e.shouldRetry(e, t, n, r, a) : a;
}
function ua(e) {
	return da(e) || !!e && (e < 400 || e > 499);
}
function da(e) {
	return e === 0 && navigator.onLine === !1;
}
var fa = {
	DoNothing: 0,
	SendEndCallback: 1,
	SendAlternateToPenaltyBox: 2,
	RemoveAlternatePermanently: 3,
	InsertDiscontinuity: 4,
	RetryRequest: 5
}, pa = {
	None: 0,
	MoveAllAlternatesMatchingHost: 1,
	MoveAllAlternatesMatchingHDCP: 2,
	MoveAllAlternatesMatchingKey: 4,
	SwitchToSDR: 8
}, ma = class extends Bn {
	constructor(e) {
		super("error-controller", e.logger), this.hls = void 0, this.playlistError = 0, this.hls = e, this.registerListeners();
	}
	registerListeners() {
		let e = this.hls;
		e.on(q.ERROR, this.onError, this), e.on(q.MANIFEST_LOADING, this.onManifestLoading, this), e.on(q.LEVEL_UPDATED, this.onLevelUpdated, this);
	}
	unregisterListeners() {
		let e = this.hls;
		e && (e.off(q.ERROR, this.onError, this), e.off(q.ERROR, this.onErrorOut, this), e.off(q.MANIFEST_LOADING, this.onManifestLoading, this), e.off(q.LEVEL_UPDATED, this.onLevelUpdated, this));
	}
	destroy() {
		this.unregisterListeners(), this.hls = null;
	}
	startLoad(e) {}
	stopLoad() {
		this.playlistError = 0;
	}
	getVariantLevelIndex(e) {
		return e?.type === Y.MAIN ? e.level : this.getVariantIndex();
	}
	getVariantIndex() {
		var e;
		let t = this.hls, n = t.currentLevel;
		return (e = t.loadLevelObj) != null && e.details || n === -1 ? t.loadLevel : n;
	}
	variantHasKey(e, t) {
		if (e) {
			var n;
			if ((n = e.details) != null && n.hasKey(t)) return !0;
			let r = e.audioGroups;
			if (r) return this.hls.allAudioTracks.filter((e) => r.indexOf(e.groupId) >= 0).some((e) => e.details?.hasKey(t));
		}
		return !1;
	}
	onManifestLoading() {
		this.playlistError = 0;
	}
	onLevelUpdated() {
		this.playlistError = 0;
	}
	onError(e, t) {
		var n;
		if (t.fatal) return;
		let r = this.hls, i = t.context;
		switch (t.details) {
			case K.FRAG_LOAD_ERROR:
			case K.FRAG_LOAD_TIMEOUT:
			case K.KEY_LOAD_ERROR:
			case K.KEY_LOAD_TIMEOUT:
				t.errorAction = this.getFragRetryOrSwitchAction(t);
				return;
			case K.FRAG_PARSING_ERROR: if ((n = t.frag) != null && n.gap) {
				t.errorAction = ha();
				return;
			}
			case K.FRAG_GAP:
			case K.FRAG_DECRYPT_ERROR:
				t.errorAction = this.getFragRetryOrSwitchAction(t), t.errorAction.action = fa.SendAlternateToPenaltyBox;
				return;
			case K.LEVEL_EMPTY_ERROR:
			case K.LEVEL_PARSING_ERROR:
				{
					var a;
					let e = t.parent === Y.MAIN ? t.level : r.loadLevel;
					t.details === K.LEVEL_EMPTY_ERROR && (a = t.context) != null && (a = a.levelDetails) != null && a.live ? t.errorAction = this.getPlaylistRetryOrSwitchAction(t, e) : (t.levelRetry = !1, t.errorAction = this.getLevelSwitchAction(t, e));
				}
				return;
			case K.LEVEL_LOAD_ERROR:
			case K.LEVEL_LOAD_TIMEOUT:
				typeof i?.level == "number" && (t.errorAction = this.getPlaylistRetryOrSwitchAction(t, i.level));
				return;
			case K.AUDIO_TRACK_LOAD_ERROR:
			case K.AUDIO_TRACK_LOAD_TIMEOUT:
			case K.SUBTITLE_LOAD_ERROR:
			case K.SUBTITLE_TRACK_LOAD_TIMEOUT:
				if (i) {
					let e = r.loadLevelObj;
					if (e && (i.type === J.AUDIO_TRACK && e.hasAudioGroup(i.groupId) || i.type === J.SUBTITLE_TRACK && e.hasSubtitleGroup(i.groupId))) {
						t.errorAction = this.getPlaylistRetryOrSwitchAction(t, r.loadLevel), t.errorAction.action = fa.SendAlternateToPenaltyBox, t.errorAction.flags = pa.MoveAllAlternatesMatchingHost;
						return;
					}
				}
				return;
			case K.KEY_SYSTEM_STATUS_OUTPUT_RESTRICTED:
				t.errorAction = {
					action: fa.SendAlternateToPenaltyBox,
					flags: pa.MoveAllAlternatesMatchingHDCP
				};
				return;
			case K.KEY_SYSTEM_SESSION_UPDATE_FAILED:
			case K.KEY_SYSTEM_STATUS_INTERNAL_ERROR:
			case K.KEY_SYSTEM_NO_SESSION:
				t.errorAction = {
					action: fa.SendAlternateToPenaltyBox,
					flags: pa.MoveAllAlternatesMatchingKey
				};
				return;
			case K.BUFFER_ADD_CODEC_ERROR:
			case K.REMUX_ALLOC_ERROR:
			case K.BUFFER_APPEND_ERROR:
				t.errorAction ||= this.getLevelSwitchAction(t, t.level ?? r.loadLevel);
				return;
			case K.INTERNAL_EXCEPTION:
			case K.BUFFER_APPENDING_ERROR:
			case K.BUFFER_FULL_ERROR:
			case K.LEVEL_SWITCH_ERROR:
			case K.BUFFER_STALLED_ERROR:
			case K.BUFFER_SEEK_OVER_HOLE:
			case K.BUFFER_NUDGE_ON_STALL:
				t.errorAction = ha();
				return;
		}
		t.type === G.KEY_SYSTEM_ERROR && (t.levelRetry = !1, t.errorAction = ha());
	}
	getPlaylistRetryOrSwitchAction(e, t) {
		let n = this.hls, r = oa(n.config.playlistLoadPolicy, e), i = this.playlistError++;
		if (la(r, i, ra(e), e.response)) return {
			action: fa.RetryRequest,
			flags: pa.None,
			retryConfig: r,
			retryCount: i
		};
		let a = this.getLevelSwitchAction(e, t);
		return r && (a.retryConfig = r, a.retryCount = i), a;
	}
	getFragRetryOrSwitchAction(e) {
		let t = this.hls, n = this.getVariantLevelIndex(e.frag), r = t.levels[n], { fragLoadPolicy: i, keyLoadPolicy: a } = t.config, o = oa(ia(e) ? a : i, e), s = t.levels.reduce((e, t) => e + t.fragmentError, 0);
		if (r && (e.details !== K.FRAG_GAP && r.fragmentError++, !aa(e) && la(o, s, ra(e), e.response))) return {
			action: fa.RetryRequest,
			flags: pa.None,
			retryConfig: o,
			retryCount: s
		};
		let c = this.getLevelSwitchAction(e, n);
		return o && (c.retryConfig = o, c.retryCount = s), c;
	}
	getLevelSwitchAction(e, t) {
		let n = this.hls;
		t ??= n.loadLevel;
		let r = this.hls.levels[t];
		if (r) {
			let t = e.details;
			r.loadError++, t === K.BUFFER_APPEND_ERROR && r.fragmentError++;
			let o = -1, { levels: s, loadLevel: c, minAutoLevel: l, maxAutoLevel: u } = n;
			!n.autoLevelEnabled && !n.config.preserveManualLevelOnError && (n.loadLevel = -1);
			let d = e.frag?.type, f = (d === Y.AUDIO && t === K.FRAG_PARSING_ERROR || e.sourceBufferName === "audio" && (t === K.BUFFER_ADD_CODEC_ERROR || t === K.BUFFER_APPEND_ERROR)) && s.some(({ audioCodec: e }) => r.audioCodec !== e), p = e.sourceBufferName === "video" && (t === K.BUFFER_ADD_CODEC_ERROR || t === K.BUFFER_APPEND_ERROR) && s.some(({ codecSet: e, audioCodec: t }) => r.codecSet !== e && r.audioCodec === t), { type: m, groupId: h } = e.context ?? {};
			for (let n = s.length; n--;) {
				let g = (n + c) % s.length;
				if (g !== c && g >= l && g <= u && s[g].loadError === 0) {
					var i, a;
					let n = s[g];
					if (t === K.FRAG_GAP && d === Y.MAIN && e.frag) {
						let t = s[g].details;
						if (t) {
							let n = Qi(e.frag, t.fragments, e.frag.start);
							if (n != null && n.gap) continue;
						}
					} else if (m === J.AUDIO_TRACK && n.hasAudioGroup(h) || m === J.SUBTITLE_TRACK && n.hasSubtitleGroup(h)) continue;
					else if (d === Y.AUDIO && (i = r.audioGroups) != null && i.some((e) => n.hasAudioGroup(e)) || d === Y.SUBTITLE && (a = r.subtitleGroups) != null && a.some((e) => n.hasSubtitleGroup(e)) || f && r.audioCodec === n.audioCodec || p && r.codecSet === n.codecSet || !f && r.codecSet !== n.codecSet) continue;
					o = g;
					break;
				}
			}
			if (o > -1 && n.loadLevel !== o) return e.levelRetry = !0, this.playlistError = 0, {
				action: fa.SendAlternateToPenaltyBox,
				flags: pa.None,
				nextAutoLevel: o
			};
		}
		return {
			action: fa.SendAlternateToPenaltyBox,
			flags: pa.MoveAllAlternatesMatchingHost
		};
	}
	onErrorOut(e, t) {
		switch (t.errorAction?.action) {
			case fa.DoNothing: break;
			case fa.SendAlternateToPenaltyBox:
				this.sendAlternateToPenaltyBox(t), !t.errorAction.resolved && t.details !== K.FRAG_GAP ? t.fatal = !0 : /MediaSource readyState: ended/.test(t.error.message) && (this.warn(`MediaSource ended after "${t.sourceBufferName}" sourceBuffer append error. Attempting to recover from media error.`), this.hls.recoverMediaError());
				break;
			case fa.RetryRequest:
		}
		t.fatal && this.hls.stopLoad();
	}
	sendAlternateToPenaltyBox(e) {
		let t = this.hls, n = e.errorAction;
		if (!n) return;
		let { flags: r } = n, i = n.nextAutoLevel;
		switch (r) {
			case pa.None:
				this.switchLevel(e, i);
				break;
			case pa.MoveAllAlternatesMatchingHDCP: {
				let r = this.getVariantLevelIndex(e.frag), i = t.levels[r]?.attrs["HDCP-LEVEL"];
				if (n.hdcpLevel = i, i === "NONE") this.warn("HDCP policy resticted output with HDCP-LEVEL=NONE");
				else if (i) {
					t.maxHdcpLevel = Ci[Ci.indexOf(i) - 1], n.resolved = !0, this.warn(`Restricting playback to HDCP-LEVEL of "${t.maxHdcpLevel}" or lower`);
					break;
				}
			}
			case pa.MoveAllAlternatesMatchingKey: {
				let t = e.decryptdata;
				if (t) {
					let r = this.hls.levels, i = r.length;
					for (let n = i; n--;) this.variantHasKey(r[n], t) && (this.log(`Banned key found in level ${n} (${r[n].bitrate}bps) or audio group "${r[n].audioGroups?.join(",")}" (${e.frag?.type} fragment) ${$n(t.keyId || [])}`), r[n].fragmentError++, r[n].loadError++, this.log(`Removing level ${n} with key error (${e.error})`), this.hls.removeLevel(n));
					let a = e.frag;
					if (this.hls.levels.length < i) n.resolved = !0;
					else if (a && a.type !== Y.MAIN) {
						let e = a.decryptdata;
						e && !t.matches(e) && (n.resolved = !0);
					}
				}
				break;
			}
		}
		n.resolved || this.switchLevel(e, i);
	}
	switchLevel(e, t) {
		if (t !== void 0 && e.errorAction && (this.warn(`switching to level ${t} after ${e.details}`), this.hls.nextAutoLevel = t, e.errorAction.resolved = !0, this.hls.nextLoadLevel = this.hls.nextAutoLevel, e.details === K.BUFFER_ADD_CODEC_ERROR && e.mimeType && e.sourceBufferName !== "audiovideo")) {
			let t = di(e.mimeType), n = this.hls.levels;
			for (let r = n.length; r--;) n[r][`${e.sourceBufferName}Codec`] === t && (this.log(`Removing level ${r} for ${e.details} ("${t}" not supported)`), this.hls.removeLevel(r));
		}
	}
};
function ha(e) {
	let t = {
		action: fa.DoNothing,
		flags: pa.None
	};
	return e && (t.resolved = !0), t;
}
var ga = {
	NOT_LOADED: "NOT_LOADED",
	APPENDING: "APPENDING",
	PARTIAL: "PARTIAL",
	OK: "OK"
}, _a = class {
	constructor(e) {
		this.activePartLists = Object.create(null), this.endListFragments = Object.create(null), this.fragments = Object.create(null), this.timeRanges = Object.create(null), this.bufferPadding = .2, this.hls = void 0, this.hasGaps = !1, this.hls = e, this._registerListeners();
	}
	_registerListeners() {
		let { hls: e } = this;
		e && (e.on(q.MANIFEST_LOADING, this.onManifestLoading, this), e.on(q.BUFFER_APPENDED, this.onBufferAppended, this), e.on(q.FRAG_BUFFERED, this.onFragBuffered, this), e.on(q.FRAG_LOADED, this.onFragLoaded, this));
	}
	_unregisterListeners() {
		let { hls: e } = this;
		e && (e.off(q.MANIFEST_LOADING, this.onManifestLoading, this), e.off(q.BUFFER_APPENDED, this.onBufferAppended, this), e.off(q.FRAG_BUFFERED, this.onFragBuffered, this), e.off(q.FRAG_LOADED, this.onFragLoaded, this));
	}
	destroy() {
		this._unregisterListeners(), this.hls = this.fragments = this.activePartLists = this.endListFragments = this.timeRanges = null;
	}
	getAppendedFrag(e, t) {
		let n = this.activePartLists[t];
		if (n) for (let t = n.length; t--;) {
			let r = n[t];
			if (!r) break;
			if (r.start <= e && e <= r.end && r.loaded) return r;
		}
		return this.getBufferedFrag(e, t);
	}
	getBufferedFrag(e, t) {
		return this.getFragAtPos(e, t, !0);
	}
	getFragAtPos(e, t, n) {
		let { fragments: r } = this, i = Object.keys(r);
		for (let a = i.length; a--;) {
			let o = r[i[a]];
			if (o?.body.type === t && (!n || o.buffered)) {
				let t = o.body;
				if (t.start <= e && e <= t.end) return t;
			}
		}
		return null;
	}
	detectEvictedFragments(e, t, n, r, i) {
		this.timeRanges && (this.timeRanges[e] = t);
		let a = r?.fragment.sn || -1;
		Object.keys(this.fragments).forEach((r) => {
			let o = this.fragments[r];
			if (!o || a >= o.body.sn) return;
			if (!o.buffered && (!o.loaded || i)) {
				o.body.type === n && this.removeFragment(o.body);
				return;
			}
			let s = o.range[e];
			s && (s.time.length === 0 ? this.removeFragment(o.body) : s.time.some((e) => {
				let n = !this.isTimeBuffered(e.startPTS, e.endPTS, t);
				return n && this.removeFragment(o.body), n;
			}));
		});
	}
	detectPartialFragments(e) {
		let t = this.timeRanges;
		if (!t || e.frag.sn === "initSegment") return;
		let n = e.frag, r = ya(n), i = this.fragments[r];
		if (!i || i.buffered && n.gap) return;
		let a = !n.relurl;
		Object.keys(t).forEach((r) => {
			let o = n.elementaryStreams[r];
			if (!o) return;
			let s = t[r], c = a || o.partial === !0;
			i.range[r] = this.getBufferedTimes(n, e.part, c, s);
		}), i.loaded = null, Object.keys(i.range).length ? (this.bufferedEnd(i, n), va(i) || this.removeParts(n.sn - 1, n.type)) : this.removeFragment(i.body);
	}
	bufferedEnd(e, t) {
		e.buffered = !0, (e.body.endList = t.endList || e.body.endList) && (this.endListFragments[e.body.type] = e);
	}
	removeParts(e, t) {
		let n = this.activePartLists[t];
		n && (this.activePartLists[t] = ba(n, (t) => t.fragment.sn >= e));
	}
	fragBuffered(e, t) {
		let n = ya(e), r = this.fragments[n];
		!r && t && (r = this.fragments[n] = {
			body: e,
			appendedPTS: null,
			loaded: null,
			buffered: !1,
			range: Object.create(null)
		}, e.gap && (this.hasGaps = !0)), r && (r.loaded = null, this.bufferedEnd(r, e));
	}
	getBufferedTimes(e, t, n, r) {
		let i = {
			time: [],
			partial: n
		}, a = e.start, o = e.end, s = e.minEndPTS || o, c = e.maxStartPTS || a;
		for (let e = 0; e < r.length; e++) {
			let t = r.start(e) - this.bufferPadding, n = r.end(e) + this.bufferPadding;
			if (c >= t && s <= n) {
				i.time.push({
					startPTS: Math.max(a, r.start(e)),
					endPTS: Math.min(o, r.end(e))
				});
				break;
			}
			if (a < n && o > t) {
				let t = Math.max(a, r.start(e)), n = Math.min(o, r.end(e));
				n > t && (i.partial = !0, i.time.push({
					startPTS: t,
					endPTS: n
				}));
			} else if (o <= t) break;
		}
		return i;
	}
	getPartialFragment(e) {
		let t = null, n, r, i, a = 0, { bufferPadding: o, fragments: s } = this;
		return Object.keys(s).forEach((c) => {
			let l = s[c];
			l && va(l) && (r = l.body.start - o, i = l.body.end + o, e >= r && e <= i && (n = Math.min(e - r, i - e), a <= n && (t = l.body, a = n)));
		}), t;
	}
	isEndListAppended(e) {
		let t = this.endListFragments[e];
		return t !== void 0 && (t.buffered || va(t));
	}
	getState(e) {
		let t = ya(e), n = this.fragments[t];
		return n ? n.buffered ? va(n) ? ga.PARTIAL : ga.OK : ga.APPENDING : ga.NOT_LOADED;
	}
	isTimeBuffered(e, t, n) {
		let r, i;
		for (let a = 0; a < n.length; a++) {
			if (r = n.start(a) - this.bufferPadding, i = n.end(a) + this.bufferPadding, e >= r && t <= i) return !0;
			if (t <= r) return !1;
		}
		return !1;
	}
	onManifestLoading() {
		this.removeAllFragments();
	}
	onFragLoaded(e, t) {
		if (t.frag.sn === "initSegment" || t.frag.bitrateTest) return;
		let n = t.frag, r = t.part ? null : t, i = ya(n);
		this.fragments[i] = {
			body: n,
			appendedPTS: null,
			loaded: r,
			buffered: !1,
			range: Object.create(null)
		};
	}
	onBufferAppended(e, t) {
		let { frag: n, part: r, timeRanges: i, type: a } = t;
		if (n.sn === "initSegment") return;
		let o = n.type;
		if (r) {
			let e = this.activePartLists[o];
			e || (this.activePartLists[o] = e = []), e.push(r);
		}
		this.timeRanges = i;
		let s = i[a];
		this.detectEvictedFragments(a, s, o, r);
	}
	onFragBuffered(e, t) {
		this.detectPartialFragments(t);
	}
	hasFragment(e) {
		let t = ya(e);
		return !!this.fragments[t];
	}
	hasFragments(e) {
		let { fragments: t } = this, n = Object.keys(t);
		if (!e) return n.length > 0;
		for (let r = n.length; r--;) if (t[n[r]]?.body.type === e) return !0;
		return !1;
	}
	hasParts(e) {
		var t;
		return !!((t = this.activePartLists[e]) != null && t.length);
	}
	removeFragmentsInRange(e, t, n, r, i) {
		(!r || this.hasGaps) && Object.keys(this.fragments).forEach((a) => {
			let o = this.fragments[a];
			if (!o) return;
			let s = o.body;
			s.type !== n || r && !s.gap || s.start < t && s.end > e && (o.buffered || i) && this.removeFragment(s);
		});
	}
	removeFragment(e) {
		let t = ya(e);
		e.clearElementaryStreamInfo();
		let n = this.activePartLists[e.type];
		if (n) {
			let t = e.sn;
			this.activePartLists[e.type] = ba(n, (e) => e.fragment.sn !== t);
		}
		delete this.fragments[t], e.endList && delete this.endListFragments[e.type];
	}
	removeAllFragments() {
		var e;
		this.fragments = Object.create(null), this.endListFragments = Object.create(null), this.activePartLists = Object.create(null), this.hasGaps = !1;
		let t = (e = this.hls) == null || (e = e.latestLevelDetails) == null ? void 0 : e.partList;
		t && t.forEach((e) => e.clearElementaryStreamInfo());
	}
};
function va(e) {
	var t, n, r;
	return e.buffered && !!(e.body.gap || (t = e.range.video) != null && t.partial || (n = e.range.audio) != null && n.partial || (r = e.range.audiovideo) != null && r.partial);
}
function ya(e) {
	return `${e.type}_${e.level}_${e.sn}`;
}
function ba(e, t) {
	return e.filter((e) => {
		let n = t(e);
		return n || e.clearElementaryStreamInfo(), n;
	});
}
var xa = {
	cbc: 0,
	ctr: 1
}, Sa = class {
	constructor(e, t, n) {
		this.subtle = void 0, this.aesIV = void 0, this.aesMode = void 0, this.subtle = e, this.aesIV = t, this.aesMode = n;
	}
	decrypt(e, t) {
		switch (this.aesMode) {
			case xa.cbc: return this.subtle.decrypt({
				name: "AES-CBC",
				iv: this.aesIV
			}, t, e);
			case xa.ctr: return this.subtle.decrypt({
				name: "AES-CTR",
				counter: this.aesIV,
				length: 64
			}, t, e);
			default: throw Error(`[AESCrypto] invalid aes mode ${this.aesMode}`);
		}
	}
};
function Ca(e) {
	let t = e.byteLength, n = t && new DataView(e.buffer).getUint8(t - 1);
	return n ? e.slice(0, t - n) : e;
}
var wa = class {
	constructor() {
		this.rcon = [
			0,
			1,
			2,
			4,
			8,
			16,
			32,
			64,
			128,
			27,
			54
		], this.subMix = [
			/* @__PURE__ */ new Uint32Array(256),
			/* @__PURE__ */ new Uint32Array(256),
			/* @__PURE__ */ new Uint32Array(256),
			/* @__PURE__ */ new Uint32Array(256)
		], this.invSubMix = [
			/* @__PURE__ */ new Uint32Array(256),
			/* @__PURE__ */ new Uint32Array(256),
			/* @__PURE__ */ new Uint32Array(256),
			/* @__PURE__ */ new Uint32Array(256)
		], this.sBox = /* @__PURE__ */ new Uint32Array(256), this.invSBox = /* @__PURE__ */ new Uint32Array(256), this.key = /* @__PURE__ */ new Uint32Array(), this.ksRows = 0, this.keySize = 0, this.keySchedule = void 0, this.invKeySchedule = void 0, this.initTable();
	}
	uint8ArrayToUint32Array_(e) {
		let t = new DataView(e), n = /* @__PURE__ */ new Uint32Array(4);
		for (let e = 0; e < 4; e++) n[e] = t.getUint32(e * 4);
		return n;
	}
	initTable() {
		let e = this.sBox, t = this.invSBox, n = this.subMix, r = n[0], i = n[1], a = n[2], o = n[3], s = this.invSubMix, c = s[0], l = s[1], u = s[2], d = s[3], f = /* @__PURE__ */ new Uint32Array(256), p = 0, m = 0, h = 0;
		for (h = 0; h < 256; h++) h < 128 ? f[h] = h << 1 : f[h] = h << 1 ^ 283;
		for (h = 0; h < 256; h++) {
			let n = m ^ m << 1 ^ m << 2 ^ m << 3 ^ m << 4;
			n = n >>> 8 ^ n & 255 ^ 99, e[p] = n, t[n] = p;
			let s = f[p], h = f[s], g = f[h], _ = f[n] * 257 ^ n * 16843008;
			r[p] = _ << 24 | _ >>> 8, i[p] = _ << 16 | _ >>> 16, a[p] = _ << 8 | _ >>> 24, o[p] = _, _ = g * 16843009 ^ h * 65537 ^ s * 257 ^ p * 16843008, c[n] = _ << 24 | _ >>> 8, l[n] = _ << 16 | _ >>> 16, u[n] = _ << 8 | _ >>> 24, d[n] = _, p ? (p = s ^ f[f[f[g ^ s]]], m ^= f[f[m]]) : p = m = 1;
		}
	}
	expandKey(e) {
		let t = this.uint8ArrayToUint32Array_(e), n = !0, r = 0;
		for (; r < t.length && n;) n = t[r] === this.key[r], r++;
		if (n) return;
		this.key = t;
		let i = this.keySize = t.length;
		if (i !== 4 && i !== 6 && i !== 8) throw Error("Invalid aes key size=" + i);
		let a = this.ksRows = (i + 6 + 1) * 4, o, s, c = this.keySchedule = new Uint32Array(a), l = this.invKeySchedule = new Uint32Array(a), u = this.sBox, d = this.rcon, f = this.invSubMix, p = f[0], m = f[1], h = f[2], g = f[3], _, v;
		for (o = 0; o < a; o++) o < i ? _ = c[o] = t[o] : (v = _, o % i === 0 ? (v = v << 8 | v >>> 24, v = u[v >>> 24] << 24 | u[v >>> 16 & 255] << 16 | u[v >>> 8 & 255] << 8 | u[v & 255], v ^= d[o / i | 0] << 24) : i > 6 && o % i === 4 && (v = u[v >>> 24] << 24 | u[v >>> 16 & 255] << 16 | u[v >>> 8 & 255] << 8 | u[v & 255]), c[o] = _ = (c[o - i] ^ v) >>> 0);
		for (s = 0; s < a; s++) o = a - s, v = s & 3 ? c[o] : c[o - 4], s < 4 || o <= 4 ? l[s] = v : l[s] = p[u[v >>> 24]] ^ m[u[v >>> 16 & 255]] ^ h[u[v >>> 8 & 255]] ^ g[u[v & 255]], l[s] = l[s] >>> 0;
	}
	networkToHostOrderSwap(e) {
		return e << 24 | (e & 65280) << 8 | (e & 16711680) >> 8 | e >>> 24;
	}
	decrypt(e, t, n) {
		let r = this.keySize + 6, i = this.invKeySchedule, a = this.invSBox, o = this.invSubMix, s = o[0], c = o[1], l = o[2], u = o[3], d = this.uint8ArrayToUint32Array_(n), f = d[0], p = d[1], m = d[2], h = d[3], g = new Int32Array(e), _ = new Int32Array(g.length), v, y, b, x, S, C, w, T, E, D, O, k, A, j, M = this.networkToHostOrderSwap;
		for (; t < g.length;) {
			for (E = M(g[t]), D = M(g[t + 1]), O = M(g[t + 2]), k = M(g[t + 3]), S = E ^ i[0], C = k ^ i[1], w = O ^ i[2], T = D ^ i[3], A = 4, j = 1; j < r; j++) v = s[S >>> 24] ^ c[C >> 16 & 255] ^ l[w >> 8 & 255] ^ u[T & 255] ^ i[A], y = s[C >>> 24] ^ c[w >> 16 & 255] ^ l[T >> 8 & 255] ^ u[S & 255] ^ i[A + 1], b = s[w >>> 24] ^ c[T >> 16 & 255] ^ l[S >> 8 & 255] ^ u[C & 255] ^ i[A + 2], x = s[T >>> 24] ^ c[S >> 16 & 255] ^ l[C >> 8 & 255] ^ u[w & 255] ^ i[A + 3], S = v, C = y, w = b, T = x, A += 4;
			v = a[S >>> 24] << 24 ^ a[C >> 16 & 255] << 16 ^ a[w >> 8 & 255] << 8 ^ a[T & 255] ^ i[A], y = a[C >>> 24] << 24 ^ a[w >> 16 & 255] << 16 ^ a[T >> 8 & 255] << 8 ^ a[S & 255] ^ i[A + 1], b = a[w >>> 24] << 24 ^ a[T >> 16 & 255] << 16 ^ a[S >> 8 & 255] << 8 ^ a[C & 255] ^ i[A + 2], x = a[T >>> 24] << 24 ^ a[S >> 16 & 255] << 16 ^ a[C >> 8 & 255] << 8 ^ a[w & 255] ^ i[A + 3], _[t] = M(v ^ f), _[t + 1] = M(x ^ p), _[t + 2] = M(b ^ m), _[t + 3] = M(y ^ h), f = E, p = D, m = O, h = k, t += 4;
		}
		return _.buffer;
	}
}, Ta = class {
	constructor(e, t, n) {
		this.subtle = void 0, this.key = void 0, this.aesMode = void 0, this.subtle = e, this.key = t, this.aesMode = n;
	}
	expandKey() {
		let e = Ea(this.aesMode);
		return this.subtle.importKey("raw", this.key, { name: e }, !1, ["encrypt", "decrypt"]);
	}
};
function Ea(e) {
	switch (e) {
		case xa.cbc: return "AES-CBC";
		case xa.ctr: return "AES-CTR";
		default: throw Error(`[FastAESKey] invalid aes mode ${e}`);
	}
}
var Da = 16, Oa = class {
	constructor(e, { removePKCS7Padding: t = !0 } = {}) {
		if (this.logEnabled = !0, this.removePKCS7Padding = void 0, this.subtle = null, this.softwareDecrypter = null, this.key = null, this.fastAesKey = null, this.remainderData = null, this.currentIV = null, this.currentResult = null, this.useSoftware = void 0, this.enableSoftwareAES = void 0, this.enableSoftwareAES = e.enableSoftwareAES, this.removePKCS7Padding = t, t) try {
			let e = self.crypto;
			e && (this.subtle = e.subtle || e.webkitSubtle);
		} catch {}
		this.useSoftware = !this.subtle;
	}
	destroy() {
		this.subtle = null, this.softwareDecrypter = null, this.key = null, this.fastAesKey = null, this.remainderData = null, this.currentIV = null, this.currentResult = null;
	}
	isSync() {
		return this.useSoftware;
	}
	flush() {
		let { currentResult: e, remainderData: t } = this;
		if (!e || t) return this.reset(), null;
		let n = new Uint8Array(e);
		return this.reset(), this.removePKCS7Padding ? Ca(n) : n;
	}
	reset() {
		this.currentResult = null, this.currentIV = null, this.remainderData = null, this.softwareDecrypter &&= null;
	}
	decrypt(e, t, n, r) {
		return this.useSoftware ? new Promise((i, a) => {
			let o = ArrayBuffer.isView(e) ? e : new Uint8Array(e);
			this.softwareDecrypt(o, t, n, r);
			let s = this.flush();
			s ? i(s.buffer) : a(/* @__PURE__ */ Error("[softwareDecrypt] Failed to decrypt data"));
		}) : this.webCryptoDecrypt(new Uint8Array(e), t, n, r);
	}
	softwareDecrypt(e, t, n, r) {
		let { currentIV: i, currentResult: a, remainderData: o } = this;
		if (r !== xa.cbc || t.byteLength !== 16) return Jn.warn("SoftwareDecrypt: can only handle AES-128-CBC"), null;
		this.logOnce("JS AES decrypt"), o && (e = Ir(o, e), this.remainderData = null);
		let s = this.getValidChunk(e);
		if (!s.length) return null;
		i && (n = i);
		let c = this.softwareDecrypter;
		c ||= this.softwareDecrypter = new wa(), c.expandKey(t);
		let l = a;
		return this.currentResult = c.decrypt(s.buffer, 0, n), this.currentIV = s.slice(-16).buffer, l || null;
	}
	webCryptoDecrypt(e, t, n, r) {
		if (this.key !== t || !this.fastAesKey) {
			if (!this.subtle) return Promise.resolve(this.onWebCryptoError(e, t, n, r));
			this.key = t, this.fastAesKey = new Ta(this.subtle, t, r);
		}
		return this.fastAesKey.expandKey().then((t) => this.subtle ? (this.logOnce("WebCrypto AES decrypt"), new Sa(this.subtle, new Uint8Array(n), r).decrypt(e.buffer, t)) : Promise.reject(/* @__PURE__ */ Error("web crypto not initialized"))).catch((i) => (Jn.warn(`[decrypter]: WebCrypto Error, disable WebCrypto API, ${i.name}: ${i.message}`), this.onWebCryptoError(e, t, n, r)));
	}
	onWebCryptoError(e, t, n, r) {
		let i = this.enableSoftwareAES;
		if (i) {
			this.useSoftware = !0, this.logEnabled = !0, this.softwareDecrypt(e, t, n, r);
			let i = this.flush();
			if (i) return i.buffer;
		}
		throw Error("WebCrypto" + (i ? " and softwareDecrypt" : "") + ": failed to decrypt data");
	}
	getValidChunk(e) {
		let t = e, n = e.length - e.length % Da;
		return n !== e.length && (t = e.slice(0, n), this.remainderData = e.slice(n)), t;
	}
	logOnce(e) {
		this.logEnabled &&= (Jn.log(`[decrypter]: ${e}`), !1);
	}
}, ka = 2 ** 17, Aa = class {
	constructor(e) {
		this.config = void 0, this.loader = null, this.partLoadTimeout = -1, this.config = e;
	}
	destroy() {
		this.loader &&= (this.loader.destroy(), null);
	}
	abort() {
		this.loader && this.loader.abort();
	}
	load(e, t) {
		let n = e.url;
		if (!n) return Promise.reject(new Pa({
			type: G.NETWORK_ERROR,
			details: K.FRAG_LOAD_ERROR,
			fatal: !1,
			frag: e,
			error: /* @__PURE__ */ Error(`Fragment does not have a ${n ? "part list" : "url"}`),
			networkDetails: null
		}));
		this.abort();
		let r = this.config, i = r.fLoader, a = r.loader;
		return new Promise((o, s) => {
			if (this.loader && this.loader.destroy(), e.gap) {
				if (e.tagList.some((e) => e[0] === "GAP")) {
					s(Ma(e));
					return;
				}
				e.gap = !1;
			}
			let c = this.loader = i ? new i(r) : new a(r), l = ja(e);
			e.loader = c;
			let u = ca(r.fragLoadPolicy.default), d = {
				loadPolicy: u,
				timeout: u.maxLoadTimeMs,
				maxRetry: 0,
				retryDelay: 0,
				maxRetryDelay: 0,
				highWaterMark: e.sn === "initSegment" ? Infinity : ka
			};
			e.stats = c.stats;
			let f = {
				onSuccess: (t, n, r, i) => {
					this.resetLoader(e, c);
					let a = t.data;
					r.resetIV && e.decryptdata && (e.decryptdata.iv = new Uint8Array(a.slice(0, 16)), a = a.slice(16)), o({
						frag: e,
						part: null,
						payload: a,
						networkDetails: i
					});
				},
				onError: (t, r, i, a) => {
					this.resetLoader(e, c), s(new Pa({
						type: G.NETWORK_ERROR,
						details: K.FRAG_LOAD_ERROR,
						fatal: !1,
						frag: e,
						response: Ln({
							url: n,
							data: void 0
						}, t),
						error: /* @__PURE__ */ Error(`HTTP Error ${t.code} ${t.text}`),
						networkDetails: i,
						stats: a
					}));
				},
				onAbort: (t, n, r) => {
					this.resetLoader(e, c), s(new Pa({
						type: G.NETWORK_ERROR,
						details: K.INTERNAL_ABORTED,
						fatal: !1,
						frag: e,
						error: /* @__PURE__ */ Error("Aborted"),
						networkDetails: r,
						stats: t
					}));
				},
				onTimeout: (t, n, r) => {
					this.resetLoader(e, c), s(new Pa({
						type: G.NETWORK_ERROR,
						details: K.FRAG_LOAD_TIMEOUT,
						fatal: !1,
						frag: e,
						error: /* @__PURE__ */ Error(`Timeout after ${d.timeout}ms`),
						networkDetails: r,
						stats: t
					}));
				}
			};
			t && (f.onProgress = (n, r, i, a) => t({
				frag: e,
				part: null,
				payload: i,
				networkDetails: a
			})), c.load(l, d, f);
		});
	}
	loadPart(e, t, n) {
		this.abort();
		let r = this.config, i = r.fLoader, a = r.loader;
		return new Promise((o, s) => {
			if (this.loader && this.loader.destroy(), e.gap || t.gap) {
				s(Ma(e, t));
				return;
			}
			let c = this.loader = i ? new i(r) : new a(r), l = ja(e, t);
			e.loader = c;
			let u = ca(r.fragLoadPolicy.default), d = {
				loadPolicy: u,
				timeout: u.maxLoadTimeMs,
				maxRetry: 0,
				retryDelay: 0,
				maxRetryDelay: 0,
				highWaterMark: ka
			};
			t.stats = c.stats, c.load(l, d, {
				onSuccess: (r, i, a, s) => {
					this.resetLoader(e, c), this.updateStatsFromPart(e, t);
					let l = {
						frag: e,
						part: t,
						payload: r.data,
						networkDetails: s
					};
					n(l), o(l);
				},
				onError: (n, r, i, a) => {
					this.resetLoader(e, c), s(new Pa({
						type: G.NETWORK_ERROR,
						details: K.FRAG_LOAD_ERROR,
						fatal: !1,
						frag: e,
						part: t,
						response: Ln({
							url: l.url,
							data: void 0
						}, n),
						error: /* @__PURE__ */ Error(`HTTP Error ${n.code} ${n.text}`),
						networkDetails: i,
						stats: a
					}));
				},
				onAbort: (n, r, i) => {
					e.stats.aborted = t.stats.aborted, this.resetLoader(e, c), s(new Pa({
						type: G.NETWORK_ERROR,
						details: K.INTERNAL_ABORTED,
						fatal: !1,
						frag: e,
						part: t,
						error: /* @__PURE__ */ Error("Aborted"),
						networkDetails: i,
						stats: n
					}));
				},
				onTimeout: (n, r, i) => {
					this.resetLoader(e, c), s(new Pa({
						type: G.NETWORK_ERROR,
						details: K.FRAG_LOAD_TIMEOUT,
						fatal: !1,
						frag: e,
						part: t,
						error: /* @__PURE__ */ Error(`Timeout after ${d.timeout}ms`),
						networkDetails: i,
						stats: n
					}));
				}
			});
		});
	}
	updateStatsFromPart(e, t) {
		let n = e.stats, r = t.stats, i = r.total;
		if (n.loaded += r.loaded, i) {
			let r = Math.round(e.duration / t.duration), a = Math.min(Math.round(n.loaded / i), r), o = (r - a) * Math.round(n.loaded / a);
			n.total = n.loaded + o;
		} else n.total = Math.max(n.loaded, n.total);
		let a = n.loading, o = r.loading;
		a.start ? a.first += o.first - o.start : (a.start = o.start, a.first = o.first), a.end = o.end;
	}
	resetLoader(e, t) {
		e.loader = null, this.loader === t && (self.clearTimeout(this.partLoadTimeout), this.loader = null), t.destroy();
	}
};
function ja(e, t = null) {
	let n = t || e, r = {
		frag: e,
		part: t,
		responseType: "arraybuffer",
		url: n.url,
		headers: {},
		rangeStart: 0,
		rangeEnd: 0
	}, i = n.byteRangeStartOffset, a = n.byteRangeEndOffset;
	if (W(i) && W(a)) {
		let t = i, n = a;
		if (e.sn === "initSegment" && Na(e.decryptdata?.method)) {
			let e = a - i;
			e % 16 && (n = a + (16 - e % 16)), i !== 0 && (r.resetIV = !0, t = i - 16);
		}
		r.rangeStart = t, r.rangeEnd = n;
	}
	return r;
}
function Ma(e, t) {
	let n = /* @__PURE__ */ Error(`GAP ${e.gap ? "tag" : "attribute"} found`), r = {
		type: G.MEDIA_ERROR,
		details: K.FRAG_GAP,
		fatal: !1,
		frag: e,
		error: n,
		networkDetails: null
	};
	return t && (r.part = t), (t || e).stats.aborted = !0, new Pa(r);
}
function Na(e) {
	return e === "AES-128" || e === "AES-256";
}
var Pa = class extends Error {
	constructor(e) {
		super(e.error.message), this.data = void 0, this.data = e;
	}
}, Fa = class extends Bn {
	constructor(e, t) {
		super(e, t), this._boundTick = void 0, this._tickTimer = null, this._tickInterval = null, this._tickCallCount = 0, this._boundTick = this.tick.bind(this);
	}
	destroy() {
		this.onHandlerDestroying(), this.onHandlerDestroyed();
	}
	onHandlerDestroying() {
		this.clearNextTick(), this.clearInterval();
	}
	onHandlerDestroyed() {}
	hasInterval() {
		return !!this._tickInterval;
	}
	hasNextTick() {
		return !!this._tickTimer;
	}
	setInterval(e) {
		return !this._tickInterval && (this._tickCallCount = 0, this._tickInterval = self.setInterval(this._boundTick, e), !0);
	}
	clearInterval() {
		return this._tickInterval ? (self.clearInterval(this._tickInterval), this._tickInterval = null, !0) : !1;
	}
	clearNextTick() {
		return this._tickTimer ? (self.clearTimeout(this._tickTimer), this._tickTimer = null, !0) : !1;
	}
	tick() {
		this._tickCallCount++, this._tickCallCount === 1 && (this.doTick(), this._tickCallCount > 1 && this.tickImmediate(), this._tickCallCount = 0);
	}
	tickImmediate() {
		this.clearNextTick(), this._tickTimer = self.setTimeout(this._boundTick, 0);
	}
	doTick() {}
}, Ia = class {
	constructor(e, t, n, r = 0, i = -1, a = !1) {
		this.level = void 0, this.sn = void 0, this.part = void 0, this.id = void 0, this.size = void 0, this.partial = void 0, this.transmuxing = La(), this.buffering = {
			audio: La(),
			video: La(),
			audiovideo: La()
		}, this.level = e, this.sn = t, this.id = n, this.size = r, this.part = i, this.partial = a;
	}
};
function La() {
	return {
		start: 0,
		executeStart: 0,
		executeEnd: 0,
		end: 0
	};
}
var Ra = {
	length: 0,
	start: () => 0,
	end: () => 0
}, Q = class e {
	static isBuffered(t, n) {
		if (t) {
			let r = e.getBuffered(t);
			for (let e = r.length; e--;) if (n >= r.start(e) && n <= r.end(e)) return !0;
		}
		return !1;
	}
	static bufferedRanges(t) {
		if (t) {
			let n = e.getBuffered(t);
			return e.timeRangesToArray(n);
		}
		return [];
	}
	static timeRangesToArray(e) {
		let t = [];
		for (let n = 0; n < e.length; n++) t.push({
			start: e.start(n),
			end: e.end(n)
		});
		return t;
	}
	static bufferInfo(t, n, r) {
		if (t) {
			let i = e.bufferedRanges(t);
			if (i.length) return e.bufferedInfo(i, n, r);
		}
		return {
			len: 0,
			start: n,
			end: n,
			bufferedIndex: -1
		};
	}
	static bufferedInfo(e, t, n) {
		t = Math.max(0, t), e.length > 1 && e.sort((e, t) => e.start - t.start || t.end - e.end);
		let r = -1, i = [];
		if (n) for (let a = 0; a < e.length; a++) {
			t >= e[a].start && t <= e[a].end && (r = a);
			let o = i.length;
			if (o) {
				let t = i[o - 1].end;
				e[a].start - t < n ? e[a].end > t && (i[o - 1].end = e[a].end) : i.push(e[a]);
			} else i.push(e[a]);
		}
		else i = e;
		let a = 0, o, s = t, c = t;
		for (let e = 0; e < i.length; e++) {
			let l = i[e].start, u = i[e].end;
			if (r === -1 && t >= l && t <= u && (r = e), t + n >= l && t < u) s = l, c = u, a = c - t;
			else if (t + n < l) {
				o = l;
				break;
			}
		}
		return {
			len: a,
			start: s || 0,
			end: c || 0,
			nextStart: o,
			buffered: e,
			bufferedIndex: r
		};
	}
	static getBuffered(e) {
		try {
			return e.buffered || Ra;
		} catch (e) {
			return Jn.log("failed to get media.buffered", e), Ra;
		}
	}
}, za = /\{\$([a-zA-Z0-9-_]+)\}/g;
function Ba(e) {
	return za.test(e);
}
function Va(e, t) {
	if (e.variableList !== null || e.hasVariableRefs) {
		let n = e.variableList;
		return t.replace(za, (t) => {
			let r = t.substring(2, t.length - 1), i = n?.[r];
			return i === void 0 ? (e.playlistParsingError ||= /* @__PURE__ */ Error(`Missing preceding EXT-X-DEFINE tag for Variable Reference: "${r}"`), t) : i;
		});
	}
	return t;
}
function Ha(e, t, n) {
	let r = e.variableList;
	r || (e.variableList = r = {});
	let i, a;
	if ("QUERYPARAM" in t) {
		i = t.QUERYPARAM;
		try {
			let e = new self.URL(n).searchParams;
			if (e.has(i)) a = e.get(i);
			else throw Error(`"${i}" does not match any query parameter in URI: "${n}"`);
		} catch (t) {
			e.playlistParsingError ||= /* @__PURE__ */ Error(`EXT-X-DEFINE QUERYPARAM: ${t.message}`);
		}
	} else i = t.NAME, a = t.VALUE;
	i in r ? e.playlistParsingError ||= /* @__PURE__ */ Error(`EXT-X-DEFINE duplicate Variable Name declarations: "${i}"`) : r[i] = a || "";
}
function Ua(e, t, n) {
	let r = t.IMPORT;
	if (n && r in n) {
		let t = e.variableList;
		t || (e.variableList = t = {}), t[r] = n[r];
	} else e.playlistParsingError ||= /* @__PURE__ */ Error(`EXT-X-DEFINE IMPORT attribute not found in Multivariant Playlist: "${r}"`);
}
var Wa = /^(\d+)x(\d+)$/, Ga = /(.+?)=(".*?"|.*?)(?:,|$)/g, Ka = class e {
	constructor(t, n) {
		typeof t == "string" && (t = e.parseAttrList(t, n)), Fn(this, t);
	}
	get clientAttrs() {
		return Object.keys(this).filter((e) => e.substring(0, 2) === "X-");
	}
	decimalInteger(e) {
		let t = parseInt(this[e], 10);
		return t > 2 ** 53 - 1 ? Infinity : t;
	}
	hexadecimalInteger(e) {
		if (this[e]) {
			let t = (this[e] || "0x").slice(2);
			t = (t.length & 1 ? "0" : "") + t;
			let n = new Uint8Array(t.length / 2);
			for (let e = 0; e < t.length / 2; e++) n[e] = parseInt(t.slice(e * 2, e * 2 + 2), 16);
			return n;
		}
		return null;
	}
	hexadecimalIntegerAsNumber(e) {
		let t = parseInt(this[e], 16);
		return t > 2 ** 53 - 1 ? Infinity : t;
	}
	decimalFloatingPoint(e) {
		return parseFloat(this[e]);
	}
	optionalFloat(e, t) {
		let n = this[e];
		return n ? parseFloat(n) : t;
	}
	enumeratedString(e) {
		return this[e];
	}
	enumeratedStringList(e, t) {
		let n = this[e];
		return (n ? n.split(/[ ,]+/) : []).reduce((e, t) => (e[t.toLowerCase()] = !0, e), t);
	}
	bool(e) {
		return this[e] === "YES";
	}
	decimalResolution(e) {
		let t = Wa.exec(this[e]);
		if (t !== null) return {
			width: parseInt(t[1], 10),
			height: parseInt(t[2], 10)
		};
	}
	static parseAttrList(e, t) {
		let n, r = {};
		for (Ga.lastIndex = 0; (n = Ga.exec(e)) !== null;) {
			let i = n[1].trim(), a = n[2], o = a.indexOf("\"") === 0 && a.lastIndexOf("\"") === a.length - 1, s = !1;
			if (o) a = a.slice(1, -1);
			else switch (i) {
				case "IV":
				case "SCTE35-CMD":
				case "SCTE35-IN":
				case "SCTE35-OUT": s = !0;
			}
			if (t && (o || s)) a = Va(t, a);
			else if (!s && !o) switch (i) {
				case "CLOSED-CAPTIONS": if (a === "NONE") break;
				case "ALLOWED-CPC":
				case "CLASS":
				case "ASSOC-LANGUAGE":
				case "AUDIO":
				case "BYTERANGE":
				case "CHANNELS":
				case "CHARACTERISTICS":
				case "CODECS":
				case "DATA-ID":
				case "END-DATE":
				case "GROUP-ID":
				case "ID":
				case "IMPORT":
				case "INSTREAM-ID":
				case "KEYFORMAT":
				case "KEYFORMATVERSIONS":
				case "LANGUAGE":
				case "NAME":
				case "PATHWAY-ID":
				case "QUERYPARAM":
				case "RECENTLY-REMOVED-DATERANGES":
				case "SERVER-URI":
				case "STABLE-RENDITION-ID":
				case "STABLE-VARIANT-ID":
				case "START-DATE":
				case "SUBTITLES":
				case "SUPPLEMENTAL-CODECS":
				case "URI":
				case "VALUE":
				case "VIDEO":
				case "X-ASSET-LIST":
				case "X-ASSET-URI": Jn.warn(`${e}: attribute ${i} is missing quotes`);
			}
			r[i] = a;
		}
		return r;
	}
}, qa = "com.apple.hls.interstitial";
function Ja(e) {
	return e !== "ID" && e !== "CLASS" && e !== "CUE" && e !== "START-DATE" && e !== "DURATION" && e !== "END-DATE" && e !== "END-ON-NEXT";
}
function Ya(e) {
	return e === "SCTE35-OUT" || e === "SCTE35-IN" || e === "SCTE35-CMD";
}
var Xa = class {
	constructor(e, t, n = 0) {
		if (this.attr = void 0, this.tagAnchor = void 0, this.tagOrder = void 0, this._startDate = void 0, this._endDate = void 0, this._dateAtEnd = void 0, this._cue = void 0, this._badValueForSameId = void 0, this.tagAnchor = t?.tagAnchor || null, this.tagOrder = t?.tagOrder ?? n, t) {
			let n = t.attr;
			for (let t in n) if (Object.prototype.hasOwnProperty.call(e, t) && e[t] !== n[t]) {
				Jn.warn(`DATERANGE tag attribute: "${t}" does not match for tags with ID: "${e.ID}"`), this._badValueForSameId = t;
				break;
			}
			e = Fn(new Ka({}), n, e);
		}
		if (this.attr = e, t ? (this._startDate = t._startDate, this._cue = t._cue, this._endDate = t._endDate, this._dateAtEnd = t._dateAtEnd) : this._startDate = new Date(e["START-DATE"]), "END-DATE" in this.attr) {
			let e = t?.endDate || new Date(this.attr["END-DATE"]);
			W(e.getTime()) && (this._endDate = e);
		}
	}
	get id() {
		return this.attr.ID;
	}
	get class() {
		return this.attr.CLASS;
	}
	get cue() {
		let e = this._cue;
		return e === void 0 ? this._cue = this.attr.enumeratedStringList(this.attr.CUE ? "CUE" : "X-CUE", {
			pre: !1,
			post: !1,
			once: !1
		}) : e;
	}
	get startTime() {
		let { tagAnchor: e } = this;
		return e === null || e.programDateTime === null ? (Jn.warn(`Expected tagAnchor Fragment with PDT set for DateRange "${this.id}": ${e}`), NaN) : e.start + (this.startDate.getTime() - e.programDateTime) / 1e3;
	}
	get startDate() {
		return this._startDate;
	}
	get endDate() {
		let e = this._endDate || this._dateAtEnd;
		if (e) return e;
		let t = this.duration;
		return t === null ? null : this._dateAtEnd = new Date(this._startDate.getTime() + t * 1e3);
	}
	get duration() {
		if ("DURATION" in this.attr) {
			let e = this.attr.decimalFloatingPoint("DURATION");
			if (W(e)) return e;
		} else if (this._endDate) return (this._endDate.getTime() - this._startDate.getTime()) / 1e3;
		return null;
	}
	get plannedDuration() {
		return "PLANNED-DURATION" in this.attr ? this.attr.decimalFloatingPoint("PLANNED-DURATION") : null;
	}
	get endOnNext() {
		return this.attr.bool("END-ON-NEXT");
	}
	get isInterstitial() {
		return this.class === qa;
	}
	get isValid() {
		return !!this.id && !this._badValueForSameId && W(this.startDate.getTime()) && (this.duration === null || this.duration >= 0) && (!this.endOnNext || !!this.class) && (!this.attr.CUE || !this.cue.pre && !this.cue.post || this.cue.pre !== this.cue.post) && (!this.isInterstitial || "X-ASSET-URI" in this.attr || "X-ASSET-LIST" in this.attr);
	}
}, Za = 10, Qa = class {
	constructor(e) {
		this.PTSKnown = !1, this.alignedSliding = !1, this.averagetargetduration = void 0, this.endCC = 0, this.endSN = 0, this.fragments = void 0, this.fragmentHint = void 0, this.partList = null, this.dateRanges = void 0, this.dateRangeTagCount = 0, this.live = !0, this.requestScheduled = -1, this.ageHeader = 0, this.advancedDateTime = void 0, this.updated = !0, this.advanced = !0, this.misses = 0, this.startCC = 0, this.startSN = 0, this.startTimeOffset = null, this.targetduration = 0, this.totalduration = 0, this.type = null, this.url = void 0, this.m3u8 = "", this.version = null, this.canBlockReload = !1, this.canSkipUntil = 0, this.canSkipDateRanges = !1, this.skippedSegments = 0, this.recentlyRemovedDateranges = void 0, this.partHoldBack = 0, this.holdBack = 0, this.partTarget = 0, this.preloadHint = void 0, this.renditionReports = void 0, this.tuneInGoal = 0, this.deltaUpdateFailed = void 0, this.driftStartTime = 0, this.driftEndTime = 0, this.driftStart = 0, this.driftEnd = 0, this.encryptedFragments = void 0, this.playlistParsingError = null, this.variableList = null, this.hasVariableRefs = !1, this.appliedTimelineOffset = void 0, this.fragments = [], this.encryptedFragments = [], this.dateRanges = {}, this.url = e;
	}
	reloaded(e) {
		if (!e) {
			this.advanced = !0, this.updated = !0;
			return;
		}
		let t = this.lastPartSn - e.lastPartSn, n = this.lastPartIndex - e.lastPartIndex;
		this.updated = this.endSN !== e.endSN || !!n || !!t || !this.live, this.advanced = this.endSN > e.endSN || t > 0 || t === 0 && n > 0, this.misses = this.updated || this.advanced ? Math.floor(e.misses * .6) : e.misses + 1;
	}
	hasKey(e) {
		return this.encryptedFragments.some((t) => {
			let n = t.decryptdata;
			return n ||= (t.setKeyFormat(e.keyFormat), t.decryptdata), !!n && e.matches(n);
		});
	}
	get hasProgramDateTime() {
		return this.fragments.length ? W(this.fragments[this.fragments.length - 1].programDateTime) : !1;
	}
	get levelTargetDuration() {
		return this.averagetargetduration || this.targetduration || Za;
	}
	get drift() {
		let e = this.driftEndTime - this.driftStartTime;
		return e > 0 ? (this.driftEnd - this.driftStart) * 1e3 / e : 1;
	}
	get edge() {
		return this.partEnd || this.fragmentEnd;
	}
	get partEnd() {
		var e;
		return (e = this.partList) != null && e.length ? this.partList[this.partList.length - 1].end : this.fragmentEnd;
	}
	get fragmentEnd() {
		return this.fragments.length ? this.fragments[this.fragments.length - 1].end : 0;
	}
	get fragmentStart() {
		return this.fragments.length ? this.fragments[0].start : 0;
	}
	get age() {
		return this.advancedDateTime ? Math.max(Date.now() - this.advancedDateTime, 0) / 1e3 : 0;
	}
	get lastPartIndex() {
		var e;
		return (e = this.partList) != null && e.length ? this.partList[this.partList.length - 1].index : -1;
	}
	get maxPartIndex() {
		let e = this.partList;
		if (e) {
			let t = this.lastPartIndex;
			if (t !== -1) {
				for (let n = e.length; n--;) if (e[n].index > t) return e[n].index;
				return t;
			}
		}
		return 0;
	}
	get lastPartSn() {
		var e;
		return (e = this.partList) != null && e.length ? this.partList[this.partList.length - 1].fragment.sn : this.endSN;
	}
	get expired() {
		if (this.live && this.age && this.misses < 3) {
			let e = this.partEnd - this.fragmentStart;
			return this.age > Math.max(e, this.totalduration) + this.levelTargetDuration;
		}
		return !1;
	}
};
function $a(e, t) {
	return e.length === t.length && !e.some((e, n) => e !== t[n]);
}
function eo(e, t) {
	return !e && !t ? !0 : !e || !t ? !1 : $a(e, t);
}
function to(e) {
	return e === "AES-128" || e === "AES-256" || e === "AES-256-CTR";
}
function no(e) {
	switch (e) {
		case "AES-128":
		case "AES-256": return xa.cbc;
		case "AES-256-CTR": return xa.ctr;
		default: throw Error(`invalid full segment method ${e}`);
	}
}
function ro(e) {
	return Uint8Array.from(atob(e), (e) => e.charCodeAt(0));
}
function io(e) {
	return Uint8Array.from(unescape(encodeURIComponent(e)), (e) => e.charCodeAt(0));
}
function ao(e) {
	let t = io(e).subarray(0, 16), n = /* @__PURE__ */ new Uint8Array(16);
	return n.set(t, 16 - t.length), n;
}
function oo(e) {
	let t = function(e, t, n) {
		let r = e[t];
		e[t] = e[n], e[n] = r;
	};
	t(e, 0, 3), t(e, 1, 2), t(e, 4, 5), t(e, 6, 7);
}
function so(e) {
	let t = e.split(":"), n = null;
	if (t[0] === "data" && t.length === 2) {
		let e = t[1].split(";"), r = e[e.length - 1].split(",");
		if (r.length === 2) {
			let t = r[0] === "base64", i = r[1];
			t ? (e.splice(-1, 1), n = ro(i)) : n = ao(i);
		}
	}
	return n;
}
var co = typeof self < "u" ? self : void 0, lo = {
	CLEARKEY: "org.w3.clearkey",
	FAIRPLAY: "com.apple.fps",
	PLAYREADY: "com.microsoft.playready",
	WIDEVINE: "com.widevine.alpha"
}, uo = {
	CLEARKEY: "org.w3.clearkey",
	FAIRPLAY: "com.apple.streamingkeydelivery",
	PLAYREADY: "com.microsoft.playready",
	WIDEVINE: "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed"
};
function fo(e) {
	switch (e) {
		case uo.FAIRPLAY: return lo.FAIRPLAY;
		case uo.PLAYREADY: return lo.PLAYREADY;
		case uo.WIDEVINE: return lo.WIDEVINE;
		case uo.CLEARKEY: return lo.CLEARKEY;
	}
}
function po(e) {
	switch (e) {
		case lo.FAIRPLAY: return uo.FAIRPLAY;
		case lo.PLAYREADY: return uo.PLAYREADY;
		case lo.WIDEVINE: return uo.WIDEVINE;
		case lo.CLEARKEY: return uo.CLEARKEY;
	}
}
function mo(e) {
	let { drmSystems: t, widevineLicenseUrl: n } = e, r = t ? [
		lo.FAIRPLAY,
		lo.WIDEVINE,
		lo.PLAYREADY,
		lo.CLEARKEY
	].filter((e) => !!t[e]) : [];
	return !r[lo.WIDEVINE] && n && r.push(lo.WIDEVINE), r;
}
var ho = function(e) {
	return co != null && (e = co.navigator) != null && e.requestMediaKeySystemAccess ? self.navigator.requestMediaKeySystemAccess.bind(self.navigator) : null;
}();
function go(e, t, n, r) {
	let i;
	switch (e) {
		case lo.FAIRPLAY:
			i = ["cenc", "sinf"];
			break;
		case lo.WIDEVINE:
		case lo.PLAYREADY:
			i = ["cenc"];
			break;
		case lo.CLEARKEY:
			i = ["cenc", "keyids"];
			break;
		default: throw Error(`Unknown key-system: ${e}`);
	}
	return _o(i, t, n, r);
}
function _o(e, t, n, r) {
	return [{
		initDataTypes: e,
		persistentState: r.persistentState || "optional",
		distinctiveIdentifier: r.distinctiveIdentifier || "optional",
		sessionTypes: r.sessionTypes || [r.sessionType || "temporary"],
		audioCapabilities: t.map((e) => ({
			contentType: `audio/mp4; codecs=${e}`,
			robustness: r.audioRobustness || "",
			encryptionScheme: r.audioEncryptionScheme || null
		})),
		videoCapabilities: n.map((e) => ({
			contentType: `video/mp4; codecs=${e}`,
			robustness: r.videoRobustness || "",
			encryptionScheme: r.videoEncryptionScheme || null
		}))
	}];
}
function vo(e) {
	var t;
	return !!e && (e.sessionType === "persistent-license" || !!((t = e.sessionTypes) != null && t.some((e) => e === "persistent-license")));
}
function yo(e) {
	let t = new Uint16Array(e.buffer, e.byteOffset, e.byteLength / 2), n = String.fromCharCode.apply(null, Array.from(t)), r = n.substring(n.indexOf("<"), n.length), i = new DOMParser().parseFromString(r, "text/xml").getElementsByTagName("KID")[0];
	if (i) {
		let e = i.childNodes[0] ? i.childNodes[0].nodeValue : i.getAttribute("VALUE");
		if (e) {
			let t = ro(e).subarray(0, 16);
			return oo(t), t;
		}
	}
	return null;
}
var bo = {}, xo = class e {
	static clearKeyUriToKeyIdMap() {
		bo = {};
	}
	static setKeyIdForUri(e, t) {
		bo[e] = t;
	}
	static addKeyIdForUri(e) {
		let t = Object.keys(bo).length % (2 ** 53 - 1), n = /* @__PURE__ */ new Uint8Array(16);
		return new DataView(n.buffer, 12, 4).setUint32(0, t), bo[e] = n, n;
	}
	constructor(e, t, n, r = [1], i = null, a) {
		this.uri = void 0, this.method = void 0, this.keyFormat = void 0, this.keyFormatVersions = void 0, this.encrypted = void 0, this.isCommonEncryption = void 0, this.iv = null, this.key = null, this.keyId = null, this.pssh = null, this.method = e, this.uri = t, this.keyFormat = n, this.keyFormatVersions = r, this.iv = i, this.encrypted = e ? e !== "NONE" : !1, this.isCommonEncryption = this.encrypted && !to(e), a != null && a.startsWith("0x") && (this.keyId = new Uint8Array(er(a)));
	}
	matches(e) {
		return e.uri === this.uri && e.method === this.method && e.encrypted === this.encrypted && e.keyFormat === this.keyFormat && $a(e.keyFormatVersions, this.keyFormatVersions) && eo(e.iv, this.iv) && eo(e.keyId, this.keyId);
	}
	isSupported() {
		if (this.method) {
			if (to(this.method) || this.method === "NONE") return !0;
			if (this.keyFormat === "identity") return this.method === "SAMPLE-AES";
			switch (this.keyFormat) {
				case uo.FAIRPLAY:
				case uo.WIDEVINE:
				case uo.PLAYREADY:
				case uo.CLEARKEY: return [
					"SAMPLE-AES",
					"SAMPLE-AES-CENC",
					"SAMPLE-AES-CTR"
				].indexOf(this.method) !== -1;
			}
		}
		return !1;
	}
	getDecryptData(t, n) {
		if (!this.encrypted || !this.uri) return null;
		if (to(this.method)) {
			let n = this.iv;
			return n ||= (typeof t != "number" && (Jn.warn(`missing IV for initialization segment with method="${this.method}" - compliance issue`), t = 0), wo(t)), new e(this.method, this.uri, "identity", this.keyFormatVersions, n);
		}
		if (this.keyId) {
			let t = bo[this.uri];
			if (t && !$a(this.keyId, t) && e.setKeyIdForUri(this.uri, this.keyId), this.pssh) return this;
		}
		let r = so(this.uri);
		if (r) switch (this.keyFormat) {
			case uo.WIDEVINE:
				if (this.pssh = r, !this.keyId) {
					let e = Gr(r.buffer);
					if (e.length) {
						var i;
						let t = e[0];
						this.keyId = (i = t.kids) != null && i.length ? t.kids[0] : null;
					}
				}
				this.keyId ||= Co(n);
				break;
			case uo.PLAYREADY: {
				let e = new Uint8Array([
					154,
					4,
					240,
					121,
					152,
					64,
					66,
					134,
					171,
					146,
					230,
					91,
					224,
					136,
					95,
					149
				]);
				this.pssh = Wr(e, null, r), this.keyId = yo(r);
				break;
			}
			default: {
				let e = r.subarray(0, 16);
				if (e.length !== 16) {
					let t = /* @__PURE__ */ new Uint8Array(16);
					t.set(e, 16 - e.length), e = t;
				}
				this.keyId = e;
				break;
			}
		}
		if (!this.keyId || this.keyId.byteLength !== 16) {
			let t;
			t = So(n), t || (t = Co(n), t ||= bo[this.uri]), t && (this.keyId = t, e.setKeyIdForUri(this.uri, t));
		}
		return this;
	}
};
function So(e) {
	let t = e?.[uo.WIDEVINE];
	return t ? t.keyId : null;
}
function Co(e) {
	let t = e?.[uo.PLAYREADY];
	if (t) {
		let e = so(t.uri);
		if (e) return yo(e);
	}
	return null;
}
function wo(e) {
	let t = /* @__PURE__ */ new Uint8Array(16);
	for (let n = 12; n < 16; n++) t[n] = e >> 8 * (15 - n) & 255;
	return t;
}
var To = /#EXT-X-STREAM-INF:([^\r\n]*)(?:[\r\n](?:#[^\r\n]*)?)*([^\r\n]+)|#EXT-X-(SESSION-DATA|SESSION-KEY|DEFINE|CONTENT-STEERING|START):([^\r\n]*)[\r\n]+/g, Eo = /#EXT-X-MEDIA:(.*)/g, Do = /^#EXT(?:INF|-X-TARGETDURATION):/m, Oo = /* @__PURE__ */ RegExp("#EXTINF:\\s*(\\d*(?:\\.\\d+)?)(?:,(.*)\\s+)?|(?!#) *(\\S[^\\r\\n]*)|#.*", "g"), ko = /* @__PURE__ */ RegExp("#EXT-X-(PROGRAM-DATE-TIME|BYTERANGE|DATERANGE|DEFINE|KEY|MAP|PART|PART-INF|PLAYLIST-TYPE|PRELOAD-HINT|RENDITION-REPORT|SERVER-CONTROL|SKIP|START):(.+)|#EXT-X-(BITRATE|DISCONTINUITY-SEQUENCE|MEDIA-SEQUENCE|TARGETDURATION|VERSION): *(\\d+)|#EXT-X-(DISCONTINUITY|ENDLIST|GAP|INDEPENDENT-SEGMENTS)|(#)([^:]*):(.*)|(#)(.*)(?:.*)\\r?\\n?"), Ao = class e {
	static findGroup(e, t) {
		for (let n = 0; n < e.length; n++) {
			let r = e[n];
			if (r.id === t) return r;
		}
	}
	static resolve(e, t) {
		return ar.buildAbsoluteURL(t, e, { alwaysNormalize: !0 });
	}
	static isMediaPlaylist(e) {
		return Do.test(e);
	}
	static parseMasterPlaylist(t, n) {
		let r = {
			contentSteering: null,
			levels: [],
			playlistParsingError: null,
			sessionData: null,
			sessionKeys: null,
			startTimeOffset: null,
			variableList: null,
			hasVariableRefs: Ba(t)
		}, i = [];
		if (To.lastIndex = 0, !t.startsWith("#EXTM3U")) return r.playlistParsingError = /* @__PURE__ */ Error("no EXTM3U delimiter"), r;
		let a;
		for (; (a = To.exec(t)) != null;) if (a[1]) {
			var o;
			let t = new Ka(a[1], r), s = Va(r, a[2]), c = {
				attrs: t,
				bitrate: t.decimalInteger("BANDWIDTH") || t.decimalInteger("AVERAGE-BANDWIDTH"),
				name: t.NAME,
				url: e.resolve(s, n)
			}, l = t.decimalResolution("RESOLUTION");
			l && (c.width = l.width, c.height = l.height), Fo(t.CODECS, c);
			let u = t["SUPPLEMENTAL-CODECS"];
			u && (c.supplemental = {}, Fo(u, c.supplemental)), (o = c.unknownCodecs) != null && o.length || i.push(c), r.levels.push(c);
		} else if (a[3]) {
			let t = a[3], i = a[4];
			switch (t) {
				case "SESSION-DATA": {
					let e = new Ka(i, r), t = e["DATA-ID"];
					t && (r.sessionData === null && (r.sessionData = {}), r.sessionData[t] = e);
					break;
				}
				case "SESSION-KEY": {
					let e = No(i, n, r);
					e.encrypted && e.isSupported() ? (r.sessionKeys === null && (r.sessionKeys = []), r.sessionKeys.push(e)) : Jn.warn(`[Keys] Ignoring invalid EXT-X-SESSION-KEY tag: "${i}"`);
					break;
				}
				case "DEFINE":
					Ha(r, new Ka(i, r), n);
					break;
				case "CONTENT-STEERING": {
					let t = new Ka(i, r);
					r.contentSteering = {
						uri: e.resolve(t["SERVER-URI"], n),
						pathwayId: t["PATHWAY-ID"] || "."
					};
					break;
				}
				case "START": r.startTimeOffset = Po(i);
			}
		}
		return r.levels = i.length > 0 && i.length < r.levels.length ? i : r.levels, r.levels.length === 0 && (r.playlistParsingError = /* @__PURE__ */ Error("no levels found in manifest")), r;
	}
	static parseMasterPlaylistMedia(t, n, r) {
		let i, a = {}, o = r.levels, s = {
			AUDIO: o.map((e) => ({
				id: e.attrs.AUDIO,
				audioCodec: e.audioCodec
			})),
			SUBTITLES: o.map((e) => ({
				id: e.attrs.SUBTITLES,
				textCodec: e.textCodec
			})),
			"CLOSED-CAPTIONS": []
		}, c = 0;
		for (Eo.lastIndex = 0; (i = Eo.exec(t)) !== null;) {
			let t = new Ka(i[1], r), o = t.TYPE;
			if (o) {
				let r = s[o], i = a[o] || [];
				a[o] = i;
				let l = t.LANGUAGE, u = t["ASSOC-LANGUAGE"], d = t.CHANNELS, f = t.CHARACTERISTICS, p = t["INSTREAM-ID"], m = {
					attrs: t,
					bitrate: 0,
					id: c++,
					groupId: t["GROUP-ID"] || "",
					name: t.NAME || l || "",
					type: o,
					default: t.bool("DEFAULT"),
					autoselect: t.bool("AUTOSELECT"),
					forced: t.bool("FORCED"),
					lang: l,
					url: t.URI ? e.resolve(t.URI, n) : ""
				};
				if (u && (m.assocLang = u), d && (m.channels = d), f && (m.characteristics = f), p && (m.instreamId = p), r != null && r.length) {
					let t = e.findGroup(r, m.groupId) || r[0];
					Io(m, t, "audioCodec"), Io(m, t, "textCodec");
				}
				i.push(m);
			}
		}
		return a;
	}
	static parseLevelPlaylist(e, t, n, r, i, a) {
		let o = { url: t }, s = new Qa(t), c = s.fragments, l = [], u = null, d = 0, f = 0, p = 0, m = 0, h = 0, g = null, _ = new ur(r, o), v, y, b, x = -1, S = !1, C = null, w;
		if (Oo.lastIndex = 0, s.m3u8 = e, s.hasVariableRefs = Ba(e), Oo.exec(e)?.[0] !== "#EXTM3U") return s.playlistParsingError = /* @__PURE__ */ Error("Missing format identifier #EXTM3U"), s;
		for (; (v = Oo.exec(e)) !== null;) {
			S && (S = !1, _ = new ur(r, o), _.playlistOffset = p, _.setStart(p), _.sn = d, _.cc = m, h && (_.bitrate = h), _.level = n, u && (_.initSegment = u, u.rawProgramDateTime && (_.rawProgramDateTime = u.rawProgramDateTime, u.rawProgramDateTime = null), C &&= (_.setByteRange(C), null)));
			let e = v[1];
			if (e) {
				_.duration = parseFloat(e);
				let t = (" " + v[2]).slice(1);
				_.title = t || null, _.tagList.push(t ? [
					"INF",
					e,
					t
				] : ["INF", e]);
			} else if (v[3]) {
				if (W(_.duration)) {
					_.playlistOffset = p, _.setStart(p), b && Bo(_, b, s), _.sn = d, _.level = n, _.cc = m, c.push(_);
					let e = (" " + v[3]).slice(1);
					_.relurl = Va(s, e), Ro(_, g, l), g = _, p += _.duration, d++, f = 0, S = !0;
				}
			} else {
				if (v = v[0].match(ko), !v) {
					Jn.warn("No matches on slow regex match for level playlist!");
					continue;
				}
				for (y = 1; y < v.length && v[y] === void 0; y++);
				let e = (" " + v[y]).slice(1), i = (" " + v[y + 1]).slice(1), l = v[y + 2] ? (" " + v[y + 2]).slice(1) : null;
				switch (e) {
					case "BYTERANGE":
						g ? _.setByteRange(i, g) : _.setByteRange(i);
						break;
					case "PROGRAM-DATE-TIME":
						_.rawProgramDateTime = i, _.tagList.push(["PROGRAM-DATE-TIME", i]), x === -1 && (x = c.length);
						break;
					case "PLAYLIST-TYPE":
						s.type && Vo(s, e, v), s.type = i.toUpperCase();
						break;
					case "MEDIA-SEQUENCE":
						s.startSN === 0 ? c.length > 0 && Ho(s, e, v) : Vo(s, e, v), d = s.startSN = parseInt(i);
						break;
					case "SKIP": {
						s.skippedSegments && Vo(s, e, v);
						let t = new Ka(i, s), n = t.decimalInteger("SKIPPED-SEGMENTS");
						if (W(n)) {
							s.skippedSegments += n;
							for (let e = n; e--;) c.push(null);
							d += n;
						}
						let r = t.enumeratedString("RECENTLY-REMOVED-DATERANGES");
						r && (s.recentlyRemovedDateranges = (s.recentlyRemovedDateranges || []).concat(r.split("	")));
						break;
					}
					case "TARGETDURATION":
						s.targetduration !== 0 && Vo(s, e, v), s.targetduration = Math.max(parseInt(i), 1);
						break;
					case "VERSION":
						s.version !== null && Vo(s, e, v), s.version = parseInt(i);
						break;
					case "INDEPENDENT-SEGMENTS": break;
					case "ENDLIST":
						s.live || Vo(s, e, v), s.live = !1;
						break;
					case "#":
						(i || l) && _.tagList.push(l ? [i, l] : [i]);
						break;
					case "DISCONTINUITY":
						m++, _.tagList.push(["DIS"]);
						break;
					case "GAP":
						_.gap = !0, _.tagList.push([e]);
						break;
					case "BITRATE":
						_.tagList.push([e, i]), h = parseInt(i) * 1e3, W(h) ? _.bitrate = h : h = 0;
						break;
					case "DATERANGE": {
						let e = new Ka(i, s), t = new Xa(e, s.dateRanges[e.ID], s.dateRangeTagCount);
						s.dateRangeTagCount++, t.isValid || s.skippedSegments ? s.dateRanges[t.id] = t : Jn.warn(`Ignoring invalid DATERANGE tag: "${i}"`), _.tagList.push(["EXT-X-DATERANGE", i]);
						break;
					}
					case "DEFINE":
						{
							let e = new Ka(i, s);
							"IMPORT" in e ? Ua(s, e, a) : Ha(s, e, t);
						}
						break;
					case "DISCONTINUITY-SEQUENCE":
						s.startCC === 0 ? c.length > 0 && Ho(s, e, v) : Vo(s, e, v), s.startCC = m = parseInt(i);
						break;
					case "KEY": {
						let e = No(i, t, s);
						if (e.isSupported()) {
							if (e.method === "NONE") {
								b = void 0;
								break;
							}
							b ||= {};
							let t = b[e.keyFormat];
							t != null && t.matches(e) || (t && (b = Fn({}, b)), b[e.keyFormat] = e);
						} else Jn.warn(`[Keys] Ignoring unsupported EXT-X-KEY tag: "${i}"`);
						break;
					}
					case "START":
						s.startTimeOffset = Po(i);
						break;
					case "MAP": {
						let e = new Ka(i, s);
						if (_.duration) {
							let t = new ur(r, o);
							zo(t, e, n, b), u = t, _.initSegment = u, u.rawProgramDateTime && !_.rawProgramDateTime && (_.rawProgramDateTime = u.rawProgramDateTime);
						} else {
							let t = _.byteRangeEndOffset;
							if (t) {
								let e = _.byteRangeStartOffset;
								C = `${t - e}@${e}`;
							} else C = null;
							zo(_, e, n, b), u = _, S = !0;
						}
						u.cc = m;
						break;
					}
					case "SERVER-CONTROL":
						w && Vo(s, e, v), w = new Ka(i), s.canBlockReload = w.bool("CAN-BLOCK-RELOAD"), s.canSkipUntil = w.optionalFloat("CAN-SKIP-UNTIL", 0), s.canSkipDateRanges = s.canSkipUntil > 0 && w.bool("CAN-SKIP-DATERANGES"), s.partHoldBack = w.optionalFloat("PART-HOLD-BACK", 0), s.holdBack = w.optionalFloat("HOLD-BACK", 0);
						break;
					case "PART-INF":
						s.partTarget && Vo(s, e, v), s.partTarget = new Ka(i).decimalFloatingPoint("PART-TARGET");
						break;
					case "PART": {
						let e = s.partList;
						e ||= s.partList = [];
						let t = f > 0 ? e[e.length - 1] : void 0, n = f++, r = new dr(new Ka(i, s), _, o, n, t);
						e.push(r), _.duration += r.duration;
						break;
					}
					case "PRELOAD-HINT":
						s.preloadHint = new Ka(i, s);
						break;
					case "RENDITION-REPORT": {
						let e = new Ka(i, s);
						s.renditionReports = s.renditionReports || [], s.renditionReports.push(e);
						break;
					}
					default: Jn.warn(`line parsed but not handled: ${v}`);
				}
			}
		}
		g && !g.relurl ? (c.pop(), p -= g.duration, s.partList && (s.fragmentHint = g)) : s.partList && (Ro(_, g, l), _.cc = m, s.fragmentHint = _, b && Bo(_, b, s)), s.targetduration || (s.playlistParsingError = /* @__PURE__ */ Error("Missing Target Duration"));
		let T = c.length, E = c[0], D = c[T - 1];
		if (p += s.skippedSegments * s.targetduration, p > 0 && T && D) {
			s.averagetargetduration = p / T;
			let e = D.sn;
			s.endSN = e === "initSegment" ? 0 : e, s.live || (D.endList = !0), x > 0 && (Lo(c, x), E && l.unshift(E));
		}
		return s.fragmentHint && (p += s.fragmentHint.duration), s.totalduration = p, l.length && s.dateRangeTagCount && E && jo(l, s), s.endCC = m, s;
	}
};
function jo(e, t) {
	let n = e.length;
	if (!n) {
		if (t.hasProgramDateTime) {
			let r = t.fragments[t.fragments.length - 1];
			e.push(r), n++;
		} else return;
	}
	let r = e[n - 1], i = t.live ? Infinity : t.totalduration, a = Object.keys(t.dateRanges);
	for (let o = a.length; o--;) {
		let s = t.dateRanges[a[o]], c = s.startDate.getTime();
		s.tagAnchor = r.ref;
		for (let r = n; r-- && !(e[r]?.sn < t.startSN);) {
			let n = Mo(t, c, e, r, i);
			if (n !== -1) {
				s.tagAnchor = t.fragments[n].ref;
				break;
			}
		}
	}
}
function Mo(e, t, n, r, i) {
	let a = n[r];
	if (a) {
		let o = a.programDateTime;
		if ((t >= o || r === 0) && t <= o + ((n[r + 1]?.start || i) - a.start) * 1e3) {
			let i = n[r].sn - e.startSN;
			if (i < 0) return -1;
			let a = e.fragments;
			if (a.length > n.length) {
				let o = (n[r + 1] || a[a.length - 1]).sn - e.startSN;
				for (let e = o; e > i; e--) {
					let n = a[e].programDateTime;
					if (t >= n && t < n + a[e].duration * 1e3) return e;
				}
			}
			return i;
		}
	}
	return -1;
}
function No(e, t, n) {
	let r = new Ka(e, n), i = r.METHOD ?? "", a = r.URI, o = r.hexadecimalInteger("IV"), s = r.KEYFORMATVERSIONS, c = r.KEYFORMAT ?? "identity";
	return a && r.IV && !o && Jn.error(`Invalid IV: ${r.IV}`), new xo(i, a ? Ao.resolve(a, t) : "", c, (s || "1").split("/").map(Number).filter(Number.isFinite), o, r.KEYID);
}
function Po(e) {
	let t = new Ka(e).decimalFloatingPoint("TIME-OFFSET");
	return W(t) ? t : null;
}
function Fo(e, t) {
	let n = (e || "").split(/[ ,]+/).filter((e) => e);
	[
		"video",
		"audio",
		"text"
	].forEach((e) => {
		let r = n.filter((t) => Yr(t, e));
		r.length && (t[`${e}Codec`] = r.map((e) => e.split("/")[0]).join(","), n = n.filter((e) => r.indexOf(e) === -1));
	}), t.unknownCodecs = n;
}
function Io(e, t, n) {
	let r = t[n];
	r && (e[n] = r);
}
function Lo(e, t) {
	let n = e[t];
	for (let r = t; r--;) {
		let t = e[r];
		if (!t) return;
		t.programDateTime = n.programDateTime - t.duration * 1e3, n = t;
	}
}
function Ro(e, t, n) {
	e.rawProgramDateTime ? n.push(e) : t != null && t.programDateTime && (e.programDateTime = t.endProgramDateTime);
}
function zo(e, t, n, r) {
	e.relurl = t.URI, t.BYTERANGE && e.setByteRange(t.BYTERANGE), e.level = n, e.sn = "initSegment", r && (e.levelkeys = r), e.initSegment = null;
}
function Bo(e, t, n) {
	e.levelkeys = t;
	let { encryptedFragments: r } = n;
	(!r.length || r[r.length - 1].levelkeys !== t) && Object.keys(t).some((e) => t[e].isCommonEncryption) && r.push(e);
}
function Vo(e, t, n) {
	e.playlistParsingError = /* @__PURE__ */ Error(`#EXT-X-${t} must not appear more than once (${n[0]})`);
}
function Ho(e, t, n) {
	e.playlistParsingError = /* @__PURE__ */ Error(`#EXT-X-${t} must appear before the first Media Segment (${n[0]})`);
}
function Uo(e, t) {
	let n = t.startPTS;
	if (W(n)) {
		let r = 0, i;
		t.sn > e.sn ? (r = n - e.start, i = e) : (r = e.start - n, i = t), i.duration !== r && i.setDuration(r);
	} else t.sn > e.sn ? e.cc === t.cc && e.minEndPTS ? t.setStart(e.start + (e.minEndPTS - e.start)) : t.setStart(e.start + e.duration) : t.setStart(Math.max(e.start - t.duration, 0));
}
function Wo(e, t, n, r, i, a, o) {
	r - n <= 0 && (o.warn("Fragment should have a positive duration", t), r = n + t.duration, a = i + t.duration);
	let s = n, c = r, l = t.startPTS, u = t.endPTS;
	if (W(l)) {
		let d = Math.abs(l - n);
		e && d > e.totalduration ? o.warn(`media timestamps and playlist times differ by ${d}s for level ${t.level} ${e.url}`) : t.deltaPTS = W(t.deltaPTS) ? Math.max(d, t.deltaPTS) : d, s = Math.max(n, l), n = Math.min(n, l), i = t.startDTS === void 0 ? i : Math.min(i, t.startDTS), c = Math.min(r, u), r = Math.max(r, u), a = t.endDTS === void 0 ? a : Math.max(a, t.endDTS);
	}
	let d = n - t.start;
	t.start !== 0 && t.setStart(n), t.setDuration(r - t.start), t.startPTS = n, t.maxStartPTS = s, t.startDTS = i, t.endPTS = r, t.minEndPTS = c, t.endDTS = a;
	let f = t.sn;
	if (!e || f < e.startSN || f > e.endSN) return 0;
	let p, m = f - e.startSN, h = e.fragments;
	for (h[m] = t, p = m; p > 0; p--) Uo(h[p], h[p - 1]);
	for (p = m; p < h.length - 1; p++) Uo(h[p], h[p + 1]);
	return e.fragmentHint && Uo(h[h.length - 1], e.fragmentHint), e.PTSKnown = e.alignedSliding = !0, d;
}
function Go(e, t, n) {
	if (e === t) return;
	let r = null, i = e.fragments;
	for (let e = i.length - 1; e >= 0; e--) {
		let t = i[e].initSegment;
		if (t) {
			r = t;
			break;
		}
	}
	e.fragmentHint && delete e.fragmentHint.endPTS;
	let a;
	Jo(e, t, (e, n, i, o) => {
		if ((!t.startCC || t.skippedSegments) && n.cc !== e.cc) {
			let r = e.cc - n.cc;
			for (let e = i; e < o.length; e++) o[e].cc += r;
			t.endCC = o[o.length - 1].cc;
		}
		W(e.startPTS) && W(e.endPTS) && (n.setStart(n.startPTS = e.startPTS), n.startDTS = e.startDTS, n.maxStartPTS = e.maxStartPTS, n.endPTS = e.endPTS, n.endDTS = e.endDTS, n.minEndPTS = e.minEndPTS, n.setDuration(e.endPTS - e.startPTS), n.duration && (a = n), t.PTSKnown = t.alignedSliding = !0), e.hasStreams && (n.elementaryStreams = e.elementaryStreams), n.loader = e.loader, e.hasStats && (n.stats = e.stats), e.initSegment && (n.initSegment = e.initSegment, r = e.initSegment);
	});
	let o = t.fragments, s = t.fragmentHint ? o.concat(t.fragmentHint) : o;
	if (r && s.forEach((e) => {
		e && (!e.initSegment || e.initSegment.relurl === r?.relurl) && (e.initSegment = r);
	}), t.skippedSegments) {
		if (t.deltaUpdateFailed = o.some((e) => !e), t.deltaUpdateFailed) {
			n.warn("[level-helper] Previous playlist missing segments skipped in delta playlist");
			for (let e = t.skippedSegments; e--;) o.shift();
			t.startSN = o[0].sn;
		} else {
			t.canSkipDateRanges && (t.dateRanges = Ko(e.dateRanges, t, n));
			let r = e.fragments.filter((e) => e.rawProgramDateTime);
			if (e.hasProgramDateTime && !t.hasProgramDateTime) for (let e = 1; e < s.length; e++) s[e].programDateTime === null && Ro(s[e], s[e - 1], r);
			jo(r, t);
		}
		t.endCC = o[o.length - 1].cc;
	}
	t.startCC ||= $o(e, t.startSN - 1)?.cc ?? o[0].cc, qo(e.partList, t.partList, (e, t) => {
		t.elementaryStreams = e.elementaryStreams, t.stats = e.stats;
	}), a ? Wo(t, a, a.startPTS, a.endPTS, a.startDTS, a.endDTS, n) : Xo(e, t), o.length && (t.totalduration = t.edge - o[0].start), t.driftStartTime = e.driftStartTime, t.driftStart = e.driftStart;
	let c = t.advancedDateTime;
	if (t.advanced && c) {
		let e = t.edge;
		t.driftStart ||= (t.driftStartTime = c, e), t.driftEndTime = c, t.driftEnd = e;
	} else t.driftEndTime = e.driftEndTime, t.driftEnd = e.driftEnd, t.advancedDateTime = e.advancedDateTime;
	t.requestScheduled === -1 && (t.requestScheduled = e.requestScheduled);
}
function Ko(e, t, n) {
	let { dateRanges: r, recentlyRemovedDateranges: i } = t, a = Fn({}, e);
	i && i.forEach((e) => {
		delete a[e];
	});
	let o = Object.keys(a).length;
	return o ? (Object.keys(r).forEach((e) => {
		let t = a[e], i = new Xa(r[e].attr, t);
		i.isValid ? (a[e] = i, t || (i.tagOrder += o)) : n.warn(`Ignoring invalid Playlist Delta Update DATERANGE tag: "${Fi(r[e].attr)}"`);
	}), a) : r;
}
function qo(e, t, n) {
	if (e && t) {
		let r = 0;
		for (let i = 0, a = e.length; i <= a; i++) {
			let a = e[i], o = t[i + r];
			a && o && a.index === o.index && a.fragment.sn === o.fragment.sn ? n(a, o) : r--;
		}
	}
}
function Jo(e, t, n) {
	let r = t.skippedSegments, i = Math.max(e.startSN, t.startSN) - t.startSN, a = +!!e.fragmentHint + (r ? t.endSN : Math.min(e.endSN, t.endSN)) - t.startSN, o = t.startSN - e.startSN, s = t.fragmentHint ? t.fragments.concat(t.fragmentHint) : t.fragments, c = e.fragmentHint ? e.fragments.concat(e.fragmentHint) : e.fragments;
	for (let l = i; l <= a; l++) {
		let i = c[o + l], a = s[l];
		if (r && !a && i && (a = t.fragments[l] = i), i && a) {
			n(i, a, l, s);
			let r = i.relurl, o = a.relurl;
			if (r && rs(r, o)) {
				t.playlistParsingError = Yo(`media sequence mismatch ${a.sn}:`, e, t, i, a);
				return;
			}
			if (i.cc !== a.cc) {
				t.playlistParsingError = Yo(`discontinuity sequence mismatch (${i.cc}!=${a.cc})`, e, t, i, a);
				return;
			}
		}
	}
}
function Yo(e, t, n, r, i) {
	return /* @__PURE__ */ Error(`${e} ${i.url}
Playlist starting @${t.startSN}
${t.m3u8}

Playlist starting @${n.startSN}
${n.m3u8}`);
}
function Xo(e, t, n = !0) {
	let r = t.startSN + t.skippedSegments - e.startSN, i = e.fragments, a = r >= 0, o = 0;
	if (a && r < i.length) o = i[r].start;
	else if (a && t.startSN === e.endSN + 1) o = e.fragmentEnd;
	else if (a && n) o = e.fragmentStart + r * t.levelTargetDuration;
	else if (!t.skippedSegments && t.fragmentStart === 0) o = e.fragmentStart;
	else return;
	Zo(t, o);
}
function Zo(e, t) {
	if (t) {
		let n = e.fragments;
		for (let r = e.skippedSegments; r < n.length; r++) n[r].addStart(t);
		e.fragmentHint && e.fragmentHint.addStart(t);
	}
}
function Qo(e, t = Infinity) {
	let n = 1e3 * e.targetduration;
	if (e.updated) {
		let r = e.fragments;
		if (r.length && n * 4 > t) {
			let e = r[r.length - 1].duration * 1e3;
			e < n && (n = e);
		}
	} else n /= 2;
	return Math.round(n);
}
function $o(e, t, n) {
	if (!e) return null;
	let r = e.fragments[t - e.startSN];
	return r || (r = e.fragmentHint, r && r.sn === t) ? r : t < e.startSN && n && n.sn === t ? n : null;
}
function es(e, t, n) {
	return e ? ts(e.partList, t, n) : null;
}
function ts(e, t, n) {
	if (e) for (let r = e.length; r--;) {
		let i = e[r];
		if (i.index === n && i.fragment.sn === t) return i;
	}
	return null;
}
function ns(e) {
	e.forEach((e, t) => {
		var n;
		(n = e.details) == null || n.fragments.forEach((e) => {
			e.level = t, e.initSegment && (e.initSegment.level = t);
		});
	});
}
function rs(e, t) {
	return e !== t && t ? is(e) !== is(t) : !1;
}
function is(e) {
	return e.replace(/\?[^?]*$/, "");
}
function as(e, t) {
	for (let n = 0, r = e.length; n < r; n++) if (e[n]?.cc === t) return e[n];
	return null;
}
function os(e, t) {
	return !!(e && t.startCC < e.endCC && t.endCC > e.startCC);
}
function ss(e, t) {
	let n = e.start + t;
	e.startPTS = n, e.setStart(n), e.endPTS = n + e.duration;
}
function cs(e, t) {
	let n = t.fragments;
	for (let t = 0, r = n.length; t < r; t++) ss(n[t], e);
	t.fragmentHint && ss(t.fragmentHint, e), t.alignedSliding = !0;
}
function ls(e, t) {
	e && (us(t, e), t.alignedSliding || ds(t, e), !t.alignedSliding && !t.skippedSegments && Xo(e, t, !1));
}
function us(e, t) {
	if (!os(t, e)) return;
	let n = Math.min(t.endCC, e.endCC), r = as(t.fragments, n), i = as(e.fragments, n);
	r && i && (Jn.log(`Aligning playlist at start of dicontinuity sequence ${n}`), cs(r.start - i.start, e));
}
function ds(e, t) {
	if (!e.hasProgramDateTime || !t.hasProgramDateTime) return;
	let n = e.fragments, r = t.fragments;
	if (!n.length || !r.length) return;
	let i, a, o = Math.min(t.endCC, e.endCC);
	t.startCC < o && e.startCC < o && (i = as(r, o), a = as(n, o)), i && a || (i = r[Math.floor(r.length / 2)], a = as(n, i.cc) || n[Math.floor(n.length / 2)]);
	let s = i.programDateTime, c = a.programDateTime;
	s && c && cs((c - s) / 1e3 - (a.start - i.start), e);
}
function fs(e, t, n) {
	ps(e, t, n), e.addEventListener(t, n);
}
function ps(e, t, n) {
	e.removeEventListener(t, n);
}
var ms = { toString: function(e) {
	let t = "", n = e.length;
	for (let r = 0; r < n; r++) t += `[${e.start(r).toFixed(3)}-${e.end(r).toFixed(3)}]`;
	return t;
} }, $ = {
	STOPPED: "STOPPED",
	IDLE: "IDLE",
	KEY_LOADING: "KEY_LOADING",
	FRAG_LOADING: "FRAG_LOADING",
	FRAG_LOADING_WAITING_RETRY: "FRAG_LOADING_WAITING_RETRY",
	WAITING_TRACK: "WAITING_TRACK",
	PARSING: "PARSING",
	PARSED: "PARSED",
	ENDED: "ENDED",
	ERROR: "ERROR",
	WAITING_INIT_PTS: "WAITING_INIT_PTS",
	WAITING_LEVEL: "WAITING_LEVEL"
}, hs = class extends Fa {
	constructor(e, t, n, r, i) {
		super(r, e.logger), this.hls = void 0, this.fragPrevious = null, this.fragCurrent = null, this.fragmentTracker = void 0, this.transmuxer = null, this._state = $.STOPPED, this.playlistType = void 0, this.media = null, this.mediaBuffer = null, this.config = void 0, this.bitrateTest = !1, this.lastCurrentTime = 0, this.nextLoadPosition = 0, this.startPosition = 0, this.startTimeOffset = null, this.retryDate = 0, this.levels = null, this.fragmentLoader = void 0, this.keyLoader = void 0, this.levelLastLoaded = null, this.startFragRequested = !1, this.decrypter = void 0, this.initPTS = [], this.buffering = !0, this.loadingParts = !1, this.loopSn = void 0, this.onMediaSeeking = () => {
			let { config: e, fragCurrent: t, media: n, mediaBuffer: r, state: i } = this, a = n ? n.currentTime : 0, o = Q.bufferInfo(r || n, a, e.maxBufferHole), s = !o.len;
			if (this.log(`Media seeking to ${W(a) ? a.toFixed(3) : a}, state: ${i}, ${s ? "out of" : "in"} buffer`), this.state === $.ENDED) this.resetLoadingState();
			else if (t) {
				let n = e.maxFragLookUpTolerance, r = t.start - n, i = t.start + t.duration + n;
				if (s || i < o.start || r > o.end) {
					let e = a > i;
					(a < r || e) && (e && t.loader && (this.log(`Cancelling fragment load for seek (sn: ${t.sn})`), t.abortRequests(), this.resetLoadingState()), this.fragPrevious = null);
				}
			}
			if (n && (this.fragmentTracker.removeFragmentsInRange(a, Infinity, this.playlistType, !0), a > this.lastCurrentTime && (this.lastCurrentTime = a), !this.loadingParts)) {
				let e = Math.max(o.end, a), t = this.shouldLoadParts(this.getLevelDetails(), e);
				t && (this.log(`LL-Part loading ON after seeking to ${a.toFixed(2)} with buffer @${e.toFixed(2)}`), this.loadingParts = t);
			}
			this.hls.hasEnoughToStart || (this.log(`Setting ${s ? "startPosition" : "nextLoadPosition"} to ${a} for seek without enough to start`), this.nextLoadPosition = a, s && (this.startPosition = a)), s && this.state === $.IDLE && this.tickImmediate();
		}, this.onMediaEnded = () => {
			this.log("setting startPosition to 0 because media ended"), this.startPosition = this.lastCurrentTime = 0;
		}, this.playlistType = i, this.hls = e, this.fragmentLoader = new Aa(e.config), this.keyLoader = n, this.fragmentTracker = t, this.config = e.config, this.decrypter = new Oa(e.config);
	}
	registerListeners() {
		let { hls: e } = this;
		e.on(q.MEDIA_ATTACHED, this.onMediaAttached, this), e.on(q.MEDIA_DETACHING, this.onMediaDetaching, this), e.on(q.MANIFEST_LOADING, this.onManifestLoading, this), e.on(q.MANIFEST_LOADED, this.onManifestLoaded, this), e.on(q.ERROR, this.onError, this);
	}
	unregisterListeners() {
		let { hls: e } = this;
		e.off(q.MEDIA_ATTACHED, this.onMediaAttached, this), e.off(q.MEDIA_DETACHING, this.onMediaDetaching, this), e.off(q.MANIFEST_LOADING, this.onManifestLoading, this), e.off(q.MANIFEST_LOADED, this.onManifestLoaded, this), e.off(q.ERROR, this.onError, this);
	}
	doTick() {
		this.onTickEnd();
	}
	onTickEnd() {}
	startLoad(e) {}
	stopLoad() {
		if (this.state === $.STOPPED) return;
		this.fragmentLoader.abort(), this.keyLoader.abort(this.playlistType);
		let e = this.fragCurrent;
		e != null && e.loader && (e.abortRequests(), this.fragmentTracker.removeFragment(e)), this.resetTransmuxer(), this.fragCurrent = null, this.fragPrevious = null, this.clearInterval(), this.clearNextTick(), this.state = $.STOPPED;
	}
	get startPositionValue() {
		let { nextLoadPosition: e, startPosition: t } = this;
		return t === -1 && e ? e : t;
	}
	get bufferingEnabled() {
		return this.buffering;
	}
	pauseBuffering() {
		this.buffering = !1;
	}
	resumeBuffering() {
		this.buffering = !0;
	}
	get inFlightFrag() {
		return {
			frag: this.fragCurrent,
			state: this.state
		};
	}
	_streamEnded(e, t) {
		if (t.live || !this.media) return !1;
		let n = e.end || 0, r = this.config.timelineOffset || 0;
		if (n <= r) return !1;
		let i = e.buffered;
		this.config.maxBufferHole && i && i.length > 1 && (e = Q.bufferedInfo(i, e.start, 0));
		let a = e.nextStart;
		if (a && a > r && a < t.edge || this.media.currentTime < e.start) return !1;
		let o = t.partList;
		if (o != null && o.length) {
			let e = o[o.length - 1];
			return Q.isBuffered(this.media, e.start + e.duration / 2);
		}
		let s = t.fragments[t.fragments.length - 1].type;
		return this.fragmentTracker.isEndListAppended(s);
	}
	getLevelDetails() {
		if (this.levels && this.levelLastLoaded !== null) return this.levelLastLoaded.details;
	}
	get timelineOffset() {
		let e = this.config.timelineOffset;
		return e ? this.getLevelDetails()?.appliedTimelineOffset || e : 0;
	}
	onMediaAttached(e, t) {
		let n = this.media = this.mediaBuffer = t.media;
		fs(n, "seeking", this.onMediaSeeking), fs(n, "ended", this.onMediaEnded);
		let r = this.config;
		this.levels && r.autoStartLoad && this.state === $.STOPPED && this.startLoad(r.startPosition);
	}
	onMediaDetaching(e, t) {
		let n = !!t.transferMedia, r = this.media;
		r !== null && (r.ended && (this.log("MSE detaching and video ended, reset startPosition"), this.startPosition = this.lastCurrentTime = 0), ps(r, "seeking", this.onMediaSeeking), ps(r, "ended", this.onMediaEnded), this.keyLoader && !n && this.keyLoader.detach(), this.media = this.mediaBuffer = null, this.loopSn = void 0, n ? (this.resetLoadingState(), this.resetTransmuxer()) : (this.loadingParts = !1, this.fragmentTracker.removeAllFragments(), this.stopLoad()));
	}
	onManifestLoading() {
		this.initPTS = [], this.levels = this.levelLastLoaded = this.fragCurrent = null, this.lastCurrentTime = this.startPosition = 0, this.startFragRequested = !1;
	}
	onError(e, t) {}
	onManifestLoaded(e, t) {
		this.startTimeOffset = t.startTimeOffset;
	}
	onHandlerDestroying() {
		this.stopLoad(), this.transmuxer &&= (this.transmuxer.destroy(), null), super.onHandlerDestroying(), this.hls = this.onMediaSeeking = this.onMediaEnded = null;
	}
	onHandlerDestroyed() {
		this.state = $.STOPPED, this.fragmentLoader && this.fragmentLoader.destroy(), this.keyLoader && this.keyLoader.destroy(), this.decrypter && this.decrypter.destroy(), this.hls = this.log = this.warn = this.decrypter = this.keyLoader = this.fragmentLoader = this.fragmentTracker = null, super.onHandlerDestroyed();
	}
	loadFragment(e, t, n) {
		this.startFragRequested = !0, this._loadFragForPlayback(e, t, n);
	}
	_loadFragForPlayback(e, t, n) {
		this._doFragLoad(e, t, n, (e) => {
			let t = e.frag;
			this.fragContextChanged(t) ? (this.warn(`${t.type} sn: ${t.sn}${e.part ? " part: " + e.part.index : ""} of ${this.fragInfo(t, !1, e.part)}) was dropped during download.`), this.fragmentTracker.removeFragment(t)) : (t.stats.chunkCount++, this._handleFragmentLoadProgress(e));
		}).then((e) => {
			if (!e) return;
			let t = this.state, n = e.frag;
			this.fragContextChanged(n) ? (t === $.FRAG_LOADING || !this.fragCurrent && t === $.PARSING) && (this.fragmentTracker.removeFragment(n), this.state = $.IDLE) : ("payload" in e && (this.log(`Loaded ${n.type} sn: ${n.sn} of ${this.playlistLabel()} ${n.level}`), this.hls.trigger(q.FRAG_LOADED, e)), this._handleFragmentLoadComplete(e));
		}).catch((t) => {
			this.state !== $.STOPPED && this.state !== $.ERROR && (this.warn(`Frag error: ${t?.message || t}`), this.resetFragmentLoading(e));
		});
	}
	clearTrackerIfNeeded(e) {
		let { fragmentTracker: t } = this;
		if (t.getState(e) === ga.APPENDING) {
			let n = e.type, r = this.getFwdBufferInfo(this.mediaBuffer, n), i = Math.max(e.duration, r ? r.len : this.config.maxBufferLength), a = this.backtrackFragment;
			((a ? e.sn - a.sn : 0) === 1 || this.reduceMaxBufferLength(i, e.duration)) && t.removeFragment(e);
		} else this.mediaBuffer?.buffered.length === 0 ? t.removeAllFragments() : t.hasParts(e.type) && (t.detectPartialFragments({
			frag: e,
			part: null,
			stats: e.stats,
			id: e.type
		}), t.getState(e) === ga.PARTIAL && t.removeFragment(e));
	}
	checkLiveUpdate(e) {
		if (e.updated && !e.live) {
			let t = e.fragments[e.fragments.length - 1];
			this.fragmentTracker.detectPartialFragments({
				frag: t,
				part: null,
				stats: t.stats,
				id: t.type
			});
		}
		e.fragments[0] || (e.deltaUpdateFailed = !0);
	}
	waitForLive(e) {
		let t = e.details;
		return t?.live && t.type !== "EVENT" && (this.levelLastLoaded !== e || t.expired);
	}
	flushMainBuffer(e, t, n = null) {
		if (!(e - t)) return;
		let r = {
			startOffset: e,
			endOffset: t,
			type: n
		};
		this.hls.trigger(q.BUFFER_FLUSHING, r);
	}
	_loadInitSegment(e, t) {
		this._doFragLoad(e, t).then((e) => {
			let t = e?.frag;
			if (!t || this.fragContextChanged(t) || !this.levels) throw Error("init load aborted");
			return e;
		}).then((e) => {
			let { hls: t } = this, { frag: n, payload: r } = e, i = n.decryptdata;
			if (r && r.byteLength > 0 && i != null && i.key && i.iv && to(i.method)) {
				let a = self.performance.now();
				return this.decrypter.decrypt(new Uint8Array(r), i.key.buffer, i.iv.buffer, no(i.method)).catch((e) => {
					throw t.trigger(q.ERROR, {
						type: G.MEDIA_ERROR,
						details: K.FRAG_DECRYPT_ERROR,
						fatal: !1,
						error: e,
						reason: e.message,
						frag: n
					}), e;
				}).then((r) => {
					let i = self.performance.now();
					return t.trigger(q.FRAG_DECRYPTED, {
						frag: n,
						payload: r,
						stats: {
							tstart: a,
							tdecrypt: i
						}
					}), e.payload = r, this.completeInitSegmentLoad(e);
				});
			}
			return this.completeInitSegmentLoad(e);
		}).catch((t) => {
			this.state !== $.STOPPED && this.state !== $.ERROR && (this.warn(t), this.resetFragmentLoading(e));
		});
	}
	completeInitSegmentLoad(e) {
		let { levels: t } = this;
		if (!t) throw Error("init load aborted, missing levels");
		let n = e.frag.stats;
		this.state !== $.STOPPED && (this.state = $.IDLE), e.frag.data = new Uint8Array(e.payload), n.parsing.start = n.buffering.start = self.performance.now(), n.parsing.end = n.buffering.end = self.performance.now(), this.tick();
	}
	unhandledEncryptionError(e, t) {
		var n, r;
		let i = e.tracks;
		if (i && !t.encrypted && ((n = i.audio) != null && n.encrypted || (r = i.video) != null && r.encrypted) && (!this.config.emeEnabled || !this.keyLoader.emeController)) {
			let e = this.media, n = /* @__PURE__ */ Error(`Encrypted track with no key in ${this.fragInfo(t)} (media ${e ? "attached mediaKeys: " + e.mediaKeys : "detached"})`);
			return this.warn(n.message), !e || e.mediaKeys ? !1 : (this.hls.trigger(q.ERROR, {
				type: G.KEY_SYSTEM_ERROR,
				details: K.KEY_SYSTEM_NO_KEYS,
				fatal: !1,
				error: n,
				frag: t
			}), this.resetTransmuxer(), !0);
		}
		return !1;
	}
	fragContextChanged(e) {
		let { fragCurrent: t } = this;
		return !e || !t || e.sn !== t.sn || e.level !== t.level;
	}
	fragBufferedComplete(e, t) {
		let n = this.mediaBuffer ? this.mediaBuffer : this.media;
		if (this.log(`Buffered ${e.type} sn: ${e.sn}${t ? " part: " + t.index : ""} of ${this.fragInfo(e, !1, t)} > buffer:${n ? ms.toString(Q.getBuffered(n)) : "(detached)"})`), lr(e)) {
			if (e.type !== Y.SUBTITLE) {
				let t = e.elementaryStreams;
				if (!Object.keys(t).some((e) => !!t[e])) {
					this.state = $.IDLE;
					return;
				}
			}
			let t = this.levels?.[e.level];
			t != null && t.fragmentError && (this.log(`Resetting level fragment error count of ${t.fragmentError} on frag buffered`), t.fragmentError = 0);
		}
		this.state = $.IDLE;
	}
	_handleFragmentLoadComplete(e) {
		let { transmuxer: t } = this;
		if (!t) return;
		let { frag: n, part: r, partsLoaded: i } = e, a = !i || i.length === 0 || i.some((e) => !e), o = new Ia(n.level, n.sn, n.stats.chunkCount + 1, 0, r ? r.index : -1, !a);
		t.flush(o);
	}
	_handleFragmentLoadProgress(e) {}
	_doFragLoad(e, t, n = null, r) {
		var i;
		this.fragCurrent = e;
		let a = t.details;
		if (!this.levels || !a) throw Error(`frag load aborted, missing level${a ? "" : " detail"}s`);
		let o = null;
		if (e.encrypted && !((i = e.decryptdata) != null && i.key)) {
			if (this.log(`Loading key for ${e.sn} of [${a.startSN}-${a.endSN}], ${this.playlistLabel()} ${e.level}`), this.state = $.KEY_LOADING, this.fragCurrent = e, o = this.keyLoader.load(e).then((e) => {
				if (!this.fragContextChanged(e.frag)) return this.hls.trigger(q.KEY_LOADED, e), this.state === $.KEY_LOADING && (this.state = $.IDLE), e;
			}), this.hls.trigger(q.KEY_LOADING, { frag: e }), this.fragCurrent === null) return this.log("context changed in KEY_LOADING"), Promise.resolve(null);
		} else e.encrypted || (o = this.keyLoader.loadClear(e, a.encryptedFragments, this.startFragRequested), o && this.log("[eme] blocking frag load until media-keys acquired"));
		let s = this.fragPrevious;
		if (lr(e) && (!s || e.sn !== s.sn)) {
			let n = this.shouldLoadParts(t.details, e.end);
			n !== this.loadingParts && (this.log(`LL-Part loading ${n ? "ON" : "OFF"} loading sn ${s?.sn}->${e.sn}`), this.loadingParts = n);
		}
		if (n = Math.max(e.start, n || 0), this.loadingParts && lr(e)) {
			let i = a.partList;
			if (i && r) {
				n > a.fragmentEnd && a.fragmentHint && (e = a.fragmentHint);
				let s = this.getNextPart(i, e, n);
				if (s > -1) {
					let c = i[s];
					e = this.fragCurrent = c.fragment, this.log(`Loading ${e.type} sn: ${e.sn} part: ${c.index} (${s}/${i.length - 1}) of ${this.fragInfo(e, !1, c)}) cc: ${e.cc} [${a.startSN}-${a.endSN}], target: ${parseFloat(n.toFixed(3))}`), this.nextLoadPosition = c.start + c.duration, this.state = $.FRAG_LOADING;
					let l;
					return l = o ? o.then((n) => !n || this.fragContextChanged(n.frag) ? null : this.doFragPartsLoad(e, c, t, r)).catch((e) => this.handleFragLoadError(e)) : this.doFragPartsLoad(e, c, t, r).catch((e) => this.handleFragLoadError(e)), this.hls.trigger(q.FRAG_LOADING, {
						frag: e,
						part: c,
						targetBufferTime: n
					}), this.fragCurrent === null ? Promise.reject(/* @__PURE__ */ Error("frag load aborted, context changed in FRAG_LOADING parts")) : l;
				}
				if (!e.url || this.loadedEndOfParts(i, n)) return Promise.resolve(null);
			}
		}
		if (lr(e) && this.loadingParts) this.log(`LL-Part loading OFF after next part miss @${n.toFixed(2)} Check buffer at sn: ${e.sn} loaded parts: ${a.partList?.filter((e) => e.loaded).map((e) => `[${e.start}-${e.end}]`)}`), this.loadingParts = !1;
		else if (!e.url) return Promise.resolve(null);
		this.log(`Loading ${e.type} sn: ${e.sn} of ${this.fragInfo(e, !1)}) cc: ${e.cc} ${"[" + a.startSN + "-" + a.endSN + "]"}, target: ${parseFloat(n.toFixed(3))}`), W(e.sn) && !this.bitrateTest && (this.nextLoadPosition = e.start + e.duration), this.state = $.FRAG_LOADING;
		let c = this.config.progressive && e.type !== Y.SUBTITLE, l;
		return l = c && o ? o.then((t) => !t || this.fragContextChanged(t.frag) ? null : this.fragmentLoader.load(e, r)).catch((e) => this.handleFragLoadError(e)) : Promise.all([this.fragmentLoader.load(e, c ? r : void 0), o]).then(([e]) => (!c && r && r(e), e)).catch((e) => this.handleFragLoadError(e)), this.hls.trigger(q.FRAG_LOADING, {
			frag: e,
			targetBufferTime: n
		}), this.fragCurrent === null ? Promise.reject(/* @__PURE__ */ Error("frag load aborted, context changed in FRAG_LOADING")) : l;
	}
	doFragPartsLoad(e, t, n, r) {
		return new Promise((i, a) => {
			let o = [], s = n.details?.partList, c = (t) => {
				this.fragmentLoader.loadPart(e, t, r).then((r) => {
					o[t.index] = r;
					let a = r.part;
					this.hls.trigger(q.FRAG_LOADED, r);
					let l = es(n.details, e.sn, t.index + 1) || ts(s, e.sn, t.index + 1);
					if (l) c(l);
					else return i({
						frag: e,
						part: a,
						partsLoaded: o
					});
				}).catch(a);
			};
			c(t);
		});
	}
	handleFragLoadError(e) {
		if ("data" in e) {
			let t = e.data;
			t.frag && t.details === K.INTERNAL_ABORTED ? this.handleFragLoadAborted(t.frag, t.part) : t.frag && t.type === G.KEY_SYSTEM_ERROR ? (t.frag.abortRequests(), this.resetStartWhenNotLoaded(), this.resetFragmentLoading(t.frag)) : this.hls.trigger(q.ERROR, t);
		} else this.hls.trigger(q.ERROR, {
			type: G.OTHER_ERROR,
			details: K.INTERNAL_EXCEPTION,
			err: e,
			error: e,
			fatal: !0
		});
		return null;
	}
	_handleTransmuxerFlush(e) {
		let t = this.getCurrentContext(e);
		if (!t || this.state !== $.PARSING) {
			!this.fragCurrent && this.state !== $.STOPPED && this.state !== $.ERROR && (this.state = $.IDLE);
			return;
		}
		let { frag: n, part: r, level: i } = t, a = self.performance.now();
		n.stats.parsing.end = a, r && (r.stats.parsing.end = a);
		let o = this.getLevelDetails(), s = o && n.sn > o.endSN || this.shouldLoadParts(o, n.end);
		s !== this.loadingParts && (this.log(`LL-Part loading ${s ? "ON" : "OFF"} after parsing segment ending @${n.end.toFixed(2)}`), this.loadingParts = s), this.updateLevelTiming(n, r, i, e.partial);
	}
	shouldLoadParts(e, t) {
		if (this.config.lowLatencyMode) {
			if (!e) return this.loadingParts;
			if (e.partList) {
				let n = e.partList[0];
				if (n.fragment.type === Y.SUBTITLE) return !1;
				if (t >= n.end + (e.fragmentHint?.duration || 0) && (this.hls.hasEnoughToStart ? this.media?.currentTime || this.lastCurrentTime : this.getLoadPosition()) > n.start - n.fragment.duration) return !0;
			}
		}
		return !1;
	}
	getCurrentContext(e) {
		let { levels: t, fragCurrent: n } = this, { level: r, sn: i, part: a } = e;
		if (!(t != null && t[r])) return this.warn(`Levels object was unset while buffering fragment ${i} of ${this.playlistLabel()} ${r}. The current chunk will not be buffered.`), null;
		let o = t[r], s = o.details, c = a > -1 ? es(s, i, a) : null, l = c ? c.fragment : $o(s, i, n);
		return l ? (n && n !== l && (l.stats = n.stats), {
			frag: l,
			part: c,
			level: o
		}) : null;
	}
	bufferFragmentData(e, t, n, r, i) {
		if (this.state !== $.PARSING) return;
		let { data1: a, data2: o } = e, s = a;
		if (o && (s = Ir(a, o)), !s.length) return;
		let c = this.initPTS[t.cc], l = c ? -c.baseTime / c.timescale : void 0, u = {
			type: e.type,
			frag: t,
			part: n,
			chunkMeta: r,
			offset: l,
			parent: t.type,
			data: s
		};
		if (this.hls.trigger(q.BUFFER_APPENDING, u), e.dropped && e.independent && !n) {
			if (i) return;
			this.flushBufferGap(t);
		}
	}
	flushBufferGap(e) {
		let t = this.media;
		if (!t) return;
		if (!Q.isBuffered(t, t.currentTime)) {
			this.flushMainBuffer(0, e.start);
			return;
		}
		let n = t.currentTime, r = Q.bufferInfo(t, n, 0), i = e.duration, a = Math.min(this.config.maxFragLookUpTolerance * 2, i * .25), o = Math.max(Math.min(e.start - a, r.end - a), n + a);
		e.start - o > a && this.flushMainBuffer(o, e.start);
	}
	getFwdBufferInfo(e, t) {
		var n;
		let r = this.getLoadPosition();
		if (!W(r)) return null;
		let i = this.lastCurrentTime > r || (n = this.media) != null && n.paused ? 0 : this.config.maxBufferHole;
		return this.getFwdBufferInfoAtPos(e, r, t, i);
	}
	getFwdBufferInfoAtPos(e, t, n, r) {
		let i = Q.bufferInfo(e, t, r);
		if (i.len === 0 && i.nextStart !== void 0) {
			let a = this.fragmentTracker.getBufferedFrag(t, n);
			if (a && (i.nextStart <= a.end || a.gap)) {
				let n = Math.max(Math.min(i.nextStart, a.end) - t, r);
				return Q.bufferInfo(e, t, n);
			}
		}
		return i;
	}
	getMaxBufferLength(e) {
		let { config: t } = this, n;
		return n = e ? Math.max(8 * t.maxBufferSize / e, t.maxBufferLength) : t.maxBufferLength, Math.min(n, t.maxMaxBufferLength);
	}
	reduceMaxBufferLength(e, t) {
		let n = this.config, r = Math.max(Math.min(e - t, n.maxBufferLength), t), i = Math.max(e - t * 3, n.maxMaxBufferLength / 2, r);
		return i >= r && (n.maxMaxBufferLength = i, this.warn(`Reduce max buffer length to ${i}s`), !0);
	}
	getAppendedFrag(e, t = Y.MAIN) {
		let n = this.fragmentTracker ? this.fragmentTracker.getAppendedFrag(e, t) : null;
		return n && "fragment" in n ? n.fragment : n;
	}
	getNextFragment(e, t) {
		let n = t.fragments, r = n.length;
		if (!r) return null;
		let { config: i } = this, a = n[0].start, o = i.lowLatencyMode && !!t.partList, s = null;
		if (t.live) {
			let n = i.initialLiveManifestSize;
			if (r < n) return this.warn(`Not enough fragments to start playback (have: ${r}, need: ${n})`), null;
			if (!t.PTSKnown && !this.startFragRequested && this.startPosition === -1 || e < a) {
				o && !this.loadingParts && (this.log("LL-Part loading ON for initial live fragment"), this.loadingParts = !0), s = this.getInitialLiveFragment(t);
				let n = this.hls.startPosition, r = this.hls.liveSyncPosition, i = s ? (n !== -1 && n >= a ? n : r) || s.start : e;
				this.log(`Setting startPosition to ${i} to match start frag at live edge. mainStart: ${n} liveSyncPosition: ${r} frag.start: ${s?.start}`), this.startPosition = this.nextLoadPosition = i;
			}
		} else e <= a && (s = n[0]);
		if (!s) {
			let n = this.loadingParts ? t.partEnd : t.fragmentEnd;
			s = this.getFragmentAtPosition(e, n, t);
		}
		let c = this.filterReplacedPrimary(s, t);
		if (!c && s) {
			let e = s.sn - t.startSN;
			c = this.filterReplacedPrimary(n[e + 1] || null, t);
		}
		return this.mapToInitFragWhenRequired(c);
	}
	isLoopLoading(e, t) {
		let n = this.fragmentTracker.getState(e);
		return (n === ga.OK || n === ga.PARTIAL && !!e.gap) && this.nextLoadPosition > t;
	}
	getNextFragmentLoopLoading(e, t, n, r, i) {
		let a = null;
		if (e.gap && (a = this.getNextFragment(this.nextLoadPosition, t), a && !a.gap && n.nextStart)) {
			let e = this.getFwdBufferInfoAtPos(this.mediaBuffer ? this.mediaBuffer : this.media, n.nextStart, r, 0);
			if (e !== null && n.len + e.len >= i) {
				let e = a.sn;
				return this.loopSn !== e && (this.log(`buffer full after gaps in "${r}" playlist starting at sn: ${e}`), this.loopSn = e), null;
			}
		}
		return this.loopSn = void 0, a;
	}
	get primaryPrefetch() {
		if (gs(this.config)) {
			var e;
			if ((e = this.hls.interstitialsManager) != null && (e = e.playingItem) != null && e.event) return !0;
		}
		return !1;
	}
	filterReplacedPrimary(e, t) {
		if (!e) return e;
		if (gs(this.config) && e.type !== Y.SUBTITLE) {
			let n = this.hls.interstitialsManager, r = n?.bufferingItem;
			if (r) {
				let n = r.event;
				if (n) {
					if (n.appendInPlace || Math.abs(e.start - r.start) > 1 || r.start === 0) return null;
				} else if (e.end <= r.start && t?.live === !1 || e.start > r.end && r.nextEvent && (r.nextEvent.appendInPlace || e.start - r.end > 1)) return null;
			}
			let i = n?.playerQueue;
			if (i) for (let t = i.length; t--;) {
				let n = i[t].interstitial;
				if (n.appendInPlace && e.start >= n.startTime && e.end <= n.resumeTime) return null;
			}
		}
		return e;
	}
	mapToInitFragWhenRequired(e) {
		return e != null && e.initSegment && !e.initSegment.data && !this.bitrateTest ? e.initSegment : e;
	}
	getNextPart(e, t, n) {
		let r = -1, i = !1, a = !0;
		for (let o = 0, s = e.length; o < s; o++) {
			let s = e[o];
			if (a &&= !s.independent, r > -1 && n < s.start) break;
			let c = s.loaded;
			c ? r = -1 : (i || (s.independent || a) && s.fragment === t) && (s.fragment !== t && this.warn(`Need buffer at ${n} but next unloaded part starts at ${s.start}`), r = o), i = c;
		}
		return r;
	}
	loadedEndOfParts(e, t) {
		let n;
		for (let r = e.length; r--;) {
			if (n = e[r], !n.loaded) return !1;
			if (t > n.start) return !0;
		}
		return !1;
	}
	getInitialLiveFragment(e) {
		let t = e.fragments, n = this.fragPrevious, r = null;
		if (n) {
			if (e.hasProgramDateTime && (this.log(`Live playlist, switching playlist, load frag with same PDT: ${n.programDateTime}`), r = Zi(t, n.endProgramDateTime, this.config.maxFragLookUpTolerance)), !r) {
				let i = n.sn + 1;
				if (i >= e.startSN && i <= e.endSN) {
					let a = t[i - e.startSN];
					n.cc === a.cc && (r = a, this.log(`Live playlist, switching playlist, load frag with next SN: ${r.sn}`));
				}
				r || (r = na(e, n.cc, n.end), r && this.log(`Live playlist, switching playlist, load frag with same CC: ${r.sn}`));
			}
		} else {
			let t = this.hls.liveSyncPosition;
			t !== null && (r = this.getFragmentAtPosition(t, this.bitrateTest ? e.fragmentEnd : e.edge, e));
		}
		return r;
	}
	getFragmentAtPosition(e, t, n) {
		let { config: r } = this, { fragPrevious: i } = this, { fragments: a, endSN: o } = n, { fragmentHint: s } = n, { maxFragLookUpTolerance: c } = r, l = n.partList, u = !!(this.loadingParts && l != null && l.length && s);
		u && !this.bitrateTest && l[l.length - 1].fragment.sn === s.sn && (a = a.concat(s), o = s.sn);
		let d;
		if (e < t) {
			var f;
			let n = e < this.lastCurrentTime || e > t - c || (f = this.media) != null && f.paused || !this.startFragRequested ? 0 : c;
			d = Qi(i, a, e, n);
		} else d = a[a.length - 1];
		if (d) {
			let e = d.sn - n.startSN, t = this.fragmentTracker.getState(d);
			if ((t === ga.OK || t === ga.PARTIAL && d.gap) && (i = d), i && d.sn === i.sn && (!u || l[0].fragment.sn > d.sn || !n.live) && d.level === i.level) {
				let t = a[e + 1];
				d = d.sn < o && this.fragmentTracker.getState(t) !== ga.OK ? t : null;
			}
		}
		return d;
	}
	alignPlaylists(e, t, n) {
		let r = e.fragments.length;
		if (!r) return this.warn("No fragments in live playlist"), 0;
		let i = e.fragmentStart, a = !t, o = e.alignedSliding && W(i);
		if (a || !o && !i) {
			ls(n, e);
			let i = e.fragmentStart;
			return this.log(`Live playlist sliding: ${i.toFixed(2)} start-sn: ${t ? t.startSN : "na"}->${e.startSN} fragments: ${r}`), i;
		}
		return i;
	}
	waitForCdnTuneIn(e) {
		return e.live && e.canBlockReload && e.partTarget && e.tuneInGoal > Math.max(e.partHoldBack, e.partTarget * 3);
	}
	setStartPosition(e, t) {
		let n = this.startPosition;
		n < t && (n = -1);
		let r = this.timelineOffset;
		if (n === -1) {
			let i = this.startTimeOffset !== null, a = i ? this.startTimeOffset : e.startTimeOffset;
			a !== null && W(a) ? (n = t + a, a < 0 && (n += e.edge), n = Math.min(Math.max(t, n), t + e.totalduration), this.log(`Setting startPosition to ${n} for start time offset ${a} found in ${i ? "multivariant" : "media"} playlist`), this.startPosition = n) : e.live ? (n = this.hls.liveSyncPosition || t, this.log(`Setting startPosition to -1 to start at live edge ${n}`), this.startPosition = -1) : (this.log("setting startPosition to 0 by default"), this.startPosition = n = 0), this.lastCurrentTime = n + r;
		}
		this.nextLoadPosition = n + r;
	}
	getLoadPosition() {
		var e;
		let { media: t } = this, n = 0;
		return (e = this.hls) != null && e.hasEnoughToStart && t ? n = t.currentTime : this.nextLoadPosition >= 0 && (n = this.nextLoadPosition), n;
	}
	handleFragLoadAborted(e, t) {
		this.transmuxer && e.type === this.playlistType && lr(e) && e.stats.aborted && (this.log(`Fragment ${e.sn}${t ? " part " + t.index : ""} of ${this.playlistLabel()} ${e.level} was aborted`), this.resetFragmentLoading(e));
	}
	resetFragmentLoading(e) {
		(!this.fragCurrent || !this.fragContextChanged(e) && this.state !== $.FRAG_LOADING_WAITING_RETRY) && (this.state = $.IDLE);
	}
	onFragmentOrKeyLoadError(e, t) {
		if (t.chunkMeta && !t.frag) {
			let e = this.getCurrentContext(t.chunkMeta);
			e && (t.frag = e.frag);
		}
		let n = t.frag;
		if (!n || n.type !== e || !this.levels) return;
		if (this.fragContextChanged(n)) {
			this.warn(`Frag load error must match current frag to retry ${n.url} > ${this.fragCurrent?.url}`);
			return;
		}
		let r = t.details === K.FRAG_GAP;
		r && this.fragmentTracker.fragBuffered(n, !0);
		let i = t.errorAction;
		if (!i) {
			this.state = $.ERROR;
			return;
		}
		let { action: a, flags: o, retryCount: s = 0, retryConfig: c } = i, l = !!c, u = l && a === fa.RetryRequest, d = l && !i.resolved && o === pa.MoveAllAlternatesMatchingHost, f = this.hls.latestLevelDetails?.live;
		if (!u && d && lr(n) && !n.endList && f && !aa(t)) this.resetFragmentErrors(e), this.treatAsGap(n), i.resolved = !0;
		else if ((u || d) && s < c.maxNumRetry) {
			let r = da(t.response?.code), a = sa(c, s);
			if (this.resetStartWhenNotLoaded(), this.retryDate = self.performance.now() + a, this.state = $.FRAG_LOADING_WAITING_RETRY, i.resolved = !0, r) {
				this.log("Waiting for connection (offline)"), this.retryDate = Infinity, t.reason = "offline";
				return;
			}
			this.warn(`Fragment ${n.sn} of ${e} ${n.level} errored with ${t.details}, retrying loading ${s + 1}/${c.maxNumRetry} in ${a}ms`);
		} else if (c) {
			if (this.resetFragmentErrors(e), s < c.maxNumRetry) !r && a !== fa.RemoveAlternatePermanently && (i.resolved = !0);
			else {
				this.warn(`${t.details} reached or exceeded max retry (${s})`);
				return;
			}
		} else this.state = a === fa.SendAlternateToPenaltyBox ? $.WAITING_LEVEL : $.ERROR;
		this.tickImmediate();
	}
	checkRetryDate() {
		let e = self.performance.now(), t = this.retryDate, n = t === Infinity;
		(!t || e >= t || n && !da(0)) && (n && this.log("Connection restored (online)"), this.resetStartWhenNotLoaded(), this.state = $.IDLE);
	}
	reduceLengthAndFlushBuffer(e) {
		if (this.state === $.PARSING || this.state === $.PARSED) {
			let t = e.frag, n = e.parent, r = this.getFwdBufferInfo(this.mediaBuffer, n), i = r && r.len > .5;
			i && this.reduceMaxBufferLength(r.len, t?.duration || 10);
			let a = !i;
			return a && this.warn(`Buffer full error while media.currentTime (${this.getLoadPosition()}) is not buffered, flush ${n} buffer`), t && (this.fragmentTracker.removeFragment(t), this.nextLoadPosition = t.start), this.resetLoadingState(), a;
		}
		return !1;
	}
	resetFragmentErrors(e) {
		e === Y.AUDIO && (this.fragCurrent = null), this.hls.hasEnoughToStart || (this.startFragRequested = !1), this.state !== $.STOPPED && (this.state = $.IDLE);
	}
	afterBufferFlushed(e, t, n) {
		if (!e) return;
		let r = Q.getBuffered(e);
		this.fragmentTracker.detectEvictedFragments(t, r, n), this.state === $.ENDED && this.resetLoadingState();
	}
	resetLoadingState() {
		this.log("Reset loading state"), this.fragCurrent = null, this.fragPrevious = null, this.state !== $.STOPPED && (this.state = $.IDLE);
	}
	resetStartWhenNotLoaded() {
		if (!this.hls.hasEnoughToStart) {
			this.startFragRequested = !1;
			let e = this.levelLastLoaded, t = e ? e.details : null;
			t != null && t.live ? (this.log("resetting startPosition for live start"), this.startPosition = -1, this.setStartPosition(t, t.fragmentStart), this.resetLoadingState()) : this.nextLoadPosition = this.startPosition;
		}
	}
	resetWhenMissingContext(e) {
		this.log(`Loading context changed while buffering sn ${e.sn} of ${this.playlistLabel()} ${e.level === -1 ? "<removed>" : e.level}. This chunk will not be buffered.`), this.removeUnbufferedFrags(), this.resetStartWhenNotLoaded(), this.resetLoadingState();
	}
	removeUnbufferedFrags(e = 0) {
		this.fragmentTracker.removeFragmentsInRange(e, Infinity, this.playlistType, !1, !0);
	}
	updateLevelTiming(e, t, n, r) {
		let i = n.details;
		if (!i) this.warn("level.details undefined");
		else {
			if (!Object.keys(e.elementaryStreams).reduce((t, a) => {
				let o = e.elementaryStreams[a];
				if (o) {
					let s = o.endPTS - o.startPTS;
					if (s <= 0) return this.warn(`Could not parse fragment ${e.sn} ${a} duration reliably (${s})`), t || !1;
					let c = r ? 0 : Wo(i, e, o.startPTS, o.endPTS, o.startDTS, o.endDTS, this);
					return this.hls.trigger(q.LEVEL_PTS_UPDATED, {
						details: i,
						level: n,
						drift: c,
						type: a,
						frag: e,
						start: o.startPTS,
						end: o.endPTS
					}), !0;
				}
				return t;
			}, !1)) {
				let t = this.transmuxer?.error === null;
				if ((n.fragmentError === 0 || t && (n.fragmentError < 2 || e.endList)) && this.treatAsGap(e, n), t) {
					let t = /* @__PURE__ */ Error(`Found no media in fragment ${e.sn} of ${this.playlistLabel()} ${e.level} resetting transmuxer to fallback to playlist timing`);
					if (this.warn(t.message), this.hls.trigger(q.ERROR, {
						type: G.MEDIA_ERROR,
						details: K.FRAG_PARSING_ERROR,
						fatal: !1,
						error: t,
						frag: e,
						reason: `Found no media in msn ${e.sn} of ${this.playlistLabel()} "${n.url}"`
					}), !this.hls) return;
					this.resetTransmuxer();
				}
			}
			this.state = $.PARSED, this.log(`Parsed ${e.type} sn: ${e.sn}${t ? " part: " + t.index : ""} of ${this.fragInfo(e, !1, t)})`), this.hls.trigger(q.FRAG_PARSED, {
				frag: e,
				part: t
			});
		}
	}
	playlistLabel() {
		return this.playlistType === Y.MAIN ? "level" : "track";
	}
	fragInfo(e, t = !0, n) {
		return `${this.playlistLabel()} ${e.level} (${n ? "part" : "frag"}:[${((t && !n ? e.startPTS : (n || e).start) ?? NaN).toFixed(3)}-${((t && !n ? e.endPTS : (n || e).end) ?? NaN).toFixed(3)}]${n && e.type === "main" ? "INDEPENDENT=" + (n.independent ? "YES" : "NO") : ""}`;
	}
	treatAsGap(e, t) {
		t && t.fragmentError++, e.gap = !0, this.fragmentTracker.removeFragment(e), this.fragmentTracker.fragBuffered(e, !0);
	}
	resetTransmuxer() {
		var e;
		(e = this.transmuxer) == null || e.reset();
	}
	recoverWorkerError(e) {
		e.event === "demuxerWorker" && (this.fragmentTracker.removeAllFragments(), this.transmuxer &&= (this.transmuxer.destroy(), null), this.resetStartWhenNotLoaded(), this.resetLoadingState());
	}
	set state(e) {
		let t = this._state;
		t !== e && (this._state = e, this.log(`${t}->${e}`));
	}
	get state() {
		return this._state;
	}
};
function gs(e) {
	return !!e.interstitialsController && e.enableInterstitialPlayback !== !1;
}
var _s = class {
	constructor() {
		this.chunks = [], this.dataLength = 0;
	}
	push(e) {
		this.chunks.push(e), this.dataLength += e.length;
	}
	flush() {
		let { chunks: e, dataLength: t } = this, n;
		if (e.length) n = e.length === 1 ? e[0] : vs(e, t);
		else return /* @__PURE__ */ new Uint8Array();
		return this.reset(), n;
	}
	reset() {
		this.chunks.length = 0, this.dataLength = 0;
	}
};
function vs(e, t) {
	let n = new Uint8Array(t), r = 0;
	for (let t = 0; t < e.length; t++) {
		let i = e[t];
		n.set(i, r), r += i.length;
	}
	return n;
}
var ys = { exports: {} }, bs;
function xs() {
	return bs || (bs = 1, (function(e) {
		var t = Object.prototype.hasOwnProperty, n = "~";
		function r() {}
		Object.create && (r.prototype = Object.create(null), new r().__proto__ || (n = !1));
		function i(e, t, n) {
			this.fn = e, this.context = t, this.once = n || !1;
		}
		function a(e, t, r, a, o) {
			if (typeof r != "function") throw TypeError("The listener must be a function");
			var s = new i(r, a || e, o), c = n ? n + t : t;
			return e._events[c] ? e._events[c].fn ? e._events[c] = [e._events[c], s] : e._events[c].push(s) : (e._events[c] = s, e._eventsCount++), e;
		}
		function o(e, t) {
			--e._eventsCount === 0 ? e._events = new r() : delete e._events[t];
		}
		function s() {
			this._events = new r(), this._eventsCount = 0;
		}
		s.prototype.eventNames = function() {
			var e = [], r, i;
			if (this._eventsCount === 0) return e;
			for (i in r = this._events) t.call(r, i) && e.push(n ? i.slice(1) : i);
			return Object.getOwnPropertySymbols ? e.concat(Object.getOwnPropertySymbols(r)) : e;
		}, s.prototype.listeners = function(e) {
			var t = n ? n + e : e, r = this._events[t];
			if (!r) return [];
			if (r.fn) return [r.fn];
			for (var i = 0, a = r.length, o = Array(a); i < a; i++) o[i] = r[i].fn;
			return o;
		}, s.prototype.listenerCount = function(e) {
			var t = n ? n + e : e, r = this._events[t];
			return r ? r.fn ? 1 : r.length : 0;
		}, s.prototype.emit = function(e, t, r, i, a, o) {
			var s = n ? n + e : e;
			if (!this._events[s]) return !1;
			var c = this._events[s], l = arguments.length, u, d;
			if (c.fn) {
				switch (c.once && this.removeListener(e, c.fn, void 0, !0), l) {
					case 1: return c.fn.call(c.context), !0;
					case 2: return c.fn.call(c.context, t), !0;
					case 3: return c.fn.call(c.context, t, r), !0;
					case 4: return c.fn.call(c.context, t, r, i), !0;
					case 5: return c.fn.call(c.context, t, r, i, a), !0;
					case 6: return c.fn.call(c.context, t, r, i, a, o), !0;
				}
				for (d = 1, u = Array(l - 1); d < l; d++) u[d - 1] = arguments[d];
				c.fn.apply(c.context, u);
			} else {
				var f = c.length, p;
				for (d = 0; d < f; d++) switch (c[d].once && this.removeListener(e, c[d].fn, void 0, !0), l) {
					case 1:
						c[d].fn.call(c[d].context);
						break;
					case 2:
						c[d].fn.call(c[d].context, t);
						break;
					case 3:
						c[d].fn.call(c[d].context, t, r);
						break;
					case 4:
						c[d].fn.call(c[d].context, t, r, i);
						break;
					default:
						if (!u) for (p = 1, u = Array(l - 1); p < l; p++) u[p - 1] = arguments[p];
						c[d].fn.apply(c[d].context, u);
				}
			}
			return !0;
		}, s.prototype.on = function(e, t, n) {
			return a(this, e, t, n, !1);
		}, s.prototype.once = function(e, t, n) {
			return a(this, e, t, n, !0);
		}, s.prototype.removeListener = function(e, t, r, i) {
			var a = n ? n + e : e;
			if (!this._events[a]) return this;
			if (!t) return o(this, a), this;
			var s = this._events[a];
			if (s.fn) s.fn !== t || i && !s.once || r && s.context !== r || o(this, a);
			else {
				for (var c = 0, l = [], u = s.length; c < u; c++) (s[c].fn !== t || i && !s[c].once || r && s[c].context !== r) && l.push(s[c]);
				l.length ? this._events[a] = l.length === 1 ? l[0] : l : o(this, a);
			}
			return this;
		}, s.prototype.removeAllListeners = function(e) {
			var t;
			return e ? (t = n ? n + e : e, this._events[t] && o(this, t)) : (this._events = new r(), this._eventsCount = 0), this;
		}, s.prototype.off = s.prototype.removeListener, s.prototype.addListener = s.prototype.on, s.prefixed = n, s.EventEmitter = s, e.exports = s;
	})(ys)), ys.exports;
}
var Ss = /*@__PURE__*/ tr(xs()), Cs = "1.6.15", ws = {};
function Ts() {
	return typeof __HLS_WORKER_BUNDLE__ == "function";
}
function Es() {
	let e = ws[Cs];
	if (e) return e.clientCount++, e;
	let t = new self.Blob([`var exports={};var module={exports:exports};function define(f){f()};define.amd=true;(${__HLS_WORKER_BUNDLE__.toString()})(true);`], { type: "text/javascript" }), n = self.URL.createObjectURL(t), r = {
		worker: new self.Worker(n),
		objectURL: n,
		clientCount: 1
	};
	return ws[Cs] = r, r;
}
function Ds(e) {
	let t = ws[e];
	if (t) return t.clientCount++, t;
	let n = new self.URL(e, self.location.href).href, r = {
		worker: new self.Worker(n),
		scriptURL: n,
		clientCount: 1
	};
	return ws[e] = r, r;
}
function Os(e) {
	let t = ws[e || Cs];
	if (t && t.clientCount-- === 1) {
		let { worker: n, objectURL: r } = t;
		delete ws[e || Cs], r && self.URL.revokeObjectURL(r), n.terminate();
	}
}
function ks(e, t) {
	return t + 10 <= e.length && e[t] === 51 && e[t + 1] === 68 && e[t + 2] === 73 && e[t + 3] < 255 && e[t + 4] < 255 && e[t + 6] < 128 && e[t + 7] < 128 && e[t + 8] < 128 && e[t + 9] < 128;
}
function As(e, t) {
	return t + 10 <= e.length && e[t] === 73 && e[t + 1] === 68 && e[t + 2] === 51 && e[t + 3] < 255 && e[t + 4] < 255 && e[t + 6] < 128 && e[t + 7] < 128 && e[t + 8] < 128 && e[t + 9] < 128;
}
function js(e, t) {
	let n = 0;
	return n = (e[t] & 127) << 21, n |= (e[t + 1] & 127) << 14, n |= (e[t + 2] & 127) << 7, n |= e[t + 3] & 127, n;
}
function Ms(e, t) {
	let n = t, r = 0;
	for (; As(e, t);) {
		r += 10;
		let n = js(e, t + 6);
		r += n, ks(e, t + 10) && (r += 10), t += r;
	}
	if (r > 0) return e.subarray(n, n + r);
}
function Ns(e, t, n, r) {
	let i = [
		96e3,
		88200,
		64e3,
		48e3,
		44100,
		32e3,
		24e3,
		22050,
		16e3,
		12e3,
		11025,
		8e3,
		7350
	], a = t[n + 2], o = a >> 2 & 15;
	if (o > 12) {
		let t = /* @__PURE__ */ Error(`invalid ADTS sampling index:${o}`);
		e.emit(q.ERROR, q.ERROR, {
			type: G.MEDIA_ERROR,
			details: K.FRAG_PARSING_ERROR,
			fatal: !0,
			error: t,
			reason: t.message
		});
		return;
	}
	let s = (a >> 6 & 3) + 1, c = t[n + 3] >> 6 & 3 | (a & 1) << 2, l = "mp4a.40." + s, u = i[o], d = o;
	(s === 5 || s === 29) && (d -= 3);
	let f = [s << 3 | (d & 14) >> 1, (d & 1) << 7 | c << 3];
	return Jn.log(`manifest codec:${r}, parsed codec:${l}, channels:${c}, rate:${u} (ADTS object type:${s} sampling index:${o})`), {
		config: f,
		samplerate: u,
		channelCount: c,
		codec: l,
		parsedCodec: l,
		manifestCodec: r
	};
}
function Ps(e, t) {
	return e[t] === 255 && (e[t + 1] & 246) == 240;
}
function Fs(e, t) {
	return e[t + 1] & 1 ? 7 : 9;
}
function Is(e, t) {
	return (e[t + 3] & 3) << 11 | e[t + 4] << 3 | (e[t + 5] & 224) >>> 5;
}
function Ls(e, t) {
	return t + 5 < e.length;
}
function Rs(e, t) {
	return t + 1 < e.length && Ps(e, t);
}
function zs(e, t) {
	return Ls(e, t) && Ps(e, t) && Is(e, t) <= e.length - t;
}
function Bs(e, t) {
	if (Rs(e, t)) {
		let n = Fs(e, t);
		if (t + n >= e.length) return !1;
		let r = Is(e, t);
		if (r <= n) return !1;
		let i = t + r;
		return i === e.length || Rs(e, i);
	}
	return !1;
}
function Vs(e, t, n, r, i) {
	if (!e.samplerate) {
		let a = Ns(t, n, r, i);
		if (!a) return;
		Fn(e, a);
	}
}
function Hs(e) {
	return 9216e4 / e;
}
function Us(e, t) {
	let n = Fs(e, t);
	if (t + n <= e.length) {
		let r = Is(e, t) - n;
		if (r > 0) return {
			headerLength: n,
			frameLength: r
		};
	}
}
function Ws(e, t, n, r, i) {
	let a = r + i * Hs(e.samplerate), o = Us(t, n), s;
	if (o) {
		let { frameLength: r, headerLength: i } = o, c = i + r, l = Math.max(0, n + c - t.length);
		l ? (s = new Uint8Array(c - i), s.set(t.subarray(n + i, t.length), 0)) : s = t.subarray(n + i, n + c);
		let u = {
			unit: s,
			pts: a
		};
		return l || e.samples.push(u), {
			sample: u,
			length: c,
			missing: l
		};
	}
	let c = t.length - n;
	return s = new Uint8Array(c), s.set(t.subarray(n, t.length), 0), {
		sample: {
			unit: s,
			pts: a
		},
		length: c,
		missing: -1
	};
}
function Gs(e, t) {
	return As(e, t) && js(e, t + 6) + 10 <= e.length - t;
}
function Ks(e) {
	return e instanceof ArrayBuffer ? e : e.byteOffset == 0 && e.byteLength == e.buffer.byteLength ? e.buffer : new Uint8Array(e).buffer;
}
function qs(e, t = 0, n = Infinity) {
	return Js(e, t, n, Uint8Array);
}
function Js(e, t, n, r) {
	let i = Ys(e), a = 1;
	"BYTES_PER_ELEMENT" in r && (a = r.BYTES_PER_ELEMENT);
	let o = Xs(e) ? e.byteOffset : 0, s = (o + e.byteLength) / a, c = (o + t) / a, l = Math.floor(Math.max(0, Math.min(c, s)));
	return new r(i, l, Math.floor(Math.min(l + Math.max(n, 0), s)) - l);
}
function Ys(e) {
	return e instanceof ArrayBuffer ? e : e.buffer;
}
function Xs(e) {
	return e && e.buffer instanceof ArrayBuffer && e.byteLength !== void 0 && e.byteOffset !== void 0;
}
function Zs(e) {
	let t = {
		key: e.type,
		description: "",
		data: "",
		mimeType: null,
		pictureType: null
	};
	if (e.size < 2) return;
	if (e.data[0] !== 3) {
		console.log("Ignore frame with unrecognized character encoding");
		return;
	}
	let n = e.data.subarray(1).indexOf(0);
	if (n === -1) return;
	let r = Qn(qs(e.data, 1, n)), i = e.data[2 + n], a = e.data.subarray(3 + n).indexOf(0);
	if (a === -1) return;
	let o = Qn(qs(e.data, 3 + n, a)), s;
	return s = r === "-->" ? Qn(qs(e.data, 4 + n + a)) : Ks(e.data.subarray(4 + n + a)), t.mimeType = r, t.pictureType = i, t.description = o, t.data = s, t;
}
function Qs(e) {
	if (e.size < 2) return;
	let t = Qn(e.data, !0), n = new Uint8Array(e.data.subarray(t.length + 1));
	return {
		key: e.type,
		info: t,
		data: n.buffer
	};
}
function $s(e) {
	if (e.size < 2) return;
	if (e.type === "TXXX") {
		let t = 1, n = Qn(e.data.subarray(t), !0);
		t += n.length + 1;
		let r = Qn(e.data.subarray(t));
		return {
			key: e.type,
			info: n,
			data: r
		};
	}
	let t = Qn(e.data.subarray(1));
	return {
		key: e.type,
		info: "",
		data: t
	};
}
function ec(e) {
	if (e.type === "WXXX") {
		if (e.size < 2) return;
		let t = 1, n = Qn(e.data.subarray(t), !0);
		t += n.length + 1;
		let r = Qn(e.data.subarray(t));
		return {
			key: e.type,
			info: n,
			data: r
		};
	}
	let t = Qn(e.data);
	return {
		key: e.type,
		info: "",
		data: t
	};
}
function tc(e) {
	return e.type === "PRIV" ? Qs(e) : e.type[0] === "W" ? ec(e) : e.type === "APIC" ? Zs(e) : $s(e);
}
function nc(e) {
	let t = String.fromCharCode(e[0], e[1], e[2], e[3]), n = js(e, 4);
	return {
		type: t,
		size: n,
		data: e.subarray(10, 10 + n)
	};
}
var rc = 10, ic = 10;
function ac(e) {
	let t = 0, n = [];
	for (; As(e, t);) {
		let r = js(e, t + 6);
		e[t + 5] >> 6 & 1 && (t += rc), t += rc;
		let i = t + r;
		for (; t + ic < i;) {
			let r = nc(e.subarray(t)), i = tc(r);
			i && n.push(i), t += r.size + rc;
		}
		ks(e, t) && (t += rc);
	}
	return n;
}
function oc(e) {
	return e && e.key === "PRIV" && e.info === "com.apple.streaming.transportStreamTimestamp";
}
function sc(e) {
	if (e.data.byteLength === 8) {
		let t = new Uint8Array(e.data), n = t[3] & 1, r = (t[4] << 23) + (t[5] << 15) + (t[6] << 7) + t[7];
		return r /= 45, n && (r += 47721858.84), Math.round(r);
	}
}
function cc(e) {
	let t = ac(e);
	for (let e = 0; e < t.length; e++) {
		let n = t[e];
		if (oc(n)) return sc(n);
	}
}
var lc = /*#__PURE__*/ function(e) {
	return e.audioId3 = "org.id3", e.dateRange = "com.apple.quicktime.HLS", e.emsg = "https://aomedia.org/emsg/ID3", e.misbklv = "urn:misb:KLV:bin:1910.1", e;
}({});
function uc(e = "", t = 9e4) {
	return {
		type: e,
		id: -1,
		pid: -1,
		inputTimeScale: t,
		sequenceNumber: -1,
		samples: [],
		dropped: 0
	};
}
var dc = class {
	constructor() {
		this._audioTrack = void 0, this._id3Track = void 0, this.frameIndex = 0, this.cachedData = null, this.basePTS = null, this.initPTS = null, this.lastPTS = null;
	}
	resetInitSegment(e, t, n, r) {
		this._id3Track = {
			type: "id3",
			id: 3,
			pid: -1,
			inputTimeScale: 9e4,
			sequenceNumber: 0,
			samples: [],
			dropped: 0
		};
	}
	resetTimeStamp(e) {
		this.initPTS = e, this.resetContiguity();
	}
	resetContiguity() {
		this.basePTS = null, this.lastPTS = null, this.frameIndex = 0;
	}
	canParse(e, t) {
		return !1;
	}
	appendFrame(e, t, n) {}
	demux(e, t) {
		this.cachedData &&= (e = Ir(this.cachedData, e), null);
		let n = Ms(e, 0), r = n ? n.length : 0, i, a = this._audioTrack, o = this._id3Track, s = n ? cc(n) : void 0, c = e.length;
		for ((this.basePTS === null || this.frameIndex === 0 && W(s)) && (this.basePTS = fc(s, t, this.initPTS), this.lastPTS = this.basePTS), this.lastPTS === null && (this.lastPTS = this.basePTS), n && n.length > 0 && o.samples.push({
			pts: this.lastPTS,
			dts: this.lastPTS,
			data: n,
			type: lc.audioId3,
			duration: Infinity
		}); r < c;) {
			if (this.canParse(e, r)) {
				let t = this.appendFrame(a, e, r);
				t ? (this.frameIndex++, this.lastPTS = t.sample.pts, r += t.length, i = r) : r = c;
			} else Gs(e, r) ? (n = Ms(e, r), o.samples.push({
				pts: this.lastPTS,
				dts: this.lastPTS,
				data: n,
				type: lc.audioId3,
				duration: Infinity
			}), r += n.length, i = r) : r++;
			if (r === c && i !== c) {
				let t = e.slice(i);
				this.cachedData = this.cachedData ? Ir(this.cachedData, t) : t;
			}
		}
		return {
			audioTrack: a,
			videoTrack: uc(),
			id3Track: o,
			textTrack: uc()
		};
	}
	demuxSampleAes(e, t, n) {
		return Promise.reject(/* @__PURE__ */ Error(`[${this}] This demuxer does not support Sample-AES decryption`));
	}
	flush(e) {
		let t = this.cachedData;
		return t && (this.cachedData = null, this.demux(t, 0)), {
			audioTrack: this._audioTrack,
			videoTrack: uc(),
			id3Track: this._id3Track,
			textTrack: uc()
		};
	}
	destroy() {
		this.cachedData = null, this._audioTrack = this._id3Track = void 0;
	}
}, fc = (e, t, n) => {
	if (W(e)) return e * 90;
	let r = n ? n.baseTime * 9e4 / n.timescale : 0;
	return t * 9e4 + r;
}, pc = null, mc = [
	32,
	64,
	96,
	128,
	160,
	192,
	224,
	256,
	288,
	320,
	352,
	384,
	416,
	448,
	32,
	48,
	56,
	64,
	80,
	96,
	112,
	128,
	160,
	192,
	224,
	256,
	320,
	384,
	32,
	40,
	48,
	56,
	64,
	80,
	96,
	112,
	128,
	160,
	192,
	224,
	256,
	320,
	32,
	48,
	56,
	64,
	80,
	96,
	112,
	128,
	144,
	160,
	176,
	192,
	224,
	256,
	8,
	16,
	24,
	32,
	40,
	48,
	56,
	64,
	80,
	96,
	112,
	128,
	144,
	160
], hc = [
	44100,
	48e3,
	32e3,
	22050,
	24e3,
	16e3,
	11025,
	12e3,
	8e3
], gc = [
	[
		0,
		72,
		144,
		12
	],
	[
		0,
		0,
		0,
		0
	],
	[
		0,
		72,
		144,
		12
	],
	[
		0,
		144,
		144,
		12
	]
], _c = [
	0,
	1,
	1,
	4
];
function vc(e, t, n, r, i) {
	if (n + 24 > t.length) return;
	let a = yc(t, n);
	if (a && n + a.frameLength <= t.length) {
		let o = r + i * (a.samplesPerFrame * 9e4 / a.sampleRate), s = {
			unit: t.subarray(n, n + a.frameLength),
			pts: o,
			dts: o
		};
		return e.config = [], e.channelCount = a.channelCount, e.samplerate = a.sampleRate, e.samples.push(s), {
			sample: s,
			length: a.frameLength,
			missing: 0
		};
	}
}
function yc(e, t) {
	let n = e[t + 1] >> 3 & 3, r = e[t + 1] >> 1 & 3, i = e[t + 2] >> 4 & 15, a = e[t + 2] >> 2 & 3;
	if (n !== 1 && i !== 0 && i !== 15 && a !== 3) {
		let o = e[t + 2] >> 1 & 1, s = e[t + 3] >> 6, c = mc[(n === 3 ? 3 - r : r === 3 ? 3 : 4) * 14 + i - 1] * 1e3, l = hc[(n === 3 ? 0 : n === 2 ? 1 : 2) * 3 + a], u = s === 3 ? 1 : 2, d = gc[n][r], f = _c[r], p = d * 8 * f, m = Math.floor(d * c / l + o) * f;
		if (pc === null) {
			let e = (navigator.userAgent || "").match(/Chrome\/(\d+)/i);
			pc = e ? parseInt(e[1]) : 0;
		}
		return pc && pc <= 87 && r === 2 && c >= 224e3 && s === 0 && (e[t + 3] = e[t + 3] | 128), {
			sampleRate: l,
			channelCount: u,
			frameLength: m,
			samplesPerFrame: p
		};
	}
}
function bc(e, t) {
	return e[t] === 255 && (e[t + 1] & 224) == 224 && !!(e[t + 1] & 6);
}
function xc(e, t) {
	return t + 1 < e.length && bc(e, t);
}
function Sc(e, t) {
	return bc(e, t) && 4 <= e.length - t;
}
function Cc(e, t) {
	if (t + 1 < e.length && bc(e, t)) {
		let n = yc(e, t), r = 4;
		n != null && n.frameLength && (r = n.frameLength);
		let i = t + r;
		return i === e.length || xc(e, i);
	}
	return !1;
}
var wc = class extends dc {
	constructor(e, t) {
		super(), this.observer = void 0, this.config = void 0, this.observer = e, this.config = t;
	}
	resetInitSegment(e, t, n, r) {
		super.resetInitSegment(e, t, n, r), this._audioTrack = {
			container: "audio/adts",
			type: "audio",
			id: 2,
			pid: -1,
			sequenceNumber: 0,
			segmentCodec: "aac",
			samples: [],
			manifestCodec: t,
			duration: r,
			inputTimeScale: 9e4,
			dropped: 0
		};
	}
	static probe(e, t) {
		if (!e) return !1;
		let n = Ms(e, 0)?.length || 0;
		if (Cc(e, n)) return !1;
		for (let r = e.length; n < r; n++) if (Bs(e, n)) return t.log("ADTS sync word found !"), !0;
		return !1;
	}
	canParse(e, t) {
		return zs(e, t);
	}
	appendFrame(e, t, n) {
		Vs(e, this.observer, t, n, e.manifestCodec);
		let r = Ws(e, t, n, this.basePTS, this.frameIndex);
		if (r && r.missing === 0) return r;
	}
}, Tc = (e, t) => {
	let n = 0, r = 5;
	t += r;
	let i = /* @__PURE__ */ new Uint32Array(1), a = /* @__PURE__ */ new Uint32Array(1), o = /* @__PURE__ */ new Uint8Array(1);
	for (; r > 0;) {
		o[0] = e[t];
		let s = Math.min(r, 8), c = 8 - s;
		a[0] = 4278190080 >>> 24 + c << c, i[0] = (o[0] & a[0]) >> c, n = n ? n << s | i[0] : i[0], t += 1, r -= s;
	}
	return n;
}, Ec = class extends dc {
	constructor(e) {
		super(), this.observer = void 0, this.observer = e;
	}
	resetInitSegment(e, t, n, r) {
		super.resetInitSegment(e, t, n, r), this._audioTrack = {
			container: "audio/ac-3",
			type: "audio",
			id: 2,
			pid: -1,
			sequenceNumber: 0,
			segmentCodec: "ac3",
			samples: [],
			manifestCodec: t,
			duration: r,
			inputTimeScale: 9e4,
			dropped: 0
		};
	}
	canParse(e, t) {
		return t + 64 < e.length;
	}
	appendFrame(e, t, n) {
		let r = Dc(e, t, n, this.basePTS, this.frameIndex);
		if (r !== -1) return {
			sample: e.samples[e.samples.length - 1],
			length: r,
			missing: 0
		};
	}
	static probe(e) {
		if (!e) return !1;
		let t = Ms(e, 0);
		if (!t) return !1;
		let n = t.length;
		return e[n] === 11 && e[n + 1] === 119 && cc(t) !== void 0 && Tc(e, n) < 16;
	}
};
function Dc(e, t, n, r, i) {
	if (n + 8 > t.length || t[n] !== 11 || t[n + 1] !== 119) return -1;
	let a = t[n + 4] >> 6;
	if (a >= 3) return -1;
	let o = [
		48e3,
		44100,
		32e3
	][a], s = t[n + 4] & 63, c = [
		64,
		69,
		96,
		64,
		70,
		96,
		80,
		87,
		120,
		80,
		88,
		120,
		96,
		104,
		144,
		96,
		105,
		144,
		112,
		121,
		168,
		112,
		122,
		168,
		128,
		139,
		192,
		128,
		140,
		192,
		160,
		174,
		240,
		160,
		175,
		240,
		192,
		208,
		288,
		192,
		209,
		288,
		224,
		243,
		336,
		224,
		244,
		336,
		256,
		278,
		384,
		256,
		279,
		384,
		320,
		348,
		480,
		320,
		349,
		480,
		384,
		417,
		576,
		384,
		418,
		576,
		448,
		487,
		672,
		448,
		488,
		672,
		512,
		557,
		768,
		512,
		558,
		768,
		640,
		696,
		960,
		640,
		697,
		960,
		768,
		835,
		1152,
		768,
		836,
		1152,
		896,
		975,
		1344,
		896,
		976,
		1344,
		1024,
		1114,
		1536,
		1024,
		1115,
		1536,
		1152,
		1253,
		1728,
		1152,
		1254,
		1728,
		1280,
		1393,
		1920,
		1280,
		1394,
		1920
	][s * 3 + a] * 2;
	if (n + c > t.length) return -1;
	let l = t[n + 6] >> 5, u = 0;
	l === 2 ? u += 2 : (l & 1 && l !== 1 && (u += 2), l & 4 && (u += 2));
	let d = (t[n + 6] << 8 | t[n + 7]) >> 12 - u & 1, f = [
		2,
		1,
		2,
		3,
		3,
		4,
		4,
		5
	][l] + d, p = t[n + 5] >> 3, m = t[n + 5] & 7, h = new Uint8Array([
		a << 6 | p << 1 | m >> 2,
		(m & 3) << 6 | l << 3 | d << 2 | s >> 4,
		s << 4 & 224
	]), g = r + i * (1536 / o * 9e4), _ = t.subarray(n, n + c);
	return e.config = h, e.channelCount = f, e.samplerate = o, e.samples.push({
		unit: _,
		pts: g
	}), c;
}
var Oc = class extends dc {
	resetInitSegment(e, t, n, r) {
		super.resetInitSegment(e, t, n, r), this._audioTrack = {
			container: "audio/mpeg",
			type: "audio",
			id: 2,
			pid: -1,
			sequenceNumber: 0,
			segmentCodec: "mp3",
			samples: [],
			manifestCodec: t,
			duration: r,
			inputTimeScale: 9e4,
			dropped: 0
		};
	}
	static probe(e) {
		if (!e) return !1;
		let t = Ms(e, 0), n = t?.length || 0;
		if (t && e[n] === 11 && e[n + 1] === 119 && cc(t) !== void 0 && Tc(e, n) <= 16) return !1;
		for (let t = e.length; n < t; n++) if (Cc(e, n)) return Jn.log("MPEG Audio sync word found !"), !0;
		return !1;
	}
	canParse(e, t) {
		return Sc(e, t);
	}
	appendFrame(e, t, n) {
		if (this.basePTS !== null) return vc(e, t, n, this.basePTS, this.frameIndex);
	}
}, kc = /\/emsg[-/]ID3/i, Ac = class {
	constructor(e, t) {
		this.remainderData = null, this.timeOffset = 0, this.config = void 0, this.videoTrack = void 0, this.audioTrack = void 0, this.id3Track = void 0, this.txtTrack = void 0, this.config = t;
	}
	resetTimeStamp() {}
	resetInitSegment(e, t, n, r) {
		let i = this.videoTrack = uc("video", 1), a = this.audioTrack = uc("audio", 1), o = this.txtTrack = uc("text", 1);
		if (this.id3Track = uc("id3", 1), this.timeOffset = 0, !(e != null && e.byteLength)) return;
		let s = Cr(e);
		if (s.video) {
			let { id: e, timescale: t, codec: n, supplemental: r } = s.video;
			i.id = e, i.timescale = o.timescale = t, i.codec = n, i.supplemental = r;
		}
		if (s.audio) {
			let { id: e, timescale: t, codec: n } = s.audio;
			a.id = e, a.timescale = t, a.codec = n;
		}
		o.id = gr.text, i.sampleDuration = 0, i.duration = a.duration = r;
	}
	resetContiguity() {
		this.remainderData = null;
	}
	static probe(e) {
		return xr(e);
	}
	demux(e, t) {
		this.timeOffset = t;
		let n = e, r = this.videoTrack, i = this.txtTrack;
		if (this.config.progressive) {
			this.remainderData && (n = Ir(this.remainderData, e));
			let t = Fr(n);
			this.remainderData = t.remainder, r.samples = t.valid || /* @__PURE__ */ new Uint8Array();
		} else r.samples = n;
		let a = this.extractID3Track(r, t);
		return i.samples = Lr(t, r), {
			videoTrack: r,
			audioTrack: this.audioTrack,
			id3Track: a,
			textTrack: this.txtTrack
		};
	}
	flush() {
		let e = this.timeOffset, t = this.videoTrack, n = this.txtTrack;
		t.samples = this.remainderData || /* @__PURE__ */ new Uint8Array(), this.remainderData = null;
		let r = this.extractID3Track(t, this.timeOffset);
		return n.samples = Lr(e, t), {
			videoTrack: t,
			audioTrack: uc(),
			id3Track: r,
			textTrack: uc()
		};
	}
	extractID3Track(e, t) {
		let n = this.id3Track;
		if (e.samples.length) {
			let r = Z(e.samples, ["emsg"]);
			r && r.forEach((e) => {
				let r = Hr(e);
				if (kc.test(r.schemeIdUri)) {
					let e = jc(r, t), i = r.eventDuration === 4294967295 ? Infinity : r.eventDuration / r.timeScale;
					i <= .001 && (i = Infinity);
					let a = r.payload;
					n.samples.push({
						data: a,
						len: a.byteLength,
						dts: e,
						pts: e,
						type: lc.emsg,
						duration: i
					});
				} else if (this.config.enableEmsgKLVMetadata && r.schemeIdUri.startsWith("urn:misb:KLV:bin:1910.1")) {
					let e = jc(r, t);
					n.samples.push({
						data: r.payload,
						len: r.payload.byteLength,
						dts: e,
						pts: e,
						type: lc.misbklv,
						duration: Infinity
					});
				}
			});
		}
		return n;
	}
	demuxSampleAes(e, t, n) {
		return Promise.reject(/* @__PURE__ */ Error("The MP4 demuxer does not support SAMPLE-AES decryption"));
	}
	destroy() {
		this.config = null, this.remainderData = null, this.videoTrack = this.audioTrack = this.id3Track = this.txtTrack = void 0;
	}
};
function jc(e, t) {
	return W(e.presentationTime) ? e.presentationTime / e.timeScale : t + e.presentationTimeDelta / e.timeScale;
}
var Mc = class {
	constructor(e, t, n) {
		this.keyData = void 0, this.decrypter = void 0, this.keyData = n, this.decrypter = new Oa(t, { removePKCS7Padding: !1 });
	}
	decryptBuffer(e) {
		return this.decrypter.decrypt(e, this.keyData.key.buffer, this.keyData.iv.buffer, xa.cbc);
	}
	decryptAacSample(e, t, n) {
		let r = e[t].unit;
		if (r.length <= 16) return;
		let i = r.subarray(16, r.length - r.length % 16), a = i.buffer.slice(i.byteOffset, i.byteOffset + i.length);
		this.decryptBuffer(a).then((i) => {
			let a = new Uint8Array(i);
			r.set(a, 16), this.decrypter.isSync() || this.decryptAacSamples(e, t + 1, n);
		}).catch(n);
	}
	decryptAacSamples(e, t, n) {
		for (;; t++) {
			if (t >= e.length) {
				n();
				return;
			}
			if (!(e[t].unit.length < 32) && (this.decryptAacSample(e, t, n), !this.decrypter.isSync())) return;
		}
	}
	getAvcEncryptedData(e) {
		let t = Math.floor((e.length - 48) / 160) * 16 + 16, n = new Int8Array(t), r = 0;
		for (let t = 32; t < e.length - 16; t += 160, r += 16) n.set(e.subarray(t, t + 16), r);
		return n;
	}
	getAvcDecryptedUnit(e, t) {
		let n = new Uint8Array(t), r = 0;
		for (let t = 32; t < e.length - 16; t += 160, r += 16) e.set(n.subarray(r, r + 16), t);
		return e;
	}
	decryptAvcSample(e, t, n, r, i) {
		let a = Vr(i.data), o = this.getAvcEncryptedData(a);
		this.decryptBuffer(o.buffer).then((o) => {
			i.data = this.getAvcDecryptedUnit(a, o), this.decrypter.isSync() || this.decryptAvcSamples(e, t, n + 1, r);
		}).catch(r);
	}
	decryptAvcSamples(e, t, n, r) {
		if (e instanceof Uint8Array) throw Error("Cannot decrypt samples of type Uint8Array");
		for (;; t++, n = 0) {
			if (t >= e.length) {
				r();
				return;
			}
			let i = e[t].units;
			for (; !(n >= i.length); n++) {
				let a = i[n];
				if (!(a.data.length <= 48 || a.type !== 1 && a.type !== 5) && (this.decryptAvcSample(e, t, n, r, a), !this.decrypter.isSync())) return;
			}
		}
	}
}, Nc = class {
	constructor() {
		this.VideoSample = null;
	}
	createVideoSample(e, t, n) {
		return {
			key: e,
			frame: !1,
			pts: t,
			dts: n,
			units: [],
			length: 0
		};
	}
	getLastNalUnit(e) {
		var t;
		let n = this.VideoSample, r;
		if (n && n.units.length !== 0 || (n = e[e.length - 1]), (t = n) != null && t.units) {
			let e = n.units;
			r = e[e.length - 1];
		}
		return r;
	}
	pushAccessUnit(e, t) {
		if (e.units.length && e.frame) {
			if (e.pts === void 0) {
				let n = t.samples, r = n.length;
				if (r) {
					let t = n[r - 1];
					e.pts = t.pts, e.dts = t.dts;
				} else {
					t.dropped++;
					return;
				}
			}
			t.samples.push(e);
		}
	}
	parseNALu(e, t, n) {
		let r = t.byteLength, i = e.naluState || 0, a = i, o = [], s = 0, c, l, u, d = -1, f = 0;
		for (i === -1 && (d = 0, f = this.getNALuType(t, 0), i = 0, s = 1); s < r;) if (c = t[s++], !i) i = +!c;
		else if (i === 1) i = c ? 0 : 2;
		else if (!c) i = 3;
		else if (c === 1) {
			if (l = s - i - 1, d >= 0) {
				let e = {
					data: t.subarray(d, l),
					type: f
				};
				o.push(e);
			} else {
				let n = this.getLastNalUnit(e.samples);
				n && (a && s <= 4 - a && n.state && (n.data = n.data.subarray(0, n.data.byteLength - a)), l > 0 && (n.data = Ir(n.data, t.subarray(0, l)), n.state = 0));
			}
			s < r ? (u = this.getNALuType(t, s), d = s, f = u, i = 0) : i = -1;
		} else i = 0;
		if (d >= 0 && i >= 0) {
			let e = {
				data: t.subarray(d, r),
				type: f,
				state: i
			};
			o.push(e);
		}
		if (o.length === 0) {
			let n = this.getLastNalUnit(e.samples);
			n && (n.data = Ir(n.data, t));
		}
		return e.naluState = i, o;
	}
}, Pc = class {
	constructor(e) {
		this.data = void 0, this.bytesAvailable = void 0, this.word = void 0, this.bitsAvailable = void 0, this.data = e, this.bytesAvailable = e.byteLength, this.word = 0, this.bitsAvailable = 0;
	}
	loadWord() {
		let e = this.data, t = this.bytesAvailable, n = e.byteLength - t, r = /* @__PURE__ */ new Uint8Array(4), i = Math.min(4, t);
		if (i === 0) throw Error("no bytes available");
		r.set(e.subarray(n, n + i)), this.word = new DataView(r.buffer).getUint32(0), this.bitsAvailable = i * 8, this.bytesAvailable -= i;
	}
	skipBits(e) {
		let t;
		e = Math.min(e, this.bytesAvailable * 8 + this.bitsAvailable), this.bitsAvailable > e ? (this.word <<= e, this.bitsAvailable -= e) : (e -= this.bitsAvailable, t = e >> 3, e -= t << 3, this.bytesAvailable -= t, this.loadWord(), this.word <<= e, this.bitsAvailable -= e);
	}
	readBits(e) {
		let t = Math.min(this.bitsAvailable, e), n = this.word >>> 32 - t;
		if (e > 32 && Jn.error("Cannot read more than 32 bits at a time"), this.bitsAvailable -= t, this.bitsAvailable > 0) this.word <<= t;
		else if (this.bytesAvailable > 0) this.loadWord();
		else throw Error("no bits available");
		return t = e - t, t > 0 && this.bitsAvailable ? n << t | this.readBits(t) : n;
	}
	skipLZ() {
		let e = 0;
		for (; e < this.bitsAvailable; ++e) if (this.word & 2147483648 >>> e) return this.word <<= e, this.bitsAvailable -= e, e;
		return this.loadWord(), e + this.skipLZ();
	}
	skipUEG() {
		this.skipBits(1 + this.skipLZ());
	}
	skipEG() {
		this.skipBits(1 + this.skipLZ());
	}
	readUEG() {
		let e = this.skipLZ();
		return this.readBits(e + 1) - 1;
	}
	readEG() {
		let e = this.readUEG();
		return 1 & e ? 1 + e >>> 1 : -1 * (e >>> 1);
	}
	readBoolean() {
		return this.readBits(1) === 1;
	}
	readUByte() {
		return this.readBits(8);
	}
	readUShort() {
		return this.readBits(16);
	}
	readUInt() {
		return this.readBits(32);
	}
}, Fc = class extends Nc {
	parsePES(e, t, n, r) {
		let i = this.parseNALu(e, n.data, r), a = this.VideoSample, o, s = !1;
		n.data = null, a && i.length && !e.audFound && (this.pushAccessUnit(a, e), a = this.VideoSample = this.createVideoSample(!1, n.pts, n.dts)), i.forEach((r) => {
			var i, c;
			switch (r.type) {
				case 1: {
					let t = !1;
					o = !0;
					let i = r.data;
					if (s && i.length > 4) {
						let e = this.readSliceType(i);
						(e === 2 || e === 4 || e === 7 || e === 9) && (t = !0);
					}
					if (t) {
						var l;
						(l = a) != null && l.frame && !a.key && (this.pushAccessUnit(a, e), a = this.VideoSample = null);
					}
					a ||= this.VideoSample = this.createVideoSample(!0, n.pts, n.dts), a.frame = !0, a.key = t;
					break;
				}
				case 5:
					o = !0, (i = a) != null && i.frame && !a.key && (this.pushAccessUnit(a, e), a = this.VideoSample = null), a ||= this.VideoSample = this.createVideoSample(!0, n.pts, n.dts), a.key = !0, a.frame = !0;
					break;
				case 6:
					o = !0, Br(r.data, 1, n.pts, t.samples);
					break;
				case 7: {
					o = !0, s = !0;
					let t = r.data, n = this.readSPS(t);
					if (!e.sps || e.width !== n.width || e.height !== n.height || e.pixelRatio?.[0] !== n.pixelRatio[0] || e.pixelRatio?.[1] !== n.pixelRatio[1]) {
						e.width = n.width, e.height = n.height, e.pixelRatio = n.pixelRatio, e.sps = [t];
						let r = t.subarray(1, 4), i = "avc1.";
						for (let e = 0; e < 3; e++) {
							let t = r[e].toString(16);
							t.length < 2 && (t = "0" + t), i += t;
						}
						e.codec = i;
					}
					break;
				}
				case 8:
					o = !0, e.pps = [r.data];
					break;
				case 9:
					o = !0, e.audFound = !0, (c = a) != null && c.frame && (this.pushAccessUnit(a, e), a = null), a ||= this.VideoSample = this.createVideoSample(!1, n.pts, n.dts);
					break;
				case 12:
					o = !0;
					break;
				default: o = !1;
			}
			a && o && a.units.push(r);
		}), r && a && (this.pushAccessUnit(a, e), this.VideoSample = null);
	}
	getNALuType(e, t) {
		return e[t] & 31;
	}
	readSliceType(e) {
		let t = new Pc(e);
		return t.readUByte(), t.readUEG(), t.readUEG();
	}
	skipScalingList(e, t) {
		let n = 8, r = 8, i;
		for (let a = 0; a < e; a++) r !== 0 && (i = t.readEG(), r = (n + i + 256) % 256), n = r === 0 ? n : r;
	}
	readSPS(e) {
		let t = new Pc(e), n = 0, r = 0, i = 0, a = 0, o, s, c, l = t.readUByte.bind(t), u = t.readBits.bind(t), d = t.readUEG.bind(t), f = t.readBoolean.bind(t), p = t.skipBits.bind(t), m = t.skipEG.bind(t), h = t.skipUEG.bind(t), g = this.skipScalingList.bind(this);
		l();
		let _ = l();
		if (u(5), p(3), l(), h(), _ === 100 || _ === 110 || _ === 122 || _ === 244 || _ === 44 || _ === 83 || _ === 86 || _ === 118 || _ === 128) {
			let e = d();
			if (e === 3 && p(1), h(), h(), p(1), f()) for (s = e === 3 ? 12 : 8, c = 0; c < s; c++) f() && g(c < 6 ? 16 : 64, t);
		}
		h();
		let v = d();
		if (v === 0) d();
		else if (v === 1) for (p(1), m(), m(), o = d(), c = 0; c < o; c++) m();
		h(), p(1);
		let y = d(), b = d(), x = u(1);
		x === 0 && p(1), p(1), f() && (n = d(), r = d(), i = d(), a = d());
		let S = [1, 1];
		if (f() && f()) switch (l()) {
			case 1:
				S = [1, 1];
				break;
			case 2:
				S = [12, 11];
				break;
			case 3:
				S = [10, 11];
				break;
			case 4:
				S = [16, 11];
				break;
			case 5:
				S = [40, 33];
				break;
			case 6:
				S = [24, 11];
				break;
			case 7:
				S = [20, 11];
				break;
			case 8:
				S = [32, 11];
				break;
			case 9:
				S = [80, 33];
				break;
			case 10:
				S = [18, 11];
				break;
			case 11:
				S = [15, 11];
				break;
			case 12:
				S = [64, 33];
				break;
			case 13:
				S = [160, 99];
				break;
			case 14:
				S = [4, 3];
				break;
			case 15:
				S = [3, 2];
				break;
			case 16:
				S = [2, 1];
				break;
			case 255: S = [l() << 8 | l(), l() << 8 | l()];
		}
		return {
			width: Math.ceil((y + 1) * 16 - n * 2 - r * 2),
			height: (2 - x) * (b + 1) * 16 - (x ? 2 : 4) * (i + a),
			pixelRatio: S
		};
	}
}, Ic = class extends Nc {
	constructor(...e) {
		super(...e), this.initVPS = null;
	}
	parsePES(e, t, n, r) {
		let i = this.parseNALu(e, n.data, r), a = this.VideoSample, o, s = !1;
		n.data = null, a && i.length && !e.audFound && (this.pushAccessUnit(a, e), a = this.VideoSample = this.createVideoSample(!1, n.pts, n.dts)), i.forEach((r) => {
			var i, c;
			switch (r.type) {
				case 0:
				case 1:
				case 2:
				case 3:
				case 4:
				case 5:
				case 6:
				case 7:
				case 8:
				case 9:
					a ||= this.VideoSample = this.createVideoSample(!1, n.pts, n.dts), a.frame = !0, o = !0;
					break;
				case 16:
				case 17:
				case 18:
				case 21:
					if (o = !0, s) {
						var l;
						(l = a) != null && l.frame && !a.key && (this.pushAccessUnit(a, e), a = this.VideoSample = null);
					}
					a ||= this.VideoSample = this.createVideoSample(!0, n.pts, n.dts), a.key = !0, a.frame = !0;
					break;
				case 19:
				case 20:
					o = !0, (i = a) != null && i.frame && !a.key && (this.pushAccessUnit(a, e), a = this.VideoSample = null), a ||= this.VideoSample = this.createVideoSample(!0, n.pts, n.dts), a.key = !0, a.frame = !0;
					break;
				case 39:
					o = !0, Br(r.data, 2, n.pts, t.samples);
					break;
				case 32:
					o = !0, e.vps || (typeof e.params != "object" && (e.params = {}), e.params = Fn(e.params, this.readVPS(r.data)), this.initVPS = r.data), e.vps = [r.data];
					break;
				case 33:
					if (o = !0, s = !0, e.vps !== void 0 && e.vps[0] !== this.initVPS && e.sps !== void 0 && !this.matchSPS(e.sps[0], r.data) && (this.initVPS = e.vps[0], e.sps = e.pps = void 0), !e.sps) {
						let t = this.readSPS(r.data);
						e.width = t.width, e.height = t.height, e.pixelRatio = t.pixelRatio, e.codec = t.codecString, e.sps = [], typeof e.params != "object" && (e.params = {});
						for (let n in t.params) e.params[n] = t.params[n];
					}
					this.pushParameterSet(e.sps, r.data, e.vps), a ||= this.VideoSample = this.createVideoSample(!0, n.pts, n.dts), a.key = !0;
					break;
				case 34:
					if (o = !0, typeof e.params == "object") {
						if (!e.pps) {
							e.pps = [];
							let t = this.readPPS(r.data);
							for (let n in t) e.params[n] = t[n];
						}
						this.pushParameterSet(e.pps, r.data, e.vps);
					}
					break;
				case 35:
					o = !0, e.audFound = !0, (c = a) != null && c.frame && (this.pushAccessUnit(a, e), a = null), a ||= this.VideoSample = this.createVideoSample(!1, n.pts, n.dts);
					break;
				default: o = !1;
			}
			a && o && a.units.push(r);
		}), r && a && (this.pushAccessUnit(a, e), this.VideoSample = null);
	}
	pushParameterSet(e, t, n) {
		(n && n[0] === this.initVPS || !n && !e.length) && e.push(t);
	}
	getNALuType(e, t) {
		return (e[t] & 126) >>> 1;
	}
	ebsp2rbsp(e) {
		let t = new Uint8Array(e.byteLength), n = 0;
		for (let r = 0; r < e.byteLength; r++) r >= 2 && e[r] === 3 && e[r - 1] === 0 && e[r - 2] === 0 || (t[n] = e[r], n++);
		return new Uint8Array(t.buffer, 0, n);
	}
	pushAccessUnit(e, t) {
		super.pushAccessUnit(e, t), this.initVPS &&= null;
	}
	readVPS(e) {
		let t = new Pc(e);
		t.readUByte(), t.readUByte(), t.readBits(4), t.skipBits(2), t.readBits(6);
		let n = t.readBits(3), r = t.readBoolean();
		return {
			numTemporalLayers: n + 1,
			temporalIdNested: r
		};
	}
	readSPS(e) {
		let t = new Pc(this.ebsp2rbsp(e));
		t.readUByte(), t.readUByte(), t.readBits(4);
		let n = t.readBits(3);
		t.readBoolean();
		let r = t.readBits(2), i = t.readBoolean(), a = t.readBits(5), o = t.readUByte(), s = t.readUByte(), c = t.readUByte(), l = t.readUByte(), u = t.readUByte(), d = t.readUByte(), f = t.readUByte(), p = t.readUByte(), m = t.readUByte(), h = t.readUByte(), g = t.readUByte(), _ = [], v = [];
		for (let e = 0; e < n; e++) _.push(t.readBoolean()), v.push(t.readBoolean());
		if (n > 0) for (let e = n; e < 8; e++) t.readBits(2);
		for (let e = 0; e < n; e++) _[e] && (t.readUByte(), t.readUByte(), t.readUByte(), t.readUByte(), t.readUByte(), t.readUByte(), t.readUByte(), t.readUByte(), t.readUByte(), t.readUByte(), t.readUByte()), v[e] && t.readUByte();
		t.readUEG();
		let y = t.readUEG();
		y == 3 && t.skipBits(1);
		let b = t.readUEG(), x = t.readUEG(), S = t.readBoolean(), C = 0, w = 0, T = 0, E = 0;
		S && (C += t.readUEG(), w += t.readUEG(), T += t.readUEG(), E += t.readUEG());
		let D = t.readUEG(), O = t.readUEG(), k = t.readUEG(), A = t.readBoolean();
		for (let e = A ? 0 : n; e <= n; e++) t.skipUEG(), t.skipUEG(), t.skipUEG();
		if (t.skipUEG(), t.skipUEG(), t.skipUEG(), t.skipUEG(), t.skipUEG(), t.skipUEG(), t.readBoolean() && t.readBoolean()) for (let e = 0; e < 4; e++) for (let n = 0; n < (e === 3 ? 2 : 6); n++) if (!t.readBoolean()) t.readUEG();
		else {
			let n = Math.min(64, 1 << 4 + (e << 1));
			e > 1 && t.readEG();
			for (let e = 0; e < n; e++) t.readEG();
		}
		t.readBoolean(), t.readBoolean(), t.readBoolean() && (t.readUByte(), t.skipUEG(), t.skipUEG(), t.readBoolean());
		let j = t.readUEG(), M = 0;
		for (let e = 0; e < j; e++) {
			let n = !1;
			if (e !== 0 && (n = t.readBoolean()), n) {
				e === j && t.readUEG(), t.readBoolean(), t.readUEG();
				let n = 0;
				for (let e = 0; e <= M; e++) {
					let e = t.readBoolean(), r = !1;
					e || (r = t.readBoolean()), (e || r) && n++;
				}
				M = n;
			} else {
				let e = t.readUEG(), n = t.readUEG();
				M = e + n;
				for (let n = 0; n < e; n++) t.readUEG(), t.readBoolean();
				for (let e = 0; e < n; e++) t.readUEG(), t.readBoolean();
			}
		}
		if (t.readBoolean()) {
			let e = t.readUEG();
			for (let n = 0; n < e; n++) {
				for (let e = 0; e < k + 4; e++) t.readBits(1);
				t.readBits(1);
			}
		}
		let N = 0, ee = 1, P = 1, te = !0, F = 1, ne = 0;
		t.readBoolean(), t.readBoolean();
		let re = !1;
		if (t.readBoolean()) {
			if (t.readBoolean()) {
				let e = t.readUByte();
				e > 0 && e < 16 ? (ee = [
					1,
					12,
					10,
					16,
					40,
					24,
					20,
					32,
					80,
					18,
					15,
					64,
					160,
					4,
					3,
					2
				][e - 1], P = [
					1,
					11,
					11,
					11,
					33,
					11,
					11,
					11,
					33,
					11,
					11,
					33,
					99,
					3,
					2,
					1
				][e - 1]) : e === 255 && (ee = t.readBits(16), P = t.readBits(16));
			}
			if (t.readBoolean() && t.readBoolean(), t.readBoolean() && (t.readBits(3), t.readBoolean(), t.readBoolean() && (t.readUByte(), t.readUByte(), t.readUByte())), t.readBoolean() && (t.readUEG(), t.readUEG()), t.readBoolean(), t.readBoolean(), t.readBoolean(), re = t.readBoolean(), re && (t.skipUEG(), t.skipUEG(), t.skipUEG(), t.skipUEG()), t.readBoolean() && (F = t.readBits(32), ne = t.readBits(32), t.readBoolean() && t.readUEG(), t.readBoolean())) {
				let e = t.readBoolean(), r = t.readBoolean(), i = !1;
				(e || r) && (i = t.readBoolean(), i && (t.readUByte(), t.readBits(5), t.readBoolean(), t.readBits(5)), t.readBits(4), t.readBits(4), i && t.readBits(4), t.readBits(5), t.readBits(5), t.readBits(5));
				for (let a = 0; a <= n; a++) {
					te = t.readBoolean();
					let n = te || t.readBoolean(), a = !1;
					n ? t.readEG() : a = t.readBoolean();
					let o = a ? 1 : t.readUEG() + 1;
					if (e) for (let e = 0; e < o; e++) t.readUEG(), t.readUEG(), i && (t.readUEG(), t.readUEG()), t.skipBits(1);
					if (r) for (let e = 0; e < o; e++) t.readUEG(), t.readUEG(), i && (t.readUEG(), t.readUEG()), t.skipBits(1);
				}
			}
			t.readBoolean() && (t.readBoolean(), t.readBoolean(), t.readBoolean(), N = t.readUEG());
		}
		let ie = b, I = x;
		if (S) {
			let e = 1, t = 1;
			y === 1 ? e = t = 2 : y == 2 && (e = 2), ie = b - e * w - e * C, I = x - t * E - t * T;
		}
		let ae = r ? [
			"A",
			"B",
			"C"
		][r] : "", oe = o << 24 | s << 16 | c << 8 | l, se = 0;
		for (let e = 0; e < 32; e++) se = (se | (oe >> e & 1) << 31 - e) >>> 0;
		let L = se.toString(16);
		return a === 1 && L === "2" && (L = "6"), {
			codecString: `hvc1.${ae}${a}.${L}.${i ? "H" : "L"}${g}.B0`,
			params: {
				general_tier_flag: i,
				general_profile_idc: a,
				general_profile_space: r,
				general_profile_compatibility_flags: [
					o,
					s,
					c,
					l
				],
				general_constraint_indicator_flags: [
					u,
					d,
					f,
					p,
					m,
					h
				],
				general_level_idc: g,
				bit_depth: D + 8,
				bit_depth_luma_minus8: D,
				bit_depth_chroma_minus8: O,
				min_spatial_segmentation_idc: N,
				chroma_format_idc: y,
				frame_rate: {
					fixed: te,
					fps: ne / F
				}
			},
			width: ie,
			height: I,
			pixelRatio: [ee, P]
		};
	}
	readPPS(e) {
		let t = new Pc(this.ebsp2rbsp(e));
		t.readUByte(), t.readUByte(), t.skipUEG(), t.skipUEG(), t.skipBits(2), t.skipBits(3), t.skipBits(2), t.skipUEG(), t.skipUEG(), t.skipEG(), t.skipBits(2), t.readBoolean() && t.skipUEG(), t.skipEG(), t.skipEG(), t.skipBits(4);
		let n = t.readBoolean(), r = t.readBoolean(), i = 1;
		return r && n ? i = 0 : r ? i = 3 : n && (i = 2), { parallelismType: i };
	}
	matchSPS(e, t) {
		return String.fromCharCode.apply(null, e).substr(3) === String.fromCharCode.apply(null, t).substr(3);
	}
}, Lc = 188, Rc = class e {
	constructor(e, t, n, r) {
		this.logger = void 0, this.observer = void 0, this.config = void 0, this.typeSupported = void 0, this.sampleAes = null, this.pmtParsed = !1, this.audioCodec = void 0, this.videoCodec = void 0, this._pmtId = -1, this._videoTrack = void 0, this._audioTrack = void 0, this._id3Track = void 0, this._txtTrack = void 0, this.aacOverFlow = null, this.remainderData = null, this.videoParser = void 0, this.observer = e, this.config = t, this.typeSupported = n, this.logger = r, this.videoParser = null;
	}
	static probe(t, n) {
		let r = e.syncOffset(t);
		return r > 0 && n.warn(`MPEG2-TS detected but first sync word found @ offset ${r}`), r !== -1;
	}
	static syncOffset(e) {
		let t = e.length, n = Math.min(940, t - Lc) + 1, r = 0;
		for (; r < n;) {
			let i = !1, a = -1, o = 0;
			for (let s = r; s < t; s += Lc) if (e[s] === 71 && (t - s === Lc || e[s + Lc] === 71)) {
				if (o++, a === -1 && (a = s, a !== 0 && (n = Math.min(a + 18612, e.length - Lc) + 1)), i ||= zc(e, s) === 0, i && o > 1 && (a === 0 && o > 2 || s + Lc > n)) return a;
			} else if (o) return -1;
			else break;
			r++;
		}
		return -1;
	}
	static createTrack(e, t) {
		return {
			container: e === "video" || e === "audio" ? "video/mp2t" : void 0,
			type: e,
			id: gr[e],
			pid: -1,
			inputTimeScale: 9e4,
			sequenceNumber: 0,
			samples: [],
			dropped: 0,
			duration: e === "audio" ? t : void 0
		};
	}
	resetInitSegment(t, n, r, i) {
		this.pmtParsed = !1, this._pmtId = -1, this._videoTrack = e.createTrack("video"), this._videoTrack.duration = i, this._audioTrack = e.createTrack("audio", i), this._id3Track = e.createTrack("id3"), this._txtTrack = e.createTrack("text"), this._audioTrack.segmentCodec = "aac", this.videoParser = null, this.aacOverFlow = null, this.remainderData = null, this.audioCodec = n, this.videoCodec = r;
	}
	resetTimeStamp() {}
	resetContiguity() {
		let { _audioTrack: e, _videoTrack: t, _id3Track: n } = this;
		e && (e.pesData = null), t && (t.pesData = null), n && (n.pesData = null), this.aacOverFlow = null, this.remainderData = null;
	}
	demux(t, n, r = !1, i = !1) {
		r || (this.sampleAes = null);
		let a, o = this._videoTrack, s = this._audioTrack, c = this._id3Track, l = this._txtTrack, u = o.pid, d = o.pesData, f = s.pid, p = c.pid, m = s.pesData, h = c.pesData, g = null, _ = this.pmtParsed, v = this._pmtId, y = t.length;
		if (this.remainderData &&= (t = Ir(this.remainderData, t), y = t.length, null), y < Lc && !i) return this.remainderData = t, {
			audioTrack: s,
			videoTrack: o,
			id3Track: c,
			textTrack: l
		};
		let b = Math.max(0, e.syncOffset(t));
		y -= (y - b) % Lc, y < t.byteLength && !i && (this.remainderData = new Uint8Array(t.buffer, y, t.buffer.byteLength - y));
		let x = 0;
		for (let e = b; e < y; e += Lc) if (t[e] === 71) {
			let n = !!(t[e + 1] & 64), i = zc(t, e), y = (t[e + 3] & 48) >> 4, x;
			if (y > 1) {
				if (x = e + 5 + t[e + 4], x === e + Lc) continue;
			} else x = e + 4;
			switch (i) {
				case u:
					n && (d && (a = Wc(d, this.logger)) && (this.readyVideoParser(o.segmentCodec), this.videoParser !== null && this.videoParser.parsePES(o, l, a, !1)), d = {
						data: [],
						size: 0
					}), d && (d.data.push(t.subarray(x, e + Lc)), d.size += e + Lc - x);
					break;
				case f:
					if (n) {
						if (m && (a = Wc(m, this.logger))) switch (s.segmentCodec) {
							case "aac":
								this.parseAACPES(s, a);
								break;
							case "mp3":
								this.parseMPEGPES(s, a);
								break;
							case "ac3": this.parseAC3PES(s, a);
						}
						m = {
							data: [],
							size: 0
						};
					}
					m && (m.data.push(t.subarray(x, e + Lc)), m.size += e + Lc - x);
					break;
				case p:
					n && (h && (a = Wc(h, this.logger)) && this.parseID3PES(c, a), h = {
						data: [],
						size: 0
					}), h && (h.data.push(t.subarray(x, e + Lc)), h.size += e + Lc - x);
					break;
				case 0:
					n && (x += t[x] + 1), v = this._pmtId = Bc(t, x);
					break;
				case v: {
					n && (x += t[x] + 1);
					let i = Vc(t, x, this.typeSupported, r, this.observer, this.logger);
					u = i.videoPid, u > 0 && (o.pid = u, o.segmentCodec = i.segmentVideoCodec), f = i.audioPid, f > 0 && (s.pid = f, s.segmentCodec = i.segmentAudioCodec), p = i.id3Pid, p > 0 && (c.pid = p), g !== null && !_ && (this.logger.warn(`MPEG-TS PMT found at ${e} after unknown PID '${g}'. Backtracking to sync byte @${b} to parse all TS packets.`), g = null, e = b - 188), _ = this.pmtParsed = !0;
					break;
				}
				case 17:
				case 8191: break;
				default: g = i;
			}
		} else x++;
		x > 0 && Hc(this.observer, /* @__PURE__ */ Error(`Found ${x} TS packet/s that do not start with 0x47`), void 0, this.logger), o.pesData = d, s.pesData = m, c.pesData = h;
		let S = {
			audioTrack: s,
			videoTrack: o,
			id3Track: c,
			textTrack: l
		};
		return i && this.extractRemainingSamples(S), S;
	}
	flush() {
		let { remainderData: e } = this;
		this.remainderData = null;
		let t;
		return t = e ? this.demux(e, -1, !1, !0) : {
			videoTrack: this._videoTrack,
			audioTrack: this._audioTrack,
			id3Track: this._id3Track,
			textTrack: this._txtTrack
		}, this.extractRemainingSamples(t), this.sampleAes ? this.decrypt(t, this.sampleAes) : t;
	}
	extractRemainingSamples(e) {
		let { audioTrack: t, videoTrack: n, id3Track: r, textTrack: i } = e, a = n.pesData, o = t.pesData, s = r.pesData, c;
		if (a && (c = Wc(a, this.logger)) ? (this.readyVideoParser(n.segmentCodec), this.videoParser !== null && (this.videoParser.parsePES(n, i, c, !0), n.pesData = null)) : n.pesData = a, o && (c = Wc(o, this.logger))) {
			switch (t.segmentCodec) {
				case "aac":
					this.parseAACPES(t, c);
					break;
				case "mp3":
					this.parseMPEGPES(t, c);
					break;
				case "ac3": this.parseAC3PES(t, c);
			}
			t.pesData = null;
		} else o != null && o.size && this.logger.log("last AAC PES packet truncated,might overlap between fragments"), t.pesData = o;
		s && (c = Wc(s, this.logger)) ? (this.parseID3PES(r, c), r.pesData = null) : r.pesData = s;
	}
	demuxSampleAes(e, t, n) {
		let r = this.demux(e, n, !0, !this.config.progressive), i = this.sampleAes = new Mc(this.observer, this.config, t);
		return this.decrypt(r, i);
	}
	readyVideoParser(e) {
		this.videoParser === null && (e === "avc" ? this.videoParser = new Fc() : e === "hevc" && (this.videoParser = new Ic()));
	}
	decrypt(e, t) {
		return new Promise((n) => {
			let { audioTrack: r, videoTrack: i } = e;
			r.samples && r.segmentCodec === "aac" ? t.decryptAacSamples(r.samples, 0, () => {
				i.samples ? t.decryptAvcSamples(i.samples, 0, 0, () => {
					n(e);
				}) : n(e);
			}) : i.samples && t.decryptAvcSamples(i.samples, 0, 0, () => {
				n(e);
			});
		});
	}
	destroy() {
		this.observer && this.observer.removeAllListeners(), this.config = this.logger = this.observer = null, this.aacOverFlow = this.videoParser = this.remainderData = this.sampleAes = null, this._videoTrack = this._audioTrack = this._id3Track = this._txtTrack = void 0;
	}
	parseAACPES(e, t) {
		let n = 0, r = this.aacOverFlow, i = t.data;
		if (r) {
			this.aacOverFlow = null;
			let t = r.missing, a = r.sample.unit.byteLength;
			if (t === -1) i = Ir(r.sample.unit, i);
			else {
				let o = a - t;
				r.sample.unit.set(i.subarray(0, t), o), e.samples.push(r.sample), n = r.missing;
			}
		}
		let a, o;
		for (a = n, o = i.length; a < o - 1 && !Rs(i, a); a++);
		if (a !== n) {
			let e, t = a < o - 1;
			if (e = t ? `AAC PES did not start with ADTS header,offset:${a}` : "No ADTS header found in AAC PES", Hc(this.observer, Error(e), t, this.logger), !t) return;
		}
		Vs(e, this.observer, i, a, this.audioCodec);
		let s;
		if (t.pts !== void 0) s = t.pts;
		else if (r) {
			let t = Hs(e.samplerate);
			s = r.sample.pts + t;
		} else {
			this.logger.warn("[tsdemuxer]: AAC PES unknown PTS");
			return;
		}
		let c = 0, l;
		for (; a < o;) {
			if (l = Ws(e, i, a, s, c), a += l.length, l.missing) {
				this.aacOverFlow = l;
				break;
			}
			for (c++; a < o - 1 && !Rs(i, a); a++);
		}
	}
	parseMPEGPES(e, t) {
		let n = t.data, r = n.length, i = 0, a = 0, o = t.pts;
		if (o === void 0) this.logger.warn("[tsdemuxer]: MPEG PES unknown PTS");
		else for (; a < r;) if (xc(n, a)) {
			let t = vc(e, n, a, o, i);
			if (t) a += t.length, i++;
			else break;
		} else a++;
	}
	parseAC3PES(e, t) {
		{
			let n = t.data, r = t.pts;
			if (r === void 0) {
				this.logger.warn("[tsdemuxer]: AC3 PES unknown PTS");
				return;
			}
			let i = n.length, a = 0, o = 0, s;
			for (; o < i && (s = Dc(e, n, o, r, a++)) > 0;) o += s;
		}
	}
	parseID3PES(e, t) {
		if (t.pts === void 0) {
			this.logger.warn("[tsdemuxer]: ID3 PES unknown PTS");
			return;
		}
		let n = Fn({}, t, {
			type: this._videoTrack ? lc.emsg : lc.audioId3,
			duration: Infinity
		});
		e.samples.push(n);
	}
};
function zc(e, t) {
	return ((e[t + 1] & 31) << 8) + e[t + 2];
}
function Bc(e, t) {
	return (e[t + 10] & 31) << 8 | e[t + 11];
}
function Vc(e, t, n, r, i, a) {
	let o = {
		audioPid: -1,
		videoPid: -1,
		id3Pid: -1,
		segmentVideoCodec: "avc",
		segmentAudioCodec: "aac"
	}, s = (e[t + 1] & 15) << 8 | e[t + 2], c = t + 3 + s - 4, l = (e[t + 10] & 15) << 8 | e[t + 11];
	for (t += 12 + l; t < c;) {
		let s = zc(e, t), c = (e[t + 3] & 15) << 8 | e[t + 4];
		switch (e[t]) {
			case 207: if (!r) {
				Uc("ADTS AAC", a);
				break;
			}
			case 15:
				o.audioPid === -1 && (o.audioPid = s);
				break;
			case 21:
				o.id3Pid === -1 && (o.id3Pid = s);
				break;
			case 219: if (!r) {
				Uc("H.264", a);
				break;
			}
			case 27:
				o.videoPid === -1 && (o.videoPid = s);
				break;
			case 3:
			case 4:
				!n.mpeg && !n.mp3 ? a.log("MPEG audio found, not supported in this browser") : o.audioPid === -1 && (o.audioPid = s, o.segmentAudioCodec = "mp3");
				break;
			case 193: if (!r) {
				Uc("AC-3", a);
				break;
			}
			case 129:
				n.ac3 ? o.audioPid === -1 && (o.audioPid = s, o.segmentAudioCodec = "ac3") : a.log("AC-3 audio found, not supported in this browser");
				break;
			case 6:
				if (o.audioPid === -1 && c > 0) {
					let r = t + 5, i = c;
					for (; i > 2;) {
						e[r] === 106 && (n.ac3 === !0 ? (o.audioPid = s, o.segmentAudioCodec = "ac3") : a.log("AC-3 audio found, not supported in this browser for now"));
						let t = e[r + 1] + 2;
						r += t, i -= t;
					}
				}
				break;
			case 194:
			case 135: return Hc(i, /* @__PURE__ */ Error("Unsupported EC-3 in M2TS found"), void 0, a), o;
			case 36: o.videoPid === -1 && (o.videoPid = s, o.segmentVideoCodec = "hevc", a.log("HEVC in M2TS found"));
		}
		t += c + 5;
	}
	return o;
}
function Hc(e, t, n, r) {
	r.warn(`parsing error: ${t.message}`), e.emit(q.ERROR, q.ERROR, {
		type: G.MEDIA_ERROR,
		details: K.FRAG_PARSING_ERROR,
		fatal: !1,
		levelRetry: n,
		error: t,
		reason: t.message
	});
}
function Uc(e, t) {
	t.log(`${e} with AES-128-CBC encryption found in unencrypted stream`);
}
function Wc(e, t) {
	let n = 0, r, i, a, o, s, c = e.data;
	if (!e || e.size === 0) return null;
	for (; c[0].length < 19 && c.length > 1;) c[0] = Ir(c[0], c[1]), c.splice(1, 1);
	if (r = c[0], (r[0] << 16) + (r[1] << 8) + r[2] === 1) {
		if (i = (r[4] << 8) + r[5], i && i > e.size - 6) return null;
		let l = r[7];
		l & 192 && (o = (r[9] & 14) * 536870912 + (r[10] & 255) * 4194304 + (r[11] & 254) * 16384 + (r[12] & 255) * 128 + (r[13] & 254) / 2, l & 64 ? (s = (r[14] & 14) * 536870912 + (r[15] & 255) * 4194304 + (r[16] & 254) * 16384 + (r[17] & 255) * 128 + (r[18] & 254) / 2, o - s > 54e5 && (t.warn(`${Math.round((o - s) / 9e4)}s delta between PTS and DTS, align them`), o = s)) : s = o), a = r[8];
		let u = a + 9;
		if (e.size <= u) return null;
		e.size -= u;
		let d = new Uint8Array(e.size);
		for (let e = 0, t = c.length; e < t; e++) {
			r = c[e];
			let t = r.byteLength;
			if (u) {
				if (u > t) {
					u -= t;
					continue;
				}
				r = r.subarray(u), t -= u, u = 0;
			}
			d.set(r, n), n += t;
		}
		return i && (i -= a + 3), {
			data: d,
			pts: o,
			dts: s,
			len: i
		};
	}
	return null;
}
var Gc = class {
	static getSilentFrame(e, t) {
		switch (e) {
			case "mp4a.40.2":
				if (t === 1) return new Uint8Array([
					0,
					200,
					0,
					128,
					35,
					128
				]);
				if (t === 2) return new Uint8Array([
					33,
					0,
					73,
					144,
					2,
					25,
					0,
					35,
					128
				]);
				if (t === 3) return new Uint8Array([
					0,
					200,
					0,
					128,
					32,
					132,
					1,
					38,
					64,
					8,
					100,
					0,
					142
				]);
				if (t === 4) return new Uint8Array([
					0,
					200,
					0,
					128,
					32,
					132,
					1,
					38,
					64,
					8,
					100,
					0,
					128,
					44,
					128,
					8,
					2,
					56
				]);
				if (t === 5) return new Uint8Array([
					0,
					200,
					0,
					128,
					32,
					132,
					1,
					38,
					64,
					8,
					100,
					0,
					130,
					48,
					4,
					153,
					0,
					33,
					144,
					2,
					56
				]);
				if (t === 6) return new Uint8Array([
					0,
					200,
					0,
					128,
					32,
					132,
					1,
					38,
					64,
					8,
					100,
					0,
					130,
					48,
					4,
					153,
					0,
					33,
					144,
					2,
					0,
					178,
					0,
					32,
					8,
					224
				]);
				break;
			default:
				if (t === 1) return new Uint8Array([
					1,
					64,
					34,
					128,
					163,
					78,
					230,
					128,
					186,
					8,
					0,
					0,
					0,
					28,
					6,
					241,
					193,
					10,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					94
				]);
				if (t === 2 || t === 3) return new Uint8Array([
					1,
					64,
					34,
					128,
					163,
					94,
					230,
					128,
					186,
					8,
					0,
					0,
					0,
					0,
					149,
					0,
					6,
					241,
					161,
					10,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					90,
					94
				]);
		}
	}
}, Kc = 2 ** 32 - 1, qc = class e {
	static init() {
		e.types = {
			avc1: [],
			avcC: [],
			hvc1: [],
			hvcC: [],
			btrt: [],
			dinf: [],
			dref: [],
			esds: [],
			ftyp: [],
			hdlr: [],
			mdat: [],
			mdhd: [],
			mdia: [],
			mfhd: [],
			minf: [],
			moof: [],
			moov: [],
			mp4a: [],
			".mp3": [],
			dac3: [],
			"ac-3": [],
			mvex: [],
			mvhd: [],
			pasp: [],
			sdtp: [],
			stbl: [],
			stco: [],
			stsc: [],
			stsd: [],
			stsz: [],
			stts: [],
			tfdt: [],
			tfhd: [],
			traf: [],
			trak: [],
			trun: [],
			trex: [],
			tkhd: [],
			vmhd: [],
			smhd: []
		};
		let t;
		for (t in e.types) e.types.hasOwnProperty(t) && (e.types[t] = [
			t.charCodeAt(0),
			t.charCodeAt(1),
			t.charCodeAt(2),
			t.charCodeAt(3)
		]);
		let n = new Uint8Array([
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			118,
			105,
			100,
			101,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			86,
			105,
			100,
			101,
			111,
			72,
			97,
			110,
			100,
			108,
			101,
			114,
			0
		]), r = new Uint8Array([
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			115,
			111,
			117,
			110,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			83,
			111,
			117,
			110,
			100,
			72,
			97,
			110,
			100,
			108,
			101,
			114,
			0
		]);
		e.HDLR_TYPES = {
			video: n,
			audio: r
		};
		let i = new Uint8Array([
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			1,
			0,
			0,
			0,
			12,
			117,
			114,
			108,
			32,
			0,
			0,
			0,
			1
		]), a = new Uint8Array([
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0
		]);
		e.STTS = e.STSC = e.STCO = a, e.STSZ = new Uint8Array([
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0
		]), e.VMHD = new Uint8Array([
			0,
			0,
			0,
			1,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0
		]), e.SMHD = new Uint8Array([
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0
		]), e.STSD = new Uint8Array([
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			1
		]);
		let o = new Uint8Array([
			105,
			115,
			111,
			109
		]), s = new Uint8Array([
			97,
			118,
			99,
			49
		]), c = new Uint8Array([
			0,
			0,
			0,
			1
		]);
		e.FTYP = e.box(e.types.ftyp, o, c, o, s), e.DINF = e.box(e.types.dinf, e.box(e.types.dref, i));
	}
	static box(e, ...t) {
		let n = 8, r = t.length, i = r;
		for (; r--;) n += t[r].byteLength;
		let a = new Uint8Array(n);
		for (a[0] = n >> 24 & 255, a[1] = n >> 16 & 255, a[2] = n >> 8 & 255, a[3] = n & 255, a.set(e, 4), r = 0, n = 8; r < i; r++) a.set(t[r], n), n += t[r].byteLength;
		return a;
	}
	static hdlr(t) {
		return e.box(e.types.hdlr, e.HDLR_TYPES[t]);
	}
	static mdat(t) {
		return e.box(e.types.mdat, t);
	}
	static mdhd(t, n) {
		n *= t;
		let r = Math.floor(n / (Kc + 1)), i = Math.floor(n % (Kc + 1));
		return e.box(e.types.mdhd, new Uint8Array([
			1,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			2,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			3,
			t >> 24 & 255,
			t >> 16 & 255,
			t >> 8 & 255,
			t & 255,
			r >> 24,
			r >> 16 & 255,
			r >> 8 & 255,
			r & 255,
			i >> 24,
			i >> 16 & 255,
			i >> 8 & 255,
			i & 255,
			85,
			196,
			0,
			0
		]));
	}
	static mdia(t) {
		return e.box(e.types.mdia, e.mdhd(t.timescale || 0, t.duration || 0), e.hdlr(t.type), e.minf(t));
	}
	static mfhd(t) {
		return e.box(e.types.mfhd, new Uint8Array([
			0,
			0,
			0,
			0,
			t >> 24,
			t >> 16 & 255,
			t >> 8 & 255,
			t & 255
		]));
	}
	static minf(t) {
		return t.type === "audio" ? e.box(e.types.minf, e.box(e.types.smhd, e.SMHD), e.DINF, e.stbl(t)) : e.box(e.types.minf, e.box(e.types.vmhd, e.VMHD), e.DINF, e.stbl(t));
	}
	static moof(t, n, r) {
		return e.box(e.types.moof, e.mfhd(t), e.traf(r, n));
	}
	static moov(t) {
		let n = t.length, r = [];
		for (; n--;) r[n] = e.trak(t[n]);
		return e.box.apply(null, [e.types.moov, e.mvhd(t[0].timescale || 0, t[0].duration || 0)].concat(r, e.mvex(t)));
	}
	static mvex(t) {
		let n = t.length, r = [];
		for (; n--;) r[n] = e.trex(t[n]);
		return e.box.apply(null, [e.types.mvex, ...r]);
	}
	static mvhd(t, n) {
		n *= t;
		let r = Math.floor(n / (Kc + 1)), i = Math.floor(n % (Kc + 1)), a = new Uint8Array([
			1,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			2,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			3,
			t >> 24 & 255,
			t >> 16 & 255,
			t >> 8 & 255,
			t & 255,
			r >> 24,
			r >> 16 & 255,
			r >> 8 & 255,
			r & 255,
			i >> 24,
			i >> 16 & 255,
			i >> 8 & 255,
			i & 255,
			0,
			1,
			0,
			0,
			1,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			1,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			1,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			64,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			255,
			255,
			255,
			255
		]);
		return e.box(e.types.mvhd, a);
	}
	static sdtp(t) {
		let n = t.samples || [], r = new Uint8Array(4 + n.length), i, a;
		for (i = 0; i < n.length; i++) a = n[i].flags, r[i + 4] = a.dependsOn << 4 | a.isDependedOn << 2 | a.hasRedundancy;
		return e.box(e.types.sdtp, r);
	}
	static stbl(t) {
		return e.box(e.types.stbl, e.stsd(t), e.box(e.types.stts, e.STTS), e.box(e.types.stsc, e.STSC), e.box(e.types.stsz, e.STSZ), e.box(e.types.stco, e.STCO));
	}
	static avc1(t) {
		let n = [], r = [], i, a, o;
		for (i = 0; i < t.sps.length; i++) a = t.sps[i], o = a.byteLength, n.push(o >>> 8 & 255), n.push(o & 255), n = n.concat(Array.prototype.slice.call(a));
		for (i = 0; i < t.pps.length; i++) a = t.pps[i], o = a.byteLength, r.push(o >>> 8 & 255), r.push(o & 255), r = r.concat(Array.prototype.slice.call(a));
		let s = e.box(e.types.avcC, new Uint8Array([
			1,
			n[3],
			n[4],
			n[5],
			255,
			224 | t.sps.length
		].concat(n, [t.pps.length], r))), c = t.width, l = t.height, u = t.pixelRatio[0], d = t.pixelRatio[1];
		return e.box(e.types.avc1, new Uint8Array([
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			1,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			c >> 8 & 255,
			c & 255,
			l >> 8 & 255,
			l & 255,
			0,
			72,
			0,
			0,
			0,
			72,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			1,
			18,
			100,
			97,
			105,
			108,
			121,
			109,
			111,
			116,
			105,
			111,
			110,
			47,
			104,
			108,
			115,
			46,
			106,
			115,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			24,
			17,
			17
		]), s, e.box(e.types.btrt, new Uint8Array([
			0,
			28,
			156,
			128,
			0,
			45,
			198,
			192,
			0,
			45,
			198,
			192
		])), e.box(e.types.pasp, new Uint8Array([
			u >> 24,
			u >> 16 & 255,
			u >> 8 & 255,
			u & 255,
			d >> 24,
			d >> 16 & 255,
			d >> 8 & 255,
			d & 255
		])));
	}
	static esds(e) {
		let t = e.config;
		return new Uint8Array([
			0,
			0,
			0,
			0,
			3,
			25,
			0,
			1,
			0,
			4,
			17,
			64,
			21,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			5,
			2,
			...t,
			6,
			1,
			2
		]);
	}
	static audioStsd(e) {
		let t = e.samplerate || 0;
		return new Uint8Array([
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			1,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			e.channelCount || 0,
			0,
			16,
			0,
			0,
			0,
			0,
			t >> 8 & 255,
			t & 255,
			0,
			0
		]);
	}
	static mp4a(t) {
		return e.box(e.types.mp4a, e.audioStsd(t), e.box(e.types.esds, e.esds(t)));
	}
	static mp3(t) {
		return e.box(e.types[".mp3"], e.audioStsd(t));
	}
	static ac3(t) {
		return e.box(e.types["ac-3"], e.audioStsd(t), e.box(e.types.dac3, t.config));
	}
	static stsd(t) {
		let { segmentCodec: n } = t;
		if (t.type === "audio") {
			if (n === "aac") return e.box(e.types.stsd, e.STSD, e.mp4a(t));
			if (n === "ac3" && t.config) return e.box(e.types.stsd, e.STSD, e.ac3(t));
			if (n === "mp3" && t.codec === "mp3") return e.box(e.types.stsd, e.STSD, e.mp3(t));
		} else if (t.pps && t.sps) {
			if (n === "avc") return e.box(e.types.stsd, e.STSD, e.avc1(t));
			if (n === "hevc" && t.vps) return e.box(e.types.stsd, e.STSD, e.hvc1(t));
		} else throw Error("video track missing pps or sps");
		throw Error(`unsupported ${t.type} segment codec (${n}/${t.codec})`);
	}
	static tkhd(t) {
		let n = t.id, r = (t.duration || 0) * (t.timescale || 0), i = t.width || 0, a = t.height || 0, o = Math.floor(r / (Kc + 1)), s = Math.floor(r % (Kc + 1));
		return e.box(e.types.tkhd, new Uint8Array([
			1,
			0,
			0,
			7,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			2,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			3,
			n >> 24 & 255,
			n >> 16 & 255,
			n >> 8 & 255,
			n & 255,
			0,
			0,
			0,
			0,
			o >> 24,
			o >> 16 & 255,
			o >> 8 & 255,
			o & 255,
			s >> 24,
			s >> 16 & 255,
			s >> 8 & 255,
			s & 255,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			1,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			1,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			64,
			0,
			0,
			0,
			i >> 8 & 255,
			i & 255,
			0,
			0,
			a >> 8 & 255,
			a & 255,
			0,
			0
		]));
	}
	static traf(t, n) {
		let r = e.sdtp(t), i = t.id, a = Math.floor(n / (Kc + 1)), o = Math.floor(n % (Kc + 1));
		return e.box(e.types.traf, e.box(e.types.tfhd, new Uint8Array([
			0,
			0,
			0,
			0,
			i >> 24,
			i >> 16 & 255,
			i >> 8 & 255,
			i & 255
		])), e.box(e.types.tfdt, new Uint8Array([
			1,
			0,
			0,
			0,
			a >> 24,
			a >> 16 & 255,
			a >> 8 & 255,
			a & 255,
			o >> 24,
			o >> 16 & 255,
			o >> 8 & 255,
			o & 255
		])), e.trun(t, r.length + 16 + 20 + 8 + 16 + 8 + 8), r);
	}
	static trak(t) {
		return t.duration = t.duration || 4294967295, e.box(e.types.trak, e.tkhd(t), e.mdia(t));
	}
	static trex(t) {
		let n = t.id;
		return e.box(e.types.trex, new Uint8Array([
			0,
			0,
			0,
			0,
			n >> 24,
			n >> 16 & 255,
			n >> 8 & 255,
			n & 255,
			0,
			0,
			0,
			1,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			1,
			0,
			1
		]));
	}
	static trun(t, n) {
		let r = t.samples || [], i = r.length, a = 12 + 16 * i, o = new Uint8Array(a), s, c, l, u, d, f;
		for (n += 8 + a, o.set([
			+(t.type === "video"),
			0,
			15,
			1,
			i >>> 24 & 255,
			i >>> 16 & 255,
			i >>> 8 & 255,
			i & 255,
			n >>> 24 & 255,
			n >>> 16 & 255,
			n >>> 8 & 255,
			n & 255
		], 0), s = 0; s < i; s++) c = r[s], l = c.duration, u = c.size, d = c.flags, f = c.cts, o.set([
			l >>> 24 & 255,
			l >>> 16 & 255,
			l >>> 8 & 255,
			l & 255,
			u >>> 24 & 255,
			u >>> 16 & 255,
			u >>> 8 & 255,
			u & 255,
			d.isLeading << 2 | d.dependsOn,
			d.isDependedOn << 6 | d.hasRedundancy << 4 | d.paddingValue << 1 | d.isNonSync,
			d.degradPrio & 61440,
			d.degradPrio & 15,
			f >>> 24 & 255,
			f >>> 16 & 255,
			f >>> 8 & 255,
			f & 255
		], 12 + 16 * s);
		return e.box(e.types.trun, o);
	}
	static initSegment(t) {
		e.types || e.init();
		let n = e.moov(t);
		return Ir(e.FTYP, n);
	}
	static hvc1(t) {
		let n = t.params, r = [
			t.vps,
			t.sps,
			t.pps
		], i = new Uint8Array([
			1,
			n.general_profile_space << 6 | (n.general_tier_flag ? 32 : 0) | n.general_profile_idc,
			n.general_profile_compatibility_flags[0],
			n.general_profile_compatibility_flags[1],
			n.general_profile_compatibility_flags[2],
			n.general_profile_compatibility_flags[3],
			n.general_constraint_indicator_flags[0],
			n.general_constraint_indicator_flags[1],
			n.general_constraint_indicator_flags[2],
			n.general_constraint_indicator_flags[3],
			n.general_constraint_indicator_flags[4],
			n.general_constraint_indicator_flags[5],
			n.general_level_idc,
			240 | n.min_spatial_segmentation_idc >> 8,
			255 & n.min_spatial_segmentation_idc,
			252 | n.parallelismType,
			252 | n.chroma_format_idc,
			248 | n.bit_depth_luma_minus8,
			248 | n.bit_depth_chroma_minus8,
			0,
			parseInt(n.frame_rate.fps),
			3 | n.temporal_id_nested << 2 | n.num_temporal_layers << 3 | (n.frame_rate.fixed ? 64 : 0),
			r.length
		]), a = i.length;
		for (let e = 0; e < r.length; e += 1) {
			a += 3;
			for (let t = 0; t < r[e].length; t += 1) a += 2 + r[e][t].length;
		}
		let o = new Uint8Array(a);
		o.set(i, 0), a = i.length;
		let s = r.length - 1;
		for (let e = 0; e < r.length; e += 1) {
			o.set(new Uint8Array([
				32 + e | (e === s ? 128 : 0),
				0,
				r[e].length
			]), a), a += 3;
			for (let t = 0; t < r[e].length; t += 1) o.set(new Uint8Array([r[e][t].length >> 8, r[e][t].length & 255]), a), a += 2, o.set(r[e][t], a), a += r[e][t].length;
		}
		let c = e.box(e.types.hvcC, o), l = t.width, u = t.height, d = t.pixelRatio[0], f = t.pixelRatio[1];
		return e.box(e.types.hvc1, new Uint8Array([
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			1,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			l >> 8 & 255,
			l & 255,
			u >> 8 & 255,
			u & 255,
			0,
			72,
			0,
			0,
			0,
			72,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			1,
			18,
			100,
			97,
			105,
			108,
			121,
			109,
			111,
			116,
			105,
			111,
			110,
			47,
			104,
			108,
			115,
			46,
			106,
			115,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			24,
			17,
			17
		]), c, e.box(e.types.btrt, new Uint8Array([
			0,
			28,
			156,
			128,
			0,
			45,
			198,
			192,
			0,
			45,
			198,
			192
		])), e.box(e.types.pasp, new Uint8Array([
			d >> 24,
			d >> 16 & 255,
			d >> 8 & 255,
			d & 255,
			f >> 24,
			f >> 16 & 255,
			f >> 8 & 255,
			f & 255
		])));
	}
};
qc.types = void 0, qc.HDLR_TYPES = void 0, qc.STTS = void 0, qc.STSC = void 0, qc.STCO = void 0, qc.STSZ = void 0, qc.VMHD = void 0, qc.SMHD = void 0, qc.STSD = void 0, qc.FTYP = void 0, qc.DINF = void 0;
var Jc = 9e4;
function Yc(e, t, n = 1, r = !1) {
	let i = e * t * n;
	return r ? Math.round(i) : i;
}
function Xc(e, t, n = 1, r = !1) {
	return Yc(e, t, 1 / n, r);
}
function Zc(e, t = !1) {
	return Yc(e, 1e3, 1 / Jc, t);
}
function Qc(e, t = 1) {
	return Yc(e, Jc, 1 / t);
}
function $c(e) {
	let { baseTime: t, timescale: n, trackId: r } = e;
	return `${t / n} (${t}/${n}) trackId: ${r}`;
}
var el = 1e4, tl = 1024, nl = 1152, rl = 1536, il = null, al = null;
function ol(e, t, n, r) {
	return {
		duration: t,
		size: n,
		cts: r,
		flags: {
			isLeading: 0,
			isDependedOn: 0,
			hasRedundancy: 0,
			degradPrio: 0,
			dependsOn: e ? 2 : 1,
			isNonSync: +!e
		}
	};
}
var sl = class extends Bn {
	constructor(e, t, n, r) {
		if (super("mp4-remuxer", r), this.observer = void 0, this.config = void 0, this.typeSupported = void 0, this.ISGenerated = !1, this._initPTS = null, this._initDTS = null, this.nextVideoTs = null, this.nextAudioTs = null, this.videoSampleDuration = null, this.isAudioContiguous = !1, this.isVideoContiguous = !1, this.videoTrackConfig = void 0, this.observer = e, this.config = t, this.typeSupported = n, this.ISGenerated = !1, il === null) {
			let e = (navigator.userAgent || "").match(/Chrome\/(\d+)/i);
			il = e ? parseInt(e[1]) : 0;
		}
		if (al === null) {
			let e = navigator.userAgent.match(/Safari\/(\d+)/i);
			al = e ? parseInt(e[1]) : 0;
		}
	}
	destroy() {
		this.config = this.videoTrackConfig = this._initPTS = this._initDTS = null;
	}
	resetTimeStamp(e) {
		let t = this._initPTS;
		t && e && e.trackId === t.trackId && e.baseTime === t.baseTime && e.timescale === t.timescale || this.log(`Reset initPTS: ${t && $c(t)} > ${e && $c(e)}`), this._initPTS = this._initDTS = e;
	}
	resetNextTimestamp() {
		this.log("reset next timestamp"), this.isVideoContiguous = !1, this.isAudioContiguous = !1;
	}
	resetInitSegment() {
		this.log("ISGenerated flag reset"), this.ISGenerated = !1, this.videoTrackConfig = void 0;
	}
	getVideoStartPts(e) {
		let t = !1, n = e[0].pts, r = e.reduce((e, r) => {
			let i = r.pts, a = i - e;
			return a < -4294967296 && (t = !0, i = cl(i, n), a = i - e), a > 0 ? e : i;
		}, n);
		return t && this.debug("PTS rollover detected"), r;
	}
	remux(e, t, n, r, i, a, o, s) {
		let c, l, u, d, f, p, m = i, h = i, g = e.pid > -1, _ = t.pid > -1, v = t.samples.length, y = e.samples.length > 0, b = o && v > 0 || v > 1;
		if ((!g || y) && (!_ || b) || this.ISGenerated || o) {
			if (this.ISGenerated) {
				let e = this.videoTrackConfig;
				(e && (t.width !== e.width || t.height !== e.height || t.pixelRatio?.[0] !== e.pixelRatio?.[0] || t.pixelRatio?.[1] !== e.pixelRatio?.[1]) || !e && b || this.nextAudioTs === null && y) && this.resetInitSegment();
			}
			this.ISGenerated || (u = this.generateIS(e, t, i, a));
			let n = this.isVideoContiguous, r = -1, o;
			if (b && (r = ll(t.samples), !n && this.config.forceKeyFrameOnDiscontinuity)) {
				if (p = !0, r > 0) {
					this.warn(`Dropped ${r} out of ${v} video samples due to a missing keyframe`);
					let e = this.getVideoStartPts(t.samples);
					t.samples = t.samples.slice(r), t.dropped += r, h += (t.samples[0].pts - e) / t.inputTimeScale, o = h;
				} else r === -1 && (this.warn(`No keyframe found out of ${v} video samples`), p = !1);
			}
			if (this.ISGenerated) {
				if (y && b) {
					let n = this.getVideoStartPts(t.samples), r = (cl(e.samples[0].pts, n) - n) / t.inputTimeScale;
					m += Math.max(0, r), h += Math.max(0, -r);
				}
				if (y) {
					if (e.samplerate || (this.warn("regenerate InitSegment as audio detected"), u = this.generateIS(e, t, i, a)), l = this.remuxAudio(e, m, this.isAudioContiguous, a, _ || b || s === Y.AUDIO ? h : void 0), b) {
						let r = l ? l.endPTS - l.startPTS : 0;
						t.inputTimeScale || (this.warn("regenerate InitSegment as video detected"), u = this.generateIS(e, t, i, a)), c = this.remuxVideo(t, h, n, r);
					}
				} else b && (c = this.remuxVideo(t, h, n, 0));
				c && (c.firstKeyFrame = r, c.independent = r !== -1, c.firstKeyFramePTS = o);
			}
		}
		return this.ISGenerated && this._initPTS && this._initDTS && (n.samples.length && (f = ul(n, i, this._initPTS, this._initDTS)), r.samples.length && (d = dl(r, i, this._initPTS))), {
			audio: l,
			video: c,
			initSegment: u,
			independent: p,
			text: d,
			id3: f
		};
	}
	computeInitPts(e, t, n, r) {
		let i = Math.round(n * t), a = cl(e, i);
		if (a < i + t) for (this.log(`Adjusting PTS for rollover in timeline near ${(i - a) / t} ${r}`); a < i + t;) a += 8589934592;
		return a - i;
	}
	generateIS(e, t, n, r) {
		let i = e.samples, a = t.samples, o = this.typeSupported, s = {}, c = this._initPTS, l = !c || r, u = "audio/mp4", d, f, p, m = -1;
		if (l && (d = f = Infinity), e.config && i.length) {
			switch (e.timescale = e.samplerate, e.segmentCodec) {
				case "mp3":
					o.mpeg ? (u = "audio/mpeg", e.codec = "") : o.mp3 && (e.codec = "mp3");
					break;
				case "ac3": e.codec = "ac-3";
			}
			s.audio = {
				id: "audio",
				container: u,
				codec: e.codec,
				initSegment: e.segmentCodec === "mp3" && o.mpeg ? /* @__PURE__ */ new Uint8Array() : qc.initSegment([e]),
				metadata: { channelCount: e.channelCount }
			}, l && (m = e.id, p = e.inputTimeScale, !c || p !== c.timescale ? d = f = this.computeInitPts(i[0].pts, p, n, "audio") : l = !1);
		}
		if (t.sps && t.pps && a.length) {
			if (t.timescale = t.inputTimeScale, s.video = {
				id: "main",
				container: "video/mp4",
				codec: t.codec,
				initSegment: qc.initSegment([t]),
				metadata: {
					width: t.width,
					height: t.height
				}
			}, l) {
				if (m = t.id, p = t.inputTimeScale, !c || p !== c.timescale) {
					let e = this.getVideoStartPts(a), t = cl(a[0].dts, e), r = this.computeInitPts(t, p, n, "video"), i = this.computeInitPts(e, p, n, "video");
					f = Math.min(f, r), d = Math.min(d, i);
				} else l = !1;
			}
			this.videoTrackConfig = {
				width: t.width,
				height: t.height,
				pixelRatio: t.pixelRatio
			};
		}
		if (Object.keys(s).length) return this.ISGenerated = !0, l ? (c && this.warn(`Timestamps at playlist time: ${r ? "" : "~"}${n} ${d / p} != initPTS: ${c.baseTime / c.timescale} (${c.baseTime}/${c.timescale}) trackId: ${c.trackId}`), this.log(`Found initPTS at playlist time: ${n} offset: ${d / p} (${d}/${p}) trackId: ${m}`), this._initPTS = {
			baseTime: d,
			timescale: p,
			trackId: m
		}, this._initDTS = {
			baseTime: f,
			timescale: p,
			trackId: m
		}) : d = p = void 0, {
			tracks: s,
			initPTS: d,
			timescale: p,
			trackId: m
		};
	}
	remuxVideo(e, t, n, r) {
		let i = e.inputTimeScale, a = e.samples, o = [], s = a.length, c = this._initPTS, l = c.baseTime * i / c.timescale, u = this.nextVideoTs, d = 8, f = this.videoSampleDuration, p, m, h = Infinity, g = -Infinity, _ = !1;
		if (!n || u === null) {
			let e = l + t * i, r = a[0].pts - cl(a[0].dts, a[0].pts);
			il && u !== null && Math.abs(e - r - (u + l)) < 15e3 ? n = !0 : u = e - r - l;
		}
		let v = u + l;
		for (let e = 0; e < s; e++) {
			let t = a[e];
			t.pts = cl(t.pts, v), t.dts = cl(t.dts, v), t.dts < a[e > 0 ? e - 1 : e].dts && (_ = !0);
		}
		_ && a.sort(function(e, t) {
			let n = e.dts - t.dts, r = e.pts - t.pts;
			return n || r;
		}), p = a[0].dts, m = a[a.length - 1].dts;
		let y = m - p, b = y ? Math.round(y / (s - 1)) : f || e.inputTimeScale / 30;
		if (n) {
			let n = p - v, r = n > b, i = n < -1;
			if ((r || i) && (r ? this.warn(`${(e.segmentCodec || "").toUpperCase()}: ${Zc(n, !0)} ms (${n}dts) hole between fragments detected at ${t.toFixed(3)}`) : this.warn(`${(e.segmentCodec || "").toUpperCase()}: ${Zc(-n, !0)} ms (${n}dts) overlapping between fragments detected at ${t.toFixed(3)}`), !i || v >= a[0].pts || il)) {
				p = v;
				let e = a[0].pts - n;
				if (r) a[0].dts = p, a[0].pts = e;
				else {
					let t = !0;
					for (let r = 0; r < a.length && !(a[r].dts > e && t); r++) {
						let e = a[r].pts;
						if (a[r].dts -= n, a[r].pts -= n, r < a.length - 1) {
							let n = a[r + 1].pts;
							t = n <= a[r].pts == n <= e;
						}
					}
				}
				this.log(`Video: Initial PTS/DTS adjusted: ${Zc(e, !0)}/${Zc(p, !0)}, delta: ${Zc(n, !0)} ms`);
			}
		}
		p = Math.max(0, p);
		let x = 0, S = 0, C = p;
		for (let e = 0; e < s; e++) {
			let t = a[e], n = t.units, r = n.length, i = 0;
			for (let e = 0; e < r; e++) i += n[e].data.length;
			S += i, x += r, t.length = i, t.dts < C ? (t.dts = C, C += b / 4 | 0 || 1) : C = t.dts, h = Math.min(t.pts, h), g = Math.max(t.pts, g);
		}
		m = a[s - 1].dts;
		let w = S + 4 * x + 8, T;
		try {
			T = new Uint8Array(w);
		} catch (e) {
			this.observer.emit(q.ERROR, q.ERROR, {
				type: G.MUX_ERROR,
				details: K.REMUX_ALLOC_ERROR,
				fatal: !1,
				error: e,
				bytes: w,
				reason: `fail allocating video mdat ${w}`
			});
			return;
		}
		let E = new DataView(T.buffer);
		E.setUint32(0, w), T.set(qc.types.mdat, 4);
		let D = !1, O = Infinity, k = Infinity, A = -Infinity, j = -Infinity;
		for (let e = 0; e < s; e++) {
			let t = a[e], n = t.units, c = 0;
			for (let e = 0, t = n.length; e < t; e++) {
				let t = n[e], r = t.data, i = t.data.byteLength;
				E.setUint32(d, i), d += 4, T.set(r, d), d += i, c += 4 + i;
			}
			let u;
			if (e < s - 1) f = a[e + 1].dts - t.dts, u = a[e + 1].pts - t.pts;
			else {
				let n = this.config, o = e > 0 ? t.dts - a[e - 1].dts : b;
				if (u = e > 0 ? t.pts - a[e - 1].pts : b, n.stretchShortVideoTrack && this.nextAudioTs !== null) {
					let e = Math.floor(n.maxBufferHole * i), a = (r ? h + r * i : this.nextAudioTs + l) - t.pts;
					a > e ? (f = a - o, f < 0 ? f = o : D = !0, this.log(`It is approximately ${a / 90} ms to the next segment; using duration ${f / 90} ms for the last video frame.`)) : f = o;
				} else f = o;
			}
			let p = Math.round(t.pts - t.dts);
			O = Math.min(O, f), A = Math.max(A, f), k = Math.min(k, u), j = Math.max(j, u), o.push(ol(t.key, f, c, p));
		}
		if (o.length) {
			if (il) {
				if (il < 70) {
					let e = o[0].flags;
					e.dependsOn = 2, e.isNonSync = 0;
				}
			} else if (al && j - k < A - O && b / A < .025 && o[0].cts === 0) {
				this.warn("Found irregular gaps in sample duration. Using PTS instead of DTS to determine MP4 sample duration.");
				let e = p;
				for (let t = 0, n = o.length; t < n; t++) {
					let r = e + o[t].duration, i = e + o[t].cts;
					if (t < n - 1) {
						let e = r + o[t + 1].cts;
						o[t].duration = e - i;
					} else o[t].duration = t ? o[t - 1].duration : b;
					o[t].cts = 0, e = r;
				}
			}
		}
		f = D || !f ? b : f;
		let M = m + f;
		this.nextVideoTs = u = M - l, this.videoSampleDuration = f, this.isVideoContiguous = !0;
		let N = {
			data1: qc.moof(e.sequenceNumber++, p, Fn(e, { samples: o })),
			data2: T,
			startPTS: (h - l) / i,
			endPTS: (g + f - l) / i,
			startDTS: (p - l) / i,
			endDTS: u / i,
			type: "video",
			hasAudio: !1,
			hasVideo: !0,
			nb: o.length,
			dropped: e.dropped
		};
		return e.samples = [], e.dropped = 0, N;
	}
	getSamplesPerFrame(e) {
		switch (e.segmentCodec) {
			case "mp3": return nl;
			case "ac3": return rl;
			default: return tl;
		}
	}
	remuxAudio(e, t, n, r, i) {
		let a = e.inputTimeScale, o = a / (e.samplerate ? e.samplerate : a), s = this.getSamplesPerFrame(e), c = s * o, l = this._initPTS, u = e.segmentCodec === "mp3" && this.typeSupported.mpeg, d = [], f = i !== void 0, p = e.samples, m = u ? 0 : 8, h = this.nextAudioTs || -1, g = l.baseTime * a / l.timescale, _ = g + t * a;
		if (this.isAudioContiguous = n ||= p.length && h > 0 && (r && Math.abs(_ - (h + g)) < 9e3 || Math.abs(cl(p[0].pts, _) - (h + g)) < 20 * c), p.forEach(function(e) {
			e.pts = cl(e.pts, _);
		}), !n || h < 0) {
			let e = p.length;
			if (p = p.filter((e) => e.pts >= 0), e !== p.length && this.warn(`Removed ${p.length - e} of ${e} samples (initPTS ${g} / ${a})`), !p.length) return;
			h = i === 0 ? 0 : r && !f ? Math.max(0, _ - g) : p[0].pts - g;
		}
		if (e.segmentCodec === "aac") {
			let t = this.config.maxAudioFramesDrift;
			for (let n = 0, r = h + g; n < p.length; n++) {
				let i = p[n], o = i.pts, s = o - r, l = Math.abs(1e3 * s / a);
				if (s <= -t * c && f) n === 0 && (this.warn(`Audio frame @ ${(o / a).toFixed(3)}s overlaps marker by ${Math.round(1e3 * s / a)} ms.`), this.nextAudioTs = h = o - g, r = o);
				else if (s >= t * c && l < el && f) {
					let t = Math.round(s / c);
					for (r = o - t * c; r < 0 && t && c;) t--, r += c;
					n === 0 && (this.nextAudioTs = h = r - g), this.warn(`Injecting ${t} audio frames @ ${((r - g) / a).toFixed(3)}s due to ${Math.round(1e3 * s / a)} ms gap.`);
					for (let a = 0; a < t; a++) {
						let t = Gc.getSilentFrame(e.parsedCodec || e.manifestCodec || e.codec, e.channelCount);
						t ||= (this.log("Unable to get silent frame for given audio codec; duplicating last frame instead."), i.unit.subarray()), p.splice(n, 0, {
							unit: t,
							pts: r
						}), r += c, n++;
					}
				}
				i.pts = r, r += c;
			}
		}
		let v = null, y = null, b, x = 0, S = p.length;
		for (; S--;) x += p[S].unit.byteLength;
		for (let t = 0, r = p.length; t < r; t++) {
			let r = p[t], i = r.unit, a = r.pts;
			if (y !== null) {
				let e = d[t - 1];
				e.duration = Math.round((a - y) / o);
			} else if (n && e.segmentCodec === "aac" && (a = h + g), v = a, x > 0) {
				x += m;
				try {
					b = new Uint8Array(x);
				} catch (e) {
					this.observer.emit(q.ERROR, q.ERROR, {
						type: G.MUX_ERROR,
						details: K.REMUX_ALLOC_ERROR,
						fatal: !1,
						error: e,
						bytes: x,
						reason: `fail allocating audio mdat ${x}`
					});
					return;
				}
				u || (new DataView(b.buffer).setUint32(0, x), b.set(qc.types.mdat, 4));
			} else return;
			b.set(i, m);
			let c = i.byteLength;
			m += c, d.push(ol(!0, s, c, 0)), y = a;
		}
		let C = d.length;
		if (!C) return;
		let w = d[d.length - 1];
		h = y - g, this.nextAudioTs = h + o * w.duration;
		let T = u ? /* @__PURE__ */ new Uint8Array() : qc.moof(e.sequenceNumber++, v / o, Fn({}, e, { samples: d }));
		e.samples = [];
		let E = (v - g) / a, D = this.nextAudioTs / a, O = {
			data1: T,
			data2: b,
			startPTS: E,
			endPTS: D,
			startDTS: E,
			endDTS: D,
			type: "audio",
			hasAudio: !0,
			hasVideo: !1,
			nb: C
		};
		return this.isAudioContiguous = !0, O;
	}
};
function cl(e, t) {
	let n;
	if (t === null) return e;
	for (n = t < e ? -8589934592 : 8589934592; Math.abs(e - t) > 4294967296;) e += n;
	return e;
}
function ll(e) {
	for (let t = 0; t < e.length; t++) if (e[t].key) return t;
	return -1;
}
function ul(e, t, n, r) {
	let i = e.samples.length;
	if (!i) return;
	let a = e.inputTimeScale;
	for (let o = 0; o < i; o++) {
		let i = e.samples[o];
		i.pts = cl(i.pts - n.baseTime * a / n.timescale, t * a) / a, i.dts = cl(i.dts - r.baseTime * a / r.timescale, t * a) / a;
	}
	let o = e.samples;
	return e.samples = [], { samples: o };
}
function dl(e, t, n) {
	let r = e.samples.length;
	if (!r) return;
	let i = e.inputTimeScale;
	for (let a = 0; a < r; a++) {
		let r = e.samples[a];
		r.pts = cl(r.pts - n.baseTime * i / n.timescale, t * i) / i;
	}
	e.samples.sort((e, t) => e.pts - t.pts);
	let a = e.samples;
	return e.samples = [], { samples: a };
}
var fl = class extends Bn {
	constructor(e, t, n, r) {
		super("passthrough-remuxer", r), this.emitInitSegment = !1, this.audioCodec = void 0, this.videoCodec = void 0, this.initData = void 0, this.initPTS = null, this.initTracks = void 0, this.lastEndTime = null, this.isVideoContiguous = !1;
	}
	destroy() {}
	resetTimeStamp(e) {
		this.lastEndTime = null;
		let t = this.initPTS;
		t && e && t.baseTime === e.baseTime && t.timescale === e.timescale || (this.initPTS = e);
	}
	resetNextTimestamp() {
		this.isVideoContiguous = !1, this.lastEndTime = null;
	}
	resetInitSegment(e, t, n, r) {
		this.audioCodec = t, this.videoCodec = n, this.generateInitSegment(e, r), this.emitInitSegment = !0;
	}
	generateInitSegment(e, t) {
		let { audioCodec: n, videoCodec: r } = this;
		if (!(e != null && e.byteLength)) {
			this.initTracks = void 0, this.initData = void 0;
			return;
		}
		let { audio: i, video: a } = this.initData = Cr(e);
		if (t) Ar(e, t);
		else {
			let e = i || a;
			e != null && e.encrypted && this.warn(`Init segment with encrypted track with has no key ("${e.codec}")!`);
		}
		i && (n = hl(i, sr.AUDIO, this)), a && (r = hl(a, sr.VIDEO, this));
		let o = {};
		i && a ? o.audiovideo = {
			container: "video/mp4",
			codec: n + "," + r,
			supplemental: a.supplemental,
			encrypted: a.encrypted,
			initSegment: e,
			id: "main"
		} : i ? o.audio = {
			container: "audio/mp4",
			codec: n,
			encrypted: i.encrypted,
			initSegment: e,
			id: "audio"
		} : a ? o.video = {
			container: "video/mp4",
			codec: r,
			supplemental: a.supplemental,
			encrypted: a.encrypted,
			initSegment: e,
			id: "main"
		} : this.warn("initSegment does not contain moov or trak boxes."), this.initTracks = o;
	}
	remux(e, t, n, r, i, a) {
		var o, s;
		let { initPTS: c, lastEndTime: l } = this, u = {
			audio: void 0,
			video: void 0,
			text: r,
			id3: n,
			initSegment: void 0
		};
		W(l) || (l = this.lastEndTime = i || 0);
		let d = t.samples;
		if (!d.length) return u;
		let f = {
			initPTS: void 0,
			timescale: void 0,
			trackId: void 0
		}, p = this.initData;
		if ((o = p) != null && o.length || (this.generateInitSegment(d), p = this.initData), !((s = p) != null && s.length)) return this.warn("Failed to generate initSegment."), u;
		this.emitInitSegment &&= (f.tracks = this.initTracks, !1);
		let m = Pr(d, p, this), h = p.audio ? m[p.audio.id] : null, g = p.video ? m[p.video.id] : null, _ = pl(g, Infinity), v = pl(h, Infinity), y = pl(g, 0, !0), b = pl(h, 0, !0), x = i, S = 0, C = h && (!g || !c && v < _ || c && c.trackId === p.audio.id), w = C ? h : g;
		if (w) {
			let e = w.timescale, t = w.start - i * e, n = C ? p.audio.id : p.video.id;
			x = w.start / e, S = C ? b - v : y - _, !a && c || !ml(c, x, i, S) && e === c.timescale || (c && this.warn(`Timestamps at playlist time: ${a ? "" : "~"}${i} ${t / e} != initPTS: ${c.baseTime / c.timescale} (${c.baseTime}/${c.timescale}) trackId: ${c.trackId}`), this.log(`Found initPTS at playlist time: ${i} offset: ${x - i} (${t}/${e}) trackId: ${n}`), c = null, f.initPTS = t, f.timescale = e, f.trackId = n);
		} else this.warn(`No audio or video samples found for initPTS at playlist time: ${i}`);
		c ? (f.initPTS = c.baseTime, f.timescale = c.timescale, f.trackId = c.trackId) : (f.timescale && f.trackId !== void 0 && f.initPTS !== void 0 || (this.warn("Could not set initPTS"), f.initPTS = x, f.timescale = 1, f.trackId = -1), this.initPTS = c = {
			baseTime: f.initPTS,
			timescale: f.timescale,
			trackId: f.trackId
		});
		let T = x - c.baseTime / c.timescale, E = T + S;
		S > 0 ? this.lastEndTime = E : (this.warn("Duration parsed from mp4 should be greater than zero"), this.resetNextTimestamp());
		let D = !!p.audio, O = !!p.video, k = "";
		D && (k += "audio"), O && (k += "video");
		let A = (p.audio ? p.audio.encrypted : !1) || (p.video ? p.video.encrypted : !1), j = {
			data1: d,
			startPTS: T,
			startDTS: T,
			endPTS: E,
			endDTS: E,
			type: k,
			hasAudio: D,
			hasVideo: O,
			nb: 1,
			dropped: 0,
			encrypted: A
		};
		u.audio = D && !O ? j : void 0, u.video = O ? j : void 0;
		let M = g?.sampleCount;
		if (M) {
			let e = g.keyFrameIndex, t = e !== -1;
			j.nb = M, j.dropped = e === 0 || this.isVideoContiguous ? 0 : t ? e : M, j.independent = t, j.firstKeyFrame = e, t && g.keyFrameStart && (j.firstKeyFramePTS = (g.keyFrameStart - c.baseTime) / c.timescale), this.isVideoContiguous || (u.independent = t), this.isVideoContiguous ||= t, j.dropped && this.warn(`fmp4 does not start with IDR: firstIDR ${e}/${M} dropped: ${j.dropped} start: ${j.firstKeyFramePTS || "NA"}`);
		}
		return u.initSegment = f, u.id3 = ul(n, i, c, c), r.samples.length && (u.text = dl(r, i, c)), u;
	}
};
function pl(e, t, n = !1) {
	return e?.start === void 0 ? t : (e.start + (n ? e.duration : 0)) / e.timescale;
}
function ml(e, t, n, r) {
	if (e === null) return !0;
	let i = Math.max(r, 1), a = t - e.baseTime / e.timescale;
	return Math.abs(a - n) > i;
}
function hl(e, t, n) {
	let r = e.codec;
	return r && r.length > 4 ? r : t === sr.AUDIO ? r === "ec-3" || r === "ac-3" || r === "alac" ? r : r === "fLaC" || r === "Opus" ? ii(r, !1) : (n.warn(`Unhandled audio codec "${r}" in mp4 MAP`), r || "mp4a") : (n.warn(`Unhandled video codec "${r}" in mp4 MAP`), r || "avc1");
}
var gl;
try {
	gl = self.performance.now.bind(self.performance);
} catch {
	gl = Date.now;
}
var _l = [
	{
		demux: Ac,
		remux: fl
	},
	{
		demux: Rc,
		remux: sl
	},
	{
		demux: wc,
		remux: sl
	},
	{
		demux: Oc,
		remux: sl
	}
];
_l.splice(2, 0, {
	demux: Ec,
	remux: sl
});
var vl = class {
	constructor(e, t, n, r, i, a) {
		this.asyncResult = !1, this.logger = void 0, this.observer = void 0, this.typeSupported = void 0, this.config = void 0, this.id = void 0, this.demuxer = void 0, this.remuxer = void 0, this.decrypter = void 0, this.probe = void 0, this.decryptionPromise = null, this.transmuxConfig = void 0, this.currentTransmuxState = void 0, this.observer = e, this.typeSupported = t, this.config = n, this.id = i, this.logger = a;
	}
	configure(e) {
		this.transmuxConfig = e, this.decrypter && this.decrypter.reset();
	}
	push(e, t, n, r) {
		let i = n.transmuxing;
		i.executeStart = gl();
		let a = new Uint8Array(e), { currentTransmuxState: o, transmuxConfig: s } = this;
		r && (this.currentTransmuxState = r);
		let { contiguous: c, discontinuity: l, trackSwitch: u, accurateTimeOffset: d, timeOffset: f, initSegmentChange: p } = r || o, { audioCodec: m, videoCodec: h, defaultInitPts: g, duration: _, initSegmentData: v } = s, y = yl(a, t);
		if (y && to(y.method)) {
			let e = this.getDecrypter(), t = no(y.method);
			if (e.isSync()) {
				let r = e.softwareDecrypt(a, y.key.buffer, y.iv.buffer, t);
				if (n.part > -1) {
					let t = e.flush();
					r = t && t.buffer;
				}
				if (!r) return i.executeEnd = gl(), bl(n);
				a = new Uint8Array(r);
			} else return this.asyncResult = !0, this.decryptionPromise = e.webCryptoDecrypt(a, y.key.buffer, y.iv.buffer, t).then((e) => {
				let t = this.push(e, null, n);
				return this.decryptionPromise = null, t;
			}), this.decryptionPromise;
		}
		let b = this.needsProbing(l, u);
		if (b) {
			let e = this.configureTransmuxer(a);
			if (e) return this.logger.warn(`[transmuxer] ${e.message}`), this.observer.emit(q.ERROR, q.ERROR, {
				type: G.MEDIA_ERROR,
				details: K.FRAG_PARSING_ERROR,
				fatal: !1,
				error: e,
				reason: e.message
			}), i.executeEnd = gl(), bl(n);
		}
		(l || u || p || b) && this.resetInitSegment(v, m, h, _, t), (l || p || b) && this.resetInitialTimestamp(g), c || this.resetContiguity();
		let x = this.transmux(a, y, f, d, n);
		this.asyncResult = xl(x);
		let S = this.currentTransmuxState;
		return S.contiguous = !0, S.discontinuity = !1, S.trackSwitch = !1, i.executeEnd = gl(), x;
	}
	flush(e) {
		let t = e.transmuxing;
		t.executeStart = gl();
		let { decrypter: n, currentTransmuxState: r, decryptionPromise: i } = this;
		if (i) return this.asyncResult = !0, i.then(() => this.flush(e));
		let a = [], { timeOffset: o } = r;
		if (n) {
			let t = n.flush();
			t && a.push(this.push(t.buffer, null, e));
		}
		let { demuxer: s, remuxer: c } = this;
		if (!s || !c) {
			t.executeEnd = gl();
			let n = [bl(e)];
			return this.asyncResult ? Promise.resolve(n) : n;
		}
		let l = s.flush(o);
		return xl(l) ? (this.asyncResult = !0, l.then((t) => (this.flushRemux(a, t, e), a))) : (this.flushRemux(a, l, e), this.asyncResult ? Promise.resolve(a) : a);
	}
	flushRemux(e, t, n) {
		let { audioTrack: r, videoTrack: i, id3Track: a, textTrack: o } = t, { accurateTimeOffset: s, timeOffset: c } = this.currentTransmuxState;
		this.logger.log(`[transmuxer.ts]: Flushed ${this.id} sn: ${n.sn}${n.part > -1 ? " part: " + n.part : ""} of ${this.id === Y.MAIN ? "level" : "track"} ${n.level}`);
		let l = this.remuxer.remux(r, i, a, o, c, s, !0, this.id);
		e.push({
			remuxResult: l,
			chunkMeta: n
		}), n.transmuxing.executeEnd = gl();
	}
	resetInitialTimestamp(e) {
		let { demuxer: t, remuxer: n } = this;
		t && n && (t.resetTimeStamp(e), n.resetTimeStamp(e));
	}
	resetContiguity() {
		let { demuxer: e, remuxer: t } = this;
		e && t && (e.resetContiguity(), t.resetNextTimestamp());
	}
	resetInitSegment(e, t, n, r, i) {
		let { demuxer: a, remuxer: o } = this;
		a && o && (a.resetInitSegment(e, t, n, r), o.resetInitSegment(e, t, n, i));
	}
	destroy() {
		this.demuxer &&= (this.demuxer.destroy(), void 0), this.remuxer &&= (this.remuxer.destroy(), void 0);
	}
	transmux(e, t, n, r, i) {
		let a;
		return a = t && t.method === "SAMPLE-AES" ? this.transmuxSampleAes(e, t, n, r, i) : this.transmuxUnencrypted(e, n, r, i), a;
	}
	transmuxUnencrypted(e, t, n, r) {
		let { audioTrack: i, videoTrack: a, id3Track: o, textTrack: s } = this.demuxer.demux(e, t, !1, !this.config.progressive);
		return {
			remuxResult: this.remuxer.remux(i, a, o, s, t, n, !1, this.id),
			chunkMeta: r
		};
	}
	transmuxSampleAes(e, t, n, r, i) {
		return this.demuxer.demuxSampleAes(e, t, n).then((e) => ({
			remuxResult: this.remuxer.remux(e.audioTrack, e.videoTrack, e.id3Track, e.textTrack, n, r, !1, this.id),
			chunkMeta: i
		}));
	}
	configureTransmuxer(e) {
		let { config: t, observer: n, typeSupported: r } = this, i;
		for (let t = 0, n = _l.length; t < n; t++) {
			var a;
			if ((a = _l[t].demux) != null && a.probe(e, this.logger)) {
				i = _l[t];
				break;
			}
		}
		if (!i) return /* @__PURE__ */ Error("Failed to find demuxer by probing fragment data");
		let o = this.demuxer, s = this.remuxer, c = i.remux, l = i.demux;
		s && s instanceof c || (this.remuxer = new c(n, t, r, this.logger)), o && o instanceof l || (this.demuxer = new l(n, t, r, this.logger), this.probe = l.probe);
	}
	needsProbing(e, t) {
		return !this.demuxer || !this.remuxer || e || t;
	}
	getDecrypter() {
		let e = this.decrypter;
		return e ||= this.decrypter = new Oa(this.config), e;
	}
};
function yl(e, t) {
	let n = null;
	return e.byteLength > 0 && t?.key != null && t.iv !== null && t.method != null && (n = t), n;
}
var bl = (e) => ({
	remuxResult: {},
	chunkMeta: e
});
function xl(e) {
	return "then" in e && e.then instanceof Function;
}
var Sl = class {
	constructor(e, t, n, r, i) {
		this.audioCodec = void 0, this.videoCodec = void 0, this.initSegmentData = void 0, this.duration = void 0, this.defaultInitPts = void 0, this.audioCodec = e, this.videoCodec = t, this.initSegmentData = n, this.duration = r, this.defaultInitPts = i || null;
	}
}, Cl = class {
	constructor(e, t, n, r, i, a) {
		this.discontinuity = void 0, this.contiguous = void 0, this.accurateTimeOffset = void 0, this.trackSwitch = void 0, this.timeOffset = void 0, this.initSegmentChange = void 0, this.discontinuity = e, this.contiguous = t, this.accurateTimeOffset = n, this.trackSwitch = r, this.timeOffset = i, this.initSegmentChange = a;
	}
}, wl = 0, Tl = class {
	constructor(e, t, n, r) {
		this.error = null, this.hls = void 0, this.id = void 0, this.instanceNo = wl++, this.observer = void 0, this.frag = null, this.part = null, this.useWorker = void 0, this.workerContext = null, this.transmuxer = null, this.onTransmuxComplete = void 0, this.onFlush = void 0, this.onWorkerMessage = (e) => {
			let t = e.data, n = this.hls;
			if (n && t != null && t.event && t.instanceNo === this.instanceNo) switch (t.event) {
				case "init": {
					let e = this.workerContext?.objectURL;
					e && self.URL.revokeObjectURL(e);
					break;
				}
				case "transmuxComplete":
					this.handleTransmuxComplete(t.data);
					break;
				case "flush":
					this.onFlush(t.data);
					break;
				case "workerLog":
					n.logger[t.data.logType] && n.logger[t.data.logType](t.data.message);
					break;
				default: t.data = t.data || {}, t.data.frag = this.frag, t.data.part = this.part, t.data.id = this.id, n.trigger(t.event, t.data);
			}
		}, this.onWorkerError = (e) => {
			if (!this.hls) return;
			let t = /* @__PURE__ */ Error(`${e.message}  (${e.filename}:${e.lineno})`);
			this.hls.config.enableWorker = !1, this.hls.logger.warn(`Error in "${this.id}" Web Worker, fallback to inline`), this.hls.trigger(q.ERROR, {
				type: G.OTHER_ERROR,
				details: K.INTERNAL_EXCEPTION,
				fatal: !1,
				event: "demuxerWorker",
				error: t
			});
		};
		let i = e.config;
		this.hls = e, this.id = t, this.useWorker = !!i.enableWorker, this.onTransmuxComplete = n, this.onFlush = r;
		let a = (e, t) => {
			t ||= {}, t.frag = this.frag || void 0, e === q.ERROR && (t = t, t.parent = this.id, t.part = this.part, this.error = t.error), this.hls.trigger(e, t);
		};
		this.observer = new Ss(), this.observer.on(q.FRAG_DECRYPTED, a), this.observer.on(q.ERROR, a);
		let o = ui(i.preferManagedMediaSource);
		if (this.useWorker && typeof Worker < "u") {
			let n = this.hls.logger;
			if (i.workerPath || Ts()) {
				try {
					i.workerPath ? (n.log(`loading Web Worker ${i.workerPath} for "${t}"`), this.workerContext = Ds(i.workerPath)) : (n.log(`injecting Web Worker for "${t}"`), this.workerContext = Es());
					let { worker: e } = this.workerContext;
					e.addEventListener("message", this.onWorkerMessage), e.addEventListener("error", this.onWorkerError), e.postMessage({
						instanceNo: this.instanceNo,
						cmd: "init",
						typeSupported: o,
						id: t,
						config: Fi(i)
					});
				} catch (r) {
					n.warn(`Error setting up "${t}" Web Worker, fallback to inline`, r), this.terminateWorker(), this.error = null, this.transmuxer = new vl(this.observer, o, i, "", t, e.logger);
				}
				return;
			}
		}
		this.transmuxer = new vl(this.observer, o, i, "", t, e.logger);
	}
	reset() {
		if (this.frag = null, this.part = null, this.workerContext) {
			let e = this.instanceNo;
			this.instanceNo = wl++;
			let t = this.hls.config, n = ui(t.preferManagedMediaSource);
			this.workerContext.worker.postMessage({
				instanceNo: this.instanceNo,
				cmd: "reset",
				resetNo: e,
				typeSupported: n,
				id: this.id,
				config: Fi(t)
			});
		}
	}
	terminateWorker() {
		if (this.workerContext) {
			let { worker: e } = this.workerContext;
			this.workerContext = null, e.removeEventListener("message", this.onWorkerMessage), e.removeEventListener("error", this.onWorkerError), Os(this.hls.config.workerPath);
		}
	}
	destroy() {
		if (this.workerContext) this.terminateWorker(), this.onWorkerMessage = this.onWorkerError = null;
		else {
			let e = this.transmuxer;
			e && (e.destroy(), this.transmuxer = null);
		}
		let e = this.observer;
		e && e.removeAllListeners(), this.frag = null, this.part = null, this.observer = null, this.hls = null;
	}
	push(e, t, n, r, i, a, o, s, c, l) {
		c.transmuxing.start = self.performance.now();
		let { instanceNo: u, transmuxer: d } = this, f = a ? a.start : i.start, p = i.decryptdata, m = this.frag, h = !(m && i.cc === m.cc), g = !(m && c.level === m.level), _ = m ? c.sn - m.sn : -1, v = this.part ? c.part - this.part.index : -1, y = _ === 0 && c.id > 1 && c.id === m?.stats.chunkCount, b = !g && (_ === 1 || _ === 0 && (v === 1 || y && v <= 0)), x = self.performance.now();
		(g || _ || i.stats.parsing.start === 0) && (i.stats.parsing.start = x), a && (v || !b) && (a.stats.parsing.start = x);
		let S = !(m && i.initSegment?.url === m.initSegment?.url), C = new Cl(h, b, s, g, f, S);
		if (!b || h || S) {
			this.hls.logger.log(`[transmuxer-interface]: Starting new transmux session for ${i.type} sn: ${c.sn}${c.part > -1 ? " part: " + c.part : ""} ${this.id === Y.MAIN ? "level" : "track"}: ${c.level} id: ${c.id}
        discontinuity: ${h}
        trackSwitch: ${g}
        contiguous: ${b}
        accurateTimeOffset: ${s}
        timeOffset: ${f}
        initSegmentChange: ${S}`);
			let e = new Sl(n, r, t, o, l);
			this.configureTransmuxer(e);
		}
		if (this.frag = i, this.part = a, this.workerContext) this.workerContext.worker.postMessage({
			instanceNo: u,
			cmd: "demux",
			data: e,
			decryptdata: p,
			chunkMeta: c,
			state: C
		}, e instanceof ArrayBuffer ? [e] : []);
		else if (d) {
			let t = d.push(e, p, c, C);
			xl(t) ? t.then((e) => {
				this.handleTransmuxComplete(e);
			}).catch((e) => {
				this.transmuxerError(e, c, "transmuxer-interface push error");
			}) : this.handleTransmuxComplete(t);
		}
	}
	flush(e) {
		e.transmuxing.start = self.performance.now();
		let { instanceNo: t, transmuxer: n } = this;
		if (this.workerContext) this.workerContext.worker.postMessage({
			instanceNo: t,
			cmd: "flush",
			chunkMeta: e
		});
		else if (n) {
			let t = n.flush(e);
			xl(t) ? t.then((t) => {
				this.handleFlushResult(t, e);
			}).catch((t) => {
				this.transmuxerError(t, e, "transmuxer-interface flush error");
			}) : this.handleFlushResult(t, e);
		}
	}
	transmuxerError(e, t, n) {
		this.hls && (this.error = e, this.hls.trigger(q.ERROR, {
			type: G.MEDIA_ERROR,
			details: K.FRAG_PARSING_ERROR,
			chunkMeta: t,
			frag: this.frag || void 0,
			part: this.part || void 0,
			fatal: !1,
			error: e,
			err: e,
			reason: n
		}));
	}
	handleFlushResult(e, t) {
		e.forEach((e) => {
			this.handleTransmuxComplete(e);
		}), this.onFlush(t);
	}
	configureTransmuxer(e) {
		let { instanceNo: t, transmuxer: n } = this;
		this.workerContext ? this.workerContext.worker.postMessage({
			instanceNo: t,
			cmd: "configure",
			config: e
		}) : n && n.configure(e);
	}
	handleTransmuxComplete(e) {
		e.chunkMeta.transmuxing.end = self.performance.now(), this.onTransmuxComplete(e);
	}
}, El = 100, Dl = class extends hs {
	constructor(e, t, n) {
		super(e, t, n, "audio-stream-controller", Y.AUDIO), this.mainAnchor = null, this.mainFragLoading = null, this.audioOnly = !1, this.bufferedTrack = null, this.switchingTrack = null, this.trackId = -1, this.waitingData = null, this.mainDetails = null, this.flushing = !1, this.bufferFlushed = !1, this.cachedTrackLoadedData = null, this.registerListeners();
	}
	onHandlerDestroying() {
		this.unregisterListeners(), super.onHandlerDestroying(), this.resetItem();
	}
	resetItem() {
		this.mainDetails = this.mainAnchor = this.mainFragLoading = this.bufferedTrack = this.switchingTrack = this.waitingData = this.cachedTrackLoadedData = null;
	}
	registerListeners() {
		super.registerListeners();
		let { hls: e } = this;
		e.on(q.LEVEL_LOADED, this.onLevelLoaded, this), e.on(q.AUDIO_TRACKS_UPDATED, this.onAudioTracksUpdated, this), e.on(q.AUDIO_TRACK_SWITCHING, this.onAudioTrackSwitching, this), e.on(q.AUDIO_TRACK_LOADED, this.onAudioTrackLoaded, this), e.on(q.BUFFER_RESET, this.onBufferReset, this), e.on(q.BUFFER_CREATED, this.onBufferCreated, this), e.on(q.BUFFER_FLUSHING, this.onBufferFlushing, this), e.on(q.BUFFER_FLUSHED, this.onBufferFlushed, this), e.on(q.INIT_PTS_FOUND, this.onInitPtsFound, this), e.on(q.FRAG_LOADING, this.onFragLoading, this), e.on(q.FRAG_BUFFERED, this.onFragBuffered, this);
	}
	unregisterListeners() {
		let { hls: e } = this;
		e && (super.unregisterListeners(), e.off(q.LEVEL_LOADED, this.onLevelLoaded, this), e.off(q.AUDIO_TRACKS_UPDATED, this.onAudioTracksUpdated, this), e.off(q.AUDIO_TRACK_SWITCHING, this.onAudioTrackSwitching, this), e.off(q.AUDIO_TRACK_LOADED, this.onAudioTrackLoaded, this), e.off(q.BUFFER_RESET, this.onBufferReset, this), e.off(q.BUFFER_CREATED, this.onBufferCreated, this), e.off(q.BUFFER_FLUSHING, this.onBufferFlushing, this), e.off(q.BUFFER_FLUSHED, this.onBufferFlushed, this), e.off(q.INIT_PTS_FOUND, this.onInitPtsFound, this), e.off(q.FRAG_LOADING, this.onFragLoading, this), e.off(q.FRAG_BUFFERED, this.onFragBuffered, this));
	}
	onInitPtsFound(e, { frag: t, id: n, initPTS: r, timescale: i, trackId: a }) {
		if (n === Y.MAIN) {
			let e = t.cc, n = this.fragCurrent;
			if (this.initPTS[e] = {
				baseTime: r,
				timescale: i,
				trackId: a
			}, this.log(`InitPTS for cc: ${e} found from main: ${r / i} (${r}/${i}) trackId: ${a}`), this.mainAnchor = t, this.state === $.WAITING_INIT_PTS) {
				let n = this.waitingData;
				(!n && !this.loadingParts || n && n.frag.cc !== e) && this.syncWithAnchor(t, n?.frag);
			} else !this.hls.hasEnoughToStart && n && n.cc !== e ? (n.abortRequests(), this.syncWithAnchor(t, n)) : this.state === $.IDLE && this.tick();
		}
	}
	getLoadPosition() {
		return !this.startFragRequested && this.nextLoadPosition >= 0 ? this.nextLoadPosition : super.getLoadPosition();
	}
	syncWithAnchor(e, t) {
		let n = this.mainFragLoading?.frag || null;
		if (t && n?.cc === t.cc) return;
		let r = (n || e).cc, i = na(this.getLevelDetails(), r, this.getLoadPosition());
		i && (this.log(`Syncing with main frag at ${i.start} cc ${i.cc}`), this.startFragRequested = !1, this.nextLoadPosition = i.start, this.resetLoadingState(), this.state === $.IDLE && this.doTickIdle());
	}
	startLoad(e, t) {
		if (!this.levels) {
			this.startPosition = e, this.state = $.STOPPED;
			return;
		}
		let n = this.lastCurrentTime;
		this.stopLoad(), this.setInterval(El), n > 0 && e === -1 ? (this.log(`Override startPosition with lastCurrentTime @${n.toFixed(3)}`), e = n, this.state = $.IDLE) : this.state = $.WAITING_TRACK, this.nextLoadPosition = this.lastCurrentTime = e + this.timelineOffset, this.startPosition = t ? -1 : e, this.tick();
	}
	doTick() {
		switch (this.state) {
			case $.IDLE:
				this.doTickIdle();
				break;
			case $.WAITING_TRACK: {
				let { levels: e, trackId: t } = this, n = e?.[t], r = n?.details;
				if (r && !this.waitForLive(n)) {
					if (this.waitForCdnTuneIn(r)) break;
					this.state = $.WAITING_INIT_PTS;
				}
				break;
			}
			case $.FRAG_LOADING_WAITING_RETRY:
				this.checkRetryDate();
				break;
			case $.WAITING_INIT_PTS: {
				let e = this.waitingData;
				if (e) {
					let { frag: t, part: n, cache: r, complete: i } = e, a = this.mainAnchor;
					if (this.initPTS[t.cc] !== void 0) {
						this.waitingData = null, this.state = $.FRAG_LOADING;
						let e = {
							frag: t,
							part: n,
							payload: r.flush().buffer,
							networkDetails: null
						};
						this._handleFragmentLoadProgress(e), i && super._handleFragmentLoadComplete(e);
					} else a && a.cc !== e.frag.cc && this.syncWithAnchor(a, e.frag);
				} else this.state = $.IDLE;
			}
		}
		this.onTickEnd();
	}
	resetLoadingState() {
		let e = this.waitingData;
		e && (this.fragmentTracker.removeFragment(e.frag), this.waitingData = null), super.resetLoadingState();
	}
	onTickEnd() {
		let { media: e } = this;
		e != null && e.readyState && (this.lastCurrentTime = e.currentTime);
	}
	doTickIdle() {
		let { hls: e, levels: t, media: n, trackId: r } = this, i = e.config;
		if (!this.buffering || !n && !this.primaryPrefetch && (this.startFragRequested || !i.startFragPrefetch) || !(t != null && t[r])) return;
		let a = t[r], o = a.details;
		if (!o || this.waitForLive(a) || this.waitForCdnTuneIn(o)) {
			this.state = $.WAITING_TRACK, this.startFragRequested = !1;
			return;
		}
		let s = this.mediaBuffer ? this.mediaBuffer : this.media;
		this.bufferFlushed && s && (this.bufferFlushed = !1, this.afterBufferFlushed(s, sr.AUDIO, Y.AUDIO));
		let c = this.getFwdBufferInfo(s, Y.AUDIO);
		if (c === null) return;
		if (!this.switchingTrack && this._streamEnded(c, o)) {
			e.trigger(q.BUFFER_EOS, { type: "audio" }), this.state = $.ENDED;
			return;
		}
		let l = c.len, u = e.maxBufferLength, d = o.fragments, f = d[0].start, p = this.getLoadPosition(), m = this.flushing ? p : c.end;
		if (this.switchingTrack && n) {
			let e = p;
			o.PTSKnown && e < f && (c.end > f || c.nextStart) && (this.log("Alt audio track ahead of main track, seek to start of alt audio track"), n.currentTime = f + .05);
		}
		if (l >= u && !this.switchingTrack && m < d[d.length - 1].start) return;
		let h = this.getNextFragment(m, o);
		if (h && this.isLoopLoading(h, m) && (h = this.getNextFragmentLoopLoading(h, o, c, Y.MAIN, u)), !h) {
			this.bufferFlushed = !0;
			return;
		}
		let g = this.mainFragLoading?.frag || null;
		if (!this.audioOnly && this.startFragRequested && g && lr(h) && !h.endList && (!o.live || !this.loadingParts && m < this.hls.liveSyncPosition) && (this.fragmentTracker.getState(g) === ga.OK && (this.mainFragLoading = g = null), g && lr(g))) {
			if (h.start > g.end) {
				let e = this.fragmentTracker.getFragAtPos(m, Y.MAIN);
				e && e.end > g.end && (g = e, this.mainFragLoading = {
					frag: e,
					targetBufferTime: null
				});
			}
			if (h.start > g.end) return;
		}
		this.loadFragment(h, a, m);
	}
	onMediaDetaching(e, t) {
		this.bufferFlushed = this.flushing = !1, super.onMediaDetaching(e, t);
	}
	onAudioTracksUpdated(e, { audioTracks: t }) {
		this.resetTransmuxer(), this.levels = t.map((e) => new Ai(e));
	}
	onAudioTrackSwitching(e, t) {
		let n = !!t.url;
		this.trackId = t.id;
		let { fragCurrent: r } = this;
		r && (r.abortRequests(), this.removeUnbufferedFrags(r.start)), this.resetLoadingState(), n ? (this.switchingTrack = t, this.flushAudioIfNeeded(t), this.state !== $.STOPPED && (this.setInterval(El), this.state = $.IDLE, this.tick())) : (this.resetTransmuxer(), this.switchingTrack = null, this.bufferedTrack = t, this.clearInterval());
	}
	onManifestLoading() {
		super.onManifestLoading(), this.bufferFlushed = this.flushing = this.audioOnly = !1, this.resetItem(), this.trackId = -1;
	}
	onLevelLoaded(e, t) {
		this.mainDetails = t.details;
		let n = this.cachedTrackLoadedData;
		n && (this.cachedTrackLoadedData = null, this.onAudioTrackLoaded(q.AUDIO_TRACK_LOADED, n));
	}
	onAudioTrackLoaded(e, t) {
		var n;
		let { levels: r } = this, { details: i, id: a, groupId: o, track: s } = t;
		if (!r) {
			this.warn(`Audio tracks reset while loading track ${a} "${s.name}" of "${o}"`);
			return;
		}
		let c = this.mainDetails;
		if (!c || i.endCC > c.endCC || c.expired) {
			this.cachedTrackLoadedData = t, this.state !== $.STOPPED && (this.state = $.WAITING_TRACK);
			return;
		}
		this.cachedTrackLoadedData = null, this.log(`Audio track ${a} "${s.name}" of "${o}" loaded [${i.startSN},${i.endSN}]${i.lastPartSn ? `[part-${i.lastPartSn}-${i.lastPartIndex}]` : ""},duration:${i.totalduration}`);
		let l = r[a], u = 0;
		if (i.live || (n = l.details) != null && n.live) {
			if (this.checkLiveUpdate(i), i.deltaUpdateFailed) return;
			l.details && (u = this.alignPlaylists(i, l.details, this.levelLastLoaded?.details)), i.alignedSliding || (us(i, c), i.alignedSliding || ds(i, c), u = i.fragmentStart);
		}
		l.details = i, this.levelLastLoaded = l, this.startFragRequested || this.setStartPosition(c, u), this.hls.trigger(q.AUDIO_TRACK_UPDATED, {
			details: i,
			id: a,
			groupId: t.groupId
		}), this.state === $.WAITING_TRACK && !this.waitForCdnTuneIn(i) && (this.state = $.IDLE), this.tick();
	}
	_handleFragmentLoadProgress(e) {
		let t = e.frag, { part: n, payload: r } = e, { config: i, trackId: a, levels: o } = this;
		if (!o) {
			this.warn(`Audio tracks were reset while fragment load was in progress. Fragment ${t.sn} of level ${t.level} will not be buffered`);
			return;
		}
		let s = o[a];
		if (!s) {
			this.warn("Audio track is undefined on fragment load progress");
			return;
		}
		let c = s.details;
		if (!c) {
			this.warn("Audio track details undefined on fragment load progress"), this.removeUnbufferedFrags(t.start);
			return;
		}
		let l = i.defaultAudioCodec || s.audioCodec || "mp4a.40.2", u = this.transmuxer;
		u ||= this.transmuxer = new Tl(this.hls, Y.AUDIO, this._handleTransmuxComplete.bind(this), this._handleTransmuxerFlush.bind(this));
		let d = this.initPTS[t.cc], f = t.initSegment?.data;
		if (d !== void 0) {
			let e = n ? n.index : -1, i = e !== -1, a = new Ia(t.level, t.sn, t.stats.chunkCount, r.byteLength, e, i);
			u.push(r, f, l, "", t, n, c.totalduration, !1, a, d);
		} else {
			this.log(`Unknown video PTS for cc ${t.cc}, waiting for video PTS before demuxing audio frag ${t.sn} of [${c.startSN} ,${c.endSN}],track ${a}`);
			let { cache: e } = this.waitingData = this.waitingData || {
				frag: t,
				part: n,
				cache: new _s(),
				complete: !1
			};
			e.push(new Uint8Array(r)), this.state !== $.STOPPED && (this.state = $.WAITING_INIT_PTS);
		}
	}
	_handleFragmentLoadComplete(e) {
		this.waitingData ? this.waitingData.complete = !0 : super._handleFragmentLoadComplete(e);
	}
	onBufferReset() {
		this.mediaBuffer = null;
	}
	onBufferCreated(e, t) {
		this.bufferFlushed = this.flushing = !1;
		let n = t.tracks.audio;
		n && (this.mediaBuffer = n.buffer || null);
	}
	onFragLoading(e, t) {
		!this.audioOnly && t.frag.type === Y.MAIN && lr(t.frag) && (this.mainFragLoading = t, this.state === $.IDLE && this.tick());
	}
	onFragBuffered(e, t) {
		let { frag: n, part: r } = t;
		if (n.type !== Y.AUDIO) this.audioOnly || n.type !== Y.MAIN || n.elementaryStreams.video || n.elementaryStreams.audiovideo || (this.audioOnly = !0, this.mainFragLoading = null);
		else if (this.fragContextChanged(n)) this.warn(`Fragment ${n.sn}${r ? " p: " + r.index : ""} of level ${n.level} finished buffering, but was aborted. state: ${this.state}, audioSwitch: ${this.switchingTrack ? this.switchingTrack.name : "false"}`);
		else {
			if (lr(n)) {
				this.fragPrevious = n;
				let e = this.switchingTrack;
				e && (this.bufferedTrack = e, this.switchingTrack = null, this.hls.trigger(q.AUDIO_TRACK_SWITCHED, Ln({}, e)));
			}
			this.fragBufferedComplete(n, r), this.media && this.tick();
		}
	}
	onError(e, t) {
		if (t.fatal) this.state = $.ERROR;
		else switch (t.details) {
			case K.FRAG_GAP:
			case K.FRAG_PARSING_ERROR:
			case K.FRAG_DECRYPT_ERROR:
			case K.FRAG_LOAD_ERROR:
			case K.FRAG_LOAD_TIMEOUT:
			case K.KEY_LOAD_ERROR:
			case K.KEY_LOAD_TIMEOUT:
				this.onFragmentOrKeyLoadError(Y.AUDIO, t);
				break;
			case K.AUDIO_TRACK_LOAD_ERROR:
			case K.AUDIO_TRACK_LOAD_TIMEOUT:
			case K.LEVEL_PARSING_ERROR:
				!t.levelRetry && this.state === $.WAITING_TRACK && t.context?.type === J.AUDIO_TRACK && (this.state = $.IDLE);
				break;
			case K.BUFFER_ADD_CODEC_ERROR:
			case K.BUFFER_APPEND_ERROR:
				if (t.parent !== "audio") return;
				this.reduceLengthAndFlushBuffer(t) || this.resetLoadingState();
				break;
			case K.BUFFER_FULL_ERROR:
				if (t.parent !== "audio") return;
				this.reduceLengthAndFlushBuffer(t) && (this.bufferedTrack = null, super.flushMainBuffer(0, Infinity, "audio"));
				break;
			case K.INTERNAL_EXCEPTION: this.recoverWorkerError(t);
		}
	}
	onBufferFlushing(e, { type: t }) {
		t !== sr.VIDEO && (this.flushing = !0);
	}
	onBufferFlushed(e, { type: t }) {
		if (t !== sr.VIDEO) {
			this.flushing = !1, this.bufferFlushed = !0, this.state === $.ENDED && (this.state = $.IDLE);
			let e = this.mediaBuffer || this.media;
			e && (this.afterBufferFlushed(e, t, Y.AUDIO), this.tick());
		}
	}
	_handleTransmuxComplete(e) {
		var t;
		let n = "audio", { hls: r } = this, { remuxResult: i, chunkMeta: a } = e, o = this.getCurrentContext(a);
		if (!o) {
			this.resetWhenMissingContext(a);
			return;
		}
		let { frag: s, part: c, level: l } = o, { details: u } = l, { audio: d, text: f, id3: p, initSegment: m } = i;
		if (this.fragContextChanged(s) || !u) this.fragmentTracker.removeFragment(s);
		else {
			if (this.state = $.PARSING, this.switchingTrack && d && this.completeAudioSwitch(this.switchingTrack), m != null && m.tracks) {
				let e = s.initSegment || s;
				if (this.unhandledEncryptionError(m, s)) return;
				this._bufferInitSegment(l, m.tracks, e, a), r.trigger(q.FRAG_PARSING_INIT_SEGMENT, {
					frag: e,
					id: n,
					tracks: m.tracks
				});
			}
			if (d) {
				let { startPTS: e, endPTS: t, startDTS: n, endDTS: r } = d;
				c && (c.elementaryStreams[sr.AUDIO] = {
					startPTS: e,
					endPTS: t,
					startDTS: n,
					endDTS: r
				}), s.setElementaryStreamInfo(sr.AUDIO, e, t, n, r), this.bufferFragmentData(d, s, c, a);
			}
			if (p != null && (t = p.samples) != null && t.length) {
				let e = Fn({
					id: n,
					frag: s,
					details: u
				}, p);
				r.trigger(q.FRAG_PARSING_METADATA, e);
			}
			if (f) {
				let e = Fn({
					id: n,
					frag: s,
					details: u
				}, f);
				r.trigger(q.FRAG_PARSING_USERDATA, e);
			}
		}
	}
	_bufferInitSegment(e, t, n, r) {
		if (this.state !== $.PARSING || (t.video && delete t.video, t.audiovideo && delete t.audiovideo, !t.audio)) return;
		let i = t.audio;
		i.id = Y.AUDIO;
		let a = e.audioCodec;
		this.log(`Init audio buffer, container:${i.container}, codecs[level/parsed]=[${a}/${i.codec}]`), a && a.split(",").length === 1 && (i.levelCodec = a), this.hls.trigger(q.BUFFER_CODECS, t);
		let o = i.initSegment;
		if (o != null && o.byteLength) {
			let e = {
				type: "audio",
				frag: n,
				part: null,
				chunkMeta: r,
				parent: n.type,
				data: o
			};
			this.hls.trigger(q.BUFFER_APPENDING, e);
		}
		this.tickImmediate();
	}
	loadFragment(e, t, n) {
		let r = this.fragmentTracker.getState(e);
		if (this.switchingTrack || r === ga.NOT_LOADED || r === ga.PARTIAL) {
			var i;
			if (!lr(e)) this._loadInitSegment(e, t);
			else if ((i = t.details) != null && i.live && !this.initPTS[e.cc]) {
				this.log(`Waiting for video PTS in continuity counter ${e.cc} of live stream before loading audio fragment ${e.sn} of level ${this.trackId}`), this.state = $.WAITING_INIT_PTS;
				let n = this.mainDetails;
				n && n.fragmentStart !== t.details.fragmentStart && ds(t.details, n);
			} else super.loadFragment(e, t, n);
		} else this.clearTrackerIfNeeded(e);
	}
	flushAudioIfNeeded(e) {
		if (this.media && this.bufferedTrack) {
			let { name: t, lang: n, assocLang: r, characteristics: i, audioCodec: a, channels: o } = this.bufferedTrack;
			Hi({
				name: t,
				lang: n,
				assocLang: r,
				characteristics: i,
				audioCodec: a,
				channels: o
			}, e, Gi) || (Ji(e.url, this.hls) ? (this.log("Switching audio track : flushing all audio"), super.flushMainBuffer(0, Infinity, "audio"), this.bufferedTrack = null) : this.bufferedTrack = e);
		}
	}
	completeAudioSwitch(e) {
		let { hls: t } = this;
		this.flushAudioIfNeeded(e), this.bufferedTrack = e, this.switchingTrack = null, t.trigger(q.AUDIO_TRACK_SWITCHED, Ln({}, e));
	}
}, Ol = class extends Bn {
	constructor(e, t) {
		super(t, e.logger), this.hls = void 0, this.canLoad = !1, this.timer = -1, this.hls = e;
	}
	destroy() {
		this.clearTimer(), this.hls = this.log = this.warn = null;
	}
	clearTimer() {
		this.timer !== -1 && (self.clearTimeout(this.timer), this.timer = -1);
	}
	startLoad() {
		this.canLoad = !0, this.loadPlaylist();
	}
	stopLoad() {
		this.canLoad = !1, this.clearTimer();
	}
	switchParams(e, t, n) {
		let r = t?.renditionReports;
		if (r) {
			let i = -1;
			for (let n = 0; n < r.length; n++) {
				let a = r[n], o;
				try {
					o = new self.URL(a.URI, t.url).href;
				} catch (e) {
					this.warn(`Could not construct new URL for Rendition Report: ${e}`), o = a.URI || "";
				}
				if (o === e) {
					i = n;
					break;
				}
				o === e.substring(0, o.length) && (i = n);
			}
			if (i !== -1) {
				let e = r[i], a = parseInt(e["LAST-MSN"]) || t.lastPartSn, o = parseInt(e["LAST-PART"]) || t.lastPartIndex;
				if (this.hls.config.lowLatencyMode) {
					let e = Math.min(t.age - t.partTarget, t.targetduration);
					o >= 0 && e > t.partTarget && (o += 1);
				}
				let s = n && Oi(n);
				return new ki(a, o >= 0 ? o : void 0, s);
			}
		}
	}
	loadPlaylist(e) {
		this.clearTimer();
	}
	loadingPlaylist(e, t) {
		this.clearTimer();
	}
	shouldLoadPlaylist(e) {
		return this.canLoad && !!e && !!e.url && (!e.details || e.details.live);
	}
	getUrlWithDirectives(e, t) {
		if (t) try {
			return t.addDirectives(e);
		} catch (e) {
			this.warn(`Could not construct new URL with HLS Delivery Directives: ${e}`);
		}
		return e;
	}
	playlistLoaded(e, t, n) {
		let { details: r, stats: i } = t, a = self.performance.now(), o = i.loading.first ? Math.max(0, a - i.loading.first) : 0;
		r.advancedDateTime = Date.now() - o;
		let s = this.hls.config.timelineOffset;
		if (s !== r.appliedTimelineOffset) {
			let e = Math.max(s || 0, 0);
			r.appliedTimelineOffset = e, r.fragments.forEach((t) => {
				t.setStart(t.playlistOffset + e);
			});
		}
		if (r.live || n != null && n.live) {
			let s = "levelInfo" in t ? t.levelInfo : t.track;
			if (r.reloaded(n), n && r.fragments.length > 0) {
				Go(n, r, this);
				let e = r.playlistParsingError;
				if (e) {
					this.warn(e);
					let n = this.hls;
					if (!n.config.ignorePlaylistParsingErrors) {
						let { networkDetails: a } = t;
						n.trigger(q.ERROR, {
							type: G.NETWORK_ERROR,
							details: K.LEVEL_PARSING_ERROR,
							fatal: !1,
							url: r.url,
							error: e,
							reason: e.message,
							level: t.level || void 0,
							parent: r.fragments[0]?.type,
							networkDetails: a,
							stats: i
						});
						return;
					}
					r.playlistParsingError = null;
				}
			}
			r.requestScheduled === -1 && (r.requestScheduled = i.loading.start);
			let c = this.hls.mainForwardBufferInfo, l = c ? c.end - c.len : 0, u = Qo(r, (r.edge - l) * 1e3);
			if (r.requestScheduled + u < a ? r.requestScheduled = a : r.requestScheduled += u, this.log(`live playlist ${e} ${r.advanced ? "REFRESHED " + r.lastPartSn + "-" + r.lastPartIndex : r.updated ? "UPDATED" : "MISSED"}`), !this.canLoad || !r.live) return;
			let d, f, p;
			if (r.canBlockReload && r.endSN && r.advanced) {
				let e = this.hls.config.lowLatencyMode, i = r.lastPartSn, o = r.endSN, c = r.lastPartIndex, l = c !== -1, u = i === o;
				l ? u ? (f = o + 1, p = e ? 0 : c) : (f = i, p = e ? c + 1 : r.maxPartIndex) : f = o + 1;
				let m = r.age, h = m + r.ageHeader, g = Math.min(h - r.partTarget, r.targetduration * 1.5);
				if (g > 0) {
					if (h > r.targetduration * 3) this.log(`Playlist last advanced ${m.toFixed(2)}s ago. Omitting segment and part directives.`), f = void 0, p = void 0;
					else if (n != null && n.tuneInGoal && h - r.partTarget > n.tuneInGoal) this.warn(`CDN Tune-in goal increased from: ${n.tuneInGoal} to: ${g} with playlist age: ${r.age}`), g = 0;
					else {
						let e = Math.floor(g / r.targetduration);
						if (f += e, p !== void 0) {
							let e = Math.round(g % r.targetduration / r.partTarget);
							p += e;
						}
						this.log(`CDN Tune-in age: ${r.ageHeader}s last advanced ${m.toFixed(2)}s goal: ${g} skip sn ${e} to part ${p}`);
					}
					r.tuneInGoal = g;
				}
				if (d = this.getDeliveryDirectives(r, t.deliveryDirectives, f, p), e || !u) {
					r.requestScheduled = a, this.loadingPlaylist(s, d);
					return;
				}
			} else (r.canBlockReload || r.canSkipUntil) && (d = this.getDeliveryDirectives(r, t.deliveryDirectives, f, p));
			d && f !== void 0 && r.canBlockReload && (r.requestScheduled = i.loading.first + Math.max(u - o * 2, u / 2)), this.scheduleLoading(s, d, r);
		} else this.clearTimer();
	}
	scheduleLoading(e, t, n) {
		let r = n || e.details;
		if (!r) {
			this.loadingPlaylist(e, t);
			return;
		}
		let i = self.performance.now(), a = r.requestScheduled;
		if (i >= a) {
			this.loadingPlaylist(e, t);
			return;
		}
		let o = a - i;
		this.log(`reload live playlist ${e.name || e.bitrate + "bps"} in ${Math.round(o)} ms`), this.clearTimer(), this.timer = self.setTimeout(() => this.loadingPlaylist(e, t), o);
	}
	getDeliveryDirectives(e, t, n, r) {
		let i = Oi(e);
		return t != null && t.skip && e.deltaUpdateFailed && (n = t.msn, r = t.part, i = Di.No), new ki(n, r, i);
	}
	checkRetry(e) {
		let t = e.details, n = ra(e), r = e.errorAction, { action: i, retryCount: a = 0, retryConfig: o } = r || {}, s = !!r && !!o && (i === fa.RetryRequest || !r.resolved && i === fa.SendAlternateToPenaltyBox);
		if (s) {
			var c;
			if (a >= o.maxNumRetry) return !1;
			if (n && (c = e.context) != null && c.deliveryDirectives) this.warn(`Retrying playlist loading ${a + 1}/${o.maxNumRetry} after "${t}" without delivery-directives`), this.loadPlaylist();
			else {
				let e = sa(o, a);
				this.clearTimer(), this.timer = self.setTimeout(() => this.loadPlaylist(), e), this.warn(`Retrying playlist loading ${a + 1}/${o.maxNumRetry} after "${t}" in ${e}ms`);
			}
			e.levelRetry = !0, r.resolved = !0;
		}
		return s;
	}
};
function kl(e, t) {
	if (e.length !== t.length) return !1;
	for (let n = 0; n < e.length; n++) if (!Al(e[n].attrs, t[n].attrs)) return !1;
	return !0;
}
function Al(e, t, n) {
	let r = e["STABLE-RENDITION-ID"];
	return r && !n ? r === t["STABLE-RENDITION-ID"] : !(n || [
		"LANGUAGE",
		"NAME",
		"CHARACTERISTICS",
		"AUTOSELECT",
		"DEFAULT",
		"FORCED",
		"ASSOC-LANGUAGE"
	]).some((n) => e[n] !== t[n]);
}
function jl(e, t) {
	return t.label.toLowerCase() === e.name.toLowerCase() && (!t.language || t.language.toLowerCase() === (e.lang || "").toLowerCase());
}
var Ml = class extends Ol {
	constructor(e) {
		super(e, "audio-track-controller"), this.tracks = [], this.groupIds = null, this.tracksInGroup = [], this.trackId = -1, this.currentTrack = null, this.selectDefaultTrack = !0, this.registerListeners();
	}
	registerListeners() {
		let { hls: e } = this;
		e.on(q.MANIFEST_LOADING, this.onManifestLoading, this), e.on(q.MANIFEST_PARSED, this.onManifestParsed, this), e.on(q.LEVEL_LOADING, this.onLevelLoading, this), e.on(q.LEVEL_SWITCHING, this.onLevelSwitching, this), e.on(q.AUDIO_TRACK_LOADED, this.onAudioTrackLoaded, this), e.on(q.ERROR, this.onError, this);
	}
	unregisterListeners() {
		let { hls: e } = this;
		e.off(q.MANIFEST_LOADING, this.onManifestLoading, this), e.off(q.MANIFEST_PARSED, this.onManifestParsed, this), e.off(q.LEVEL_LOADING, this.onLevelLoading, this), e.off(q.LEVEL_SWITCHING, this.onLevelSwitching, this), e.off(q.AUDIO_TRACK_LOADED, this.onAudioTrackLoaded, this), e.off(q.ERROR, this.onError, this);
	}
	destroy() {
		this.unregisterListeners(), this.tracks.length = 0, this.tracksInGroup.length = 0, this.currentTrack = null, super.destroy();
	}
	onManifestLoading() {
		this.tracks = [], this.tracksInGroup = [], this.groupIds = null, this.currentTrack = null, this.trackId = -1, this.selectDefaultTrack = !0;
	}
	onManifestParsed(e, t) {
		this.tracks = t.audioTracks || [];
	}
	onAudioTrackLoaded(e, t) {
		let { id: n, groupId: r, details: i } = t, a = this.tracksInGroup[n];
		if (!a || a.groupId !== r) {
			this.warn(`Audio track with id:${n} and group:${r} not found in active group ${a?.groupId}`);
			return;
		}
		let o = a.details;
		a.details = t.details, this.log(`Audio track ${n} "${a.name}" lang:${a.lang} group:${r} loaded [${i.startSN}-${i.endSN}]`), n === this.trackId && this.playlistLoaded(n, t, o);
	}
	onLevelLoading(e, t) {
		this.switchLevel(t.level);
	}
	onLevelSwitching(e, t) {
		this.switchLevel(t.level);
	}
	switchLevel(e) {
		let t = this.hls.levels[e];
		if (!t) return;
		let n = t.audioGroups || null, r = this.groupIds, i = this.currentTrack;
		if (!n || r?.length !== n?.length || n != null && n.some((e) => r?.indexOf(e) === -1)) {
			this.groupIds = n, this.trackId = -1, this.currentTrack = null;
			let e = this.tracks.filter((e) => !n || n.indexOf(e.groupId) !== -1);
			if (e.length) this.selectDefaultTrack && !e.some((e) => e.default) && (this.selectDefaultTrack = !1), e.forEach((e, t) => {
				e.id = t;
			});
			else if (!i && !this.tracksInGroup.length) return;
			this.tracksInGroup = e;
			let t = this.hls.config.audioPreference;
			if (!i && t) {
				let n = Vi(t, e, Gi);
				if (n > -1) i = e[n];
				else {
					let e = Vi(t, this.tracks);
					i = this.tracks[e];
				}
			}
			let r = this.findTrackId(i);
			r === -1 && i && (r = this.findTrackId(null));
			let a = { audioTracks: e };
			this.log(`Updating audio tracks, ${e.length} track(s) found in group(s): ${n?.join(",")}`), this.hls.trigger(q.AUDIO_TRACKS_UPDATED, a);
			let o = this.trackId;
			if (r !== -1 && o === -1) this.setAudioTrack(r);
			else if (e.length && o === -1) {
				let t = /* @__PURE__ */ Error(`No audio track selected for current audio group-ID(s): ${this.groupIds?.join(",")} track count: ${e.length}`);
				this.warn(t.message), this.hls.trigger(q.ERROR, {
					type: G.MEDIA_ERROR,
					details: K.AUDIO_TRACK_LOAD_ERROR,
					fatal: !0,
					error: t
				});
			}
		}
	}
	onError(e, t) {
		!t.fatal && t.context && (t.context.type !== J.AUDIO_TRACK || t.context.id !== this.trackId || this.groupIds && this.groupIds.indexOf(t.context.groupId) === -1 || this.checkRetry(t));
	}
	get allAudioTracks() {
		return this.tracks;
	}
	get audioTracks() {
		return this.tracksInGroup;
	}
	get audioTrack() {
		return this.trackId;
	}
	set audioTrack(e) {
		this.selectDefaultTrack = !1, this.setAudioTrack(e);
	}
	setAudioOption(e) {
		let t = this.hls;
		if (t.config.audioPreference = e, e) {
			let n = this.allAudioTracks;
			if (this.selectDefaultTrack = !1, n.length) {
				let r = this.currentTrack;
				if (r && Hi(e, r, Gi)) return r;
				let i = Vi(e, this.tracksInGroup, Gi);
				if (i > -1) {
					let e = this.tracksInGroup[i];
					return this.setAudioTrack(i), e;
				}
				if (r) {
					let r = t.loadLevel;
					r === -1 && (r = t.firstAutoLevel);
					let i = Ki(e, t.levels, n, r, Gi);
					if (i === -1) return null;
					t.nextLoadLevel = i;
				}
				if (e.channels || e.audioCodec) {
					let t = Vi(e, n);
					if (t > -1) return n[t];
				}
			}
		}
		return null;
	}
	setAudioTrack(e) {
		let t = this.tracksInGroup;
		if (e < 0 || e >= t.length) {
			this.warn(`Invalid audio track id: ${e}`);
			return;
		}
		this.selectDefaultTrack = !1;
		let n = this.currentTrack, r = t[e], i = r.details && !r.details.live;
		if (e === this.trackId && r === n && i || (this.log(`Switching to audio-track ${e} "${r.name}" lang:${r.lang} group:${r.groupId} channels:${r.channels}`), this.trackId = e, this.currentTrack = r, this.hls.trigger(q.AUDIO_TRACK_SWITCHING, Ln({}, r)), i)) return;
		let a = this.switchParams(r.url, n?.details, r.details);
		this.loadPlaylist(a);
	}
	findTrackId(e) {
		let t = this.tracksInGroup;
		for (let n = 0; n < t.length; n++) {
			let r = t[n];
			if ((!this.selectDefaultTrack || r.default) && (!e || Hi(e, r, Gi))) return n;
		}
		if (e) {
			let { name: n, lang: r, assocLang: i, characteristics: a, audioCodec: o, channels: s } = e;
			for (let e = 0; e < t.length; e++) {
				let c = t[e];
				if (Hi({
					name: n,
					lang: r,
					assocLang: i,
					characteristics: a,
					audioCodec: o,
					channels: s
				}, c, Gi)) return e;
			}
			for (let n = 0; n < t.length; n++) {
				let r = t[n];
				if (Al(e.attrs, r.attrs, [
					"LANGUAGE",
					"ASSOC-LANGUAGE",
					"CHARACTERISTICS"
				])) return n;
			}
			for (let n = 0; n < t.length; n++) {
				let r = t[n];
				if (Al(e.attrs, r.attrs, ["LANGUAGE"])) return n;
			}
		}
		return -1;
	}
	loadPlaylist(e) {
		super.loadPlaylist();
		let t = this.currentTrack;
		this.shouldLoadPlaylist(t) && Ji(t.url, this.hls) && this.scheduleLoading(t, e);
	}
	loadingPlaylist(e, t) {
		super.loadingPlaylist(e, t);
		let n = e.id, r = e.groupId, i = this.getUrlWithDirectives(e.url, t), a = e.details, o = a?.age;
		this.log(`Loading audio-track ${n} "${e.name}" lang:${e.lang} group:${r}${t?.msn === void 0 ? "" : " at sn " + t.msn + " part " + t.part}${o && a.live ? " age " + o.toFixed(1) + (a.type && " " + a.type || "") : ""} ${i}`), this.hls.trigger(q.AUDIO_TRACK_LOADING, {
			url: i,
			id: n,
			groupId: r,
			deliveryDirectives: t || null,
			track: e
		});
	}
}, Nl = class {
	constructor(e) {
		this.tracks = void 0, this.queues = {
			video: [],
			audio: [],
			audiovideo: []
		}, this.tracks = e;
	}
	destroy() {
		this.tracks = this.queues = null;
	}
	append(e, t, n) {
		if (this.queues === null || this.tracks === null) return;
		let r = this.queues[t];
		r.push(e), r.length === 1 && !n && this.executeNext(t);
	}
	appendBlocker(e) {
		return new Promise((t) => {
			let n = {
				label: "async-blocker",
				execute: t,
				onStart: () => {},
				onComplete: () => {},
				onError: () => {}
			};
			this.append(n, e);
		});
	}
	prependBlocker(e) {
		return new Promise((t) => {
			if (this.queues) {
				let n = {
					label: "async-blocker-prepend",
					execute: t,
					onStart: () => {},
					onComplete: () => {},
					onError: () => {}
				};
				this.queues[e].unshift(n);
			}
		});
	}
	removeBlockers() {
		this.queues !== null && [
			this.queues.video,
			this.queues.audio,
			this.queues.audiovideo
		].forEach((e) => {
			let t = e[0]?.label;
			(t === "async-blocker" || t === "async-blocker-prepend") && (e[0].execute(), e.splice(0, 1));
		});
	}
	unblockAudio(e) {
		this.queues !== null && this.queues.audio[0] === e && this.shiftAndExecuteNext("audio");
	}
	executeNext(e) {
		if (this.queues === null || this.tracks === null) return;
		let t = this.queues[e];
		if (t.length) {
			let n = t[0];
			try {
				n.execute();
			} catch (t) {
				if (n.onError(t), this.queues === null || this.tracks === null) return;
				let r = this.tracks[e]?.buffer;
				r != null && r.updating || this.shiftAndExecuteNext(e);
			}
		}
	}
	shiftAndExecuteNext(e) {
		this.queues !== null && (this.queues[e].shift(), this.executeNext(e));
	}
	current(e) {
		return this.queues?.[e][0] || null;
	}
	toString() {
		let { queues: e, tracks: t } = this;
		return e === null || t === null ? "<destroyed>" : `
${this.list("video")}
${this.list("audio")}
${this.list("audiovideo")}}`;
	}
	list(e) {
		var t, n;
		return (t = this.queues) != null && t[e] || (n = this.tracks) != null && n[e] ? `${e}: (${this.listSbInfo(e)}) ${this.listOps(e)}` : "";
	}
	listSbInfo(e) {
		let t = this.tracks?.[e], n = t?.buffer;
		return n ? `SourceBuffer${n.updating ? " updating" : ""}${t.ended ? " ended" : ""}${t.ending ? " ending" : ""}` : "none";
	}
	listOps(e) {
		return this.queues?.[e].map((e) => e.label).join(", ") || "";
	}
}, Pl = /(avc[1234]|hvc1|hev1|dvh[1e]|vp09|av01)(?:\.[^.,]+)+/, Fl = "HlsJsTrackRemovedError", Il = class extends Error {
	constructor(e) {
		super(e), this.name = Fl;
	}
}, Ll = class extends Bn {
	constructor(e, t) {
		super("buffer-controller", e.logger), this.hls = void 0, this.fragmentTracker = void 0, this.details = null, this._objectUrl = null, this.operationQueue = null, this.bufferCodecEventsTotal = 0, this.media = null, this.mediaSource = null, this.lastMpegAudioChunk = null, this.blockedAudioAppend = null, this.lastVideoAppendEnd = 0, this.appendSource = void 0, this.transferData = void 0, this.overrides = void 0, this.appendErrors = {
			audio: 0,
			video: 0,
			audiovideo: 0
		}, this.tracks = {}, this.sourceBuffers = [[null, null], [null, null]], this._onEndStreaming = (e) => {
			this.hls && this.mediaSource?.readyState === "open" && this.hls.pauseBuffering();
		}, this._onStartStreaming = (e) => {
			this.hls && this.hls.resumeBuffering();
		}, this._onMediaSourceOpen = (e) => {
			let { media: t, mediaSource: n } = this;
			e && this.log("Media source opened"), t && n && (n.removeEventListener("sourceopen", this._onMediaSourceOpen), t.removeEventListener("emptied", this._onMediaEmptied), this.updateDuration(), this.hls.trigger(q.MEDIA_ATTACHED, {
				media: t,
				mediaSource: n
			}), this.mediaSource !== null && this.checkPendingTracks());
		}, this._onMediaSourceClose = () => {
			this.log("Media source closed");
		}, this._onMediaSourceEnded = () => {
			this.log("Media source ended");
		}, this._onMediaEmptied = () => {
			let { mediaSrc: e, _objectUrl: t } = this;
			e !== t && this.error(`Media element src was set while attaching MediaSource (${t} > ${e})`);
		}, this.hls = e, this.fragmentTracker = t, this.appendSource = Xn(Yn(e.config.preferManagedMediaSource)), this.initTracks(), this.registerListeners();
	}
	hasSourceTypes() {
		return Object.keys(this.tracks).length > 0;
	}
	destroy() {
		this.unregisterListeners(), this.details = null, this.lastMpegAudioChunk = this.blockedAudioAppend = null, this.transferData = this.overrides = void 0, this.operationQueue &&= (this.operationQueue.destroy(), null), this.hls = this.fragmentTracker = null, this._onMediaSourceOpen = this._onMediaSourceClose = null, this._onMediaSourceEnded = null, this._onStartStreaming = this._onEndStreaming = null;
	}
	registerListeners() {
		let { hls: e } = this;
		e.on(q.MEDIA_ATTACHING, this.onMediaAttaching, this), e.on(q.MEDIA_DETACHING, this.onMediaDetaching, this), e.on(q.MANIFEST_LOADING, this.onManifestLoading, this), e.on(q.MANIFEST_PARSED, this.onManifestParsed, this), e.on(q.BUFFER_RESET, this.onBufferReset, this), e.on(q.BUFFER_APPENDING, this.onBufferAppending, this), e.on(q.BUFFER_CODECS, this.onBufferCodecs, this), e.on(q.BUFFER_EOS, this.onBufferEos, this), e.on(q.BUFFER_FLUSHING, this.onBufferFlushing, this), e.on(q.LEVEL_UPDATED, this.onLevelUpdated, this), e.on(q.FRAG_PARSED, this.onFragParsed, this), e.on(q.FRAG_CHANGED, this.onFragChanged, this), e.on(q.ERROR, this.onError, this);
	}
	unregisterListeners() {
		let { hls: e } = this;
		e.off(q.MEDIA_ATTACHING, this.onMediaAttaching, this), e.off(q.MEDIA_DETACHING, this.onMediaDetaching, this), e.off(q.MANIFEST_LOADING, this.onManifestLoading, this), e.off(q.MANIFEST_PARSED, this.onManifestParsed, this), e.off(q.BUFFER_RESET, this.onBufferReset, this), e.off(q.BUFFER_APPENDING, this.onBufferAppending, this), e.off(q.BUFFER_CODECS, this.onBufferCodecs, this), e.off(q.BUFFER_EOS, this.onBufferEos, this), e.off(q.BUFFER_FLUSHING, this.onBufferFlushing, this), e.off(q.LEVEL_UPDATED, this.onLevelUpdated, this), e.off(q.FRAG_PARSED, this.onFragParsed, this), e.off(q.FRAG_CHANGED, this.onFragChanged, this), e.off(q.ERROR, this.onError, this);
	}
	transferMedia() {
		let { media: e, mediaSource: t } = this;
		if (!e) return null;
		let n = {};
		if (this.operationQueue) {
			let e = this.isUpdating();
			e || this.operationQueue.removeBlockers();
			let t = this.isQueued();
			(e || t) && this.warn(`Transfering MediaSource with${t ? " operations in queue" : ""}${e ? " updating SourceBuffer(s)" : ""} ${this.operationQueue}`), this.operationQueue.destroy();
		}
		let r = this.transferData;
		return !this.sourceBufferCount && r && r.mediaSource === t ? Fn(n, r.tracks) : this.sourceBuffers.forEach((e) => {
			let [t] = e;
			t && (n[t] = Fn({}, this.tracks[t]), this.removeBuffer(t)), e[0] = e[1] = null;
		}), {
			media: e,
			mediaSource: t,
			tracks: n
		};
	}
	initTracks() {
		let e = {};
		this.sourceBuffers = [[null, null], [null, null]], this.tracks = e, this.resetQueue(), this.resetAppendErrors(), this.lastMpegAudioChunk = this.blockedAudioAppend = null, this.lastVideoAppendEnd = 0;
	}
	onManifestLoading() {
		this.bufferCodecEventsTotal = 0, this.details = null;
	}
	onManifestParsed(e, t) {
		var n;
		let r = 2;
		(t.audio && !t.video || !t.altAudio) && (r = 1), this.bufferCodecEventsTotal = r, this.log(`${r} bufferCodec event(s) expected.`), (n = this.transferData) != null && n.mediaSource && this.sourceBufferCount && r && this.bufferCreated();
	}
	onMediaAttaching(e, t) {
		let n = this.media = t.media;
		this.transferData = this.overrides = void 0;
		let r = Yn(this.appendSource);
		if (r) {
			let e = !!t.mediaSource;
			(e || t.overrides) && (this.transferData = t, this.overrides = t.overrides);
			let i = this.mediaSource = t.mediaSource || new r();
			if (this.assignMediaSource(i), e) this._objectUrl = n.src, this.attachTransferred();
			else {
				let e = this._objectUrl = self.URL.createObjectURL(i);
				if (this.appendSource) try {
					n.removeAttribute("src");
					let t = self.ManagedMediaSource;
					n.disableRemotePlayback = n.disableRemotePlayback || t && i instanceof t, Rl(n), zl(n, e), n.load();
				} catch {
					n.src = e;
				}
				else n.src = e;
			}
			n.addEventListener("emptied", this._onMediaEmptied);
		}
	}
	assignMediaSource(e) {
		this.log(`${this.transferData?.mediaSource === e ? "transferred" : "created"} media source: ${e.constructor?.name}`), e.addEventListener("sourceopen", this._onMediaSourceOpen), e.addEventListener("sourceended", this._onMediaSourceEnded), e.addEventListener("sourceclose", this._onMediaSourceClose), this.appendSource && (e.addEventListener("startstreaming", this._onStartStreaming), e.addEventListener("endstreaming", this._onEndStreaming));
	}
	attachTransferred() {
		let e = this.media, t = this.transferData;
		if (!t || !e) return;
		let n = this.tracks, r = t.tracks, i = r ? Object.keys(r) : null, a = i ? i.length : 0, o = () => {
			Promise.resolve().then(() => {
				this.media && this.mediaSourceOpenOrEnded && this._onMediaSourceOpen();
			});
		};
		if (r && i && a) {
			if (!this.tracksReady) {
				this.hls.config.startFragPrefetch = !0, this.log("attachTransferred: waiting for SourceBuffer track info");
				return;
			}
			if (this.log(`attachTransferred: (bufferCodecEventsTotal ${this.bufferCodecEventsTotal})
required tracks: ${Fi(n, (e, t) => e === "initSegment" ? void 0 : t)};
transfer tracks: ${Fi(r, (e, t) => e === "initSegment" ? void 0 : t)}}`), !Zn(r, n)) {
				t.mediaSource = null, t.tracks = void 0;
				let i = e.currentTime, a = this.details, o = Math.max(i, a?.fragments[0].start || 0);
				if (o - i > 1) {
					this.log(`attachTransferred: waiting for playback to reach new tracks start time ${i} -> ${o}`);
					return;
				}
				this.warn(`attachTransferred: resetting MediaSource for incompatible tracks ("${Object.keys(r)}"->"${Object.keys(n)}") start time: ${o} currentTime: ${i}`), this.onMediaDetaching(q.MEDIA_DETACHING, {}), this.onMediaAttaching(q.MEDIA_ATTACHING, t), e.currentTime = o;
				return;
			}
			this.transferData = void 0, i.forEach((e) => {
				let t = e, n = r[t];
				if (n) {
					let e = n.buffer;
					if (e) {
						let r = this.fragmentTracker, i = n.id;
						if (r.hasFragments(i) || r.hasParts(i)) {
							let n = Q.getBuffered(e);
							r.detectEvictedFragments(t, n, i, null, !0);
						}
						let a = Bl(t), o = [t, e];
						this.sourceBuffers[a] = o, e.updating && this.operationQueue && this.operationQueue.prependBlocker(t), this.trackSourceBuffer(t, n);
					}
				}
			}), o(), this.bufferCreated();
		} else this.log("attachTransferred: MediaSource w/o SourceBuffers"), o();
	}
	get mediaSourceOpenOrEnded() {
		let e = this.mediaSource?.readyState;
		return e === "open" || e === "ended";
	}
	onMediaDetaching(e, t) {
		let n = !!t.transferMedia;
		this.transferData = this.overrides = void 0;
		let { media: r, mediaSource: i, _objectUrl: a } = this;
		if (i) {
			if (this.log(`media source ${n ? "transferring" : "detaching"}`), n) this.sourceBuffers.forEach(([e]) => {
				e && this.removeBuffer(e);
			}), this.resetQueue();
			else {
				if (this.mediaSourceOpenOrEnded) {
					let e = i.readyState === "open";
					try {
						let t = i.sourceBuffers;
						for (let n = t.length; n--;) e && t[n].abort(), i.removeSourceBuffer(t[n]);
						e && i.endOfStream();
					} catch (e) {
						this.warn(`onMediaDetaching: ${e.message} while calling endOfStream`);
					}
				}
				this.sourceBufferCount && this.onBufferReset();
			}
			i.removeEventListener("sourceopen", this._onMediaSourceOpen), i.removeEventListener("sourceended", this._onMediaSourceEnded), i.removeEventListener("sourceclose", this._onMediaSourceClose), this.appendSource && (i.removeEventListener("startstreaming", this._onStartStreaming), i.removeEventListener("endstreaming", this._onEndStreaming)), this.mediaSource = null, this._objectUrl = null;
		}
		r && (r.removeEventListener("emptied", this._onMediaEmptied), n || (a && self.URL.revokeObjectURL(a), this.mediaSrc === a ? (r.removeAttribute("src"), this.appendSource && Rl(r), r.load()) : this.warn("media|source.src was changed by a third party - skip cleanup")), this.media = null), this.hls.trigger(q.MEDIA_DETACHED, t);
	}
	onBufferReset() {
		this.sourceBuffers.forEach(([e]) => {
			e && this.resetBuffer(e);
		}), this.initTracks();
	}
	resetBuffer(e) {
		let t = this.tracks[e]?.buffer;
		if (this.removeBuffer(e), t) try {
			var n;
			(n = this.mediaSource) != null && n.sourceBuffers.length && this.mediaSource.removeSourceBuffer(t);
		} catch (t) {
			this.warn(`onBufferReset ${e}`, t);
		}
		delete this.tracks[e];
	}
	removeBuffer(e) {
		this.removeBufferListeners(e), this.sourceBuffers[Bl(e)] = [null, null];
		let t = this.tracks[e];
		t && (t.buffer = void 0);
	}
	resetQueue() {
		this.operationQueue && this.operationQueue.destroy(), this.operationQueue = new Nl(this.tracks);
	}
	onBufferCodecs(e, t) {
		let n = this.tracks, r = Object.keys(t);
		this.log(`BUFFER_CODECS: "${r}" (current SB count ${this.sourceBufferCount})`);
		let i = "audiovideo" in t && (n.audio || n.video) || n.audiovideo && ("audio" in t || "video" in t), a = !i && this.sourceBufferCount && this.media && r.some((e) => !n[e]);
		i || a ? this.warn(`Unsupported transition between "${Object.keys(n)}" and "${r}" SourceBuffers`) : (r.forEach((e) => {
			var r;
			let { id: i, codec: a, levelCodec: o, container: s, metadata: c, supplemental: l } = t[e], u = n[e], d = (r = this.transferData) == null || (r = r.tracks) == null ? void 0 : r[e], f = d != null && d.buffer ? d : u, p = f?.pendingCodec || f?.codec, m = f?.levelCodec;
			u ||= n[e] = {
				buffer: void 0,
				listeners: [],
				codec: a,
				supplemental: l,
				container: s,
				levelCodec: o,
				metadata: c,
				id: i
			};
			let h = oi(p, m), g = h?.replace(Pl, "$1"), _ = oi(a, o), v = _?.replace(Pl, "$1");
			_ && h && g !== v && (e.slice(0, 5) === "audio" && (_ = ii(_, this.appendSource)), this.log(`switching codec ${p} to ${_}`), _ !== (u.pendingCodec || u.codec) && (u.pendingCodec = _), u.container = s, this.appendChangeType(e, s, _));
		}), (this.tracksReady || this.sourceBufferCount) && (t.tracks = this.sourceBufferTracks), this.sourceBufferCount || (this.bufferCodecEventsTotal > 1 && !this.tracks.video && !t.video && t.audio?.id === "main" && (this.log("Main audio-only"), this.bufferCodecEventsTotal = 1), this.mediaSourceOpenOrEnded && this.checkPendingTracks()));
	}
	get sourceBufferTracks() {
		return Object.keys(this.tracks).reduce((e, t) => {
			let n = this.tracks[t];
			return e[t] = {
				id: n.id,
				container: n.container,
				codec: n.codec,
				levelCodec: n.levelCodec
			}, e;
		}, {});
	}
	appendChangeType(e, t, n) {
		let r = `${t};codecs=${n}`, i = {
			label: `change-type=${r}`,
			execute: () => {
				let i = this.tracks[e];
				if (i) {
					let a = i.buffer;
					a != null && a.changeType && (this.log(`changing ${e} sourceBuffer type to ${r}`), a.changeType(r), i.codec = n, i.container = t);
				}
				this.shiftAndExecuteNext(e);
			},
			onStart: () => {},
			onComplete: () => {},
			onError: (t) => {
				this.warn(`Failed to change ${e} SourceBuffer type`, t);
			}
		};
		this.append(i, e, this.isPending(this.tracks[e]));
	}
	blockAudio(e) {
		let t = e.start, n = t + e.duration * .05;
		if (this.fragmentTracker.getAppendedFrag(t, Y.MAIN)?.gap === !0) return;
		let r = {
			label: "block-audio",
			execute: () => {
				let e = this.tracks.video;
				(this.lastVideoAppendEnd > n || e != null && e.buffer && Q.isBuffered(e.buffer, n) || this.fragmentTracker.getAppendedFrag(n, Y.MAIN)?.gap === !0) && (this.blockedAudioAppend = null, this.shiftAndExecuteNext("audio"));
			},
			onStart: () => {},
			onComplete: () => {},
			onError: (e) => {
				this.warn("Error executing block-audio operation", e);
			}
		};
		this.blockedAudioAppend = {
			op: r,
			frag: e
		}, this.append(r, "audio", !0);
	}
	unblockAudio() {
		let { blockedAudioAppend: e, operationQueue: t } = this;
		e && t && (this.blockedAudioAppend = null, t.unblockAudio(e.op));
	}
	onBufferAppending(e, t) {
		let { tracks: n } = this, { data: r, type: i, parent: a, frag: o, part: s, chunkMeta: c, offset: l } = t, u = c.buffering[i], { sn: d, cc: f } = o, p = self.performance.now();
		u.start = p;
		let m = o.stats.buffering, h = s ? s.stats.buffering : null;
		m.start === 0 && (m.start = p), h && h.start === 0 && (h.start = p);
		let g = n.audio, _ = !1;
		i === "audio" && g?.container === "audio/mpeg" && (_ = !this.lastMpegAudioChunk || c.id === 1 || this.lastMpegAudioChunk.sn !== c.sn, this.lastMpegAudioChunk = c);
		let v = n.video, y = v?.buffer;
		if (y && d !== "initSegment") {
			let e = s || o, t = this.blockedAudioAppend;
			if (i === "audio" && a !== "main" && !this.blockedAudioAppend && !(v.ending || v.ended)) {
				let t = e.start + e.duration * .05, n = y.buffered, r = this.currentOp("video");
				(!n.length && !r || !r && !Q.isBuffered(y, t) && this.lastVideoAppendEnd < t) && this.blockAudio(e);
			} else if (i === "video") {
				let n = e.end;
				if (t) {
					let e = t.frag.start;
					(n > e || n < this.lastVideoAppendEnd || Q.isBuffered(y, e)) && this.unblockAudio();
				}
				this.lastVideoAppendEnd = n;
			}
		}
		let b = (s || o).start, x = {
			label: `append-${i}`,
			execute: () => {
				u.executeStart = self.performance.now();
				let e = this.tracks[i]?.buffer;
				e && (_ ? this.updateTimestampOffset(e, b, .1, i, d, f) : l !== void 0 && W(l) && this.updateTimestampOffset(e, l, 1e-6, i, d, f)), this.appendExecutor(r, i);
			},
			onStart: () => {},
			onComplete: () => {
				let e = self.performance.now();
				u.executeEnd = u.end = e, m.first === 0 && (m.first = e), h && h.first === 0 && (h.first = e);
				let t = {};
				this.sourceBuffers.forEach(([e, n]) => {
					e && (t[e] = Q.getBuffered(n));
				}), this.appendErrors[i] = 0, i === "audio" || i === "video" ? this.appendErrors.audiovideo = 0 : (this.appendErrors.audio = 0, this.appendErrors.video = 0), this.hls.trigger(q.BUFFER_APPENDED, {
					type: i,
					frag: o,
					part: s,
					chunkMeta: c,
					parent: o.type,
					timeRanges: t
				});
			},
			onError: (e) => {
				let t = {
					type: G.MEDIA_ERROR,
					parent: o.type,
					details: K.BUFFER_APPEND_ERROR,
					sourceBufferName: i,
					frag: o,
					part: s,
					chunkMeta: c,
					error: e,
					err: e,
					fatal: !1
				}, n = this.media?.error;
				if (e.code === DOMException.QUOTA_EXCEEDED_ERR || e.name == "QuotaExceededError" || "quota" in e) t.details = K.BUFFER_FULL_ERROR;
				else if (e.code === DOMException.INVALID_STATE_ERR && this.mediaSourceOpenOrEnded && !n) t.errorAction = ha(!0);
				else if (e.name === Fl && this.sourceBufferCount === 0) t.errorAction = ha(!0);
				else {
					let e = ++this.appendErrors[i];
					this.warn(`Failed ${e}/${this.hls.config.appendErrorMaxRetry} times to append segment in "${i}" sourceBuffer (${n || "no media error"})`), (e >= this.hls.config.appendErrorMaxRetry || n) && (t.fatal = !0);
				}
				this.hls.trigger(q.ERROR, t);
			}
		};
		this.log(`queuing "${i}" append sn: ${d}${s ? " p: " + s.index : ""} of ${o.type === Y.MAIN ? "level" : "track"} ${o.level} cc: ${f}`), this.append(x, i, this.isPending(this.tracks[i]));
	}
	getFlushOp(e, t, n) {
		return this.log(`queuing "${e}" remove ${t}-${n}`), {
			label: "remove",
			execute: () => {
				this.removeExecutor(e, t, n);
			},
			onStart: () => {},
			onComplete: () => {
				this.hls.trigger(q.BUFFER_FLUSHED, { type: e });
			},
			onError: (r) => {
				this.warn(`Failed to remove ${t}-${n} from "${e}" SourceBuffer`, r);
			}
		};
	}
	onBufferFlushing(e, t) {
		let { type: n, startOffset: r, endOffset: i } = t;
		n ? this.append(this.getFlushOp(n, r, i), n) : this.sourceBuffers.forEach(([e]) => {
			e && this.append(this.getFlushOp(e, r, i), e);
		});
	}
	onFragParsed(e, t) {
		let { frag: n, part: r } = t, i = [], a = r ? r.elementaryStreams : n.elementaryStreams;
		a[sr.AUDIOVIDEO] ? i.push("audiovideo") : (a[sr.AUDIO] && i.push("audio"), a[sr.VIDEO] && i.push("video")), i.length === 0 && this.warn(`Fragments must have at least one ElementaryStreamType set. type: ${n.type} level: ${n.level} sn: ${n.sn}`), this.blockBuffers(() => {
			let e = self.performance.now();
			n.stats.buffering.end = e, r && (r.stats.buffering.end = e);
			let t = r ? r.stats : n.stats;
			this.hls.trigger(q.FRAG_BUFFERED, {
				frag: n,
				part: r,
				stats: t,
				id: n.type
			});
		}, i).catch((e) => {
			this.warn(`Fragment buffered callback ${e}`), this.stepOperationQueue(this.sourceBufferTypes);
		});
	}
	onFragChanged(e, t) {
		this.trimBuffers();
	}
	get bufferedToEnd() {
		return this.sourceBufferCount > 0 && !this.sourceBuffers.some(([e]) => {
			if (e) {
				let t = this.tracks[e];
				if (t) return !t.ended || t.ending;
			}
			return !1;
		});
	}
	onBufferEos(e, t) {
		this.sourceBuffers.forEach(([e]) => {
			if (e) {
				let n = this.tracks[e];
				t.type && t.type !== e || (n.ending = !0, n.ended || (n.ended = !0, this.log(`${e} buffer reached EOS`)));
			}
		});
		let n = this.overrides?.endOfStream !== !1;
		this.sourceBufferCount > 0 && !this.sourceBuffers.some(([e]) => {
			var t;
			return e && !((t = this.tracks[e]) != null && t.ended);
		}) ? n ? (this.log("Queueing EOS"), this.blockUntilOpen(() => {
			this.tracksEnded();
			let { mediaSource: e } = this;
			!e || e.readyState !== "open" ? e && this.log(`Could not call mediaSource.endOfStream(). mediaSource.readyState: ${e.readyState}`) : (this.log("Calling mediaSource.endOfStream()"), e.endOfStream(), this.hls.trigger(q.BUFFERED_TO_END, void 0));
		})) : (this.tracksEnded(), this.hls.trigger(q.BUFFERED_TO_END, void 0)) : t.type === "video" && this.unblockAudio();
	}
	tracksEnded() {
		this.sourceBuffers.forEach(([e]) => {
			if (e !== null) {
				let t = this.tracks[e];
				t && (t.ending = !1);
			}
		});
	}
	onLevelUpdated(e, { details: t }) {
		t.fragments.length && (this.details = t, this.updateDuration());
	}
	updateDuration() {
		this.blockUntilOpen(() => {
			let e = this.getDurationAndRange();
			e && this.updateMediaSource(e);
		});
	}
	onError(e, t) {
		if (t.details === K.BUFFER_APPEND_ERROR && t.frag) {
			let e = t.errorAction?.nextAutoLevel;
			W(e) && e !== t.frag.level && this.resetAppendErrors();
		}
	}
	resetAppendErrors() {
		this.appendErrors = {
			audio: 0,
			video: 0,
			audiovideo: 0
		};
	}
	trimBuffers() {
		let { hls: e, details: t, media: n } = this;
		if (!n || t === null || !this.sourceBufferCount) return;
		let r = e.config, i = n.currentTime, a = t.levelTargetDuration, o = t.live && r.liveBackBufferLength !== null ? r.liveBackBufferLength : r.backBufferLength;
		if (W(o) && o >= 0) {
			let e = Math.max(o, a), t = Math.floor(i / a) * a - e;
			this.flushBackBuffer(i, a, t);
		}
		let s = r.frontBufferFlushThreshold;
		if (W(s) && s > 0) {
			let e = Math.max(r.maxBufferLength, s), t = Math.max(e, a), n = Math.floor(i / a) * a + t;
			this.flushFrontBuffer(i, a, n);
		}
	}
	flushBackBuffer(e, t, n) {
		this.sourceBuffers.forEach(([e, t]) => {
			if (t) {
				let i = Q.getBuffered(t);
				if (i.length > 0 && n > i.start(0)) {
					var r;
					this.hls.trigger(q.BACK_BUFFER_REACHED, { bufferEnd: n });
					let t = this.tracks[e];
					if ((r = this.details) != null && r.live) this.hls.trigger(q.LIVE_BACK_BUFFER_REACHED, { bufferEnd: n });
					else if (t != null && t.ended) {
						this.log(`Cannot flush ${e} back buffer while SourceBuffer is in ended state`);
						return;
					}
					this.hls.trigger(q.BUFFER_FLUSHING, {
						startOffset: 0,
						endOffset: n,
						type: e
					});
				}
			}
		});
	}
	flushFrontBuffer(e, t, n) {
		this.sourceBuffers.forEach(([t, r]) => {
			if (r) {
				let i = Q.getBuffered(r), a = i.length;
				if (a < 2) return;
				let o = i.start(a - 1), s = i.end(a - 1);
				if (n > o || e >= o && e <= s) return;
				this.hls.trigger(q.BUFFER_FLUSHING, {
					startOffset: o,
					endOffset: Infinity,
					type: t
				});
			}
		});
	}
	getDurationAndRange() {
		let { details: e, mediaSource: t } = this;
		if (!e || !this.media || t?.readyState !== "open") return null;
		let n = e.edge;
		if (e.live && this.hls.config.liveDurationInfinity) {
			if (e.fragments.length && t.setLiveSeekableRange) {
				let t = Math.max(0, e.fragmentStart);
				return {
					duration: Infinity,
					start: t,
					end: Math.max(t, n)
				};
			}
			return { duration: Infinity };
		}
		let r = this.overrides?.duration;
		if (r) return W(r) ? { duration: r } : null;
		let i = this.media.duration;
		return n > (W(t.duration) ? t.duration : 0) && n > i || !W(i) ? { duration: n } : null;
	}
	updateMediaSource({ duration: e, start: t, end: n }) {
		let r = this.mediaSource;
		this.media && r && r.readyState === "open" && (r.duration !== e && (W(e) && this.log(`Updating MediaSource duration to ${e.toFixed(3)}`), r.duration = e), t !== void 0 && n !== void 0 && (this.log(`MediaSource duration is set to ${r.duration}. Setting seekable range to ${t}-${n}.`), r.setLiveSeekableRange(t, n)));
	}
	get tracksReady() {
		let e = this.pendingTrackCount;
		return e > 0 && (e >= this.bufferCodecEventsTotal || this.isPending(this.tracks.audiovideo));
	}
	checkPendingTracks() {
		let { bufferCodecEventsTotal: e, pendingTrackCount: t, tracks: n } = this;
		if (this.log(`checkPendingTracks (pending: ${t} codec events expected: ${e}) ${Fi(n)}`), this.tracksReady) {
			let e = this.transferData?.tracks;
			e && Object.keys(e).length ? this.attachTransferred() : this.createSourceBuffers();
		}
	}
	bufferCreated() {
		if (this.sourceBufferCount) {
			let e = {};
			this.sourceBuffers.forEach(([t, n]) => {
				if (t) {
					let r = this.tracks[t];
					e[t] = {
						buffer: n,
						container: r.container,
						codec: r.codec,
						supplemental: r.supplemental,
						levelCodec: r.levelCodec,
						id: r.id,
						metadata: r.metadata
					};
				}
			}), this.hls.trigger(q.BUFFER_CREATED, { tracks: e }), this.log(`SourceBuffers created. Running queue: ${this.operationQueue}`), this.sourceBuffers.forEach(([e]) => {
				this.executeNext(e);
			});
		} else {
			let e = /* @__PURE__ */ Error("could not create source buffer for media codec(s)");
			this.hls.trigger(q.ERROR, {
				type: G.MEDIA_ERROR,
				details: K.BUFFER_INCOMPATIBLE_CODECS_ERROR,
				fatal: !0,
				error: e,
				reason: e.message
			});
		}
	}
	createSourceBuffers() {
		let { tracks: e, sourceBuffers: t, mediaSource: n } = this;
		if (!n) throw Error("createSourceBuffers called when mediaSource was null");
		for (let i in e) {
			let a = i, o = e[a];
			if (this.isPending(o)) {
				let e = this.getTrackCodec(o, a), i = `${o.container};codecs=${e}`;
				o.codec = e, this.log(`creating sourceBuffer(${i})${this.currentOp(a) ? " Queued" : ""} ${Fi(o)}`);
				try {
					let e = n.addSourceBuffer(i), r = Bl(a);
					t[r] = [a, e], o.buffer = e;
				} catch (e) {
					var r;
					this.error(`error while trying to add sourceBuffer: ${e.message}`), this.shiftAndExecuteNext(a), (r = this.operationQueue) == null || r.removeBlockers(), delete this.tracks[a], this.hls.trigger(q.ERROR, {
						type: G.MEDIA_ERROR,
						details: K.BUFFER_ADD_CODEC_ERROR,
						fatal: !1,
						error: e,
						sourceBufferName: a,
						mimeType: i,
						parent: o.id
					});
					return;
				}
				this.trackSourceBuffer(a, o);
			}
		}
		this.bufferCreated();
	}
	getTrackCodec(e, t) {
		let n = e.supplemental, r = e.codec;
		n && (t === "video" || t === "audiovideo") && Xr(n, "video") && (r = ai(r, n));
		let i = oi(r, e.levelCodec);
		return i ? t.slice(0, 5) === "audio" ? ii(i, this.appendSource) : i : "";
	}
	trackSourceBuffer(e, t) {
		let n = t.buffer;
		if (!n) return;
		let r = this.getTrackCodec(t, e);
		this.tracks[e] = {
			buffer: n,
			codec: r,
			container: t.container,
			levelCodec: t.levelCodec,
			supplemental: t.supplemental,
			metadata: t.metadata,
			id: t.id,
			listeners: []
		}, this.removeBufferListeners(e), this.addBufferListener(e, "updatestart", this.onSBUpdateStart), this.addBufferListener(e, "updateend", this.onSBUpdateEnd), this.addBufferListener(e, "error", this.onSBUpdateError), this.appendSource && this.addBufferListener(e, "bufferedchange", (e, t) => {
			let n = t.removedRanges;
			n != null && n.length && this.hls.trigger(q.BUFFER_FLUSHED, { type: e });
		});
	}
	get mediaSrc() {
		var e, t;
		return (((e = this.media) == null || (t = e.querySelector) == null ? void 0 : t.call(e, "source")) || this.media)?.src;
	}
	onSBUpdateStart(e) {
		let t = this.currentOp(e);
		t && t.onStart();
	}
	onSBUpdateEnd(e) {
		if (this.mediaSource?.readyState === "closed") {
			this.resetBuffer(e);
			return;
		}
		let t = this.currentOp(e);
		t && (t.onComplete(), this.shiftAndExecuteNext(e));
	}
	onSBUpdateError(e, t) {
		let n = /* @__PURE__ */ Error(`${e} SourceBuffer error. MediaSource readyState: ${this.mediaSource?.readyState}`);
		this.error(`${n}`, t), this.hls.trigger(q.ERROR, {
			type: G.MEDIA_ERROR,
			details: K.BUFFER_APPENDING_ERROR,
			sourceBufferName: e,
			error: n,
			fatal: !1
		});
		let r = this.currentOp(e);
		r && r.onError(n);
	}
	updateTimestampOffset(e, t, n, r, i, a) {
		let o = t - e.timestampOffset;
		Math.abs(o) >= n && (this.log(`Updating ${r} SourceBuffer timestampOffset to ${t} (sn: ${i} cc: ${a})`), e.timestampOffset = t);
	}
	removeExecutor(e, t, n) {
		let { media: r, mediaSource: i } = this, a = this.tracks[e], o = a?.buffer;
		if (!r || !i || !o) {
			this.warn(`Attempting to remove from the ${e} SourceBuffer, but it does not exist`), this.shiftAndExecuteNext(e);
			return;
		}
		let s = W(r.duration) ? r.duration : Infinity, c = W(i.duration) ? i.duration : Infinity, l = Math.max(0, t), u = Math.min(n, s, c);
		u > l && (!a.ending || a.ended) ? (a.ended = !1, this.log(`Removing [${l},${u}] from the ${e} SourceBuffer`), o.remove(l, u)) : this.shiftAndExecuteNext(e);
	}
	appendExecutor(e, t) {
		let n = this.tracks[t], r = n?.buffer;
		if (!r) throw new Il(`Attempting to append to the ${t} SourceBuffer, but it does not exist`);
		n.ending = !1, n.ended = !1, r.appendBuffer(e);
	}
	blockUntilOpen(e) {
		if (this.isUpdating() || this.isQueued()) this.blockBuffers(e).catch((e) => {
			this.warn(`SourceBuffer blocked callback ${e}`), this.stepOperationQueue(this.sourceBufferTypes);
		});
		else try {
			e();
		} catch (e) {
			this.warn(`Callback run without blocking ${this.operationQueue} ${e}`);
		}
	}
	isUpdating() {
		return this.sourceBuffers.some(([e, t]) => e && t.updating);
	}
	isQueued() {
		return this.sourceBuffers.some(([e]) => e && !!this.currentOp(e));
	}
	isPending(e) {
		return !!e && !e.buffer;
	}
	blockBuffers(e, t = this.sourceBufferTypes) {
		if (!t.length) return this.log("Blocking operation requested, but no SourceBuffers exist"), Promise.resolve().then(e);
		let { operationQueue: n } = this, r = t.map((e) => this.appendBlocker(e));
		return t.length > 1 && this.blockedAudioAppend && this.unblockAudio(), Promise.all(r).then((t) => {
			n === this.operationQueue && (e(), this.stepOperationQueue(this.sourceBufferTypes));
		});
	}
	stepOperationQueue(e) {
		e.forEach((e) => {
			let t = this.tracks[e]?.buffer;
			t && !t.updating && this.shiftAndExecuteNext(e);
		});
	}
	append(e, t, n) {
		this.operationQueue && this.operationQueue.append(e, t, n);
	}
	appendBlocker(e) {
		if (this.operationQueue) return this.operationQueue.appendBlocker(e);
	}
	currentOp(e) {
		return this.operationQueue ? this.operationQueue.current(e) : null;
	}
	executeNext(e) {
		e && this.operationQueue && this.operationQueue.executeNext(e);
	}
	shiftAndExecuteNext(e) {
		this.operationQueue && this.operationQueue.shiftAndExecuteNext(e);
	}
	get pendingTrackCount() {
		return Object.keys(this.tracks).reduce((e, t) => e + +!!this.isPending(this.tracks[t]), 0);
	}
	get sourceBufferCount() {
		return this.sourceBuffers.reduce((e, [t]) => e + +!!t, 0);
	}
	get sourceBufferTypes() {
		return this.sourceBuffers.map(([e]) => e).filter((e) => !!e);
	}
	addBufferListener(e, t, n) {
		let r = this.tracks[e];
		if (!r) return;
		let i = r.buffer;
		if (!i) return;
		let a = n.bind(this, e);
		r.listeners.push({
			event: t,
			listener: a
		}), i.addEventListener(t, a);
	}
	removeBufferListeners(e) {
		let t = this.tracks[e];
		if (!t) return;
		let n = t.buffer;
		n && (t.listeners.forEach((e) => {
			n.removeEventListener(e.event, e.listener);
		}), t.listeners.length = 0);
	}
};
function Rl(e) {
	let t = e.querySelectorAll("source");
	[].slice.call(t).forEach((t) => {
		e.removeChild(t);
	});
}
function zl(e, t) {
	let n = self.document.createElement("source");
	n.type = "video/mp4", n.src = t, e.appendChild(n);
}
function Bl(e) {
	return +(e === "audio");
}
var Vl = class e {
	constructor(e) {
		this.hls = void 0, this.autoLevelCapping = void 0, this.firstLevel = void 0, this.media = void 0, this.restrictedLevels = void 0, this.timer = void 0, this.clientRect = void 0, this.streamController = void 0, this.hls = e, this.autoLevelCapping = Infinity, this.firstLevel = -1, this.media = null, this.restrictedLevels = [], this.timer = void 0, this.clientRect = null, this.registerListeners();
	}
	setStreamController(e) {
		this.streamController = e;
	}
	destroy() {
		this.hls && this.unregisterListener(), this.timer && this.stopCapping(), this.media = null, this.clientRect = null, this.hls = this.streamController = null;
	}
	registerListeners() {
		let { hls: e } = this;
		e.on(q.FPS_DROP_LEVEL_CAPPING, this.onFpsDropLevelCapping, this), e.on(q.MEDIA_ATTACHING, this.onMediaAttaching, this), e.on(q.MANIFEST_PARSED, this.onManifestParsed, this), e.on(q.LEVELS_UPDATED, this.onLevelsUpdated, this), e.on(q.BUFFER_CODECS, this.onBufferCodecs, this), e.on(q.MEDIA_DETACHING, this.onMediaDetaching, this);
	}
	unregisterListener() {
		let { hls: e } = this;
		e.off(q.FPS_DROP_LEVEL_CAPPING, this.onFpsDropLevelCapping, this), e.off(q.MEDIA_ATTACHING, this.onMediaAttaching, this), e.off(q.MANIFEST_PARSED, this.onManifestParsed, this), e.off(q.LEVELS_UPDATED, this.onLevelsUpdated, this), e.off(q.BUFFER_CODECS, this.onBufferCodecs, this), e.off(q.MEDIA_DETACHING, this.onMediaDetaching, this);
	}
	onFpsDropLevelCapping(e, t) {
		let n = this.hls.levels[t.droppedLevel];
		this.isLevelAllowed(n) && this.restrictedLevels.push({
			bitrate: n.bitrate,
			height: n.height,
			width: n.width
		});
	}
	onMediaAttaching(e, t) {
		this.media = t.media instanceof HTMLVideoElement ? t.media : null, this.clientRect = null, this.timer && this.hls.levels.length && this.detectPlayerSize();
	}
	onManifestParsed(e, t) {
		let n = this.hls;
		this.restrictedLevels = [], this.firstLevel = t.firstLevel, n.config.capLevelToPlayerSize && t.video && this.startCapping();
	}
	onLevelsUpdated(e, t) {
		this.timer && W(this.autoLevelCapping) && this.detectPlayerSize();
	}
	onBufferCodecs(e, t) {
		this.hls.config.capLevelToPlayerSize && t.video && this.startCapping();
	}
	onMediaDetaching() {
		this.stopCapping(), this.media = null;
	}
	detectPlayerSize() {
		if (this.media) {
			if (this.mediaHeight <= 0 || this.mediaWidth <= 0) {
				this.clientRect = null;
				return;
			}
			let e = this.hls.levels;
			if (e.length) {
				let t = this.hls, n = this.getMaxLevel(e.length - 1);
				n !== this.autoLevelCapping && t.logger.log(`Setting autoLevelCapping to ${n}: ${e[n].height}p@${e[n].bitrate} for media ${this.mediaWidth}x${this.mediaHeight}`), t.autoLevelCapping = n, t.autoLevelEnabled && t.autoLevelCapping > this.autoLevelCapping && this.streamController && this.streamController.nextLevelSwitch(), this.autoLevelCapping = t.autoLevelCapping;
			}
		}
	}
	getMaxLevel(t) {
		let n = this.hls.levels;
		if (!n.length) return -1;
		let r = n.filter((e, n) => this.isLevelAllowed(e) && n <= t);
		return this.clientRect = null, e.getMaxLevelByMediaSize(r, this.mediaWidth, this.mediaHeight);
	}
	startCapping() {
		this.timer || (this.autoLevelCapping = Infinity, self.clearInterval(this.timer), this.timer = self.setInterval(this.detectPlayerSize.bind(this), 1e3), this.detectPlayerSize());
	}
	stopCapping() {
		this.restrictedLevels = [], this.firstLevel = -1, this.autoLevelCapping = Infinity, this.timer &&= (self.clearInterval(this.timer), void 0);
	}
	getDimensions() {
		if (this.clientRect) return this.clientRect;
		let e = this.media, t = {
			width: 0,
			height: 0
		};
		if (e) {
			let n = e.getBoundingClientRect();
			t.width = n.width, t.height = n.height, !t.width && !t.height && (t.width = n.right - n.left || e.width || 0, t.height = n.bottom - n.top || e.height || 0);
		}
		return this.clientRect = t, t;
	}
	get mediaWidth() {
		return this.getDimensions().width * this.contentScaleFactor;
	}
	get mediaHeight() {
		return this.getDimensions().height * this.contentScaleFactor;
	}
	get contentScaleFactor() {
		let e = 1;
		if (!this.hls.config.ignoreDevicePixelRatio) try {
			e = self.devicePixelRatio;
		} catch {}
		return Math.min(e, this.hls.config.maxDevicePixelRatio);
	}
	isLevelAllowed(e) {
		return !this.restrictedLevels.some((t) => e.bitrate === t.bitrate && e.width === t.width && e.height === t.height);
	}
	static getMaxLevelByMediaSize(e, t, n) {
		if (!(e != null && e.length)) return -1;
		let r = (e, t) => !t || e.width !== t.width || e.height !== t.height, i = e.length - 1, a = Math.max(t, n);
		for (let t = 0; t < e.length; t += 1) {
			let n = e[t];
			if ((n.width >= a || n.height >= a) && r(n, e[t + 1])) {
				i = t;
				break;
			}
		}
		return i;
	}
}, Hl = {
	MANIFEST: "m",
	AUDIO: "a",
	VIDEO: "v",
	MUXED: "av",
	INIT: "i",
	CAPTION: "c",
	TIMED_TEXT: "tt",
	KEY: "k",
	OTHER: "o"
}, Ul = { HLS: "h" }, Wl = class e {
	constructor(t, n) {
		Array.isArray(t) && (t = t.map((t) => t instanceof e ? t : new e(t))), this.value = t, this.params = n;
	}
}, Gl = "Dict";
function Kl(e) {
	return Array.isArray(e) ? JSON.stringify(e) : e instanceof Map ? "Map{}" : e instanceof Set ? "Set{}" : typeof e == "object" ? JSON.stringify(e) : String(e);
}
function ql(e, t, n, r) {
	return Error(`failed to ${e} "${Kl(t)}" as ${n}`, { cause: r });
}
function Jl(e, t, n) {
	return ql("serialize", e, t, n);
}
var Yl = class {
	constructor(e) {
		this.description = e;
	}
}, Xl = "Bare Item", Zl = "Boolean";
function Ql(e) {
	if (typeof e != "boolean") throw Jl(e, Zl);
	return e ? "?1" : "?0";
}
function $l(e) {
	return btoa(String.fromCharCode(...e));
}
var eu = "Byte Sequence";
function tu(e) {
	if (ArrayBuffer.isView(e) === !1) throw Jl(e, eu);
	return `:${$l(e)}:`;
}
var nu = "Integer";
function ru(e) {
	return e < -999999999999999 || 999999999999999 < e;
}
function iu(e) {
	if (ru(e)) throw Jl(e, nu);
	return e.toString();
}
function au(e) {
	return `@${iu(e.getTime() / 1e3)}`;
}
function ou(e, t) {
	if (e < 0) return -ou(-e, t);
	let n = 10 ** t;
	if (Math.abs(e * n % 1 - .5) < 2 ** -52) {
		let t = Math.floor(e * n);
		return (t % 2 == 0 ? t : t + 1) / n;
	}
	return Math.round(e * n) / n;
}
var su = "Decimal";
function cu(e) {
	let t = ou(e, 3);
	if (Math.floor(Math.abs(t)).toString().length > 12) throw Jl(e, su);
	let n = t.toString();
	return n.includes(".") ? n : `${n}.0`;
}
var lu = "String", uu = /[\x00-\x1f\x7f]+/;
function du(e) {
	if (uu.test(e)) throw Jl(e, lu);
	return `"${e.replace(/\\/g, "\\\\").replace(/"/g, "\\\"")}"`;
}
function fu(e) {
	return e.description || e.toString().slice(7, -1);
}
var pu = "Token";
function mu(e) {
	let t = fu(e);
	if (/^([a-zA-Z*])([!#$%&'*+\-.^_`|~\w:/]*)$/.test(t) === !1) throw Jl(t, pu);
	return t;
}
function hu(e) {
	switch (typeof e) {
		case "number":
			if (!W(e)) throw Jl(e, Xl);
			return Number.isInteger(e) ? iu(e) : cu(e);
		case "string": return du(e);
		case "symbol": return mu(e);
		case "boolean": return Ql(e);
		case "object":
			if (e instanceof Date) return au(e);
			if (e instanceof Uint8Array) return tu(e);
			if (e instanceof Yl) return mu(e);
		default: throw Jl(e, Xl);
	}
}
var gu = "Key";
function _u(e) {
	if (/^[a-z*][a-z0-9\-_.*]*$/.test(e) === !1) throw Jl(e, gu);
	return e;
}
function vu(e) {
	return e == null ? "" : Object.entries(e).map(([e, t]) => t === !0 ? `;${_u(e)}` : `;${_u(e)}=${hu(t)}`).join("");
}
function yu(e) {
	return e instanceof Wl ? `${hu(e.value)}${vu(e.params)}` : hu(e);
}
function bu(e) {
	return `(${e.value.map(yu).join(" ")})${vu(e.params)}`;
}
function xu(e, t = { whitespace: !0 }) {
	if (typeof e != "object" || !e) throw Jl(e, Gl);
	let n = e instanceof Map ? e.entries() : Object.entries(e), r = t?.whitespace ? " " : "";
	return Array.from(n).map(([e, t]) => {
		t instanceof Wl || (t = new Wl(t));
		let n = _u(e);
		return t.value === !0 ? n += vu(t.params) : (n += "=", Array.isArray(t.value) ? n += bu(t) : n += yu(t)), n;
	}).join(`,${r}`);
}
function Su(e, t) {
	return xu(e, t);
}
var Cu = "CMCD-Object", wu = "CMCD-Request", Tu = "CMCD-Session", Eu = "CMCD-Status", Du = {
	br: Cu,
	ab: Cu,
	d: Cu,
	ot: Cu,
	tb: Cu,
	tpb: Cu,
	lb: Cu,
	tab: Cu,
	lab: Cu,
	url: Cu,
	pb: wu,
	bl: wu,
	tbl: wu,
	dl: wu,
	ltc: wu,
	mtp: wu,
	nor: wu,
	nrr: wu,
	rc: wu,
	sn: wu,
	sta: wu,
	su: wu,
	ttfb: wu,
	ttfbb: wu,
	ttlb: wu,
	cmsdd: wu,
	cmsds: wu,
	smrt: wu,
	df: wu,
	cs: wu,
	ts: wu,
	cid: Tu,
	pr: Tu,
	sf: Tu,
	sid: Tu,
	st: Tu,
	v: Tu,
	msd: Tu,
	bs: Eu,
	bsd: Eu,
	cdn: Eu,
	rtp: Eu,
	bg: Eu,
	pt: Eu,
	ec: Eu,
	e: Eu
}, Ou = { REQUEST: wu };
function ku(e) {
	return Object.keys(e).reduce((t, n) => {
		var r;
		return (r = e[n]) == null || r.forEach((e) => t[e] = n), t;
	}, {});
}
function Au(e, t) {
	let n = {};
	if (!e) return n;
	let r = Object.keys(e), i = t ? ku(t) : {};
	return r.reduce((t, n) => {
		let r = Du[n] || i[n] || Ou.REQUEST, a = t[r] ?? (t[r] = {});
		return a[n] = e[n], t;
	}, n);
}
function ju(e) {
	return [
		"ot",
		"sf",
		"st",
		"e",
		"sta"
	].includes(e);
}
function Mu(e) {
	return typeof e == "number" ? W(e) : e != null && e !== "" && e !== !1;
}
var Nu = "event";
function Pu(e, t) {
	let n = new URL(e), r = new URL(t);
	if (n.origin !== r.origin) return e;
	let i = n.pathname.split("/").slice(1), a = r.pathname.split("/").slice(1, -1);
	for (; i[0] === a[0];) i.shift(), a.shift();
	for (; a.length;) a.shift(), i.unshift("..");
	return i.join("/") + n.search + n.hash;
}
var Fu = (e) => Math.round(e), Iu = (e, t) => Array.isArray(e) ? e.map((e) => Iu(e, t)) : e instanceof Wl && typeof e.value == "string" ? new Wl(Iu(e.value, t), e.params) : (t.baseUrl && (e = Pu(e, t.baseUrl)), t.version === 1 ? encodeURIComponent(e) : e), Lu = (e) => Fu(e / 100) * 100, Ru = {
	br: Fu,
	d: Fu,
	bl: Lu,
	dl: Lu,
	mtp: Lu,
	nor: (e, t) => {
		let n = e;
		return t.version >= 2 && (e instanceof Wl && typeof e.value == "string" ? n = new Wl([e]) : typeof e == "string" && (n = [e])), Iu(n, t);
	},
	rtp: Lu,
	tb: Fu
}, zu = "request", Bu = "response", Vu = /* @__PURE__ */ "ab.bg.bl.br.bs.bsd.cdn.cid.cs.df.ec.lab.lb.ltc.msd.mtp.pb.pr.pt.sf.sid.sn.st.sta.tab.tb.tbl.tpb.ts.v".split("."), Hu = ["e"], Uu = /^[a-zA-Z0-9-.]+-[a-zA-Z0-9-.]+$/;
function Wu(e) {
	return Uu.test(e);
}
function Gu(e) {
	return Vu.includes(e) || Hu.includes(e) || Wu(e);
}
var Ku = [
	"d",
	"dl",
	"nor",
	"ot",
	"rtp",
	"su"
];
function qu(e) {
	return Vu.includes(e) || Ku.includes(e) || Wu(e);
}
var Ju = [
	"cmsdd",
	"cmsds",
	"rc",
	"smrt",
	"ttfb",
	"ttfbb",
	"ttlb",
	"url"
];
function Yu(e) {
	return Vu.includes(e) || Ku.includes(e) || Ju.includes(e) || Wu(e);
}
var Xu = [
	"bl",
	"br",
	"bs",
	"cid",
	"d",
	"dl",
	"mtp",
	"nor",
	"nrr",
	"ot",
	"pr",
	"rtp",
	"sf",
	"sid",
	"st",
	"su",
	"tb",
	"v"
];
function Zu(e) {
	return Xu.includes(e) || Wu(e);
}
var Qu = {
	[Bu]: Yu,
	[Nu]: Gu,
	[zu]: qu
};
function $u(e, t = {}) {
	let n = {};
	if (typeof e != "object" || !e) return n;
	let r = t.version || e.v || 1, i = t.reportingMode || zu, a = r === 1 ? Zu : Qu[i], o = Object.keys(e).filter(a), s = t.filter;
	typeof s == "function" && (o = o.filter(s));
	let c = i === Bu || i === Nu;
	c && !o.includes("ts") && o.push("ts"), r > 1 && !o.includes("v") && o.push("v");
	let l = Fn({}, Ru, t.formatters), u = {
		version: r,
		reportingMode: i,
		baseUrl: t.baseUrl
	};
	return o.sort().forEach((t) => {
		let i = e[t], a = l[t];
		if (typeof a == "function" && (i = a(i, u)), t === "v") {
			if (r === 1) return;
			i = r;
		}
		(t != "pr" || i !== 1) && (c && t === "ts" && !W(i) && (i = Date.now()), Mu(i) && (ju(t) && typeof i == "string" && (i = new Yl(i)), n[t] = i));
	}), n;
}
function ed(e, t = {}) {
	let n = {};
	if (!e) return n;
	let r = Au($u(e, t), t?.customHeaderMap);
	return Object.entries(r).reduce((e, [t, n]) => {
		let r = Su(n, { whitespace: !1 });
		return r && (e[t] = r), e;
	}, n);
}
function td(e, t, n) {
	return Fn(e, ed(t, n));
}
var nd = "CMCD";
function rd(e, t = {}) {
	return e ? Su($u(e, t), { whitespace: !1 }) : "";
}
function id(e, t = {}) {
	if (!e) return "";
	let n = rd(e, t);
	return encodeURIComponent(n);
}
function ad(e, t = {}) {
	return e ? `${nd}=${id(e, t)}` : "";
}
var od = /CMCD=[^&#]+/;
function sd(e, t, n) {
	let r = ad(t, n);
	return r ? od.test(e) ? e.replace(od, r) : `${e}${e.includes("?") ? "&" : "?"}${r}` : e;
}
var cd = class {
	constructor(e) {
		this.hls = void 0, this.config = void 0, this.media = void 0, this.sid = void 0, this.cid = void 0, this.useHeaders = !1, this.includeKeys = void 0, this.initialized = !1, this.starved = !1, this.buffering = !0, this.audioBuffer = void 0, this.videoBuffer = void 0, this.onWaiting = () => {
			this.initialized && (this.starved = !0), this.buffering = !0;
		}, this.onPlaying = () => {
			this.initialized ||= !0, this.buffering = !1;
		}, this.applyPlaylistData = (e) => {
			try {
				this.apply(e, {
					ot: Hl.MANIFEST,
					su: !this.initialized
				});
			} catch (e) {
				this.hls.logger.warn("Could not generate manifest CMCD data.", e);
			}
		}, this.applyFragmentData = (e) => {
			try {
				let { frag: t, part: n } = e, r = this.hls.levels[t.level], i = this.getObjectType(t), a = {
					d: (n || t).duration * 1e3,
					ot: i
				};
				(i === Hl.VIDEO || i === Hl.AUDIO || i == Hl.MUXED) && (a.br = r.bitrate / 1e3, a.tb = this.getTopBandwidth(i) / 1e3, a.bl = this.getBufferLength(i));
				let o = n ? this.getNextPart(n) : this.getNextFrag(t);
				o != null && o.url && o.url !== t.url && (a.nor = o.url), this.apply(e, a);
			} catch (e) {
				this.hls.logger.warn("Could not generate segment CMCD data.", e);
			}
		}, this.hls = e;
		let t = this.config = e.config, { cmcd: n } = t;
		n != null && (t.pLoader = this.createPlaylistLoader(), t.fLoader = this.createFragmentLoader(), this.sid = n.sessionId || e.sessionId, this.cid = n.contentId, this.useHeaders = n.useHeaders === !0, this.includeKeys = n.includeKeys, this.registerListeners());
	}
	registerListeners() {
		let e = this.hls;
		e.on(q.MEDIA_ATTACHED, this.onMediaAttached, this), e.on(q.MEDIA_DETACHED, this.onMediaDetached, this), e.on(q.BUFFER_CREATED, this.onBufferCreated, this);
	}
	unregisterListeners() {
		let e = this.hls;
		e.off(q.MEDIA_ATTACHED, this.onMediaAttached, this), e.off(q.MEDIA_DETACHED, this.onMediaDetached, this), e.off(q.BUFFER_CREATED, this.onBufferCreated, this);
	}
	destroy() {
		this.unregisterListeners(), this.onMediaDetached(), this.hls = this.config = this.audioBuffer = this.videoBuffer = null, this.onWaiting = this.onPlaying = this.media = null;
	}
	onMediaAttached(e, t) {
		this.media = t.media, this.media.addEventListener("waiting", this.onWaiting), this.media.addEventListener("playing", this.onPlaying);
	}
	onMediaDetached() {
		this.media &&= (this.media.removeEventListener("waiting", this.onWaiting), this.media.removeEventListener("playing", this.onPlaying), null);
	}
	onBufferCreated(e, t) {
		this.audioBuffer = t.tracks.audio?.buffer, this.videoBuffer = t.tracks.video?.buffer;
	}
	createData() {
		return {
			v: 1,
			sf: Ul.HLS,
			sid: this.sid,
			cid: this.cid,
			pr: this.media?.playbackRate,
			mtp: this.hls.bandwidthEstimate / 1e3
		};
	}
	apply(e, t = {}) {
		Fn(t, this.createData());
		let n = t.ot === Hl.INIT || t.ot === Hl.VIDEO || t.ot === Hl.MUXED;
		this.starved && n && (t.bs = !0, t.su = !0, this.starved = !1), t.su ?? (t.su = this.buffering);
		let { includeKeys: r } = this;
		r && (t = Object.keys(t).reduce((e, n) => (r.includes(n) && (e[n] = t[n]), e), {}));
		let i = { baseUrl: e.url };
		this.useHeaders ? (e.headers ||= {}, td(e.headers, t, i)) : e.url = sd(e.url, t, i);
	}
	getNextFrag(e) {
		let t = this.hls.levels[e.level]?.details;
		if (t) {
			let n = e.sn - t.startSN;
			return t.fragments[n + 1];
		}
	}
	getNextPart(e) {
		var t;
		let { index: n, fragment: r } = e, i = (t = this.hls.levels[r.level]) == null || (t = t.details) == null ? void 0 : t.partList;
		if (i) {
			let { sn: e } = r;
			for (let t = i.length - 1; t >= 0; t--) {
				let r = i[t];
				if (r.index === n && r.fragment.sn === e) return i[t + 1];
			}
		}
	}
	getObjectType(e) {
		let { type: t } = e;
		if (t === "subtitle") return Hl.TIMED_TEXT;
		if (e.sn === "initSegment") return Hl.INIT;
		if (t === "audio") return Hl.AUDIO;
		if (t === "main") return this.hls.audioTracks.length ? Hl.VIDEO : Hl.MUXED;
	}
	getTopBandwidth(e) {
		let t = 0, n, r = this.hls;
		if (e === Hl.AUDIO) n = r.audioTracks;
		else {
			let e = r.maxAutoLevel, t = e > -1 ? e + 1 : r.levels.length;
			n = r.levels.slice(0, t);
		}
		return n.forEach((e) => {
			e.bitrate > t && (t = e.bitrate);
		}), t > 0 ? t : NaN;
	}
	getBufferLength(e) {
		let t = this.media, n = e === Hl.AUDIO ? this.audioBuffer : this.videoBuffer;
		return !n || !t ? NaN : Q.bufferInfo(n, t.currentTime, this.config.maxBufferHole).len * 1e3;
	}
	createPlaylistLoader() {
		let { pLoader: e } = this.config, t = this.applyPlaylistData, n = e || this.config.loader;
		return class {
			constructor(e) {
				this.loader = void 0, this.loader = new n(e);
			}
			get stats() {
				return this.loader.stats;
			}
			get context() {
				return this.loader.context;
			}
			destroy() {
				this.loader.destroy();
			}
			abort() {
				this.loader.abort();
			}
			load(e, n, r) {
				t(e), this.loader.load(e, n, r);
			}
		};
	}
	createFragmentLoader() {
		let { fLoader: e } = this.config, t = this.applyFragmentData, n = e || this.config.loader;
		return class {
			constructor(e) {
				this.loader = void 0, this.loader = new n(e);
			}
			get stats() {
				return this.loader.stats;
			}
			get context() {
				return this.loader.context;
			}
			destroy() {
				this.loader.destroy();
			}
			abort() {
				this.loader.abort();
			}
			load(e, n, r) {
				t(e), this.loader.load(e, n, r);
			}
		};
	}
}, ld = 3e5, ud = class extends Bn {
	constructor(e) {
		super("content-steering", e.logger), this.hls = void 0, this.loader = null, this.uri = null, this.pathwayId = ".", this._pathwayPriority = null, this.timeToLoad = 300, this.reloadTimer = -1, this.updated = 0, this.started = !1, this.enabled = !0, this.levels = null, this.audioTracks = null, this.subtitleTracks = null, this.penalizedPathways = {}, this.hls = e, this.registerListeners();
	}
	registerListeners() {
		let e = this.hls;
		e.on(q.MANIFEST_LOADING, this.onManifestLoading, this), e.on(q.MANIFEST_LOADED, this.onManifestLoaded, this), e.on(q.MANIFEST_PARSED, this.onManifestParsed, this), e.on(q.ERROR, this.onError, this);
	}
	unregisterListeners() {
		let e = this.hls;
		e && (e.off(q.MANIFEST_LOADING, this.onManifestLoading, this), e.off(q.MANIFEST_LOADED, this.onManifestLoaded, this), e.off(q.MANIFEST_PARSED, this.onManifestParsed, this), e.off(q.ERROR, this.onError, this));
	}
	pathways() {
		return (this.levels || []).reduce((e, t) => (e.indexOf(t.pathwayId) === -1 && e.push(t.pathwayId), e), []);
	}
	get pathwayPriority() {
		return this._pathwayPriority;
	}
	set pathwayPriority(e) {
		this.updatePathwayPriority(e);
	}
	startLoad() {
		if (this.started = !0, this.clearTimeout(), this.enabled && this.uri) {
			if (this.updated) {
				let e = this.timeToLoad * 1e3 - (performance.now() - this.updated);
				if (e > 0) {
					this.scheduleRefresh(this.uri, e);
					return;
				}
			}
			this.loadSteeringManifest(this.uri);
		}
	}
	stopLoad() {
		this.started = !1, this.loader &&= (this.loader.destroy(), null), this.clearTimeout();
	}
	clearTimeout() {
		this.reloadTimer !== -1 && (self.clearTimeout(this.reloadTimer), this.reloadTimer = -1);
	}
	destroy() {
		this.unregisterListeners(), this.stopLoad(), this.hls = null, this.levels = this.audioTracks = this.subtitleTracks = null;
	}
	removeLevel(e) {
		let t = this.levels;
		t && (this.levels = t.filter((t) => t !== e));
	}
	onManifestLoading() {
		this.stopLoad(), this.enabled = !0, this.timeToLoad = 300, this.updated = 0, this.uri = null, this.pathwayId = ".", this.levels = this.audioTracks = this.subtitleTracks = null;
	}
	onManifestLoaded(e, t) {
		let { contentSteering: n } = t;
		n !== null && (this.pathwayId = n.pathwayId, this.uri = n.uri, this.started && this.startLoad());
	}
	onManifestParsed(e, t) {
		this.audioTracks = t.audioTracks, this.subtitleTracks = t.subtitleTracks;
	}
	onError(e, t) {
		let { errorAction: n } = t;
		if (n?.action === fa.SendAlternateToPenaltyBox && n.flags === pa.MoveAllAlternatesMatchingHost) {
			let e = this.levels, r = this._pathwayPriority, i = this.pathwayId;
			if (t.context) {
				let { groupId: n, pathwayId: r, type: a } = t.context;
				n && e ? i = this.getPathwayForGroupId(n, a, i) : r && (i = r);
			}
			i in this.penalizedPathways || (this.penalizedPathways[i] = performance.now()), !r && e && (r = this.pathways()), r && r.length > 1 && (this.updatePathwayPriority(r), n.resolved = this.pathwayId !== i), t.details === K.BUFFER_APPEND_ERROR && !t.fatal ? n.resolved = !0 : n.resolved || this.warn(`Could not resolve ${t.details} ("${t.error.message}") with content-steering for Pathway: ${i} levels: ${e && e.length} priorities: ${Fi(r)} penalized: ${Fi(this.penalizedPathways)}`);
		}
	}
	filterParsedLevels(e) {
		this.levels = e;
		let t = this.getLevelsForPathway(this.pathwayId);
		if (t.length === 0) {
			let n = e[0].pathwayId;
			this.log(`No levels found in Pathway ${this.pathwayId}. Setting initial Pathway to "${n}"`), t = this.getLevelsForPathway(n), this.pathwayId = n;
		}
		return t.length !== e.length && this.log(`Found ${t.length}/${e.length} levels in Pathway "${this.pathwayId}"`), t;
	}
	getLevelsForPathway(e) {
		return this.levels === null ? [] : this.levels.filter((t) => e === t.pathwayId);
	}
	updatePathwayPriority(e) {
		this._pathwayPriority = e;
		let t, n = this.penalizedPathways, r = performance.now();
		Object.keys(n).forEach((e) => {
			r - n[e] > ld && delete n[e];
		});
		for (let r = 0; r < e.length; r++) {
			let i = e[r];
			if (i in n) continue;
			if (i === this.pathwayId) return;
			let a = this.hls.nextLoadLevel, o = this.hls.levels[a];
			if (t = this.getLevelsForPathway(i), t.length > 0) {
				this.log(`Setting Pathway to "${i}"`), this.pathwayId = i, ns(t), this.hls.trigger(q.LEVELS_UPDATED, { levels: t });
				let e = this.hls.levels[a];
				o && e && this.levels && (e.attrs["STABLE-VARIANT-ID"] !== o.attrs["STABLE-VARIANT-ID"] && e.bitrate !== o.bitrate && this.log(`Unstable Pathways change from bitrate ${o.bitrate} to ${e.bitrate}`), this.hls.nextLoadLevel = a);
				break;
			}
		}
	}
	getPathwayForGroupId(e, t, n) {
		let r = this.getLevelsForPathway(n).concat(this.levels || []);
		for (let n = 0; n < r.length; n++) if (t === J.AUDIO_TRACK && r[n].hasAudioGroup(e) || t === J.SUBTITLE_TRACK && r[n].hasSubtitleGroup(e)) return r[n].pathwayId;
		return n;
	}
	clonePathways(e) {
		let t = this.levels;
		if (!t) return;
		let n = {}, r = {};
		e.forEach((e) => {
			let { ID: i, "BASE-ID": a, "URI-REPLACEMENT": o } = e;
			if (t.some((e) => e.pathwayId === i)) return;
			let s = this.getLevelsForPathway(a).map((e) => {
				let t = new Ka(e.attrs);
				t["PATHWAY-ID"] = i;
				let a = t.AUDIO && `${t.AUDIO}_clone_${i}`, s = t.SUBTITLES && `${t.SUBTITLES}_clone_${i}`;
				a && (n[t.AUDIO] = a, t.AUDIO = a), s && (r[t.SUBTITLES] = s, t.SUBTITLES = s);
				let c = fd(e.uri, t["STABLE-VARIANT-ID"], "PER-VARIANT-URIS", o), l = new Ai({
					attrs: t,
					audioCodec: e.audioCodec,
					bitrate: e.bitrate,
					height: e.height,
					name: e.name,
					url: c,
					videoCodec: e.videoCodec,
					width: e.width
				});
				if (e.audioGroups) for (let t = 1; t < e.audioGroups.length; t++) l.addGroupId("audio", `${e.audioGroups[t]}_clone_${i}`);
				if (e.subtitleGroups) for (let t = 1; t < e.subtitleGroups.length; t++) l.addGroupId("text", `${e.subtitleGroups[t]}_clone_${i}`);
				return l;
			});
			t.push(...s), dd(this.audioTracks, n, o, i), dd(this.subtitleTracks, r, o, i);
		});
	}
	loadSteeringManifest(e) {
		let t = this.hls.config, n = t.loader;
		this.loader && this.loader.destroy(), this.loader = new n(t);
		let r;
		try {
			r = new self.URL(e);
		} catch {
			this.enabled = !1, this.log(`Failed to parse Steering Manifest URI: ${e}`);
			return;
		}
		if (r.protocol !== "data:") {
			let e = (this.hls.bandwidthEstimate || t.abrEwmaDefaultEstimate) | 0;
			r.searchParams.set("_HLS_pathway", this.pathwayId), r.searchParams.set("_HLS_throughput", "" + e);
		}
		let i = {
			responseType: "json",
			url: r.href
		}, a = t.steeringManifestLoadPolicy.default, o = a.errorRetry || a.timeoutRetry || {}, s = {
			loadPolicy: a,
			timeout: a.maxLoadTimeMs,
			maxRetry: o.maxNumRetry || 0,
			retryDelay: o.retryDelayMs || 0,
			maxRetryDelay: o.maxRetryDelayMs || 0
		};
		this.log(`Requesting steering manifest: ${r}`), this.loader.load(i, s, {
			onSuccess: (e, t, n, i) => {
				this.log(`Loaded steering manifest: "${r}"`);
				let a = e.data;
				if (a?.VERSION !== 1) {
					this.log(`Steering VERSION ${a.VERSION} not supported!`);
					return;
				}
				this.updated = performance.now(), this.timeToLoad = a.TTL;
				let { "RELOAD-URI": o, "PATHWAY-CLONES": s, "PATHWAY-PRIORITY": c } = a;
				if (o) try {
					this.uri = new self.URL(o, r).href;
				} catch {
					this.enabled = !1, this.log(`Failed to parse Steering Manifest RELOAD-URI: ${o}`);
					return;
				}
				this.scheduleRefresh(this.uri || n.url), s && this.clonePathways(s);
				let l = {
					steeringManifest: a,
					url: r.toString()
				};
				this.hls.trigger(q.STEERING_MANIFEST_LOADED, l), c && this.updatePathwayPriority(c);
			},
			onError: (e, t, n, r) => {
				if (this.log(`Error loading steering manifest: ${e.code} ${e.text} (${t.url})`), this.stopLoad(), e.code === 410) {
					this.enabled = !1, this.log(`Steering manifest ${t.url} no longer available`);
					return;
				}
				let i = this.timeToLoad * 1e3;
				if (e.code === 429) {
					let e = this.loader;
					if (typeof e?.getResponseHeader == "function") {
						let t = e.getResponseHeader("Retry-After");
						t && (i = parseFloat(t) * 1e3);
					}
					this.log(`Steering manifest ${t.url} rate limited`);
				} else this.scheduleRefresh(this.uri || t.url, i);
			},
			onTimeout: (e, t, n) => {
				this.log(`Timeout loading steering manifest (${t.url})`), this.scheduleRefresh(this.uri || t.url);
			}
		});
	}
	scheduleRefresh(e, t = this.timeToLoad * 1e3) {
		this.clearTimeout(), this.reloadTimer = self.setTimeout(() => {
			let t = this.hls?.media;
			t && !t.ended ? this.loadSteeringManifest(e) : this.scheduleRefresh(e, this.timeToLoad * 1e3);
		}, t);
	}
};
function dd(e, t, n, r) {
	e && Object.keys(t).forEach((i) => {
		let a = e.filter((e) => e.groupId === i).map((e) => {
			let a = Fn({}, e);
			return a.details = void 0, a.attrs = new Ka(a.attrs), a.url = a.attrs.URI = fd(e.url, e.attrs["STABLE-RENDITION-ID"], "PER-RENDITION-URIS", n), a.groupId = a.attrs["GROUP-ID"] = t[i], a.attrs["PATHWAY-ID"] = r, a;
		});
		e.push(...a);
	});
}
function fd(e, t, n, r) {
	let { HOST: i, PARAMS: a, [n]: o } = r, s;
	t && (s = o?.[t], s && (e = s));
	let c = new self.URL(e);
	return i && !s && (c.host = i), a && Object.keys(a).sort().forEach((e) => {
		e && c.searchParams.set(e, a[e]);
	}), c.href;
}
var pd = class e extends Bn {
	constructor(t) {
		super("eme", t.logger), this.hls = void 0, this.config = void 0, this.media = null, this.mediaResolved = void 0, this.keyFormatPromise = null, this.keySystemAccessPromises = {}, this._requestLicenseFailureCount = 0, this.mediaKeySessions = [], this.keyIdToKeySessionPromise = {}, this.mediaKeys = null, this.setMediaKeysQueue = e.CDMCleanupPromise ? [e.CDMCleanupPromise] : [], this.bannedKeyIds = {}, this.onMediaEncrypted = (e) => {
			let { initDataType: t, initData: n } = e, r = `"${e.type}" event: init data type: "${t}"`;
			if (this.debug(r), n !== null) {
				if (!this.keyFormatPromise) {
					let e = Object.keys(this.keySystemAccessPromises);
					e.length || (e = mo(this.config));
					let t = e.map(po).filter((e) => !!e);
					this.keyFormatPromise = this.getKeyFormatPromise(t);
				}
				this.keyFormatPromise.then((i) => {
					let a = fo(i);
					if (t !== "sinf" || a !== lo.FAIRPLAY) {
						this.log(`Ignoring "${e.type}" event with init data type: "${t}" for selected key-system ${a}`);
						return;
					}
					let o;
					try {
						let e = _r(new Uint8Array(n)), t = Nr(ro(JSON.parse(e).sinf));
						if (!t) throw Error("'schm' box missing or not cbcs/cenc with schi > tenc");
						o = new Uint8Array(t.subarray(8, 24));
					} catch (e) {
						this.warn(`${r} Failed to parse sinf: ${e}`);
						return;
					}
					let s = $n(o), { keyIdToKeySessionPromise: c, mediaKeySessions: l } = this, u = c[s];
					for (let e = 0; e < l.length; e++) {
						let r = l[e], i = r.decryptdata;
						if (!i.keyId) continue;
						let a = $n(i.keyId);
						if ($a(o, i.keyId) || i.uri.replace(/-/g, "").indexOf(s) !== -1) {
							if (u = c[a], !u) continue;
							if (i.pssh) break;
							delete c[a], i.pssh = new Uint8Array(n), i.keyId = o, u = c[s] = u.then(() => this.generateRequestWithPreferredKeySession(r, t, n, "encrypted-event-key-match")), u.catch((e) => this.handleError(e));
							break;
						}
					}
					u || this.handleError(/* @__PURE__ */ Error(`Key ID ${s} not encountered in playlist. Key-system sessions ${l.length}.`));
				}).catch((e) => this.handleError(e));
			}
		}, this.onWaitingForKey = (e) => {
			this.log(`"${e.type}" event`);
		}, this.hls = t, this.config = t.config, this.registerListeners();
	}
	destroy() {
		this.onDestroying(), this.onMediaDetached();
		let e = this.config;
		e.requestMediaKeySystemAccessFunc = null, e.licenseXhrSetup = e.licenseResponseCallback = void 0, e.drmSystems = e.drmSystemOptions = {}, this.hls = this.config = this.keyIdToKeySessionPromise = null, this.onMediaEncrypted = this.onWaitingForKey = null;
	}
	registerListeners() {
		this.hls.on(q.MEDIA_ATTACHED, this.onMediaAttached, this), this.hls.on(q.MEDIA_DETACHED, this.onMediaDetached, this), this.hls.on(q.MANIFEST_LOADING, this.onManifestLoading, this), this.hls.on(q.MANIFEST_LOADED, this.onManifestLoaded, this), this.hls.on(q.DESTROYING, this.onDestroying, this);
	}
	unregisterListeners() {
		this.hls.off(q.MEDIA_ATTACHED, this.onMediaAttached, this), this.hls.off(q.MEDIA_DETACHED, this.onMediaDetached, this), this.hls.off(q.MANIFEST_LOADING, this.onManifestLoading, this), this.hls.off(q.MANIFEST_LOADED, this.onManifestLoaded, this), this.hls.off(q.DESTROYING, this.onDestroying, this);
	}
	getLicenseServerUrl(e) {
		let { drmSystems: t, widevineLicenseUrl: n } = this.config, r = t?.[e];
		if (r) return r.licenseUrl;
		if (e === lo.WIDEVINE && n) return n;
	}
	getLicenseServerUrlOrThrow(e) {
		let t = this.getLicenseServerUrl(e);
		if (t === void 0) throw Error(`no license server URL configured for key-system "${e}"`);
		return t;
	}
	getServerCertificateUrl(e) {
		let { drmSystems: t } = this.config, n = t?.[e];
		if (n) return n.serverCertificateUrl;
		this.log(`No Server Certificate in config.drmSystems["${e}"]`);
	}
	attemptKeySystemAccess(e) {
		let t = this.hls.levels, n = (e, t, n) => !!e && n.indexOf(e) === t, r = t.map((e) => e.audioCodec).filter(n), i = t.map((e) => e.videoCodec).filter(n);
		return r.length + i.length === 0 && i.push("avc1.42e01e"), new Promise((t, n) => {
			let a = (e) => {
				let o = e.shift();
				this.getMediaKeysPromise(o, r, i).then((e) => t({
					keySystem: o,
					mediaKeys: e
				})).catch((t) => {
					e.length ? a(e) : t instanceof gd ? n(t) : n(new gd({
						type: G.KEY_SYSTEM_ERROR,
						details: K.KEY_SYSTEM_NO_ACCESS,
						error: t,
						fatal: !0
					}, t.message));
				});
			};
			a(e);
		});
	}
	requestMediaKeySystemAccess(e, t) {
		let { requestMediaKeySystemAccessFunc: n } = this.config;
		if (typeof n != "function") {
			let e = `Configured requestMediaKeySystemAccess is not a function ${n}`;
			return ho === null && self.location.protocol === "http:" && (e = `navigator.requestMediaKeySystemAccess is not available over insecure protocol ${location.protocol}`), Promise.reject(Error(e));
		}
		return n(e, t);
	}
	getMediaKeysPromise(e, t, n) {
		let r = go(e, t, n, this.config.drmSystemOptions || {}), i = this.keySystemAccessPromises[e], a = i?.keySystemAccess;
		if (!a) {
			this.log(`Requesting encrypted media "${e}" key-system access with config: ${Fi(r)}`), a = this.requestMediaKeySystemAccess(e, r);
			let t = i = this.keySystemAccessPromises[e] = { keySystemAccess: a };
			return a.catch((t) => {
				this.log(`Failed to obtain access to key-system "${e}": ${t}`);
			}), a.then((n) => {
				this.log(`Access for key-system "${n.keySystem}" obtained`);
				let r = this.fetchServerCertificate(e);
				this.log(`Create media-keys for "${e}"`);
				let i = t.mediaKeys = n.createMediaKeys().then((n) => (this.log(`Media-keys created for "${e}"`), t.hasMediaKeys = !0, r.then((t) => t ? this.setMediaKeysServerCertificate(n, e, t) : n)));
				return i.catch((t) => {
					this.error(`Failed to create media-keys for "${e}"}: ${t}`);
				}), i;
			});
		}
		return a.then(() => i.mediaKeys);
	}
	createMediaKeySessionContext({ decryptdata: e, keySystem: t, mediaKeys: n }) {
		this.log(`Creating key-system session "${t}" keyId: ${$n(e.keyId || [])} keyUri: ${e.uri}`);
		let r = {
			decryptdata: e,
			keySystem: t,
			mediaKeys: n,
			mediaKeysSession: n.createSession(),
			keyStatus: "status-pending"
		};
		return this.mediaKeySessions.push(r), r;
	}
	renewKeySession(e) {
		let t = e.decryptdata;
		if (t.pssh) {
			let n = this.createMediaKeySessionContext(e), r = md(t);
			this.keyIdToKeySessionPromise[r] = this.generateRequestWithPreferredKeySession(n, "cenc", t.pssh.buffer, "expired");
		} else this.warn("Could not renew expired session. Missing pssh initData.");
		this.removeSession(e);
	}
	updateKeySession(e, t) {
		let n = e.mediaKeysSession;
		return this.log(`Updating key-session "${n.sessionId}" for keyId ${$n(e.decryptdata.keyId || [])}
      } (data length: ${t.byteLength})`), n.update(t);
	}
	getSelectedKeySystemFormats() {
		return Object.keys(this.keySystemAccessPromises).map((e) => ({
			keySystem: e,
			hasMediaKeys: this.keySystemAccessPromises[e].hasMediaKeys
		})).filter(({ hasMediaKeys: e }) => !!e).map(({ keySystem: e }) => po(e)).filter((e) => !!e);
	}
	getKeySystemAccess(e) {
		return this.getKeySystemSelectionPromise(e).then(({ keySystem: e, mediaKeys: t }) => this.attemptSetMediaKeys(e, t));
	}
	selectKeySystem(e) {
		return new Promise((t, n) => {
			this.getKeySystemSelectionPromise(e).then(({ keySystem: e }) => {
				let r = po(e);
				r ? t(r) : n(/* @__PURE__ */ Error(`Unable to find format for key-system "${e}"`));
			}).catch(n);
		});
	}
	selectKeySystemFormat(e) {
		let t = Object.keys(e.levelkeys || {});
		return this.keyFormatPromise ||= (this.log(`Selecting key-system from fragment (sn: ${e.sn} ${e.type}: ${e.level}) key formats ${t.join(", ")}`), this.getKeyFormatPromise(t)), this.keyFormatPromise;
	}
	getKeyFormatPromise(e) {
		let t = mo(this.config), n = e.map(fo).filter((e) => !!e && t.indexOf(e) !== -1);
		return this.selectKeySystem(n);
	}
	getKeyStatus(e) {
		let { mediaKeySessions: t } = this;
		for (let n = 0; n < t.length; n++) {
			let r = hd(e, t[n]);
			if (r) return r;
		}
	}
	loadKey(e) {
		let t = e.keyInfo.decryptdata, n = md(t), r = this.bannedKeyIds[n];
		if (r || this.getKeyStatus(t) === "internal-error") {
			let n = _d(r || "internal-error", t);
			return this.handleError(n, e.frag), Promise.reject(n);
		}
		let i = `(keyId: ${n} format: "${t.keyFormat}" method: ${t.method} uri: ${t.uri})`;
		this.log(`Starting session for key ${i}`);
		let a = this.keyIdToKeySessionPromise[n];
		if (!a) {
			let r = this.getKeySystemForKeyPromise(t).then(({ keySystem: n, mediaKeys: r }) => (this.throwIfDestroyed(), this.log(`Handle encrypted media sn: ${e.frag.sn} ${e.frag.type}: ${e.frag.level} using key ${i}`), this.attemptSetMediaKeys(n, r).then(() => (this.throwIfDestroyed(), this.createMediaKeySessionContext({
				keySystem: n,
				mediaKeys: r,
				decryptdata: t
			}))))).then((e) => {
				let n = t.pssh ? t.pssh.buffer : null;
				return this.generateRequestWithPreferredKeySession(e, "cenc", n, "playlist-key");
			});
			return r.catch((t) => this.handleError(t, e.frag)), this.keyIdToKeySessionPromise[n] = r, r;
		}
		return a.catch((n) => {
			if (n instanceof gd) {
				let r = Ln({}, n.data);
				this.getKeyStatus(t) === "internal-error" && (r.decryptdata = t);
				let i = new gd(r, n.message);
				this.handleError(i, e.frag);
			}
		}), a;
	}
	throwIfDestroyed(e = "Invalid state") {
		if (!this.hls) throw Error("invalid state");
	}
	handleError(e, t) {
		if (this.hls) {
			if (e instanceof gd) {
				t && (e.data.frag = t);
				let n = e.data.decryptdata;
				this.error(`${e.message}${n ? ` (${$n(n.keyId || [])})` : ""}`), this.hls.trigger(q.ERROR, e.data);
			} else this.error(e.message), this.hls.trigger(q.ERROR, {
				type: G.KEY_SYSTEM_ERROR,
				details: K.KEY_SYSTEM_NO_KEYS,
				error: e,
				fatal: !0
			});
		}
	}
	getKeySystemForKeyPromise(e) {
		let t = md(e), n = this.keyIdToKeySessionPromise[t];
		if (!n) {
			let t = fo(e.keyFormat), n = t ? [t] : mo(this.config);
			return this.attemptKeySystemAccess(n);
		}
		return n;
	}
	getKeySystemSelectionPromise(e) {
		if (e.length || (e = mo(this.config)), e.length === 0) throw new gd({
			type: G.KEY_SYSTEM_ERROR,
			details: K.KEY_SYSTEM_NO_CONFIGURED_LICENSE,
			fatal: !0
		}, `Missing key-system license configuration options ${Fi({ drmSystems: this.config.drmSystems })}`);
		return this.attemptKeySystemAccess(e);
	}
	attemptSetMediaKeys(e, t) {
		if (this.mediaResolved = void 0, this.mediaKeys === t) return Promise.resolve();
		let n = this.setMediaKeysQueue.slice();
		this.log(`Setting media-keys for "${e}"`);
		let r = Promise.all(n).then(() => this.media ? this.media.setMediaKeys(t) : new Promise((e, n) => {
			this.mediaResolved = () => {
				if (this.mediaResolved = void 0, !this.media) return n(/* @__PURE__ */ Error("Attempted to set mediaKeys without media element attached"));
				this.mediaKeys = t, this.media.setMediaKeys(t).then(e).catch(n);
			};
		}));
		return this.mediaKeys = t, this.setMediaKeysQueue.push(r), r.then(() => {
			this.log(`Media-keys set for "${e}"`), n.push(r), this.setMediaKeysQueue = this.setMediaKeysQueue.filter((e) => n.indexOf(e) === -1);
		});
	}
	generateRequestWithPreferredKeySession(e, t, n, r) {
		var i;
		let a = (i = this.config.drmSystems) == null || (i = i[e.keySystem]) == null ? void 0 : i.generateRequest;
		if (a) try {
			let r = a.call(this.hls, t, n, e);
			if (!r) throw Error("Invalid response from configured generateRequest filter");
			t = r.initDataType, n = r.initData ? r.initData : null, e.decryptdata.pssh = n ? new Uint8Array(n) : null;
		} catch (e) {
			if (this.warn(e.message), this.hls && this.hls.config.debug) throw e;
		}
		if (n === null) return this.log(`Skipping key-session request for "${r}" (no initData)`), Promise.resolve(e);
		let o = md(e.decryptdata), s = e.decryptdata.uri;
		this.log(`Generating key-session request for "${r}" keyId: ${o} URI: ${s} (init data type: ${t} length: ${n.byteLength})`);
		let c = new Ss(), l = e._onmessage = (t) => {
			let n = e.mediaKeysSession;
			if (!n) {
				c.emit("error", /* @__PURE__ */ Error("invalid state"));
				return;
			}
			let { messageType: r, message: i } = t;
			this.log(`"${r}" message event for session "${n.sessionId}" message size: ${i.byteLength}`), r === "license-request" || r === "license-renewal" ? this.renewLicense(e, i).catch((e) => {
				c.eventNames().length ? c.emit("error", e) : this.handleError(e);
			}) : r === "license-release" ? e.keySystem === lo.FAIRPLAY && this.updateKeySession(e, io("acknowledged")).then(() => this.removeSession(e)).catch((e) => this.handleError(e)) : this.warn(`unhandled media key message type "${r}"`);
		}, u = (e, t) => {
			t.keyStatus = e;
			let n;
			e.startsWith("usable") ? c.emit("resolved") : e === "internal-error" || e === "output-restricted" || e === "output-downscaled" ? n = _d(e, t.decryptdata) : e === "expired" ? n = /* @__PURE__ */ Error(`key expired (keyId: ${o})`) : e === "released" ? n = /* @__PURE__ */ Error("key released") : e === "status-pending" || this.warn(`unhandled key status change "${e}" (keyId: ${o})`), n && (c.eventNames().length ? c.emit("error", n) : this.handleError(n));
		}, d = e._onkeystatuseschange = (t) => {
			if (!e.mediaKeysSession) {
				c.emit("error", /* @__PURE__ */ Error("invalid state"));
				return;
			}
			let n = this.getKeyStatuses(e);
			if (!Object.keys(n).some((e) => n[e] !== "status-pending")) return;
			if (n[o] === "expired") {
				this.log(`Expired key ${Fi(n)} in key-session "${e.mediaKeysSession.sessionId}"`), this.renewKeySession(e);
				return;
			}
			let r = n[o];
			if (r) u(r, e);
			else {
				var i;
				let t = 1e3;
				e.keyStatusTimeouts ||= {}, (i = e.keyStatusTimeouts)[o] || (i[o] = self.setTimeout(() => {
					if (!e.mediaKeysSession || !this.mediaKeys) return;
					let n = this.getKeyStatus(e.decryptdata);
					if (n && n !== "status-pending") return this.log(`No status for keyId ${o} in key-session "${e.mediaKeysSession.sessionId}". Using session key-status ${n} from other session.`), u(n, e);
					this.log(`key status for ${o} in key-session "${e.mediaKeysSession.sessionId}" timed out after ${t}ms`), r = "internal-error", u(r, e);
				}, t)), this.log(`No status for keyId ${o} (${Fi(n)}).`);
			}
		};
		fs(e.mediaKeysSession, "message", l), fs(e.mediaKeysSession, "keystatuseschange", d);
		let f = new Promise((e, t) => {
			c.on("error", t), c.on("resolved", e);
		});
		return e.mediaKeysSession.generateRequest(t, n).then(() => {
			this.log(`Request generated for key-session "${e.mediaKeysSession.sessionId}" keyId: ${o} URI: ${s}`);
		}).catch((t) => {
			throw new gd({
				type: G.KEY_SYSTEM_ERROR,
				details: K.KEY_SYSTEM_NO_SESSION,
				error: t,
				decryptdata: e.decryptdata,
				fatal: !1
			}, `Error generating key-session request: ${t}`);
		}).then(() => f).catch((t) => (c.removeAllListeners(), this.removeSession(e).then(() => {
			throw t;
		}))).then(() => (c.removeAllListeners(), e));
	}
	getKeyStatuses(e) {
		let t = {};
		return e.mediaKeysSession.keyStatuses.forEach((n, r) => {
			if (typeof r == "string" && typeof n == "object") {
				let e = r;
				r = n, n = e;
			}
			let i = "buffer" in r ? new Uint8Array(r.buffer, r.byteOffset, r.byteLength) : new Uint8Array(r);
			if (e.keySystem === lo.PLAYREADY && i.length === 16) {
				let e = $n(i);
				t[e] = n, oo(i);
			}
			let a = $n(i);
			n === "internal-error" && (this.bannedKeyIds[a] = n), this.log(`key status change "${n}" for keyStatuses keyId: ${a} key-session "${e.mediaKeysSession.sessionId}"`), t[a] = n;
		}), t;
	}
	fetchServerCertificate(e) {
		let t = this.config, n = t.loader, r = new n(t), i = this.getServerCertificateUrl(e);
		return i ? (this.log(`Fetching server certificate for "${e}"`), new Promise((n, a) => {
			let o = {
				responseType: "arraybuffer",
				url: i
			}, s = t.certLoadPolicy.default, c = {
				loadPolicy: s,
				timeout: s.maxLoadTimeMs,
				maxRetry: 0,
				retryDelay: 0,
				maxRetryDelay: 0
			};
			r.load(o, c, {
				onSuccess: (e, t, r, i) => {
					n(e.data);
				},
				onError: (t, n, r, s) => {
					a(new gd({
						type: G.KEY_SYSTEM_ERROR,
						details: K.KEY_SYSTEM_SERVER_CERTIFICATE_REQUEST_FAILED,
						fatal: !0,
						networkDetails: r,
						response: Ln({
							url: o.url,
							data: void 0
						}, t)
					}, `"${e}" certificate request failed (${i}). Status: ${t.code} (${t.text})`));
				},
				onTimeout: (t, n, r) => {
					a(new gd({
						type: G.KEY_SYSTEM_ERROR,
						details: K.KEY_SYSTEM_SERVER_CERTIFICATE_REQUEST_FAILED,
						fatal: !0,
						networkDetails: r,
						response: {
							url: o.url,
							data: void 0
						}
					}, `"${e}" certificate request timed out (${i})`));
				},
				onAbort: (e, t, n) => {
					a(/* @__PURE__ */ Error("aborted"));
				}
			});
		})) : Promise.resolve();
	}
	setMediaKeysServerCertificate(e, t, n) {
		return new Promise((r, i) => {
			e.setServerCertificate(n).then((i) => {
				this.log(`setServerCertificate ${i ? "success" : "not supported by CDM"} (${n.byteLength}) on "${t}"`), r(e);
			}).catch((e) => {
				i(new gd({
					type: G.KEY_SYSTEM_ERROR,
					details: K.KEY_SYSTEM_SERVER_CERTIFICATE_UPDATE_FAILED,
					error: e,
					fatal: !0
				}, e.message));
			});
		});
	}
	renewLicense(e, t) {
		return this.requestLicense(e, new Uint8Array(t)).then((t) => this.updateKeySession(e, new Uint8Array(t)).catch((t) => {
			throw new gd({
				type: G.KEY_SYSTEM_ERROR,
				details: K.KEY_SYSTEM_SESSION_UPDATE_FAILED,
				decryptdata: e.decryptdata,
				error: t,
				fatal: !1
			}, t.message);
		}));
	}
	unpackPlayReadyKeyMessage(e, t) {
		let n = String.fromCharCode.apply(null, new Uint16Array(t.buffer));
		if (!n.includes("PlayReadyKeyMessage")) return e.setRequestHeader("Content-Type", "text/xml; charset=utf-8"), t;
		let r = new DOMParser().parseFromString(n, "application/xml"), i = r.querySelectorAll("HttpHeader");
		if (i.length > 0) {
			let t;
			for (let n = 0, r = i.length; n < r; n++) {
				t = i[n];
				let r = t.querySelector("name")?.textContent, a = t.querySelector("value")?.textContent;
				r && a && e.setRequestHeader(r, a);
			}
		}
		let a = r.querySelector("Challenge")?.textContent;
		if (!a) throw Error("Cannot find <Challenge> in key message");
		return io(atob(a));
	}
	setupLicenseXHR(e, t, n, r) {
		let i = this.config.licenseXhrSetup;
		return i ? Promise.resolve().then(() => {
			if (!n.decryptdata) throw Error("Key removed");
			return i.call(this.hls, e, t, n, r);
		}).catch((a) => {
			if (!n.decryptdata) throw a;
			return e.open("POST", t, !0), i.call(this.hls, e, t, n, r);
		}).then((n) => (e.readyState || e.open("POST", t, !0), {
			xhr: e,
			licenseChallenge: n || r
		})) : (e.open("POST", t, !0), Promise.resolve({
			xhr: e,
			licenseChallenge: r
		}));
	}
	requestLicense(e, t) {
		let n = this.config.keyLoadPolicy.default;
		return new Promise((r, i) => {
			let a = this.getLicenseServerUrlOrThrow(e.keySystem);
			this.log(`Sending license request to URL: ${a}`);
			let o = new XMLHttpRequest();
			o.responseType = "arraybuffer", o.onreadystatechange = () => {
				if (!this.hls || !e.mediaKeysSession) return i(/* @__PURE__ */ Error("invalid state"));
				if (o.readyState === 4) {
					if (o.status === 200) {
						this._requestLicenseFailureCount = 0;
						let t = o.response;
						this.log(`License received ${t instanceof ArrayBuffer ? t.byteLength : t}`);
						let n = this.config.licenseResponseCallback;
						if (n) try {
							t = n.call(this.hls, o, a, e);
						} catch (e) {
							this.error(e);
						}
						r(t);
					} else {
						let s = n.errorRetry, c = s ? s.maxNumRetry : 0;
						if (this._requestLicenseFailureCount++, this._requestLicenseFailureCount > c || o.status >= 400 && o.status < 500) i(new gd({
							type: G.KEY_SYSTEM_ERROR,
							details: K.KEY_SYSTEM_LICENSE_REQUEST_FAILED,
							decryptdata: e.decryptdata,
							fatal: !0,
							networkDetails: o,
							response: {
								url: a,
								data: void 0,
								code: o.status,
								text: o.statusText
							}
						}, `License Request XHR failed (${a}). Status: ${o.status} (${o.statusText})`));
						else {
							let n = c - this._requestLicenseFailureCount + 1;
							this.warn(`Retrying license request, ${n} attempts left`), this.requestLicense(e, t).then(r, i);
						}
					}
				}
			}, e.licenseXhr && e.licenseXhr.readyState !== XMLHttpRequest.DONE && e.licenseXhr.abort(), e.licenseXhr = o, this.setupLicenseXHR(o, a, e, t).then(({ xhr: t, licenseChallenge: n }) => {
				e.keySystem == lo.PLAYREADY && (n = this.unpackPlayReadyKeyMessage(t, n)), t.send(n);
			}).catch(i);
		});
	}
	onDestroying() {
		this.unregisterListeners(), this._clear();
	}
	onMediaAttached(e, t) {
		if (!this.config.emeEnabled) return;
		let n = t.media;
		this.media = n, fs(n, "encrypted", this.onMediaEncrypted), fs(n, "waitingforkey", this.onWaitingForKey);
		let r = this.mediaResolved;
		r ? r() : this.mediaKeys = n.mediaKeys;
	}
	onMediaDetached() {
		let e = this.media;
		e && (ps(e, "encrypted", this.onMediaEncrypted), ps(e, "waitingforkey", this.onWaitingForKey), this.media = null, this.mediaKeys = null);
	}
	_clear() {
		var t;
		this._requestLicenseFailureCount = 0, this.keyIdToKeySessionPromise = {}, this.bannedKeyIds = {};
		let n = this.mediaResolved;
		if (n && n(), !this.mediaKeys && !this.mediaKeySessions.length) return;
		let r = this.media, i = this.mediaKeySessions.slice();
		this.mediaKeySessions = [], this.mediaKeys = null, xo.clearKeyUriToKeyIdMap();
		let a = i.length;
		e.CDMCleanupPromise = Promise.all(i.map((e) => this.removeSession(e)).concat((r == null || (t = r.setMediaKeys(null)) == null ? void 0 : t.catch((e) => {
			this.log(`Could not clear media keys: ${e}`), this.hls && this.hls.trigger(q.ERROR, {
				type: G.OTHER_ERROR,
				details: K.KEY_SYSTEM_DESTROY_MEDIA_KEYS_ERROR,
				fatal: !1,
				error: /* @__PURE__ */ Error(`Could not clear media keys: ${e}`)
			});
		})) || Promise.resolve())).catch((e) => {
			this.log(`Could not close sessions and clear media keys: ${e}`), this.hls && this.hls.trigger(q.ERROR, {
				type: G.OTHER_ERROR,
				details: K.KEY_SYSTEM_DESTROY_CLOSE_SESSION_ERROR,
				fatal: !1,
				error: /* @__PURE__ */ Error(`Could not close sessions and clear media keys: ${e}`)
			});
		}).then(() => {
			a && this.log("finished closing key sessions and clearing media keys");
		});
	}
	onManifestLoading() {
		this._clear();
	}
	onManifestLoaded(e, { sessionKeys: t }) {
		if (t && this.config.emeEnabled && !this.keyFormatPromise) {
			let e = t.reduce((e, t) => (e.indexOf(t.keyFormat) === -1 && e.push(t.keyFormat), e), []);
			this.log(`Selecting key-system from session-keys ${e.join(", ")}`), this.keyFormatPromise = this.getKeyFormatPromise(e);
		}
	}
	removeSession(e) {
		let { mediaKeysSession: t, licenseXhr: n, decryptdata: r } = e;
		if (t) {
			this.log(`Remove licenses and keys and close session "${t.sessionId}" keyId: ${$n(r?.keyId || [])}`), e._onmessage &&= (t.removeEventListener("message", e._onmessage), void 0), e._onkeystatuseschange &&= (t.removeEventListener("keystatuseschange", e._onkeystatuseschange), void 0), n && n.readyState !== XMLHttpRequest.DONE && n.abort(), e.mediaKeysSession = e.decryptdata = e.licenseXhr = void 0;
			let i = this.mediaKeySessions.indexOf(e);
			i > -1 && this.mediaKeySessions.splice(i, 1);
			let { keyStatusTimeouts: a } = e;
			a && Object.keys(a).forEach((e) => self.clearTimeout(a[e]));
			let { drmSystemOptions: o } = this.config;
			return (vo(o) ? new Promise((e, n) => {
				self.setTimeout(() => n(/* @__PURE__ */ Error("MediaKeySession.remove() timeout")), 8e3), t.remove().then(e).catch(n);
			}) : Promise.resolve()).catch((e) => {
				this.log(`Could not remove session: ${e}`), this.hls && this.hls.trigger(q.ERROR, {
					type: G.OTHER_ERROR,
					details: K.KEY_SYSTEM_DESTROY_REMOVE_SESSION_ERROR,
					fatal: !1,
					error: /* @__PURE__ */ Error(`Could not remove session: ${e}`)
				});
			}).then(() => t.close()).catch((e) => {
				this.log(`Could not close session: ${e}`), this.hls && this.hls.trigger(q.ERROR, {
					type: G.OTHER_ERROR,
					details: K.KEY_SYSTEM_DESTROY_CLOSE_SESSION_ERROR,
					fatal: !1,
					error: /* @__PURE__ */ Error(`Could not close session: ${e}`)
				});
			});
		}
		return Promise.resolve();
	}
};
pd.CDMCleanupPromise = void 0;
function md(e) {
	if (!e) throw Error("Could not read keyId of undefined decryptdata");
	if (e.keyId === null) throw Error("keyId is null");
	return $n(e.keyId);
}
function hd(e, t) {
	if (e.keyId && t.mediaKeysSession.keyStatuses.has(e.keyId)) return t.mediaKeysSession.keyStatuses.get(e.keyId);
	if (e.matches(t.decryptdata)) return t.keyStatus;
}
var gd = class extends Error {
	constructor(e, t) {
		super(t), this.data = void 0, e.error ||= Error(t), this.data = e, e.err = e.error;
	}
};
function _d(e, t) {
	let n = e === "output-restricted", r = n ? K.KEY_SYSTEM_STATUS_OUTPUT_RESTRICTED : K.KEY_SYSTEM_STATUS_INTERNAL_ERROR;
	return new gd({
		type: G.KEY_SYSTEM_ERROR,
		details: r,
		fatal: !1,
		decryptdata: t
	}, n ? "HDCP level output restricted" : `key status changed to "${e}"`);
}
var vd = class {
	constructor(e) {
		this.hls = void 0, this.isVideoPlaybackQualityAvailable = !1, this.timer = void 0, this.media = null, this.lastTime = void 0, this.lastDroppedFrames = 0, this.lastDecodedFrames = 0, this.streamController = void 0, this.hls = e, this.registerListeners();
	}
	setStreamController(e) {
		this.streamController = e;
	}
	registerListeners() {
		this.hls.on(q.MEDIA_ATTACHING, this.onMediaAttaching, this), this.hls.on(q.MEDIA_DETACHING, this.onMediaDetaching, this);
	}
	unregisterListeners() {
		this.hls.off(q.MEDIA_ATTACHING, this.onMediaAttaching, this), this.hls.off(q.MEDIA_DETACHING, this.onMediaDetaching, this);
	}
	destroy() {
		this.timer && clearInterval(this.timer), this.unregisterListeners(), this.isVideoPlaybackQualityAvailable = !1, this.media = null;
	}
	onMediaAttaching(e, t) {
		let n = this.hls.config;
		if (n.capLevelOnFPSDrop) {
			let e = t.media instanceof self.HTMLVideoElement ? t.media : null;
			this.media = e, e && typeof e.getVideoPlaybackQuality == "function" && (this.isVideoPlaybackQualityAvailable = !0), self.clearInterval(this.timer), this.timer = self.setInterval(this.checkFPSInterval.bind(this), n.fpsDroppedMonitoringPeriod);
		}
	}
	onMediaDetaching() {
		this.media = null;
	}
	checkFPS(e, t, n) {
		let r = performance.now();
		if (t) {
			if (this.lastTime) {
				let e = r - this.lastTime, i = n - this.lastDroppedFrames, a = t - this.lastDecodedFrames, o = 1e3 * i / e, s = this.hls;
				if (s.trigger(q.FPS_DROP, {
					currentDropped: i,
					currentDecoded: a,
					totalDroppedFrames: n
				}), o > 0 && i > s.config.fpsDroppedMonitoringThreshold * a) {
					let e = s.currentLevel;
					s.logger.warn("drop FPS ratio greater than max allowed value for currentLevel: " + e), e > 0 && (s.autoLevelCapping === -1 || s.autoLevelCapping >= e) && (--e, s.trigger(q.FPS_DROP_LEVEL_CAPPING, {
						level: e,
						droppedLevel: s.currentLevel
					}), s.autoLevelCapping = e, this.streamController.nextLevelSwitch());
				}
			}
			this.lastTime = r, this.lastDroppedFrames = n, this.lastDecodedFrames = t;
		}
	}
	checkFPSInterval() {
		let e = this.media;
		if (e) {
			if (this.isVideoPlaybackQualityAvailable) {
				let t = e.getVideoPlaybackQuality();
				this.checkFPS(e, t.totalVideoFrames, t.droppedVideoFrames);
			} else this.checkFPS(e, e.webkitDecodedFrameCount, e.webkitDroppedFrameCount);
		}
	}
};
function yd(e, t) {
	let n;
	try {
		n = new Event("addtrack");
	} catch {
		n = document.createEvent("Event"), n.initEvent("addtrack", !1, !1);
	}
	n.track = e, t.dispatchEvent(n);
}
function bd(e, t) {
	let n = e.mode;
	if (n === "disabled" && (e.mode = "hidden"), e.cues && !e.cues.getCueById(t.id)) try {
		if (e.addCue(t), !e.cues.getCueById(t.id)) throw Error(`addCue is failed for: ${t}`);
	} catch (n) {
		Jn.debug(`[texttrack-utils]: ${n}`);
		try {
			let n = new self.TextTrackCue(t.startTime, t.endTime, t.text);
			n.id = t.id, e.addCue(n);
		} catch (e) {
			Jn.debug(`[texttrack-utils]: Legacy TextTrackCue fallback failed: ${e}`);
		}
	}
	n === "disabled" && (e.mode = n);
}
function xd(e, t) {
	let n = e.mode;
	if (n === "disabled" && (e.mode = "hidden"), e.cues) for (let n = e.cues.length; n--;) t && e.cues[n].removeEventListener("enter", t), e.removeCue(e.cues[n]);
	n === "disabled" && (e.mode = n);
}
function Sd(e, t, n, r) {
	let i = e.mode;
	if (i === "disabled" && (e.mode = "hidden"), e.cues && e.cues.length > 0) {
		let i = wd(e.cues, t, n);
		for (let t = 0; t < i.length; t++) (!r || r(i[t])) && e.removeCue(i[t]);
	}
	i === "disabled" && (e.mode = i);
}
function Cd(e, t) {
	if (t <= e[0].startTime) return 0;
	let n = e.length - 1;
	if (t > e[n].endTime) return -1;
	let r = 0, i = n, a;
	for (; r <= i;) if (a = Math.floor((i + r) / 2), t < e[a].startTime) i = a - 1;
	else if (t > e[a].startTime && r < n) r = a + 1;
	else return a;
	return e[r].startTime - t < t - e[i].startTime ? r : i;
}
function wd(e, t, n) {
	let r = [], i = Cd(e, t);
	if (i > -1) for (let a = i, o = e.length; a < o; a++) {
		let i = e[a];
		if (i.startTime >= t && i.endTime <= n) r.push(i);
		else if (i.startTime > n) return r;
	}
	return r;
}
function Td(e) {
	let t = [];
	for (let n = 0; n < e.length; n++) {
		let r = e[n];
		(r.kind === "subtitles" || r.kind === "captions") && r.label && t.push(e[n]);
	}
	return t;
}
var Ed = class extends Ol {
	constructor(e) {
		super(e, "subtitle-track-controller"), this.media = null, this.tracks = [], this.groupIds = null, this.tracksInGroup = [], this.trackId = -1, this.currentTrack = null, this.selectDefaultTrack = !0, this.queuedDefaultTrack = -1, this.useTextTrackPolling = !1, this.subtitlePollingInterval = -1, this._subtitleDisplay = !0, this.asyncPollTrackChange = () => this.pollTrackChange(0), this.onTextTracksChanged = () => {
			if (this.useTextTrackPolling || self.clearInterval(this.subtitlePollingInterval), !this.media || !this.hls.config.renderTextTracksNatively) return;
			let e = null, t = Td(this.media.textTracks);
			for (let n = 0; n < t.length; n++) if (t[n].mode === "hidden") e = t[n];
			else if (t[n].mode === "showing") {
				e = t[n];
				break;
			}
			let n = this.findTrackForTextTrack(e);
			this.subtitleTrack !== n && this.setSubtitleTrack(n);
		}, this.registerListeners();
	}
	destroy() {
		this.unregisterListeners(), this.tracks.length = 0, this.tracksInGroup.length = 0, this.currentTrack = null, this.onTextTracksChanged = this.asyncPollTrackChange = null, super.destroy();
	}
	get subtitleDisplay() {
		return this._subtitleDisplay;
	}
	set subtitleDisplay(e) {
		this._subtitleDisplay = e, this.trackId > -1 && this.toggleTrackModes();
	}
	registerListeners() {
		let { hls: e } = this;
		e.on(q.MEDIA_ATTACHED, this.onMediaAttached, this), e.on(q.MEDIA_DETACHING, this.onMediaDetaching, this), e.on(q.MANIFEST_LOADING, this.onManifestLoading, this), e.on(q.MANIFEST_PARSED, this.onManifestParsed, this), e.on(q.LEVEL_LOADING, this.onLevelLoading, this), e.on(q.LEVEL_SWITCHING, this.onLevelSwitching, this), e.on(q.SUBTITLE_TRACK_LOADED, this.onSubtitleTrackLoaded, this), e.on(q.ERROR, this.onError, this);
	}
	unregisterListeners() {
		let { hls: e } = this;
		e.off(q.MEDIA_ATTACHED, this.onMediaAttached, this), e.off(q.MEDIA_DETACHING, this.onMediaDetaching, this), e.off(q.MANIFEST_LOADING, this.onManifestLoading, this), e.off(q.MANIFEST_PARSED, this.onManifestParsed, this), e.off(q.LEVEL_LOADING, this.onLevelLoading, this), e.off(q.LEVEL_SWITCHING, this.onLevelSwitching, this), e.off(q.SUBTITLE_TRACK_LOADED, this.onSubtitleTrackLoaded, this), e.off(q.ERROR, this.onError, this);
	}
	onMediaAttached(e, t) {
		this.media = t.media, this.media && (this.queuedDefaultTrack > -1 && (this.subtitleTrack = this.queuedDefaultTrack, this.queuedDefaultTrack = -1), this.useTextTrackPolling = !(this.media.textTracks && "onchange" in this.media.textTracks), this.useTextTrackPolling ? this.pollTrackChange(500) : this.media.textTracks.addEventListener("change", this.asyncPollTrackChange));
	}
	pollTrackChange(e) {
		self.clearInterval(this.subtitlePollingInterval), this.subtitlePollingInterval = self.setInterval(this.onTextTracksChanged, e);
	}
	onMediaDetaching(e, t) {
		let n = this.media;
		if (!n) return;
		let r = !!t.transferMedia;
		self.clearInterval(this.subtitlePollingInterval), this.useTextTrackPolling || n.textTracks.removeEventListener("change", this.asyncPollTrackChange), this.trackId > -1 && (this.queuedDefaultTrack = this.trackId), this.subtitleTrack = -1, this.media = null, r || Td(n.textTracks).forEach((e) => {
			xd(e);
		});
	}
	onManifestLoading() {
		this.tracks = [], this.groupIds = null, this.tracksInGroup = [], this.trackId = -1, this.currentTrack = null, this.selectDefaultTrack = !0;
	}
	onManifestParsed(e, t) {
		this.tracks = t.subtitleTracks;
	}
	onSubtitleTrackLoaded(e, t) {
		let { id: n, groupId: r, details: i } = t, a = this.tracksInGroup[n];
		if (!a || a.groupId !== r) {
			this.warn(`Subtitle track with id:${n} and group:${r} not found in active group ${a?.groupId}`);
			return;
		}
		let o = a.details;
		a.details = t.details, this.log(`Subtitle track ${n} "${a.name}" lang:${a.lang} group:${r} loaded [${i.startSN}-${i.endSN}]`), n === this.trackId && this.playlistLoaded(n, t, o);
	}
	onLevelLoading(e, t) {
		this.switchLevel(t.level);
	}
	onLevelSwitching(e, t) {
		this.switchLevel(t.level);
	}
	switchLevel(e) {
		let t = this.hls.levels[e];
		if (!t) return;
		let n = t.subtitleGroups || null, r = this.groupIds, i = this.currentTrack;
		if (!n || r?.length !== n?.length || n != null && n.some((e) => r?.indexOf(e) === -1)) {
			this.groupIds = n, this.trackId = -1, this.currentTrack = null;
			let e = this.tracks.filter((e) => !n || n.indexOf(e.groupId) !== -1);
			if (e.length) this.selectDefaultTrack && !e.some((e) => e.default) && (this.selectDefaultTrack = !1), e.forEach((e, t) => {
				e.id = t;
			});
			else if (!i && !this.tracksInGroup.length) return;
			this.tracksInGroup = e;
			let t = this.hls.config.subtitlePreference;
			if (!i && t) {
				this.selectDefaultTrack = !1;
				let n = Vi(t, e);
				if (n > -1) i = e[n];
				else {
					let e = Vi(t, this.tracks);
					i = this.tracks[e];
				}
			}
			let r = this.findTrackId(i);
			r === -1 && i && (r = this.findTrackId(null));
			let a = { subtitleTracks: e };
			this.log(`Updating subtitle tracks, ${e.length} track(s) found in "${n?.join(",")}" group-id`), this.hls.trigger(q.SUBTITLE_TRACKS_UPDATED, a), r !== -1 && this.trackId === -1 && this.setSubtitleTrack(r);
		}
	}
	findTrackId(e) {
		let t = this.tracksInGroup, n = this.selectDefaultTrack;
		for (let r = 0; r < t.length; r++) {
			let i = t[r];
			if (!(n && !i.default || !n && !e) && (!e || Hi(i, e))) return r;
		}
		if (e) {
			for (let n = 0; n < t.length; n++) {
				let r = t[n];
				if (Al(e.attrs, r.attrs, [
					"LANGUAGE",
					"ASSOC-LANGUAGE",
					"CHARACTERISTICS"
				])) return n;
			}
			for (let n = 0; n < t.length; n++) {
				let r = t[n];
				if (Al(e.attrs, r.attrs, ["LANGUAGE"])) return n;
			}
		}
		return -1;
	}
	findTrackForTextTrack(e) {
		if (e) {
			let t = this.tracksInGroup;
			for (let n = 0; n < t.length; n++) {
				let r = t[n];
				if (jl(r, e)) return n;
			}
		}
		return -1;
	}
	onError(e, t) {
		!t.fatal && t.context && (t.context.type !== J.SUBTITLE_TRACK || t.context.id !== this.trackId || this.groupIds && this.groupIds.indexOf(t.context.groupId) === -1 || this.checkRetry(t));
	}
	get allSubtitleTracks() {
		return this.tracks;
	}
	get subtitleTracks() {
		return this.tracksInGroup;
	}
	get subtitleTrack() {
		return this.trackId;
	}
	set subtitleTrack(e) {
		this.selectDefaultTrack = !1, this.setSubtitleTrack(e);
	}
	setSubtitleOption(e) {
		if (this.hls.config.subtitlePreference = e, e) {
			if (e.id === -1) return this.setSubtitleTrack(-1), null;
			let t = this.allSubtitleTracks;
			if (this.selectDefaultTrack = !1, t.length) {
				let n = this.currentTrack;
				if (n && Hi(e, n)) return n;
				let r = Vi(e, this.tracksInGroup);
				if (r > -1) {
					let e = this.tracksInGroup[r];
					return this.setSubtitleTrack(r), e;
				}
				if (n) return null;
				{
					let n = Vi(e, t);
					if (n > -1) return t[n];
				}
			}
		}
		return null;
	}
	loadPlaylist(e) {
		super.loadPlaylist(), this.shouldLoadPlaylist(this.currentTrack) && this.scheduleLoading(this.currentTrack, e);
	}
	loadingPlaylist(e, t) {
		super.loadingPlaylist(e, t);
		let n = e.id, r = e.groupId, i = this.getUrlWithDirectives(e.url, t), a = e.details, o = a?.age;
		this.log(`Loading subtitle ${n} "${e.name}" lang:${e.lang} group:${r}${t?.msn === void 0 ? "" : " at sn " + t.msn + " part " + t.part}${o && a.live ? " age " + o.toFixed(1) + (a.type && " " + a.type || "") : ""} ${i}`), this.hls.trigger(q.SUBTITLE_TRACK_LOADING, {
			url: i,
			id: n,
			groupId: r,
			deliveryDirectives: t || null,
			track: e
		});
	}
	toggleTrackModes() {
		let { media: e } = this;
		if (!e) return;
		let t = Td(e.textTracks), n = this.currentTrack, r;
		if (n && (r = t.filter((e) => jl(n, e))[0], r || this.warn(`Unable to find subtitle TextTrack with name "${n.name}" and language "${n.lang}"`)), [].slice.call(t).forEach((e) => {
			e.mode !== "disabled" && e !== r && (e.mode = "disabled");
		}), r) {
			let e = this.subtitleDisplay ? "showing" : "hidden";
			r.mode !== e && (r.mode = e);
		}
	}
	setSubtitleTrack(e) {
		let t = this.tracksInGroup;
		if (!this.media) {
			this.queuedDefaultTrack = e;
			return;
		}
		if (e < -1 || e >= t.length || !W(e)) {
			this.warn(`Invalid subtitle track id: ${e}`);
			return;
		}
		this.selectDefaultTrack = !1;
		let n = this.currentTrack, r = t[e] || null;
		if (this.trackId = e, this.currentTrack = r, this.toggleTrackModes(), !r) {
			this.hls.trigger(q.SUBTITLE_TRACK_SWITCH, { id: e });
			return;
		}
		let i = !!r.details && !r.details.live;
		if (e === this.trackId && r === n && i) return;
		this.log(`Switching to subtitle-track ${e}` + (r ? ` "${r.name}" lang:${r.lang} group:${r.groupId}` : ""));
		let { id: a, groupId: o = "", name: s, type: c, url: l } = r;
		this.hls.trigger(q.SUBTITLE_TRACK_SWITCH, {
			id: a,
			groupId: o,
			name: s,
			type: c,
			url: l
		});
		let u = this.switchParams(r.url, n?.details, r.details);
		this.loadPlaylist(u);
	}
};
function Dd() {
	try {
		return crypto.randomUUID();
	} catch {
		try {
			let e = URL.createObjectURL(new Blob()), t = e.toString();
			return URL.revokeObjectURL(e), t.slice(t.lastIndexOf("/") + 1);
		} catch {
			let e = (/* @__PURE__ */ new Date()).getTime();
			return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (t) => {
				let n = (e + Math.random() * 16) % 16 | 0;
				return e = Math.floor(e / 16), (t == "x" ? n : n & 3 | 8).toString(16);
			});
		}
	}
}
function Od(e) {
	let t = 5381, n = e.length;
	for (; n;) t = t * 33 ^ e.charCodeAt(--n);
	return (t >>> 0).toString();
}
var kd = .025, Ad = /*#__PURE__*/ function(e) {
	return e[e.Point = 0] = "Point", e[e.Range = 1] = "Range", e;
}({});
function jd(e, t, n) {
	return `${e.identifier}-${n + 1}-${Od(t)}`;
}
var Md = class {
	constructor(e, t) {
		this.base = void 0, this._duration = null, this._timelineStart = null, this.appendInPlaceDisabled = void 0, this.appendInPlaceStarted = void 0, this.dateRange = void 0, this.hasPlayed = !1, this.cumulativeDuration = 0, this.resumeOffset = NaN, this.playoutLimit = NaN, this.restrictions = {
			skip: !1,
			jump: !1
		}, this.snapOptions = {
			out: !1,
			in: !1
		}, this.assetList = [], this.assetListLoader = void 0, this.assetListResponse = null, this.resumeAnchor = void 0, this.error = void 0, this.resetOnResume = void 0, this.base = t, this.dateRange = e, this.setDateRange(e);
	}
	setDateRange(e) {
		this.dateRange = e, this.resumeOffset = e.attr.optionalFloat("X-RESUME-OFFSET", this.resumeOffset), this.playoutLimit = e.attr.optionalFloat("X-PLAYOUT-LIMIT", this.playoutLimit), this.restrictions = e.attr.enumeratedStringList("X-RESTRICT", this.restrictions), this.snapOptions = e.attr.enumeratedStringList("X-SNAP", this.snapOptions);
	}
	reset() {
		var e;
		this.appendInPlaceStarted = !1, (e = this.assetListLoader) == null || e.destroy(), this.assetListLoader = void 0, this.supplementsPrimary || (this.assetListResponse = null, this.assetList = [], this._duration = null);
	}
	isAssetPastPlayoutLimit(e) {
		if (e > 0 && e >= this.assetList.length) return !0;
		let t = this.playoutLimit;
		return e <= 0 || isNaN(t) ? !1 : t === 0 || (this.assetList[e]?.startOffset || 0) > t;
	}
	findAssetIndex(e) {
		return this.assetList.indexOf(e);
	}
	get identifier() {
		return this.dateRange.id;
	}
	get startDate() {
		return this.dateRange.startDate;
	}
	get startTime() {
		let e = this.dateRange.startTime;
		if (this.snapOptions.out) {
			let t = this.dateRange.tagAnchor;
			if (t) return Nd(e, t);
		}
		return e;
	}
	get startOffset() {
		return this.cue.pre ? 0 : this.startTime;
	}
	get startIsAligned() {
		if (this.startTime === 0 || this.snapOptions.out) return !0;
		let e = this.dateRange.tagAnchor;
		if (e) {
			let t = this.dateRange.startTime;
			return t - Nd(t, e) < .1;
		}
		return !1;
	}
	get resumptionOffset() {
		let e = this.resumeOffset, t = W(e) ? e : this.duration;
		return this.cumulativeDuration + t;
	}
	get resumeTime() {
		let e = this.startOffset + this.resumptionOffset;
		if (this.snapOptions.in) {
			let t = this.resumeAnchor;
			if (t) return Nd(e, t);
		}
		return e;
	}
	get appendInPlace() {
		return this.appendInPlaceStarted ? !0 : !this.appendInPlaceDisabled && !!(!this.cue.once && !this.cue.pre && this.startIsAligned && (isNaN(this.playoutLimit) && isNaN(this.resumeOffset) || this.resumeOffset && this.duration && Math.abs(this.resumeOffset - this.duration) < kd));
	}
	set appendInPlace(e) {
		this.appendInPlaceStarted ? this.resetOnResume = !e : this.appendInPlaceDisabled = !e;
	}
	get timelineStart() {
		return this._timelineStart === null ? this.startTime : this._timelineStart;
	}
	set timelineStart(e) {
		this._timelineStart = e;
	}
	get duration() {
		let e = this.playoutLimit, t;
		return t = this._duration === null ? this.dateRange.duration ? this.dateRange.duration : this.dateRange.plannedDuration || 0 : this._duration, !isNaN(e) && e < t && (t = e), t;
	}
	set duration(e) {
		this._duration = e;
	}
	get cue() {
		return this.dateRange.cue;
	}
	get timelineOccupancy() {
		return this.dateRange.attr["X-TIMELINE-OCCUPIES"] === "RANGE" ? Ad.Range : Ad.Point;
	}
	get supplementsPrimary() {
		return this.dateRange.attr["X-TIMELINE-STYLE"] === "PRIMARY";
	}
	get contentMayVary() {
		return this.dateRange.attr["X-CONTENT-MAY-VARY"] !== "NO";
	}
	get assetUrl() {
		return this.dateRange.attr["X-ASSET-URI"];
	}
	get assetListUrl() {
		return this.dateRange.attr["X-ASSET-LIST"];
	}
	get baseUrl() {
		return this.base.url;
	}
	get assetListLoaded() {
		return this.assetList.length > 0 || this.assetListResponse !== null;
	}
	toString() {
		return Id(this);
	}
};
function Nd(e, t) {
	return e - t.start < t.duration / 2 && !(Math.abs(e - (t.start + t.duration)) < kd) ? t.start : t.start + t.duration;
}
function Pd(e, t, n) {
	let r = new self.URL(e, n);
	return r.protocol !== "data:" && r.searchParams.set("_HLS_primary_id", t), r;
}
function Fd(e, t) {
	for (; (n = e.assetList[++t]) != null && n.error;) var n;
	return t;
}
function Id(e) {
	return `["${e.identifier}" ${e.cue.pre ? "<pre>" : e.cue.post ? "<post>" : ""}${e.timelineStart.toFixed(2)}-${e.resumeTime.toFixed(2)}]`;
}
function Ld(e) {
	let t = e.timelineStart, n = e.duration || 0;
	return `["${e.identifier}" ${t.toFixed(2)}-${(t + n).toFixed(2)}]`;
}
var Rd = class {
	constructor(e, t, n, r) {
		this.hls = void 0, this.interstitial = void 0, this.assetItem = void 0, this.tracks = null, this.hasDetails = !1, this.mediaAttached = null, this._currentTime = void 0, this._bufferedEosTime = void 0, this.checkPlayout = () => {
			this.reachedPlayout(this.currentTime) && this.hls && this.hls.trigger(q.PLAYOUT_LIMIT_REACHED, {});
		};
		let i = this.hls = new e(t);
		this.interstitial = n, this.assetItem = r;
		let a = () => {
			this.hasDetails = !0;
		};
		i.once(q.LEVEL_LOADED, a), i.once(q.AUDIO_TRACK_LOADED, a), i.once(q.SUBTITLE_TRACK_LOADED, a), i.on(q.MEDIA_ATTACHING, (e, { media: t }) => {
			this.removeMediaListeners(), this.mediaAttached = t, this.interstitial.playoutLimit && (t.addEventListener("timeupdate", this.checkPlayout), this.appendInPlace && i.on(q.BUFFER_APPENDED, () => {
				let e = this.bufferedEnd;
				this.reachedPlayout(e) && (this._bufferedEosTime = e, i.trigger(q.BUFFERED_TO_END, void 0));
			}));
		});
	}
	get appendInPlace() {
		return this.interstitial.appendInPlace;
	}
	loadSource() {
		let e = this.hls;
		if (e) {
			if (e.url) e.levels.length && !e.started && e.startLoad(-1, !0);
			else {
				let t = this.assetItem.uri;
				try {
					t = Pd(t, e.config.primarySessionId || "").href;
				} catch {}
				e.loadSource(t);
			}
		}
	}
	bufferedInPlaceToEnd(e) {
		var t;
		if (!this.appendInPlace) return !1;
		if ((t = this.hls) != null && t.bufferedToEnd) return !0;
		if (!e) return !1;
		let n = Math.min(this._bufferedEosTime || Infinity, this.duration), r = this.timelineOffset, i = Q.bufferInfo(e, r, 0);
		return this.getAssetTime(i.end) >= n - .02;
	}
	reachedPlayout(e) {
		let t = this.interstitial.playoutLimit;
		return this.startOffset + e >= t;
	}
	get destroyed() {
		var e;
		return !((e = this.hls) != null && e.userConfig);
	}
	get assetId() {
		return this.assetItem.identifier;
	}
	get interstitialId() {
		return this.assetItem.parentIdentifier;
	}
	get media() {
		return this.hls?.media || null;
	}
	get bufferedEnd() {
		let e = this.media || this.mediaAttached;
		if (!e) return this._bufferedEosTime ? this._bufferedEosTime : this.currentTime;
		let t = Q.bufferInfo(e, e.currentTime, .001);
		return this.getAssetTime(t.end);
	}
	get currentTime() {
		let e = this.media || this.mediaAttached;
		return e ? this.getAssetTime(e.currentTime) : this._currentTime || 0;
	}
	get duration() {
		let e = this.assetItem.duration;
		if (!e) return 0;
		let t = this.interstitial.playoutLimit;
		if (t) {
			let n = t - this.startOffset;
			if (n > 0 && n < e) return n;
		}
		return e;
	}
	get remaining() {
		let e = this.duration;
		return e ? Math.max(0, e - this.currentTime) : 0;
	}
	get startOffset() {
		return this.assetItem.startOffset;
	}
	get timelineOffset() {
		return this.hls?.config.timelineOffset || 0;
	}
	set timelineOffset(e) {
		let t = this.timelineOffset;
		if (e !== t) {
			let n = e - t;
			if (Math.abs(n) > 1 / 9e4 && this.hls) {
				if (this.hasDetails) throw Error("Cannot set timelineOffset after playlists are loaded");
				this.hls.config.timelineOffset = e;
			}
		}
	}
	getAssetTime(e) {
		let t = this.timelineOffset, n = this.duration;
		return Math.min(Math.max(0, e - t), n);
	}
	removeMediaListeners() {
		let e = this.mediaAttached;
		e && (this._currentTime = e.currentTime, this.bufferSnapShot(), e.removeEventListener("timeupdate", this.checkPlayout));
	}
	bufferSnapShot() {
		if (this.mediaAttached) {
			var e;
			(e = this.hls) != null && e.bufferedToEnd && (this._bufferedEosTime = this.bufferedEnd);
		}
	}
	destroy() {
		this.removeMediaListeners(), this.hls && this.hls.destroy(), this.hls = null, this.tracks = this.mediaAttached = this.checkPlayout = null;
	}
	attachMedia(e) {
		var t;
		this.loadSource(), (t = this.hls) == null || t.attachMedia(e);
	}
	detachMedia() {
		var e;
		this.removeMediaListeners(), this.mediaAttached = null, (e = this.hls) == null || e.detachMedia();
	}
	resumeBuffering() {
		var e;
		(e = this.hls) == null || e.resumeBuffering();
	}
	pauseBuffering() {
		var e;
		(e = this.hls) == null || e.pauseBuffering();
	}
	transferMedia() {
		return this.bufferSnapShot(), this.hls?.transferMedia() || null;
	}
	resetDetails() {
		let e = this.hls;
		if (e && this.hasDetails) {
			e.stopLoad();
			let t = (e) => delete e.details;
			e.levels.forEach(t), e.allAudioTracks.forEach(t), e.allSubtitleTracks.forEach(t), this.hasDetails = !1;
		}
	}
	on(e, t, n) {
		var r;
		(r = this.hls) == null || r.on(e, t);
	}
	once(e, t, n) {
		var r;
		(r = this.hls) == null || r.once(e, t);
	}
	off(e, t, n) {
		var r;
		(r = this.hls) == null || r.off(e, t);
	}
	toString() {
		return `HlsAssetPlayer: ${Ld(this.assetItem)} ${this.hls?.sessionId} ${this.appendInPlace ? "append-in-place" : ""}`;
	}
}, zd = .033, Bd = class extends Bn {
	constructor(e, t) {
		super("interstitials-sched", t), this.onScheduleUpdate = void 0, this.eventMap = {}, this.events = null, this.items = null, this.durations = {
			primary: 0,
			playout: 0,
			integrated: 0
		}, this.onScheduleUpdate = e;
	}
	destroy() {
		this.reset(), this.onScheduleUpdate = null;
	}
	reset() {
		this.eventMap = {}, this.setDurations(0, 0, 0), this.events && this.events.forEach((e) => e.reset()), this.events = this.items = null;
	}
	resetErrorsInRange(e, t) {
		return this.events ? this.events.reduce((n, r) => e <= r.startOffset && t > r.startOffset ? (delete r.error, n + 1) : n, 0) : 0;
	}
	get duration() {
		let e = this.items;
		return e ? e[e.length - 1].end : 0;
	}
	get length() {
		return this.items ? this.items.length : 0;
	}
	getEvent(e) {
		return e && this.eventMap[e] || null;
	}
	hasEvent(e) {
		return e in this.eventMap;
	}
	findItemIndex(e, t) {
		if (e.event) return this.findEventIndex(e.event.identifier);
		let n = -1;
		e.nextEvent ? n = this.findEventIndex(e.nextEvent.identifier) - 1 : e.previousEvent && (n = this.findEventIndex(e.previousEvent.identifier) + 1);
		let r = this.items;
		if (r) for (r[n] || (t === void 0 && (t = e.start), n = this.findItemIndexAtTime(t)); n >= 0 && (i = r[n]) != null && i.event;) {
			var i;
			n--;
		}
		return n;
	}
	findItemIndexAtTime(e, t) {
		let n = this.items;
		if (n) for (let r = 0; r < n.length; r++) {
			let i = n[r];
			if (t && t !== "primary" && (i = i[t]), e === i.start || e > i.start && e < i.end) return r;
		}
		return -1;
	}
	findJumpRestrictedIndex(e, t) {
		let n = this.items;
		if (n) for (let r = e; r <= t && n[r]; r++) {
			let e = n[r].event;
			if (e != null && e.restrictions.jump && !e.appendInPlace) return r;
		}
		return -1;
	}
	findEventIndex(e) {
		let t = this.items;
		if (t) {
			for (let n = t.length; n--;) if (t[n].event?.identifier === e) return n;
		}
		return -1;
	}
	findAssetIndex(e, t) {
		let n = e.assetList, r = n.length;
		if (r > 1) for (let e = 0; e < r; e++) {
			let i = n[e];
			if (!i.error) {
				let n = i.timelineStart;
				if (t === n || t > n && (t < n + (i.duration || 0) || e === r - 1)) return e;
			}
		}
		return 0;
	}
	get assetIdAtEnd() {
		var e;
		let t = (e = this.items) == null || (e = e[this.length - 1]) == null ? void 0 : e.event;
		if (t) {
			let e = t.assetList, n = e[e.length - 1];
			if (n) return n.identifier;
		}
		return null;
	}
	parseInterstitialDateRanges(e, t) {
		let n = e.main.details, { dateRanges: r } = n, i = this.events, a = this.parseDateRanges(r, { url: n.url }, t), o = Object.keys(r), s = i ? i.filter((e) => !o.includes(e.identifier)) : [];
		a.length && a.sort((e, t) => {
			let n = e.cue.pre, r = e.cue.post, i = t.cue.pre, a = t.cue.post;
			if (n && !i) return -1;
			if (i && !n || r && !a) return 1;
			if (a && !r) return -1;
			if (!n && !i && !r && !a) {
				let n = e.startTime, r = t.startTime;
				if (n !== r) return n - r;
			}
			return e.dateRange.tagOrder - t.dateRange.tagOrder;
		}), this.events = a, s.forEach((e) => {
			this.removeEvent(e);
		}), this.updateSchedule(e, s);
	}
	updateSchedule(e, t = [], n = !1) {
		let r = this.events || [];
		if (r.length || t.length || this.length < 2) {
			let i = this.items, a = this.parseSchedule(r, e);
			(n || t.length || i?.length !== a.length || a.some((e, t) => Math.abs(e.playout.start - i[t].playout.start) > .005 || Math.abs(e.playout.end - i[t].playout.end) > .005)) && (this.items = a, this.onScheduleUpdate(t, i));
		}
	}
	parseDateRanges(e, t, n) {
		let r = [], i = Object.keys(e);
		for (let a = 0; a < i.length; a++) {
			let o = i[a], s = e[o];
			if (s.isInterstitial) {
				let e = this.eventMap[o];
				e ? e.setDateRange(s) : (e = new Md(s, t), this.eventMap[o] = e, n === !1 && (e.appendInPlace = n)), r.push(e);
			}
		}
		return r;
	}
	parseSchedule(e, t) {
		let n = [], r = t.main.details, i = r.live ? Infinity : r.edge, a = 0;
		if (e = e.filter((e) => !e.error && !(e.cue.once && e.hasPlayed)), e.length) {
			this.resolveOffsets(e, t);
			let r = 0, o = 0;
			if (e.forEach((t, s) => {
				let c = t.cue.pre, l = t.cue.post, u = e[s - 1] || null, d = t.appendInPlace, f = l ? i : t.startOffset, p = t.duration, m = t.timelineOccupancy === Ad.Range ? p : 0, h = t.resumptionOffset, g = u?.startTime === f, _ = f + t.cumulativeDuration, v = d ? _ + p : f + h;
				if (c || !l && f <= 0) {
					let e = o;
					o += m, t.timelineStart = _;
					let r = a;
					a += p, n.push({
						event: t,
						start: _,
						end: v,
						playout: {
							start: r,
							end: a
						},
						integrated: {
							start: e,
							end: o
						}
					});
				} else if (f <= i) {
					if (!g) {
						let i = f - r;
						if (i > zd) {
							let c = r, l = o;
							o += i;
							let u = a;
							a += i;
							let d = {
								previousEvent: e[s - 1] || null,
								nextEvent: t,
								start: c,
								end: c + i,
								playout: {
									start: u,
									end: a
								},
								integrated: {
									start: l,
									end: o
								}
							};
							n.push(d);
						} else i > 0 && u && (u.cumulativeDuration += i, n[n.length - 1].end = f);
					}
					l && (v = _), t.timelineStart = _;
					let i = o;
					o += m;
					let c = a;
					a += p, n.push({
						event: t,
						start: _,
						end: v,
						playout: {
							start: c,
							end: a
						},
						integrated: {
							start: i,
							end: o
						}
					});
				} else return;
				let y = t.resumeTime;
				r = l || y > i ? i : y;
			}), r < i) {
				let e = r, t = o, s = i - r;
				o += s;
				let c = a;
				a += s, n.push({
					previousEvent: n[n.length - 1]?.event || null,
					nextEvent: null,
					start: r,
					end: e + s,
					playout: {
						start: c,
						end: a
					},
					integrated: {
						start: t,
						end: o
					}
				});
			}
			this.setDurations(i, a, o);
		} else n.push({
			previousEvent: null,
			nextEvent: null,
			start: 0,
			end: i,
			playout: {
				start: 0,
				end: i
			},
			integrated: {
				start: 0,
				end: i
			}
		}), this.setDurations(i, i, i);
		return n;
	}
	setDurations(e, t, n) {
		this.durations = {
			primary: e,
			playout: t,
			integrated: n
		};
	}
	resolveOffsets(e, t) {
		let n = t.main.details, r = n.live ? Infinity : n.edge, i = 0, a = -1;
		e.forEach((o, s) => {
			let c = o.cue.pre, l = o.cue.post, u = c ? 0 : l ? r : o.startTime;
			this.updateAssetDurations(o), a === u ? o.cumulativeDuration = i : (i = 0, a = u), !l && o.snapOptions.in && (o.resumeAnchor = Qi(null, n.fragments, o.startOffset + o.resumptionOffset, 0, 0) || void 0), o.appendInPlace && !o.appendInPlaceStarted && (this.primaryCanResumeInPlaceAt(o, t) || (o.appendInPlace = !1)), !o.appendInPlace && s + 1 < e.length && e[s + 1].startTime - e[s].resumeTime < zd && (e[s + 1].appendInPlace = !1, e[s + 1].appendInPlace && this.warn(`Could not change append strategy for abutting event ${o}`));
			let d = W(o.resumeOffset) ? o.resumeOffset : o.duration;
			i += d;
		});
	}
	primaryCanResumeInPlaceAt(e, t) {
		let n = e.resumeTime, r = e.startTime + e.resumptionOffset;
		return Math.abs(n - r) > kd ? (this.log(`"${e.identifier}" resumption ${n} not aligned with estimated timeline end ${r}`), !1) : !Object.keys(t).some((r) => {
			let i = t[r].details, a = i.edge;
			if (n >= a) return this.log(`"${e.identifier}" resumption ${n} past ${r} playlist end ${a}`), !1;
			let o = Qi(null, i.fragments, n);
			if (!o) return this.log(`"${e.identifier}" resumption ${n} does not align with any fragments in ${r} playlist (${i.fragStart}-${i.fragmentEnd})`), !0;
			let s = r === "audio" ? .175 : 0;
			return Math.abs(o.start - n) < kd + s || Math.abs(o.end - n) < kd + s ? !1 : (this.log(`"${e.identifier}" resumption ${n} not aligned with ${r} fragment bounds (${o.start}-${o.end} sn: ${o.sn} cc: ${o.cc})`), !0);
		});
	}
	updateAssetDurations(e) {
		if (!e.assetListLoaded) return;
		let t = e.timelineStart, n = 0, r = !1, i = !1;
		for (let a = 0; a < e.assetList.length; a++) {
			let o = e.assetList[a], s = t + n;
			o.startOffset = n, o.timelineStart = s, r ||= o.duration === null, i ||= !!o.error;
			let c = o.error ? 0 : o.duration || 0;
			n += c;
		}
		e.duration = r && !i ? Math.max(n, e.duration) : n;
	}
	removeEvent(e) {
		e.reset(), delete this.eventMap[e.identifier];
	}
};
function Vd(e) {
	return `[${e.event ? "\"" + e.event.identifier + "\"" : "primary"}: ${e.start.toFixed(2)}-${e.end.toFixed(2)}]`;
}
var Hd = class {
	constructor(e) {
		this.hls = void 0, this.hls = e;
	}
	destroy() {
		this.hls = null;
	}
	loadAssetList(e, t) {
		let n = e.assetListUrl, r;
		try {
			r = Pd(n, this.hls.sessionId, e.baseUrl);
		} catch (t) {
			let r = this.assignAssetListError(e, K.ASSET_LIST_LOAD_ERROR, t, n);
			this.hls.trigger(q.ERROR, r);
			return;
		}
		t && r.protocol !== "data:" && r.searchParams.set("_HLS_start_offset", "" + t);
		let i = this.hls.config, a = i.loader, o = new a(i), s = {
			responseType: "json",
			url: r.href
		}, c = i.interstitialAssetListLoadPolicy.default, l = {
			loadPolicy: c,
			timeout: c.maxLoadTimeMs,
			maxRetry: 0,
			retryDelay: 0,
			maxRetryDelay: 0
		};
		return o.load(s, l, {
			onSuccess: (t, n, r, i) => {
				let a = t.data, o = a?.ASSETS;
				if (Array.isArray(o)) e.assetListResponse = a, this.hls.trigger(q.ASSET_LIST_LOADED, {
					event: e,
					assetListResponse: a,
					networkDetails: i
				});
				else {
					let t = this.assignAssetListError(e, K.ASSET_LIST_PARSING_ERROR, /* @__PURE__ */ Error("Invalid interstitial asset list"), r.url, n, i);
					this.hls.trigger(q.ERROR, t);
				}
			},
			onError: (t, n, r, i) => {
				let a = this.assignAssetListError(e, K.ASSET_LIST_LOAD_ERROR, /* @__PURE__ */ Error(`Error loading X-ASSET-LIST: HTTP status ${t.code} ${t.text} (${n.url})`), n.url, i, r);
				this.hls.trigger(q.ERROR, a);
			},
			onTimeout: (t, n, r) => {
				let i = this.assignAssetListError(e, K.ASSET_LIST_LOAD_TIMEOUT, /* @__PURE__ */ Error(`Timeout loading X-ASSET-LIST (${n.url})`), n.url, t, r);
				this.hls.trigger(q.ERROR, i);
			}
		}), this.hls.trigger(q.ASSET_LIST_LOADING, { event: e }), o;
	}
	assignAssetListError(e, t, n, r, i, a) {
		return e.error = n, {
			type: G.NETWORK_ERROR,
			details: t,
			fatal: !1,
			interstitial: e,
			url: r,
			error: n,
			networkDetails: a,
			stats: i
		};
	}
};
function Ud(e) {
	var t;
	e == null || (t = e.play()) == null || t.catch(() => {});
}
function Wd(e, t) {
	return `[${e}] Advancing timeline position to ${t}`;
}
var Gd = class extends Bn {
	constructor(e, t) {
		super("interstitials", e.logger), this.HlsPlayerClass = void 0, this.hls = void 0, this.assetListLoader = void 0, this.mediaSelection = null, this.altSelection = null, this.media = null, this.detachedData = null, this.requiredTracks = null, this.manager = null, this.playerQueue = [], this.bufferedPos = -1, this.timelinePos = -1, this.schedule = void 0, this.playingItem = null, this.bufferingItem = null, this.waitingItem = null, this.endedItem = null, this.playingAsset = null, this.endedAsset = null, this.bufferingAsset = null, this.shouldPlay = !1, this.onPlay = () => {
			this.shouldPlay = !0;
		}, this.onPause = () => {
			this.shouldPlay = !1;
		}, this.onSeeking = () => {
			let e = this.currentTime;
			if (e === void 0 || this.playbackDisabled || !this.schedule) return;
			let t = e - this.timelinePos;
			if (Math.abs(t) < 1 / 7056e5) return;
			let n = t <= -.01;
			this.timelinePos = e, this.bufferedPos = e;
			let r = this.playingItem;
			if (!r) {
				this.checkBuffer();
				return;
			}
			if (n && this.schedule.resetErrorsInRange(e, e - t) && this.updateSchedule(!0), this.checkBuffer(), n && e < r.start || e >= r.end) {
				var i;
				let t = this.findItemIndex(r), a = this.schedule.findItemIndexAtTime(e);
				if (a === -1 && (a = t + (n ? -1 : 1), this.log(`seeked ${n ? "back " : ""}to position not covered by schedule ${e} (resolving from ${t} to ${a})`)), !this.isInterstitial(r) && (i = this.media) != null && i.paused && (this.shouldPlay = !1), !n && a > t) {
					let e = this.schedule.findJumpRestrictedIndex(t + 1, a);
					if (e > t) {
						this.setSchedulePosition(e);
						return;
					}
				}
				this.setSchedulePosition(a);
				return;
			}
			let a = this.playingAsset;
			if (!a) {
				if (this.playingLastItem && this.isInterstitial(r)) {
					let t = r.event.assetList[0];
					t && (this.endedItem = this.playingItem, this.playingItem = null, this.setScheduleToAssetAtTime(e, t));
				}
				return;
			}
			let o = a.timelineStart, s = a.duration || 0;
			if (n && e < o || e >= o + s) {
				var c;
				(c = r.event) != null && c.appendInPlace && (this.clearAssetPlayers(r.event, r), this.flushFrontBuffer(e)), this.setScheduleToAssetAtTime(e, a);
			}
		}, this.onTimeupdate = () => {
			let e = this.currentTime;
			if (e === void 0 || this.playbackDisabled) return;
			if (e > this.timelinePos) this.timelinePos = e, e > this.bufferedPos && this.checkBuffer();
			else return;
			let t = this.playingItem;
			if (!t || this.playingLastItem) return;
			if (e >= t.end) {
				this.timelinePos = t.end;
				let e = this.findItemIndex(t);
				this.setSchedulePosition(e + 1);
			}
			let n = this.playingAsset;
			n && e >= n.timelineStart + (n.duration || 0) && this.setScheduleToAssetAtTime(e, n);
		}, this.onScheduleUpdate = (e, t) => {
			let n = this.schedule;
			if (!n) return;
			let r = this.playingItem, i = n.events || [], a = n.items || [], o = n.durations, s = e.map((e) => e.identifier), c = !!(i.length || s.length);
			(c || t) && this.log(`INTERSTITIALS_UPDATED (${i.length}): ${i}
Schedule: ${a.map((e) => Vd(e))} pos: ${this.timelinePos}`), s.length && this.log(`Removed events ${s}`);
			let l = null, u = null;
			r && (l = this.updateItem(r, this.timelinePos), this.itemsMatch(r, l) ? this.playingItem = l : this.waitingItem = this.endedItem = null), this.waitingItem = this.updateItem(this.waitingItem), this.endedItem = this.updateItem(this.endedItem);
			let d = this.bufferingItem;
			if (d && (u = this.updateItem(d, this.bufferedPos), this.itemsMatch(d, u) ? this.bufferingItem = u : d.event && (this.bufferingItem = this.playingItem, this.clearInterstitial(d.event, null))), e.forEach((e) => {
				e.assetList.forEach((e) => {
					this.clearAssetPlayer(e.identifier, null);
				});
			}), this.playerQueue.forEach((e) => {
				if (e.interstitial.appendInPlace) {
					let t = e.assetItem.timelineStart, n = e.timelineOffset - t;
					if (n) try {
						e.timelineOffset = t;
					} catch (r) {
						Math.abs(n) > kd && this.warn(`${r} ("${e.assetId}" ${e.timelineOffset}->${t})`);
					}
				}
			}), c || t) {
				if (this.hls.trigger(q.INTERSTITIALS_UPDATED, {
					events: i.slice(0),
					schedule: a.slice(0),
					durations: o,
					removedIds: s
				}), this.isInterstitial(r) && s.includes(r.event.identifier)) {
					this.warn(`Interstitial "${r.event.identifier}" removed while playing`), this.primaryFallback(r.event);
					return;
				}
				r && this.trimInPlace(l, r), d && u !== l && this.trimInPlace(u, d), this.checkBuffer();
			}
		}, this.hls = e, this.HlsPlayerClass = t, this.assetListLoader = new Hd(e), this.schedule = new Bd(this.onScheduleUpdate, e.logger), this.registerListeners();
	}
	registerListeners() {
		let e = this.hls;
		e && (e.on(q.MEDIA_ATTACHING, this.onMediaAttaching, this), e.on(q.MEDIA_ATTACHED, this.onMediaAttached, this), e.on(q.MEDIA_DETACHING, this.onMediaDetaching, this), e.on(q.MANIFEST_LOADING, this.onManifestLoading, this), e.on(q.LEVEL_UPDATED, this.onLevelUpdated, this), e.on(q.AUDIO_TRACK_SWITCHING, this.onAudioTrackSwitching, this), e.on(q.AUDIO_TRACK_UPDATED, this.onAudioTrackUpdated, this), e.on(q.SUBTITLE_TRACK_SWITCH, this.onSubtitleTrackSwitch, this), e.on(q.SUBTITLE_TRACK_UPDATED, this.onSubtitleTrackUpdated, this), e.on(q.EVENT_CUE_ENTER, this.onInterstitialCueEnter, this), e.on(q.ASSET_LIST_LOADED, this.onAssetListLoaded, this), e.on(q.BUFFER_APPENDED, this.onBufferAppended, this), e.on(q.BUFFER_FLUSHED, this.onBufferFlushed, this), e.on(q.BUFFERED_TO_END, this.onBufferedToEnd, this), e.on(q.MEDIA_ENDED, this.onMediaEnded, this), e.on(q.ERROR, this.onError, this), e.on(q.DESTROYING, this.onDestroying, this));
	}
	unregisterListeners() {
		let e = this.hls;
		e && (e.off(q.MEDIA_ATTACHING, this.onMediaAttaching, this), e.off(q.MEDIA_ATTACHED, this.onMediaAttached, this), e.off(q.MEDIA_DETACHING, this.onMediaDetaching, this), e.off(q.MANIFEST_LOADING, this.onManifestLoading, this), e.off(q.LEVEL_UPDATED, this.onLevelUpdated, this), e.off(q.AUDIO_TRACK_SWITCHING, this.onAudioTrackSwitching, this), e.off(q.AUDIO_TRACK_UPDATED, this.onAudioTrackUpdated, this), e.off(q.SUBTITLE_TRACK_SWITCH, this.onSubtitleTrackSwitch, this), e.off(q.SUBTITLE_TRACK_UPDATED, this.onSubtitleTrackUpdated, this), e.off(q.EVENT_CUE_ENTER, this.onInterstitialCueEnter, this), e.off(q.ASSET_LIST_LOADED, this.onAssetListLoaded, this), e.off(q.BUFFER_CODECS, this.onBufferCodecs, this), e.off(q.BUFFER_APPENDED, this.onBufferAppended, this), e.off(q.BUFFER_FLUSHED, this.onBufferFlushed, this), e.off(q.BUFFERED_TO_END, this.onBufferedToEnd, this), e.off(q.MEDIA_ENDED, this.onMediaEnded, this), e.off(q.ERROR, this.onError, this), e.off(q.DESTROYING, this.onDestroying, this));
	}
	startLoad() {
		this.resumeBuffering();
	}
	stopLoad() {
		this.pauseBuffering();
	}
	resumeBuffering() {
		var e;
		(e = this.getBufferingPlayer()) == null || e.resumeBuffering();
	}
	pauseBuffering() {
		var e;
		(e = this.getBufferingPlayer()) == null || e.pauseBuffering();
	}
	destroy() {
		this.unregisterListeners(), this.stopLoad(), this.assetListLoader && this.assetListLoader.destroy(), this.emptyPlayerQueue(), this.clearScheduleState(), this.schedule && this.schedule.destroy(), this.media = this.detachedData = this.mediaSelection = this.requiredTracks = this.altSelection = this.schedule = this.manager = null, this.hls = this.HlsPlayerClass = this.log = null, this.assetListLoader = null, this.onPlay = this.onPause = this.onSeeking = this.onTimeupdate = null, this.onScheduleUpdate = null;
	}
	onDestroying() {
		let e = this.primaryMedia || this.media;
		e && this.removeMediaListeners(e);
	}
	removeMediaListeners(e) {
		ps(e, "play", this.onPlay), ps(e, "pause", this.onPause), ps(e, "seeking", this.onSeeking), ps(e, "timeupdate", this.onTimeupdate);
	}
	onMediaAttaching(e, t) {
		let n = this.media = t.media;
		fs(n, "seeking", this.onSeeking), fs(n, "timeupdate", this.onTimeupdate), fs(n, "play", this.onPlay), fs(n, "pause", this.onPause);
	}
	onMediaAttached(e, t) {
		let n = this.effectivePlayingItem, r = this.detachedData;
		if (this.detachedData = null, n === null) this.checkStart();
		else if (!r) {
			this.clearScheduleState();
			let e = this.findItemIndex(n);
			this.setSchedulePosition(e);
		}
	}
	clearScheduleState() {
		this.log("clear schedule state"), this.playingItem = this.bufferingItem = this.waitingItem = this.endedItem = this.playingAsset = this.endedAsset = this.bufferingAsset = null;
	}
	onMediaDetaching(e, t) {
		let n = !!t.transferMedia, r = this.media;
		if (this.media = null, !n && (r && this.removeMediaListeners(r), this.detachedData)) {
			let e = this.getBufferingPlayer();
			e && (this.log(`Removing schedule state for detachedData and ${e}`), this.playingAsset = this.endedAsset = this.bufferingAsset = this.bufferingItem = this.waitingItem = this.detachedData = null, e.detachMedia()), this.shouldPlay = !1;
		}
	}
	get interstitialsManager() {
		if (!this.hls) return null;
		if (this.manager) return this.manager;
		let e = this, t = () => e.bufferingItem || e.waitingItem, n = (t) => t && e.getAssetPlayer(t.identifier), r = (t, r, i, o, s) => {
			if (t) {
				let c = t[r].start, l = t.event;
				if (l) {
					if (r === "playout" || l.timelineOccupancy !== Ad.Point) {
						let e = n(i);
						e?.interstitial === l && (c += e.assetItem.startOffset + e[s]);
					}
				} else {
					let n = o === "bufferedPos" ? a() : e[o];
					c += n - t.start;
				}
				return c;
			}
			return 0;
		}, i = (t, n) => {
			var r;
			if (t !== 0 && n !== "primary" && (r = e.schedule) != null && r.length) {
				let r = e.schedule.findItemIndexAtTime(t), i = e.schedule.items?.[r];
				if (i) return t + (i[n].start - i.start);
			}
			return t;
		}, a = () => {
			let t = e.bufferedPos;
			return t === Number.MAX_VALUE ? o("primary") : Math.max(t, 0);
		}, o = (t) => {
			var n;
			return (n = e.primaryDetails) != null && n.live ? e.primaryDetails.edge : e.schedule?.durations[t] || 0;
		}, s = (t, i) => {
			var a;
			let o = e.effectivePlayingItem;
			if (o != null && (a = o.event) != null && a.restrictions.skip || !e.schedule) return;
			e.log(`seek to ${t} "${i}"`);
			let s = e.effectivePlayingItem, c = e.schedule.findItemIndexAtTime(t, i), l = e.schedule.items?.[c], u = e.getBufferingPlayer(), d = u?.interstitial?.appendInPlace, f = s && e.itemsMatch(s, l);
			if (s && (d || f)) {
				let a = n(e.playingAsset), o = a?.media || e.primaryMedia;
				if (o) {
					let n = i === "primary" ? o.currentTime : r(s, i, e.playingAsset, "timelinePos", "currentTime"), c = t - n, l = (d ? n : o.currentTime) + c;
					if (l >= 0 && (!a || d || l <= a.duration)) {
						o.currentTime = l;
						return;
					}
				}
			}
			if (l) {
				let n = t;
				if (i !== "primary") {
					let e = t - l[i].start;
					n = l.start + e;
				}
				let r = !e.isInterstitial(l);
				if ((!e.isInterstitial(s) || s.event.appendInPlace) && (r || l.event.appendInPlace)) {
					let t = e.media || (d ? u?.media : null);
					t && (t.currentTime = n);
				} else if (s) {
					let a = e.findItemIndex(s);
					if (c > a) {
						let t = e.schedule.findJumpRestrictedIndex(a + 1, c);
						if (t > a) {
							e.setSchedulePosition(t);
							return;
						}
					}
					let o = 0;
					if (r) e.timelinePos = n, e.checkBuffer();
					else {
						let e = l.event.assetList, n = t - (l[i] || l).start;
						for (let t = e.length; t--;) {
							let r = e[t];
							if (r.duration && n >= r.startOffset && n < r.startOffset + r.duration) {
								o = t;
								break;
							}
						}
					}
					e.setSchedulePosition(c, o);
				}
			}
		}, c = () => {
			let n = e.effectivePlayingItem;
			if (e.isInterstitial(n)) return n;
			let r = t();
			return e.isInterstitial(r) ? r : null;
		}, l = {
			get bufferedEnd() {
				let n = t(), i = e.bufferingItem;
				return i && i === n && (r(i, "playout", e.bufferingAsset, "bufferedPos", "bufferedEnd") - i.playout.start || e.bufferingAsset?.startOffset) || 0;
			},
			get currentTime() {
				let t = c(), n = e.effectivePlayingItem;
				return n && n === t ? r(n, "playout", e.effectivePlayingAsset, "timelinePos", "currentTime") - n.playout.start : 0;
			},
			set currentTime(t) {
				let n = c(), r = e.effectivePlayingItem;
				r && r === n && s(t + r.playout.start, "playout");
			},
			get duration() {
				let e = c();
				return e ? e.playout.end - e.playout.start : 0;
			},
			get assetPlayers() {
				let t = c()?.event.assetList;
				return t ? t.map((t) => e.getAssetPlayer(t.identifier)) : [];
			},
			get playingIndex() {
				let t = c()?.event;
				return t && e.effectivePlayingAsset ? t.findAssetIndex(e.effectivePlayingAsset) : -1;
			},
			get scheduleItem() {
				return c();
			}
		};
		return this.manager = {
			get events() {
				var t;
				return ((t = e.schedule) == null || (t = t.events) == null ? void 0 : t.slice(0)) || [];
			},
			get schedule() {
				var t;
				return ((t = e.schedule) == null || (t = t.items) == null ? void 0 : t.slice(0)) || [];
			},
			get interstitialPlayer() {
				return c() ? l : null;
			},
			get playerQueue() {
				return e.playerQueue.slice(0);
			},
			get bufferingAsset() {
				return e.bufferingAsset;
			},
			get bufferingItem() {
				return t();
			},
			get bufferingIndex() {
				let n = t();
				return e.findItemIndex(n);
			},
			get playingAsset() {
				return e.effectivePlayingAsset;
			},
			get playingItem() {
				return e.effectivePlayingItem;
			},
			get playingIndex() {
				let t = e.effectivePlayingItem;
				return e.findItemIndex(t);
			},
			primary: {
				get bufferedEnd() {
					return a();
				},
				get currentTime() {
					let t = e.timelinePos;
					return t > 0 ? t : 0;
				},
				set currentTime(e) {
					s(e, "primary");
				},
				get duration() {
					return o("primary");
				},
				get seekableStart() {
					return e.primaryDetails?.fragmentStart || 0;
				}
			},
			integrated: {
				get bufferedEnd() {
					return r(t(), "integrated", e.bufferingAsset, "bufferedPos", "bufferedEnd");
				},
				get currentTime() {
					return r(e.effectivePlayingItem, "integrated", e.effectivePlayingAsset, "timelinePos", "currentTime");
				},
				set currentTime(e) {
					s(e, "integrated");
				},
				get duration() {
					return o("integrated");
				},
				get seekableStart() {
					return i(e.primaryDetails?.fragmentStart || 0, "integrated");
				}
			},
			skip: () => {
				let t = e.effectivePlayingItem, n = t?.event;
				if (n && !n.restrictions.skip) {
					let r = e.findItemIndex(t);
					if (n.appendInPlace) {
						let e = t.playout.start + t.event.duration;
						s(e + .001, "playout");
					} else e.advanceAfterAssetEnded(n, r, Infinity);
				}
			}
		};
	}
	get effectivePlayingItem() {
		return this.waitingItem || this.playingItem || this.endedItem;
	}
	get effectivePlayingAsset() {
		return this.playingAsset || this.endedAsset;
	}
	get playingLastItem() {
		let e = this.playingItem, t = this.schedule?.items;
		return !this.playbackStarted || !e || !t ? !1 : this.findItemIndex(e) === t.length - 1;
	}
	get playbackStarted() {
		return this.effectivePlayingItem !== null;
	}
	get currentTime() {
		var e;
		if (this.mediaSelection === null) return;
		let t = this.waitingItem || this.playingItem;
		if (this.isInterstitial(t) && !t.event.appendInPlace) return;
		let n = this.media;
		!n && (e = this.bufferingItem) != null && (e = e.event) != null && e.appendInPlace && (n = this.primaryMedia);
		let r = n?.currentTime;
		if (r !== void 0 && W(r)) return r;
	}
	get primaryMedia() {
		return this.media || this.detachedData?.media || null;
	}
	isInterstitial(e) {
		return !!(e != null && e.event);
	}
	retreiveMediaSource(e, t) {
		let n = this.getAssetPlayer(e);
		n && this.transferMediaFromPlayer(n, t);
	}
	transferMediaFromPlayer(e, t) {
		let n = e.interstitial.appendInPlace, r = e.media;
		if (n && r === this.primaryMedia) {
			if (this.bufferingAsset = null, (!t || this.isInterstitial(t) && !t.event.appendInPlace) && t && r) {
				this.detachedData = { media: r };
				return;
			}
			let n = e.transferMedia();
			this.log(`transfer MediaSource from ${e} ${Fi(n)}`), this.detachedData = n;
		} else t && r && (this.shouldPlay ||= !r.paused);
	}
	transferMediaTo(e, t) {
		if (e.media === t) return;
		let n = null, r = this.hls, i = e !== r, a = i && e.interstitial.appendInPlace, o = this.detachedData?.mediaSource, s;
		if (r.media) a && (n = r.transferMedia(), this.detachedData = n), s = "Primary";
		else if (o) {
			let e = this.getBufferingPlayer();
			e ? (n = e.transferMedia(), s = `${e}`) : s = "detached MediaSource";
		} else s = "detached media";
		if (!n) {
			if (o) n = this.detachedData, this.log(`using detachedData: MediaSource ${Fi(n)}`);
			else if (!this.detachedData || r.media === t) {
				let e = this.playerQueue;
				e.length > 1 && e.forEach((e) => {
					if (i && e.interstitial.appendInPlace !== a) {
						let t = e.interstitial;
						this.clearInterstitial(e.interstitial, null), t.appendInPlace = !1, t.appendInPlace && this.warn(`Could not change append strategy for queued assets ${t}`);
					}
				}), this.hls.detachMedia(), this.detachedData = { media: t };
			}
		}
		let c = n && "mediaSource" in n && n.mediaSource?.readyState !== "closed", l = c && n ? n : t;
		this.log(`${c ? "transfering MediaSource" : "attaching media"} to ${i ? e : "Primary"} from ${s} (media.currentTime: ${t.currentTime})`);
		let u = this.schedule;
		if (l === n && u) {
			let t = i && e.assetId === u.assetIdAtEnd;
			l.overrides = {
				duration: u.duration,
				endOfStream: !i || t,
				cueRemoval: !i
			};
		}
		e.attachMedia(l);
	}
	onInterstitialCueEnter() {
		this.onTimeupdate();
	}
	checkStart() {
		let e = this.schedule, t = e?.events;
		if (!t || this.playbackDisabled || !this.media) return;
		this.bufferedPos === -1 && (this.bufferedPos = 0);
		let n = this.timelinePos, r = this.effectivePlayingItem;
		if (n === -1) {
			let n = this.hls.startPosition;
			if (this.log(Wd("checkStart", n)), this.timelinePos = n, t.length && t[0].cue.pre) {
				let n = e.findEventIndex(t[0].identifier);
				this.setSchedulePosition(n);
			} else if (n >= 0 || !this.primaryLive) {
				let t = this.timelinePos = n > 0 ? n : 0, r = e.findItemIndexAtTime(t);
				this.setSchedulePosition(r);
			}
		} else if (r && !this.playingItem) {
			let t = e.findItemIndex(r);
			this.setSchedulePosition(t);
		}
	}
	advanceAssetBuffering(e, t) {
		let n = e.event, r = Fd(n, n.findAssetIndex(t));
		if (!n.isAssetPastPlayoutLimit(r)) this.bufferedToEvent(e, r);
		else if (this.schedule) {
			let t = this.schedule.items?.[this.findItemIndex(e) + 1];
			t && this.bufferedToItem(t);
		}
	}
	advanceAfterAssetEnded(e, t, n) {
		let r = Fd(e, n);
		if (!e.isAssetPastPlayoutLimit(r)) {
			if (e.appendInPlace) {
				let t = e.assetList[r];
				t && this.advanceInPlace(t.timelineStart);
			}
			this.setSchedulePosition(t, r);
		} else if (this.schedule) {
			let n = this.schedule.items;
			if (n) {
				let r = t + 1;
				if (r >= n.length) {
					this.setSchedulePosition(-1);
					return;
				}
				let i = e.resumeTime;
				this.timelinePos < i && (this.log(Wd("advanceAfterAssetEnded", i)), this.timelinePos = i, e.appendInPlace && this.advanceInPlace(i), this.checkBuffer(this.bufferedPos < i)), this.setSchedulePosition(r);
			}
		}
	}
	setScheduleToAssetAtTime(e, t) {
		let n = this.schedule;
		if (!n) return;
		let r = t.parentIdentifier, i = n.getEvent(r);
		if (i) {
			let t = n.findEventIndex(r), a = n.findAssetIndex(i, e);
			this.advanceAfterAssetEnded(i, t, a - 1);
		}
	}
	setSchedulePosition(e, t) {
		let n = this.schedule?.items;
		if (!n || this.playbackDisabled) return;
		let r = e >= 0 ? n[e] : null;
		this.log(`setSchedulePosition ${e}, ${t} (${r && Vd(r)}) pos: ${this.timelinePos}`);
		let i = this.waitingItem || this.playingItem, a = this.playingLastItem;
		if (this.isInterstitial(i)) {
			let s = i.event, c = this.playingAsset, l = c?.identifier, u = l ? this.getAssetPlayer(l) : null;
			if (u && l && (!this.eventItemsMatch(i, r) || t !== void 0 && l !== s.assetList[t].identifier)) {
				var o;
				let t = s.findAssetIndex(c);
				if (this.log(`INTERSTITIAL_ASSET_ENDED ${t + 1}/${s.assetList.length} ${Ld(c)}`), this.endedAsset = c, this.playingAsset = null, this.hls.trigger(q.INTERSTITIAL_ASSET_ENDED, {
					asset: c,
					assetListIndex: t,
					event: s,
					schedule: n.slice(0),
					scheduleIndex: e,
					player: u
				}), i !== this.playingItem) {
					this.itemsMatch(i, this.playingItem) && !this.playingAsset && this.advanceAfterAssetEnded(s, this.findItemIndex(this.playingItem), t);
					return;
				}
				this.retreiveMediaSource(l, r), u.media && !((o = this.detachedData) != null && o.mediaSource) && u.detachMedia();
			}
			if (!this.eventItemsMatch(i, r) && (this.endedItem = i, this.playingItem = null, this.log(`INTERSTITIAL_ENDED ${s} ${Vd(i)}`), s.hasPlayed = !0, this.hls.trigger(q.INTERSTITIAL_ENDED, {
				event: s,
				schedule: n.slice(0),
				scheduleIndex: e
			}), s.cue.once)) {
				this.updateSchedule();
				let e = this.schedule?.items;
				if (r && e) {
					let n = this.findItemIndex(r);
					this.advanceSchedule(n, e, t, i, a);
				}
				return;
			}
		}
		this.advanceSchedule(e, n, t, i, a);
	}
	advanceSchedule(e, t, n, r, i) {
		let a = this.schedule;
		if (!a) return;
		let o = t[e] || null, s = this.primaryMedia, c = this.playerQueue;
		if (c.length && c.forEach((t) => {
			let n = t.interstitial, r = a.findEventIndex(n.identifier);
			(r < e || r > e + 1) && this.clearInterstitial(n, o);
		}), this.isInterstitial(o)) {
			this.timelinePos = Math.min(Math.max(this.timelinePos, o.start), o.end);
			let i = o.event;
			if (n === void 0) {
				n = a.findAssetIndex(i, this.timelinePos);
				let t = Fd(i, n - 1);
				if (i.isAssetPastPlayoutLimit(t) || i.appendInPlace && this.timelinePos === o.end) {
					this.advanceAfterAssetEnded(i, e, n);
					return;
				}
				n = t;
			}
			let c = this.waitingItem;
			this.assetsBuffered(o, s) || this.setBufferingItem(o);
			let l = this.preloadAssets(i, n);
			if (this.eventItemsMatch(o, c || r) || (this.waitingItem = o, this.log(`INTERSTITIAL_STARTED ${Vd(o)} ${i.appendInPlace ? "append in place" : ""}`), this.hls.trigger(q.INTERSTITIAL_STARTED, {
				event: i,
				schedule: t.slice(0),
				scheduleIndex: e
			})), !i.assetListLoaded) {
				this.log(`Waiting for ASSET-LIST to complete loading ${i}`);
				return;
			}
			if (i.assetListLoader &&= (i.assetListLoader.destroy(), void 0), !s) {
				this.log(`Waiting for attachMedia to start Interstitial ${i}`);
				return;
			}
			this.waitingItem = this.endedItem = null, this.playingItem = o;
			let u = i.assetList[n];
			if (!u) {
				this.advanceAfterAssetEnded(i, e, n || 0);
				return;
			}
			if (l ||= this.getAssetPlayer(u.identifier), l === null || l.destroyed) {
				let e = i.assetList.length;
				this.warn(`asset ${n + 1}/${e} player destroyed ${i}`), l = this.createAssetPlayer(i, u, n), l.loadSource();
			}
			if (!this.eventItemsMatch(o, this.bufferingItem) && i.appendInPlace && this.isAssetBuffered(u)) return;
			this.startAssetPlayer(l, n, t, e, s), this.shouldPlay && Ud(l.media);
		} else o ? (this.resumePrimary(o, e, r), this.shouldPlay && Ud(this.hls.media)) : i && this.isInterstitial(r) && (this.endedItem = null, this.playingItem = r, r.event.appendInPlace || this.attachPrimary(a.durations.primary, null));
	}
	get playbackDisabled() {
		return this.hls.config.enableInterstitialPlayback === !1;
	}
	get primaryDetails() {
		return this.mediaSelection?.main.details;
	}
	get primaryLive() {
		var e;
		return !!((e = this.primaryDetails) != null && e.live);
	}
	resumePrimary(e, t, n) {
		var r;
		if (this.playingItem = e, this.playingAsset = this.endedAsset = null, this.waitingItem = this.endedItem = null, this.bufferedToItem(e), this.log(`resuming ${Vd(e)}`), !((r = this.detachedData) != null && r.mediaSource)) {
			let n = this.timelinePos;
			(n < e.start || n >= e.end) && (n = this.getPrimaryResumption(e, t), this.log(Wd("resumePrimary", n)), this.timelinePos = n), this.attachPrimary(n, e);
		}
		if (!n) return;
		let i = this.schedule?.items;
		i && (this.log(`INTERSTITIALS_PRIMARY_RESUMED ${Vd(e)}`), this.hls.trigger(q.INTERSTITIALS_PRIMARY_RESUMED, {
			schedule: i.slice(0),
			scheduleIndex: t
		}), this.checkBuffer());
	}
	getPrimaryResumption(e, t) {
		let n = e.start;
		if (this.primaryLive) {
			let e = this.primaryDetails;
			if (t === 0) return this.hls.startPosition;
			if (e && (n < e.fragmentStart || n > e.edge)) return this.hls.liveSyncPosition || -1;
		}
		return n;
	}
	isAssetBuffered(e) {
		let t = this.getAssetPlayer(e.identifier);
		return t != null && t.hls ? t.hls.bufferedToEnd : Q.bufferInfo(this.primaryMedia, this.timelinePos, 0).end + 1 >= e.timelineStart + (e.duration || 0);
	}
	attachPrimary(e, t, n) {
		t ? this.setBufferingItem(t) : this.bufferingItem = this.playingItem, this.bufferingAsset = null;
		let r = this.primaryMedia;
		if (!r) return;
		let i = this.hls;
		i.media ? this.checkBuffer() : (this.transferMediaTo(i, r), n && this.startLoadingPrimaryAt(e, n)), n || (this.log(Wd("attachPrimary", e)), this.timelinePos = e, this.startLoadingPrimaryAt(e, n));
	}
	startLoadingPrimaryAt(e, t) {
		let n = this.hls;
		!n.loadingEnabled || !n.media || Math.abs((n.mainForwardBufferInfo?.start || n.media.currentTime) - e) > .5 ? n.startLoad(e, t) : n.bufferingEnabled || n.resumeBuffering();
	}
	onManifestLoading() {
		var e;
		this.stopLoad(), (e = this.schedule) == null || e.reset(), this.emptyPlayerQueue(), this.clearScheduleState(), this.shouldPlay = !1, this.bufferedPos = this.timelinePos = -1, this.mediaSelection = this.altSelection = this.manager = this.requiredTracks = null, this.hls.off(q.BUFFER_CODECS, this.onBufferCodecs, this), this.hls.on(q.BUFFER_CODECS, this.onBufferCodecs, this);
	}
	onLevelUpdated(e, t) {
		if (t.level === -1 || !this.schedule) return;
		let n = this.hls.levels[t.level];
		if (!n.details) return;
		let r = Ln(Ln({}, this.mediaSelection || this.altSelection), {}, { main: n });
		this.mediaSelection = r, this.schedule.parseInterstitialDateRanges(r, this.hls.config.interstitialAppendInPlace), !this.effectivePlayingItem && this.schedule.items && this.checkStart();
	}
	onAudioTrackUpdated(e, t) {
		let n = this.hls.audioTracks[t.id], r = this.mediaSelection;
		if (!r) {
			this.altSelection = Ln(Ln({}, this.altSelection), {}, { audio: n });
			return;
		}
		let i = Ln(Ln({}, r), {}, { audio: n });
		this.mediaSelection = i;
	}
	onSubtitleTrackUpdated(e, t) {
		let n = this.hls.subtitleTracks[t.id], r = this.mediaSelection;
		if (!r) {
			this.altSelection = Ln(Ln({}, this.altSelection), {}, { subtitles: n });
			return;
		}
		let i = Ln(Ln({}, r), {}, { subtitles: n });
		this.mediaSelection = i;
	}
	onAudioTrackSwitching(e, t) {
		let n = Bi(t);
		this.playerQueue.forEach(({ hls: e }) => e && (e.setAudioOption(t) || e.setAudioOption(n)));
	}
	onSubtitleTrackSwitch(e, t) {
		let n = Bi(t);
		this.playerQueue.forEach(({ hls: e }) => e && (e.setSubtitleOption(t) || t.id !== -1 && e.setSubtitleOption(n)));
	}
	onBufferCodecs(e, t) {
		let n = t.tracks;
		n && (this.requiredTracks = n);
	}
	onBufferAppended(e, t) {
		this.checkBuffer();
	}
	onBufferFlushed(e, t) {
		let n = this.playingItem;
		if (n && !this.itemsMatch(n, this.bufferingItem) && !this.isInterstitial(n)) {
			let e = this.timelinePos;
			this.bufferedPos = e, this.checkBuffer();
		}
	}
	onBufferedToEnd(e) {
		if (!this.schedule) return;
		let t = this.schedule.events;
		if (this.bufferedPos < Number.MAX_VALUE && t) {
			for (let e = 0; e < t.length; e++) {
				let n = t[e];
				if (n.cue.post) {
					let e = this.schedule.findEventIndex(n.identifier), t = this.schedule.items?.[e];
					this.isInterstitial(t) && this.eventItemsMatch(t, this.bufferingItem) && this.bufferedToItem(t, 0);
					break;
				}
			}
			this.bufferedPos = Number.MAX_VALUE;
		}
	}
	onMediaEnded(e) {
		let t = this.playingItem;
		if (!this.playingLastItem && t) {
			let e = this.findItemIndex(t);
			this.setSchedulePosition(e + 1);
		} else this.shouldPlay = !1;
	}
	updateItem(e, t) {
		let n = this.schedule?.items;
		return e && n && n[this.findItemIndex(e, t)] || null;
	}
	trimInPlace(e, t) {
		if (this.isInterstitial(e) && e.event.appendInPlace && t.end - e.end > .25) {
			e.event.assetList.forEach((t, n) => {
				e.event.isAssetPastPlayoutLimit(n) && this.clearAssetPlayer(t.identifier, null);
			});
			let n = e.end + .25, r = Q.bufferInfo(this.primaryMedia, n, 0);
			(r.end > n || (r.nextStart || 0) > n) && (this.log(`trim buffered interstitial ${Vd(e)} (was ${Vd(t)})`), this.attachPrimary(n, null, !0), this.flushFrontBuffer(n));
		}
	}
	itemsMatch(e, t) {
		return !!t && (e === t || e.event && t.event && this.eventItemsMatch(e, t) || !e.event && !t.event && this.findItemIndex(e) === this.findItemIndex(t));
	}
	eventItemsMatch(e, t) {
		return !!t && (e === t || e.event.identifier === t.event?.identifier);
	}
	findItemIndex(e, t) {
		return e && this.schedule ? this.schedule.findItemIndex(e, t) : -1;
	}
	updateSchedule(e = !1) {
		var t;
		let n = this.mediaSelection;
		n && ((t = this.schedule) == null || t.updateSchedule(n, [], e));
	}
	checkBuffer(e) {
		let t = this.schedule?.items;
		if (!t) return;
		let n = Q.bufferInfo(this.primaryMedia, this.timelinePos, 0);
		e && (this.bufferedPos = this.timelinePos), e ||= n.len < 1, this.updateBufferedPos(n.end, t, e);
	}
	updateBufferedPos(e, t, n) {
		let r = this.schedule, i = this.bufferingItem;
		if (this.bufferedPos > e || !r) return;
		if (t.length === 1 && this.itemsMatch(t[0], i)) {
			this.bufferedPos = e;
			return;
		}
		let a = this.playingItem, o = this.findItemIndex(a), s = r.findItemIndexAtTime(e);
		if (this.bufferedPos < e) {
			var c;
			let n = this.findItemIndex(i), r = Math.min(n + 1, t.length - 1), a = t[r];
			if ((s === -1 && i && e >= i.end || (c = a.event) != null && c.appendInPlace && e + .01 >= a.start) && (s = r), this.isInterstitial(i)) {
				let e = i.event;
				if (r - o > 1 && e.appendInPlace === !1 || e.assetList.length === 0 && e.assetListLoader) return;
			}
			if (this.bufferedPos = e, s > n && s > o) this.bufferedToItem(a);
			else {
				let t = this.primaryDetails;
				this.primaryLive && t && e > t.edge - t.targetduration && a.start < t.edge + this.hls.config.interstitialLiveLookAhead && this.isInterstitial(a) && this.preloadAssets(a.event, 0);
			}
		} else n && a && !this.itemsMatch(a, i) && (s === o ? this.bufferedToItem(a) : s === o + 1 && this.bufferedToItem(t[s]));
	}
	assetsBuffered(e, t) {
		return e.event.assetList.length !== 0 && !e.event.assetList.some((e) => {
			let n = this.getAssetPlayer(e.identifier);
			return !(n != null && n.bufferedInPlaceToEnd(t));
		});
	}
	setBufferingItem(e) {
		let t = this.bufferingItem, n = this.schedule;
		if (!this.itemsMatch(e, t) && n) {
			let { items: r, events: i } = n;
			if (!r || !i) return t;
			let a = this.isInterstitial(e), o = this.getBufferingPlayer();
			this.bufferingItem = e, this.bufferedPos = Math.max(e.start, Math.min(e.end, this.timelinePos));
			let s = o ? o.remaining : t ? t.end - this.timelinePos : 0;
			if (this.log(`INTERSTITIALS_BUFFERED_TO_BOUNDARY ${Vd(e)}` + (t ? ` (${s.toFixed(2)} remaining)` : "")), !this.playbackDisabled) {
				if (a) {
					let t = n.findAssetIndex(e.event, this.bufferedPos);
					e.event.assetList.forEach((e, n) => {
						let r = this.getAssetPlayer(e.identifier);
						r && (n === t && r.loadSource(), r.resumeBuffering());
					});
				} else this.hls.resumeBuffering(), this.playerQueue.forEach((e) => e.pauseBuffering());
			}
			this.hls.trigger(q.INTERSTITIALS_BUFFERED_TO_BOUNDARY, {
				events: i.slice(0),
				schedule: r.slice(0),
				bufferingIndex: this.findItemIndex(e),
				playingIndex: this.findItemIndex(this.playingItem)
			});
		} else this.bufferingItem !== e && (this.bufferingItem = e);
		return t;
	}
	bufferedToItem(e, t = 0) {
		let n = this.setBufferingItem(e);
		if (!this.playbackDisabled) {
			if (this.isInterstitial(e)) this.bufferedToEvent(e, t);
			else if (n !== null) {
				this.bufferingAsset = null;
				let t = this.detachedData;
				t && t.mediaSource ? this.attachPrimary(e.start, e, !0) : this.preloadPrimary(e);
			}
		}
	}
	preloadPrimary(e) {
		let t = this.findItemIndex(e), n = this.getPrimaryResumption(e, t);
		this.startLoadingPrimaryAt(n);
	}
	bufferedToEvent(e, t) {
		let n = e.event, r = n.assetList.length === 0 && !n.assetListLoader, i = n.cue.once;
		if (r || !i) {
			let e = this.preloadAssets(n, t);
			if (e != null && e.interstitial.appendInPlace) {
				let t = this.primaryMedia;
				t && this.bufferAssetPlayer(e, t);
			}
		}
	}
	preloadAssets(e, t) {
		let n = e.assetUrl, r = e.assetList.length, i = r === 0 && !e.assetListLoader, a = e.cue.once;
		if (i) {
			let i = e.timelineStart;
			if (e.appendInPlace) {
				var o;
				let t = this.playingItem;
				!this.isInterstitial(t) && (t == null || (o = t.nextEvent) == null ? void 0 : o.identifier) === e.identifier && this.flushFrontBuffer(i + .25);
			}
			let a, s = 0;
			if (!this.playingItem && this.primaryLive && (s = this.hls.startPosition, s === -1 && (s = this.hls.liveSyncPosition || 0)), s && !(e.cue.pre || e.cue.post)) {
				let e = s - i;
				e > 0 && (a = Math.round(e * 1e3) / 1e3);
			}
			if (this.log(`Load interstitial asset ${t + 1}/${n ? 1 : r} ${e}${a ? ` live-start: ${s} start-offset: ${a}` : ""}`), n) return this.createAsset(e, 0, 0, i, e.duration, n);
			let c = this.assetListLoader.loadAssetList(e, a);
			c && (e.assetListLoader = c);
		} else if (!a && r) {
			for (let n = t; n < r; n++) {
				let t = e.assetList[n], r = this.getAssetPlayerQueueIndex(t.identifier);
				(r === -1 || this.playerQueue[r].destroyed) && !t.error && this.createAssetPlayer(e, t, n);
			}
			let n = e.assetList[t];
			if (n) {
				let e = this.getAssetPlayer(n.identifier);
				return e && e.loadSource(), e;
			}
		}
		return null;
	}
	flushFrontBuffer(e) {
		let t = this.requiredTracks;
		t && (this.log(`Removing front buffer starting at ${e}`), Object.keys(t).forEach((t) => {
			this.hls.trigger(q.BUFFER_FLUSHING, {
				startOffset: e,
				endOffset: Infinity,
				type: t
			});
		}));
	}
	getAssetPlayerQueueIndex(e) {
		let t = this.playerQueue;
		for (let n = 0; n < t.length; n++) if (e === t[n].assetId) return n;
		return -1;
	}
	getAssetPlayer(e) {
		let t = this.getAssetPlayerQueueIndex(e);
		return this.playerQueue[t] || null;
	}
	getBufferingPlayer() {
		let { playerQueue: e, primaryMedia: t } = this;
		if (t) {
			for (let n = 0; n < e.length; n++) if (e[n].media === t) return e[n];
		}
		return null;
	}
	createAsset(e, t, n, r, i, a) {
		let o = {
			parentIdentifier: e.identifier,
			identifier: jd(e, a, t),
			duration: i,
			startOffset: n,
			timelineStart: r,
			uri: a
		};
		return this.createAssetPlayer(e, o, t);
	}
	createAssetPlayer(e, t, n) {
		let r = this.hls, i = r.userConfig, a = i.videoPreference, o = r.loadLevelObj || r.levels[r.currentLevel];
		(a || o) && (a = Fn({}, a), o.videoCodec && (a.videoCodec = o.videoCodec), o.videoRange && (a.allowedVideoRanges = [o.videoRange]));
		let s = r.audioTracks[r.audioTrack], c = r.subtitleTracks[r.subtitleTrack], l = 0;
		if (this.primaryLive || e.appendInPlace) {
			let e = this.timelinePos - t.timelineStart;
			if (e > 1) {
				let n = t.duration;
				n && e < n && (l = e);
			}
		}
		let u = t.identifier, d = Ln(Ln({}, i), {}, {
			maxMaxBufferLength: Math.min(180, r.config.maxMaxBufferLength),
			autoStartLoad: !0,
			startFragPrefetch: !0,
			primarySessionId: r.sessionId,
			assetPlayerId: u,
			abrEwmaDefaultEstimate: r.bandwidthEstimate,
			interstitialsController: void 0,
			startPosition: l,
			liveDurationInfinity: !1,
			testBandwidth: !1,
			videoPreference: a,
			audioPreference: s || i.audioPreference,
			subtitlePreference: c || i.subtitlePreference
		});
		e.appendInPlace && (e.appendInPlaceStarted = !0, t.timelineStart && (d.timelineOffset = t.timelineStart));
		let f = d.cmcd;
		f != null && f.sessionId && f.contentId && (d.cmcd = Fn({}, f, { contentId: Od(t.uri) })), this.getAssetPlayer(u) && this.warn(`Duplicate date range identifier ${e} and asset ${u}`);
		let p = new Rd(this.HlsPlayerClass, d, e, t);
		this.playerQueue.push(p), e.assetList[n] = t;
		let m = !0, h = (r) => {
			if (r.live) {
				let t = /* @__PURE__ */ Error(`Interstitials MUST be VOD assets ${e}`), r = {
					fatal: !0,
					type: G.OTHER_ERROR,
					details: K.INTERSTITIAL_ASSET_ITEM_ERROR,
					error: t
				}, i = this.schedule?.findEventIndex(e.identifier) || -1;
				this.handleAssetItemError(r, e, i, n, t.message);
				return;
			}
			let i = r.edge - r.fragmentStart, a = t.duration;
			(m || a === null || i > a) && (m = !1, this.log(`Interstitial asset "${u}" duration change ${a} > ${i}`), t.duration = i, this.updateSchedule());
		};
		p.on(q.LEVEL_UPDATED, (e, { details: t }) => h(t)), p.on(q.LEVEL_PTS_UPDATED, (e, { details: t }) => h(t)), p.on(q.EVENT_CUE_ENTER, () => this.onInterstitialCueEnter());
		let g = (e, t) => {
			let n = this.getAssetPlayer(u);
			if (n && t.tracks) {
				n.off(q.BUFFER_CODECS, g), n.tracks = t.tracks;
				let e = this.primaryMedia;
				this.bufferingAsset === n.assetItem && e && !n.media && this.bufferAssetPlayer(n, e);
			}
		};
		p.on(q.BUFFER_CODECS, g), p.on(q.BUFFERED_TO_END, () => {
			let n = this.getAssetPlayer(u);
			if (this.log(`buffered to end of asset ${n}`), !n || !this.schedule) return;
			let r = this.schedule.findEventIndex(e.identifier), i = this.schedule.items?.[r];
			this.isInterstitial(i) && this.advanceAssetBuffering(i, t);
		});
		let _ = (t) => () => {
			if (!this.getAssetPlayer(u) || !this.schedule) return;
			this.shouldPlay = !0;
			let n = this.schedule.findEventIndex(e.identifier);
			this.advanceAfterAssetEnded(e, n, t);
		};
		return p.once(q.MEDIA_ENDED, _(n)), p.once(q.PLAYOUT_LIMIT_REACHED, _(Infinity)), p.on(q.ERROR, (t, r) => {
			if (!this.schedule) return;
			let i = this.getAssetPlayer(u);
			if (r.details === K.BUFFER_STALLED_ERROR) {
				if (i != null && i.appendInPlace) {
					this.handleInPlaceStall(e);
					return;
				}
				this.onTimeupdate(), this.checkBuffer(!0);
			} else this.handleAssetItemError(r, e, this.schedule.findEventIndex(e.identifier), n, `Asset player error ${r.error} ${e}`);
		}), p.on(q.DESTROYING, () => {
			if (!this.getAssetPlayer(u) || !this.schedule) return;
			let t = /* @__PURE__ */ Error(`Asset player destroyed unexpectedly ${u}`), r = {
				fatal: !0,
				type: G.OTHER_ERROR,
				details: K.INTERSTITIAL_ASSET_ITEM_ERROR,
				error: t
			};
			this.handleAssetItemError(r, e, this.schedule.findEventIndex(e.identifier), n, t.message);
		}), this.log(`INTERSTITIAL_ASSET_PLAYER_CREATED ${Ld(t)}`), this.hls.trigger(q.INTERSTITIAL_ASSET_PLAYER_CREATED, {
			asset: t,
			assetListIndex: n,
			event: e,
			player: p
		}), p;
	}
	clearInterstitial(e, t) {
		this.clearAssetPlayers(e, t), e.reset();
	}
	clearAssetPlayers(e, t) {
		e.assetList.forEach((e) => {
			this.clearAssetPlayer(e.identifier, t);
		});
	}
	resetAssetPlayer(e) {
		let t = this.getAssetPlayerQueueIndex(e);
		if (t !== -1) {
			this.log(`reset asset player "${e}" after error`);
			let n = this.playerQueue[t];
			this.transferMediaFromPlayer(n, null), n.resetDetails();
		}
	}
	clearAssetPlayer(e, t) {
		let n = this.getAssetPlayerQueueIndex(e);
		if (n !== -1) {
			let e = this.playerQueue[n];
			this.log(`clear ${e} toSegment: ${t && Vd(t)}`), this.transferMediaFromPlayer(e, t), this.playerQueue.splice(n, 1), e.destroy();
		}
	}
	emptyPlayerQueue() {
		let e;
		for (; e = this.playerQueue.pop();) e.destroy();
		this.playerQueue = [];
	}
	startAssetPlayer(e, t, n, r, i) {
		let { interstitial: a, assetItem: o, assetId: s } = e, c = a.assetList.length, l = this.playingAsset;
		this.endedAsset = null, this.playingAsset = o, l && l.identifier === s || (l && (this.clearAssetPlayer(l.identifier, n[r]), delete l.error), this.log(`INTERSTITIAL_ASSET_STARTED ${t + 1}/${c} ${Ld(o)}`), this.hls.trigger(q.INTERSTITIAL_ASSET_STARTED, {
			asset: o,
			assetListIndex: t,
			event: a,
			schedule: n.slice(0),
			scheduleIndex: r,
			player: e
		})), this.bufferAssetPlayer(e, i);
	}
	bufferAssetPlayer(e, t) {
		if (!this.schedule) return;
		let { interstitial: n, assetItem: r } = e, i = this.schedule.findEventIndex(n.identifier), a = this.schedule.items?.[i];
		if (!a) return;
		e.loadSource(), this.setBufferingItem(a), this.bufferingAsset = r;
		let o = this.getBufferingPlayer();
		if (o === e) return;
		let s = n.appendInPlace;
		if (s && o?.interstitial.appendInPlace === !1) return;
		let c = o?.tracks || this.detachedData?.tracks || this.requiredTracks;
		if (s && r !== this.playingAsset) {
			if (!e.tracks) {
				this.log(`Waiting for track info before buffering ${e}`);
				return;
			}
			if (c && !Zn(c, e.tracks)) {
				let t = /* @__PURE__ */ Error(`Asset ${Ld(r)} SourceBuffer tracks ('${Object.keys(e.tracks)}') are not compatible with primary content tracks ('${Object.keys(c)}')`), a = {
					fatal: !0,
					type: G.OTHER_ERROR,
					details: K.INTERSTITIAL_ASSET_ITEM_ERROR,
					error: t
				}, o = n.findAssetIndex(r);
				this.handleAssetItemError(a, n, i, o, t.message);
				return;
			}
		}
		this.transferMediaTo(e, t);
	}
	handleInPlaceStall(e) {
		let t = this.schedule, n = this.primaryMedia;
		if (!t || !n) return;
		let r = n.currentTime, i = t.findAssetIndex(e, r), a = e.assetList[i];
		if (a) {
			let o = this.getAssetPlayer(a.identifier);
			if (o) {
				let s = o.currentTime || r - a.timelineStart, c = o.duration - s;
				if (this.warn(`Stalled at ${s} of ${s + c} in ${o} ${e} (media.currentTime: ${r})`), s && (c / n.playbackRate < .5 || o.bufferedInPlaceToEnd(n)) && o.hls) {
					let n = t.findEventIndex(e.identifier);
					this.advanceAfterAssetEnded(e, n, i);
				}
			}
		}
	}
	advanceInPlace(e) {
		let t = this.primaryMedia;
		t && t.currentTime < e && (t.currentTime = e);
	}
	handleAssetItemError(e, t, n, r, i) {
		if (e.details === K.BUFFER_STALLED_ERROR) return;
		let a = t.assetList[r] || null;
		if (this.warn(`INTERSTITIAL_ASSET_ERROR ${a && Ld(a)} ${e.error}`), !this.schedule) return;
		let o = a?.identifier || "", s = this.getAssetPlayerQueueIndex(o), c = this.playerQueue[s] || null, l = this.schedule.items, u = Fn({}, e, {
			fatal: !1,
			errorAction: ha(!0),
			asset: a,
			assetListIndex: r,
			event: t,
			schedule: l,
			scheduleIndex: n,
			player: c
		});
		if (this.hls.trigger(q.INTERSTITIAL_ASSET_ERROR, u), !e.fatal) return;
		let d = this.playingAsset, f = this.bufferingAsset, p = Error(i);
		if (a && (this.clearAssetPlayer(o, null), a.error = p), !t.assetList.some((e) => !e.error)) t.error = p;
		else for (let e = r; e < t.assetList.length; e++) this.resetAssetPlayer(t.assetList[e].identifier);
		this.updateSchedule(!0), t.error ? this.primaryFallback(t) : d && d.identifier === o ? this.advanceAfterAssetEnded(t, n, r) : f && f.identifier === o && this.isInterstitial(this.bufferingItem) && this.advanceAssetBuffering(this.bufferingItem, f);
	}
	primaryFallback(e) {
		let t = e.timelineStart, n = this.effectivePlayingItem, r = this.timelinePos;
		if (n) {
			this.log(`Fallback to primary from event "${e.identifier}" start: ${t} pos: ${r} playing: ${Vd(n)} error: ${e.error}`), r === -1 && (r = this.hls.startPosition);
			let i = this.updateItem(n, r);
			this.itemsMatch(n, i) && this.clearInterstitial(e, null), e.appendInPlace && (this.attachPrimary(t, null), this.flushFrontBuffer(t));
		} else if (r === -1) {
			this.checkStart();
			return;
		}
		if (!this.schedule) return;
		let i = this.schedule.findItemIndexAtTime(r);
		this.setSchedulePosition(i);
	}
	onAssetListLoaded(e, t) {
		var n;
		let r = t.event, i = r.identifier, a = t.assetListResponse.ASSETS;
		if (!((n = this.schedule) != null && n.hasEvent(i))) return;
		let o = r.timelineStart, s = r.duration, c = 0;
		a.forEach((e, t) => {
			let n = parseFloat(e.DURATION);
			this.createAsset(r, t, c, o + c, n, e.URI), c += n;
		}), r.duration = c, this.log(`Loaded asset-list with duration: ${c} (was: ${s}) ${r}`);
		let l = this.waitingItem?.event.identifier === i;
		this.updateSchedule();
		let u = this.bufferingItem?.event;
		if (l) {
			let e = this.schedule.findEventIndex(i), t = this.schedule.items?.[e];
			if (t) {
				if (!this.playingItem && this.timelinePos > t.end && this.schedule.findItemIndexAtTime(this.timelinePos) !== e) {
					r.error = /* @__PURE__ */ Error(`Interstitial ${a.length ? "no longer within playback range" : "asset-list is empty"} ${this.timelinePos} ${r}`), this.log(r.error.message), this.updateSchedule(!0), this.primaryFallback(r);
					return;
				}
				this.setBufferingItem(t);
			}
			this.setSchedulePosition(e);
		} else if (u?.identifier === i) {
			let e = r.assetList[0];
			if (e) {
				let t = this.getAssetPlayer(e.identifier);
				if (u.appendInPlace) {
					let e = this.primaryMedia;
					t && e && this.bufferAssetPlayer(t, e);
				} else t && t.loadSource();
			}
		}
	}
	onError(e, t) {
		if (this.schedule) switch (t.details) {
			case K.ASSET_LIST_PARSING_ERROR:
			case K.ASSET_LIST_LOAD_ERROR:
			case K.ASSET_LIST_LOAD_TIMEOUT: {
				let e = t.interstitial;
				e && (this.updateSchedule(!0), this.primaryFallback(e));
				break;
			}
			case K.BUFFER_STALLED_ERROR: {
				let e = this.endedItem || this.waitingItem || this.playingItem;
				if (this.isInterstitial(e) && e.event.appendInPlace) {
					this.handleInPlaceStall(e.event);
					return;
				}
				this.log(`Primary player stall @${this.timelinePos} bufferedPos: ${this.bufferedPos}`), this.onTimeupdate(), this.checkBuffer(!0);
				break;
			}
		}
	}
}, Kd = 500, qd = class extends hs {
	constructor(e, t, n) {
		super(e, t, n, "subtitle-stream-controller", Y.SUBTITLE), this.currentTrackId = -1, this.tracksBuffered = [], this.mainDetails = null, this.registerListeners();
	}
	onHandlerDestroying() {
		this.unregisterListeners(), super.onHandlerDestroying(), this.mainDetails = null;
	}
	registerListeners() {
		super.registerListeners();
		let { hls: e } = this;
		e.on(q.LEVEL_LOADED, this.onLevelLoaded, this), e.on(q.SUBTITLE_TRACKS_UPDATED, this.onSubtitleTracksUpdated, this), e.on(q.SUBTITLE_TRACK_SWITCH, this.onSubtitleTrackSwitch, this), e.on(q.SUBTITLE_TRACK_LOADED, this.onSubtitleTrackLoaded, this), e.on(q.SUBTITLE_FRAG_PROCESSED, this.onSubtitleFragProcessed, this), e.on(q.BUFFER_FLUSHING, this.onBufferFlushing, this);
	}
	unregisterListeners() {
		super.unregisterListeners();
		let { hls: e } = this;
		e.off(q.LEVEL_LOADED, this.onLevelLoaded, this), e.off(q.SUBTITLE_TRACKS_UPDATED, this.onSubtitleTracksUpdated, this), e.off(q.SUBTITLE_TRACK_SWITCH, this.onSubtitleTrackSwitch, this), e.off(q.SUBTITLE_TRACK_LOADED, this.onSubtitleTrackLoaded, this), e.off(q.SUBTITLE_FRAG_PROCESSED, this.onSubtitleFragProcessed, this), e.off(q.BUFFER_FLUSHING, this.onBufferFlushing, this);
	}
	startLoad(e, t) {
		this.stopLoad(), this.state = $.IDLE, this.setInterval(Kd), this.nextLoadPosition = this.lastCurrentTime = e + this.timelineOffset, this.startPosition = t ? -1 : e, this.tick();
	}
	onManifestLoading() {
		super.onManifestLoading(), this.mainDetails = null;
	}
	onMediaDetaching(e, t) {
		this.tracksBuffered = [], super.onMediaDetaching(e, t);
	}
	onLevelLoaded(e, t) {
		this.mainDetails = t.details;
	}
	onSubtitleFragProcessed(e, t) {
		let { frag: n, success: r } = t;
		if (this.fragContextChanged(n) || (lr(n) && (this.fragPrevious = n), this.state = $.IDLE), !r) return;
		let i = this.tracksBuffered[this.currentTrackId];
		if (!i) return;
		let a, o = n.start;
		for (let e = 0; e < i.length; e++) if (o >= i[e].start && o <= i[e].end) {
			a = i[e];
			break;
		}
		let s = n.start + n.duration;
		a ? a.end = s : (a = {
			start: o,
			end: s
		}, i.push(a)), this.fragmentTracker.fragBuffered(n), this.fragBufferedComplete(n, null), this.media && this.tick();
	}
	onBufferFlushing(e, t) {
		let { startOffset: n, endOffset: r } = t;
		if (n === 0 && r !== Infinity) {
			let e = r - 1;
			if (e <= 0) return;
			t.endOffsetSubtitles = Math.max(0, e), this.tracksBuffered.forEach((t) => {
				for (let n = 0; n < t.length;) if (t[n].end <= e) t.shift();
				else {
					if (t[n].start < e) t[n].start = e;
					else break;
					n++;
				}
			}), this.fragmentTracker.removeFragmentsInRange(n, e, Y.SUBTITLE);
		}
	}
	onError(e, t) {
		let n = t.frag;
		n?.type === Y.SUBTITLE && (t.details === K.FRAG_GAP && this.fragmentTracker.fragBuffered(n, !0), this.fragCurrent && this.fragCurrent.abortRequests(), this.state !== $.STOPPED && (this.state = $.IDLE));
	}
	onSubtitleTracksUpdated(e, { subtitleTracks: t }) {
		this.levels && kl(this.levels, t) ? this.levels = t.map((e) => new Ai(e)) : (this.tracksBuffered = [], this.levels = t.map((e) => {
			let t = new Ai(e);
			return this.tracksBuffered[t.id] = [], t;
		}), this.fragmentTracker.removeFragmentsInRange(0, Infinity, Y.SUBTITLE), this.fragPrevious = null, this.mediaBuffer = null);
	}
	onSubtitleTrackSwitch(e, t) {
		var n;
		if (this.currentTrackId = t.id, !((n = this.levels) != null && n.length) || this.currentTrackId === -1) {
			this.clearInterval();
			return;
		}
		let r = this.levels[this.currentTrackId];
		this.mediaBuffer = r != null && r.details ? this.mediaBufferTimeRanges : null, r && this.state !== $.STOPPED && this.setInterval(Kd);
	}
	onSubtitleTrackLoaded(e, t) {
		var n;
		let { currentTrackId: r, levels: i } = this, { details: a, id: o } = t;
		if (!i) {
			this.warn(`Subtitle tracks were reset while loading level ${o}`);
			return;
		}
		let s = i[o];
		if (o >= i.length || !s) return;
		this.log(`Subtitle track ${o} loaded [${a.startSN},${a.endSN}]${a.lastPartSn ? `[part-${a.lastPartSn}-${a.lastPartIndex}]` : ""},duration:${a.totalduration}`), this.mediaBuffer = this.mediaBufferTimeRanges;
		let c = 0;
		if (a.live || (n = s.details) != null && n.live) {
			if (a.deltaUpdateFailed) return;
			let e = this.mainDetails;
			if (!e) {
				this.startFragRequested = !1;
				return;
			}
			let t = e.fragments[0];
			s.details ? (c = this.alignPlaylists(a, s.details, this.levelLastLoaded?.details), c === 0 && t && (c = t.start, Zo(a, c))) : a.hasProgramDateTime && e.hasProgramDateTime ? (ds(a, e), c = a.fragmentStart) : t && (c = t.start, Zo(a, c)), e && !this.startFragRequested && this.setStartPosition(e, c);
		}
		s.details = a, this.levelLastLoaded = s, o === r && (this.hls.trigger(q.SUBTITLE_TRACK_UPDATED, {
			details: a,
			id: o,
			groupId: t.groupId
		}), this.tick(), a.live && !this.fragCurrent && this.media && this.state === $.IDLE && (Qi(null, a.fragments, this.media.currentTime, 0) || (this.warn("Subtitle playlist not aligned with playback"), s.details = void 0)));
	}
	_handleFragmentLoadComplete(e) {
		let { frag: t, payload: n } = e, r = t.decryptdata, i = this.hls;
		if (!this.fragContextChanged(t) && n && n.byteLength > 0 && r != null && r.key && r.iv && to(r.method)) {
			let e = performance.now();
			this.decrypter.decrypt(new Uint8Array(n), r.key.buffer, r.iv.buffer, no(r.method)).catch((e) => {
				throw i.trigger(q.ERROR, {
					type: G.MEDIA_ERROR,
					details: K.FRAG_DECRYPT_ERROR,
					fatal: !1,
					error: e,
					reason: e.message,
					frag: t
				}), e;
			}).then((n) => {
				let r = performance.now();
				i.trigger(q.FRAG_DECRYPTED, {
					frag: t,
					payload: n,
					stats: {
						tstart: e,
						tdecrypt: r
					}
				});
			}).catch((e) => {
				this.warn(`${e.name}: ${e.message}`), this.state = $.IDLE;
			});
		}
	}
	doTick() {
		if (!this.media) this.state = $.IDLE;
		else if (this.state === $.IDLE) {
			let { currentTrackId: e, levels: t } = this, n = t?.[e];
			if (!n || !t.length || !n.details || this.waitForLive(n)) return;
			let { config: r } = this, i = this.getLoadPosition(), { end: a, len: o } = Q.bufferedInfo(this.tracksBuffered[this.currentTrackId] || [], i, r.maxBufferHole), s = n.details;
			if (o > this.hls.maxBufferLength + s.levelTargetDuration) return;
			let c = s.fragments, l = c.length, u = s.edge, d = null, f = this.fragPrevious;
			if (a < u) {
				let e = r.maxFragLookUpTolerance, t = a > u - e ? 0 : e;
				d = Qi(f, c, Math.max(c[0].start, a), t), !d && f && f.start < c[0].start && (d = c[0]);
			} else d = c[l - 1];
			if (d = this.filterReplacedPrimary(d, n.details), !d) return;
			let p = c[d.sn - s.startSN - 1];
			if (p && p.cc === d.cc && this.fragmentTracker.getState(p) === ga.NOT_LOADED && (d = p), this.fragmentTracker.getState(d) === ga.NOT_LOADED) {
				let e = this.mapToInitFragWhenRequired(d);
				e && this.loadFragment(e, n, a);
			}
		}
	}
	loadFragment(e, t, n) {
		lr(e) ? super.loadFragment(e, t, n) : this._loadInitSegment(e, t);
	}
	get mediaBufferTimeRanges() {
		return new Jd(this.tracksBuffered[this.currentTrackId] || []);
	}
}, Jd = class {
	constructor(e) {
		this.buffered = void 0;
		let t = (t, n, r) => {
			if (n >>>= 0, n > r - 1) throw new DOMException(`Failed to execute '${t}' on 'TimeRanges': The index provided (${n}) is greater than the maximum bound (${r})`);
			return e[n][t];
		};
		this.buffered = {
			get length() {
				return e.length;
			},
			end(n) {
				return t("end", n, e.length);
			},
			start(n) {
				return t("start", n, e.length);
			}
		};
	}
}, Yd = {
	42: 225,
	92: 233,
	94: 237,
	95: 243,
	96: 250,
	123: 231,
	124: 247,
	125: 209,
	126: 241,
	127: 9608,
	128: 174,
	129: 176,
	130: 189,
	131: 191,
	132: 8482,
	133: 162,
	134: 163,
	135: 9834,
	136: 224,
	137: 32,
	138: 232,
	139: 226,
	140: 234,
	141: 238,
	142: 244,
	143: 251,
	144: 193,
	145: 201,
	146: 211,
	147: 218,
	148: 220,
	149: 252,
	150: 8216,
	151: 161,
	152: 42,
	153: 8217,
	154: 9473,
	155: 169,
	156: 8480,
	157: 8226,
	158: 8220,
	159: 8221,
	160: 192,
	161: 194,
	162: 199,
	163: 200,
	164: 202,
	165: 203,
	166: 235,
	167: 206,
	168: 207,
	169: 239,
	170: 212,
	171: 217,
	172: 249,
	173: 219,
	174: 171,
	175: 187,
	176: 195,
	177: 227,
	178: 205,
	179: 204,
	180: 236,
	181: 210,
	182: 242,
	183: 213,
	184: 245,
	185: 123,
	186: 125,
	187: 92,
	188: 94,
	189: 95,
	190: 124,
	191: 8764,
	192: 196,
	193: 228,
	194: 214,
	195: 246,
	196: 223,
	197: 165,
	198: 164,
	199: 9475,
	200: 197,
	201: 229,
	202: 216,
	203: 248,
	204: 9487,
	205: 9491,
	206: 9495,
	207: 9499
}, Xd = (e) => String.fromCharCode(Yd[e] || e), Zd = 15, Qd = 100, $d = {
	17: 1,
	18: 3,
	21: 5,
	22: 7,
	23: 9,
	16: 11,
	19: 12,
	20: 14
}, ef = {
	17: 2,
	18: 4,
	21: 6,
	22: 8,
	23: 10,
	19: 13,
	20: 15
}, tf = {
	25: 1,
	26: 3,
	29: 5,
	30: 7,
	31: 9,
	24: 11,
	27: 12,
	28: 14
}, nf = {
	25: 2,
	26: 4,
	29: 6,
	30: 8,
	31: 10,
	27: 13,
	28: 15
}, rf = [
	"white",
	"green",
	"blue",
	"cyan",
	"red",
	"yellow",
	"magenta",
	"black",
	"transparent"
], af = class {
	constructor() {
		this.time = null, this.verboseLevel = 0;
	}
	log(e, t) {
		if (this.verboseLevel >= e) {
			let n = typeof t == "function" ? t() : t;
			Jn.log(`${this.time} [${e}] ${n}`);
		}
	}
}, of = function(e) {
	let t = [];
	for (let n = 0; n < e.length; n++) t.push(e[n].toString(16));
	return t;
}, sf = class {
	constructor() {
		this.foreground = "white", this.underline = !1, this.italics = !1, this.background = "black", this.flash = !1;
	}
	reset() {
		this.foreground = "white", this.underline = !1, this.italics = !1, this.background = "black", this.flash = !1;
	}
	setStyles(e) {
		let t = [
			"foreground",
			"underline",
			"italics",
			"background",
			"flash"
		];
		for (let n = 0; n < t.length; n++) {
			let r = t[n];
			e.hasOwnProperty(r) && (this[r] = e[r]);
		}
	}
	isDefault() {
		return this.foreground === "white" && !this.underline && !this.italics && this.background === "black" && !this.flash;
	}
	equals(e) {
		return this.foreground === e.foreground && this.underline === e.underline && this.italics === e.italics && this.background === e.background && this.flash === e.flash;
	}
	copy(e) {
		this.foreground = e.foreground, this.underline = e.underline, this.italics = e.italics, this.background = e.background, this.flash = e.flash;
	}
	toString() {
		return "color=" + this.foreground + ", underline=" + this.underline + ", italics=" + this.italics + ", background=" + this.background + ", flash=" + this.flash;
	}
}, cf = class {
	constructor() {
		this.uchar = " ", this.penState = new sf();
	}
	reset() {
		this.uchar = " ", this.penState.reset();
	}
	setChar(e, t) {
		this.uchar = e, this.penState.copy(t);
	}
	setPenState(e) {
		this.penState.copy(e);
	}
	equals(e) {
		return this.uchar === e.uchar && this.penState.equals(e.penState);
	}
	copy(e) {
		this.uchar = e.uchar, this.penState.copy(e.penState);
	}
	isEmpty() {
		return this.uchar === " " && this.penState.isDefault();
	}
}, lf = class {
	constructor(e) {
		this.chars = [], this.pos = 0, this.currPenState = new sf(), this.cueStartTime = null, this.logger = void 0;
		for (let e = 0; e < Qd; e++) this.chars.push(new cf());
		this.logger = e;
	}
	equals(e) {
		for (let t = 0; t < Qd; t++) if (!this.chars[t].equals(e.chars[t])) return !1;
		return !0;
	}
	copy(e) {
		for (let t = 0; t < Qd; t++) this.chars[t].copy(e.chars[t]);
	}
	isEmpty() {
		let e = !0;
		for (let t = 0; t < Qd; t++) if (!this.chars[t].isEmpty()) {
			e = !1;
			break;
		}
		return e;
	}
	setCursor(e) {
		this.pos !== e && (this.pos = e), this.pos < 0 ? (this.logger.log(3, "Negative cursor position " + this.pos), this.pos = 0) : this.pos > Qd && (this.logger.log(3, "Too large cursor position " + this.pos), this.pos = Qd);
	}
	moveCursor(e) {
		let t = this.pos + e;
		if (e > 1) for (let e = this.pos + 1; e < t + 1; e++) this.chars[e].setPenState(this.currPenState);
		this.setCursor(t);
	}
	backSpace() {
		this.moveCursor(-1), this.chars[this.pos].setChar(" ", this.currPenState);
	}
	insertChar(e) {
		e >= 144 && this.backSpace();
		let t = Xd(e);
		this.pos >= Qd ? this.logger.log(0, () => "Cannot insert " + e.toString(16) + " (" + t + ") at position " + this.pos + ". Skipping it!") : (this.chars[this.pos].setChar(t, this.currPenState), this.moveCursor(1));
	}
	clearFromPos(e) {
		let t;
		for (t = e; t < Qd; t++) this.chars[t].reset();
	}
	clear() {
		this.clearFromPos(0), this.pos = 0, this.currPenState.reset();
	}
	clearToEndOfRow() {
		this.clearFromPos(this.pos);
	}
	getTextString() {
		let e = [], t = !0;
		for (let n = 0; n < Qd; n++) {
			let r = this.chars[n].uchar;
			r !== " " && (t = !1), e.push(r);
		}
		return t ? "" : e.join("");
	}
	setPenStyles(e) {
		this.currPenState.setStyles(e), this.chars[this.pos].setPenState(this.currPenState);
	}
}, uf = class {
	constructor(e) {
		this.rows = [], this.currRow = 14, this.nrRollUpRows = null, this.lastOutputScreen = null, this.logger = void 0;
		for (let t = 0; t < Zd; t++) this.rows.push(new lf(e));
		this.logger = e;
	}
	reset() {
		for (let e = 0; e < Zd; e++) this.rows[e].clear();
		this.currRow = 14;
	}
	equals(e) {
		let t = !0;
		for (let n = 0; n < Zd; n++) if (!this.rows[n].equals(e.rows[n])) {
			t = !1;
			break;
		}
		return t;
	}
	copy(e) {
		for (let t = 0; t < Zd; t++) this.rows[t].copy(e.rows[t]);
	}
	isEmpty() {
		let e = !0;
		for (let t = 0; t < Zd; t++) if (!this.rows[t].isEmpty()) {
			e = !1;
			break;
		}
		return e;
	}
	backSpace() {
		this.rows[this.currRow].backSpace();
	}
	clearToEndOfRow() {
		this.rows[this.currRow].clearToEndOfRow();
	}
	insertChar(e) {
		this.rows[this.currRow].insertChar(e);
	}
	setPen(e) {
		this.rows[this.currRow].setPenStyles(e);
	}
	moveCursor(e) {
		this.rows[this.currRow].moveCursor(e);
	}
	setCursor(e) {
		this.logger.log(2, "setCursor: " + e), this.rows[this.currRow].setCursor(e);
	}
	setPAC(e) {
		this.logger.log(2, () => "pacData = " + Fi(e));
		let t = e.row - 1;
		if (this.nrRollUpRows && t < this.nrRollUpRows - 1 && (t = this.nrRollUpRows - 1), this.nrRollUpRows && this.currRow !== t) {
			for (let e = 0; e < Zd; e++) this.rows[e].clear();
			let e = this.currRow + 1 - this.nrRollUpRows, n = this.lastOutputScreen;
			if (n) {
				let r = n.rows[e].cueStartTime, i = this.logger.time;
				if (r !== null && i !== null && r < i) for (let r = 0; r < this.nrRollUpRows; r++) this.rows[t - this.nrRollUpRows + r + 1].copy(n.rows[e + r]);
			}
		}
		this.currRow = t;
		let n = this.rows[this.currRow];
		if (e.indent !== null) {
			let t = e.indent, r = Math.max(t - 1, 0);
			n.setCursor(e.indent), e.color = n.chars[r].penState.foreground;
		}
		let r = {
			foreground: e.color,
			underline: e.underline,
			italics: e.italics,
			background: "black",
			flash: !1
		};
		this.setPen(r);
	}
	setBkgData(e) {
		this.logger.log(2, () => "bkgData = " + Fi(e)), this.backSpace(), this.setPen(e), this.insertChar(32);
	}
	setRollUpRows(e) {
		this.nrRollUpRows = e;
	}
	rollUp() {
		if (this.nrRollUpRows === null) {
			this.logger.log(3, "roll_up but nrRollUpRows not set yet");
			return;
		}
		this.logger.log(1, () => this.getDisplayText());
		let e = this.currRow + 1 - this.nrRollUpRows, t = this.rows.splice(e, 1)[0];
		t.clear(), this.rows.splice(this.currRow, 0, t), this.logger.log(2, "Rolling up");
	}
	getDisplayText(e) {
		e ||= !1;
		let t = [], n = "", r = -1;
		for (let n = 0; n < Zd; n++) {
			let i = this.rows[n].getTextString();
			i && (r = n + 1, e ? t.push("Row " + r + ": '" + i + "'") : t.push(i.trim()));
		}
		return t.length > 0 && (n = e ? "[" + t.join(" | ") + "]" : t.join("\n")), n;
	}
	getTextAndFormat() {
		return this.rows;
	}
}, df = class {
	constructor(e, t, n) {
		this.chNr = void 0, this.outputFilter = void 0, this.mode = void 0, this.verbose = void 0, this.displayedMemory = void 0, this.nonDisplayedMemory = void 0, this.lastOutputScreen = void 0, this.currRollUpRow = void 0, this.writeScreen = void 0, this.cueStartTime = void 0, this.logger = void 0, this.chNr = e, this.outputFilter = t, this.mode = null, this.verbose = 0, this.displayedMemory = new uf(n), this.nonDisplayedMemory = new uf(n), this.lastOutputScreen = new uf(n), this.currRollUpRow = this.displayedMemory.rows[14], this.writeScreen = this.displayedMemory, this.mode = null, this.cueStartTime = null, this.logger = n;
	}
	reset() {
		this.mode = null, this.displayedMemory.reset(), this.nonDisplayedMemory.reset(), this.lastOutputScreen.reset(), this.outputFilter.reset(), this.currRollUpRow = this.displayedMemory.rows[14], this.writeScreen = this.displayedMemory, this.mode = null, this.cueStartTime = null;
	}
	getHandler() {
		return this.outputFilter;
	}
	setHandler(e) {
		this.outputFilter = e;
	}
	setPAC(e) {
		this.writeScreen.setPAC(e);
	}
	setBkgData(e) {
		this.writeScreen.setBkgData(e);
	}
	setMode(e) {
		e !== this.mode && (this.mode = e, this.logger.log(2, () => "MODE=" + e), this.mode === "MODE_POP-ON" ? this.writeScreen = this.nonDisplayedMemory : (this.writeScreen = this.displayedMemory, this.writeScreen.reset()), this.mode !== "MODE_ROLL-UP" && (this.displayedMemory.nrRollUpRows = null, this.nonDisplayedMemory.nrRollUpRows = null), this.mode = e);
	}
	insertChars(e) {
		for (let t = 0; t < e.length; t++) this.writeScreen.insertChar(e[t]);
		let t = this.writeScreen === this.displayedMemory ? "DISP" : "NON_DISP";
		this.logger.log(2, () => t + ": " + this.writeScreen.getDisplayText(!0)), (this.mode === "MODE_PAINT-ON" || this.mode === "MODE_ROLL-UP") && (this.logger.log(1, () => "DISPLAYED: " + this.displayedMemory.getDisplayText(!0)), this.outputDataUpdate());
	}
	ccRCL() {
		this.logger.log(2, "RCL - Resume Caption Loading"), this.setMode("MODE_POP-ON");
	}
	ccBS() {
		this.logger.log(2, "BS - BackSpace"), this.mode !== "MODE_TEXT" && (this.writeScreen.backSpace(), this.writeScreen === this.displayedMemory && this.outputDataUpdate());
	}
	ccAOF() {}
	ccAON() {}
	ccDER() {
		this.logger.log(2, "DER- Delete to End of Row"), this.writeScreen.clearToEndOfRow(), this.outputDataUpdate();
	}
	ccRU(e) {
		this.logger.log(2, "RU(" + e + ") - Roll Up"), this.writeScreen = this.displayedMemory, this.setMode("MODE_ROLL-UP"), this.writeScreen.setRollUpRows(e);
	}
	ccFON() {
		this.logger.log(2, "FON - Flash On"), this.writeScreen.setPen({ flash: !0 });
	}
	ccRDC() {
		this.logger.log(2, "RDC - Resume Direct Captioning"), this.setMode("MODE_PAINT-ON");
	}
	ccTR() {
		this.logger.log(2, "TR"), this.setMode("MODE_TEXT");
	}
	ccRTD() {
		this.logger.log(2, "RTD"), this.setMode("MODE_TEXT");
	}
	ccEDM() {
		this.logger.log(2, "EDM - Erase Displayed Memory"), this.displayedMemory.reset(), this.outputDataUpdate(!0);
	}
	ccCR() {
		this.logger.log(2, "CR - Carriage Return"), this.writeScreen.rollUp(), this.outputDataUpdate(!0);
	}
	ccENM() {
		this.logger.log(2, "ENM - Erase Non-displayed Memory"), this.nonDisplayedMemory.reset();
	}
	ccEOC() {
		if (this.logger.log(2, "EOC - End Of Caption"), this.mode === "MODE_POP-ON") {
			let e = this.displayedMemory;
			this.displayedMemory = this.nonDisplayedMemory, this.nonDisplayedMemory = e, this.writeScreen = this.nonDisplayedMemory, this.logger.log(1, () => "DISP: " + this.displayedMemory.getDisplayText());
		}
		this.outputDataUpdate(!0);
	}
	ccTO(e) {
		this.logger.log(2, "TO(" + e + ") - Tab Offset"), this.writeScreen.moveCursor(e);
	}
	ccMIDROW(e) {
		let t = { flash: !1 };
		t.underline = e % 2 == 1, t.italics = e >= 46, t.foreground = t.italics ? "white" : [
			"white",
			"green",
			"blue",
			"cyan",
			"red",
			"yellow",
			"magenta"
		][Math.floor(e / 2) - 16], this.logger.log(2, "MIDROW: " + Fi(t)), this.writeScreen.setPen(t);
	}
	outputDataUpdate(e = !1) {
		let t = this.logger.time;
		t !== null && this.outputFilter && (this.cueStartTime === null && !this.displayedMemory.isEmpty() ? this.cueStartTime = t : this.displayedMemory.equals(this.lastOutputScreen) || (this.outputFilter.newCue(this.cueStartTime, t, this.lastOutputScreen), e && this.outputFilter.dispatchCue && this.outputFilter.dispatchCue(), this.cueStartTime = this.displayedMemory.isEmpty() ? null : t), this.lastOutputScreen.copy(this.displayedMemory));
	}
	cueSplitAtTime(e) {
		this.outputFilter && (this.displayedMemory.isEmpty() || (this.outputFilter.newCue && this.outputFilter.newCue(this.cueStartTime, e, this.displayedMemory), this.cueStartTime = e));
	}
}, ff = class {
	constructor(e, t, n) {
		this.channels = void 0, this.currentChannel = 0, this.cmdHistory = hf(), this.logger = void 0;
		let r = this.logger = new af();
		this.channels = [
			null,
			new df(e, t, r),
			new df(e + 1, n, r)
		];
	}
	getHandler(e) {
		return this.channels[e].getHandler();
	}
	setHandler(e, t) {
		this.channels[e].setHandler(t);
	}
	addData(e, t) {
		this.logger.time = e;
		for (let e = 0; e < t.length; e += 2) {
			let n = t[e] & 127, r = t[e + 1] & 127, i = !1, a = null;
			if (n === 0 && r === 0) continue;
			this.logger.log(3, () => "[" + of([t[e], t[e + 1]]) + "] -> (" + of([n, r]) + ")");
			let o = this.cmdHistory;
			if (n >= 16 && n <= 31) {
				if (mf(n, r, o)) {
					pf(null, null, o), this.logger.log(3, () => "Repeated command (" + of([n, r]) + ") is dropped");
					continue;
				}
				pf(n, r, this.cmdHistory), i = this.parseCmd(n, r), i ||= this.parseMidrow(n, r), i ||= this.parsePAC(n, r), i ||= this.parseBackgroundAttributes(n, r);
			} else pf(null, null, o);
			if (!i && (a = this.parseChars(n, r), a)) {
				let e = this.currentChannel;
				e && e > 0 ? this.channels[e].insertChars(a) : this.logger.log(2, "No channel found yet. TEXT-MODE?");
			}
			!i && !a && this.logger.log(2, () => "Couldn't parse cleaned data " + of([n, r]) + " orig: " + of([t[e], t[e + 1]]));
		}
	}
	parseCmd(e, t) {
		if (!((e === 20 || e === 28 || e === 21 || e === 29) && t >= 32 && t <= 47 || (e === 23 || e === 31) && t >= 33 && t <= 35)) return !1;
		let n = e === 20 || e === 21 || e === 23 ? 1 : 2, r = this.channels[n];
		return e === 20 || e === 21 || e === 28 || e === 29 ? t === 32 ? r.ccRCL() : t === 33 ? r.ccBS() : t === 34 ? r.ccAOF() : t === 35 ? r.ccAON() : t === 36 ? r.ccDER() : t === 37 ? r.ccRU(2) : t === 38 ? r.ccRU(3) : t === 39 ? r.ccRU(4) : t === 40 ? r.ccFON() : t === 41 ? r.ccRDC() : t === 42 ? r.ccTR() : t === 43 ? r.ccRTD() : t === 44 ? r.ccEDM() : t === 45 ? r.ccCR() : t === 46 ? r.ccENM() : t === 47 && r.ccEOC() : r.ccTO(t - 32), this.currentChannel = n, !0;
	}
	parseMidrow(e, t) {
		let n = 0;
		if ((e === 17 || e === 25) && t >= 32 && t <= 47) {
			if (n = e === 17 ? 1 : 2, n !== this.currentChannel) return this.logger.log(0, "Mismatch channel in midrow parsing"), !1;
			let r = this.channels[n];
			return r ? (r.ccMIDROW(t), this.logger.log(3, () => "MIDROW (" + of([e, t]) + ")"), !0) : !1;
		}
		return !1;
	}
	parsePAC(e, t) {
		let n;
		if (!((e >= 17 && e <= 23 || e >= 25 && e <= 31) && t >= 64 && t <= 127 || (e === 16 || e === 24) && t >= 64 && t <= 95)) return !1;
		let r = e <= 23 ? 1 : 2;
		n = t >= 64 && t <= 95 ? r === 1 ? $d[e] : tf[e] : r === 1 ? ef[e] : nf[e];
		let i = this.channels[r];
		return i ? (i.setPAC(this.interpretPAC(n, t)), this.currentChannel = r, !0) : !1;
	}
	interpretPAC(e, t) {
		let n, r = {
			color: null,
			italics: !1,
			indent: null,
			underline: !1,
			row: e
		};
		return n = t > 95 ? t - 96 : t - 64, r.underline = (n & 1) == 1, n <= 13 ? r.color = [
			"white",
			"green",
			"blue",
			"cyan",
			"red",
			"yellow",
			"magenta",
			"white"
		][Math.floor(n / 2)] : n <= 15 ? (r.italics = !0, r.color = "white") : r.indent = Math.floor((n - 16) / 2) * 4, r;
	}
	parseChars(e, t) {
		let n, r = null, i = null;
		if (e >= 25 ? (n = 2, i = e - 8) : (n = 1, i = e), i >= 17 && i <= 19) {
			let e;
			e = i === 17 ? t + 80 : i === 18 ? t + 112 : t + 144, this.logger.log(2, () => "Special char '" + Xd(e) + "' in channel " + n), r = [e];
		} else e >= 32 && e <= 127 && (r = t === 0 ? [e] : [e, t]);
		return r && this.logger.log(3, () => "Char codes =  " + of(r).join(",")), r;
	}
	parseBackgroundAttributes(e, t) {
		if (!((e === 16 || e === 24) && t >= 32 && t <= 47 || (e === 23 || e === 31) && t >= 45 && t <= 47)) return !1;
		let n, r = {};
		e === 16 || e === 24 ? (n = Math.floor((t - 32) / 2), r.background = rf[n], t % 2 == 1 && (r.background += "_semi")) : t === 45 ? r.background = "transparent" : (r.foreground = "black", t === 47 && (r.underline = !0));
		let i = e <= 23 ? 1 : 2;
		return this.channels[i].setBkgData(r), !0;
	}
	reset() {
		for (let e = 0; e < Object.keys(this.channels).length; e++) {
			let t = this.channels[e];
			t && t.reset();
		}
		pf(null, null, this.cmdHistory);
	}
	cueSplitAtTime(e) {
		for (let t = 0; t < this.channels.length; t++) {
			let n = this.channels[t];
			n && n.cueSplitAtTime(e);
		}
	}
};
function pf(e, t, n) {
	n.a = e, n.b = t;
}
function mf(e, t, n) {
	return n.a === e && n.b === t;
}
function hf() {
	return {
		a: null,
		b: null
	};
}
var gf = (function() {
	if (co != null && co.VTTCue) return self.VTTCue;
	let e = [
		"",
		"lr",
		"rl"
	], t = [
		"start",
		"middle",
		"end",
		"left",
		"right"
	];
	function n(e, t) {
		if (typeof t != "string" || !Array.isArray(e)) return !1;
		let n = t.toLowerCase();
		return ~e.indexOf(n) ? n : !1;
	}
	function r(t) {
		return n(e, t);
	}
	function i(e) {
		return n(t, e);
	}
	function a(e, ...t) {
		let n = 1;
		for (; n < arguments.length; n++) {
			let t = arguments[n];
			for (let n in t) e[n] = t[n];
		}
		return e;
	}
	function o(e, t, n) {
		let o = this, s = { enumerable: !0 };
		o.hasBeenReset = !1;
		let c = "", l = !1, u = e, d = t, f = n, p = null, m = "", h = !0, g = "auto", _ = "start", v = 50, y = "middle", b = 50, x = "middle";
		Object.defineProperty(o, "id", a({}, s, {
			get: function() {
				return c;
			},
			set: function(e) {
				c = "" + e;
			}
		})), Object.defineProperty(o, "pauseOnExit", a({}, s, {
			get: function() {
				return l;
			},
			set: function(e) {
				l = !!e;
			}
		})), Object.defineProperty(o, "startTime", a({}, s, {
			get: function() {
				return u;
			},
			set: function(e) {
				if (typeof e != "number") throw TypeError("Start time must be set to a number.");
				u = e, this.hasBeenReset = !0;
			}
		})), Object.defineProperty(o, "endTime", a({}, s, {
			get: function() {
				return d;
			},
			set: function(e) {
				if (typeof e != "number") throw TypeError("End time must be set to a number.");
				d = e, this.hasBeenReset = !0;
			}
		})), Object.defineProperty(o, "text", a({}, s, {
			get: function() {
				return f;
			},
			set: function(e) {
				f = "" + e, this.hasBeenReset = !0;
			}
		})), Object.defineProperty(o, "region", a({}, s, {
			get: function() {
				return p;
			},
			set: function(e) {
				p = e, this.hasBeenReset = !0;
			}
		})), Object.defineProperty(o, "vertical", a({}, s, {
			get: function() {
				return m;
			},
			set: function(e) {
				let t = r(e);
				if (t === !1) throw SyntaxError("An invalid or illegal string was specified.");
				m = t, this.hasBeenReset = !0;
			}
		})), Object.defineProperty(o, "snapToLines", a({}, s, {
			get: function() {
				return h;
			},
			set: function(e) {
				h = !!e, this.hasBeenReset = !0;
			}
		})), Object.defineProperty(o, "line", a({}, s, {
			get: function() {
				return g;
			},
			set: function(e) {
				if (typeof e != "number" && e !== "auto") throw SyntaxError("An invalid number or illegal string was specified.");
				g = e, this.hasBeenReset = !0;
			}
		})), Object.defineProperty(o, "lineAlign", a({}, s, {
			get: function() {
				return _;
			},
			set: function(e) {
				let t = i(e);
				if (!t) throw SyntaxError("An invalid or illegal string was specified.");
				_ = t, this.hasBeenReset = !0;
			}
		})), Object.defineProperty(o, "position", a({}, s, {
			get: function() {
				return v;
			},
			set: function(e) {
				if (e < 0 || e > 100) throw Error("Position must be between 0 and 100.");
				v = e, this.hasBeenReset = !0;
			}
		})), Object.defineProperty(o, "positionAlign", a({}, s, {
			get: function() {
				return y;
			},
			set: function(e) {
				let t = i(e);
				if (!t) throw SyntaxError("An invalid or illegal string was specified.");
				y = t, this.hasBeenReset = !0;
			}
		})), Object.defineProperty(o, "size", a({}, s, {
			get: function() {
				return b;
			},
			set: function(e) {
				if (e < 0 || e > 100) throw Error("Size must be between 0 and 100.");
				b = e, this.hasBeenReset = !0;
			}
		})), Object.defineProperty(o, "align", a({}, s, {
			get: function() {
				return x;
			},
			set: function(e) {
				let t = i(e);
				if (!t) throw SyntaxError("An invalid or illegal string was specified.");
				x = t, this.hasBeenReset = !0;
			}
		})), o.displayState = void 0;
	}
	return o.prototype.getCueAsHTML = function() {
		return self.WebVTT.convertCueToDOMTree(self, this.text);
	}, o;
})(), _f = class {
	decode(e, t) {
		if (!e) return "";
		if (typeof e != "string") throw Error("Error - expected string data.");
		return decodeURIComponent(encodeURIComponent(e));
	}
};
function vf(e) {
	function t(e, t, n, r) {
		return (e | 0) * 3600 + (t | 0) * 60 + (n | 0) + parseFloat(r || 0);
	}
	let n = e.match(/^(?:(\d+):)?(\d{2}):(\d{2})(\.\d+)?/);
	return n ? parseFloat(n[2]) > 59 ? t(n[2], n[3], 0, n[4]) : t(n[1], n[2], n[3], n[4]) : null;
}
var yf = class {
	constructor() {
		this.values = Object.create(null);
	}
	set(e, t) {
		!this.get(e) && t !== "" && (this.values[e] = t);
	}
	get(e, t, n) {
		return n ? this.has(e) ? this.values[e] : t[n] : this.has(e) ? this.values[e] : t;
	}
	has(e) {
		return e in this.values;
	}
	alt(e, t, n) {
		for (let r = 0; r < n.length; ++r) if (t === n[r]) {
			this.set(e, t);
			break;
		}
	}
	integer(e, t) {
		/^-?\d+$/.test(t) && this.set(e, parseInt(t, 10));
	}
	percent(e, t) {
		if (/^([\d]{1,3})(\.[\d]*)?%$/.test(t)) {
			let n = parseFloat(t);
			if (n >= 0 && n <= 100) return this.set(e, n), !0;
		}
		return !1;
	}
};
function bf(e, t, n, r) {
	let i = r ? e.split(r) : [e];
	for (let e in i) {
		if (typeof i[e] != "string") continue;
		let r = i[e].split(n);
		if (r.length !== 2) continue;
		let a = r[0], o = r[1];
		t(a, o);
	}
}
var xf = new gf(0, 0, ""), Sf = xf.align === "middle" ? "middle" : "center";
function Cf(e, t, n) {
	let r = e;
	function i() {
		let t = vf(e);
		if (t === null) throw Error("Malformed timestamp: " + r);
		return e = e.replace(/^[^\sa-zA-Z-]+/, ""), t;
	}
	function a(e, t) {
		let r = new yf();
		bf(e, function(e, t) {
			let i;
			switch (e) {
				case "region":
					for (let i = n.length - 1; i >= 0; i--) if (n[i].id === t) {
						r.set(e, n[i].region);
						break;
					}
					break;
				case "vertical":
					r.alt(e, t, ["rl", "lr"]);
					break;
				case "line":
					i = t.split(","), r.integer(e, i[0]), r.percent(e, i[0]) && r.set("snapToLines", !1), r.alt(e, i[0], ["auto"]), i.length === 2 && r.alt("lineAlign", i[1], [
						"start",
						Sf,
						"end"
					]);
					break;
				case "position":
					i = t.split(","), r.percent(e, i[0]), i.length === 2 && r.alt("positionAlign", i[1], [
						"start",
						Sf,
						"end",
						"line-left",
						"line-right",
						"auto"
					]);
					break;
				case "size":
					r.percent(e, t);
					break;
				case "align": r.alt(e, t, [
					"start",
					Sf,
					"end",
					"left",
					"right"
				]);
			}
		}, /:/, /\s/), t.region = r.get("region", null), t.vertical = r.get("vertical", "");
		let i = r.get("line", "auto");
		i === "auto" && xf.line === -1 && (i = -1), t.line = i, t.lineAlign = r.get("lineAlign", "start"), t.snapToLines = r.get("snapToLines", !0), t.size = r.get("size", 100), t.align = r.get("align", Sf);
		let a = r.get("position", "auto");
		a === "auto" && xf.position === 50 && (a = t.align === "start" || t.align === "left" ? 0 : t.align === "end" || t.align === "right" ? 100 : 50), t.position = a;
	}
	function o() {
		e = e.replace(/^\s+/, "");
	}
	if (o(), t.startTime = i(), o(), e.slice(0, 3) !== "-->") throw Error("Malformed time stamp (time stamps must be separated by '-->'): " + r);
	e = e.slice(3), o(), t.endTime = i(), o(), a(e, t);
}
function wf(e) {
	return e.replace(/<br(?: \/)?>/gi, "\n");
}
var Tf = class {
	constructor() {
		this.state = "INITIAL", this.buffer = "", this.decoder = new _f(), this.regionList = [], this.cue = null, this.oncue = void 0, this.onparsingerror = void 0, this.onflush = void 0;
	}
	parse(e) {
		let t = this;
		e && (t.buffer += t.decoder.decode(e, { stream: !0 }));
		function n() {
			let e = t.buffer, n = 0;
			for (e = wf(e); n < e.length && e[n] !== "\r" && e[n] !== "\n";) ++n;
			let r = e.slice(0, n);
			return e[n] === "\r" && ++n, e[n] === "\n" && ++n, t.buffer = e.slice(n), r;
		}
		function r(e) {
			bf(e, function(e, t) {}, /:/);
		}
		try {
			let e = "";
			if (t.state === "INITIAL") {
				if (!/\r\n|\n/.test(t.buffer)) return this;
				e = n();
				let r = e.match(/^(ï»¿)?WEBVTT([ \t].*)?$/);
				if (!(r != null && r[0])) throw Error("Malformed WebVTT signature.");
				t.state = "HEADER";
			}
			let i = !1;
			for (; t.buffer;) {
				if (!/\r\n|\n/.test(t.buffer)) return this;
				switch (i ? i = !1 : e = n(), t.state) {
					case "HEADER":
						/:/.test(e) ? r(e) : e || (t.state = "ID");
						continue;
					case "NOTE":
						e || (t.state = "ID");
						continue;
					case "ID":
						if (/^NOTE($|[ \t])/.test(e)) {
							t.state = "NOTE";
							break;
						}
						if (!e) continue;
						if (t.cue = new gf(0, 0, ""), t.state = "CUE", e.indexOf("-->") === -1) {
							t.cue.id = e;
							continue;
						}
					case "CUE":
						if (!t.cue) {
							t.state = "BADCUE";
							continue;
						}
						try {
							Cf(e, t.cue, t.regionList);
						} catch {
							t.cue = null, t.state = "BADCUE";
							continue;
						}
						t.state = "CUETEXT";
						continue;
					case "CUETEXT":
						{
							let n = e.indexOf("-->") !== -1;
							if (!e || n && (i = !0)) {
								t.oncue && t.cue && t.oncue(t.cue), t.cue = null, t.state = "ID";
								continue;
							}
							if (t.cue === null) continue;
							t.cue.text && (t.cue.text += "\n"), t.cue.text += e;
						}
						continue;
					case "BADCUE": e || (t.state = "ID");
				}
			}
		} catch {
			t.state === "CUETEXT" && t.cue && t.oncue && t.oncue(t.cue), t.cue = null, t.state = t.state === "INITIAL" ? "BADWEBVTT" : "BADCUE";
		}
		return this;
	}
	flush() {
		let e = this;
		try {
			if ((e.cue || e.state === "HEADER") && (e.buffer += "\n\n", e.parse()), e.state === "INITIAL" || e.state === "BADWEBVTT") throw Error("Malformed WebVTT signature.");
		} catch (t) {
			e.onparsingerror && e.onparsingerror(t);
		}
		return e.onflush && e.onflush(), this;
	}
}, Ef = /\r\n|\n\r|\n|\r/g, Df = function(e, t, n = 0) {
	return e.slice(n, n + t.length) === t;
}, Of = function(e) {
	let t = parseInt(e.slice(-3)), n = parseInt(e.slice(-6, -4)), r = parseInt(e.slice(-9, -7)), i = e.length > 9 ? parseInt(e.substring(0, e.indexOf(":"))) : 0;
	if (!W(t) || !W(n) || !W(r) || !W(i)) throw Error(`Malformed X-TIMESTAMP-MAP: Local:${e}`);
	return t += 1e3 * n, t += 6e4 * r, t += 36e5 * i, t;
};
function kf(e, t, n) {
	return Od(e.toString()) + Od(t.toString()) + Od(n);
}
var Af = function(e, t, n) {
	let r = e[t], i = e[r.prevCC];
	if (!i || !i.new && r.new) e.ccOffset = e.presentationOffset = r.start, r.new = !1;
	else {
		for (; (a = i) != null && a.new;) {
			var a;
			e.ccOffset += r.start - i.start, r.new = !1, r = i, i = e[r.prevCC];
		}
		e.presentationOffset = n;
	}
};
function jf(e, t, n, r, i, a, o) {
	let s = new Tf(), c = Qn(new Uint8Array(e)).trim().replace(Ef, "\n").split("\n"), l = [], u = t ? Qc(t.baseTime, t.timescale) : 0, d = "00:00.000", f = 0, p = 0, m, h = !0;
	s.oncue = function(e) {
		let a = n[r], o = n.ccOffset, s = (f - u) / 9e4;
		if (a != null && a.new && (p === void 0 ? Af(n, r, s) : o = n.ccOffset = a.start), s) {
			if (!t) {
				m = /* @__PURE__ */ Error("Missing initPTS for VTT MPEGTS");
				return;
			}
			o = s - n.presentationOffset;
		}
		let c = e.endTime - e.startTime, d = cl((e.startTime + o - p) * 9e4, i * 9e4) / 9e4;
		e.startTime = Math.max(d, 0), e.endTime = Math.max(d + c, 0);
		let h = e.text.trim();
		e.text = decodeURIComponent(encodeURIComponent(h)), e.id ||= kf(e.startTime, e.endTime, h), e.endTime > 0 && l.push(e);
	}, s.onparsingerror = function(e) {
		m = e;
	}, s.onflush = function() {
		m ? o(m) : a(l);
	}, c.forEach((e) => {
		if (h) {
			if (Df(e, "X-TIMESTAMP-MAP=")) {
				h = !1, e.slice(16).split(",").forEach((e) => {
					Df(e, "LOCAL:") ? d = e.slice(6) : Df(e, "MPEGTS:") && (f = parseInt(e.slice(7)));
				});
				try {
					p = Of(d) / 1e3;
				} catch (e) {
					m = e;
				}
				return;
			}
			e === "" && (h = !1);
		}
		s.parse(e + "\n");
	}), s.flush();
}
var Mf = "stpp.ttml.im1t", Nf = /^(\d{2,}):(\d{2}):(\d{2}):(\d{2})\.?(\d+)?$/, Pf = /^(\d*(?:\.\d*)?)(h|m|s|ms|f|t)$/, Ff = {
	left: "start",
	center: "center",
	right: "end",
	start: "start",
	end: "end"
};
function If(e, t, n, r) {
	let i = Z(new Uint8Array(e), ["mdat"]);
	if (i.length === 0) {
		r(/* @__PURE__ */ Error("Could not parse IMSC1 mdat"));
		return;
	}
	let a = i.map((e) => Qn(e)), o = Xc(t.baseTime, 1, t.timescale);
	try {
		a.forEach((e) => n(Lf(e, o)));
	} catch (e) {
		r(e);
	}
}
function Lf(e, t) {
	let n = new DOMParser().parseFromString(e, "text/xml").getElementsByTagName("tt")[0];
	if (!n) throw Error("Invalid ttml");
	let r = {
		frameRate: 30,
		subFrameRate: 1,
		frameRateMultiplier: 0,
		tickRate: 0
	}, i = Object.keys(r).reduce((e, t) => (e[t] = n.getAttribute(`ttp:${t}`) || r[t], e), {}), a = n.getAttribute("xml:space") !== "preserve", o = zf(Rf(n, "styling", "style")), s = zf(Rf(n, "layout", "region")), c = Rf(n, "body", "[begin]");
	return [].map.call(c, (e) => {
		let n = Bf(e, a);
		if (!n || !e.hasAttribute("begin")) return null;
		let r = Wf(e.getAttribute("begin"), i), c = Wf(e.getAttribute("dur"), i), l = Wf(e.getAttribute("end"), i);
		if (r === null) throw Uf(e);
		if (l === null) {
			if (c === null) throw Uf(e);
			l = r + c;
		}
		let u = new gf(r - t, l - t, n);
		u.id = kf(u.startTime, u.endTime, u.text);
		let d = s[e.getAttribute("region")], f = o[e.getAttribute("style")], p = Vf(d, f, o), { textAlign: m } = p;
		if (m) {
			let e = Ff[m];
			e && (u.lineAlign = e), u.align = m;
		}
		return Fn(u, p), u;
	}).filter((e) => e !== null);
}
function Rf(e, t, n) {
	let r = e.getElementsByTagName(t)[0];
	return r ? [].slice.call(r.querySelectorAll(n)) : [];
}
function zf(e) {
	return e.reduce((e, t) => {
		let n = t.getAttribute("xml:id");
		return n && (e[n] = t), e;
	}, {});
}
function Bf(e, t) {
	return [].slice.call(e.childNodes).reduce((e, n, r) => {
		var i;
		return n.nodeName === "br" && r ? e + "\n" : (i = n.childNodes) != null && i.length ? Bf(n, t) : t ? e + n.textContent.trim().replace(/\s+/g, " ") : e + n.textContent;
	}, "");
}
function Vf(e, t, n) {
	let r = "http://www.w3.org/ns/ttml#styling", i = null, a = [
		"displayAlign",
		"textAlign",
		"color",
		"backgroundColor",
		"fontSize",
		"fontFamily"
	], o = e != null && e.hasAttribute("style") ? e.getAttribute("style") : null;
	return o && n.hasOwnProperty(o) && (i = n[o]), a.reduce((n, a) => {
		let o = Hf(t, r, a) || Hf(e, r, a) || Hf(i, r, a);
		return o && (n[a] = o), n;
	}, {});
}
function Hf(e, t, n) {
	return e && e.hasAttributeNS(t, n) ? e.getAttributeNS(t, n) : null;
}
function Uf(e) {
	return /* @__PURE__ */ Error(`Could not parse ttml timestamp ${e}`);
}
function Wf(e, t) {
	if (!e) return null;
	let n = vf(e);
	return n === null && (Nf.test(e) ? n = Gf(e, t) : Pf.test(e) && (n = Kf(e, t))), n;
}
function Gf(e, t) {
	let n = Nf.exec(e), r = (n[4] | 0) + (n[5] | 0) / t.subFrameRate;
	return (n[1] | 0) * 3600 + (n[2] | 0) * 60 + (n[3] | 0) + r / t.frameRate;
}
function Kf(e, t) {
	let n = Pf.exec(e), r = Number(n[1]);
	switch (n[2]) {
		case "h": return r * 3600;
		case "m": return r * 60;
		case "ms": return r * 1e3;
		case "f": return r / t.frameRate;
		case "t": return r / t.tickRate;
	}
	return r;
}
var qf = class {
	constructor(e, t) {
		this.timelineController = void 0, this.cueRanges = [], this.trackName = void 0, this.startTime = null, this.endTime = null, this.screen = null, this.timelineController = e, this.trackName = t;
	}
	dispatchCue() {
		this.startTime !== null && (this.timelineController.addCues(this.trackName, this.startTime, this.endTime, this.screen, this.cueRanges), this.startTime = null);
	}
	newCue(e, t, n) {
		(this.startTime === null || this.startTime > e) && (this.startTime = e), this.endTime = t, this.screen = n, this.timelineController.createCaptionsTrack(this.trackName);
	}
	reset() {
		this.cueRanges = [], this.startTime = null;
	}
}, Jf = class {
	constructor(e) {
		this.hls = void 0, this.media = null, this.config = void 0, this.enabled = !0, this.Cues = void 0, this.textTracks = [], this.tracks = [], this.initPTS = [], this.unparsedVttFrags = [], this.captionsTracks = {}, this.nonNativeCaptionsTracks = {}, this.cea608Parser1 = void 0, this.cea608Parser2 = void 0, this.lastCc = -1, this.lastSn = -1, this.lastPartIndex = -1, this.prevCC = -1, this.vttCCs = Qf(), this.captionsProperties = void 0, this.hls = e, this.config = e.config, this.Cues = e.config.cueHandler, this.captionsProperties = {
			textTrack1: {
				label: this.config.captionsTextTrack1Label,
				languageCode: this.config.captionsTextTrack1LanguageCode
			},
			textTrack2: {
				label: this.config.captionsTextTrack2Label,
				languageCode: this.config.captionsTextTrack2LanguageCode
			},
			textTrack3: {
				label: this.config.captionsTextTrack3Label,
				languageCode: this.config.captionsTextTrack3LanguageCode
			},
			textTrack4: {
				label: this.config.captionsTextTrack4Label,
				languageCode: this.config.captionsTextTrack4LanguageCode
			}
		}, e.on(q.MEDIA_ATTACHING, this.onMediaAttaching, this), e.on(q.MEDIA_DETACHING, this.onMediaDetaching, this), e.on(q.MANIFEST_LOADING, this.onManifestLoading, this), e.on(q.MANIFEST_LOADED, this.onManifestLoaded, this), e.on(q.SUBTITLE_TRACKS_UPDATED, this.onSubtitleTracksUpdated, this), e.on(q.FRAG_LOADING, this.onFragLoading, this), e.on(q.FRAG_LOADED, this.onFragLoaded, this), e.on(q.FRAG_PARSING_USERDATA, this.onFragParsingUserdata, this), e.on(q.FRAG_DECRYPTED, this.onFragDecrypted, this), e.on(q.INIT_PTS_FOUND, this.onInitPtsFound, this), e.on(q.SUBTITLE_TRACKS_CLEARED, this.onSubtitleTracksCleared, this), e.on(q.BUFFER_FLUSHING, this.onBufferFlushing, this);
	}
	destroy() {
		let { hls: e } = this;
		e.off(q.MEDIA_ATTACHING, this.onMediaAttaching, this), e.off(q.MEDIA_DETACHING, this.onMediaDetaching, this), e.off(q.MANIFEST_LOADING, this.onManifestLoading, this), e.off(q.MANIFEST_LOADED, this.onManifestLoaded, this), e.off(q.SUBTITLE_TRACKS_UPDATED, this.onSubtitleTracksUpdated, this), e.off(q.FRAG_LOADING, this.onFragLoading, this), e.off(q.FRAG_LOADED, this.onFragLoaded, this), e.off(q.FRAG_PARSING_USERDATA, this.onFragParsingUserdata, this), e.off(q.FRAG_DECRYPTED, this.onFragDecrypted, this), e.off(q.INIT_PTS_FOUND, this.onInitPtsFound, this), e.off(q.SUBTITLE_TRACKS_CLEARED, this.onSubtitleTracksCleared, this), e.off(q.BUFFER_FLUSHING, this.onBufferFlushing, this), this.hls = this.config = this.media = null, this.cea608Parser1 = this.cea608Parser2 = void 0;
	}
	initCea608Parsers() {
		let e = new qf(this, "textTrack1"), t = new qf(this, "textTrack2"), n = new qf(this, "textTrack3"), r = new qf(this, "textTrack4");
		this.cea608Parser1 = new ff(1, e, t), this.cea608Parser2 = new ff(3, n, r);
	}
	addCues(e, t, n, r, i) {
		let a = !1;
		for (let e = i.length; e--;) {
			let r = i[e], o = Zf(r[0], r[1], t, n);
			if (o >= 0 && (r[0] = Math.min(r[0], t), r[1] = Math.max(r[1], n), a = !0, o / (n - t) > .5)) return;
		}
		if (a || i.push([t, n]), this.config.renderTextTracksNatively) {
			let i = this.captionsTracks[e];
			this.Cues.newCue(i, t, n, r);
		} else {
			let i = this.Cues.newCue(null, t, n, r);
			this.hls.trigger(q.CUES_PARSED, {
				type: "captions",
				cues: i,
				track: e
			});
		}
	}
	onInitPtsFound(e, { frag: t, id: n, initPTS: r, timescale: i, trackId: a }) {
		let { unparsedVttFrags: o } = this;
		n === Y.MAIN && (this.initPTS[t.cc] = {
			baseTime: r,
			timescale: i,
			trackId: a
		}), o.length && (this.unparsedVttFrags = [], o.forEach((e) => {
			this.initPTS[e.frag.cc] ? this.onFragLoaded(q.FRAG_LOADED, e) : this.hls.trigger(q.SUBTITLE_FRAG_PROCESSED, {
				success: !1,
				frag: e.frag,
				error: /* @__PURE__ */ Error("Subtitle discontinuity domain does not match main")
			});
		}));
	}
	getExistingTrack(e, t) {
		let { media: n } = this;
		if (n) for (let r = 0; r < n.textTracks.length; r++) {
			let i = n.textTracks[r];
			if (Xf(i, {
				name: e,
				lang: t,
				characteristics: "transcribes-spoken-dialog,describes-music-and-sound"
			})) return i;
		}
		return null;
	}
	createCaptionsTrack(e) {
		this.config.renderTextTracksNatively ? this.createNativeTrack(e) : this.createNonNativeTrack(e);
	}
	createNativeTrack(e) {
		if (this.captionsTracks[e]) return;
		let { captionsProperties: t, captionsTracks: n, media: r } = this, { label: i, languageCode: a } = t[e], o = this.getExistingTrack(i, a);
		if (o) n[e] = o, xd(n[e]), yd(n[e], r);
		else {
			let t = this.createTextTrack("captions", i, a);
			t && (t[e] = !0, n[e] = t);
		}
	}
	createNonNativeTrack(e) {
		if (this.nonNativeCaptionsTracks[e]) return;
		let t = this.captionsProperties[e];
		if (!t) return;
		let n = {
			_id: e,
			label: t.label,
			kind: "captions",
			default: t.media ? !!t.media.default : !1,
			closedCaptions: t.media
		};
		this.nonNativeCaptionsTracks[e] = n, this.hls.trigger(q.NON_NATIVE_TEXT_TRACKS_FOUND, { tracks: [n] });
	}
	createTextTrack(e, t, n) {
		let r = this.media;
		if (r) return r.addTextTrack(e, t, n);
	}
	onMediaAttaching(e, t) {
		this.media = t.media, t.mediaSource || this._cleanTracks();
	}
	onMediaDetaching(e, t) {
		let n = !!t.transferMedia;
		if (this.media = null, n) return;
		let { captionsTracks: r } = this;
		Object.keys(r).forEach((e) => {
			xd(r[e]), delete r[e];
		}), this.nonNativeCaptionsTracks = {};
	}
	onManifestLoading() {
		this.lastCc = -1, this.lastSn = -1, this.lastPartIndex = -1, this.prevCC = -1, this.vttCCs = Qf(), this._cleanTracks(), this.tracks = [], this.captionsTracks = {}, this.nonNativeCaptionsTracks = {}, this.textTracks = [], this.unparsedVttFrags = [], this.initPTS = [], this.cea608Parser1 && this.cea608Parser2 && (this.cea608Parser1.reset(), this.cea608Parser2.reset());
	}
	_cleanTracks() {
		let { media: e } = this;
		if (!e) return;
		let t = e.textTracks;
		if (t) for (let e = 0; e < t.length; e++) xd(t[e]);
	}
	onSubtitleTracksUpdated(e, t) {
		let n = t.subtitleTracks || [], r = n.some((e) => e.textCodec === Mf);
		if (this.config.enableWebVTT || r && this.config.enableIMSC1) {
			if (kl(this.tracks, n)) {
				this.tracks = n;
				return;
			}
			if (this.textTracks = [], this.tracks = n, this.config.renderTextTracksNatively) {
				let e = this.media, t = e ? Td(e.textTracks) : null;
				if (this.tracks.forEach((e, n) => {
					let r;
					if (t) {
						let n = null;
						for (let r = 0; r < t.length; r++) if (t[r] && Xf(t[r], e)) {
							n = t[r], t[r] = null;
							break;
						}
						n && (r = n);
					}
					if (r) xd(r);
					else {
						let t = Yf(e);
						r = this.createTextTrack(t, e.name, e.lang), r && (r.mode = "disabled");
					}
					r && this.textTracks.push(r);
				}), t != null && t.length) {
					let e = t.filter((e) => e !== null).map((e) => e.label);
					e.length && this.hls.logger.warn(`Media element contains unused subtitle tracks: ${e.join(", ")}. Replace media element for each source to clear TextTracks and captions menu.`);
				}
			} else if (this.tracks.length) {
				let e = this.tracks.map((e) => ({
					label: e.name,
					kind: e.type.toLowerCase(),
					default: e.default,
					subtitleTrack: e
				}));
				this.hls.trigger(q.NON_NATIVE_TEXT_TRACKS_FOUND, { tracks: e });
			}
		}
	}
	onManifestLoaded(e, t) {
		this.config.enableCEA708Captions && t.captions && t.captions.forEach((e) => {
			let t = /(?:CC|SERVICE)([1-4])/.exec(e.instreamId);
			if (!t) return;
			let n = `textTrack${t[1]}`, r = this.captionsProperties[n];
			r && (r.label = e.name, e.lang && (r.languageCode = e.lang), r.media = e);
		});
	}
	closedCaptionsForLevel(e) {
		return this.hls.levels[e.level]?.attrs["CLOSED-CAPTIONS"];
	}
	onFragLoading(e, t) {
		if (this.enabled && t.frag.type === Y.MAIN) {
			let { cea608Parser1: e, cea608Parser2: n, lastSn: r } = this, { cc: i, sn: a } = t.frag, o = t.part?.index ?? -1;
			e && n && (a !== r + 1 || a === r && o !== this.lastPartIndex + 1 || i !== this.lastCc) && (e.reset(), n.reset()), this.lastCc = i, this.lastSn = a, this.lastPartIndex = o;
		}
	}
	onFragLoaded(e, t) {
		let { frag: n, payload: r } = t;
		if (n.type === Y.SUBTITLE) {
			if (r.byteLength) {
				let e = n.decryptdata, i = "stats" in t;
				if (e == null || !e.encrypted || i) {
					let e = this.tracks[n.level], i = this.vttCCs;
					i[n.cc] || (i[n.cc] = {
						start: n.start,
						prevCC: this.prevCC,
						new: !0
					}, this.prevCC = n.cc), e && e.textCodec === Mf ? this._parseIMSC1(n, r) : this._parseVTTs(t);
				}
			} else this.hls.trigger(q.SUBTITLE_FRAG_PROCESSED, {
				success: !1,
				frag: n,
				error: /* @__PURE__ */ Error("Empty subtitle payload")
			});
		}
	}
	_parseIMSC1(e, t) {
		let n = this.hls;
		If(t, this.initPTS[e.cc], (t) => {
			this._appendCues(t, e.level), n.trigger(q.SUBTITLE_FRAG_PROCESSED, {
				success: !0,
				frag: e
			});
		}, (t) => {
			n.logger.log(`Failed to parse IMSC1: ${t}`), n.trigger(q.SUBTITLE_FRAG_PROCESSED, {
				success: !1,
				frag: e,
				error: t
			});
		});
	}
	_parseVTTs(e) {
		var t;
		let { frag: n, payload: r } = e, { initPTS: i, unparsedVttFrags: a } = this, o = i.length - 1;
		if (!i[n.cc] && o === -1) {
			a.push(e);
			return;
		}
		let s = this.hls;
		jf((t = n.initSegment) != null && t.data ? Ir(n.initSegment.data, new Uint8Array(r)).buffer : r, this.initPTS[n.cc], this.vttCCs, n.cc, n.start, (e) => {
			this._appendCues(e, n.level), s.trigger(q.SUBTITLE_FRAG_PROCESSED, {
				success: !0,
				frag: n
			});
		}, (t) => {
			let i = t.message === "Missing initPTS for VTT MPEGTS";
			i ? a.push(e) : this._fallbackToIMSC1(n, r), s.logger.log(`Failed to parse VTT cue: ${t}`), i && o > n.cc || s.trigger(q.SUBTITLE_FRAG_PROCESSED, {
				success: !1,
				frag: n,
				error: t
			});
		});
	}
	_fallbackToIMSC1(e, t) {
		let n = this.tracks[e.level];
		n.textCodec || If(t, this.initPTS[e.cc], () => {
			n.textCodec = Mf, this._parseIMSC1(e, t);
		}, () => {
			n.textCodec = "wvtt";
		});
	}
	_appendCues(e, t) {
		let n = this.hls;
		if (this.config.renderTextTracksNatively) {
			let n = this.textTracks[t];
			if (!n || n.mode === "disabled") return;
			e.forEach((e) => bd(n, e));
		} else {
			let r = this.tracks[t];
			if (!r) return;
			let i = r.default ? "default" : "subtitles" + t;
			n.trigger(q.CUES_PARSED, {
				type: "subtitles",
				cues: e,
				track: i
			});
		}
	}
	onFragDecrypted(e, t) {
		let { frag: n } = t;
		n.type === Y.SUBTITLE && this.onFragLoaded(q.FRAG_LOADED, t);
	}
	onSubtitleTracksCleared() {
		this.tracks = [], this.captionsTracks = {};
	}
	onFragParsingUserdata(e, t) {
		if (!this.enabled || !this.config.enableCEA708Captions) return;
		let { frag: n, samples: r } = t;
		if (n.type !== Y.MAIN || this.closedCaptionsForLevel(n) !== "NONE") for (let e = 0; e < r.length; e++) {
			let t = r[e].bytes;
			if (t) {
				this.cea608Parser1 || this.initCea608Parsers();
				let n = this.extractCea608Data(t);
				this.cea608Parser1.addData(r[e].pts, n[0]), this.cea608Parser2.addData(r[e].pts, n[1]);
			}
		}
	}
	onBufferFlushing(e, { startOffset: t, endOffset: n, endOffsetSubtitles: r, type: i }) {
		let { media: a } = this;
		if (!(!a || a.currentTime < n)) {
			if (!i || i === "video") {
				let { captionsTracks: e } = this;
				Object.keys(e).forEach((r) => Sd(e[r], t, n));
			}
			if (this.config.renderTextTracksNatively && t === 0 && r !== void 0) {
				let { textTracks: e } = this;
				Object.keys(e).forEach((n) => Sd(e[n], t, r));
			}
		}
	}
	extractCea608Data(e) {
		let t = [[], []], n = e[0] & 31, r = 2;
		for (let i = 0; i < n; i++) {
			let n = e[r++], i = 127 & e[r++], a = 127 & e[r++];
			if ((i !== 0 || a !== 0) && 4 & n) {
				let e = 3 & n;
				(e === 0 || e === 1) && (t[e].push(i), t[e].push(a));
			}
		}
		return t;
	}
};
function Yf(e) {
	return e.characteristics && /transcribes-spoken-dialog/gi.test(e.characteristics) && /describes-music-and-sound/gi.test(e.characteristics) ? "captions" : "subtitles";
}
function Xf(e, t) {
	return !!e && e.kind === Yf(t) && jl(t, e);
}
function Zf(e, t, n, r) {
	return Math.min(t, r) - Math.max(e, n);
}
function Qf() {
	return {
		ccOffset: 0,
		presentationOffset: 0,
		0: {
			start: 0,
			prevCC: -1,
			new: !0
		}
	};
}
var $f = /\s/, ep = { newCue(e, t, n, r) {
	let i = [], a, o, s, c, l, u = self.VTTCue || self.TextTrackCue;
	for (let f = 0; f < r.rows.length; f++) if (a = r.rows[f], s = !0, c = 0, l = "", !a.isEmpty()) {
		var d;
		for (let e = 0; e < a.chars.length; e++) $f.test(a.chars[e].uchar) && s ? c++ : (l += a.chars[e].uchar, s = !1);
		a.cueStartTime = t, t === n && (n += 1e-4), c >= 16 ? c-- : c++;
		let r = wf(l.trim()), p = kf(t, n, r);
		e != null && (d = e.cues) != null && d.getCueById(p) || (o = new u(t, n, r), o.id = p, o.line = f + 1, o.align = "left", o.position = 10 + Math.min(80, Math.floor(c * 8 / 32) * 10), i.push(o));
	}
	return e && i.length && (i.sort((e, t) => e.line === "auto" || t.line === "auto" ? 0 : e.line > 8 && t.line > 8 ? t.line - e.line : e.line - t.line), i.forEach((t) => bd(e, t))), i;
} };
function tp() {
	if (self.fetch && self.AbortController && self.ReadableStream && self.Request) try {
		return new self.ReadableStream({}), !0;
	} catch {}
	return !1;
}
var np = /(\d+)-(\d+)\/(\d+)/, rp = class {
	constructor(e) {
		this.fetchSetup = void 0, this.requestTimeout = void 0, this.request = null, this.response = null, this.controller = void 0, this.context = null, this.config = null, this.callbacks = null, this.stats = void 0, this.loader = null, this.fetchSetup = e.fetchSetup || sp, this.controller = new self.AbortController(), this.stats = new or();
	}
	destroy() {
		this.loader = this.callbacks = this.context = this.config = this.request = null, this.abortInternal(), this.response = null, this.fetchSetup = this.controller = this.stats = null;
	}
	abortInternal() {
		this.controller && !this.stats.loading.end && (this.stats.aborted = !0, this.controller.abort());
	}
	abort() {
		var e;
		this.abortInternal(), (e = this.callbacks) != null && e.onAbort && this.callbacks.onAbort(this.stats, this.context, this.response);
	}
	load(e, t, n) {
		let r = this.stats;
		if (r.loading.start) throw Error("Loader can only be used once.");
		r.loading.start = self.performance.now();
		let i = ip(e, this.controller.signal), a = e.responseType === "arraybuffer", o = a ? "byteLength" : "length", { maxTimeToFirstByteMs: s, maxLoadTimeMs: c } = t.loadPolicy;
		this.context = e, this.config = t, this.callbacks = n, this.request = this.fetchSetup(e, i), self.clearTimeout(this.requestTimeout), t.timeout = s && W(s) ? s : c, this.requestTimeout = self.setTimeout(() => {
			this.callbacks && (this.abortInternal(), this.callbacks.onTimeout(r, e, this.response));
		}, t.timeout), (xl(this.request) ? this.request.then(self.fetch) : self.fetch(this.request)).then((n) => {
			this.response = this.loader = n;
			let i = Math.max(self.performance.now(), r.loading.start);
			if (self.clearTimeout(this.requestTimeout), t.timeout = c, this.requestTimeout = self.setTimeout(() => {
				this.callbacks && (this.abortInternal(), this.callbacks.onTimeout(r, e, this.response));
			}, c - (i - r.loading.start)), !n.ok) {
				let { status: e, statusText: t } = n;
				throw new cp(t || "fetch, bad network response", e, n);
			}
			r.loading.first = i, r.total = op(n.headers) || r.total;
			let o = this.callbacks?.onProgress;
			return o && W(t.highWaterMark) ? this.loadProgressively(n, r, e, t.highWaterMark, o) : a ? n.arrayBuffer() : e.responseType === "json" ? n.json() : n.text();
		}).then((n) => {
			var i;
			let a = this.response;
			if (!a) throw Error("loader destroyed");
			self.clearTimeout(this.requestTimeout), r.loading.end = Math.max(self.performance.now(), r.loading.first);
			let s = n[o];
			s && (r.loaded = r.total = s);
			let c = {
				url: a.url,
				data: n,
				code: a.status
			}, l = this.callbacks?.onProgress;
			l && !W(t.highWaterMark) && l(r, e, n, a), (i = this.callbacks) == null || i.onSuccess(c, r, e, a);
		}).catch((t) => {
			var n;
			if (self.clearTimeout(this.requestTimeout), r.aborted) return;
			let i = t && t.code || 0, a = t ? t.message : null;
			(n = this.callbacks) == null || n.onError({
				code: i,
				text: a
			}, e, t ? t.details : null, r);
		});
	}
	getCacheAge() {
		let e = null;
		if (this.response) {
			let t = this.response.headers.get("age");
			e = t ? parseFloat(t) : null;
		}
		return e;
	}
	getResponseHeader(e) {
		return this.response ? this.response.headers.get(e) : null;
	}
	loadProgressively(e, t, n, r = 0, i) {
		let a = new _s(), o = e.body.getReader(), s = () => o.read().then((o) => {
			if (o.done) return a.dataLength && i(t, n, a.flush().buffer, e), Promise.resolve(/* @__PURE__ */ new ArrayBuffer(0));
			let c = o.value, l = c.length;
			return t.loaded += l, l < r || a.dataLength ? (a.push(c), a.dataLength >= r && i(t, n, a.flush().buffer, e)) : i(t, n, c.buffer, e), s();
		}).catch(() => Promise.reject());
		return s();
	}
};
function ip(e, t) {
	let n = {
		method: "GET",
		mode: "cors",
		credentials: "same-origin",
		signal: t,
		headers: new self.Headers(Fn({}, e.headers))
	};
	return e.rangeEnd && n.headers.set("Range", "bytes=" + e.rangeStart + "-" + String(e.rangeEnd - 1)), n;
}
function ap(e) {
	let t = np.exec(e);
	if (t) return parseInt(t[2]) - parseInt(t[1]) + 1;
}
function op(e) {
	let t = e.get("Content-Range");
	if (t) {
		let e = ap(t);
		if (W(e)) return e;
	}
	let n = e.get("Content-Length");
	if (n) return parseInt(n);
}
function sp(e, t) {
	return new self.Request(e.url, t);
}
var cp = class extends Error {
	constructor(e, t, n) {
		super(e), this.code = void 0, this.details = void 0, this.code = t, this.details = n;
	}
}, lp = /^age:\s*[\d.]+\s*$/im, up = class {
	constructor(e) {
		this.xhrSetup = void 0, this.requestTimeout = void 0, this.retryTimeout = void 0, this.retryDelay = void 0, this.config = null, this.callbacks = null, this.context = null, this.loader = null, this.stats = void 0, this.xhrSetup = e && e.xhrSetup || null, this.stats = new or(), this.retryDelay = 0;
	}
	destroy() {
		this.callbacks = null, this.abortInternal(), this.loader = null, this.config = null, this.context = null, this.xhrSetup = null;
	}
	abortInternal() {
		let e = this.loader;
		self.clearTimeout(this.requestTimeout), self.clearTimeout(this.retryTimeout), e && (e.onreadystatechange = null, e.onprogress = null, e.readyState !== 4 && (this.stats.aborted = !0, e.abort()));
	}
	abort() {
		var e;
		this.abortInternal(), (e = this.callbacks) != null && e.onAbort && this.callbacks.onAbort(this.stats, this.context, this.loader);
	}
	load(e, t, n) {
		if (this.stats.loading.start) throw Error("Loader can only be used once.");
		this.stats.loading.start = self.performance.now(), this.context = e, this.config = t, this.callbacks = n, this.loadInternal();
	}
	loadInternal() {
		let { config: e, context: t } = this;
		if (!e || !t) return;
		let n = this.loader = new self.XMLHttpRequest(), r = this.stats;
		r.loading.first = 0, r.loaded = 0, r.aborted = !1;
		let i = this.xhrSetup;
		i ? Promise.resolve().then(() => {
			if (!(this.loader !== n || this.stats.aborted)) return i(n, t.url);
		}).catch((e) => {
			if (!(this.loader !== n || this.stats.aborted)) return n.open("GET", t.url, !0), i(n, t.url);
		}).then(() => {
			this.loader !== n || this.stats.aborted || this.openAndSendXhr(n, t, e);
		}).catch((e) => {
			var i;
			(i = this.callbacks) == null || i.onError({
				code: n.status,
				text: e.message
			}, t, n, r);
		}) : this.openAndSendXhr(n, t, e);
	}
	openAndSendXhr(e, t, n) {
		e.readyState || e.open("GET", t.url, !0);
		let r = t.headers, { maxTimeToFirstByteMs: i, maxLoadTimeMs: a } = n.loadPolicy;
		if (r) for (let t in r) e.setRequestHeader(t, r[t]);
		t.rangeEnd && e.setRequestHeader("Range", "bytes=" + t.rangeStart + "-" + (t.rangeEnd - 1)), e.onreadystatechange = this.readystatechange.bind(this), e.onprogress = this.loadprogress.bind(this), e.responseType = t.responseType, self.clearTimeout(this.requestTimeout), n.timeout = i && W(i) ? i : a, this.requestTimeout = self.setTimeout(this.loadtimeout.bind(this), n.timeout), e.send();
	}
	readystatechange() {
		let { context: e, loader: t, stats: n } = this;
		if (!e || !t) return;
		let r = t.readyState, i = this.config;
		if (!n.aborted && r >= 2 && (n.loading.first === 0 && (n.loading.first = Math.max(self.performance.now(), n.loading.start), i.timeout !== i.loadPolicy.maxLoadTimeMs && (self.clearTimeout(this.requestTimeout), i.timeout = i.loadPolicy.maxLoadTimeMs, this.requestTimeout = self.setTimeout(this.loadtimeout.bind(this), i.loadPolicy.maxLoadTimeMs - (n.loading.first - n.loading.start)))), r === 4)) {
			self.clearTimeout(this.requestTimeout), t.onreadystatechange = null, t.onprogress = null;
			let r = t.status, s = t.responseType === "text" ? t.responseText : null;
			if (r >= 200 && r < 300) {
				let i = s ?? t.response;
				if (i != null) {
					var a;
					n.loading.end = Math.max(self.performance.now(), n.loading.first), n.loaded = n.total = t.responseType === "arraybuffer" ? i.byteLength : i.length, n.bwEstimate = n.total * 8e3 / (n.loading.end - n.loading.first);
					let o = this.callbacks?.onProgress;
					o && o(n, e, i, t);
					let s = {
						url: t.responseURL,
						data: i,
						code: r
					};
					(a = this.callbacks) == null || a.onSuccess(s, n, e, t);
					return;
				}
			}
			let c = i.loadPolicy.errorRetry, l = n.retry;
			if (la(c, l, !1, {
				url: e.url,
				data: void 0,
				code: r
			})) this.retry(c);
			else {
				var o;
				Jn.error(`${r} while loading ${e.url}`), (o = this.callbacks) == null || o.onError({
					code: r,
					text: t.statusText
				}, e, t, n);
			}
		}
	}
	loadtimeout() {
		if (!this.config) return;
		let e = this.config.loadPolicy.timeoutRetry, t = this.stats.retry;
		if (la(e, t, !0)) this.retry(e);
		else {
			Jn.warn(`timeout while loading ${this.context?.url}`);
			let e = this.callbacks;
			e && (this.abortInternal(), e.onTimeout(this.stats, this.context, this.loader));
		}
	}
	retry(e) {
		let { context: t, stats: n } = this;
		this.retryDelay = sa(e, n.retry), n.retry++, Jn.warn(`${status ? "HTTP Status " + status : "Timeout"} while loading ${t?.url}, retrying ${n.retry}/${e.maxNumRetry} in ${this.retryDelay}ms`), this.abortInternal(), this.loader = null, self.clearTimeout(this.retryTimeout), this.retryTimeout = self.setTimeout(this.loadInternal.bind(this), this.retryDelay);
	}
	loadprogress(e) {
		let t = this.stats;
		t.loaded = e.loaded, e.lengthComputable && (t.total = e.total);
	}
	getCacheAge() {
		let e = null;
		if (this.loader && lp.test(this.loader.getAllResponseHeaders())) {
			let t = this.loader.getResponseHeader("age");
			e = t ? parseFloat(t) : null;
		}
		return e;
	}
	getResponseHeader(e) {
		return this.loader && RegExp(`^${e}:\\s*[\\d.]+\\s*$`, "im").test(this.loader.getAllResponseHeaders()) ? this.loader.getResponseHeader(e) : null;
	}
}, dp = Ln(Ln({
	autoStartLoad: !0,
	startPosition: -1,
	defaultAudioCodec: void 0,
	debug: !1,
	capLevelOnFPSDrop: !1,
	capLevelToPlayerSize: !1,
	ignoreDevicePixelRatio: !1,
	maxDevicePixelRatio: Infinity,
	preferManagedMediaSource: !0,
	initialLiveManifestSize: 1,
	maxBufferLength: 30,
	backBufferLength: Infinity,
	frontBufferFlushThreshold: Infinity,
	startOnSegmentBoundary: !1,
	maxBufferSize: 6e7,
	maxFragLookUpTolerance: .25,
	maxBufferHole: .1,
	detectStallWithCurrentTimeMs: 1250,
	highBufferWatchdogPeriod: 2,
	nudgeOffset: .1,
	nudgeMaxRetry: 3,
	nudgeOnVideoHole: !0,
	liveSyncMode: "edge",
	liveSyncDurationCount: 3,
	liveSyncOnStallIncrease: 1,
	liveMaxLatencyDurationCount: Infinity,
	liveSyncDuration: void 0,
	liveMaxLatencyDuration: void 0,
	maxLiveSyncPlaybackRate: 1,
	liveDurationInfinity: !1,
	liveBackBufferLength: null,
	maxMaxBufferLength: 600,
	enableWorker: !0,
	workerPath: null,
	enableSoftwareAES: !0,
	startLevel: void 0,
	startFragPrefetch: !1,
	fpsDroppedMonitoringPeriod: 5e3,
	fpsDroppedMonitoringThreshold: .2,
	appendErrorMaxRetry: 3,
	ignorePlaylistParsingErrors: !1,
	loader: up,
	fLoader: void 0,
	pLoader: void 0,
	xhrSetup: void 0,
	licenseXhrSetup: void 0,
	licenseResponseCallback: void 0,
	abrController: Yi,
	bufferController: Ll,
	capLevelController: Vl,
	errorController: ma,
	fpsController: vd,
	stretchShortVideoTrack: !1,
	maxAudioFramesDrift: 1,
	forceKeyFrameOnDiscontinuity: !0,
	abrEwmaFastLive: 3,
	abrEwmaSlowLive: 9,
	abrEwmaFastVoD: 3,
	abrEwmaSlowVoD: 9,
	abrEwmaDefaultEstimate: 5e5,
	abrEwmaDefaultEstimateMax: 5e6,
	abrBandWidthFactor: .95,
	abrBandWidthUpFactor: .7,
	abrMaxWithRealBitrate: !1,
	maxStarvationDelay: 4,
	maxLoadingDelay: 4,
	minAutoBitrate: 0,
	emeEnabled: !1,
	widevineLicenseUrl: void 0,
	drmSystems: {},
	drmSystemOptions: {},
	requestMediaKeySystemAccessFunc: ho,
	requireKeySystemAccessOnStart: !1,
	testBandwidth: !0,
	progressive: !1,
	lowLatencyMode: !0,
	cmcd: void 0,
	enableDateRangeMetadataCues: !0,
	enableEmsgMetadataCues: !0,
	enableEmsgKLVMetadata: !1,
	enableID3MetadataCues: !0,
	enableInterstitialPlayback: !0,
	interstitialAppendInPlace: !0,
	interstitialLiveLookAhead: 10,
	useMediaCapabilities: !0,
	preserveManualLevelOnError: !1,
	certLoadPolicy: { default: {
		maxTimeToFirstByteMs: 8e3,
		maxLoadTimeMs: 2e4,
		timeoutRetry: null,
		errorRetry: null
	} },
	keyLoadPolicy: { default: {
		maxTimeToFirstByteMs: 8e3,
		maxLoadTimeMs: 2e4,
		timeoutRetry: {
			maxNumRetry: 1,
			retryDelayMs: 1e3,
			maxRetryDelayMs: 2e4,
			backoff: "linear"
		},
		errorRetry: {
			maxNumRetry: 8,
			retryDelayMs: 1e3,
			maxRetryDelayMs: 2e4,
			backoff: "linear"
		}
	} },
	manifestLoadPolicy: { default: {
		maxTimeToFirstByteMs: Infinity,
		maxLoadTimeMs: 2e4,
		timeoutRetry: {
			maxNumRetry: 2,
			retryDelayMs: 0,
			maxRetryDelayMs: 0
		},
		errorRetry: {
			maxNumRetry: 1,
			retryDelayMs: 1e3,
			maxRetryDelayMs: 8e3
		}
	} },
	playlistLoadPolicy: { default: {
		maxTimeToFirstByteMs: 1e4,
		maxLoadTimeMs: 2e4,
		timeoutRetry: {
			maxNumRetry: 2,
			retryDelayMs: 0,
			maxRetryDelayMs: 0
		},
		errorRetry: {
			maxNumRetry: 2,
			retryDelayMs: 1e3,
			maxRetryDelayMs: 8e3
		}
	} },
	fragLoadPolicy: { default: {
		maxTimeToFirstByteMs: 1e4,
		maxLoadTimeMs: 12e4,
		timeoutRetry: {
			maxNumRetry: 4,
			retryDelayMs: 0,
			maxRetryDelayMs: 0
		},
		errorRetry: {
			maxNumRetry: 6,
			retryDelayMs: 1e3,
			maxRetryDelayMs: 8e3
		}
	} },
	steeringManifestLoadPolicy: { default: {
		maxTimeToFirstByteMs: 1e4,
		maxLoadTimeMs: 2e4,
		timeoutRetry: {
			maxNumRetry: 2,
			retryDelayMs: 0,
			maxRetryDelayMs: 0
		},
		errorRetry: {
			maxNumRetry: 1,
			retryDelayMs: 1e3,
			maxRetryDelayMs: 8e3
		}
	} },
	interstitialAssetListLoadPolicy: { default: {
		maxTimeToFirstByteMs: 1e4,
		maxLoadTimeMs: 3e4,
		timeoutRetry: {
			maxNumRetry: 0,
			retryDelayMs: 0,
			maxRetryDelayMs: 0
		},
		errorRetry: {
			maxNumRetry: 0,
			retryDelayMs: 1e3,
			maxRetryDelayMs: 8e3
		}
	} },
	manifestLoadingTimeOut: 1e4,
	manifestLoadingMaxRetry: 1,
	manifestLoadingRetryDelay: 1e3,
	manifestLoadingMaxRetryTimeout: 64e3,
	levelLoadingTimeOut: 1e4,
	levelLoadingMaxRetry: 4,
	levelLoadingRetryDelay: 1e3,
	levelLoadingMaxRetryTimeout: 64e3,
	fragLoadingTimeOut: 2e4,
	fragLoadingMaxRetry: 6,
	fragLoadingRetryDelay: 1e3,
	fragLoadingMaxRetryTimeout: 64e3
}, fp()), {}, {
	subtitleStreamController: qd,
	subtitleTrackController: Ed,
	timelineController: Jf,
	audioStreamController: Dl,
	audioTrackController: Ml,
	emeController: pd,
	cmcdController: cd,
	contentSteeringController: ud,
	interstitialsController: Gd
});
function fp() {
	return {
		cueHandler: ep,
		enableWebVTT: !0,
		enableIMSC1: !0,
		enableCEA708Captions: !0,
		captionsTextTrack1Label: "English",
		captionsTextTrack1LanguageCode: "en",
		captionsTextTrack2Label: "Spanish",
		captionsTextTrack2LanguageCode: "es",
		captionsTextTrack3Label: "Unknown CC",
		captionsTextTrack3LanguageCode: "",
		captionsTextTrack4Label: "Unknown CC",
		captionsTextTrack4LanguageCode: "",
		renderTextTracksNatively: !0
	};
}
function pp(e, t, n) {
	if ((t.liveSyncDurationCount || t.liveMaxLatencyDurationCount) && (t.liveSyncDuration || t.liveMaxLatencyDuration)) throw Error("Illegal hls.js config: don't mix up liveSyncDurationCount/liveMaxLatencyDurationCount and liveSyncDuration/liveMaxLatencyDuration");
	if (t.liveMaxLatencyDurationCount !== void 0 && (t.liveSyncDurationCount === void 0 || t.liveMaxLatencyDurationCount <= t.liveSyncDurationCount)) throw Error("Illegal hls.js config: \"liveMaxLatencyDurationCount\" must be greater than \"liveSyncDurationCount\"");
	if (t.liveMaxLatencyDuration !== void 0 && (t.liveSyncDuration === void 0 || t.liveMaxLatencyDuration <= t.liveSyncDuration)) throw Error("Illegal hls.js config: \"liveMaxLatencyDuration\" must be greater than \"liveSyncDuration\"");
	let r = mp(e), i = [
		"manifest",
		"level",
		"frag"
	], a = [
		"TimeOut",
		"MaxRetry",
		"RetryDelay",
		"MaxRetryTimeout"
	];
	return i.forEach((e) => {
		let i = `${e === "level" ? "playlist" : e}LoadPolicy`, o = t[i] === void 0, s = [];
		a.forEach((n) => {
			let a = `${e}Loading${n}`, c = t[a];
			if (c !== void 0 && o) {
				s.push(a);
				let e = r[i].default;
				switch (t[i] = { default: e }, n) {
					case "TimeOut":
						e.maxLoadTimeMs = c, e.maxTimeToFirstByteMs = c;
						break;
					case "MaxRetry":
						e.errorRetry.maxNumRetry = c, e.timeoutRetry.maxNumRetry = c;
						break;
					case "RetryDelay":
						e.errorRetry.retryDelayMs = c, e.timeoutRetry.retryDelayMs = c;
						break;
					case "MaxRetryTimeout": e.errorRetry.maxRetryDelayMs = c, e.timeoutRetry.maxRetryDelayMs = c;
				}
			}
		}), s.length && n.warn(`hls.js config: "${s.join("\", \"")}" setting(s) are deprecated, use "${i}": ${Fi(t[i])}`);
	}), Ln(Ln({}, r), t);
}
function mp(e) {
	return e && typeof e == "object" ? Array.isArray(e) ? e.map(mp) : Object.keys(e).reduce((t, n) => (t[n] = mp(e[n]), t), {}) : e;
}
function hp(e, t) {
	let n = e.loader;
	n !== rp && n !== up ? (t.log("[config]: Custom loader detected, cannot enable progressive streaming"), e.progressive = !1) : tp() && (e.loader = rp, e.progressive = !0, e.enableSoftwareAES = !0, t.log("[config]: Progressive streaming enabled, using FetchLoader"));
}
var gp = 2, _p = .1, vp = .05, yp = 100, bp = class extends Fa {
	constructor(e, t) {
		super("gap-controller", e.logger), this.hls = void 0, this.fragmentTracker = void 0, this.media = null, this.mediaSource = void 0, this.nudgeRetry = 0, this.stallReported = !1, this.stalled = null, this.moved = !1, this.seeking = !1, this.buffered = {}, this.lastCurrentTime = 0, this.ended = 0, this.waiting = 0, this.onMediaPlaying = () => {
			this.ended = 0, this.waiting = 0;
		}, this.onMediaWaiting = () => {
			var e;
			(e = this.media) != null && e.seeking || (this.waiting = self.performance.now(), this.tick());
		}, this.onMediaEnded = () => {
			this.hls && (this.ended = this.media?.currentTime || 1, this.hls.trigger(q.MEDIA_ENDED, { stalled: !1 }));
		}, this.hls = e, this.fragmentTracker = t, this.registerListeners();
	}
	registerListeners() {
		let { hls: e } = this;
		e && (e.on(q.MEDIA_ATTACHED, this.onMediaAttached, this), e.on(q.MEDIA_DETACHING, this.onMediaDetaching, this), e.on(q.BUFFER_APPENDED, this.onBufferAppended, this));
	}
	unregisterListeners() {
		let { hls: e } = this;
		e && (e.off(q.MEDIA_ATTACHED, this.onMediaAttached, this), e.off(q.MEDIA_DETACHING, this.onMediaDetaching, this), e.off(q.BUFFER_APPENDED, this.onBufferAppended, this));
	}
	destroy() {
		super.destroy(), this.unregisterListeners(), this.media = this.hls = this.fragmentTracker = null, this.mediaSource = void 0;
	}
	onMediaAttached(e, t) {
		this.setInterval(yp), this.mediaSource = t.mediaSource;
		let n = this.media = t.media;
		fs(n, "playing", this.onMediaPlaying), fs(n, "waiting", this.onMediaWaiting), fs(n, "ended", this.onMediaEnded);
	}
	onMediaDetaching(e, t) {
		this.clearInterval();
		let { media: n } = this;
		n && (ps(n, "playing", this.onMediaPlaying), ps(n, "waiting", this.onMediaWaiting), ps(n, "ended", this.onMediaEnded), this.media = null), this.mediaSource = void 0;
	}
	onBufferAppended(e, t) {
		this.buffered = t.timeRanges;
	}
	get hasBuffered() {
		return Object.keys(this.buffered).length > 0;
	}
	tick() {
		var e;
		if (!((e = this.media) != null && e.readyState) || !this.hasBuffered) return;
		let t = this.media.currentTime;
		this.poll(t, this.lastCurrentTime), this.lastCurrentTime = t;
	}
	poll(e, t) {
		let n = this.hls?.config;
		if (!n) return;
		let r = this.media;
		if (!r) return;
		let { seeking: i } = r, a = this.seeking && !i, o = !this.seeking && i, s = r.paused && !i || r.ended || r.playbackRate === 0;
		if (this.seeking = i, e !== t) {
			t && (this.ended = 0), this.moved = !0, i || (this.nudgeRetry = 0, n.nudgeOnVideoHole && !s && e > t && this.nudgeOnVideoHole(e, t)), this.waiting === 0 && this.stallResolved(e);
			return;
		}
		if (o || a) {
			a && this.stallResolved(e);
			return;
		}
		if (s) {
			this.nudgeRetry = 0, this.stallResolved(e), !this.ended && r.ended && this.hls && (this.ended = e || 1, this.hls.trigger(q.MEDIA_ENDED, { stalled: !1 }));
			return;
		}
		if (!Q.getBuffered(r).length) {
			this.nudgeRetry = 0;
			return;
		}
		let c = Q.bufferInfo(r, e, 0), l = c.nextStart || 0, u = this.fragmentTracker;
		if (i && u && this.hls) {
			let t = xp(this.hls.inFlightFragments, e), n = c.len > gp, r = !l || t || l - e > gp && !u.getPartialFragment(e);
			if (n || r) return;
			this.moved = !1;
		}
		let d = this.hls?.latestLevelDetails;
		if (!this.moved && this.stalled !== null && u) {
			if (!(c.len > 0) && !l) return;
			let t = Math.max(l, c.start || 0) - e, n = d != null && d.live ? d.targetduration * 2 : gp, i = Cp(e, u);
			if (t > 0 && (t <= n || i)) {
				r.paused || this._trySkipBufferHole(i);
				return;
			}
		}
		let f = n.detectStallWithCurrentTimeMs, p = self.performance.now(), m = this.waiting, h = this.stalled;
		if (h === null) {
			if (m > 0 && p - m < f) h = this.stalled = m;
			else {
				this.stalled = p;
				return;
			}
		}
		let g = p - h;
		if (!i && (g >= f || m) && this.hls) {
			if (this.mediaSource?.readyState === "ended" && !(d != null && d.live) && Math.abs(e - (d?.edge || 0)) < 1) {
				if (this.ended) return;
				this.ended = e || 1, this.hls.trigger(q.MEDIA_ENDED, { stalled: !0 });
				return;
			}
			if (this._reportStall(c), !this.media || !this.hls) return;
		}
		let _ = Q.bufferInfo(r, e, n.maxBufferHole);
		this._tryFixBufferStall(_, g, e);
	}
	stallResolved(e) {
		let t = this.stalled;
		if (t && this.hls && (this.stalled = null, this.stallReported)) {
			let n = self.performance.now() - t;
			this.log(`playback not stuck anymore @${e}, after ${Math.round(n)}ms`), this.stallReported = !1, this.waiting = 0, this.hls.trigger(q.STALL_RESOLVED, {});
		}
	}
	nudgeOnVideoHole(e, t) {
		var n;
		let r = this.buffered.video;
		if (this.hls && this.media && this.fragmentTracker && (n = this.buffered.audio) != null && n.length && r && r.length > 1 && e > r.end(0)) {
			let n = Q.bufferedInfo(Q.timeRangesToArray(this.buffered.audio), e, 0);
			if (n.len > 1 && t >= n.start) {
				let n = Q.timeRangesToArray(r), i = Q.bufferedInfo(n, t, 0).bufferedIndex;
				if (i > -1 && i < n.length - 1) {
					let t = Q.bufferedInfo(n, e, 0).bufferedIndex, r = n[i].end, a = n[i + 1].start;
					if ((t === -1 || t > i) && a - r < 1 && e - r < 2) {
						let n = /* @__PURE__ */ Error(`nudging playhead to flush pipeline after video hole. currentTime: ${e} hole: ${r} -> ${a} buffered index: ${t}`);
						this.warn(n.message), this.media.currentTime += 1e-6;
						let i = Cp(e, this.fragmentTracker);
						i && "fragment" in i ? i = i.fragment : i ||= void 0;
						let o = Q.bufferInfo(this.media, e, 0);
						this.hls.trigger(q.ERROR, {
							type: G.MEDIA_ERROR,
							details: K.BUFFER_SEEK_OVER_HOLE,
							fatal: !1,
							error: n,
							reason: n.message,
							frag: i,
							buffer: o.len,
							bufferInfo: o
						});
					}
				}
			}
		}
	}
	_tryFixBufferStall(e, t, n) {
		let { fragmentTracker: r, media: i } = this, a = this.hls?.config;
		if (!i || !r || !a) return;
		let o = this.hls?.latestLevelDetails, s = Cp(n, r);
		if ((s || o != null && o.live && n < o.fragmentStart) && (this._trySkipBufferHole(s) || !this.media)) return;
		let c = e.buffered, l = this.adjacentTraversal(e, n);
		(c && c.length > 1 && e.len > a.maxBufferHole || e.nextStart && (e.nextStart - n < a.maxBufferHole || l)) && (t > a.highBufferWatchdogPeriod * 1e3 || this.waiting) && (this.warn("Trying to nudge playhead over buffer-hole"), this._tryNudgeBuffer(e));
	}
	adjacentTraversal(e, t) {
		let n = this.fragmentTracker, r = e.nextStart;
		if (n && r) {
			let e = n.getFragAtPos(t, Y.MAIN), i = n.getFragAtPos(r, Y.MAIN);
			if (e && i) return i.sn - e.sn < 2;
		}
		return !1;
	}
	_reportStall(e) {
		let { hls: t, media: n, stallReported: r, stalled: i } = this;
		if (!r && i !== null && n && t) {
			this.stallReported = !0;
			let r = /* @__PURE__ */ Error(`Playback stalling at @${n.currentTime} due to low buffer (${Fi(e)})`);
			this.warn(r.message), t.trigger(q.ERROR, {
				type: G.MEDIA_ERROR,
				details: K.BUFFER_STALLED_ERROR,
				fatal: !1,
				error: r,
				buffer: e.len,
				bufferInfo: e,
				stalled: { start: i }
			});
		}
	}
	_trySkipBufferHole(e) {
		let { fragmentTracker: t, media: n } = this, r = this.hls?.config;
		if (!n || !t || !r) return 0;
		let i = n.currentTime, a = Q.bufferInfo(n, i, 0), o = i < a.start ? a.start : a.nextStart;
		if (o && this.hls) {
			let c = a.len <= r.maxBufferHole, l = a.len > 0 && a.len < 1 && n.readyState < 3, u = o - i;
			if (u > 0 && (c || l)) {
				if (u > r.maxBufferHole) {
					let n = !1;
					if (i === 0) {
						let e = t.getAppendedFrag(0, Y.MAIN);
						e && o < e.end && (n = !0);
					}
					if (!n && e) {
						var s;
						if (!((s = this.hls.loadLevelObj) != null && s.details) || xp(this.hls.inFlightFragments, o)) return 0;
						let n = !1, r = e.end;
						for (; r < o;) {
							let e = Cp(r, t);
							if (e) r += e.duration;
							else {
								n = !0;
								break;
							}
						}
						if (n) return 0;
					}
				}
				let c = Math.max(o + vp, i + _p);
				if (this.warn(`skipping hole, adjusting currentTime from ${i} to ${c}`), this.moved = !0, n.currentTime = c, !(e != null && e.gap)) {
					let t = /* @__PURE__ */ Error(`fragment loaded with buffer holes, seeking from ${i} to ${c}`), n = {
						type: G.MEDIA_ERROR,
						details: K.BUFFER_SEEK_OVER_HOLE,
						fatal: !1,
						error: t,
						reason: t.message,
						buffer: a.len,
						bufferInfo: a
					};
					e && ("fragment" in e ? n.part = e : n.frag = e), this.hls.trigger(q.ERROR, n);
				}
				return c;
			}
		}
		return 0;
	}
	_tryNudgeBuffer(e) {
		let { hls: t, media: n, nudgeRetry: r } = this, i = t?.config;
		if (!n || !i) return 0;
		let a = n.currentTime;
		if (this.nudgeRetry++, r < i.nudgeMaxRetry) {
			let o = a + (r + 1) * i.nudgeOffset, s = /* @__PURE__ */ Error(`Nudging 'currentTime' from ${a} to ${o}`);
			this.warn(s.message), n.currentTime = o, t.trigger(q.ERROR, {
				type: G.MEDIA_ERROR,
				details: K.BUFFER_NUDGE_ON_STALL,
				error: s,
				fatal: !1,
				buffer: e.len,
				bufferInfo: e
			});
		} else {
			let n = /* @__PURE__ */ Error(`Playhead still not moving while enough data buffered @${a} after ${i.nudgeMaxRetry} nudges`);
			this.error(n.message), t.trigger(q.ERROR, {
				type: G.MEDIA_ERROR,
				details: K.BUFFER_STALLED_ERROR,
				error: n,
				fatal: !0,
				buffer: e.len,
				bufferInfo: e
			});
		}
	}
};
function xp(e, t) {
	let n = Sp(e.main);
	if (n && n.start <= t) return n;
	let r = Sp(e.audio);
	return r && r.start <= t ? r : null;
}
function Sp(e) {
	if (!e) return null;
	switch (e.state) {
		case $.IDLE:
		case $.STOPPED:
		case $.ENDED:
		case $.ERROR: return null;
	}
	return e.frag;
}
function Cp(e, t) {
	return t.getAppendedFrag(e, Y.MAIN) || t.getPartialFragment(e);
}
var wp = .25;
function Tp() {
	if (typeof self < "u") return self.VTTCue || self.TextTrackCue;
}
function Ep(e, t, n, r, i) {
	let a = new e(t, n, "");
	try {
		a.value = r, i && (a.type = i);
	} catch {
		a = new e(t, n, Fi(i ? Ln({ type: i }, r) : r));
	}
	return a;
}
var Dp = (() => {
	let e = Tp();
	try {
		e && new e(0, Infinity, "");
	} catch {
		return Number.MAX_VALUE;
	}
	return Infinity;
})(), Op = class {
	constructor(e) {
		this.hls = void 0, this.id3Track = null, this.media = null, this.dateRangeCuesAppended = {}, this.removeCues = !0, this.assetCue = void 0, this.onEventCueEnter = () => {
			this.hls && this.hls.trigger(q.EVENT_CUE_ENTER, {});
		}, this.hls = e, this._registerListeners();
	}
	destroy() {
		this._unregisterListeners(), this.id3Track = null, this.media = null, this.dateRangeCuesAppended = {}, this.hls = this.onEventCueEnter = null;
	}
	_registerListeners() {
		let { hls: e } = this;
		e && (e.on(q.MEDIA_ATTACHING, this.onMediaAttaching, this), e.on(q.MEDIA_ATTACHED, this.onMediaAttached, this), e.on(q.MEDIA_DETACHING, this.onMediaDetaching, this), e.on(q.MANIFEST_LOADING, this.onManifestLoading, this), e.on(q.FRAG_PARSING_METADATA, this.onFragParsingMetadata, this), e.on(q.BUFFER_FLUSHING, this.onBufferFlushing, this), e.on(q.LEVEL_UPDATED, this.onLevelUpdated, this), e.on(q.LEVEL_PTS_UPDATED, this.onLevelPtsUpdated, this));
	}
	_unregisterListeners() {
		let { hls: e } = this;
		e && (e.off(q.MEDIA_ATTACHING, this.onMediaAttaching, this), e.off(q.MEDIA_ATTACHED, this.onMediaAttached, this), e.off(q.MEDIA_DETACHING, this.onMediaDetaching, this), e.off(q.MANIFEST_LOADING, this.onManifestLoading, this), e.off(q.FRAG_PARSING_METADATA, this.onFragParsingMetadata, this), e.off(q.BUFFER_FLUSHING, this.onBufferFlushing, this), e.off(q.LEVEL_UPDATED, this.onLevelUpdated, this), e.off(q.LEVEL_PTS_UPDATED, this.onLevelPtsUpdated, this));
	}
	onMediaAttaching(e, t) {
		this.media = t.media, t.overrides?.cueRemoval === !1 && (this.removeCues = !1);
	}
	onMediaAttached() {
		let e = this.hls?.latestLevelDetails;
		e && this.updateDateRangeCues(e);
	}
	onMediaDetaching(e, t) {
		this.media = null, t.transferMedia || (this.id3Track &&= (this.removeCues && xd(this.id3Track, this.onEventCueEnter), null), this.dateRangeCuesAppended = {});
	}
	onManifestLoading() {
		this.dateRangeCuesAppended = {};
	}
	createTrack(e) {
		let t = this.getID3Track(e.textTracks);
		return t.mode = "hidden", t;
	}
	getID3Track(e) {
		if (this.media) {
			for (let t = 0; t < e.length; t++) {
				let n = e[t];
				if (n.kind === "metadata" && n.label === "id3") return yd(n, this.media), n;
			}
			return this.media.addTextTrack("metadata", "id3");
		}
	}
	onFragParsingMetadata(e, t) {
		if (!this.media || !this.hls) return;
		let { enableEmsgMetadataCues: n, enableID3MetadataCues: r } = this.hls.config;
		if (!n && !r) return;
		let { samples: i } = t;
		this.id3Track ||= this.createTrack(this.media);
		let a = Tp();
		if (a) for (let e = 0; e < i.length; e++) {
			let t = i[e].type;
			if (t === lc.emsg && !n || !r) continue;
			let o = ac(i[e].data), s = i[e].pts, c = s + i[e].duration;
			c > Dp && (c = Dp), c - s <= 0 && (c = s + wp);
			for (let e = 0; e < o.length; e++) {
				let n = o[e];
				if (!oc(n)) {
					this.updateId3CueEnds(s, t);
					let e = Ep(a, s, c, n, t);
					e && this.id3Track.addCue(e);
				}
			}
		}
	}
	updateId3CueEnds(e, t) {
		let n = this.id3Track?.cues;
		if (n) for (let r = n.length; r--;) {
			let i = n[r];
			i.type === t && i.startTime < e && i.endTime === Dp && (i.endTime = e);
		}
	}
	onBufferFlushing(e, { startOffset: t, endOffset: n, type: r }) {
		let { id3Track: i, hls: a } = this;
		if (!a) return;
		let { config: { enableEmsgMetadataCues: o, enableID3MetadataCues: s } } = a;
		if (i && (o || s)) {
			let e;
			e = r === "audio" ? (e) => e.type === lc.audioId3 && s : r === "video" ? (e) => e.type === lc.emsg && o : (e) => e.type === lc.audioId3 && s || e.type === lc.emsg && o, Sd(i, t, n, e);
		}
	}
	onLevelUpdated(e, { details: t }) {
		this.updateDateRangeCues(t, !0);
	}
	onLevelPtsUpdated(e, t) {
		Math.abs(t.drift) > .01 && this.updateDateRangeCues(t.details);
	}
	updateDateRangeCues(e, t) {
		if (!this.hls || !this.media) return;
		let { assetPlayerId: n, timelineOffset: r, enableDateRangeMetadataCues: i, interstitialsController: a } = this.hls.config;
		if (!i) return;
		let o = Tp();
		if (n && r && !a) {
			let { fragmentStart: t, fragmentEnd: r } = e, i = this.assetCue;
			i ? (i.startTime = t, i.endTime = r) : o && (i = this.assetCue = Ep(o, t, r, { assetPlayerId: this.hls.config.assetPlayerId }, "hlsjs.interstitial.asset"), i && (i.id = n, this.id3Track ||= this.createTrack(this.media), this.id3Track.addCue(i), i.addEventListener("enter", this.onEventCueEnter)));
		}
		if (!e.hasProgramDateTime) return;
		let { id3Track: s } = this, { dateRanges: c } = e, l = Object.keys(c), u = this.dateRangeCuesAppended;
		if (s && t) {
			var d;
			if ((d = s.cues) != null && d.length) {
				let e = Object.keys(u).filter((e) => !l.includes(e));
				for (let t = e.length; t--;) {
					let n = e[t], r = u[n]?.cues;
					delete u[n], r && Object.keys(r).forEach((e) => {
						let t = r[e];
						if (t) {
							t.removeEventListener("enter", this.onEventCueEnter);
							try {
								s.removeCue(t);
							} catch {}
						}
					});
				}
			} else u = this.dateRangeCuesAppended = {};
		}
		let f = e.fragments[e.fragments.length - 1];
		if (l.length !== 0 && W(f?.programDateTime)) {
			this.id3Track ||= this.createTrack(this.media);
			for (let e = 0; e < l.length; e++) {
				let t = l[e], n = c[t], r = n.startTime, i = u[t], s = i?.cues || {}, d = i?.durationKnown || !1, f = Dp, { duration: p, endDate: m } = n;
				if (m && p !== null) f = r + p, d = !0;
				else if (n.endOnNext && !d) {
					let e = l.reduce((e, t) => {
						if (t !== n.id) {
							let r = c[t];
							if (r.class === n.class && r.startDate > n.startDate && (!e || n.startDate < e.startDate)) return r;
						}
						return e;
					}, null);
					e && (f = e.startTime, d = !0);
				}
				let h = Object.keys(n.attr);
				for (let e = 0; e < h.length; e++) {
					let c = h[e];
					if (!Ja(c)) continue;
					let l = s[c];
					if (l) d && !(i != null && i.durationKnown) ? l.endTime = f : Math.abs(l.startTime - r) > .01 && (l.startTime = r, l.endTime = f);
					else if (o) {
						let e = n.attr[c];
						Ya(c) && (e = er(e));
						let i = Ep(o, r, f, {
							key: c,
							data: e
						}, lc.dateRange);
						i && (i.id = t, this.id3Track.addCue(i), s[c] = i, a && (c === "X-ASSET-LIST" || c === "X-ASSET-URL") && i.addEventListener("enter", this.onEventCueEnter));
					}
				}
				u[t] = {
					cues: s,
					dateRange: n,
					durationKnown: d
				};
			}
		}
	}
}, kp = class {
	constructor(e) {
		this.hls = void 0, this.config = void 0, this.media = null, this.currentTime = 0, this.stallCount = 0, this._latency = null, this._targetLatencyUpdated = !1, this.onTimeupdate = () => {
			let { media: e } = this, t = this.levelDetails;
			if (!e || !t) return;
			this.currentTime = e.currentTime;
			let n = this.computeLatency();
			if (n === null) return;
			this._latency = n;
			let { lowLatencyMode: r, maxLiveSyncPlaybackRate: i } = this.config;
			if (!r || i === 1 || !t.live) return;
			let a = this.targetLatency;
			if (a === null) return;
			let o = n - a;
			if (o < Math.min(this.maxLatency, a + t.targetduration) && o > .05 && this.forwardBufferLength > 1) {
				let t = Math.min(2, Math.max(1, i)), n = Math.round(2 / (1 + Math.exp(-.75 * o - this.edgeStalled)) * 20) / 20, r = Math.min(t, Math.max(1, n));
				this.changeMediaPlaybackRate(e, r);
			} else e.playbackRate !== 1 && e.playbackRate !== 0 && this.changeMediaPlaybackRate(e, 1);
		}, this.hls = e, this.config = e.config, this.registerListeners();
	}
	get levelDetails() {
		return this.hls?.latestLevelDetails || null;
	}
	get latency() {
		return this._latency || 0;
	}
	get maxLatency() {
		let { config: e } = this;
		if (e.liveMaxLatencyDuration !== void 0) return e.liveMaxLatencyDuration;
		let t = this.levelDetails;
		return t ? e.liveMaxLatencyDurationCount * t.targetduration : 0;
	}
	get targetLatency() {
		let e = this.levelDetails;
		if (e === null || this.hls === null) return null;
		let { holdBack: t, partHoldBack: n, targetduration: r } = e, { liveSyncDuration: i, liveSyncDurationCount: a, lowLatencyMode: o } = this.config, s = this.hls.userConfig, c = o && n || t;
		(this._targetLatencyUpdated || s.liveSyncDuration || s.liveSyncDurationCount || c === 0) && (c = i === void 0 ? a * r : i);
		let l = r;
		return c + Math.min(this.stallCount * this.config.liveSyncOnStallIncrease, l);
	}
	set targetLatency(e) {
		this.stallCount = 0, this.config.liveSyncDuration = e, this._targetLatencyUpdated = !0;
	}
	get liveSyncPosition() {
		let e = this.estimateLiveEdge(), t = this.targetLatency;
		if (e === null || t === null) return null;
		let n = this.levelDetails;
		if (n === null) return null;
		let r = n.edge, i = e - t - this.edgeStalled, a = r - n.totalduration, o = r - (this.config.lowLatencyMode && n.partTarget || n.targetduration);
		return Math.min(Math.max(a, i), o);
	}
	get drift() {
		let e = this.levelDetails;
		return e === null ? 1 : e.drift;
	}
	get edgeStalled() {
		let e = this.levelDetails;
		if (e === null) return 0;
		let t = (this.config.lowLatencyMode && e.partTarget || e.targetduration) * 3;
		return Math.max(e.age - t, 0);
	}
	get forwardBufferLength() {
		let { media: e } = this, t = this.levelDetails;
		if (!e || !t) return 0;
		let n = e.buffered.length;
		return (n ? e.buffered.end(n - 1) : t.edge) - this.currentTime;
	}
	destroy() {
		this.unregisterListeners(), this.onMediaDetaching(), this.hls = null;
	}
	registerListeners() {
		let { hls: e } = this;
		e && (e.on(q.MEDIA_ATTACHED, this.onMediaAttached, this), e.on(q.MEDIA_DETACHING, this.onMediaDetaching, this), e.on(q.MANIFEST_LOADING, this.onManifestLoading, this), e.on(q.LEVEL_UPDATED, this.onLevelUpdated, this), e.on(q.ERROR, this.onError, this));
	}
	unregisterListeners() {
		let { hls: e } = this;
		e && (e.off(q.MEDIA_ATTACHED, this.onMediaAttached, this), e.off(q.MEDIA_DETACHING, this.onMediaDetaching, this), e.off(q.MANIFEST_LOADING, this.onManifestLoading, this), e.off(q.LEVEL_UPDATED, this.onLevelUpdated, this), e.off(q.ERROR, this.onError, this));
	}
	onMediaAttached(e, t) {
		this.media = t.media, this.media.addEventListener("timeupdate", this.onTimeupdate);
	}
	onMediaDetaching() {
		this.media &&= (this.media.removeEventListener("timeupdate", this.onTimeupdate), null);
	}
	onManifestLoading() {
		this._latency = null, this.stallCount = 0;
	}
	onLevelUpdated(e, { details: t }) {
		t.advanced && this.onTimeupdate(), !t.live && this.media && this.media.removeEventListener("timeupdate", this.onTimeupdate);
	}
	onError(e, t) {
		var n;
		t.details === K.BUFFER_STALLED_ERROR && (this.stallCount++, this.hls && (n = this.levelDetails) != null && n.live && this.hls.logger.warn("[latency-controller]: Stall detected, adjusting target latency"));
	}
	changeMediaPlaybackRate(e, t) {
		var n;
		e.playbackRate !== t && ((n = this.hls) == null || n.logger.debug(`[latency-controller]: latency=${this.latency.toFixed(3)}, targetLatency=${this.targetLatency?.toFixed(3)}, forwardBufferLength=${this.forwardBufferLength.toFixed(3)}: adjusting playback rate from ${e.playbackRate} to ${t}`), e.playbackRate = t);
	}
	estimateLiveEdge() {
		let e = this.levelDetails;
		return e === null ? null : e.edge + e.age;
	}
	computeLatency() {
		let e = this.estimateLiveEdge();
		return e === null ? null : e - this.currentTime;
	}
}, Ap = class extends Ol {
	constructor(e, t) {
		super(e, "level-controller"), this._levels = [], this._firstLevel = -1, this._maxAutoLevel = -1, this._startLevel = void 0, this.currentLevel = null, this.currentLevelIndex = -1, this.manualLevelIndex = -1, this.steering = void 0, this.onParsedComplete = void 0, this.steering = t, this._registerListeners();
	}
	_registerListeners() {
		let { hls: e } = this;
		e.on(q.MANIFEST_LOADING, this.onManifestLoading, this), e.on(q.MANIFEST_LOADED, this.onManifestLoaded, this), e.on(q.LEVEL_LOADED, this.onLevelLoaded, this), e.on(q.LEVELS_UPDATED, this.onLevelsUpdated, this), e.on(q.FRAG_BUFFERED, this.onFragBuffered, this), e.on(q.ERROR, this.onError, this);
	}
	_unregisterListeners() {
		let { hls: e } = this;
		e.off(q.MANIFEST_LOADING, this.onManifestLoading, this), e.off(q.MANIFEST_LOADED, this.onManifestLoaded, this), e.off(q.LEVEL_LOADED, this.onLevelLoaded, this), e.off(q.LEVELS_UPDATED, this.onLevelsUpdated, this), e.off(q.FRAG_BUFFERED, this.onFragBuffered, this), e.off(q.ERROR, this.onError, this);
	}
	destroy() {
		this._unregisterListeners(), this.steering = null, this.resetLevels(), super.destroy();
	}
	stopLoad() {
		this._levels.forEach((e) => {
			e.loadError = 0, e.fragmentError = 0;
		}), super.stopLoad();
	}
	resetLevels() {
		this._startLevel = void 0, this.manualLevelIndex = -1, this.currentLevelIndex = -1, this.currentLevel = null, this._levels = [], this._maxAutoLevel = -1;
	}
	onManifestLoading(e, t) {
		this.resetLevels();
	}
	onManifestLoaded(e, t) {
		let n = this.hls.config.preferManagedMediaSource, r = [], i = {}, a = {}, o = !1, s = !1, c = !1;
		t.levels.forEach((e) => {
			let t = e.attrs, { audioCodec: l, videoCodec: u } = e;
			l && (e.audioCodec = l = ii(l, n) || void 0), u &&= e.videoCodec = ci(u);
			let { width: d, height: f, unknownCodecs: p } = e, m = p?.length || 0;
			if (o ||= !!(d && f), s ||= !!u, c ||= !!l, m || l && !this.isAudioSupported(l) || u && !this.isVideoSupported(u)) {
				this.log(`Some or all CODECS not supported "${t.CODECS}"`);
				return;
			}
			let { CODECS: h, "FRAME-RATE": g, "HDCP-LEVEL": _, "PATHWAY-ID": v, RESOLUTION: y, "VIDEO-RANGE": b } = t, x = `${`${v || "."}-`}${e.bitrate}-${y}-${g}-${h}-${b}-${_}`;
			if (!i[x]) {
				let t = this.createLevel(e);
				i[x] = t, a[x] = 1, r.push(t);
			} else if (i[x].uri !== e.url && !e.attrs["PATHWAY-ID"]) {
				let t = a[x] += 1;
				e.attrs["PATHWAY-ID"] = Array(t + 1).join(".");
				let n = this.createLevel(e);
				i[x] = n, r.push(n);
			} else i[x].addGroupId("audio", t.AUDIO), i[x].addGroupId("text", t.SUBTITLES);
		}), this.filterAndSortMediaOptions(r, t, o, s, c);
	}
	createLevel(e) {
		let t = new Ai(e), n = e.supplemental;
		if (n != null && n.videoCodec && !this.isVideoSupported(n.videoCodec)) {
			let e = /* @__PURE__ */ Error(`SUPPLEMENTAL-CODECS not supported "${n.videoCodec}"`);
			this.log(e.message), t.supportedResult = hi(e, []);
		}
		return t;
	}
	isAudioSupported(e) {
		return Xr(e, "audio", this.hls.config.preferManagedMediaSource);
	}
	isVideoSupported(e) {
		return Xr(e, "video", this.hls.config.preferManagedMediaSource);
	}
	filterAndSortMediaOptions(e, t, n, r, i) {
		let a = [], o = [], s = e, c = t.stats?.parsing || {};
		if ((n || r) && i && (s = s.filter(({ videoCodec: e, videoRange: t, width: n, height: r }) => (!!e || !!(n && r)) && Ei(t))), s.length === 0) {
			Promise.resolve().then(() => {
				if (this.hls) {
					let e = "no level with compatible codecs found in manifest", n = e;
					t.levels.length && (n = `one or more CODECS in variant not supported: ${Fi(t.levels.map((e) => e.attrs.CODECS).filter((e, t, n) => n.indexOf(e) === t))}`, this.warn(n), e += ` (${n})`);
					let r = Error(e);
					this.hls.trigger(q.ERROR, {
						type: G.MEDIA_ERROR,
						details: K.MANIFEST_INCOMPATIBLE_CODECS_ERROR,
						fatal: !0,
						url: t.url,
						error: r,
						reason: n
					});
				}
			}), c.end = performance.now();
			return;
		}
		t.audioTracks && (a = t.audioTracks.filter((e) => !e.audioCodec || this.isAudioSupported(e.audioCodec)), jp(a)), t.subtitles && (o = t.subtitles, jp(o));
		let l = s.slice(0);
		s.sort((e, t) => {
			if (e.attrs["HDCP-LEVEL"] !== t.attrs["HDCP-LEVEL"]) return (e.attrs["HDCP-LEVEL"] || "") > (t.attrs["HDCP-LEVEL"] || "") ? 1 : -1;
			if (n && e.height !== t.height) return e.height - t.height;
			if (e.frameRate !== t.frameRate) return e.frameRate - t.frameRate;
			if (e.videoRange !== t.videoRange) return Ti.indexOf(e.videoRange) - Ti.indexOf(t.videoRange);
			if (e.videoCodec !== t.videoCodec) {
				let n = $r(e.videoCodec), r = $r(t.videoCodec);
				if (n !== r) return r - n;
			}
			if (e.uri === t.uri && e.codecSet !== t.codecSet) {
				let n = ei(e.codecSet), r = ei(t.codecSet);
				if (n !== r) return r - n;
			}
			return e.averageBitrate === t.averageBitrate ? 0 : e.averageBitrate - t.averageBitrate;
		});
		let u = l[0];
		if (this.steering && (s = this.steering.filterParsedLevels(s), s.length !== l.length)) {
			for (let e = 0; e < l.length; e++) if (l[e].pathwayId === s[0].pathwayId) {
				u = l[e];
				break;
			}
		}
		this._levels = s;
		for (let e = 0; e < s.length; e++) if (s[e] === u) {
			this._firstLevel = e;
			let t = u.bitrate, n = this.hls.bandwidthEstimate;
			if (this.log(`manifest loaded, ${s.length} level(s) found, first bitrate: ${t}`), this.hls.userConfig?.abrEwmaDefaultEstimate === void 0) {
				let e = Math.min(t, this.hls.config.abrEwmaDefaultEstimateMax);
				e > n && n === this.hls.abrEwmaDefaultEstimate && (this.hls.bandwidthEstimate = e);
			}
			break;
		}
		let d = i && !r, f = this.hls.config, p = !!(f.audioStreamController && f.audioTrackController), m = {
			levels: s,
			audioTracks: a,
			subtitleTracks: o,
			sessionData: t.sessionData,
			sessionKeys: t.sessionKeys,
			firstLevel: this._firstLevel,
			stats: t.stats,
			audio: i,
			video: r,
			altAudio: p && !d && a.some((e) => !!e.url)
		};
		c.end = performance.now(), this.hls.trigger(q.MANIFEST_PARSED, m);
	}
	get levels() {
		return this._levels.length === 0 ? null : this._levels;
	}
	get loadLevelObj() {
		return this.currentLevel;
	}
	get level() {
		return this.currentLevelIndex;
	}
	set level(e) {
		let t = this._levels;
		if (t.length === 0) return;
		if (e < 0 || e >= t.length) {
			let n = /* @__PURE__ */ Error("invalid level idx"), r = e < 0;
			if (this.hls.trigger(q.ERROR, {
				type: G.OTHER_ERROR,
				details: K.LEVEL_SWITCH_ERROR,
				level: e,
				fatal: r,
				error: n,
				reason: n.message
			}), r) return;
			e = Math.min(e, t.length - 1);
		}
		let n = this.currentLevelIndex, r = this.currentLevel, i = r ? r.attrs["PATHWAY-ID"] : void 0, a = t[e], o = a.attrs["PATHWAY-ID"];
		if (this.currentLevelIndex = e, this.currentLevel = a, n === e && r && i === o) return;
		this.log(`Switching to level ${e} (${a.height ? a.height + "p " : ""}${a.videoRange ? a.videoRange + " " : ""}${a.codecSet ? a.codecSet + " " : ""}@${a.bitrate})${o ? " with Pathway " + o : ""} from level ${n}${i ? " with Pathway " + i : ""}`);
		let s = {
			level: e,
			attrs: a.attrs,
			details: a.details,
			bitrate: a.bitrate,
			averageBitrate: a.averageBitrate,
			maxBitrate: a.maxBitrate,
			realBitrate: a.realBitrate,
			width: a.width,
			height: a.height,
			codecSet: a.codecSet,
			audioCodec: a.audioCodec,
			videoCodec: a.videoCodec,
			audioGroups: a.audioGroups,
			subtitleGroups: a.subtitleGroups,
			loaded: a.loaded,
			loadError: a.loadError,
			fragmentError: a.fragmentError,
			name: a.name,
			id: a.id,
			uri: a.uri,
			url: a.url,
			urlId: 0,
			audioGroupIds: a.audioGroupIds,
			textGroupIds: a.textGroupIds
		};
		this.hls.trigger(q.LEVEL_SWITCHING, s);
		let c = a.details;
		if (!c || c.live) {
			let e = this.switchParams(a.uri, r?.details, c);
			this.loadPlaylist(e);
		}
	}
	get manualLevel() {
		return this.manualLevelIndex;
	}
	set manualLevel(e) {
		this.manualLevelIndex = e, this._startLevel === void 0 && (this._startLevel = e), e !== -1 && (this.level = e);
	}
	get firstLevel() {
		return this._firstLevel;
	}
	set firstLevel(e) {
		this._firstLevel = e;
	}
	get startLevel() {
		if (this._startLevel === void 0) {
			let e = this.hls.config.startLevel;
			return e === void 0 ? this.hls.firstAutoLevel : e;
		}
		return this._startLevel;
	}
	set startLevel(e) {
		this._startLevel = e;
	}
	get pathways() {
		return this.steering ? this.steering.pathways() : [];
	}
	get pathwayPriority() {
		return this.steering ? this.steering.pathwayPriority : null;
	}
	set pathwayPriority(e) {
		if (this.steering) {
			let t = this.steering.pathways(), n = e.filter((e) => t.indexOf(e) !== -1);
			if (e.length < 1) {
				this.warn(`pathwayPriority ${e} should contain at least one pathway from list: ${t}`);
				return;
			}
			this.steering.pathwayPriority = n;
		}
	}
	onError(e, t) {
		!t.fatal && t.context && t.context.type === J.LEVEL && t.context.level === this.level && this.checkRetry(t);
	}
	onFragBuffered(e, { frag: t }) {
		if (t !== void 0 && t.type === Y.MAIN) {
			let e = t.elementaryStreams;
			if (!Object.keys(e).some((t) => !!e[t])) return;
			let n = this._levels[t.level];
			n != null && n.loadError && (this.log(`Resetting level error count of ${n.loadError} on frag buffered`), n.loadError = 0);
		}
	}
	onLevelLoaded(e, t) {
		var n;
		let { level: r, details: i } = t, a = t.levelInfo;
		if (!a) {
			var o;
			this.warn(`Invalid level index ${r}`), (o = t.deliveryDirectives) != null && o.skip && (i.deltaUpdateFailed = !0);
		} else if (a === this.currentLevel || t.withoutMultiVariant) {
			a.fragmentError === 0 && (a.loadError = 0);
			let e = a.details;
			e === t.details && e.advanced && (e = void 0), this.playlistLoaded(r, t, e);
		} else (n = t.deliveryDirectives) != null && n.skip && (i.deltaUpdateFailed = !0);
	}
	loadPlaylist(e) {
		super.loadPlaylist(), this.shouldLoadPlaylist(this.currentLevel) && this.scheduleLoading(this.currentLevel, e);
	}
	loadingPlaylist(e, t) {
		super.loadingPlaylist(e, t);
		let n = this.getUrlWithDirectives(e.uri, t), r = this.currentLevelIndex, i = e.attrs["PATHWAY-ID"], a = e.details, o = a?.age;
		this.log(`Loading level index ${r}${t?.msn === void 0 ? "" : " at sn " + t.msn + " part " + t.part}${i ? " Pathway " + i : ""}${o && a.live ? " age " + o.toFixed(1) + (a.type && " " + a.type || "") : ""} ${n}`), this.hls.trigger(q.LEVEL_LOADING, {
			url: n,
			level: r,
			levelInfo: e,
			pathwayId: e.attrs["PATHWAY-ID"],
			id: 0,
			deliveryDirectives: t || null
		});
	}
	get nextLoadLevel() {
		return this.manualLevelIndex === -1 ? this.hls.nextAutoLevel : this.manualLevelIndex;
	}
	set nextLoadLevel(e) {
		this.level = e, this.manualLevelIndex === -1 && (this.hls.nextAutoLevel = e);
	}
	removeLevel(e) {
		var t;
		if (this._levels.length === 1) return;
		let n = this._levels.filter((t, n) => n !== e || (this.steering && this.steering.removeLevel(t), t === this.currentLevel && (this.currentLevel = null, this.currentLevelIndex = -1, t.details && t.details.fragments.forEach((e) => e.level = -1)), !1));
		ns(n), this._levels = n, this.currentLevelIndex > -1 && (t = this.currentLevel) != null && t.details && (this.currentLevelIndex = this.currentLevel.details.fragments[0].level), this.manualLevelIndex > -1 && (this.manualLevelIndex = this.currentLevelIndex);
		let r = n.length - 1;
		this._firstLevel = Math.min(this._firstLevel, r), this._startLevel &&= Math.min(this._startLevel, r), this.hls.trigger(q.LEVELS_UPDATED, { levels: n });
	}
	onLevelsUpdated(e, { levels: t }) {
		this._levels = t;
	}
	checkMaxAutoUpdated() {
		let { autoLevelCapping: e, maxAutoLevel: t, maxHdcpLevel: n } = this.hls;
		this._maxAutoLevel !== t && (this._maxAutoLevel = t, this.hls.trigger(q.MAX_AUTO_LEVEL_UPDATED, {
			autoLevelCapping: e,
			levels: this.levels,
			maxAutoLevel: t,
			minAutoLevel: this.hls.minAutoLevel,
			maxHdcpLevel: n
		}));
	}
};
function jp(e) {
	let t = {};
	e.forEach((e) => {
		let n = e.groupId || "";
		e.id = t[n] = t[n] || 0, t[n]++;
	});
}
function Mp() {
	return self.SourceBuffer || self.WebKitSourceBuffer;
}
function Np() {
	if (!Yn()) return !1;
	let e = Mp();
	return !e || e.prototype && typeof e.prototype.appendBuffer == "function" && typeof e.prototype.remove == "function";
}
function Pp() {
	if (!Np()) return !1;
	let e = Yn();
	return typeof e?.isTypeSupported == "function" && ([
		"avc1.42E01E,mp4a.40.2",
		"av01.0.01M.08",
		"vp09.00.50.08"
	].some((t) => e.isTypeSupported(Qr(t, "video"))) || ["mp4a.40.2", "fLaC"].some((t) => e.isTypeSupported(Qr(t, "audio"))));
}
function Fp() {
	var e;
	let t = Mp();
	return typeof (t == null || (e = t.prototype) == null ? void 0 : e.changeType) == "function";
}
var Ip = 100, Lp = class extends hs {
	constructor(e, t, n) {
		super(e, t, n, "stream-controller", Y.MAIN), this.audioCodecSwap = !1, this.level = -1, this._forceStartLoad = !1, this._hasEnoughToStart = !1, this.altAudio = 0, this.audioOnly = !1, this.fragPlaying = null, this.fragLastKbps = 0, this.couldBacktrack = !1, this.backtrackFragment = null, this.audioCodecSwitch = !1, this.videoBuffer = null, this.onMediaPlaying = () => {
			this.tick();
		}, this.onMediaSeeked = () => {
			let e = this.media, t = e ? e.currentTime : null;
			if (t === null || !W(t) || (this.log(`Media seeked to ${t.toFixed(3)}`), !this.getBufferedFrag(t))) return;
			let n = this.getFwdBufferInfoAtPos(e, t, Y.MAIN, 0);
			n === null || n.len === 0 ? this.warn(`Main forward buffer length at ${t} on "seeked" event ${n ? n.len : "empty"})`) : this.tick();
		}, this.registerListeners();
	}
	registerListeners() {
		super.registerListeners();
		let { hls: e } = this;
		e.on(q.MANIFEST_PARSED, this.onManifestParsed, this), e.on(q.LEVEL_LOADING, this.onLevelLoading, this), e.on(q.LEVEL_LOADED, this.onLevelLoaded, this), e.on(q.FRAG_LOAD_EMERGENCY_ABORTED, this.onFragLoadEmergencyAborted, this), e.on(q.AUDIO_TRACK_SWITCHING, this.onAudioTrackSwitching, this), e.on(q.AUDIO_TRACK_SWITCHED, this.onAudioTrackSwitched, this), e.on(q.BUFFER_CREATED, this.onBufferCreated, this), e.on(q.BUFFER_FLUSHED, this.onBufferFlushed, this), e.on(q.LEVELS_UPDATED, this.onLevelsUpdated, this), e.on(q.FRAG_BUFFERED, this.onFragBuffered, this);
	}
	unregisterListeners() {
		super.unregisterListeners();
		let { hls: e } = this;
		e.off(q.MANIFEST_PARSED, this.onManifestParsed, this), e.off(q.LEVEL_LOADED, this.onLevelLoaded, this), e.off(q.FRAG_LOAD_EMERGENCY_ABORTED, this.onFragLoadEmergencyAborted, this), e.off(q.AUDIO_TRACK_SWITCHING, this.onAudioTrackSwitching, this), e.off(q.AUDIO_TRACK_SWITCHED, this.onAudioTrackSwitched, this), e.off(q.BUFFER_CREATED, this.onBufferCreated, this), e.off(q.BUFFER_FLUSHED, this.onBufferFlushed, this), e.off(q.LEVELS_UPDATED, this.onLevelsUpdated, this), e.off(q.FRAG_BUFFERED, this.onFragBuffered, this);
	}
	onHandlerDestroying() {
		this.onMediaPlaying = this.onMediaSeeked = null, this.unregisterListeners(), super.onHandlerDestroying();
	}
	startLoad(e, t) {
		if (this.levels) {
			let { lastCurrentTime: n, hls: r } = this;
			if (this.stopLoad(), this.setInterval(Ip), this.level = -1, !this.startFragRequested) {
				let e = r.startLevel;
				e === -1 && (r.config.testBandwidth && this.levels.length > 1 ? (e = 0, this.bitrateTest = !0) : e = r.firstAutoLevel), r.nextLoadLevel = e, this.level = r.loadLevel, this._hasEnoughToStart = !!t;
			}
			n > 0 && e === -1 && !t && (this.log(`Override startPosition with lastCurrentTime @${n.toFixed(3)}`), e = n), this.state = $.IDLE, this.nextLoadPosition = this.lastCurrentTime = e + this.timelineOffset, this.startPosition = t ? -1 : e, this.tick();
		} else this._forceStartLoad = !0, this.state = $.STOPPED;
	}
	stopLoad() {
		this._forceStartLoad = !1, super.stopLoad();
	}
	doTick() {
		switch (this.state) {
			case $.WAITING_LEVEL: {
				let { levels: e, level: t } = this, n = e?.[t], r = n?.details;
				if (r && (!r.live || this.levelLastLoaded === n && !this.waitForLive(n))) {
					if (this.waitForCdnTuneIn(r)) break;
					this.state = $.IDLE;
					break;
				}
				if (this.hls.nextLoadLevel !== this.level) {
					this.state = $.IDLE;
					break;
				}
				break;
			}
			case $.FRAG_LOADING_WAITING_RETRY: this.checkRetryDate();
		}
		this.state === $.IDLE && this.doTickIdle(), this.onTickEnd();
	}
	onTickEnd() {
		var e;
		super.onTickEnd(), (e = this.media) != null && e.readyState && this.media.seeking === !1 && (this.lastCurrentTime = this.media.currentTime), this.checkFragmentChanged();
	}
	doTickIdle() {
		let { hls: e, levelLastLoaded: t, levels: n, media: r } = this;
		if (t === null || !r && !this.primaryPrefetch && (this.startFragRequested || !e.config.startFragPrefetch) || this.altAudio && this.audioOnly) return;
		let i = this.buffering ? e.nextLoadLevel : e.loadLevel;
		if (!(n != null && n[i])) return;
		let a = n[i], o = this.getMainFwdBufferInfo();
		if (o === null) return;
		let s = this.getLevelDetails();
		if (s && this._streamEnded(o, s)) {
			let e = {};
			this.altAudio === 2 && (e.type = "video"), this.hls.trigger(q.BUFFER_EOS, e), this.state = $.ENDED;
			return;
		}
		if (!this.buffering) return;
		e.loadLevel !== i && e.manualLevel === -1 && this.log(`Adapting to level ${i} from level ${this.level}`), this.level = e.nextLoadLevel = i;
		let c = a.details;
		if (!c || this.state === $.WAITING_LEVEL || this.waitForLive(a)) {
			this.level = i, this.state = $.WAITING_LEVEL, this.startFragRequested = !1;
			return;
		}
		let l = o.len, u = this.getMaxBufferLength(a.maxBitrate);
		if (l >= u) return;
		this.backtrackFragment && this.backtrackFragment.start > o.end && (this.backtrackFragment = null);
		let d = this.backtrackFragment ? this.backtrackFragment.start : o.end, f = this.getNextFragment(d, c);
		if (this.couldBacktrack && !this.fragPrevious && f && lr(f) && this.fragmentTracker.getState(f) !== ga.OK) {
			let e = (this.backtrackFragment ?? f).sn - c.startSN, t = c.fragments[e - 1];
			t && f.cc === t.cc && (f = t, this.fragmentTracker.removeFragment(t));
		} else this.backtrackFragment && o.len && (this.backtrackFragment = null);
		if (f && this.isLoopLoading(f, d)) {
			if (!f.gap) {
				let e = this.audioOnly && !this.altAudio ? sr.AUDIO : sr.VIDEO, t = (e === sr.VIDEO ? this.videoBuffer : this.mediaBuffer) || this.media;
				t && this.afterBufferFlushed(t, e, Y.MAIN);
			}
			f = this.getNextFragmentLoopLoading(f, c, o, Y.MAIN, u);
		}
		f && (f.initSegment && !f.initSegment.data && !this.bitrateTest && (f = f.initSegment), this.loadFragment(f, a, d));
	}
	loadFragment(e, t, n) {
		let r = this.fragmentTracker.getState(e);
		r === ga.NOT_LOADED || r === ga.PARTIAL ? lr(e) ? this.bitrateTest ? (this.log(`Fragment ${e.sn} of level ${e.level} is being downloaded to test bitrate and will not be buffered`), this._loadBitrateTestFrag(e, t)) : super.loadFragment(e, t, n) : this._loadInitSegment(e, t) : this.clearTrackerIfNeeded(e);
	}
	getBufferedFrag(e) {
		return this.fragmentTracker.getBufferedFrag(e, Y.MAIN);
	}
	followingBufferedFrag(e) {
		return e ? this.getBufferedFrag(e.end + .5) : null;
	}
	immediateLevelSwitch() {
		this.abortCurrentFrag(), this.flushMainBuffer(0, Infinity);
	}
	nextLevelSwitch() {
		let { levels: e, media: t } = this;
		if (t != null && t.readyState) {
			let n, r = this.getAppendedFrag(t.currentTime);
			r && r.start > 1 && this.flushMainBuffer(0, r.start - 1);
			let i = this.getLevelDetails();
			if (i != null && i.live) {
				let e = this.getMainFwdBufferInfo();
				if (!e || e.len < i.targetduration * 2) return;
			}
			if (!t.paused && e) {
				let t = e[this.hls.nextLoadLevel], r = this.fragLastKbps;
				n = r && this.fragCurrent ? this.fragCurrent.duration * t.maxBitrate / (1e3 * r) + 1 : 0;
			} else n = 0;
			let a = this.getBufferedFrag(t.currentTime + n);
			if (a) {
				let e = this.followingBufferedFrag(a);
				if (e) {
					this.abortCurrentFrag();
					let t = e.maxStartPTS ? e.maxStartPTS : e.start, n = e.duration, r = Math.max(a.end, t + Math.min(Math.max(n - this.config.maxFragLookUpTolerance, n * (this.couldBacktrack ? .5 : .125)), n * (this.couldBacktrack ? .75 : .25)));
					this.flushMainBuffer(r, Infinity);
				}
			}
		}
	}
	abortCurrentFrag() {
		let e = this.fragCurrent;
		switch (this.fragCurrent = null, this.backtrackFragment = null, e && (e.abortRequests(), this.fragmentTracker.removeFragment(e)), this.state) {
			case $.KEY_LOADING:
			case $.FRAG_LOADING:
			case $.FRAG_LOADING_WAITING_RETRY:
			case $.PARSING:
			case $.PARSED: this.state = $.IDLE;
		}
		this.nextLoadPosition = this.getLoadPosition();
	}
	flushMainBuffer(e, t) {
		super.flushMainBuffer(e, t, this.altAudio === 2 ? "video" : null);
	}
	onMediaAttached(e, t) {
		super.onMediaAttached(e, t);
		let n = t.media;
		fs(n, "playing", this.onMediaPlaying), fs(n, "seeked", this.onMediaSeeked);
	}
	onMediaDetaching(e, t) {
		let { media: n } = this;
		n && (ps(n, "playing", this.onMediaPlaying), ps(n, "seeked", this.onMediaSeeked)), this.videoBuffer = null, this.fragPlaying = null, super.onMediaDetaching(e, t), t.transferMedia || (this._hasEnoughToStart = !1);
	}
	onManifestLoading() {
		super.onManifestLoading(), this.log("Trigger BUFFER_RESET"), this.hls.trigger(q.BUFFER_RESET, void 0), this.couldBacktrack = !1, this.fragLastKbps = 0, this.fragPlaying = this.backtrackFragment = null, this.altAudio = 0, this.audioOnly = !1;
	}
	onManifestParsed(e, t) {
		let n = !1, r = !1;
		for (let e = 0; e < t.levels.length; e++) {
			let i = t.levels[e].audioCodec;
			i && (n ||= i.indexOf("mp4a.40.2") !== -1, r ||= i.indexOf("mp4a.40.5") !== -1);
		}
		this.audioCodecSwitch = n && r && !Fp(), this.audioCodecSwitch && this.log("Both AAC/HE-AAC audio found in levels; declaring level codec as HE-AAC"), this.levels = t.levels, this.startFragRequested = !1;
	}
	onLevelLoading(e, t) {
		let { levels: n } = this;
		if (!n || this.state !== $.IDLE) return;
		let r = t.levelInfo;
		(!r.details || r.details.live && (this.levelLastLoaded !== r || r.details.expired) || this.waitForCdnTuneIn(r.details)) && (this.state = $.WAITING_LEVEL);
	}
	onLevelLoaded(e, t) {
		var n;
		let { levels: r, startFragRequested: i } = this, a = t.level, o = t.details, s = o.totalduration;
		if (!r) {
			this.warn(`Levels were reset while loading level ${a}`);
			return;
		}
		this.log(`Level ${a} loaded [${o.startSN},${o.endSN}]${o.lastPartSn ? `[part-${o.lastPartSn}-${o.lastPartIndex}]` : ""}, cc [${o.startCC}, ${o.endCC}] duration:${s}`);
		let c = t.levelInfo, l = this.fragCurrent;
		l && (this.state === $.FRAG_LOADING || this.state === $.FRAG_LOADING_WAITING_RETRY) && l.level !== t.level && l.loader && this.abortCurrentFrag();
		let u = 0;
		if (o.live || (n = c.details) != null && n.live) {
			if (this.checkLiveUpdate(o), o.deltaUpdateFailed) return;
			u = this.alignPlaylists(o, c.details, this.levelLastLoaded?.details);
		}
		if (c.details = o, this.levelLastLoaded = c, i || this.setStartPosition(o, u), this.hls.trigger(q.LEVEL_UPDATED, {
			details: o,
			level: a
		}), this.state === $.WAITING_LEVEL) {
			if (this.waitForCdnTuneIn(o)) return;
			this.state = $.IDLE;
		}
		i && o.live && this.synchronizeToLiveEdge(o), this.tick();
	}
	synchronizeToLiveEdge(e) {
		let { config: t, media: n } = this;
		if (!n) return;
		let r = this.hls.liveSyncPosition, i = this.getLoadPosition(), a = e.fragmentStart, o = e.edge, s = i >= a - t.maxFragLookUpTolerance && i <= o;
		if (r !== null && n.duration > r && (i < r || !s)) {
			let a = t.liveMaxLatencyDuration === void 0 ? t.liveMaxLatencyDurationCount * e.targetduration : t.liveMaxLatencyDuration;
			if ((!s && n.readyState < 4 || i < o - a) && (this._hasEnoughToStart || (this.nextLoadPosition = r), n.readyState)) {
				if (this.warn(`Playback: ${i.toFixed(3)} is located too far from the end of live sliding playlist: ${o}, reset currentTime to : ${r.toFixed(3)}`), this.config.liveSyncMode === "buffered") {
					var c;
					let e = Q.bufferInfo(n, r, 0);
					if (!((c = e.buffered) != null && c.length) || e.start <= i) {
						n.currentTime = r;
						return;
					}
					let { nextStart: t } = Q.bufferedInfo(e.buffered, i, 0);
					t && (n.currentTime = t);
				} else n.currentTime = r;
			}
		}
	}
	_handleFragmentLoadProgress(e) {
		let t = e.frag, { part: n, payload: r } = e, { levels: i } = this;
		if (!i) {
			this.warn(`Levels were reset while fragment load was in progress. Fragment ${t.sn} of level ${t.level} will not be buffered`);
			return;
		}
		let a = i[t.level];
		if (!a) {
			this.warn(`Level ${t.level} not found on progress`);
			return;
		}
		let o = a.details;
		if (!o) {
			this.warn(`Dropping fragment ${t.sn} of level ${t.level} after level details were reset`), this.fragmentTracker.removeFragment(t);
			return;
		}
		let s = a.videoCodec, c = o.PTSKnown || !o.live, l = t.initSegment?.data, u = this._getAudioCodec(a), d = this.transmuxer = this.transmuxer || new Tl(this.hls, Y.MAIN, this._handleTransmuxComplete.bind(this), this._handleTransmuxerFlush.bind(this)), f = n ? n.index : -1, p = f !== -1, m = new Ia(t.level, t.sn, t.stats.chunkCount, r.byteLength, f, p), h = this.initPTS[t.cc];
		d.push(r, l, u, s, t, n, o.totalduration, c, m, h);
	}
	onAudioTrackSwitching(e, t) {
		let n = this.hls, r = this.altAudio !== 0;
		if (Ji(t.url, n)) this.altAudio = 1;
		else {
			if (this.mediaBuffer !== this.media) {
				this.log("Switching on main audio, use media.buffered to schedule main fragment loading"), this.mediaBuffer = this.media;
				let e = this.fragCurrent;
				e && (this.log("Switching to main audio track, cancel main fragment load"), e.abortRequests(), this.fragmentTracker.removeFragment(e)), this.resetTransmuxer(), this.resetLoadingState();
			} else this.audioOnly && this.resetTransmuxer();
			if (r) {
				this.altAudio = 0, this.fragmentTracker.removeAllFragments(), n.once(q.BUFFER_FLUSHED, () => {
					this.hls && this.hls.trigger(q.AUDIO_TRACK_SWITCHED, t);
				}), n.trigger(q.BUFFER_FLUSHING, {
					startOffset: 0,
					endOffset: Infinity,
					type: null
				});
				return;
			}
			n.trigger(q.AUDIO_TRACK_SWITCHED, t);
		}
	}
	onAudioTrackSwitched(e, t) {
		let n = Ji(t.url, this.hls);
		if (n) {
			let e = this.videoBuffer;
			e && this.mediaBuffer !== e && (this.log("Switching on alternate audio, use video.buffered to schedule main fragment loading"), this.mediaBuffer = e);
		}
		this.altAudio = n ? 2 : 0, this.tick();
	}
	onBufferCreated(e, t) {
		let n = t.tracks, r, i, a = !1;
		for (let e in n) {
			let t = n[e];
			if (t.id === "main") {
				if (i = e, r = t, e === "video") {
					let t = n[e];
					t && (this.videoBuffer = t.buffer);
				}
			} else a = !0;
		}
		a && r ? (this.log(`Alternate track found, use ${i}.buffered to schedule main fragment loading`), this.mediaBuffer = r.buffer) : this.mediaBuffer = this.media;
	}
	onFragBuffered(e, t) {
		let { frag: n, part: r } = t, i = n.type === Y.MAIN;
		if (i) {
			if (this.fragContextChanged(n)) {
				this.warn(`Fragment ${n.sn}${r ? " p: " + r.index : ""} of level ${n.level} finished buffering, but was aborted. state: ${this.state}`), this.state === $.PARSED && (this.state = $.IDLE);
				return;
			}
			let e = r ? r.stats : n.stats;
			this.fragLastKbps = Math.round(8 * e.total / (e.buffering.end - e.loading.first)), lr(n) && (this.fragPrevious = n), this.fragBufferedComplete(n, r);
		}
		let a = this.media;
		a && (!this._hasEnoughToStart && Q.getBuffered(a).length && (this._hasEnoughToStart = !0, this.seekToStartPos()), i && this.tick());
	}
	get hasEnoughToStart() {
		return this._hasEnoughToStart;
	}
	onError(e, t) {
		if (t.fatal) this.state = $.ERROR;
		else switch (t.details) {
			case K.FRAG_GAP:
			case K.FRAG_PARSING_ERROR:
			case K.FRAG_DECRYPT_ERROR:
			case K.FRAG_LOAD_ERROR:
			case K.FRAG_LOAD_TIMEOUT:
			case K.KEY_LOAD_ERROR:
			case K.KEY_LOAD_TIMEOUT:
				this.onFragmentOrKeyLoadError(Y.MAIN, t);
				break;
			case K.LEVEL_LOAD_ERROR:
			case K.LEVEL_LOAD_TIMEOUT:
			case K.LEVEL_PARSING_ERROR:
				!t.levelRetry && this.state === $.WAITING_LEVEL && t.context?.type === J.LEVEL && (this.state = $.IDLE);
				break;
			case K.BUFFER_ADD_CODEC_ERROR:
			case K.BUFFER_APPEND_ERROR:
				if (t.parent !== "main") return;
				this.reduceLengthAndFlushBuffer(t) && this.resetLoadingState();
				break;
			case K.BUFFER_FULL_ERROR:
				if (t.parent !== "main") return;
				this.reduceLengthAndFlushBuffer(t) && (!this.config.interstitialsController && this.config.assetPlayerId ? this._hasEnoughToStart = !0 : this.flushMainBuffer(0, Infinity));
				break;
			case K.INTERNAL_EXCEPTION: this.recoverWorkerError(t);
		}
	}
	onFragLoadEmergencyAborted() {
		this.state = $.IDLE, this._hasEnoughToStart || (this.startFragRequested = !1, this.nextLoadPosition = this.lastCurrentTime), this.tickImmediate();
	}
	onBufferFlushed(e, { type: t }) {
		if (t !== sr.AUDIO || !this.altAudio) {
			let e = (t === sr.VIDEO ? this.videoBuffer : this.mediaBuffer) || this.media;
			e && (this.afterBufferFlushed(e, t, Y.MAIN), this.tick());
		}
	}
	onLevelsUpdated(e, t) {
		this.level > -1 && this.fragCurrent && (this.level = this.fragCurrent.level, this.level === -1 && this.resetWhenMissingContext(this.fragCurrent)), this.levels = t.levels;
	}
	swapAudioCodec() {
		this.audioCodecSwap = !this.audioCodecSwap;
	}
	seekToStartPos() {
		let { media: e } = this;
		if (!e) return;
		let t = e.currentTime, n = this.startPosition;
		if (n >= 0 && t < n) {
			if (e.seeking) {
				this.log(`could not seek to ${n}, already seeking at ${t}`);
				return;
			}
			let r = this.timelineOffset;
			r && n && (n += r);
			let i = this.getLevelDetails(), a = Q.getBuffered(e), o = a.length ? a.start(0) : 0, s = o - n, c = Math.max(this.config.maxBufferHole, this.config.maxFragLookUpTolerance);
			(this.config.startOnSegmentBoundary || s > 0 && (s < c || this.loadingParts && s < 2 * (i?.partTarget || 0))) && (this.log(`adjusting start position by ${s} to match buffer start`), n += s, this.startPosition = n), t < n && (this.log(`seek to target start position ${n} from current time ${t} buffer start ${o}`), e.currentTime = n);
		}
	}
	_getAudioCodec(e) {
		let t = this.config.defaultAudioCodec || e.audioCodec;
		return this.audioCodecSwap && t && (this.log("Swapping audio codec"), t = t.indexOf("mp4a.40.5") === -1 ? "mp4a.40.5" : "mp4a.40.2"), t;
	}
	_loadBitrateTestFrag(e, t) {
		e.bitrateTest = !0, this._doFragLoad(e, t).then((e) => {
			let { hls: n } = this, r = e?.frag;
			if (!r || this.fragContextChanged(r)) return;
			t.fragmentError = 0, this.state = $.IDLE, this.startFragRequested = !1, this.bitrateTest = !1;
			let i = r.stats;
			i.parsing.start = i.parsing.end = i.buffering.start = i.buffering.end = self.performance.now(), n.trigger(q.FRAG_LOADED, e), r.bitrateTest = !1;
		}).catch((t) => {
			this.state !== $.STOPPED && this.state !== $.ERROR && (this.warn(t), this.resetFragmentLoading(e));
		});
	}
	_handleTransmuxComplete(e) {
		let t = this.playlistType, { hls: n } = this, { remuxResult: r, chunkMeta: i } = e, a = this.getCurrentContext(i);
		if (!a) {
			this.resetWhenMissingContext(i);
			return;
		}
		let { frag: o, part: s, level: c } = a, { video: l, text: u, id3: d, initSegment: f } = r, { details: p } = c, m = this.altAudio ? void 0 : r.audio;
		if (this.fragContextChanged(o)) this.fragmentTracker.removeFragment(o);
		else {
			if (this.state = $.PARSING, f) {
				let e = f.tracks;
				if (e) {
					let r = o.initSegment || o;
					if (this.unhandledEncryptionError(f, o)) return;
					this._bufferInitSegment(c, e, r, i), n.trigger(q.FRAG_PARSING_INIT_SEGMENT, {
						frag: r,
						id: t,
						tracks: e
					});
				}
				let r = f.initPTS, a = f.timescale, s = this.initPTS[o.cc];
				if (W(r) && (!s || s.baseTime !== r || s.timescale !== a)) {
					let e = f.trackId;
					this.initPTS[o.cc] = {
						baseTime: r,
						timescale: a,
						trackId: e
					}, n.trigger(q.INIT_PTS_FOUND, {
						frag: o,
						id: t,
						initPTS: r,
						timescale: a,
						trackId: e
					});
				}
			}
			if (l && p) {
				m && l.type === "audiovideo" && this.logMuxedErr(o);
				let e = p.fragments[o.sn - 1 - p.startSN], t = o.sn === p.startSN, n = !e || o.cc > e.cc;
				if (r.independent !== !1) {
					let { startPTS: e, endPTS: r, startDTS: a, endDTS: c } = l;
					if (s) s.elementaryStreams[l.type] = {
						startPTS: e,
						endPTS: r,
						startDTS: a,
						endDTS: c
					};
					else if (l.firstKeyFrame && l.independent && i.id === 1 && !n && (this.couldBacktrack = !0), l.dropped && l.independent) {
						let i = this.getMainFwdBufferInfo(), a = (i ? i.end : this.getLoadPosition()) + this.config.maxBufferHole, s = l.firstKeyFramePTS ? l.firstKeyFramePTS : e;
						if (!t && a < s - this.config.maxBufferHole && !n) {
							this.backtrack(o);
							return;
						}
						n && (o.gap = !0), o.setElementaryStreamInfo(l.type, o.start, r, o.start, c, !0);
					} else t && e - (p.appliedTimelineOffset || 0) > gp && (o.gap = !0);
					o.setElementaryStreamInfo(l.type, e, r, a, c), this.backtrackFragment &&= o, this.bufferFragmentData(l, o, s, i, t || n);
				} else if (t || n) o.gap = !0;
				else {
					this.backtrack(o);
					return;
				}
			}
			if (m) {
				let { startPTS: e, endPTS: t, startDTS: n, endDTS: r } = m;
				s && (s.elementaryStreams[sr.AUDIO] = {
					startPTS: e,
					endPTS: t,
					startDTS: n,
					endDTS: r
				}), o.setElementaryStreamInfo(sr.AUDIO, e, t, n, r), this.bufferFragmentData(m, o, s, i);
			}
			if (p && d != null && d.samples.length) {
				let e = {
					id: t,
					frag: o,
					details: p,
					samples: d.samples
				};
				n.trigger(q.FRAG_PARSING_METADATA, e);
			}
			if (p && u) {
				let e = {
					id: t,
					frag: o,
					details: p,
					samples: u.samples
				};
				n.trigger(q.FRAG_PARSING_USERDATA, e);
			}
		}
	}
	logMuxedErr(e) {
		this.warn(`${lr(e) ? "Media" : "Init"} segment with muxed audiovideo where only video expected: ${e.url}`);
	}
	_bufferInitSegment(e, t, n, r) {
		if (this.state !== $.PARSING) return;
		this.audioOnly = !!t.audio && !t.video, this.altAudio && !this.audioOnly && (delete t.audio, t.audiovideo && this.logMuxedErr(n));
		let { audio: i, video: a, audiovideo: o } = t;
		if (i) {
			let n = e.audioCodec, r = oi(i.codec, n);
			r === "mp4a" && (r = "mp4a.40.5");
			let a = navigator.userAgent.toLowerCase();
			if (this.audioCodecSwitch) {
				r &&= r.indexOf("mp4a.40.5") === -1 ? "mp4a.40.5" : "mp4a.40.2";
				let e = i.metadata;
				e && "channelCount" in e && (e.channelCount || 1) !== 1 && a.indexOf("firefox") === -1 && (r = "mp4a.40.5");
			}
			r && r.indexOf("mp4a.40.5") !== -1 && a.indexOf("android") !== -1 && i.container !== "audio/mpeg" && (r = "mp4a.40.2", this.log(`Android: force audio codec to ${r}`)), n && n !== r && this.log(`Swapping manifest audio codec "${n}" for "${r}"`), i.levelCodec = r, i.id = Y.MAIN, this.log(`Init audio buffer, container:${i.container}, codecs[selected/level/parsed]=[${r || ""}/${n || ""}/${i.codec}]`), delete t.audiovideo;
		}
		if (a) {
			a.levelCodec = e.videoCodec, a.id = Y.MAIN;
			let n = a.codec;
			if (n?.length === 4) switch (n) {
				case "hvc1":
				case "hev1":
					a.codec = "hvc1.1.6.L120.90";
					break;
				case "av01":
					a.codec = "av01.0.04M.08";
					break;
				case "avc1": a.codec = "avc1.42e01e";
			}
			this.log(`Init video buffer, container:${a.container}, codecs[level/parsed]=[${e.videoCodec || ""}/${n}]${a.codec === n ? "" : " parsed-corrected=" + a.codec}${a.supplemental ? " supplemental=" + a.supplemental : ""}`), delete t.audiovideo;
		}
		o && (this.log(`Init audiovideo buffer, container:${o.container}, codecs[level/parsed]=[${e.codecs}/${o.codec}]`), delete t.video, delete t.audio);
		let s = Object.keys(t);
		if (s.length) {
			if (this.hls.trigger(q.BUFFER_CODECS, t), !this.hls) return;
			s.forEach((e) => {
				let i = t[e].initSegment;
				i != null && i.byteLength && this.hls.trigger(q.BUFFER_APPENDING, {
					type: e,
					data: i,
					frag: n,
					part: null,
					chunkMeta: r,
					parent: n.type
				});
			});
		}
		this.tickImmediate();
	}
	getMainFwdBufferInfo() {
		let e = this.mediaBuffer && this.altAudio === 2 ? this.mediaBuffer : this.media;
		return this.getFwdBufferInfo(e, Y.MAIN);
	}
	get maxBufferLength() {
		let { levels: e, level: t } = this, n = e?.[t];
		return n ? this.getMaxBufferLength(n.maxBitrate) : this.config.maxBufferLength;
	}
	backtrack(e) {
		this.couldBacktrack = !0, this.backtrackFragment = e, this.resetTransmuxer(), this.flushBufferGap(e), this.fragmentTracker.removeFragment(e), this.fragPrevious = null, this.nextLoadPosition = e.start, this.state = $.IDLE;
	}
	checkFragmentChanged() {
		let e = this.media, t = null;
		if (e && e.readyState > 1 && e.seeking === !1) {
			let n = e.currentTime;
			if (Q.isBuffered(e, n) ? t = this.getAppendedFrag(n) : Q.isBuffered(e, n + .1) && (t = this.getAppendedFrag(n + .1)), t) {
				this.backtrackFragment = null;
				let e = this.fragPlaying, n = t.level;
				e && t.sn === e.sn && e.level === n || (this.fragPlaying = t, this.hls.trigger(q.FRAG_CHANGED, { frag: t }), e && e.level === n || this.hls.trigger(q.LEVEL_SWITCHED, { level: n }));
			}
		}
	}
	get nextLevel() {
		let e = this.nextBufferedFrag;
		return e ? e.level : -1;
	}
	get currentFrag() {
		if (this.fragPlaying) return this.fragPlaying;
		let e = this.media?.currentTime || this.lastCurrentTime;
		return W(e) ? this.getAppendedFrag(e) : null;
	}
	get currentProgramDateTime() {
		let e = this.media?.currentTime || this.lastCurrentTime;
		if (W(e)) {
			let t = this.getLevelDetails(), n = this.currentFrag || (t ? Qi(null, t.fragments, e) : null);
			if (n) {
				let t = n.programDateTime;
				if (t !== null) {
					let r = t + (e - n.start) * 1e3;
					return new Date(r);
				}
			}
		}
		return null;
	}
	get currentLevel() {
		let e = this.currentFrag;
		return e ? e.level : -1;
	}
	get nextBufferedFrag() {
		let e = this.currentFrag;
		return e ? this.followingBufferedFrag(e) : null;
	}
	get forceStartLoad() {
		return this._forceStartLoad;
	}
}, Rp = class extends Bn {
	constructor(e, t) {
		super("key-loader", t), this.config = void 0, this.keyIdToKeyInfo = {}, this.emeController = null, this.config = e;
	}
	abort(e) {
		for (let t in this.keyIdToKeyInfo) {
			let n = this.keyIdToKeyInfo[t].loader;
			if (n) {
				if (e && e !== n.context?.frag.type) return;
				n.abort();
			}
		}
	}
	detach() {
		for (let e in this.keyIdToKeyInfo) {
			let t = this.keyIdToKeyInfo[e];
			(t.mediaKeySessionContext || t.decryptdata.isCommonEncryption) && delete this.keyIdToKeyInfo[e];
		}
	}
	destroy() {
		this.detach();
		for (let e in this.keyIdToKeyInfo) {
			let t = this.keyIdToKeyInfo[e].loader;
			t && t.destroy();
		}
		this.keyIdToKeyInfo = {};
	}
	createKeyLoadError(e, t = K.KEY_LOAD_ERROR, n, r, i) {
		return new Pa({
			type: G.NETWORK_ERROR,
			details: t,
			fatal: !1,
			frag: e,
			response: i,
			error: n,
			networkDetails: r
		});
	}
	loadClear(e, t, n) {
		if (this.emeController && this.config.emeEnabled && !this.emeController.getSelectedKeySystemFormats().length) {
			if (t.length) for (let r = 0, i = t.length; r < i; r++) {
				let a = t[r];
				if (e.cc <= a.cc && (!lr(e) || !lr(a) || e.sn < a.sn) || !n && r == i - 1) return this.emeController.selectKeySystemFormat(a).then((e) => {
					if (!this.emeController) return;
					a.setKeyFormat(e);
					let t = fo(e);
					if (t) return this.emeController.getKeySystemAccess([t]);
				});
			}
			if (this.config.requireKeySystemAccessOnStart) {
				let e = mo(this.config);
				if (e.length) return this.emeController.getKeySystemAccess(e);
			}
		}
		return null;
	}
	load(e) {
		return !e.decryptdata && e.encrypted && this.emeController && this.config.emeEnabled ? this.emeController.selectKeySystemFormat(e).then((t) => this.loadInternal(e, t)) : this.loadInternal(e);
	}
	loadInternal(e, t) {
		var n, r;
		t && e.setKeyFormat(t);
		let i = e.decryptdata;
		if (!i) {
			let n = /* @__PURE__ */ Error(t ? `Expected frag.decryptdata to be defined after setting format ${t}` : `Missing decryption data on fragment in onKeyLoading (emeEnabled with controller: ${this.emeController && this.config.emeEnabled})`);
			return Promise.reject(this.createKeyLoadError(e, K.KEY_LOAD_ERROR, n));
		}
		let a = i.uri;
		if (!a) return Promise.reject(this.createKeyLoadError(e, K.KEY_LOAD_ERROR, /* @__PURE__ */ Error(`Invalid key URI: "${a}"`)));
		let o = zp(i), s = this.keyIdToKeyInfo[o];
		if ((n = s) != null && n.decryptdata.key) return i.key = s.decryptdata.key, Promise.resolve({
			frag: e,
			keyInfo: s
		});
		if (this.emeController && (r = s) != null && r.keyLoadPromise) switch (this.emeController.getKeyStatus(s.decryptdata)) {
			case "usable":
			case "usable-in-future": return s.keyLoadPromise.then((t) => {
				let { keyInfo: n } = t;
				return i.key = n.decryptdata.key, {
					frag: e,
					keyInfo: n
				};
			});
		}
		switch (this.log(`${this.keyIdToKeyInfo[o] ? "Rel" : "L"}oading${i.keyId ? " keyId: " + $n(i.keyId) : ""} URI: ${i.uri} from ${e.type} ${e.level}`), s = this.keyIdToKeyInfo[o] = {
			decryptdata: i,
			keyLoadPromise: null,
			loader: null,
			mediaKeySessionContext: null
		}, i.method) {
			case "SAMPLE-AES":
			case "SAMPLE-AES-CENC":
			case "SAMPLE-AES-CTR": return i.keyFormat === "identity" ? this.loadKeyHTTP(s, e) : this.loadKeyEME(s, e);
			case "AES-128":
			case "AES-256":
			case "AES-256-CTR": return this.loadKeyHTTP(s, e);
			default: return Promise.reject(this.createKeyLoadError(e, K.KEY_LOAD_ERROR, /* @__PURE__ */ Error(`Key supplied with unsupported METHOD: "${i.method}"`)));
		}
	}
	loadKeyEME(e, t) {
		let n = {
			frag: t,
			keyInfo: e
		};
		if (this.emeController && this.config.emeEnabled) {
			var r;
			if (!e.decryptdata.keyId && (r = t.initSegment) != null && r.data) {
				let n = jr(t.initSegment.data);
				if (n.length) {
					let t = n[0];
					t.some((e) => e !== 0) ? (this.log(`Using keyId found in init segment ${$n(t)}`), xo.setKeyIdForUri(e.decryptdata.uri, t)) : (t = xo.addKeyIdForUri(e.decryptdata.uri), this.log(`Generating keyId to patch media ${$n(t)}`)), e.decryptdata.keyId = t;
				}
			}
			return !e.decryptdata.keyId && !lr(t) ? Promise.resolve(n) : (e.keyLoadPromise = this.emeController.loadKey(n).then((t) => (e.mediaKeySessionContext = t, n))).catch((n) => {
				throw e.keyLoadPromise = null, "data" in n && (n.data.frag = t), n;
			});
		}
		return Promise.resolve(n);
	}
	loadKeyHTTP(e, t) {
		let n = this.config, r = n.loader, i = new r(n);
		return t.keyLoader = e.loader = i, e.keyLoadPromise = new Promise((r, a) => {
			let o = {
				keyInfo: e,
				frag: t,
				responseType: "arraybuffer",
				url: e.decryptdata.uri
			}, s = n.keyLoadPolicy.default, c = {
				loadPolicy: s,
				timeout: s.maxLoadTimeMs,
				maxRetry: 0,
				retryDelay: 0,
				maxRetryDelay: 0
			};
			i.load(o, c, {
				onSuccess: (e, t, n, i) => {
					let { frag: o, keyInfo: s } = n, c = zp(s.decryptdata);
					if (!o.decryptdata || s !== this.keyIdToKeyInfo[c]) return a(this.createKeyLoadError(o, K.KEY_LOAD_ERROR, /* @__PURE__ */ Error("after key load, decryptdata unset or changed"), i));
					s.decryptdata.key = o.decryptdata.key = new Uint8Array(e.data), o.keyLoader = null, s.loader = null, r({
						frag: o,
						keyInfo: s
					});
				},
				onError: (e, n, r, i) => {
					this.resetLoader(n), a(this.createKeyLoadError(t, K.KEY_LOAD_ERROR, /* @__PURE__ */ Error(`HTTP Error ${e.code} loading key ${e.text}`), r, Ln({
						url: o.url,
						data: void 0
					}, e)));
				},
				onTimeout: (e, n, r) => {
					this.resetLoader(n), a(this.createKeyLoadError(t, K.KEY_LOAD_TIMEOUT, /* @__PURE__ */ Error("key loading timed out"), r));
				},
				onAbort: (e, n, r) => {
					this.resetLoader(n), a(this.createKeyLoadError(t, K.INTERNAL_ABORTED, /* @__PURE__ */ Error("key loading aborted"), r));
				}
			});
		});
	}
	resetLoader(e) {
		let { frag: t, keyInfo: n, url: r } = e, i = n.loader;
		t.keyLoader === i && (t.keyLoader = null, n.loader = null);
		let a = zp(n.decryptdata) || r;
		delete this.keyIdToKeyInfo[a], i && i.destroy();
	}
};
function zp(e) {
	if (e.keyFormat !== uo.FAIRPLAY) {
		let t = e.keyId;
		if (t) return $n(t);
	}
	return e.uri;
}
function Bp(e) {
	let { type: t } = e;
	switch (t) {
		case J.AUDIO_TRACK: return Y.AUDIO;
		case J.SUBTITLE_TRACK: return Y.SUBTITLE;
		default: return Y.MAIN;
	}
}
function Vp(e, t) {
	let n = e.url;
	return (n === void 0 || n.indexOf("data:") === 0) && (n = t.url), n;
}
var Hp = class {
	constructor(e) {
		this.hls = void 0, this.loaders = Object.create(null), this.variableList = null, this.onManifestLoaded = this.checkAutostartLoad, this.hls = e, this.registerListeners();
	}
	startLoad(e) {}
	stopLoad() {
		this.destroyInternalLoaders();
	}
	registerListeners() {
		let { hls: e } = this;
		e.on(q.MANIFEST_LOADING, this.onManifestLoading, this), e.on(q.LEVEL_LOADING, this.onLevelLoading, this), e.on(q.AUDIO_TRACK_LOADING, this.onAudioTrackLoading, this), e.on(q.SUBTITLE_TRACK_LOADING, this.onSubtitleTrackLoading, this), e.on(q.LEVELS_UPDATED, this.onLevelsUpdated, this);
	}
	unregisterListeners() {
		let { hls: e } = this;
		e.off(q.MANIFEST_LOADING, this.onManifestLoading, this), e.off(q.LEVEL_LOADING, this.onLevelLoading, this), e.off(q.AUDIO_TRACK_LOADING, this.onAudioTrackLoading, this), e.off(q.SUBTITLE_TRACK_LOADING, this.onSubtitleTrackLoading, this), e.off(q.LEVELS_UPDATED, this.onLevelsUpdated, this);
	}
	createInternalLoader(e) {
		let t = this.hls.config, n = t.pLoader, r = t.loader, i = new (n || r)(t);
		return this.loaders[e.type] = i, i;
	}
	getInternalLoader(e) {
		return this.loaders[e.type];
	}
	resetInternalLoader(e) {
		this.loaders[e] && delete this.loaders[e];
	}
	destroyInternalLoaders() {
		for (let e in this.loaders) {
			let t = this.loaders[e];
			t && t.destroy(), this.resetInternalLoader(e);
		}
	}
	destroy() {
		this.variableList = null, this.unregisterListeners(), this.destroyInternalLoaders();
	}
	onManifestLoading(e, t) {
		let { url: n } = t;
		this.variableList = null, this.load({
			id: null,
			level: 0,
			responseType: "text",
			type: J.MANIFEST,
			url: n,
			deliveryDirectives: null,
			levelOrTrack: null
		});
	}
	onLevelLoading(e, t) {
		let { id: n, level: r, pathwayId: i, url: a, deliveryDirectives: o, levelInfo: s } = t;
		this.load({
			id: n,
			level: r,
			pathwayId: i,
			responseType: "text",
			type: J.LEVEL,
			url: a,
			deliveryDirectives: o,
			levelOrTrack: s
		});
	}
	onAudioTrackLoading(e, t) {
		let { id: n, groupId: r, url: i, deliveryDirectives: a, track: o } = t;
		this.load({
			id: n,
			groupId: r,
			level: null,
			responseType: "text",
			type: J.AUDIO_TRACK,
			url: i,
			deliveryDirectives: a,
			levelOrTrack: o
		});
	}
	onSubtitleTrackLoading(e, t) {
		let { id: n, groupId: r, url: i, deliveryDirectives: a, track: o } = t;
		this.load({
			id: n,
			groupId: r,
			level: null,
			responseType: "text",
			type: J.SUBTITLE_TRACK,
			url: i,
			deliveryDirectives: a,
			levelOrTrack: o
		});
	}
	onLevelsUpdated(e, t) {
		let n = this.loaders[J.LEVEL];
		if (n) {
			let e = n.context;
			e && !t.levels.some((t) => t === e.levelOrTrack) && (n.abort(), delete this.loaders[J.LEVEL]);
		}
	}
	load(e) {
		let t = this.hls.config, n = this.getInternalLoader(e);
		if (n) {
			let t = this.hls.logger, r = n.context;
			if (r && r.levelOrTrack === e.levelOrTrack && (r.url === e.url || r.deliveryDirectives && !e.deliveryDirectives)) {
				r.url === e.url ? t.log(`[playlist-loader]: ignore ${e.url} ongoing request`) : t.log(`[playlist-loader]: ignore ${e.url} in favor of ${r.url}`);
				return;
			}
			t.log(`[playlist-loader]: aborting previous loader for type: ${e.type}`), n.abort();
		}
		let r;
		if (r = e.type === J.MANIFEST ? t.manifestLoadPolicy.default : Fn({}, t.playlistLoadPolicy.default, {
			timeoutRetry: null,
			errorRetry: null
		}), n = this.createInternalLoader(e), W(e.deliveryDirectives?.part)) {
			let t;
			if (e.type === J.LEVEL && e.level !== null ? t = this.hls.levels[e.level].details : e.type === J.AUDIO_TRACK && e.id !== null ? t = this.hls.audioTracks[e.id].details : e.type === J.SUBTITLE_TRACK && e.id !== null && (t = this.hls.subtitleTracks[e.id].details), t) {
				let e = t.partTarget, n = t.targetduration;
				if (e && n) {
					let t = Math.max(e * 3, n * .8) * 1e3;
					r = Fn({}, r, {
						maxTimeToFirstByteMs: Math.min(t, r.maxTimeToFirstByteMs),
						maxLoadTimeMs: Math.min(t, r.maxTimeToFirstByteMs)
					});
				}
			}
		}
		let i = r.errorRetry || r.timeoutRetry || {}, a = {
			loadPolicy: r,
			timeout: r.maxLoadTimeMs,
			maxRetry: i.maxNumRetry || 0,
			retryDelay: i.retryDelayMs || 0,
			maxRetryDelay: i.maxRetryDelayMs || 0
		};
		n.load(e, a, {
			onSuccess: (e, t, n, r) => {
				let i = this.getInternalLoader(n);
				this.resetInternalLoader(n.type);
				let a = e.data;
				t.parsing.start = performance.now(), Ao.isMediaPlaylist(a) || n.type !== J.MANIFEST ? this.handleTrackOrLevelPlaylist(e, t, n, r || null, i) : this.handleMasterPlaylist(e, t, n, r);
			},
			onError: (e, t, n, r) => {
				this.handleNetworkError(t, n, !1, e, r);
			},
			onTimeout: (e, t, n) => {
				this.handleNetworkError(t, n, !0, void 0, e);
			}
		});
	}
	checkAutostartLoad() {
		if (!this.hls) return;
		let { config: { autoStartLoad: e, startPosition: t }, forceStartLoad: n } = this.hls;
		(e || n) && (this.hls.logger.log(`${e ? "auto" : "force"} startLoad with configured startPosition ${t}`), this.hls.startLoad(t));
	}
	handleMasterPlaylist(e, t, n, r) {
		let i = this.hls, a = e.data, o = Vp(e, n), s = Ao.parseMasterPlaylist(a, o);
		if (s.playlistParsingError) {
			t.parsing.end = performance.now(), this.handleManifestParsingError(e, n, s.playlistParsingError, r, t);
			return;
		}
		let { contentSteering: c, levels: l, sessionData: u, sessionKeys: d, startTimeOffset: f, variableList: p } = s;
		this.variableList = p, l.forEach((e) => {
			let { unknownCodecs: t } = e;
			if (t) {
				let { preferManagedMediaSource: n } = this.hls.config, { audioCodec: r, videoCodec: i } = e;
				for (let a = t.length; a--;) {
					let o = t[a];
					Xr(o, "audio", n) ? (e.audioCodec = r = r ? `${r},${o}` : o, Jr.audio[r.substring(0, 4)] = 2, t.splice(a, 1)) : Xr(o, "video", n) && (e.videoCodec = i = i ? `${i},${o}` : o, Jr.video[i.substring(0, 4)] = 2, t.splice(a, 1));
				}
			}
		});
		let { AUDIO: m = [], SUBTITLES: h, "CLOSED-CAPTIONS": g } = Ao.parseMasterPlaylistMedia(a, o, s);
		m.length && !m.some((e) => !e.url) && l[0].audioCodec && !l[0].attrs.AUDIO && (this.hls.logger.log("[playlist-loader]: audio codec signaled in quality level, but no embedded audio track signaled, create one"), m.unshift({
			type: "main",
			name: "main",
			groupId: "main",
			default: !1,
			autoselect: !1,
			forced: !1,
			id: -1,
			attrs: new Ka({}),
			bitrate: 0,
			url: ""
		})), i.trigger(q.MANIFEST_LOADED, {
			levels: l,
			audioTracks: m,
			subtitles: h,
			captions: g,
			contentSteering: c,
			url: o,
			stats: t,
			networkDetails: r,
			sessionData: u,
			sessionKeys: d,
			startTimeOffset: f,
			variableList: p
		});
	}
	handleTrackOrLevelPlaylist(e, t, n, r, i) {
		let a = this.hls, { id: o, level: s, type: c } = n, l = Vp(e, n), u = W(s) ? s : W(o) ? o : 0, d = Bp(n), f = Ao.parseLevelPlaylist(e.data, l, u, d, 0, this.variableList);
		if (c === J.MANIFEST) {
			let e = {
				attrs: new Ka({}),
				bitrate: 0,
				details: f,
				name: "",
				url: l
			};
			f.requestScheduled = t.loading.start + Qo(f, 0), a.trigger(q.MANIFEST_LOADED, {
				levels: [e],
				audioTracks: [],
				url: l,
				stats: t,
				networkDetails: r,
				sessionData: null,
				sessionKeys: null,
				contentSteering: null,
				startTimeOffset: null,
				variableList: null
			});
		}
		t.parsing.end = performance.now(), n.levelDetails = f, this.handlePlaylistLoaded(f, e, t, n, r, i);
	}
	handleManifestParsingError(e, t, n, r, i) {
		this.hls.trigger(q.ERROR, {
			type: G.NETWORK_ERROR,
			details: K.MANIFEST_PARSING_ERROR,
			fatal: t.type === J.MANIFEST,
			url: e.url,
			err: n,
			error: n,
			reason: n.message,
			response: e,
			context: t,
			networkDetails: r,
			stats: i
		});
	}
	handleNetworkError(e, t, n = !1, r, i) {
		let a = `A network ${n ? "timeout" : "error" + (r ? " (status " + r.code + ")" : "")} occurred while loading ${e.type}`;
		e.type === J.LEVEL ? a += `: ${e.level} id: ${e.id}` : (e.type === J.AUDIO_TRACK || e.type === J.SUBTITLE_TRACK) && (a += ` id: ${e.id} group-id: "${e.groupId}"`);
		let o = Error(a);
		this.hls.logger.warn(`[playlist-loader]: ${a}`);
		let s = K.UNKNOWN, c = !1, l = this.getInternalLoader(e);
		switch (e.type) {
			case J.MANIFEST:
				s = n ? K.MANIFEST_LOAD_TIMEOUT : K.MANIFEST_LOAD_ERROR, c = !0;
				break;
			case J.LEVEL:
				s = n ? K.LEVEL_LOAD_TIMEOUT : K.LEVEL_LOAD_ERROR, c = !1;
				break;
			case J.AUDIO_TRACK:
				s = n ? K.AUDIO_TRACK_LOAD_TIMEOUT : K.AUDIO_TRACK_LOAD_ERROR, c = !1;
				break;
			case J.SUBTITLE_TRACK: s = n ? K.SUBTITLE_TRACK_LOAD_TIMEOUT : K.SUBTITLE_LOAD_ERROR, c = !1;
		}
		l && this.resetInternalLoader(e.type);
		let u = {
			type: G.NETWORK_ERROR,
			details: s,
			fatal: c,
			url: e.url,
			loader: l,
			context: e,
			error: o,
			networkDetails: t,
			stats: i
		};
		r && (u.response = Ln({
			url: t?.url || e.url,
			data: void 0
		}, r)), this.hls.trigger(q.ERROR, u);
	}
	handlePlaylistLoaded(e, t, n, r, i, a) {
		let o = this.hls, { type: s, level: c, levelOrTrack: l, id: u, groupId: d, deliveryDirectives: f } = r, p = Vp(t, r), m = Bp(r), h = typeof r.level == "number" && m === Y.MAIN ? c : void 0, g = e.playlistParsingError;
		if (g) {
			if (this.hls.logger.warn(`${g} ${e.url}`), !o.config.ignorePlaylistParsingErrors) {
				o.trigger(q.ERROR, {
					type: G.NETWORK_ERROR,
					details: K.LEVEL_PARSING_ERROR,
					fatal: !1,
					url: p,
					error: g,
					reason: g.message,
					response: t,
					context: r,
					level: h,
					parent: m,
					networkDetails: i,
					stats: n
				});
				return;
			}
			e.playlistParsingError = null;
		}
		if (e.fragments.length) switch (e.live && a && (a.getCacheAge && (e.ageHeader = a.getCacheAge() || 0), (!a.getCacheAge || isNaN(e.ageHeader)) && (e.ageHeader = 0)), s) {
			case J.MANIFEST:
			case J.LEVEL:
				if (h) {
					if (!l) h = 0;
					else if (l !== o.levels[h]) {
						let e = o.levels.indexOf(l);
						e > -1 && (h = e);
					}
				}
				o.trigger(q.LEVEL_LOADED, {
					details: e,
					levelInfo: l || o.levels[0],
					level: h || 0,
					id: u || 0,
					stats: n,
					networkDetails: i,
					deliveryDirectives: f,
					withoutMultiVariant: s === J.MANIFEST
				});
				break;
			case J.AUDIO_TRACK:
				o.trigger(q.AUDIO_TRACK_LOADED, {
					details: e,
					track: l,
					id: u || 0,
					groupId: d || "",
					stats: n,
					networkDetails: i,
					deliveryDirectives: f
				});
				break;
			case J.SUBTITLE_TRACK: o.trigger(q.SUBTITLE_TRACK_LOADED, {
				details: e,
				track: l,
				id: u || 0,
				groupId: d || "",
				stats: n,
				networkDetails: i,
				deliveryDirectives: f
			});
		}
		else {
			let a = e.playlistParsingError = /* @__PURE__ */ Error("No Segments found in Playlist");
			o.trigger(q.ERROR, {
				type: G.NETWORK_ERROR,
				details: K.LEVEL_EMPTY_ERROR,
				fatal: !1,
				url: p,
				error: a,
				reason: a.message,
				response: t,
				context: r,
				level: h,
				parent: m,
				networkDetails: i,
				stats: n
			});
		}
	}
}, Up = class e {
	static get version() {
		return Cs;
	}
	static isMSESupported() {
		return Np();
	}
	static isSupported() {
		return Pp();
	}
	static getMediaSource() {
		return Yn();
	}
	static get Events() {
		return q;
	}
	static get MetadataSchema() {
		return lc;
	}
	static get ErrorTypes() {
		return G;
	}
	static get ErrorDetails() {
		return K;
	}
	static get DefaultConfig() {
		return e.defaultConfig ? e.defaultConfig : dp;
	}
	static set DefaultConfig(t) {
		e.defaultConfig = t;
	}
	constructor(t = {}) {
		this.config = void 0, this.userConfig = void 0, this.logger = void 0, this.coreComponents = void 0, this.networkControllers = void 0, this._emitter = new Ss(), this._autoLevelCapping = -1, this._maxHdcpLevel = null, this.abrController = void 0, this.bufferController = void 0, this.capLevelController = void 0, this.latencyController = void 0, this.levelController = void 0, this.streamController = void 0, this.audioStreamController = void 0, this.subtititleStreamController = void 0, this.audioTrackController = void 0, this.subtitleTrackController = void 0, this.interstitialsController = void 0, this.gapController = void 0, this.emeController = void 0, this.cmcdController = void 0, this._media = null, this._url = null, this._sessionId = void 0, this.triggeringException = void 0, this.started = !1;
		let n = this.logger = qn(t.debug || !1, "Hls instance", t.assetPlayerId), r = this.config = pp(e.DefaultConfig, t, n);
		this.userConfig = t, r.progressive && hp(r, n);
		let { abrController: i, bufferController: a, capLevelController: o, errorController: s, fpsController: c } = r, l = new s(this), u = this.abrController = new i(this), d = new _a(this), f = r.interstitialsController, p = f ? this.interstitialsController = new f(this, e) : null, m = this.bufferController = new a(this, d), h = this.capLevelController = new o(this), g = new c(this), _ = new Hp(this), v = r.contentSteeringController, y = v ? new v(this) : null, b = this.levelController = new Ap(this, y), x = new Op(this), S = new Rp(this.config, this.logger), C = this.streamController = new Lp(this, d, S), w = this.gapController = new bp(this, d);
		h.setStreamController(C), g.setStreamController(C);
		let T = [
			_,
			b,
			C
		];
		p && T.splice(1, 0, p), y && T.splice(1, 0, y), this.networkControllers = T;
		let E = [
			u,
			m,
			w,
			h,
			g,
			x,
			d
		];
		this.audioTrackController = this.createController(r.audioTrackController, T);
		let D = r.audioStreamController;
		D && T.push(this.audioStreamController = new D(this, d, S)), this.subtitleTrackController = this.createController(r.subtitleTrackController, T);
		let O = r.subtitleStreamController;
		O && T.push(this.subtititleStreamController = new O(this, d, S)), this.createController(r.timelineController, E), S.emeController = this.emeController = this.createController(r.emeController, E), this.cmcdController = this.createController(r.cmcdController, E), this.latencyController = this.createController(kp, E), this.coreComponents = E, T.push(l);
		let k = l.onErrorOut;
		typeof k == "function" && this.on(q.ERROR, k, l), this.on(q.MANIFEST_LOADED, _.onManifestLoaded, _);
	}
	createController(e, t) {
		if (e) {
			let n = new e(this);
			return t && t.push(n), n;
		}
		return null;
	}
	on(e, t, n = this) {
		this._emitter.on(e, t, n);
	}
	once(e, t, n = this) {
		this._emitter.once(e, t, n);
	}
	removeAllListeners(e) {
		this._emitter.removeAllListeners(e);
	}
	off(e, t, n = this, r) {
		this._emitter.off(e, t, n, r);
	}
	listeners(e) {
		return this._emitter.listeners(e);
	}
	emit(e, t, n) {
		return this._emitter.emit(e, t, n);
	}
	trigger(e, t) {
		if (this.config.debug) return this.emit(e, e, t);
		try {
			return this.emit(e, e, t);
		} catch (t) {
			if (this.logger.error("An internal error happened while handling event " + e + ". Error message: \"" + t.message + "\". Here is a stacktrace:", t), !this.triggeringException) {
				this.triggeringException = !0;
				let n = e === q.ERROR;
				this.trigger(q.ERROR, {
					type: G.OTHER_ERROR,
					details: K.INTERNAL_EXCEPTION,
					fatal: n,
					event: e,
					error: t
				}), this.triggeringException = !1;
			}
		}
		return !1;
	}
	listenerCount(e) {
		return this._emitter.listenerCount(e);
	}
	destroy() {
		this.logger.log("destroy"), this.trigger(q.DESTROYING, void 0), this.detachMedia(), this.removeAllListeners(), this._autoLevelCapping = -1, this._url = null, this.networkControllers.forEach((e) => e.destroy()), this.networkControllers.length = 0, this.coreComponents.forEach((e) => e.destroy()), this.coreComponents.length = 0;
		let e = this.config;
		e.xhrSetup = e.fetchSetup = void 0, this.userConfig = null;
	}
	attachMedia(e) {
		if (!e || "media" in e && !e.media) {
			let t = /* @__PURE__ */ Error(`attachMedia failed: invalid argument (${e})`);
			this.trigger(q.ERROR, {
				type: G.OTHER_ERROR,
				details: K.ATTACH_MEDIA_ERROR,
				fatal: !0,
				error: t
			});
			return;
		}
		this.logger.log("attachMedia"), this._media && (this.logger.warn("media must be detached before attaching"), this.detachMedia());
		let t = "media" in e, n = t ? e.media : e, r = t ? e : { media: n };
		this._media = n, this.trigger(q.MEDIA_ATTACHING, r);
	}
	detachMedia() {
		this.logger.log("detachMedia"), this.trigger(q.MEDIA_DETACHING, {}), this._media = null;
	}
	transferMedia() {
		this._media = null;
		let e = this.bufferController.transferMedia();
		return this.trigger(q.MEDIA_DETACHING, { transferMedia: e }), e;
	}
	loadSource(e) {
		this.stopLoad();
		let t = this.media, n = this._url, r = this._url = ar.buildAbsoluteURL(self.location.href, e, { alwaysNormalize: !0 });
		this._autoLevelCapping = -1, this._maxHdcpLevel = null, this.logger.log(`loadSource:${r}`), t && n && (n !== r || this.bufferController.hasSourceTypes()) && (this.detachMedia(), this.attachMedia(t)), this.trigger(q.MANIFEST_LOADING, { url: e });
	}
	get url() {
		return this._url;
	}
	get hasEnoughToStart() {
		return this.streamController.hasEnoughToStart;
	}
	get startPosition() {
		return this.streamController.startPositionValue;
	}
	startLoad(e = -1, t) {
		this.logger.log(`startLoad(${e + (t ? ", <skip seek to start>" : "")})`), this.started = !0, this.resumeBuffering();
		for (let n = 0; n < this.networkControllers.length && (this.networkControllers[n].startLoad(e, t), this.started && this.networkControllers); n++);
	}
	stopLoad() {
		this.logger.log("stopLoad"), this.started = !1;
		for (let e = 0; e < this.networkControllers.length && (this.networkControllers[e].stopLoad(), !this.started && this.networkControllers); e++);
	}
	get loadingEnabled() {
		return this.started;
	}
	get bufferingEnabled() {
		return this.streamController.bufferingEnabled;
	}
	resumeBuffering() {
		this.bufferingEnabled || (this.logger.log("resume buffering"), this.networkControllers.forEach((e) => {
			e.resumeBuffering && e.resumeBuffering();
		}));
	}
	pauseBuffering() {
		this.bufferingEnabled && (this.logger.log("pause buffering"), this.networkControllers.forEach((e) => {
			e.pauseBuffering && e.pauseBuffering();
		}));
	}
	get inFlightFragments() {
		let e = { [Y.MAIN]: this.streamController.inFlightFrag };
		return this.audioStreamController && (e[Y.AUDIO] = this.audioStreamController.inFlightFrag), this.subtititleStreamController && (e[Y.SUBTITLE] = this.subtititleStreamController.inFlightFrag), e;
	}
	swapAudioCodec() {
		this.logger.log("swapAudioCodec"), this.streamController.swapAudioCodec();
	}
	recoverMediaError() {
		this.logger.log("recoverMediaError");
		let e = this._media, t = e?.currentTime;
		this.detachMedia(), e && (this.attachMedia(e), t && this.startLoad(t));
	}
	removeLevel(e) {
		this.levelController.removeLevel(e);
	}
	get sessionId() {
		let e = this._sessionId;
		return e ||= this._sessionId = Dd(), e;
	}
	get levels() {
		return this.levelController.levels || [];
	}
	get latestLevelDetails() {
		return this.streamController.getLevelDetails() || null;
	}
	get loadLevelObj() {
		return this.levelController.loadLevelObj;
	}
	get currentLevel() {
		return this.streamController.currentLevel;
	}
	set currentLevel(e) {
		this.logger.log(`set currentLevel:${e}`), this.levelController.manualLevel = e, this.streamController.immediateLevelSwitch();
	}
	get nextLevel() {
		return this.streamController.nextLevel;
	}
	set nextLevel(e) {
		this.logger.log(`set nextLevel:${e}`), this.levelController.manualLevel = e, this.streamController.nextLevelSwitch();
	}
	get loadLevel() {
		return this.levelController.level;
	}
	set loadLevel(e) {
		this.logger.log(`set loadLevel:${e}`), this.levelController.manualLevel = e;
	}
	get nextLoadLevel() {
		return this.levelController.nextLoadLevel;
	}
	set nextLoadLevel(e) {
		this.levelController.nextLoadLevel = e;
	}
	get firstLevel() {
		return Math.max(this.levelController.firstLevel, this.minAutoLevel);
	}
	set firstLevel(e) {
		this.logger.log(`set firstLevel:${e}`), this.levelController.firstLevel = e;
	}
	get startLevel() {
		let e = this.levelController.startLevel;
		return e === -1 && this.abrController.forcedAutoLevel > -1 ? this.abrController.forcedAutoLevel : e;
	}
	set startLevel(e) {
		this.logger.log(`set startLevel:${e}`), e !== -1 && (e = Math.max(e, this.minAutoLevel)), this.levelController.startLevel = e;
	}
	get capLevelToPlayerSize() {
		return this.config.capLevelToPlayerSize;
	}
	set capLevelToPlayerSize(e) {
		let t = !!e;
		t !== this.config.capLevelToPlayerSize && (t ? this.capLevelController.startCapping() : (this.capLevelController.stopCapping(), this.autoLevelCapping = -1, this.streamController.nextLevelSwitch()), this.config.capLevelToPlayerSize = t);
	}
	get autoLevelCapping() {
		return this._autoLevelCapping;
	}
	get bandwidthEstimate() {
		let { bwEstimator: e } = this.abrController;
		return e ? e.getEstimate() : NaN;
	}
	set bandwidthEstimate(e) {
		this.abrController.resetEstimator(e);
	}
	get abrEwmaDefaultEstimate() {
		let { bwEstimator: e } = this.abrController;
		return e ? e.defaultEstimate : NaN;
	}
	get ttfbEstimate() {
		let { bwEstimator: e } = this.abrController;
		return e ? e.getEstimateTTFB() : NaN;
	}
	set autoLevelCapping(e) {
		this._autoLevelCapping !== e && (this.logger.log(`set autoLevelCapping:${e}`), this._autoLevelCapping = e, this.levelController.checkMaxAutoUpdated());
	}
	get maxHdcpLevel() {
		return this._maxHdcpLevel;
	}
	set maxHdcpLevel(e) {
		wi(e) && this._maxHdcpLevel !== e && (this._maxHdcpLevel = e, this.levelController.checkMaxAutoUpdated());
	}
	get autoLevelEnabled() {
		return this.levelController.manualLevel === -1;
	}
	get manualLevel() {
		return this.levelController.manualLevel;
	}
	get minAutoLevel() {
		let { levels: e, config: { minAutoBitrate: t } } = this;
		if (!e) return 0;
		let n = e.length;
		for (let r = 0; r < n; r++) if (e[r].maxBitrate >= t) return r;
		return 0;
	}
	get maxAutoLevel() {
		let { levels: e, autoLevelCapping: t, maxHdcpLevel: n } = this, r;
		if (r = t === -1 && e != null && e.length ? e.length - 1 : t, n) for (let t = r; t--;) {
			let r = e[t].attrs["HDCP-LEVEL"];
			if (r && r <= n) return t;
		}
		return r;
	}
	get firstAutoLevel() {
		return this.abrController.firstAutoLevel;
	}
	get nextAutoLevel() {
		return this.abrController.nextAutoLevel;
	}
	set nextAutoLevel(e) {
		this.abrController.nextAutoLevel = e;
	}
	get playingDate() {
		return this.streamController.currentProgramDateTime;
	}
	get mainForwardBufferInfo() {
		return this.streamController.getMainFwdBufferInfo();
	}
	get maxBufferLength() {
		return this.streamController.maxBufferLength;
	}
	setAudioOption(e) {
		return this.audioTrackController?.setAudioOption(e) || null;
	}
	setSubtitleOption(e) {
		return this.subtitleTrackController?.setSubtitleOption(e) || null;
	}
	get allAudioTracks() {
		let e = this.audioTrackController;
		return e ? e.allAudioTracks : [];
	}
	get audioTracks() {
		let e = this.audioTrackController;
		return e ? e.audioTracks : [];
	}
	get audioTrack() {
		let e = this.audioTrackController;
		return e ? e.audioTrack : -1;
	}
	set audioTrack(e) {
		let t = this.audioTrackController;
		t && (t.audioTrack = e);
	}
	get allSubtitleTracks() {
		let e = this.subtitleTrackController;
		return e ? e.allSubtitleTracks : [];
	}
	get subtitleTracks() {
		let e = this.subtitleTrackController;
		return e ? e.subtitleTracks : [];
	}
	get subtitleTrack() {
		let e = this.subtitleTrackController;
		return e ? e.subtitleTrack : -1;
	}
	get media() {
		return this._media;
	}
	set subtitleTrack(e) {
		let t = this.subtitleTrackController;
		t && (t.subtitleTrack = e);
	}
	get subtitleDisplay() {
		let e = this.subtitleTrackController;
		return e ? e.subtitleDisplay : !1;
	}
	set subtitleDisplay(e) {
		let t = this.subtitleTrackController;
		t && (t.subtitleDisplay = e);
	}
	get lowLatencyMode() {
		return this.config.lowLatencyMode;
	}
	set lowLatencyMode(e) {
		this.config.lowLatencyMode = e;
	}
	get liveSyncPosition() {
		return this.latencyController.liveSyncPosition;
	}
	get latency() {
		return this.latencyController.latency;
	}
	get maxLatency() {
		return this.latencyController.maxLatency;
	}
	get targetLatency() {
		return this.latencyController.targetLatency;
	}
	set targetLatency(e) {
		this.latencyController.targetLatency = e;
	}
	get drift() {
		return this.latencyController.drift;
	}
	get forceStartLoad() {
		return this.streamController.forceStartLoad;
	}
	get pathways() {
		return this.levelController.pathways;
	}
	get pathwayPriority() {
		return this.levelController.pathwayPriority;
	}
	set pathwayPriority(e) {
		this.levelController.pathwayPriority = e;
	}
	get bufferedToEnd() {
		var e;
		return !!((e = this.bufferController) != null && e.bufferedToEnd);
	}
	get interstitialsManager() {
		return this.interstitialsController?.interstitialsManager || null;
	}
	getMediaDecodingInfo(e, t = this.allAudioTracks) {
		return _i(e, Ri(t), navigator.mediaCapabilities);
	}
};
Up.defaultConfig = void 0;
// frontend/node_modules/@gradio/utils/dist/src/hls.js
function Wp() {
	return Up.isSupported();
}
var Gp = .25, Kp = .01, qp = 3, Jp = .1;
function Yp(e) {
	for (let t = 0; t < e.buffered.length; t++) if (e.buffered.start(t) <= e.currentTime && e.buffered.end(t) > e.currentTime) return e.buffered.end(t) - e.currentTime;
	return 0;
}
function Xp(e) {
	let t = -1, n = 0, r = 0, i = setInterval(() => {
		e.paused || e.ended || e.seeking ? n = 0 : e.currentTime === t ? (n += 1, n < 3 || Yp(e) < Gp || (n = 0, r >= qp || (r += 1, e.currentTime += Kp, e.play().catch(() => {})))) : (e.currentTime > t + Jp && (r = 0), t = e.currentTime, n = 0);
	}, 250);
	return () => clearInterval(i);
}
function Zp(e, t, n) {
	let r = new Up({
		maxBufferLength: 4,
		maxMaxBufferLength: 30,
		lowLatencyMode: !0
	});
	r.on(Up.Events.MANIFEST_PARSED, () => n?.()), r.on(Up.Events.ERROR, (e, t) => {
		if (!t.fatal) console.debug("HLS non-fatal error:", t.details);
		else switch (console.error("HLS error:", e, t), t.type) {
			case Up.ErrorTypes.NETWORK_ERROR:
				console.error("Fatal network error encountered, trying to recover"), r.startLoad();
				break;
			case Up.ErrorTypes.MEDIA_ERROR:
				console.error("Fatal media error encountered, trying to recover"), r.recoverMediaError();
				break;
			default: console.error("Fatal error, cannot recover"), r.destroy();
		}
	});
	let i = Xp(e);
	r.on(Up.Events.DESTROYING, i);
	try {
		r.loadSource(t), r.attachMedia(e);
	} catch (e) {
		throw i(), r.destroy(), e;
	}
	return r;
}
function Qp(e) {
	let t = e.loadLevelObj, n = e.loadLevel;
	!t || n < 0 || e.trigger(Up.Events.LEVEL_LOADING, {
		url: t.uri,
		level: n,
		levelInfo: t,
		pathwayId: t.attrs["PATHWAY-ID"],
		id: 0,
		deliveryDirectives: null
	});
}
// frontend/node_modules/@gradio/video/dist/shared/Video.svelte
var $p = s("<div><span class=\"load-wrap svelte-1me9ud\"><span class=\"loader svelte-1me9ud\"></span></span></div> <video crossorigin=\"anonymous\" class=\"svelte-1me9ud\"><!></video>", 3);
function em(e, n) {
	P(n, !0);
	let r = z(n, "src", 3, void 0), i = z(n, "muted", 3, void 0), o = z(n, "playsinline", 3, void 0), s = z(n, "preload", 3, void 0), c = z(n, "autoplay", 3, void 0), u = z(n, "controls", 3, void 0), d = z(n, "currentTime", 15, void 0), f = z(n, "duration", 15, void 0), p = z(n, "paused", 15, void 0), m = z(n, "node", 15, void 0), _ = z(n, "processingVideo", 3, !1), v, b, x;
	function S() {
		v?.destroy(), v = void 0, b = void 0, x = void 0;
	}
	_e(S), ve(() => {
		if (!m() || !n.is_stream || !r() || !Wp()) {
			S();
			return;
		}
		let e = m();
		v && b === e && x === r() ? Qp(v) : (S(), b = e, x = r(), v = Zp(e, r(), () => {
			C(() => c()) && Nt(e);
		}));
	});
	var w = $p(), T = B(w);
	let E;
	var O = D(T, 2), k = R(O), A = (e) => {
		var r = y(), i = B(r);
		ae(i, () => n.children), t(e, r);
	};
	a(k, (e) => {
		n.children && e(A);
	}), F(O), h(() => pe(O, d)), h(() => j("duration", "durationchange", O, f)), h(() => ce(O, p)), ee(O, (e) => m(e), () => m()), xe(O, (e, t) => kn?.(e, t), () => ({ autoplay: c() ?? !1 })), N(() => {
		E = g(T, 1, "overlay svelte-1me9ud", null, E, { hidden: !_() }), be(O, "src", r()), O.muted = i(), O.playsInline = o(), be(O, "preload", s()), O.autoplay = c(), O.controls = u(), O.loop = n.loop, be(O, "data-testid", n["data-testid"]);
	}), he("loadeddata", O, () => n.onloadeddata?.()), l("click", O, () => n.onclick?.()), he("play", O, () => n.onplay?.()), he("pause", O, () => n.onpause?.()), he("ended", O, () => n.onended?.()), l("mouseover", O, () => n.onmouseover?.()), l("mouseout", O, () => n.onmouseout?.()), he("focus", O, () => n.onfocus?.()), he("blur", O, () => n.onblur?.()), he("error", O, () => n.onerror?.("Video not playable")), he("loadstart", O, () => n.onloadstart?.()), he("loadedmetadata", O, () => n.onloadedmetadata?.()), t(e, w), M();
}
o([
	"click",
	"mouseover",
	"mouseout"
]);
// frontend/node_modules/dequal/dist/index.mjs
var tm = Object.prototype.hasOwnProperty;
function nm(e, t, n) {
	for (n of e.keys()) if (rm(n, t)) return n;
}
function rm(e, t) {
	var n, r, i;
	if (e === t) return !0;
	if (e && t && (n = e.constructor) === t.constructor) {
		if (n === Date) return e.getTime() === t.getTime();
		if (n === RegExp) return e.toString() === t.toString();
		if (n === Array) {
			if ((r = e.length) === t.length) for (; r-- && rm(e[r], t[r]););
			return r === -1;
		}
		if (n === Set) {
			if (e.size !== t.size) return !1;
			for (r of e) if (i = r, i && typeof i == "object" && (i = nm(t, i), !i) || !t.has(i)) return !1;
			return !0;
		}
		if (n === Map) {
			if (e.size !== t.size) return !1;
			for (r of e) if (i = r[0], i && typeof i == "object" && (i = nm(t, i), !i) || !rm(r[1], t.get(i))) return !1;
			return !0;
		}
		if (n === ArrayBuffer) e = new Uint8Array(e), t = new Uint8Array(t);
		else if (n === DataView) {
			if ((r = e.byteLength) === t.byteLength) for (; r-- && e.getInt8(r) === t.getInt8(r););
			return r === -1;
		}
		if (ArrayBuffer.isView(e)) {
			if ((r = e.byteLength) === t.byteLength) for (; r-- && e[r] === t[r];);
			return r === -1;
		}
		if (!n || typeof e == "object") {
			for (n in r = 0, e) if (tm.call(e, n) && ++r && !tm.call(t, n) || !(n in t) || !rm(e[n], t[n])) return !1;
			return Object.keys(t).length === r;
		}
	}
	return e !== e && t !== t;
}
// frontend/shared/utils.ts
async function im(e) {
	return e ? `<div style="display: flex; flex-wrap: wrap; gap: 16px">${(await Promise.all(e.map(async ([e, t]) => e === null || !e.url ? "" : await jt(e.url, "url")))).map((e) => `<img src="${e}" style="height: 400px" />`).join("")}</div>` : "";
}
async function am(e, t, n = "uploaded_file") {
	let r = e.type.split("/")[1] || "png", i = new File([e], `${n}.${r}`);
	return (await t([new dn({
		path: i.name,
		orig_name: i.name,
		blob: i,
		size: i.size,
		mime_type: i.type,
		is_stream: !1
	})]) ?? []).filter((e) => e !== null);
}
// frontend/shared/Gallery.svelte
var om = s("<div class=\"icon-button\"><!></div>"), sm = s("<!> <!> <!> <!>", 1), cm = s("<caption class=\"caption svelte-1qqxspv\"> </caption>"), lm = s("<!> <!>", 1), um = s("<button><!></button>"), dm = s("<span><!> <button class=\"media-button svelte-1qqxspv\" aria-label=\"detailed view of selected image\"><!></button> <!> <div class=\"thumbnails scroll-hide svelte-1qqxspv\" data-testid=\"container_el\"></div></span>"), fm = s("<!> <!> <!> <!> <!>", 1), pm = s("<span class=\"card-field-label svelte-1qqxspv\"> </span> <span> </span>", 1), mm = s("<span> </span>"), hm = s("<div class=\"card-field svelte-1qqxspv\"><!></div>"), gm = s("<div class=\"card-fields svelte-1qqxspv\"></div>"), _m = s("<button class=\"delete-button svelte-1qqxspv\" aria-label=\"Delete image\"><!></button>"), vm = s("<div class=\"gallery-item svelte-1qqxspv\"><button><!> <!></button> <!></div>"), ym = s("<div class=\"gallery-container svelte-1qqxspv\"><!> <div><!> <div></div></div></div>");
function bm(e, n) {
	P(n, !0);
	var r = this && this.__awaiter || function(e, t, n, r) {
		function i(e) {
			return e instanceof n ? e : new n(function(t) {
				t(e);
			});
		}
		return new (n ||= Promise)(function(n, a) {
			function o(e) {
				try {
					c(r.next(e));
				} catch (e) {
					a(e);
				}
			}
			function s(e) {
				try {
					c(r.throw(e));
				} catch (e) {
					a(e);
				}
			}
			function c(e) {
				e.done ? n(e.value) : i(e.value).then(o, s);
			}
			c((r = r.apply(e, t || [])).next());
		});
	};
	let i = z(n, "show_label", 3, !0), o = z(n, "value", 15), s = z(n, "columns", 19, () => [2]), c = z(n, "rows", 3, void 0), d = z(n, "height", 3, "auto"), p = z(n, "allow_preview", 3, !0), h = z(n, "object_fit", 3, "cover"), _ = z(n, "show_share_button", 3, !1), v = z(n, "show_download_button", 3, !1), y = z(n, "show_download_all_button", 3, !1), b = z(n, "selected_index", 15), C = z(n, "show_fullscreen_button", 3, !0), w = z(n, "fullscreen", 3, !1), T = z(n, "root", 3, ""), E = z(n, "file_types", 19, () => ["image", "video"]), O = z(n, "max_file_size", 3, null), k = z(n, "fit_columns", 3, !0), j = z(n, "buttons", 3, null), te = z(n, "oncustom_button_click", 3, null), ne = z(n, "onpreview_open", 3, () => {}), re = z(n, "onchange", 3, () => {}), ie = z(n, "onclear", 3, () => {}), ae = z(n, "onselect", 3, (e) => {}), oe = z(n, "onshare", 3, (e) => {}), se = z(n, "onerror", 3, (e) => {}), ce = z(n, "onpreview_close", 3, () => {}), le = z(n, "onfullscreen", 3, (e) => {}), de = z(n, "ondelete", 3, () => {}), pe = z(n, "onupload", 3, () => {}), me = z(n, "onsource_change", 3, () => {}), he = null, ge = !1, _e, xe = A(!1), H = L(() => o() == null ? null : o().map((e) => "video" in e ? {
		video: e.video,
		caption: e.caption
	} : "image" in e ? {
		image: e.image,
		caption: e.caption
	} : {}));
	function Ce(e, t, n) {
		if (e && t && n) {
			let n = e.length;
			return Array.isArray(t) ? t.map((e) => Math.min(e, n)) : Math.min(t, n);
		}
		return t;
	}
	let we = L(() => Ce(S(H), s(), k())), Te = A(fe(o()));
	b() == null && n.preview && o() !== null && o() !== void 0 && o().length && b(0), ve(() => {
		rm(S(Te), o()) || (S(xe) ? (b(n.preview && o() !== null && o() !== void 0 && o().length ? 0 : null), V(xe, !1)) : b() !== null && o() !== null ? b(Math.max(0, Math.min(b(), o().length - 1))) : b(null), re()(), V(Te, o(), !0));
	});
	let Ee = L(() => ((b() !== null && b() !== void 0 ? b() : 0) + ((S(H) === null || S(H) === void 0 ? void 0 : S(H).length) ?? 0) - 1) % ((S(H) === null || S(H) === void 0 ? void 0 : S(H).length) ?? 0)), De = L(() => ((b() !== null && b() !== void 0 ? b() : 0) + 1) % ((S(H) === null || S(H) === void 0 ? void 0 : S(H).length) ?? 0));
	function Oe(e) {
		S(H) !== null && ae()({
			index: e,
			value: S(H) === null || S(H) === void 0 ? void 0 : S(H)[e]
		});
	}
	function Ae(e) {
		let t = e.target;
		e.offsetX < t.offsetWidth / 2 ? b(S(Ee)) : b(S(De)), Oe(b());
	}
	function je(e) {
		switch (e.code) {
			case "Escape":
				e.preventDefault(), b(null), ce()();
				break;
			case "ArrowLeft":
				e.preventDefault(), b(S(Ee)), Oe(b());
				break;
			case "ArrowRight": e.preventDefault(), b(S(De)), Oe(b());
		}
	}
	ve(() => {
		p() && S(Ne) && Pe(b());
	});
	let Me = [], Ne = A(void 0);
	function Pe(e) {
		return r(this, void 0, void 0, function* () {
			var t;
			if (typeof e != "number" || (yield x(), Me[e] === void 0) || !S(Ne)) return;
			(t = Me[e]) == null || t.focus();
			let { left: n, width: r } = S(Ne).getBoundingClientRect(), { left: i, width: a } = Me[e].getBoundingClientRect(), o = i - n + a / 2 - r / 2 + S(Ne).scrollLeft;
			S(Ne) && typeof S(Ne).scrollTo == "function" && S(Ne).scrollTo({
				left: o < 0 ? 0 : o,
				behavior: "smooth"
			});
		});
	}
	function Ie(e, t) {
		return r(this, void 0, void 0, function* () {
			let r;
			try {
				r = yield n._fetch(e);
			} catch (t) {
				if (t instanceof TypeError) {
					window.open(e, "_blank", "noreferrer");
					return;
				}
				throw t;
			}
			let i = yield r.blob(), a = URL.createObjectURL(i), o = document.createElement("a");
			o.href = a, o.download = t, o.click(), URL.revokeObjectURL(a);
		});
	}
	let Re = new Uint32Array(Array.from({ length: 256 }, (e, t) => {
		let n = t;
		for (let e = 0; e < 8; e++) n = n & 1 ? 3988292384 ^ n >>> 1 : n >>> 1;
		return n >>> 0;
	}));
	function ze(e) {
		let t = 4294967295;
		for (let n of e) t = Re[(t ^ n) & 255] ^ t >>> 8;
		return (t ^ 4294967295) >>> 0;
	}
	function U(e, t, n) {
		e.setUint16(t, n, !0);
	}
	function Be(e, t, n) {
		e.setUint32(t, n, !0);
	}
	function Ve(e) {
		return new Uint8Array(e);
	}
	function Ue(e, t, n) {
		let r = (e.orig_name || e.path || t).split(/[/\\]/).pop() || t, i = n.get(r) ?? 0;
		if (n.set(r, i + 1), i === 0) return r;
		let a = r.lastIndexOf("."), o = a > 0 ? r.slice(0, a) : r, s = a > 0 ? r.slice(a) : "";
		return `${o}-${i + 1}${s}`;
	}
	function We(e) {
		let t = new TextEncoder(), n = [], r = [], i = 2048, a = 0;
		for (let o of e) {
			let e = t.encode(o.name), s = ze(o.data), c = Ve(30 + e.length), l = new DataView(c.buffer);
			Be(l, 0, 67324752), U(l, 4, 20), U(l, 6, i), U(l, 8, 0), U(l, 10, 0), U(l, 12, 33), Be(l, 14, s), Be(l, 18, o.data.length), Be(l, 22, o.data.length), U(l, 26, e.length), U(l, 28, 0), c.set(e, 30), n.push(c, o.data);
			let u = Ve(46 + e.length), d = new DataView(u.buffer);
			Be(d, 0, 33639248), U(d, 4, 20), U(d, 6, 20), U(d, 8, i), U(d, 10, 0), U(d, 12, 0), U(d, 14, 33), Be(d, 16, s), Be(d, 20, o.data.length), Be(d, 24, o.data.length), U(d, 28, e.length), U(d, 30, 0), U(d, 32, 0), U(d, 34, 0), U(d, 36, 0), Be(d, 38, 0), Be(d, 42, a), u.set(e, 46), r.push(u), a += c.length + o.data.length;
		}
		let o = a, s = r.reduce((e, t) => e + t.length, 0), c = Ve(22), l = new DataView(c.buffer);
		Be(l, 0, 101010256), U(l, 4, 0), U(l, 6, 0), U(l, 8, e.length), U(l, 10, e.length), Be(l, 12, s), Be(l, 16, o), U(l, 20, 0);
		let u = new Uint8Array(o + s + c.length), d = 0;
		for (let e of [
			...n,
			...r,
			c
		]) u.set(e, d), d += e.length;
		return u;
	}
	function Ge(e, t) {
		return r(this, void 0, void 0, function* () {
			let r;
			try {
				r = yield n._fetch(e);
			} catch (t) {
				return t instanceof TypeError && window.open(e, "_blank", "noreferrer"), null;
			}
			return r.ok ? {
				name: t,
				data: new Uint8Array(yield r.arrayBuffer())
			} : null;
		});
	}
	function qe(e) {
		return r(this, void 0, void 0, function* () {
			let t = /* @__PURE__ */ new Map(), n = (yield Promise.all(e.flatMap((e, n) => {
				let r = "image" in e ? e.image : e.video, i = "image" in e ? `image-${n + 1}` : `video-${n + 1}`;
				if (!r.url) return [];
				let a = Ue(r, i, t);
				return [Ge(r.url, a)];
			}))).filter((e) => e !== null);
			if (n.length === 0) return;
			let r = We(n), i = URL.createObjectURL(new Blob([r.buffer], { type: "application/zip" })), a = document.createElement("a");
			a.href = i, a.download = "gallery.zip", a.click(), URL.revokeObjectURL(i);
		});
	}
	function Ye() {
		S(H) && qe(S(H));
	}
	let Xe = L(() => b() != null && S(H) != null ? S(H)[b()] : null), Ze = !1;
	function Qe() {
		S(Ne) && (Ze = S(Ne).scrollWidth > S(Ne).clientWidth);
	}
	ue(() => (Qe(), document.addEventListener("fullscreenchange", () => {
		ge = !!document.fullscreenElement;
	}), window.addEventListener("resize", Qe), () => window.removeEventListener("resize", Qe))), ve(() => {
		S(H), Qe(), S(Ne) && Qe();
	});
	function $e(e) {
		if (!o() || !S(H)) return;
		let t = S(H)[e], n;
		"image" in t ? n = {
			file: t.image,
			index: e
		} : "video" in t && (n = {
			file: t.video,
			index: e
		}), n && de()(n);
	}
	let et = !1;
	var tt = lm(), rt = B(tt), at = (e) => {
		{
			let t = L(() => n.label || "Gallery");
			ke(e, {
				get show_label() {
					return i();
				},
				get Icon() {
					return nt;
				},
				get label() {
					return S(t);
				}
			});
		}
	};
	a(rt, (e) => {
		i() && e(at);
	});
	var ot = D(rt, 2), st = (e) => {
		Le(e, {
			unpadded_box: !0,
			size: "large",
			children: (e, t) => {
				nt(e, {});
			},
			$$slots: { default: !0 }
		});
	}, ct = (e) => {
		var r = ym(), s = R(r), x = (e) => {
			var r = dm();
			g(r, 1, "preview svelte-1qqxspv", null, {}, { minimal: !1 });
			var i = R(r);
			cn(i, {
				display_top_corner: !1,
				get buttons() {
					return j();
				},
				get on_custom_button_click() {
					return te();
				},
				children: (e, r) => {
					var i = sm(), o = B(i), s = (e) => {
						{
							let t = L(() => n.i18n("common.download"));
							Fe(e, {
								get Icon() {
									return Ke;
								},
								get label() {
									return S(t);
								},
								onclick: () => {
									let e = "image" in S(Xe) ? S(Xe)?.image : S(Xe)?.video;
									if (e == null) return;
									let { url: t, orig_name: n } = e;
									t && Ie(t, n ?? "image");
								}
							});
						}
					};
					a(o, (e) => {
						v() && e(s);
					});
					var c = D(o, 2), l = (e) => {
						ln(e, {
							get fullscreen() {
								return w();
							},
							onclick: (e) => le()({ detail: e })
						});
					};
					a(c, (e) => {
						C() && e(l);
					});
					var u = D(c, 2), d = (e) => {
						var r = om();
						Lt(R(r), {
							get i18n() {
								return n.i18n;
							},
							onshare: (e) => {
								oe()({ detail: e });
							},
							onerror: (e) => {
								se()({ detail: e });
							},
							get value() {
								return S(H);
							},
							get formatter() {
								return im;
							}
						}), F(r), t(e, r);
					};
					a(u, (e) => {
						_() && e(d);
					});
					var f = D(u, 2), p = (e) => {
						Fe(e, {
							get Icon() {
								return He;
							},
							label: "Close",
							onclick: () => {
								b(null), ce()();
							}
						});
					};
					a(f, (e) => {
						ge || e(p);
					}), t(e, i);
				},
				$$slots: { default: !0 }
			});
			var o = D(i, 2), s = R(o), c = (e) => {
				{
					let t = L(() => ({
						alt: S(Xe).caption || "",
						title: S(Xe).caption || null,
						class: S(Xe).caption && "with-caption",
						loading: "lazy"
					}));
					En(e, {
						get restProps() {
							return S(t);
						},
						get src() {
							return S(Xe).image.url;
						},
						data_testid: "detailed-image"
					});
				}
			}, d = (e) => {
				{
					let t = L(() => S(Xe).caption || "");
					em(e, {
						get src() {
							return S(Xe).video.url;
						},
						"data-testid": "detailed-video",
						get alt() {
							return S(t);
						},
						loading: "lazy",
						loop: !1,
						is_stream: !1,
						muted: !1,
						controls: !0
					});
				}
			};
			a(s, (e) => {
				"image" in S(Xe) ? e(c) : e(d, -1);
			}), F(o);
			var p = D(o, 2), h = (e) => {
				var n = cm(), r = I(n, !0);
				N(() => u(r, S(Xe).caption)), t(e, n);
			};
			a(p, (e) => {
				S(Xe)?.caption && e(h);
			});
			var y = D(p, 2);
			f(y, 21, () => S(H), m, (e, n, r) => {
				var i = um();
				let o;
				var s = R(i), c = (e) => {
					{
						let t = L(() => ({
							title: S(n).caption || null,
							alt: "",
							class: "with-caption",
							loading: "lazy"
						}));
						En(e, {
							get src() {
								return S(n).image.url;
							},
							get restProps() {
								return S(t);
							},
							data_testid: `thumbnail ${r + 1}`
						});
					}
				}, u = (e) => {
					var i = lm(), a = B(i);
					ft(a, {});
					var o = D(a, 2);
					{
						let e = L(() => S(n).caption || null);
						em(o, {
							get src() {
								return S(n).video.url;
							},
							get title() {
								return S(e);
							},
							is_stream: !1,
							"data-testid": "thumbnail " + (r + 1),
							alt: "",
							loading: "lazy",
							loop: !1
						});
					}
					t(e, i);
				};
				a(s, (e) => {
					"image" in S(n) ? e(c) : e(u, -1);
				}), F(i), ee(i, (e, t) => Me[t] = e, (e) => Me?.[e], () => [r]), N(() => {
					o = g(i, 1, "thumbnail-item thumbnail-small svelte-1qqxspv", null, o, { selected: b() === r && !0 }), be(i, "aria-label", "Thumbnail " + (r + 1) + " of " + S(H).length);
				}), l("click", i, () => {
					b(r), Oe(r);
				}), t(e, i);
			}), F(y), ee(y, (e) => V(Ne, e), () => S(Ne)), F(r), N(() => {
				Se(o, `height: calc(100% - ${S(Xe).caption ? "80px" : "60px"})`), Se(y, `justify-content: ${Ze ? "flex-start" : "center"};`);
			}), l("keydown", r, je), l("click", o, function(...e) {
				("image" in S(Xe) ? (e) => Ae(e) : null)?.apply(this, e);
			}), t(e, r);
		};
		a(s, (e) => {
			S(Xe) && p() && e(x);
		});
		var k = D(s, 2);
		let A, M;
		var P = R(k), re = (e) => {
			Cn(e, {
				get i18n() {
					return n.i18n;
				},
				onclear: () => {
					o([]), ie()();
				},
				children: (e, r) => {
					var i = fm(), o = B(i), s = (e) => {
						{
							let t = L(() => n.i18n("common.download_all"));
							Fe(e, {
								get Icon() {
									return Je;
								},
								get label() {
									return S(t);
								},
								onclick: Ye
							});
						}
					};
					a(o, (e) => {
						y() && e(s);
					});
					var c = D(o, 2), l = (e) => {
						{
							let t = L(() => n.i18n("upload_text.click_to_upload"));
							Fe(e, {
								get Icon() {
									return vt;
								},
								get label() {
									return S(t);
								},
								children: (e, t) => {
									xn(e, {
										icon_upload: !0,
										onload: (e) => pe()(e),
										get filetype() {
											return E();
										},
										file_count: "multiple",
										get max_file_size() {
											return O();
										},
										get root() {
											return T();
										},
										onerror: (e) => se()(e),
										get stream_handler() {
											return n.stream_handler;
										},
										get upload() {
											return n.upload;
										},
										get upload_promise() {
											return he;
										},
										set upload_promise(e) {
											he = e;
										},
										get uploading() {
											return et;
										},
										set uploading(e) {
											et = e;
										}
									});
								},
								$$slots: { default: !0 }
							});
						}
					}, u = L(() => n.upload && n.stream_handler && n.sources.includes("upload"));
					a(c, (e) => {
						S(u) && e(l);
					});
					var d = D(c, 2), f = (e) => {
						{
							let t = L(() => n.i18n("common.webcam"));
							Fe(e, {
								get Icon() {
									return St;
								},
								get label() {
									return S(t);
								},
								onclick: () => {
									me()("webcam");
								}
							});
						}
					}, p = L(() => n.sources.includes("webcam"));
					a(d, (e) => {
						S(p) && e(f);
					});
					var m = D(d, 2), h = (e) => {
						{
							let t = L(() => n.i18n("common.video"));
							Fe(e, {
								get Icon() {
									return bt;
								},
								get label() {
									return S(t);
								},
								onclick: () => {
									me()("webcam-video");
								}
							});
						}
					}, g = L(() => n.sources.includes("webcam-video"));
					a(m, (e) => {
						S(g) && e(h);
					});
					var _ = D(m, 2), v = (e) => {
						{
							let t = L(() => n.i18n("upload_text.paste_clipboard"));
							Fe(e, {
								get label() {
									return S(t);
								},
								onclick: () => {
									me()("clipboard");
								},
								get Icon() {
									return it;
								}
							});
						}
					}, b = L(() => n.sources.includes("clipboard"));
					a(_, (e) => {
						S(b) && e(v);
					}), t(e, i);
				},
				$$slots: { default: !0 }
			});
		}, ae = (e) => {
			cn(e, {
				children: (e, t) => {
					{
						let t = L(() => n.i18n("common.download_all"));
						Fe(e, {
							get Icon() {
								return Je;
							},
							get label() {
								return S(t);
							},
							onclick: Ye
						});
					}
				},
				$$slots: { default: !0 }
			});
		};
		a(P, (e) => {
			n.interactive && b() === null ? e(re) : y() && !(S(Xe) && p()) && e(ae, 1);
		});
		var ue = D(P, 2);
		let de;
		f(ue, 23, () => S(H), (e, t) => t + ":" + ("image" in e ? typeof e.image == "string" ? e.image : e.image.url : e.video.url), (e, r, i) => {
			var o = vm(), s = R(o);
			let c;
			var d = R(s), h = (e) => {}, _ = L(() => S(r).caption?.startsWith("__card_no_thumbnail__\n")), v = (e) => {
				{
					let t = L(() => S(r).caption || ""), n = L(() => typeof S(r).image == "string" ? S(r).image : S(r).image.url);
					En(e, {
						get alt() {
							return S(t);
						},
						get src() {
							return S(n);
						},
						loading: "lazy"
					});
				}
			}, y = (e) => {
				var n = lm(), a = B(n);
				ft(a, {});
				var o = D(a, 2);
				{
					let e = L(() => S(r).caption || null), t = L(() => "thumbnail " + (S(i) + 1));
					em(o, {
						get src() {
							return S(r).video.url;
						},
						get title() {
							return S(e);
						},
						is_stream: !1,
						get "data-testid"() {
							return S(t);
						},
						alt: "",
						loading: "lazy",
						loop: !1
					});
				}
				t(e, n);
			};
			a(d, (e) => {
				S(_) ? e(h) : "image" in S(r) ? e(v, 1) : e(y, -1);
			});
			var x = D(d, 2), C = (e) => {
				var n = gm();
				f(n, 21, () => S(r).caption.split("\n").filter((e) => e !== "__card_no_thumbnail__"), m, (e, n) => {
					var r = hm(), i = R(r), o = (e) => {
						var r = pm(), i = B(r), a = I(i, !0), o = D(i, 2), s = I(o, !0);
						N((e, t) => {
							u(a, e), u(s, t);
						}, [() => S(n).slice(0, S(n).indexOf(": ")), () => S(n).slice(S(n).indexOf(": ") + 2)]), t(e, r);
					}, s = L(() => S(n).includes(": ")), c = (e) => {
						var r = mm(), i = I(r, !0);
						N(() => u(i, S(n))), t(e, r);
					};
					a(i, (e) => {
						S(s) ? e(o) : e(c, -1);
					}), F(r), t(e, r);
				}), F(n), t(e, n);
			};
			a(x, (e) => {
				S(r).caption && e(C);
			}), F(s);
			var w = D(s, 2), T = (e) => {
				var n = _m();
				He(R(n), {}), F(n), l("click", n, (e) => {
					e.stopPropagation(), $e(S(i));
				}), t(e, n);
			};
			a(w, (e) => {
				n.interactive && e(T);
			}), F(o), N((e) => {
				c = g(s, 1, "thumbnail-item thumbnail-lg svelte-1qqxspv", null, c, { selected: b() === S(i) }), be(s, "aria-label", e);
			}, [() => (S(r).caption?.startsWith("__card_no_thumbnail__\n") ? "Card " : "Thumbnail ") + (S(i) + 1) + " of " + S(H).length]), l("click", s, () => {
				b() === null && p() && ne()(), b(S(i)), Oe(S(i));
			}), t(e, o);
		}), F(ue), F(k), F(r), ee(r, (e) => _e = e, () => _e), N(() => {
			A = g(k, 1, "grid-wrap svelte-1qqxspv", null, A, {
				minimal: !1,
				"fixed-height": !d() || d() == "auto",
				hidden: ge
			}), M = Se(k, "", M, { height: d() === "auto" ? null : typeof d() == "number" ? d() + "px" : d() }), de = g(ue, 1, "grid-container svelte-1qqxspv", null, de, { "pt-6": i() }), Se(ue, `--grid-cols:${S(we) ?? ""}; --grid-rows:${c() ?? ""}; --object-fit: ${h() ?? ""};`);
		}), t(e, r);
	};
	a(ot, (e) => {
		o() == null || S(H) == null || S(H).length === 0 ? e(st) : e(ct, -1);
	}), ye("innerHeight", (e) => e), t(e, tt), M();
}
o(["keydown", "click"]);
// frontend/node_modules/@gradio/statustracker/dist/static/utils.js
function xm(e) {
	let t = [
		"",
		"k",
		"M",
		"G",
		"T",
		"P",
		"E",
		"Z"
	], n = 0;
	for (; e > 1e3 && n < t.length - 1;) e /= 1e3, n++;
	let r = t[n];
	return (Number.isInteger(e) ? e : e.toFixed(1)) + r;
}
// frontend/node_modules/svelte/src/motion/utils.js
function Sm(e) {
	return Object.prototype.toString.call(e) === "[object Date]";
}
// frontend/node_modules/svelte/src/motion/spring.js
function Cm(e, t, n, r) {
	if (typeof n == "number" || Sm(n)) {
		let i = r - n, a = (n - t) / (e.dt || 1 / 60), o = (a + (e.opts.stiffness * i - e.opts.damping * a) * e.inv_mass) * e.dt;
		return Math.abs(o) < e.opts.precision && Math.abs(i) < e.opts.precision ? r : (e.settled = !1, Sm(n) ? new Date(n.getTime() + o) : n + o);
	}
	if (Array.isArray(n)) return n.map((i, a) => Cm(e, t[a], n[a], r[a]));
	if (typeof n == "object") {
		let i = {};
		for (let a in n) i[a] = Cm(e, t[a], n[a], r[a]);
		return i;
	}
	throw Error(`Cannot spring ${typeof n} values`);
}
function wm(e, t = {}) {
	let n = se(e), { stiffness: i = .15, damping: a = .8, precision: o = .01 } = t, s, c, l, u = e, d = e, f = 1, m = 0, h = !1;
	function g(t, i = {}) {
		d = t;
		let a = l = {};
		return e == null || i.hard || _.stiffness >= 1 && _.damping >= 1 ? (h = !0, s = p.now(), u = t, n.set(e = d), Promise.resolve()) : (i.soft && (m = 1 / ((i.soft === !0 ? .5 : +i.soft) * 60), f = 0), c ||= (s = p.now(), h = !1, r((t) => {
			if (h) return h = !1, c = null, !1;
			f = Math.min(f + m, 1);
			let r = Math.min(t - s, 1e3 / 30), i = {
				inv_mass: f,
				opts: _,
				settled: !0,
				dt: r * 60 / 1e3
			}, a = Cm(i, u, e, d);
			return s = t, u = e, n.set(e = a), i.settled && (c = null), !i.settled;
		})), new Promise((e) => {
			c.promise.then(() => {
				a === l && e();
			});
		}));
	}
	let _ = {
		set: g,
		update: (t, n) => g(t(d, e), n),
		subscribe: n.subscribe,
		stiffness: i,
		damping: a,
		precision: o
	};
	return _;
}
// frontend/node_modules/@gradio/statustracker/dist/static/Loader.svelte
var Tm = s("<div><svg viewBox=\"-1200 -1200 3000 3000\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\" class=\"svelte-m6d381\"><g><path d=\"M255.926 0.754768L509.702 139.936V221.027L255.926 81.8465V0.754768Z\" fill=\"#FF7C00\" fill-opacity=\"0.4\" class=\"svelte-m6d381\"></path><path d=\"M509.69 139.936L254.981 279.641V361.255L509.69 221.55V139.936Z\" fill=\"#FF7C00\" class=\"svelte-m6d381\"></path><path d=\"M0.250138 139.937L254.981 279.641V361.255L0.250138 221.55V139.937Z\" fill=\"#FF7C00\" fill-opacity=\"0.4\" class=\"svelte-m6d381\"></path><path d=\"M255.923 0.232622L0.236328 139.936V221.55L255.923 81.8469V0.232622Z\" fill=\"#FF7C00\" class=\"svelte-m6d381\"></path></g><g><path d=\"M255.926 141.5L509.702 280.681V361.773L255.926 222.592V141.5Z\" fill=\"#FF7C00\" fill-opacity=\"0.4\" class=\"svelte-m6d381\"></path><path d=\"M509.69 280.679L254.981 420.384V501.998L509.69 362.293V280.679Z\" fill=\"#FF7C00\" class=\"svelte-m6d381\"></path><path d=\"M0.250138 280.681L254.981 420.386V502L0.250138 362.295V280.681Z\" fill=\"#FF7C00\" fill-opacity=\"0.4\" class=\"svelte-m6d381\"></path><path d=\"M255.923 140.977L0.236328 280.68V362.294L255.923 222.591V140.977Z\" fill=\"#FF7C00\" class=\"svelte-m6d381\"></path></g></svg></div>");
function Em(e, n) {
	P(n, !0);
	let r = () => ge(l, "$top", a), i = () => ge(u, "$bottom", a), [a, o] = de();
	var s = this && this.__awaiter || function(e, t, n, r) {
		function i(e) {
			return e instanceof n ? e : new n(function(t) {
				t(e);
			});
		}
		return new (n ||= Promise)(function(n, a) {
			function o(e) {
				try {
					c(r.next(e));
				} catch (e) {
					a(e);
				}
			}
			function s(e) {
				try {
					c(r.throw(e));
				} catch (e) {
					a(e);
				}
			}
			function c(e) {
				e.done ? n(e.value) : i(e.value).then(o, s);
			}
			c((r = r.apply(e, t || [])).next());
		});
	};
	let c = z(n, "margin", 3, !0), l = wm([0, 0]), u = wm([0, 0]), d = A(!1);
	function f() {
		return s(this, void 0, void 0, function* () {
			yield Promise.all([l.set([125, 140]), u.set([-125, -140])]), yield Promise.all([l.set([-125, 140]), u.set([125, -140])]), yield Promise.all([l.set([-125, 0]), u.set([125, -0])]), yield Promise.all([l.set([125, 0]), u.set([-125, 0])]);
		});
	}
	function p() {
		return s(this, void 0, void 0, function* () {
			yield f(), S(d) || p();
		});
	}
	function m() {
		return s(this, void 0, void 0, function* () {
			yield Promise.all([l.set([125, 0]), u.set([-125, 0])]), p();
		});
	}
	ve(() => (m(), () => {
		V(d, !0);
	}));
	var h = Tm();
	let _;
	var v = R(h), y = R(v), b = D(y);
	F(v), F(h), N(() => {
		_ = g(h, 1, "svelte-m6d381", null, _, { margin: c() }), Se(y, `transform: translate(${r()[0] ?? ""}px, ${r()[1] ?? ""}px);`), Se(b, `transform: translate(${i()[0] ?? ""}px, ${i()[1] ?? ""}px);`);
	}), t(e, h), M(), o();
}
// frontend/node_modules/@gradio/statustracker/dist/static/index.svelte
var Dm = function(e, t, n, r) {
	function i(e) {
		return e instanceof n ? e : new n(function(t) {
			t(e);
		});
	}
	return new (n ||= Promise)(function(n, a) {
		function o(e) {
			try {
				c(r.next(e));
			} catch (e) {
				a(e);
			}
		}
		function s(e) {
			try {
				c(r.throw(e));
			} catch (e) {
				a(e);
			}
		}
		function c(e) {
			e.done ? n(e.value) : i(e.value).then(o, s);
		}
		c((r = r.apply(e, t || [])).next());
	});
}, Om = [], km = !1, Am = typeof window < "u" ? window.requestAnimationFrame : (e) => {}, jm = /* @__PURE__ */ new Set();
function Mm(e) {
	return Dm(this, arguments, void 0, function* (e, t = !0) {
		if (!(window.__gradio_mode__ === "website" || window.__gradio_mode__ !== "app" && t !== !0)) {
			if (Om.push(e), !km) km = !0;
			else return;
			yield x(), Am(() => {
				let e = [0, 0];
				for (let t = 0; t < Om.length; t++) {
					let n = Om[t].getBoundingClientRect();
					(t === 0 || n.top + window.scrollY <= e[0]) && (e[0] = n.top + window.scrollY, e[1] = t);
				}
				window.scrollTo({
					top: e[0] - 20,
					behavior: "smooth"
				}), km = !1, Om = [];
			});
		}
	});
}
var Nm = s("<div class=\"validation-error svelte-124hqw6\"> <button class=\"svelte-124hqw6\"><!></button></div>"), Pm = s("<div class=\"eta-bar svelte-124hqw6\"></div>"), Fm = s("<!> ", 1), Im = s("<!> <!> <!> <!>", 1), Lm = s("<div class=\"progress-level svelte-124hqw6\"><div class=\"progress-level-inner svelte-124hqw6\"><!></div> <div class=\"progress-bar-wrap svelte-124hqw6\" role=\"progressbar\" aria-valuemin=\"0\" aria-valuemax=\"100\"><div class=\"progress-bar svelte-124hqw6\"></div></div></div>"), Rm = s("<p class=\"loading svelte-124hqw6\"> </p> <!>", 1), zm = s("<!> <div><!> <!></div> <!> <!>", 1), Bm = s("<div class=\"clear-status svelte-124hqw6\"><!></div> <span class=\"error svelte-124hqw6\"> </span> <!>", 1), Vm = s("<div> <!> </div>"), Hm = s("<div data-testid=\"status-tracker\"><!> <!></div> <!>", 1);
function Um(e, n) {
	P(n, !0);
	let r = z(n, "eta", 3, null), i = z(n, "component_id", 3, null), o = z(n, "fn_index", 3, null), s = z(n, "scroll_to_output", 3, !1), c = z(n, "timer", 3, !0), l = z(n, "show_progress", 3, "full"), d = z(n, "message", 3, null), p = z(n, "progress", 3, null), h = z(n, "time_start", 3, null), _ = z(n, "eta_total", 3, null), v = z(n, "variant", 3, "default"), x = z(n, "loading_text", 3, "Loading..."), w = z(n, "absolute", 3, !0), E = z(n, "translucent", 3, !1), O = z(n, "border", 3, !1), k = z(n, "validation_error", 7, null), j = z(n, "show_validation_error", 3, !0), te = z(n, "type", 3, null), ne = z(n, "used_cache", 3, null), re = z(n, "cache_duration", 3, null), ie = z(n, "avg_time", 3, null), oe = z(n, "cache_event_id", 3, null), se, ce = !1, le = A(0), ue = A(null), de = A(null), fe = A(!1), pe = A(null), me = A(!1), he = A(!1), ge = A(null), _e = A(null), ye = A("from cache"), xe = A(!1), H = null, Ce = null, we = null;
	function Te() {
		H && clearTimeout(H), Ce && clearTimeout(Ce), H = null, Ce = null, V(me, !1), V(he, !1);
	}
	let Ee = L(() => !(j() && k()) && (te() === "input" || !n.status || n.status === "complete" || l() === "hidden" || n.status == "streaming")), De = A(0), Oe = L(() => S(de) === null || S(de) <= 0 || !S(De) ? 0 : Math.min(S(De) / S(de), 1)), ke = L(() => S(De).toFixed(1)), Ae = L(() => p() == null), je = L(() => r() !== null && r() !== void 0 ? r() : S(ue));
	function Me() {
		Am(() => {
			V(De, (performance.now() - S(le)) / 1e3), ce && Me();
		});
	}
	let Ne = L(() => {
		let e = null;
		e = p() == null ? null : p().map((e) => {
			if (e.index != null && e.length != null) return e.index / e.length;
			if (e.progress != null) return e.progress;
		});
		let t, n = "";
		return e ? (t = e[e.length - 1], n = t === 0 ? "0" : "150ms") : t = void 0, {
			progress_level: e,
			last_progress_level: t,
			progress_bar_transition: n
		};
	}), Pe = L(() => {
		if (S(Ne).last_progress_level == null) return null;
		let e = Math.round(Math.min(Math.max(S(Ne).last_progress_level, 0), 1) * 100), t = `${e}%`, n = p() === null || p() === void 0 ? void 0 : p()[p().length - 1];
		return n?.index != null && n?.length != null && (t = `${xm(n.index)} / ${xm(n.length)}`, n.unit && (t += ` ${n.unit}`)), n?.desc && (t = `${n.desc}: ${t}`), {
			valuenow: e,
			valuetext: t
		};
	});
	function Ie() {
		ce || (h() ?? V(ue, V(pe, null), !0), V(le, h() !== null && h() !== void 0 ? h() : performance.now(), !0), ce = !0, Me());
	}
	function Le() {
		V(ue, V(pe, null), !0), ce &&= !1;
	}
	ve(() => {
		n.status === "pending" ? Ie() : C(() => {
			Le();
		});
	}), ve(() => {
		n.status === "pending" && h() != null && ce && V(le, h());
	}), ve(() => {
		se && s() && (n.status === "pending" || n.status === "complete") && Mm(se, n.autoscroll);
	}), ve(() => {
		_() == null ? S(je) != null && S(ue) !== S(je) && (V(de, (performance.now() - S(le)) / 1e3 + S(je)), V(pe, S(de).toFixed(1), !0), V(ue, S(je), !0)) : (V(de, _()), V(pe, _().toFixed(1), !0), r() != null && V(ue, r()));
	});
	function Re() {
		V(fe, !1);
	}
	ve(() => {
		C(() => {
			Re();
		}), n.status === "error" && d() && V(fe, !0);
	}), ve(() => {
		if (n.status === "complete" && te() === "output" && ne() && re() != null) {
			let e = oe() == null ? null : `${(i() !== null && i() !== void 0 ? i() : o()) ?? "unknown"}:${o() !== null && o() !== void 0 ? o() : "unknown"}:${oe()}`;
			if (e === we || e != null && jm.has(e)) return;
			we = e, e != null && jm.add(e), V(ge, re().toFixed(1), !0), V(ye, ne() === "full" ? "from cache" : "used cache", !0), V(xe, ie() != null && ie() > re() && ie() > 0, !0), V(_e, S(xe) ? ie().toFixed(1) : null, !0), V(me, !0), V(he, !1), H && clearTimeout(H), Ce && clearTimeout(Ce), H = setTimeout(() => {
				V(he, !0), Ce = setTimeout(() => {
					V(me, !1), V(he, !1);
				}, 500);
			}, 1750);
		} else te() === "output" && !ne() && Te();
	});
	var ze = Hm(), U = B(ze);
	let Be, Ve;
	var Ue = R(U), We = (e) => {
		var r = Nm(), i = R(r), a = D(i), o = R(a);
		{
			let e = L(() => n.i18n ? n.i18n("common.clear") : "Clear");
			Fe(o, {
				get Icon() {
					return He;
				},
				get label() {
					return S(e);
				},
				disabled: !1,
				size: "x-small",
				background: "var(--background-fill-primary)",
				color: "var(--error-background-text)",
				border: "var(--border-color-primary)",
				onclick: () => k(null)
			});
		}
		F(a), F(r), N(() => u(i, `${k() ?? ""} `)), t(e, r);
	};
	a(Ue, (e) => {
		k() && j() && e(We);
	});
	var Ge = D(Ue, 2), Ke = (e) => {
		var i = zm(), o = B(i), s = (e) => {
			var n = Pm();
			let r;
			N(() => r = Se(n, "", r, { transform: `translateX(${(S(Oe) || 0) * 100 - 100}%)` })), t(e, n);
		};
		a(o, (e) => {
			v() === "default" && S(Ae) && l() === "full" && e(s);
		});
		var d = D(o, 2);
		let h;
		var _ = R(d), C = (e) => {
			var n = y(), r = B(n);
			f(r, 17, p, m, (e, n) => {
				var r = y(), i = B(r), o = (e) => {
					var r = Fm(), i = B(r), o = (e) => {
						var r = b();
						N((e, t) => u(r, `${e ?? ""}/${t ?? ""}`), [() => xm(S(n).index || 0), () => xm(S(n).length)]), t(e, r);
					}, s = (e) => {
						var r = b();
						N((e) => u(r, e), [() => xm(S(n).index || 0)]), t(e, r);
					};
					a(i, (e) => {
						S(n).length == null ? e(s, -1) : e(o);
					});
					var c = D(i);
					N(() => u(c, ` ${S(n).unit ?? ""} |  `)), t(e, r);
				};
				a(i, (e) => {
					S(n).index != null && e(o);
				}), t(e, r);
			}), t(e, n);
		}, w = (e) => {
			var r = b();
			N(() => u(r, `queue: ${n.queue_position + 1}/${n.queue_size ?? ""} |`)), t(e, r);
		}, E = (e) => {
			var n = b("processing |");
			t(e, n);
		};
		a(_, (e) => {
			p() ? e(C) : n.queue_position !== null && n.queue_size !== void 0 && n.queue_position >= 0 ? e(w, 1) : n.queue_position === 0 && e(E, 2);
		});
		var O = D(_, 2), k = (e) => {
			var n = b();
			N(() => u(n, `${S(ke) ?? ""}${r() ? `/${S(pe)}` : ""}s`)), t(e, n);
		};
		a(O, (e) => {
			c() && e(k);
		}), F(d);
		var A = D(d, 2), j = (e) => {
			var r = Lm(), i = R(r), o = R(i), s = (e) => {
				var n = y(), r = B(n);
				f(r, 17, p, m, (e, n, r) => {
					var i = y(), o = B(i), s = (e) => {
						var i = Im(), o = B(i), s = (e) => {
							var n = b("\xA0/");
							t(e, n);
						};
						a(o, (e) => {
							r !== 0 && e(s);
						});
						var c = D(o, 2), l = (e) => {
							var r = b();
							N(() => u(r, S(n).desc)), t(e, r);
						};
						a(c, (e) => {
							S(n).desc != null && e(l);
						});
						var d = D(c, 2), f = (e) => {
							var n = b("-");
							t(e, n);
						};
						a(d, (e) => {
							S(n).desc != null && S(Ne).progress_level && S(Ne).progress_level[r] != null && e(f);
						});
						var p = D(d, 2), m = (e) => {
							var n = b();
							N((e) => u(n, `${e ?? ""}%`), [() => (100 * (S(Ne).progress_level[r] || 0)).toFixed(1)]), t(e, n);
						};
						a(p, (e) => {
							S(Ne).progress_level != null && e(m);
						}), t(e, i);
					};
					a(o, (e) => {
						(S(n).desc != null || S(Ne).progress_level && S(Ne).progress_level[r] != null) && e(s);
					}), t(e, i);
				}), t(e, n);
			};
			a(o, (e) => {
				p() != null && e(s);
			}), F(i);
			var c = D(i, 2), l = R(c);
			let d;
			F(c), F(r), N((e) => {
				be(c, "aria-label", e), be(c, "aria-valuenow", S(Pe)?.valuenow), be(c, "aria-valuetext", S(Pe)?.valuetext), d = Se(l, "", d, {
					width: `${S(Ne).last_progress_level * 100}%`,
					transition: S(Ne).progress_bar_transition
				});
			}, [() => p()?.[p().length - 1]?.desc || n.i18n("common.progress")]), t(e, r);
		}, M = (e) => {
			{
				let t = L(() => v() === "default");
				Em(e, { get margin() {
					return S(t);
				} });
			}
		};
		a(A, (e) => {
			S(Ne).last_progress_level == null ? l() === "full" && e(M, 1) : e(j);
		});
		var ee = D(A, 2), P = (e) => {
			var r = Rm(), i = B(r), a = I(i, !0), o = D(i, 2);
			ae(o, () => n.additional_loading_text ?? T), N(() => u(a, x())), t(e, r);
		};
		a(ee, (e) => {
			c() || e(P);
		}), N(() => h = g(d, 1, "progress-text svelte-124hqw6", null, h, {
			"meta-text-center": v() === "center",
			"meta-text": v() === "default"
		})), t(e, i);
	}, qe = (e) => {
		var r = Bm(), i = B(r), a = R(i);
		{
			let e = L(() => n.i18n("common.clear"));
			Fe(a, {
				get Icon() {
					return He;
				},
				get label() {
					return S(e);
				},
				disabled: !1,
				onclick: () => {
					n.on_clear_status?.();
				}
			});
		}
		F(i);
		var o = D(i, 2), s = I(o, !0), c = D(o, 2);
		ae(c, () => n.error_details ?? T), N((e) => u(s, e), [() => n.i18n("common.error")]), t(e, r);
	};
	a(Ge, (e) => {
		n.status === "pending" ? e(Ke) : n.status === "error" && e(qe, 1);
	}), F(U), ee(U, (e) => se = e, () => se);
	var Je = D(U, 2), Ye = (e) => {
		var n = Vm();
		let r, i;
		var o = R(n), s = D(o), c = (e) => {
			var n = b();
			N(() => u(n, `~${S(_e) ?? ""}s
			→ `)), t(e, n);
		};
		a(s, (e) => {
			S(xe) && e(c);
		});
		var l = D(s);
		F(n), N(() => {
			r = g(n, 1, "cache-indicator svelte-124hqw6", null, r, { "fade-out": S(he) }), i = Se(n, "", i, { position: w() ? "absolute" : "static" }), u(o, `⚡ ${S(ye) ?? ""}: `), u(l, `${S(ge) ?? ""}s`);
		}), t(e, n);
	};
	a(Je, (e) => {
		S(me) && e(Ye);
	}), N(() => {
		Be = g(U, 1, `wrap ${v() ?? ""} ${l() ?? ""}`, "svelte-124hqw6", Be, {
			"no-click": k() && j(),
			hide: S(Ee),
			translucent: v() === "center" && (n.status === "pending" || n.status === "error") || E() || l() === "minimal" || k(),
			generating: n.status === "generating" && l() === "full",
			border: O()
		}), Ve = Se(U, "", Ve, {
			position: w() ? "absolute" : "static",
			padding: w() ? "0" : "var(--size-8) 0"
		});
	}), t(e, ze), M();
}
// frontend/node_modules/amuchina/dist/utils.js
var Wm = (e) => JSON.parse(JSON.stringify(e)), Gm = (e) => e.nodeType === 1, Km = (e) => Sh.has(e.tagName), qm = (e) => "action" in e, Jm = (e) => e.tagName === "IFRAME", Ym = (e) => "formAction" in e, Xm = (e) => "protocol" in e, Zm = (() => {
	let e = /^(?:\w+script|data):/i;
	return (t) => e.test(t);
})(), Qm = (() => {
	let e = /(?:script|data):/i;
	return (t) => e.test(t);
})(), $m = (e) => {
	let t = {};
	for (let n = 0, r = e.length; n < r; n++) {
		let r = e[n];
		for (let e in r) t[e] = t[e] ? t[e].concat(r[e]) : r[e];
	}
	return t;
}, eh = (e, t) => {
	let n = e.firstChild;
	for (; n;) {
		let r = n.nextSibling;
		Gm(n) && (t(n, e), n.parentNode && eh(n, t)), n = r;
	}
}, th = (e, t) => {
	let n = document.createNodeIterator(e, NodeFilter.SHOW_ELEMENT), r;
	for (; r = n.nextNode();) {
		let e = r.parentNode;
		e && t(r, e);
	}
}, nh = (e, t) => globalThis.document && globalThis.document.createNodeIterator ? th(e, t) : eh(e, t), rh = /* @__PURE__ */ "a.abbr.acronym.address.area.article.aside.audio.b.bdi.bdo.bgsound.big.blockquote.body.br.button.canvas.caption.center.cite.code.col.colgroup.datalist.dd.del.details.dfn.dialog.dir.div.dl.dt.em.fieldset.figcaption.figure.font.footer.form.h1.h2.h3.h4.h5.h6.head.header.hgroup.hr.html.i.img.input.ins.kbd.keygen.label.layer.legend.li.link.listing.main.map.mark.marquee.menu.meta.meter.nav.nobr.ol.optgroup.option.output.p.picture.popup.pre.progress.q.rb.rp.rt.rtc.ruby.s.samp.section.select.selectmenu.small.source.span.strike.strong.style.sub.summary.sup.table.tbody.td.tfoot.th.thead.time.tr.track.tt.u.ul.var.video.wbr".split("."), ih = [
	"basefont",
	"command",
	"data",
	"iframe",
	"image",
	"plaintext",
	"portal",
	"slot",
	"textarea",
	"title",
	"xmp"
], ah = /* @__PURE__ */ new Set([...rh, ...ih]), oh = /* @__PURE__ */ "svg.a.altglyph.altglyphdef.altglyphitem.animatecolor.animatemotion.animatetransform.circle.clippath.defs.desc.ellipse.filter.font.g.glyph.glyphref.hkern.image.line.lineargradient.marker.mask.metadata.mpath.path.pattern.polygon.polyline.radialgradient.rect.stop.style.switch.symbol.text.textpath.title.tref.tspan.view.vkern.feBlend.feColorMatrix.feComponentTransfer.feComposite.feConvolveMatrix.feDiffuseLighting.feDisplacementMap.feDistantLight.feFlood.feFuncA.feFuncB.feFuncG.feFuncR.feGaussianBlur.feImage.feMerge.feMergeNode.feMorphology.feOffset.fePointLight.feSpecularLighting.feSpotLight.feTile.feTurbulence".split("."), sh = [
	"animate",
	"color-profile",
	"cursor",
	"discard",
	"fedropshadow",
	"font-face",
	"font-face-format",
	"font-face-name",
	"font-face-src",
	"font-face-uri",
	"foreignobject",
	"hatch",
	"hatchpath",
	"mesh",
	"meshgradient",
	"meshpatch",
	"meshrow",
	"missing-glyph",
	"script",
	"set",
	"solidcolor",
	"unknown",
	"use"
], ch = /* @__PURE__ */ new Set([...oh, ...sh]), lh = /* @__PURE__ */ "math.menclose.merror.mfenced.mfrac.mglyph.mi.mlabeledtr.mmultiscripts.mn.mo.mover.mpadded.mphantom.mroot.mrow.ms.mspace.msqrt.mstyle.msub.msup.msubsup.mtable.mtd.mtext.mtr.munder.munderover".split("."), uh = [
	"maction",
	"maligngroup",
	"malignmark",
	"mlongdiv",
	"mscarries",
	"mscarry",
	"msgroup",
	"mstack",
	"msline",
	"msrow",
	"semantics",
	"annotation",
	"annotation-xml",
	"mprescripts",
	"none"
], dh = /* @__PURE__ */ new Set([...lh, ...uh]), fh = /* @__PURE__ */ "abbr.accept.accept-charset.accesskey.action.align.alink.allow.allowfullscreen.alt.anchor.archive.as.async.autocapitalize.autocomplete.autocorrect.autofocus.autopictureinpicture.autoplay.axis.background.behavior.bgcolor.border.bordercolor.capture.cellpadding.cellspacing.challenge.char.charoff.charset.checked.cite.class.classid.clear.code.codebase.codetype.color.cols.colspan.compact.content.contenteditable.controls.controlslist.conversiondestination.coords.crossorigin.csp.data.datetime.declare.decoding.default.defer.dir.direction.dirname.disabled.disablepictureinpicture.disableremoteplayback.disallowdocumentaccess.download.draggable.elementtiming.enctype.end.enterkeyhint.event.exportparts.face.for.form.formaction.formenctype.formmethod.formnovalidate.formtarget.frame.frameborder.headers.height.hidden.high.href.hreflang.hreftranslate.hspace.http-equiv.id.imagesizes.imagesrcset.importance.impressiondata.impressionexpiry.incremental.inert.inputmode.integrity.invisible.ismap.keytype.kind.label.lang.language.latencyhint.leftmargin.link.list.loading.longdesc.loop.low.lowsrc.manifest.marginheight.marginwidth.max.maxlength.mayscript.media.method.min.minlength.multiple.muted.name.nohref.nomodule.nonce.noresize.noshade.novalidate.nowrap.object.open.optimum.part.pattern.ping.placeholder.playsinline.policy.poster.preload.pseudo.readonly.referrerpolicy.rel.reportingorigin.required.resources.rev.reversed.role.rows.rowspan.rules.sandbox.scheme.scope.scopes.scrollamount.scrolldelay.scrolling.select.selected.shadowroot.shadowrootdelegatesfocus.shape.size.sizes.slot.span.spellcheck.src.srclang.srcset.standby.start.step.style.summary.tabindex.target.text.title.topmargin.translate.truespeed.trusttoken.type.usemap.valign.value.valuetype.version.virtualkeyboardpolicy.vlink.vspace.webkitdirectory.width.wrap".split("."), ph = ["allowpaymentrequest", "is"];
[...fh, ...ph];
var mh = /* @__PURE__ */ "accent-height.accumulate.additive.alignment-baseline.ascent.attributename.attributetype.azimuth.basefrequency.baseline-shift.begin.bias.by.class.clip.clippathunits.clip-path.clip-rule.color.color-interpolation.color-interpolation-filters.color-profile.color-rendering.cx.cy.d.dx.dy.diffuseconstant.direction.display.divisor.dominant-baseline.dur.edgemode.elevation.end.fill.fill-opacity.fill-rule.filter.filterunits.flood-color.flood-opacity.font-family.font-size.font-size-adjust.font-stretch.font-style.font-variant.font-weight.fx.fy.g1.g2.glyph-name.glyphref.gradientunits.gradienttransform.height.href.id.image-rendering.in.in2.k.k1.k2.k3.k4.kerning.keypoints.keysplines.keytimes.lang.lengthadjust.letter-spacing.kernelmatrix.kernelunitlength.lighting-color.local.marker-end.marker-mid.marker-start.markerheight.markerunits.markerwidth.maskcontentunits.maskunits.max.mask.media.method.mode.min.name.numoctaves.offset.operator.opacity.order.orient.orientation.origin.overflow.paint-order.path.pathlength.patterncontentunits.patterntransform.patternunits.points.preservealpha.preserveaspectratio.primitiveunits.r.rx.ry.radius.refx.refy.repeatcount.repeatdur.restart.result.rotate.scale.seed.shape-rendering.specularconstant.specularexponent.spreadmethod.startoffset.stddeviation.stitchtiles.stop-color.stop-opacity.stroke-dasharray.stroke-dashoffset.stroke-linecap.stroke-linejoin.stroke-miterlimit.stroke-opacity.stroke.stroke-width.style.surfacescale.systemlanguage.tabindex.targetx.targety.transform.transform-origin.text-anchor.text-decoration.text-rendering.textlength.type.u1.u2.unicode.values.viewbox.visibility.version.vert-adv-y.vert-origin-x.vert-origin-y.width.word-spacing.wrap.writing-mode.xchannelselector.ychannelselector.x.x1.x2.xmlns.y.y1.y2.z.zoomandpan".split("."), hh = [];
[...mh, ...hh];
var gh = /* @__PURE__ */ "accent.accentunder.align.bevelled.close.columnsalign.columnlines.columnspan.denomalign.depth.dir.display.displaystyle.encoding.fence.frame.height.href.id.largeop.length.linethickness.lspace.lquote.mathbackground.mathcolor.mathsize.mathvariant.maxsize.minsize.movablelimits.notation.numalign.open.rowalign.rowlines.rowspacing.rowspan.rspace.rquote.scriptlevel.scriptminsize.scriptsizemultiplier.selection.separator.separators.stretchy.subscriptshift.supscriptshift.symmetric.voffset.width.xmlns".split("."), _h = [];
[...gh, ..._h];
var vh = {
	HTML: "http://www.w3.org/1999/xhtml",
	SVG: "http://www.w3.org/2000/svg",
	MATH: "http://www.w3.org/1998/Math/MathML"
}, yh = {
	[vh.HTML]: ah,
	[vh.SVG]: ch,
	[vh.MATH]: dh
};
vh.HTML, vh.SVG, vh.MATH;
var bh = {
	[vh.HTML]: "html",
	[vh.SVG]: "svg",
	[vh.MATH]: "math"
}, xh = {
	[vh.HTML]: "",
	[vh.SVG]: "svg:",
	[vh.MATH]: "math:"
}, Sh = /* @__PURE__ */ new Set([
	"A",
	"AREA",
	"BUTTON",
	"FORM",
	"IFRAME",
	"INPUT"
]), Ch = {
	allowComments: !0,
	allowCustomElements: !1,
	allowUnknownMarkup: !1,
	allowElements: [
		...rh,
		...oh.map((e) => `svg:${e}`),
		...lh.map((e) => `math:${e}`)
	],
	allowAttributes: $m([
		Object.fromEntries(fh.map((e) => [e, ["*"]])),
		Object.fromEntries(mh.map((e) => [e, ["svg:*"]])),
		Object.fromEntries(gh.map((e) => [e, ["math:*"]]))
	])
}, wh = function(e, t, n, r, i) {
	if (r === "m") throw TypeError("Private method is not writable");
	if (r === "a" && !i) throw TypeError("Private accessor was defined without a setter");
	if (typeof t == "function" ? e !== t || !i : !t.has(e)) throw TypeError("Cannot write private member to an object whose class did not declare it");
	return r === "a" ? i.call(e, n) : i ? i.value = n : t.set(e, n), n;
}, Th = function(e, t, n, r) {
	if (n === "a" && !r) throw TypeError("Private accessor was defined without a getter");
	if (typeof t == "function" ? e !== t || !r : !t.has(e)) throw TypeError("Cannot read private member from an object whose class did not declare it");
	return n === "m" ? r : n === "a" ? r.call(e) : r ? r.value : t.get(e);
}, Eh, Dh, Oh, kh = class {
	constructor(e = {}) {
		Eh.set(this, void 0), Dh.set(this, void 0), Oh.set(this, void 0), this.getConfiguration = () => Wm(Th(this, Eh, "f")), this.sanitize = (e) => {
			let t = Th(this, Dh, "f"), n = Th(this, Oh, "f");
			return nh(e, (e, r) => {
				let i = e.namespaceURI || vh.HTML, a = r.namespaceURI || vh.HTML, o = yh[i], s = bh[i], c = xh[i], l = e.tagName.toLowerCase(), u = `${c}${l}`, d = `${c}*`;
				if (!o.has(l) || !t.has(u) || i !== a && l !== s) r.removeChild(e);
				else {
					let t = e.getAttributeNames(), r = t.length;
					if (r) {
						for (let i = 0; i < r; i++) {
							let r = t[i], a = n[r];
							a && (a.has(d) || a.has(u)) || e.removeAttribute(r);
						}
						if (Km(e)) {
							if (Xm(e)) {
								let t = e.getAttribute("href");
								t && Qm(t) && Zm(e.protocol) && e.removeAttribute("href");
							} else qm(e) ? Zm(e.action) && e.removeAttribute("action") : Ym(e) ? Zm(e.formAction) && e.removeAttribute("formaction") : Jm(e) && (Zm(e.src) && e.removeAttribute("formaction"), e.setAttribute("sandbox", "allow-scripts"));
						}
					}
				}
			}), e;
		}, this.sanitizeFor = (e, t) => {
			throw Error("\"sanitizeFor\" is not implemented yet");
		};
		let { allowComments: t, allowCustomElements: n, allowUnknownMarkup: r, blockElements: i, dropElements: a, dropAttributes: o } = e;
		if (t === !1) throw Error("A false \"allowComments\" is not supported yet");
		if (n) throw Error("A true \"allowCustomElements\" is not supported yet");
		if (r) throw Error("A true \"allowUnknownMarkup\" is not supported yet");
		if (i) throw Error("\"blockElements\" is not supported yet, use \"allowElements\" instead");
		if (a) throw Error("\"dropElements\" is not supported yet, use \"allowElements\" instead");
		if (o) throw Error("\"dropAttributes\" is not supported yet, use \"allowAttributes\" instead");
		wh(this, Eh, Wm(Ch), "f");
		let { allowElements: s, allowAttributes: c } = e;
		s && (Th(this, Eh, "f").allowElements = e.allowElements), c && (Th(this, Eh, "f").allowAttributes = e.allowAttributes), wh(this, Dh, new Set(Th(this, Eh, "f").allowElements), "f"), wh(this, Oh, Object.fromEntries(Object.entries(Th(this, Eh, "f").allowAttributes || {}).map(([e, t]) => [e, new Set(t)])), "f");
	}
};
Eh = /* @__PURE__ */ new WeakMap(), Dh = /* @__PURE__ */ new WeakMap(), Oh = /* @__PURE__ */ new WeakMap(), kh.getDefaultConfiguration = () => Wm(Ch);
// frontend/node_modules/@gradio/sanitize/dist/browser.js
var Ah = kh.getDefaultConfiguration();
Ah.allowElements = (Ah.allowElements ?? []).filter((e) => e !== "style" && e !== "svg:style" && e !== "link" && e !== "meta"), new kh(Ah);
// frontend/node_modules/svelte/src/transition/index.js
var jh = (e) => e;
function Mh(e, { delay: t = 0, duration: n = 400, easing: r = jh } = {}) {
	let i = +getComputedStyle(e).opacity;
	return {
		delay: t,
		duration: n,
		easing: r,
		css: (e) => `opacity: ${e * i}`
	};
}
// frontend/node_modules/@gradio/statustracker/dist/static/ToastContent.svelte
o([
	"touchstart",
	"touchmove",
	"touchend",
	"click",
	"keydown"
]);
// frontend/node_modules/@gradio/statustracker/dist/static/StreamingBar.svelte
var Nh = s("<div class=\"streaming-bar svelte-xj6qzf\"></div>");
function Ph(e, n) {
	var r = y(), i = B(r), o = (e) => {
		var r = Nh();
		let i;
		N(() => i = Se(r, "", i, { "animation-duration": `${n.time_limit ?? ""}s` })), t(e, r);
	};
	a(i, (e) => {
		n.time_limit && e(o);
	}), t(e, r);
}
// frontend/node_modules/@gradio/file/dist/shared/utils.js
var Fh = (e) => {
	let t = [
		"B",
		"KB",
		"MB",
		"GB",
		"PB"
	], n = 0;
	for (; e > 1024;) e /= 1024, n++;
	let r = t[n];
	return e.toFixed(1) + "&nbsp;" + r;
}, Ih = s("<span class=\"drag-handle svelte-87ui99\">⋮⋮</span>"), Lh = s("<!>&nbsp;&#8675;", 1), Rh = s("<td class=\"svelte-87ui99\"><button class=\"label-clear-button svelte-87ui99\" aria-label=\"Remove this file\">×</button></td>"), zh = s("<tr><td class=\"filename svelte-87ui99\"><!> <span class=\"stem svelte-87ui99\"> </span> <span class=\"ext svelte-87ui99\"> </span></td><td class=\"download svelte-87ui99\"><!></td><!></tr>"), Bh = s("<div class=\"file-preview-holder svelte-87ui99\"><table class=\"file-preview svelte-87ui99\"><tbody class=\"svelte-87ui99\"></tbody></table></div>");
function Vh(e, n) {
	P(n, !0);
	let r = z(n, "value", 7), i = z(n, "selectable", 3, !1), o = z(n, "height", 3, void 0), s = z(n, "allow_reordering", 3, !1), c = A(null), p = A(null);
	function m(e, t) {
		V(c, t, !0), e.dataTransfer && (e.dataTransfer.effectAllowed = "move", e.dataTransfer.setData("text/plain", t.toString()));
	}
	function h(e, t) {
		if (e.preventDefault(), t === S(x).length - 1) {
			let n = e.currentTarget.getBoundingClientRect(), r = n.top + n.height / 2;
			V(p, e.clientY > r ? S(x).length : t, !0);
		} else V(p, t, !0);
		e.dataTransfer && (e.dataTransfer.dropEffect = "move");
	}
	function _(e) {
		e.dataTransfer?.dropEffect && e.dataTransfer.dropEffect !== "none" || (V(c, null), V(p, null));
	}
	function v(e, t) {
		if (e.preventDefault(), S(c) === null || S(c) === t) return;
		let i = Array.isArray(r()) ? [...r()] : [r()], [a] = i.splice(S(c), 1);
		i.splice(S(p) === S(x).length ? S(x).length : t, 0, a);
		let o = Array.isArray(r()) ? i : i[0];
		n.onchange === null || n.onchange === void 0 || n.onchange(o), V(c, null), V(p, null);
	}
	function y(e) {
		let t = e.lastIndexOf(".");
		return t === -1 ? [e, ""] : [e.slice(0, t), e.slice(t)];
	}
	let x = L(() => (Array.isArray(r()) ? r() : [r()]).map((e) => {
		let [t, n] = y(e.orig_name ?? "");
		return Object.assign(Object.assign({}, e), {
			filename_stem: t,
			filename_ext: n
		});
	}));
	function C(e, t) {
		let r = e.currentTarget;
		(e.target === r || r && r.firstElementChild && e.composedPath().includes(r.firstElementChild)) && (n.onselect === null || n.onselect === void 0 || n.onselect({
			value: S(x)[t].orig_name,
			index: t
		}));
	}
	function w(e) {
		let t = Array.isArray(r()) ? [...r()] : [r()], i = t.splice(e, 1), a = Array.isArray(r()) ? t : t[0];
		r(a), n.ondelete === null || n.ondelete === void 0 || n.ondelete(i[0]), n.onchange === null || n.onchange === void 0 || n.onchange(a);
	}
	function T(e) {
		n.ondownload === null || n.ondownload === void 0 || n.ondownload(e);
	}
	let E = typeof window < "u";
	var O = Bh();
	let k;
	var j = R(O), ee = R(j);
	f(ee, 23, () => S(x), (e, t) => (e.url ?? "") + "::" + t, (e, r, o) => {
		var f = zh();
		let y;
		var O = R(f), k = R(O), A = (e) => {
			var n = Ih();
			t(e, n);
		};
		a(k, (e) => {
			s() && S(x).length > 1 && e(A);
		});
		var j = D(k, 2), M = I(j, !0), ee = D(j, 2), P = I(ee, !0);
		F(O);
		var te = D(O), ne = R(te), ie = (e) => {
			{
				let n = L(() => E && window.__is_colab__ ? null : S(r).orig_name);
				Me(e, {
					get href() {
						return S(r).url;
					},
					onclick: () => T(S(r)),
					get download() {
						return S(n);
					},
					children: (e, n) => {
						var i = Lh(), a = B(i);
						d(a, () => S(r).size == null ? "(size unknown)" : Fh(S(r).size)), re(), t(e, i);
					},
					$$slots: { default: !0 }
				});
			}
		}, ae = (e) => {
			var r = b();
			N((e) => u(r, e), [() => n.i18n("file.uploading")]), t(e, r);
		};
		a(ne, (e) => {
			S(r).url ? e(ie) : e(ae, -1);
		}), F(te);
		var oe = D(te), se = (e) => {
			var n = Rh(), r = I(n);
			l("click", r, () => {
				w(S(o));
			}), l("keydown", r, (e) => {
				e.key === "Enter" && w(S(o));
			}), t(e, n);
		};
		a(oe, (e) => {
			S(x).length > 1 && e(se);
		}), F(f), N(() => {
			y = g(f, 1, "file svelte-87ui99", null, y, {
				selectable: i(),
				dragging: S(c) === S(o),
				"drop-target": S(p) === S(o) || S(o) === S(x).length - 1 && S(p) === S(x).length
			}), be(f, "data-drop-target", S(p) === S(x).length && S(o) === S(x).length - 1 || S(p) === S(o) + 1 ? "after" : "before"), be(f, "draggable", s() && S(x).length > 1), be(O, "aria-label", S(r).orig_name), u(M, S(r).filename_stem), u(P, S(r).filename_ext);
		}), l("click", f, (e) => {
			C(e, S(o));
		}), he("dragstart", f, (e) => m(e, S(o))), he("dragenter", f, (e) => e.preventDefault()), he("dragover", f, (e) => h(e, S(o))), he("drop", f, (e) => v(e, S(o))), he("dragend", f, _), t(e, f);
	}), F(ee), F(j), F(O), N(() => k = Se(O, "", k, { "max-height": o() ? typeof o() == "number" ? o() + "px" : o() : "auto" })), t(e, O), M();
}
o(["click", "keydown"]);
// frontend/node_modules/@gradio/file/dist/shared/FileUpload.svelte
var Hh = s("<!> <!>", 1), Uh = s("<!> <!> <!>", 1);
function Wh(e, n) {
	P(n, !0);
	var r = this && this.__awaiter || function(e, t, n, r) {
		function i(e) {
			return e instanceof n ? e : new n(function(t) {
				t(e);
			});
		}
		return new (n ||= Promise)(function(n, a) {
			function o(e) {
				try {
					c(r.next(e));
				} catch (e) {
					a(e);
				}
			}
			function s(e) {
				try {
					c(r.throw(e));
				} catch (e) {
					a(e);
				}
			}
			function c(e) {
				e.done ? n(e.value) : i(e.value).then(o, s);
			}
			c((r = r.apply(e, t || [])).next());
		});
	};
	let i = z(n, "value", 15), o = z(n, "show_label", 3, !0), s = z(n, "file_count", 3, "single"), c = z(n, "file_types", 3, null), l = z(n, "selectable", 3, !1), u = z(n, "height", 3, void 0), d = z(n, "max_file_size", 3, null), f = z(n, "uploading", 15, !1), p = z(n, "allow_reordering", 3, !1), m = z(n, "upload_promise", 15), h = z(n, "buttons", 3, null), g = z(n, "on_custom_button_click", 3, null), _ = z(n, "disable_click", 3, !1), v = z(n, "aria_label", 3, void 0);
	function b(e) {
		return r(this, void 0, void 0, function* () {
			Array.isArray(i()) ? i([...i(), ...Array.isArray(e) ? e : [e]]) : i() ? i([i(), ...Array.isArray(e) ? e : [e]]) : i(e), yield x(), n.onchange === null || n.onchange === void 0 || n.onchange(i()), n.onupload === null || n.onupload === void 0 || n.onupload(i());
		});
	}
	function C() {
		i(null), n.onchange === null || n.onchange === void 0 || n.onchange(null), n.onclear === null || n.onclear === void 0 || n.onclear();
	}
	let w = A(!1);
	var E = Uh(), O = B(E), k = (e) => {
		cn(e, {
			get buttons() {
				return h();
			},
			get on_custom_button_click() {
				return g();
			}
		});
	};
	a(O, (e) => {
		o() && h() && h().length > 0 && e(k);
	});
	var j = D(O, 2);
	{
		let e = L(() => !i()), t = L(() => n.label || "File");
		ke(j, {
			get show_label() {
				return o();
			},
			get Icon() {
				return et;
			},
			get float() {
				return S(e);
			},
			get label() {
				return S(t);
			}
		});
	}
	var N = D(j, 2), ee = (e) => {
		var r = Hh(), o = B(r);
		{
			let e = L(() => h() || []);
			cn(o, {
				get buttons() {
					return S(e);
				},
				get on_custom_button_click() {
					return g();
				},
				children: (e, r) => {
					var o = Hh(), l = B(o), u = (e) => {
						{
							let t = L(() => n.i18n("common.upload"));
							Fe(e, {
								get Icon() {
									return vt;
								},
								get label() {
									return S(t);
								},
								children: (e, t) => {
									xn(e, {
										icon_upload: !0,
										onload: b,
										get filetype() {
											return c();
										},
										get file_count() {
											return s();
										},
										get max_file_size() {
											return d();
										},
										get root() {
											return n.root;
										},
										get onerror() {
											return n.onerror;
										},
										get stream_handler() {
											return n.stream_handler;
										},
										get upload() {
											return n.upload;
										},
										get upload_promise() {
											return m();
										},
										set upload_promise(e) {
											m(e);
										},
										get dragging() {
											return S(w);
										},
										set dragging(e) {
											V(w, e, !0);
										},
										get uploading() {
											return f();
										},
										set uploading(e) {
											f(e);
										}
									});
								},
								$$slots: { default: !0 }
							});
						}
					}, p = L(() => !(s() === "single" && (Array.isArray(i()) ? i().length > 0 : i() !== null)));
					a(l, (e) => {
						S(p) && e(u);
					});
					var h = D(l, 2);
					{
						let e = L(() => n.i18n("common.clear"));
						Fe(h, {
							get Icon() {
								return He;
							},
							get label() {
								return S(e);
							},
							onclick: (e) => {
								e.stopPropagation(), C();
							}
						});
					}
					t(e, o);
				},
				$$slots: { default: !0 }
			});
		}
		Vh(D(o, 2), {
			get i18n() {
				return n.i18n;
			},
			get onselect() {
				return n.onselect;
			},
			get selectable() {
				return l();
			},
			get value() {
				return i();
			},
			get height() {
				return u();
			},
			get onchange() {
				return n.onchange;
			},
			get ondelete() {
				return n.ondelete;
			},
			get allow_reordering() {
				return p();
			}
		}), t(e, r);
	}, te = L(() => i() && (!Array.isArray(i()) || i().length > 0)), F = (e) => {
		xn(e, {
			onload: b,
			get filetype() {
				return c();
			},
			get file_count() {
				return s();
			},
			get max_file_size() {
				return d();
			},
			get root() {
				return n.root;
			},
			get onerror() {
				return n.onerror;
			},
			get stream_handler() {
				return n.stream_handler;
			},
			get upload() {
				return n.upload;
			},
			get height() {
				return u();
			},
			get disable_click() {
				return _();
			},
			get aria_label() {
				return v();
			},
			get upload_promise() {
				return m();
			},
			set upload_promise(e) {
				m(e);
			},
			get dragging() {
				return S(w);
			},
			set dragging(e) {
				V(w, e, !0);
			},
			get uploading() {
				return f();
			},
			set uploading(e) {
				f(e);
			},
			children: (e, r) => {
				var i = y(), a = B(i);
				ae(a, () => n.children ?? T), t(e, i);
			},
			$$slots: { default: !0 }
		});
	};
	a(N, (e) => {
		S(te) ? e(ee) : e(F, -1);
	}), t(e, E), M();
}
// frontend/node_modules/@gradio/image/dist/shared/WebcamPermissions.svelte
var Gh = s("<button class=\"svelte-9xp153\"><div class=\"wrap svelte-9xp153\"><span class=\"icon-wrap svelte-9xp153\"><!></span> </div></button>");
function Kh(e, n) {
	var r = Gh();
	Se(r, "", {}, { height: "100%" });
	var i = R(r), a = R(i);
	St(R(a), {}), F(a);
	var o = D(a);
	o.nodeValue = " Click to Access Webcam", F(i), F(r), l("click", r, function(...e) {
		n.onclick?.apply(this, e);
	}), t(e, r);
}
o(["click"]);
// frontend/node_modules/@gradio/image/dist/shared/stream_utils.js
function qh() {
	return navigator.mediaDevices.enumerateDevices();
}
async function Jh(e, t) {
	t.srcObject = e, t.muted = !0, await t.play();
}
async function Yh(e, t, n, r) {
	let i = {
		video: r ? {
			deviceId: { exact: r },
			...n?.video
		} : n?.video || {
			width: { ideal: 1920 },
			height: { ideal: 1440 }
		},
		audio: e && (n?.audio ?? !0)
	};
	return navigator.mediaDevices.getUserMedia(i).then((e) => (Jh(e, t), e));
}
function Xh(e) {
	return e.filter((e) => e.kind === "videoinput");
}
// frontend/node_modules/@gradio/image/dist/shared/Webcam.svelte
var Zh = s("<div title=\"grant webcam access\" style=\"height: 100%\"><!></div>"), Qh = s("<div class=\"icon-with-text svelte-1d3tw37\" style=\"width:var(--size-24);\"><div class=\"icon color-primary svelte-1d3tw37\" title=\"spinner\"><!></div> </div>"), $h = s("<div class=\"icon-with-text svelte-1d3tw37\"><div class=\"icon color-primary svelte-1d3tw37\" title=\"stop recording\"><!></div> </div>"), eg = s("<div class=\"icon-with-text svelte-1d3tw37\"><div class=\"icon color-primary svelte-1d3tw37\" title=\"start recording\"><!></div> </div>"), tg = s("<div class=\"icon svelte-1d3tw37\" title=\"capture photo\"><!></div>"), ng = s("<button class=\"device-select-button svelte-1d3tw37\" aria-label=\"select input source\" aria-haspopup=\"listbox\"><span class=\"device-select-icon svelte-1d3tw37\"><!></span></button>"), rg = s("<option class=\"svelte-1d3tw37\"> </option>"), ig = s("<select class=\"select-wrap svelte-1d3tw37\" aria-label=\"select source\"></select>"), ag = s("<div class=\"button-wrap svelte-1d3tw37\"><button><!></button> <!> <!></div>"), og = s("<div class=\"wrap svelte-1d3tw37\"><!>  <video data-testid=\"webcam-video\" playsinline=\"\"></video> <img/> <!></div>", 2);
function sg(e, n) {
	P(n, !0);
	var r = this && this.__awaiter || function(e, t, n, r) {
		function i(e) {
			return e instanceof n ? e : new n(function(t) {
				t(e);
			});
		}
		return new (n ||= Promise)(function(n, a) {
			function o(e) {
				try {
					c(r.next(e));
				} catch (e) {
					a(e);
				}
			}
			function s(e) {
				try {
					c(r.throw(e));
				} catch (e) {
					a(e);
				}
			}
			function c(e) {
				e.done ? n(e.value) : i(e.value).then(o, s);
			}
			c((r = r.apply(e, t || [])).next());
		});
	};
	let o, s = A(fe([])), c = A(null), d, p = z(n, "stream_state", 3, "closed"), h = z(n, "streaming", 3, !1), _ = z(n, "pending", 3, !1), v = z(n, "root", 3, ""), b = z(n, "stream_every", 3, 1), x = z(n, "mode", 3, "image"), C = z(n, "webcam_constraints", 3, null), w = z(n, "value", 3, null), T = z(n, "time_limit", 3, null);
	ue(() => {
		d = document.createElement("canvas"), h() && x() === "image" && window.setInterval(() => {
			o && !_() && j();
		}, b() * 1e3);
	});
	let E = (e) => r(void 0, void 0, void 0, function* () {
		let t = e.target.value;
		yield Yh(n.include_audio, o, C(), t).then((e) => r(void 0, void 0, void 0, function* () {
			re = e, V(c, S(s).find((e) => e.deviceId === t) || null, !0), V(ce, !1);
		}));
	});
	function k() {
		return r(this, void 0, void 0, function* () {
			try {
				Yh(n.include_audio, o, C()).then((e) => r(this, void 0, void 0, function* () {
					V(se, !0), V(s, yield qh(), !0), re = e;
				})).then(() => Xh(S(s))).then((e) => {
					V(s, e, !0);
					let t = re.getTracks().map((e) => e.getSettings()?.deviceId)[0];
					V(c, t && e.find((e) => e.deviceId === t) || S(s)[0], !0);
				}), navigator.mediaDevices && navigator.mediaDevices.getUserMedia || n.onerror === null || n.onerror === void 0 || n.onerror(n.i18n("image.no_webcam_support"));
			} catch (e) {
				if (e instanceof DOMException && e.name == "NotAllowedError") n.onerror === null || n.onerror === void 0 || n.onerror(n.i18n("image.allow_webcam_access"));
				else throw e;
			}
		});
	}
	function j() {
		if ((!h() || h() && S(te)) && o.videoWidth && o.videoHeight) {
			var e = d.getContext("2d");
			if (d.width = o.videoWidth, d.height = o.videoHeight, e.drawImage(o, 0, 0, o.videoWidth, o.videoHeight), n.mirror_webcam && (e.scale(-1, 1), e.drawImage(o, -o.videoWidth, 0)), h() && (!S(te) || p() === "waiting")) return;
			if (h()) {
				let e = d.toDataURL("image/jpeg");
				n.onstream === null || n.onstream === void 0 || n.onstream(e);
				return;
			}
			d.toBlob((e) => {
				h() ? n.onstream === null || n.onstream === void 0 || n.onstream(e) : n.oncapture === null || n.oncapture === void 0 || n.oncapture(e);
			}, `image/${h() ? "jpeg" : "png"}`, .8);
		}
	}
	let te = A(!1), ne = [], re, ie, ae;
	function oe() {
		if (S(te)) {
			ae.stop();
			let e = new Blob(ne, { type: ie }), t = new FileReader();
			t.onload = function(t) {
				return r(this, void 0, void 0, function* () {
					if (t.target) {
						let t = yield un([new File([e], "sample." + ie.substring(6))]), r = ((yield n.upload(t, v()))?.filter(Boolean))[0];
						n.oncapture === null || n.oncapture === void 0 || n.oncapture(r), n.onstop_recording === null || n.onstop_recording === void 0 || n.onstop_recording();
					}
				});
			}, t.readAsDataURL(e);
		} else if (typeof MediaRecorder < "u") {
			n.onstart_recording === null || n.onstart_recording === void 0 || n.onstart_recording(), ne = [];
			for (let e of ["video/webm", "video/mp4"]) if (MediaRecorder.isTypeSupported(e)) {
				ie = e;
				break;
			}
			if (ie === null) {
				console.error("No supported MediaRecorder mimeType");
				return;
			}
			ae = new MediaRecorder(re, { mimeType: ie }), ae.addEventListener("dataavailable", function(e) {
				ne.push(e.data);
			}), ae.start(200);
		}
		V(te, !S(te));
	}
	let se = A(!1);
	function L({ destroy: e } = {}) {
		x() === "image" && h() && V(te, !S(te)), e || (x() === "image" ? j() : oe()), !S(te) && re && (n.onclose_stream === null || n.onclose_stream === void 0 || n.onclose_stream());
	}
	let ce = A(!1);
	function le(e, t) {
		let n = (n) => {
			e && !e.contains(n.target) && !n.defaultPrevented && t(n);
		};
		return document.addEventListener("click", n, !0), { destroy() {
			document.removeEventListener("click", n, !0);
		} };
	}
	function de(e) {
		e.preventDefault(), e.stopPropagation(), V(ce, !1);
	}
	_e(() => {
		typeof window < "u" && (L({ destroy: !0 }), re?.getTracks().forEach((e) => e.stop()));
	});
	var pe = { click_outside: le }, me = og(), he = R(me);
	Ph(he, { get time_limit() {
		return T();
	} });
	var ge = D(he, 2);
	let ve;
	ee(ge, (e) => o = e, () => o);
	var ye = D(ge, 2);
	let Se;
	var H = D(ye, 2), Ce = (e) => {
		var n = Zh();
		Kh(R(n), { onclick: async () => k() }), F(n), i(1, n, () => Mh, () => ({
			delay: 100,
			duration: 200
		})), t(e, n);
	}, we = (e) => {
		var r = ag(), i = R(r);
		let o;
		var d = R(i), _ = (e) => {
			var r = y(), i = B(r), o = (e) => {
				var r = Qh(), i = R(r);
				wt(R(i), {}), F(i);
				var a = D(i);
				F(r), N((e) => u(a, ` ${e ?? ""}`), [() => n.i18n("audio.waiting")]), t(e, r);
			}, s = (e) => {
				var r = $h(), i = R(r);
				mt(R(i), {}), F(i);
				var a = D(i);
				F(r), N((e) => u(a, ` ${e ?? ""}`), [() => n.i18n("audio.stop")]), t(e, r);
			}, c = (e) => {
				var r = eg(), i = R(r);
				Be(R(i), {}), F(i);
				var a = D(i);
				F(r), N((e) => u(a, ` ${e ?? ""}`), [() => n.i18n("audio.record")]), t(e, r);
			};
			a(i, (e) => {
				h() && p() === "waiting" ? e(o) : h() && p() === "open" || !h() && S(te) ? e(s, 1) : e(c, -1);
			}), t(e, r);
		}, v = (e) => {
			var n = tg();
			ze(R(n), {}), F(n), t(e, n);
		};
		a(d, (e) => {
			x() === "video" || h() ? e(_) : e(v, -1);
		}), F(i);
		var b = D(i, 2), C = (e) => {
			var n = ng(), r = R(n);
			Xe(R(r), {}), F(r), F(n), N(() => be(n, "aria-expanded", S(ce))), l("click", n, () => V(ce, !0)), t(e, n);
		};
		a(b, (e) => {
			!S(te) && S(s).length > 1 && e(C);
		});
		var w = D(b, 2), T = (e) => {
			var n = ig();
			f(n, 21, () => S(s), m, (e, n) => {
				var r = rg(), i = I(r, !0), a = {};
				N(() => {
					O(r, S(c).deviceId === S(n).deviceId), u(i, S(n).label), a !== (a = S(n).deviceId) && (r.value = (r.__value = a) ?? "");
				}), t(e, r);
			}), F(n), xe(n, (e, t) => le?.(e, t), () => de), l("change", n, E), t(e, n);
		};
		a(w, (e) => {
			S(ce) && S(c) && e(T);
		}), F(r), N(() => {
			o = g(i, 1, "capture-button svelte-1d3tw37", null, o, { "photo-capture": x() === "image" && !h() }), be(i, "aria-label", x() === "image" ? "capture photo" : "start recording");
		}), l("click", i, () => L()), t(e, r);
	};
	return a(H, (e) => {
		S(se) ? e(we, -1) : e(Ce);
	}), F(me), N(() => {
		ve = g(ge, 1, "svelte-1d3tw37", null, ve, {
			flip: n.mirror_webcam,
			hide: !S(se) || S(se) && !!w()
		}), be(ye, "src", w()?.url), Se = g(ye, 1, "svelte-1d3tw37", null, Se, { hide: !S(se) || S(se) && !w() });
	}), t(e, me), M(pe);
}
// frontend/node_modules/@gradio/image/dist/shared/ImageUploader.svelte
o(["click", "change"]), o(["click"]);
// frontend/Example.svelte
var cg = s("<span class=\"caption svelte-s3apn9\"> </span>"), lg = s("<div class=\"image-container svelte-s3apn9\"><img class=\"svelte-s3apn9\"/> <!></div>"), ug = s("<div class=\"image-container svelte-s3apn9\"><video preload=\"metadata\" class=\"svelte-s3apn9\"></video> <!></div>", 2), dg = s("<div class=\"more-indicator svelte-s3apn9\">…</div>"), fg = s("<div class=\"images-wrapper svelte-s3apn9\"><!> <!></div>"), pg = s("<div><!></div>");
function mg(e, n) {
	P(n, !0);
	let r = z(n, "selected", 3, !1);
	var i = pg();
	let o;
	var s = R(i), c = (e) => {
		var r = fg(), i = R(r);
		f(i, 17, () => n.value.slice(0, 3), m, (e, n) => {
			var r = y(), i = B(r), o = (e) => {
				var r = lg(), i = R(r), o = D(i, 2), s = (e) => {
					var r = cg(), i = I(r, !0);
					N(() => u(i, S(n).caption)), t(e, r);
				};
				a(o, (e) => {
					S(n).caption && e(s);
				}), F(r), N(() => {
					be(i, "src", S(n).image.url), be(i, "alt", S(n).caption || "");
				}), t(e, r);
			}, s = (e) => {
				var r = ug(), i = R(r);
				i.controls = !1, i.muted = !0;
				var o = D(i, 2), s = (e) => {
					var r = cg(), i = I(r, !0);
					N(() => u(i, S(n).caption)), t(e, r);
				};
				a(o, (e) => {
					S(n).caption && e(s);
				}), F(r), N(() => be(i, "src", S(n).video.url)), t(e, r);
			};
			a(i, (e) => {
				"image" in S(n) && S(n).image ? e(o) : "video" in S(n) && S(n).video && e(s, 1);
			}), t(e, r);
		});
		var o = D(i, 2), s = (e) => {
			var n = dg();
			t(e, n);
		};
		a(o, (e) => {
			n.value.length > 3 && e(s);
		}), F(r), t(e, r);
	};
	a(s, (e) => {
		n.value && n.value.length > 0 && e(c);
	}), F(i), N(() => o = g(i, 1, "container svelte-s3apn9", null, o, {
		table: n.type === "table",
		gallery: n.type === "gallery",
		selected: r()
	})), t(e, i), M();
}
// frontend/Index.svelte
var hg = /* @__PURE__ */ new Set([
	"$$slots",
	"$$events",
	"$$legacy"
]), gg = s("<div><!></div> <!> <!>", 1), _g = s("<!> <!>", 1);
function vg(e, r) {
	P(r, !0);
	var i = this && this.__awaiter || function(e, t, n, r) {
		function i(e) {
			return e instanceof n ? e : new n(function(t) {
				t(e);
			});
		}
		return new (n ||= Promise)(function(n, a) {
			function o(e) {
				try {
					c(r.next(e));
				} catch (e) {
					a(e);
				}
			}
			function s(e) {
				try {
					c(r.throw(e));
				} catch (e) {
					a(e);
				}
			}
			function c(e) {
				e.done ? n(e.value) : i(e.value).then(o, s);
			}
			c((r = r.apply(e, t || [])).next());
		});
	};
	let o = A(void 0);
	class s extends It {
		get_data() {
			let e = Object.create(null, { get_data: { get: () => super.get_data } });
			return i(this, void 0, void 0, function* () {
				return S(o) && (yield S(o), yield x()), yield e.get_data.call(this);
			});
		}
	}
	let c = new s(ie(r, hg), {
		selected_index: null,
		file_types: ["image", "video"]
	}), u = A(!1);
	function d(e) {
		if (!c.props.value) return;
		let { index: t } = e;
		c.dispatch("delete", e), c.props.value = c.props.value.filter((e, n) => n !== t), c.dispatch("change", c.props.value);
	}
	function f(e) {
		return i(this, void 0, void 0, function* () {
			return (yield Promise.all(e.map((e) => i(this, void 0, void 0, function* () {
				if (e.path?.toLowerCase().endsWith(".svg") && e.url) {
					let t = yield (yield fetch(e.url)).text();
					return Object.assign(Object.assign({}, e), { url: `data:image/svg+xml,${encodeURIComponent(t)}` });
				}
				return e;
			})))).map((e) => e.mime_type?.includes("video") ? {
				video: e,
				caption: null
			} : {
				image: e,
				caption: null
			});
		});
	}
	let p, m = A(fe(c.props.sources ? c.props.sources[0] : "upload")), h = L(() => c.props.value === null || c.props.value.length === 0), _ = L(() => c.props.file_types?.includes("video") && c.props.sources.includes("webcam") ? c.props.sources.concat(["webcam-video"]) : c.props.sources);
	ve(() => {
		S(m) && S(_).includes(S(m)) || V(m, S(_)[0], !0);
	});
	function v() {
		return i(this, void 0, void 0, function* () {
			navigator.clipboard.read().then((e) => i(this, void 0, void 0, function* () {
				var t;
				let n = null;
				for (let t = 0; t < e.length; t++) {
					let r = e[t].types.find((e) => (c.props.file_types || ["image"]).some((t) => e.startsWith(t + "/")));
					if (r) {
						let i = yield e[t].getType(r);
						n = new File([i], `clipboard.${r.replace("image/", "")}`);
						break;
					}
				}
				if (n) {
					let e = yield f(yield am(n, (e) => c.shared.client.upload(e, c.shared.root), "clipboard_upload"));
					(t = c.props.value) == null || t.push(...e), c.dispatch("change", c.props.value), V(m, null);
				} else c.dispatch("warning", "No image or video found in clipboard");
			}));
		});
	}
	function b(e) {
		return i(this, void 0, void 0, function* () {
			e === "clipboard" && (yield v());
		});
	}
	function C(e) {
		return i(this, void 0, void 0, function* () {
			yield x(), e === "clipboard" ? yield v() : (V(m, e, !0), V(h, !0));
		});
	}
	{
		let r = L(() => c.props.height || void 0);
		De(e, {
			get visible() {
				return c.shared.visible;
			},
			variant: "solid",
			padding: !1,
			get elem_id() {
				return c.shared.elem_id;
			},
			get elem_classes() {
				return c.shared.elem_classes;
			},
			get container() {
				return c.shared.container;
			},
			get scale() {
				return c.shared.scale;
			},
			get min_width() {
				return c.shared.min_width;
			},
			allow_overflow: !1,
			get height() {
				return S(r);
			},
			get fullscreen() {
				return S(u);
			},
			set fullscreen(e) {
				V(u, e, !0);
			},
			children: (e, r) => {
				var i = _g(), s = B(i);
				Um(s, E({
					get autoscroll() {
						return c.shared.autoscroll;
					},
					get i18n() {
						return c.i18n;
					}
				}, () => c.shared.loading_status, { on_clear_status: () => c.dispatch("clear_status", c.shared.loading_status) }));
				var x = D(s, 2), w = (e) => {
					var r = gg(), i = B(r), s = R(i);
					{
						let e = L(() => !S(_).includes("upload") || S(m) === "clipboard"), n = L(() => S(m) === "clipboard" ? c.i18n("upload_text.paste_clipboard") : void 0);
						ee(Wh(s, {
							get disable_click() {
								return S(e);
							},
							get aria_label() {
								return S(n);
							},
							value: null,
							get root() {
								return c.shared.root;
							},
							get label() {
								return c.shared.label;
							},
							get max_file_size() {
								return c.shared.max_file_size;
							},
							file_count: "multiple",
							get file_types() {
								return c.props.file_types;
							},
							get i18n() {
								return c.i18n;
							},
							upload: (...e) => c.shared.client.upload(...e),
							stream_handler: (...e) => c.shared.client.stream(...e),
							onupload: async (e) => {
								let t = Array.isArray(e) ? e : [e];
								c.props.value = await f(t), V(m, null), c.dispatch("upload", c.props.value), c.dispatch("change", c.props.value);
							},
							onerror: (e) => {
								c.shared.loading_status = c.shared.loading_status || {}, c.shared.loading_status.status = "error", c.dispatch("error", e);
							},
							get upload_promise() {
								return S(o);
							},
							set upload_promise(e) {
								V(o, e, !0);
							},
							children: (e, n) => {
								var r = y(), i = B(r), o = (e) => {
									Yt(e, {
										get i18n() {
											return c.i18n;
										},
										type: "clipboard",
										mode: "short"
									});
								}, s = (e) => {
									Yt(e, {
										get i18n() {
											return c.i18n;
										},
										type: "gallery"
									});
								};
								a(i, (e) => {
									S(m) === "clipboard" ? e(o) : e(s, -1);
								}), t(e, r);
							},
							$$slots: { default: !0 }
						}), (e) => p = e, () => p);
					}
					F(i);
					var u = D(i, 2), d = (e) => {
						sg(e, {
							get root() {
								return c.shared.root;
							},
							value: null,
							oncapture: async (e) => {
								if (!(e instanceof Blob)) return;
								let t = await f(await am(e, (e) => c.shared.client.upload(e, c.shared.root), "webcam_upload"));
								c.props.value?.push(...t), V(m, null), c.dispatch("change", c.props.value);
							},
							mirror_webcam: !0,
							streaming: !1,
							mode: "image",
							include_audio: !1,
							get i18n() {
								return c.i18n;
							},
							upload: (...e) => c.shared.client.upload(...e)
						});
					}, h = (e) => {
						sg(e, {
							get root() {
								return c.shared.root;
							},
							value: null,
							oncapture: async (e) => {
								if (!e) return;
								let t = { ...e };
								t.mime_type = "video/webm";
								let n = await f([t]);
								c.props.value?.push(...n), V(m, null), c.dispatch("change", c.props.value);
							},
							mirror_webcam: !0,
							streaming: !1,
							mode: "video",
							include_audio: !1,
							get i18n() {
								return c.i18n;
							},
							upload: (...e) => c.shared.client.upload(...e)
						});
					};
					a(u, (e) => {
						S(m) === "webcam" ? e(d) : S(m) === "webcam-video" && e(h, 1);
					});
					var x = D(u, 2), C = (e) => {
						nn(e, {
							get sources() {
								return S(_);
							},
							handle_clear: () => c.dispatch("clear"),
							handle_select: (e) => b(e),
							get active_source() {
								return S(m);
							},
							set active_source(e) {
								V(m, e, !0);
							}
						});
					}, w = L(() => S(_).length > 1 || S(_).includes("clipboard"));
					a(x, (e) => {
						S(w) && e(C);
					}), N((e) => g(i, 1, e, "svelte-r41nsf"), [() => n(!c.props.value || S(m) && S(m).includes("webcam") ? "hidden-upload-input" : "upload-wrapper")]), l("click", i, function(...e) {
						(S(m) === "clipboard" ? v : void 0)?.apply(this, e);
					}), t(e, r);
				}, T = (e) => {
					{
						let t = L(() => c.props.buttons.some((e) => typeof e == "string" && e === "share")), n = L(() => c.props.buttons.some((e) => typeof e == "string" && e === "download")), r = L(() => c.props.buttons.some((e) => typeof e == "string" && e === "download_all")), i = L(() => c.props.buttons.some((e) => typeof e == "string" && e === "fullscreen"));
						bm(e, {
							onchange: () => c.dispatch("change"),
							onclear: () => {
								V(m, S(_)[0], !0), c.dispatch("change");
							},
							onselect: (e) => c.dispatch("select", e),
							onshare: (e) => c.dispatch("share", e.detail),
							onerror: (e) => c.dispatch("error", e.detail),
							onpreview_open: () => {
								c.dispatch("preview_open");
							},
							onpreview_close: () => c.dispatch("preview_close"),
							onfullscreen: ({ detail: e }) => {
								V(u, e, !0);
							},
							ondelete: d,
							onupload: async (e) => {
								let t = await f(Array.isArray(e) ? e : [e]);
								c.props.value = c.props.value ? [...c.props.value, ...t] : t, c.dispatch("upload", t), c.dispatch("change", c.props.value);
							},
							get sources() {
								return S(_);
							},
							onsource_change: (e) => C(e),
							get label() {
								return c.shared.label;
							},
							get show_label() {
								return c.shared.show_label;
							},
							get columns() {
								return c.props.columns;
							},
							get rows() {
								return c.props.rows;
							},
							get height() {
								return c.props.height;
							},
							get preview() {
								return c.props.preview;
							},
							get object_fit() {
								return c.props.object_fit;
							},
							get interactive() {
								return c.shared.interactive;
							},
							get allow_preview() {
								return c.props.allow_preview;
							},
							get show_share_button() {
								return S(t);
							},
							get show_download_button() {
								return S(n);
							},
							get show_download_all_button() {
								return S(r);
							},
							get fit_columns() {
								return c.props.fit_columns;
							},
							get i18n() {
								return c.i18n;
							},
							_fetch: (...e) => c.shared.client.fetch(...e),
							get show_fullscreen_button() {
								return S(i);
							},
							get buttons() {
								return c.props.buttons;
							},
							oncustom_button_click: (e) => {
								c.dispatch("custom_button_click", { id: e });
							},
							get fullscreen() {
								return S(u);
							},
							get root() {
								return c.shared.root;
							},
							get file_types() {
								return c.props.file_types;
							},
							get max_file_size() {
								return c.shared.max_file_size;
							},
							upload: (...e) => c.shared.client.upload(...e),
							stream_handler: (...e) => c.shared.client.stream(...e),
							get selected_index() {
								return c.props.selected_index;
							},
							set selected_index(e) {
								c.props.selected_index = e;
							},
							get value() {
								return c.props.value;
							},
							set value(e) {
								c.props.value = e;
							}
						});
					}
				};
				a(x, (e) => {
					c.shared.interactive && S(h) ? e(w) : e(T, -1);
				}), t(e, i);
			},
			$$slots: { default: !0 }
		});
	}
	M();
}
o(["click"]);
export { mg as BaseExample, bm as BaseGallery, vg as default };
