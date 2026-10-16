/* Traduction de l'interface : le texte français sert de clé, PEI_EN donne l'anglais.
   Une clé absente reste en français, l'affichage n'est donc jamais cassé. */
"use strict";

const I18N = {
  lang: "fr",
  names: { fr: "Français", en: "English" },
};

function readCookie(name) {
  const m = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
  return m ? decodeURIComponent(m[1]) : null;
}

function initialLang() {
  let saved = null;
  try { saved = localStorage.getItem("pei_lang"); } catch (e) { /* stockage indisponible */ }
  const fromCookie = readCookie("pei_lang");
  const fromBrowser = (navigator.language || "fr").slice(0, 2).toLowerCase();
  const lang = saved || fromCookie || fromBrowser;
  return lang === "en" ? "en" : "fr";
}

function setLang(lang) {
  I18N.lang = lang === "en" ? "en" : "fr";
  try { localStorage.setItem("pei_lang", I18N.lang); } catch (e) { /* stockage indisponible */ }
  document.cookie = `pei_lang=${I18N.lang}; path=/; max-age=31536000; samesite=lax`;
  document.documentElement.lang = I18N.lang;
}

function tr(text, vars) {
  let s = I18N.lang === "en" && typeof PEI_EN !== "undefined" ? (PEI_EN[text] ?? text) : text;
  if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (vars[k] !== undefined && vars[k] !== null ? vars[k] : m));
  return s;
}

function locale() { return I18N.lang === "en" ? "en-GB" : "fr-FR"; }

setLang(initialLang());
