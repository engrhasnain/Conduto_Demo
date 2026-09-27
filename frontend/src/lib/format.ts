import type { Lang } from "./api";

export const LOCALE: Record<Lang, string> = { es: "es-EC", en: "en-US", pt: "pt-BR" };
const SYMBOL: Record<string, string> = { USD: "USD", PEN: "S/", BRL: "R$" };

export function money(x: number | null | undefined, lang: Lang, currency = "USD", compact = true): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "–";
  const n = new Intl.NumberFormat(LOCALE[lang], compact
    ? { notation: "compact", maximumFractionDigits: Math.abs(x) >= 1e9 ? 2 : 1 }
    : { maximumFractionDigits: 0 }).format(x);
  return `${SYMBOL[currency] ?? currency} ${n}`;
}

export function num(x: number | null | undefined, lang: Lang, digits = 0): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "–";
  return new Intl.NumberFormat(LOCALE[lang], { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(x);
}

export function pct(x: number | null | undefined, lang: Lang, digits = 1): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "–";
  return new Intl.NumberFormat(LOCALE[lang], { style: "percent", minimumFractionDigits: digits, maximumFractionDigits: digits }).format(x);
}

export function pts(x: number, lang: Lang, signed = true): string {
  const v = x * 100;
  const s = new Intl.NumberFormat(LOCALE[lang], { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(Math.abs(v));
  const sign = signed ? (v > 0.05 ? "+" : v < -0.05 ? "−" : "") : "";
  return `${sign}${s} ${{ es: "puntos", en: "points", pt: "pontos" }[lang]}`;
}

export function period(p: string | null | undefined, lang: Lang, long = false): string {
  if (!p) return "–";
  const [y, m] = p.split("-").map(Number);
  return new Intl.DateTimeFormat(LOCALE[lang], { month: long ? "long" : "short", year: "numeric", timeZone: "UTC" })
    .format(new Date(Date.UTC(y, m - 1, 15)));
}

export function date(d: string | null | undefined, lang: Lang): string {
  if (!d) return "–";
  const [y, m, dd] = d.split("-").map(Number);
  return new Intl.DateTimeFormat(LOCALE[lang], { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" })
    .format(new Date(Date.UTC(y, m - 1, dd)));
}

export function ratio(x: number | null | undefined): string {
  return x === null || x === undefined ? "–" : x.toFixed(2);
}
