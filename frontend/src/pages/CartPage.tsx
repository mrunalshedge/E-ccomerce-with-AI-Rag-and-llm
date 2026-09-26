import { Lock, ShoppingCart, Trash2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { TotalsBreakdown } from "../components/PriceBreakdown";
import { ProductImage } from "../components/ProductImage";
import { QuantityStepper } from "../components/QuantityStepper";
import { Button, buttonVariants } from "../components/ui/button";
import { Card, EmptyState, ErrorState, Skeleton } from "../components/ui/primitives";
import { useI18n } from "../i18n/I18nProvider";
import { formatINR } from "../lib/format";
import { useCart, useRemoveCartItem, useUpdateCartItem } from "../lib/queries";

const MAX_PER_ITEM = 10;

export function CartPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const cart = useCart();
  const update = useUpdateCartItem();
  const remove = useRemoveCartItem();
  const onError = (error: Error) => toast.error(error.message);

  if (cart.isLoading) return <Skeleton className="h-64" />;
  if (cart.isError || !cart.data) {
    return <ErrorState message={cart.error?.message ?? t("error_generic")} onRetry={() => cart.refetch()} retryLabel={t("retry")} />;
  }

  const { items, totals } = cart.data;
  if (items.length === 0) {
    return (
      <EmptyState
        icon={<ShoppingCart className="h-6 w-6" />}
        title={t("cart_empty")}
        body={t("cart_empty_hint")}
        action={<Link to="/" className={buttonVariants()}>{t("continue_shopping")}</Link>}
      />
    );
  }

  const busy = update.isPending || remove.isPending;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">{t("your_cart")}</h1>
      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <ul className="space-y-3">
          {items.map((line) => (
            <li key={line.product_id}>
              <Card className="flex gap-4 p-3 sm:p-4">
                <Link to={`/products/${line.product_id}`} className="w-20 shrink-0 sm:w-24">
                  <ProductImage src={line.image_url} title={line.title} category={line.category} />
                </Link>
                <div className="flex min-w-0 flex-1 flex-col">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <Link to={`/products/${line.product_id}`} className="line-clamp-2 font-semibold hover:text-brand">
                        {line.title}
                      </Link>
                      <p className="text-xs text-muted">{t("sold_by", { name: line.seller_name })}</p>
                    </div>
                    <div className="text-right">
                      <div className="font-bold tabular">{formatINR(line.line_total)}</div>
                      <div className="text-xs text-muted tabular">{formatINR(line.unit_price.final_price)} × {line.quantity}</div>
                    </div>
                  </div>
                  <div className="mt-auto flex items-center justify-between pt-3">
                    <QuantityStepper
                      value={line.quantity}
                      max={Math.min(MAX_PER_ITEM, line.available_stock)}
                      onChange={(quantity) => update.mutate({ productId: line.product_id, quantity }, { onError })}
                      disabled={busy}
                      label={t("quantity")}
                    />
                    <Button variant="ghost" size="sm" className="text-muted hover:text-danger" onClick={() => remove.mutate(line.product_id, { onError })} disabled={busy}>
                      <Trash2 className="h-4 w-4" /> <span className="hidden sm:inline">{t("remove")}</span>
                    </Button>
                  </div>
                </div>
              </Card>
            </li>
          ))}
        </ul>

        <aside className="lg:sticky lg:top-24 lg:self-start">
          <Card className="p-5">
            <TotalsBreakdown totals={totals} />
            <p className="mt-4 flex gap-2 rounded-xl bg-brand-soft p-3 text-xs text-brand">
              <Lock className="h-4 w-4 shrink-0" aria-hidden />
              {t("price_locked_note")}
            </p>
            <Button size="lg" className="mt-4 w-full" onClick={() => navigate("/checkout")}>
              {t("proceed_to_checkout")}
            </Button>
          </Card>
        </aside>
      </div>
    </div>
  );
}
