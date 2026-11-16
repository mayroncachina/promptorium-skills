// dc_lite.js: runtime mínimo para renderizar artboards .dc.html do Claude Design fora do editor.
// Substitui o ./support.js do Claude Design (que só existe dentro do editor) para que o layout
// possa ser auditado no Playwright. Cobre o que o formato documenta: <helmet>, buracos {{ caminho }},
// atributos com buraco (valor bruto, string interpolada, eventos onClick etc.), <sc-if>, <sc-for>,
// <dc-import> (arquivos irmãos via window.__DC_SRC), props com os defaults de data-props e a classe
// Component extends DCLogic com state/setState/forceUpdate e o ciclo de vida do React.
// Não é o runtime oficial: diferenças finas de renderização são possíveis e o relatório avisa isso.
(function () {
  "use strict";
  var SRC = window.__DC_SRC || {};
  var LOG = (window.__DC_LOG = []);
  var HOLE = /\{\{\s*([^{}]+?)\s*\}\}/g;
  var WHOLE = /^\s*\{\{\s*([^{}]+?)\s*\}\}\s*$/;
  var EVT = { doubleclick: "dblclick" };
  function erro(onde, e) {
    var msg = "[dc-lite] " + onde + ": " + (e && e.message ? e.message : e);
    LOG.push(msg);
    try { console.error(msg); } catch (_) {}
  }

  function DCLogic(props) { this.props = props || {}; this.state = {}; }
  DCLogic.prototype.setState = function (parcial, cb) {
    var antes = this.state;
    var novo = typeof parcial === "function" ? parcial(this.state, this.props) : parcial;
    this.state = Object.assign({}, this.state, novo || {});
    if (this.__host) this.__host.agendar(antes, cb);
  };
  DCLogic.prototype.forceUpdate = function (cb) { if (this.__host) this.__host.agendar(this.state, cb); };
  var React = { createRef: function () { return { current: null }; }, Fragment: "fragment" };
  window.DCLogic = DCLogic;

  function procura(caminho, escopo) {
    var p = caminho.trim();
    if (p === "true") return true;
    if (p === "false") return false;
    if (p === "null") return null;
    if (p === "undefined") return undefined;
    if (/^-?\d+(\.\d+)?$/.test(p)) return Number(p);
    var m = p.match(/^(['"])(.*)\1$/);
    if (m) return m[2];
    var v = escopo;
    var partes = p.split(".");
    for (var i = 0; i < partes.length; i++) {
      if (v == null) return undefined;
      v = v[partes[i]];
    }
    return v;
  }
  function texto(v) { return v == null || v === false ? "" : String(v); }
  function interpola(s, escopo) { return s.replace(HOLE, function (_, p) { return texto(procura(p, escopo)); }); }
  function camelo(s) { return s.replace(/-([a-z])/g, function (_, c) { return c.toUpperCase(); }); }

  function compila(script, arquivo) {
    if (!script) return null;
    try {
      return new Function("DCLogic", "React", script.textContent +
        "\n;return typeof Component !== 'undefined' ? Component : null;")(DCLogic, React);
    } catch (e) { erro("logic de " + arquivo, e); return null; }
  }
  function defaults(script) {
    var out = {};
    if (!script || !script.getAttribute("data-props")) return out;
    try {
      var d = JSON.parse(script.getAttribute("data-props"));
      Object.keys(d).forEach(function (k) {
        if (k.charAt(0) !== "$" && d[k] && Object.prototype.hasOwnProperty.call(d[k], "default")) out[k] = d[k]["default"];
      });
    } catch (e) { erro("data-props", e); }
    return out;
  }
  function resolve(base, nome) {
    var dir = base.indexOf("/") >= 0 ? base.slice(0, base.lastIndexOf("/") + 1) : "";
    var alvo = nome.charAt(0) === "/" ? nome.slice(1) : dir + nome;
    var partes = [];
    alvo.split("/").forEach(function (x) { if (x === "..") partes.pop(); else if (x && x !== ".") partes.push(x); });
    return partes.join("/");
  }

  var helmetsFeitos = {};
  function helmet(no, arquivo, doDocumento) {
    if (helmetsFeitos[arquivo]) return;
    helmetsFeitos[arquivo] = true;
    Array.prototype.slice.call(no.childNodes).forEach(function (c) {
      if (c.nodeType !== 1) return;
      document.head.appendChild(doDocumento ? c : document.importNode(c, true));
    });
  }

  function Host(raiz, script, arquivo, props) {
    this.arquivo = arquivo;
    this.tpl = raiz;
    var Comp = compila(script, arquivo) || function (p) { DCLogic.call(this, p); };
    if (!(Comp.prototype instanceof DCLogic) && Comp.prototype.setState === undefined) {
      Comp.prototype = Object.create(DCLogic.prototype);
    }
    var p = Object.assign({}, defaults(script), props || {});
    try { this.inst = new Comp(p); } catch (e) { erro("constructor de " + arquivo, e); this.inst = new DCLogic(p); }
    if (!this.inst.props) this.inst.props = p;
    if (!this.inst.state) this.inst.state = {};
    this.inst.__host = this;
    this.filhos = [];
    this.no = document.createElement("div");
    this.no.setAttribute("data-dc-root", arquivo);
    this.no.style.display = "contents";
    this.pendente = false;
    this.cbs = [];
  }
  Host.prototype.render = function () {
    var vals = {};
    try { vals = (this.inst.renderVals ? this.inst.renderVals() : {}) || {}; }
    catch (e) { erro("renderVals de " + this.arquivo, e); }
    var escopo = Object.assign(Object.create(this.inst.props || {}), vals);
    var frag = document.createDocumentFragment();
    this.idxFilho = 0;
    filhos(this.tpl, frag, escopo, this);
    this.no.replaceChildren(frag);
  };
  Host.prototype.montar = function () {
    this.render();
    try { if (this.inst.componentDidMount) this.inst.componentDidMount(); } catch (e) { erro("componentDidMount de " + this.arquivo, e); }
  };
  Host.prototype.agendar = function (estadoAntes, cb) {
    var self = this;
    if (cb) this.cbs.push(cb);
    if (this.pendente) return;
    this.pendente = true;
    this.antes = estadoAntes;
    Promise.resolve().then(function () {
      self.pendente = false;
      var props = self.inst.props;
      self.render();
      try { if (self.inst.componentDidUpdate) self.inst.componentDidUpdate(props, self.antes); } catch (e) { erro("componentDidUpdate de " + self.arquivo, e); }
      var cbs = self.cbs; self.cbs = [];
      cbs.forEach(function (f) { try { f(); } catch (e) { erro("callback de setState", e); } });
    });
  };

  function atributo(no, nome, escopo) {
    var v = no.getAttribute(nome);
    if (v == null) return undefined;
    var w = v.match(WHOLE);
    return w ? procura(w[1], escopo) : interpola(v, escopo);
  }
  function filhos(pai, out, escopo, host) {
    var lista = pai.childNodes;
    for (var i = 0; i < lista.length; i++) no(lista[i], out, escopo, host);
  }
  function no(n, out, escopo, host) {
    if (n.nodeType === 3) {
      var t = n.nodeValue;
      out.appendChild(document.createTextNode(t.indexOf("{{") >= 0 ? interpola(t, escopo) : t));
      return;
    }
    if (n.nodeType !== 1) return;
    var tag = n.localName;
    if (tag === "helmet") { helmet(n, host.arquivo, n.ownerDocument === document); return; }
    if (tag === "script") return;
    if (tag === "sc-if") {
      if (atributo(n, "value", escopo)) filhos(n, out, escopo, host);
      return;
    }
    if (tag === "sc-for") {
      var itens = atributo(n, "list", escopo) || [];
      var como = n.getAttribute("as") || "item";
      Array.prototype.forEach.call(itens, function (item, i) {
        var s = Object.create(escopo);
        s[como] = item;
        s.$index = i;
        filhos(n, out, s, host);
      });
      return;
    }
    if (tag === "dc-import") { importa(n, out, escopo, host); return; }
    var el = n.cloneNode(false);
    Array.prototype.slice.call(el.attributes).forEach(function (a) {
      var nome = a.name, v = a.value;
      if (nome.indexOf("hint-") === 0) { el.removeAttribute(nome); return; }
      if (v.indexOf("{{") < 0) return;
      var w = v.match(WHOLE);
      if (!w) { el.setAttribute(nome, interpola(v, escopo)); return; }
      var val = procura(w[1], escopo);
      if (/^on[a-z]+$/.test(nome)) {
        el.removeAttribute(nome);
        if (typeof val === "function") {
          var ev = EVT[nome.slice(2)] || nome.slice(2);
          if (ev === "change" && ((el.localName === "input" && !/^(checkbox|radio)$/i.test(el.type)) || el.localName === "textarea")) ev = "input";
          el.addEventListener(ev, val);
        }
        return;
      }
      if (nome === "ref") {
        el.removeAttribute(nome);
        if (typeof val === "function") val(el); else if (val && typeof val === "object") val.current = el;
        return;
      }
      if (val === false || val == null) { el.removeAttribute(nome); return; }
      if (nome === "style" && typeof val === "object") { el.removeAttribute("style"); Object.assign(el.style, val); return; }
      el.setAttribute(nome, val === true ? "" : String(val));
      if (/^(value|checked|selected|disabled)$/.test(nome)) { try { el[nome] = val; } catch (_) {} }
    });
    filhos(n, el, escopo, host);
    out.appendChild(el);
  }
  function importa(n, out, escopo, host) {
    var nome = n.getAttribute("name") || "";
    var arquivo = resolve(host.arquivo, /\.dc\.html$/.test(nome) ? nome : nome + ".dc.html");
    var props = {};
    Array.prototype.forEach.call(n.attributes, function (a) {
      if (a.name === "name" || a.name.indexOf("hint-") === 0) return;
      props[camelo(a.name)] = atributo(n, a.name, escopo);
    });
    var idx = host.idxFilho++;
    var filho = host.filhos[idx];
    if (!filho || filho.arquivo !== arquivo) {
      var fonte = SRC[arquivo];
      if (fonte == null) { erro("dc-import", "arquivo não encontrado: " + arquivo); return; }
      var doc = new DOMParser().parseFromString(fonte, "text/html");
      var raiz = doc.querySelector("x-dc");
      if (!raiz) { erro("dc-import", arquivo + " sem <x-dc>"); return; }
      filho = host.filhos[idx] = new Host(raiz, doc.querySelector("script[data-dc-script]"), arquivo, props);
      filho.no.setAttribute("data-dc-import", nome);
      filho.montar();
    } else {
      var antes = filho.inst.props;
      filho.inst.props = Object.assign({}, defaults(null), antes, props);
      filho.render();
      try { if (filho.inst.componentDidUpdate) filho.inst.componentDidUpdate(antes, filho.inst.state); } catch (e) { erro("componentDidUpdate de " + arquivo, e); }
    }
    out.appendChild(filho.no);
  }

  function iniciar() {
    var raiz = document.querySelector("x-dc");
    if (!raiz) { erro("início", "a página não tem <x-dc>"); window.__DC_READY = true; return; }
    var arquivo = window.__DC_FILE || "Main.dc.html";
    var host = new Host(raiz, document.querySelector("script[data-dc-script]"), arquivo, {});
    raiz.parentNode.insertBefore(host.no, raiz);
    Array.prototype.slice.call(raiz.querySelectorAll("helmet")).forEach(function (h) { helmet(h, arquivo, true); });
    raiz.remove();
    host.montar();
    window.__DC_READY = true;
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
