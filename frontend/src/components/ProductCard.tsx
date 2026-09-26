import { Truck } from "lucide-react";
import { Link } from "react-router-dom";

import { useI18n } from "../i18n/I18nProvider";
import { formatINR, isZero } from "../lib/format";
import type { Product } from "../lib/types";
import { ProductImage } from "./ProductImage";
import { RatingChip } from "./reviews/Stars";
import { TrustChip } from "./TrustScore";
import { Badge } from "./ui/primitives";

export function ProductCard({ product }: { product: Product }) {
  const { t, category } = useI18n();
  const { price, seller } = product;
  const soldOut = product.stock === 0;

  return (
    <Link
      to={`/products/${product.id}`}
      className="group flex flex-col rounded-2xl border border-line bg-surface p-3 transition hover:-translate-y-0.5 hover:border-brand/40 hover:shadow-lg hover:shadow-black/5"
    >
      <div className="relative">
        <ProductImage src={product.image_url} title={product.title} category={product.category} />
        {soldOut && (
          <span className="absolute inset-0 flex items-center justify-center rounded-xl bg-surface/70 text-sm font-semibold backdrop-blur-[1px]">
            {t("out_of_stock")}
          </span>
        )}
      </div>

      <div className="mt-3 flex flex-1 flex-col">
        <span className="text-xs font-medium uppercase tracking-wide text-muted">{category(product.category)}</span>
        <h3 className="mt-0.5 line-clamp-2 font-semibold leading-snug group-hover:text-brand">{product.title}</h3>
        <div className="mt-1 h-4">
          <RatingChip average={product.rating.average} count={product.rating.count} />
        </div>

        <div className="mt-2 flex items-center justify-between gap-2 text-xs text-muted">
          <span className="truncate">{seller.business_name}</span>
          <TrustChip score={seller.trust_score} label={String(Math.round(seller.trust_score))} />
        </div>

        <div className="mt-auto pt-3">
          <div className="text-xl font-bold tabular">{formatINR(price.final_price)}</div>
          <div className="text-xs text-muted">{t("incl_all")}</div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {isZero(price.delivery_fee) && (
              <Badge tone="brand">
                <Truck className="h-3 w-3" aria-hidden /> {t("free_delivery")}
              </Badge>
            )}
            {!soldOut && product.stock <= 5 && <Badge tone="warn">{t("only_left", { n: product.stock })}</Badge>}
          </div>
        </div>
      </div>
    </Link>
  );
}
