import { BadgeCheck, ChevronLeft, ChevronRight, ReceiptIndianRupee, RotateCcw, SearchX, Sparkles, Truck } from "lucide-react";
import type { ReactNode } from "react";
import { useSearchParams } from "react-router-dom";

import { ProductCard } from "../components/ProductCard";
import { Button } from "../components/ui/button";
import { EmptyState, ErrorState, Skeleton } from "../components/ui/primitives";
import { useI18n } from "../i18n/I18nProvider";
import { PAGE_SIZE, useCategories, useProducts, useSearch } from "../lib/queries";
import { cn } from "../lib/utils";

function Pillar({ icon, title, body }: { icon: ReactNode; title: string; body: string }) {
  return (
    <div className="flex items-center gap-2.5 rounded-2xl bg-surface/70 p-3 ring-1 ring-line sm:items-start sm:gap-3 sm:p-4">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-soft text-brand sm:h-10 sm:w-10">{icon}</div>
      <div>
        <h3 className="text-[13px] font-semibold leading-snug sm:text-sm">{title}</h3>
        {/* Details hidden on phones so products stay near the top. */}
        <p className="mt-0.5 hidden text-sm text-muted sm:block">{body}</p>
      </div>
    </div>
  );
}

function Hero() {
  const { t } = useI18n();
  return (
    <section className="mb-6 overflow-hidden rounded-3xl border border-line bg-gradient-to-br from-brand-soft via-surface to-surface p-5 sm:mb-8 sm:p-10">
      <h1 className="max-w-2xl text-2xl font-bold leading-tight tracking-tight sm:text-4xl">{t("hero_title")}</h1>
      <p className="mt-2 max-w-2xl text-sm text-muted sm:mt-3 sm:text-lg">{t("hero_subtitle")}</p>
      <div className="mt-5 grid grid-cols-2 gap-2 sm:mt-8 sm:gap-3 lg:grid-cols-4">
        <Pillar icon={<ReceiptIndianRupee className="h-5 w-5" />} title={t("trust_price_title")} body={t("trust_price_body")} />
        <Pillar icon={<BadgeCheck className="h-5 w-5" />} title={t("trust_seller_title")} body={t("trust_seller_body")} />
        <Pillar icon={<RotateCcw className="h-5 w-5" />} title={t("trust_return_title")} body={t("trust_return_body")} />
        <Pillar icon={<Truck className="h-5 w-5" />} title={t("trust_track_title")} body={t("trust_track_body")} />
      </div>
    </section>
  );
}

export function HomePage() {
  const { t, category: categoryLabel } = useI18n();
  const [params, setParams] = useSearchParams();
  const q = (params.get("q") ?? "").trim();
  const category = params.get("category") ?? "";
  const page = Math.max(1, Number(params.get("page")) || 1);

  // Browsing uses the paginated catalogue; typing a query switches to smart (semantic) search.
  const browse = useProducts({ category, page });
  const search = useSearch({ q, category });
  const products = q ? search : browse;
  const categories = useCategories();
  const pages = !q && browse.data ? Math.max(1, Math.ceil(browse.data.total / PAGE_SIZE)) : 1;

  const update = (changes: Record<string, string | null>) => {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    setParams(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const chip = (active: boolean) =>
    cn(
      "shrink-0 rounded-full border px-4 py-2 text-sm font-medium transition",
      active ? "border-brand bg-brand text-on-brand" : "border-line bg-surface hover:border-brand/50",
    );

  return (
    <>
      {!q && !category && page === 1 && <Hero />}

      <div className="-mx-4 mb-5 flex gap-2 overflow-x-auto px-4 pb-1" role="tablist" aria-label="Categories">
        <button role="tab" aria-selected={!category} className={chip(!category)} onClick={() => update({ category: null, page: null })}>
          {t("all_categories")}
        </button>
        {categories.data?.map((c) => (
          <button key={c.category} role="tab" aria-selected={category === c.category} className={chip(category === c.category)} onClick={() => update({ category: c.category, page: null })}>
            {categoryLabel(c.category)} <span className="opacity-60">· {c.count}</span>
          </button>
        ))}
      </div>

      <div className="mb-4 flex items-baseline justify-between gap-4">
        <h2 className="text-xl font-semibold">{q ? t("results_for", { q }) : category ? categoryLabel(category) : t("all_categories")}</h2>
        {products.data && <span className="text-sm text-muted">{t("products_count", { n: products.data.total })}</span>}
      </div>
      {q && (
        <p className="-mt-2 mb-4 flex items-center gap-1.5 text-sm text-muted">
          <Sparkles className="h-4 w-4 text-brand" aria-hidden /> {t("smart_search_hint")}
        </p>
      )}

      {products.isError ? (
        <ErrorState message={products.error.message} onRetry={() => products.refetch()} retryLabel={t("retry")} />
      ) : products.isLoading ? (
        <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 lg:grid-cols-4">
          {Array.from({ length: 8 }, (_, i) => (
            <div key={i} className="rounded-2xl border border-line bg-surface p-3">
              <Skeleton className="aspect-square" />
              <Skeleton className="mt-3 h-4 w-3/4" />
              <Skeleton className="mt-2 h-6 w-1/2" />
            </div>
          ))}
        </div>
      ) : products.data && products.data.items.length > 0 ? (
        <>
          <div className={cn("grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 lg:grid-cols-4", products.isPlaceholderData && "opacity-60")}>
            {products.data.items.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
          {pages > 1 && (
            <nav className="mt-8 flex items-center justify-center gap-3" aria-label="Pagination">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => update({ page: String(page - 1) })}>
                <ChevronLeft className="h-4 w-4" /> {t("previous")}
              </Button>
              <span className="text-sm text-muted">{t("page_of", { page, pages })}</span>
              <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => update({ page: String(page + 1) })}>
                {t("next")} <ChevronRight className="h-4 w-4" />
              </Button>
            </nav>
          )}
        </>
      ) : (
        <EmptyState
          icon={<SearchX className="h-6 w-6" />}
          title={t("no_products")}
          body={t("no_products_hint")}
          action={<Button variant="outline" onClick={() => setParams(new URLSearchParams())}>{t("clear_filters")}</Button>}
        />
      )}
    </>
  );
}
