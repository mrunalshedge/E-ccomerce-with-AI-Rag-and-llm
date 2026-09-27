import { LayoutGrid, Search, Store } from "lucide-react";
import { useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useI18n } from "../../i18n/I18nProvider";
import { useSuggestions } from "../../lib/queries";
import type { SearchSuggestion } from "../../lib/types";
import { cn } from "../../lib/utils";

/** Bold the part of ``text`` that matches what was typed (any word start or the whole text). */
function Highlight({ text, query }: { text: string; query: string }) {
  const q = query.trim().toLowerCase();
  const index = text.toLowerCase().indexOf(q);
  if (!q || index < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, index)}
      <strong className="font-semibold text-fg">{text.slice(index, index + q.length)}</strong>
      {text.slice(index + q.length)}
    </>
  );
}

function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return debounced;
}

/** Search box with trie-backed autocomplete (accessible combobox: ↑ ↓ Enter Esc). */
export function SearchBar({ className }: { className?: string }) {
  const { t, category } = useI18n();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const listId = useId();
  const wrapper = useRef<HTMLFormElement>(null);
  const suggestions = useSuggestions(useDebounced(q, 150));
  const items = open && q.trim() ? (suggestions.data ?? []) : [];

  useEffect(() => {
    setQ(params.get("q") ?? "");
  }, [params]);

  useEffect(() => {
    setActive(-1);
  }, [suggestions.data]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (wrapper.current && !wrapper.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const go = (s: SearchSuggestion) => {
    setOpen(false);
    if (s.kind === "product" && s.product_id) navigate(`/products/${s.product_id}`);
    else if (s.kind === "category" && s.category) navigate(`/?category=${encodeURIComponent(s.category)}`);
    else navigate(`/?q=${encodeURIComponent(s.text)}`);
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (active >= 0 && items[active]) return go(items[active]);
    setOpen(false);
    const next = new URLSearchParams();
    if (q.trim()) next.set("q", q.trim());
    navigate(`/?${next}`);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown" && items.length) {
      e.preventDefault();
      setOpen(true);
      setActive((i) => (i + 1) % items.length);
    } else if (e.key === "ArrowUp" && items.length) {
      e.preventDefault();
      setActive((i) => (i <= 0 ? items.length - 1 : i - 1));
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <form ref={wrapper} onSubmit={submit} role="search" className={cn("relative", className)}>
      <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
      <input
        type="search"
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        placeholder={t("search_placeholder")}
        aria-label={t("search")}
        role="combobox"
        aria-expanded={items.length > 0}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
        autoComplete="off"
        className="h-11 w-full rounded-xl border border-line bg-surface-2 pl-10 pr-4 text-sm placeholder:text-muted/80 focus:border-brand focus:bg-surface focus:outline-none focus:ring-4 focus:ring-ring"
      />
      {items.length > 0 && (
        <ul id={listId} role="listbox" className="absolute left-0 right-0 z-50 mt-2 overflow-hidden rounded-xl border border-line bg-surface p-1.5 shadow-xl shadow-black/10">
          {items.map((s, i) => (
            <li
              key={`${s.kind}-${s.text}`}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              onMouseDown={(e) => {
                e.preventDefault(); // keep focus; select on click
                go(s);
              }}
              onMouseEnter={() => setActive(i)}
              className={cn("flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 text-sm text-muted", i === active && "bg-surface-2")}
            >
              {s.kind === "product" ? (
                <Search className="h-4 w-4 shrink-0" aria-hidden />
              ) : s.kind === "category" ? (
                <LayoutGrid className="h-4 w-4 shrink-0 text-brand" aria-hidden />
              ) : (
                <Store className="h-4 w-4 shrink-0" aria-hidden />
              )}
              <span className="truncate">
                <Highlight text={s.kind === "category" ? category(s.text) : s.text} query={q} />
              </span>
              {s.kind !== "product" && (
                <span className="ml-auto shrink-0 text-xs">{s.kind === "category" ? t("suggest_category") : t("suggest_seller")}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}
