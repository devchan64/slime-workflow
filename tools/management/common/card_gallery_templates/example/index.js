import { C as e, S as t, _ as n, a as r, d as i, f as a, g as o, h as s, l as c, m as l, n as u, o as d, p as f, r as p, s as m, t as h, v as g, x as _, y as v } from "./index-client-DliZyeTQ.js";
// frontend/Example.svelte
var y = f("<span class=\"caption svelte-s3apn9\"> </span>"), b = f("<div class=\"image-container svelte-s3apn9\"><img class=\"svelte-s3apn9\"/> <!></div>"), x = f("<div class=\"image-container svelte-s3apn9\"><video preload=\"metadata\" class=\"svelte-s3apn9\"></video> <!></div>", 2), S = f("<div class=\"more-indicator svelte-s3apn9\">…</div>"), C = f("<div class=\"images-wrapper svelte-s3apn9\"><!> <!></div>"), w = f("<div><!></div>");
function T(f, T) {
	t(T, !0);
	let E = h(T, "selected", 3, !1);
	var D = w();
	let O;
	var k = o(D), A = (t) => {
		var f = C(), p = o(f);
		r(p, 17, () => T.value.slice(0, 3), d, (t, r) => {
			var d = a(), f = n(d), p = (t) => {
				var n = b(), a = o(n), d = v(a, 2), f = (e) => {
					var t = y(), n = g(t, !0);
					s(() => c(n, l(r).caption)), i(e, t);
				};
				m(d, (e) => {
					l(r).caption && e(f);
				}), e(n), s(() => {
					u(a, "src", l(r).image.url), u(a, "alt", l(r).caption || "");
				}), i(t, n);
			}, h = (t) => {
				var n = x(), a = o(n);
				a.controls = !1, a.muted = !0;
				var d = v(a, 2), f = (e) => {
					var t = y(), n = g(t, !0);
					s(() => c(n, l(r).caption)), i(e, t);
				};
				m(d, (e) => {
					l(r).caption && e(f);
				}), e(n), s(() => u(a, "src", l(r).video.url)), i(t, n);
			};
			m(f, (e) => {
				"image" in l(r) && l(r).image ? e(p) : "video" in l(r) && l(r).video && e(h, 1);
			}), i(t, d);
		});
		var h = v(p, 2), _ = (e) => {
			var t = S();
			i(e, t);
		};
		m(h, (e) => {
			T.value.length > 3 && e(_);
		}), e(f), i(t, f);
	};
	m(k, (e) => {
		T.value && T.value.length > 0 && e(A);
	}), e(D), s(() => O = p(D, 1, "container svelte-s3apn9", null, O, {
		table: T.type === "table",
		gallery: T.type === "gallery",
		selected: E()
	})), i(f, D), _();
}
export { T as default };
