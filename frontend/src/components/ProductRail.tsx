import { ChevronLeft, ChevronRight } from "lucide-react";
import { useRef, type ReactNode } from "react";

import { useI18n } from "../i18n/I18nProvider";
import type { Product } from "../lib/types";
import { ProductCard } from "./ProductCard";
import { Badge } from "./ui/primitives";

/** Horizontally scrolling row of product cards (snap scrolling on touch, arrows on desktop). */
export function ProductRail({
  title,
  icon,
  products,
  labels,
}: {
  title: string;
  icon?: ReactNode;
  products: Product[];
  labels?: Record<number, string>; // optional badge per product id (e.g. "Bought together")
}) {
  const { t } = useI18n();
  const track = useRef<HTMLDivElement>(null);
  if (products.length === 0) return null;
  const scroll = (dir: 1 | -1) => track.current?.scrollBy({ left: dir * track.current.clientWidth * 0.8, behavior: "smooth" });

  return (
    <section className="mb-8" aria-label={title}>
      <div className="mb-3 flex items-center gap-2">
        {icon}
        <h2 className="text-lg font-semibold">{title}</h2>
        <div className="ml-auto hidden gap-1 sm:flex">
          <button onClick={() => scroll(-1)} className="rounded-lg border border-line p-1.5 text-muted hover:text-fg" aria-label={t("scroll_left")}>
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button onClick={() => scroll(1)} className="rounded-lg border border-line p-1.5 text-muted hover:text-fg" aria-label={t("scroll_right")}>
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
      <div ref={track} className="-mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4 pb-2 sm:gap-4">
        {products.map((p) => (
          <div key={p.id} className="relative w-44 shrink-0 snap-start sm:w-52">
            {labels?.[p.id] && (
              <Badge tone="brand" className="absolute left-5 top-5 z-10 shadow-sm">
                {labels[p.id]}
              </Badge>
            )}
            <ProductCard product={p} />
          </div>
        ))}
      </div>
    </section>
  );
}
