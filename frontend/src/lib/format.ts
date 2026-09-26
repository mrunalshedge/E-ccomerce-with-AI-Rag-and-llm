import type { Language, Money } from "./types";

const LOCALES: Record<Language, string> = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" };

/** ₹1,239 for whole rupees, ₹1,239.50 otherwise (Indian digit grouping). */
export function formatINR(amount: Money | number): string {
  const value = typeof amount === "number" ? amount : Number(amount);
  const whole = Number.isInteger(value);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: whole ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatDate(iso: string, lang: Language, withTime = false): string {
  return new Intl.DateTimeFormat(LOCALES[lang], {
    day: "numeric",
    month: "short",
    year: "numeric",
    ...(withTime ? { hour: "numeric", minute: "2-digit" } : {}),
  }).format(new Date(iso));
}

export function isZero(amount: Money): boolean {
  return Number(amount) === 0;
}
