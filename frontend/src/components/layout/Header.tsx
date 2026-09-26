import { ChevronDown, Languages, LogOut, Moon, Package, RotateCcw, Search, ShieldCheck, ShoppingCart, Sun, SunMoon, UserRound } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { useAuth } from "../../auth/AuthProvider";
import { LANGUAGES, useI18n } from "../../i18n/I18nProvider";
import { LANGUAGE_NAMES } from "../../i18n/strings";
import { api } from "../../lib/api";
import { useCart } from "../../lib/queries";
import type { Language } from "../../lib/types";
import { cn } from "../../lib/utils";
import { useTheme, type ThemeChoice } from "../../theme/ThemeProvider";
import { buttonVariants } from "../ui/button";

export function Logo() {
  return (
    <Link to="/" className="flex shrink-0 items-center gap-2 font-bold tracking-tight" aria-label="ShopSense home">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-on-brand">
        <ShieldCheck className="h-5 w-5" aria-hidden />
      </span>
      <span className="text-lg">ShopSense</span>
    </Link>
  );
}

/** Small click-to-open menu that closes on outside click or Escape. */
function Menu({ label, trigger, children }: { label: string; trigger: ReactNode; children: (close: () => void) => ReactNode }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);
  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        aria-label={label}
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((v) => !v)}
        className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "px-2.5")}
      >
        {trigger}
      </button>
      {open && (
        <div role="menu" className="absolute right-0 z-50 mt-2 min-w-48 rounded-xl border border-line bg-surface p-1.5 shadow-xl shadow-black/10">
          {children(() => setOpen(false))}
        </div>
      )}
    </div>
  );
}

const menuItem = "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm hover:bg-surface-2";

function SearchBar({ className }: { className?: string }) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [q, setQ] = useState(params.get("q") ?? "");
  useEffect(() => {
    setQ(params.get("q") ?? "");
  }, [params]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const next = new URLSearchParams();
    if (q.trim()) next.set("q", q.trim());
    navigate(`/?${next}`);
  };
  return (
    <form onSubmit={submit} role="search" className={cn("relative", className)}>
      <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
      <input
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder={t("search_placeholder")}
        aria-label={t("search")}
        className="h-11 w-full rounded-xl border border-line bg-surface-2 pl-10 pr-4 text-sm placeholder:text-muted/80 focus:border-brand focus:bg-surface focus:outline-none focus:ring-4 focus:ring-ring"
      />
    </form>
  );
}

export function Header() {
  const { t, lang, setLang } = useI18n();
  const { theme, setTheme } = useTheme();
  const { user, isCustomer, logout } = useAuth();
  const cart = useCart();
  const navigate = useNavigate();
  const cartCount = cart.data?.totals.items_count ?? 0;

  const changeLanguage = (next: Language) => {
    setLang(next);
    // Remember it on the account too, so it follows the user across devices.
    if (user) api("/auth/me", { method: "PATCH", json: { preferred_language: next } }).catch(() => undefined);
  };

  const themes: { value: ThemeChoice; icon: ReactNode; label: string }[] = [
    { value: "light", icon: <Sun className="h-4 w-4" />, label: t("theme_light") },
    { value: "dark", icon: <Moon className="h-4 w-4" />, label: t("theme_dark") },
    { value: "system", icon: <SunMoon className="h-4 w-4" />, label: t("theme_system") },
  ];
  const ThemeIcon = theme === "dark" ? Moon : theme === "light" ? Sun : SunMoon;

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-surface/90 backdrop-blur supports-[backdrop-filter]:bg-surface/75">
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
        <Logo />
        <SearchBar className="mx-2 hidden flex-1 md:block" />
        <div className="ml-auto flex items-center gap-0.5">
          <Menu label={t("language")} trigger={<><Languages className="h-4 w-4" /><span className="hidden sm:inline">{LANGUAGE_NAMES[lang]}</span></>}>
            {(close) =>
              LANGUAGES.map((code) => (
                <button key={code} role="menuitemradio" aria-checked={lang === code} className={cn(menuItem, lang === code && "font-semibold text-brand")} onClick={() => { changeLanguage(code); close(); }}>
                  {LANGUAGE_NAMES[code]}
                </button>
              ))
            }
          </Menu>

          <Menu label={t("theme")} trigger={<ThemeIcon className="h-4 w-4" />}>
            {(close) =>
              themes.map((option) => (
                <button key={option.value} role="menuitemradio" aria-checked={theme === option.value} className={cn(menuItem, theme === option.value && "font-semibold text-brand")} onClick={() => { setTheme(option.value); close(); }}>
                  {option.icon}
                  {option.label}
                </button>
              ))
            }
          </Menu>

          {(isCustomer || !user) && (
            <Link to="/cart" className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "relative px-2.5")} aria-label={`${t("cart")} (${cartCount})`}>
              <ShoppingCart className="h-5 w-5" />
              <span className="hidden sm:inline">{t("cart")}</span>
              {cartCount > 0 && (
                <span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-brand px-1 text-[11px] font-bold text-on-brand">
                  {cartCount}
                </span>
              )}
            </Link>
          )}

          {user ? (
            <Menu label={user.name} trigger={<><UserRound className="h-4 w-4" /><span className="hidden max-w-28 truncate sm:inline">{user.name.split(" ")[0]}</span><ChevronDown className="h-3.5 w-3.5" /></>}>
              {(close) => (
                <>
                  <div className="px-3 py-2 text-xs text-muted">{user.email}</div>
                  {isCustomer && (
                    <>
                      <Link to="/orders" className={menuItem} onClick={close}><Package className="h-4 w-4" />{t("my_orders")}</Link>
                      <Link to="/returns" className={menuItem} onClick={close}><RotateCcw className="h-4 w-4" />{t("my_returns")}</Link>
                    </>
                  )}
                  <button className={cn(menuItem, "text-danger")} onClick={() => { close(); logout(); navigate("/"); }}>
                    <LogOut className="h-4 w-4" />{t("logout")}
                  </button>
                </>
              )}
            </Menu>
          ) : (
            <Link to="/login" className={cn(buttonVariants({ size: "sm" }), "ml-1")}>{t("login")}</Link>
          )}
        </div>
      </div>
      <div className="px-4 pb-3 md:hidden">
        <SearchBar />
      </div>
      {user && user.role !== "customer" && (
        <div className="border-t border-line bg-info-soft px-4 py-2 text-center text-sm text-info">
          {user.role === "seller" ? t("seller_dashboard_soon") : t("admin_panel_soon")}
        </div>
      )}
    </header>
  );
}
