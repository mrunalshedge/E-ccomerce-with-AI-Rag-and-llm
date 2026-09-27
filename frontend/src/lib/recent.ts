// Guest "recently viewed" list in localStorage: most recent first, no duplicates, capped at 12
// (the same LRU behaviour the backend uses for logged-in users).
const KEY = "shopsense.recent";
const CAPACITY = 12;

export function getRecentLocal(): number[] {
  try {
    const ids = JSON.parse(localStorage.getItem(KEY) ?? "[]") as unknown;
    return Array.isArray(ids) ? ids.filter((id): id is number => Number.isInteger(id)) : [];
  } catch {
    return [];
  }
}

export function rememberRecentLocal(productId: number): void {
  const ids = [productId, ...getRecentLocal().filter((id) => id !== productId)].slice(0, CAPACITY);
  try {
    localStorage.setItem(KEY, JSON.stringify(ids));
  } catch {
    /* storage unavailable: just don't remember */
  }
}
