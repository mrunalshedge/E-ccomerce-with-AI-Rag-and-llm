import { ArrowLeft, Clock, LifeBuoy, MapPin, RotateCcw, Star } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";

import { OrderTimeline } from "../components/OrderTimeline";
import { TotalsBreakdown } from "../components/PriceBreakdown";
import { ReturnForm } from "../components/ReturnForm";
import { ReviewForm } from "../components/reviews/ReviewForm";
import { Stars } from "../components/reviews/Stars";
import { OrderStatusBadge, PaymentStatusBadge, ReturnStatusBadge } from "../components/StatusBadges";
import { Button, buttonVariants } from "../components/ui/button";
import { Badge, Card, ErrorState, Skeleton } from "../components/ui/primitives";
import { useI18n } from "../i18n/I18nProvider";
import { formatDate, formatINR } from "../lib/format";
import { useCancelOrder, useMyReviews, useOrder, useReturns } from "../lib/queries";
import type { Order } from "../lib/types";

const RETURN_WINDOW_DAYS = 7;

function daysLeftToReturn(order: Order): number {
  if (!order.delivered_at) return 0;
  const deadline = new Date(order.delivered_at).getTime() + RETURN_WINDOW_DAYS * 86_400_000;
  return Math.ceil((deadline - Date.now()) / 86_400_000);
}

export function OrderDetailPage() {
  const { t, lang } = useI18n();
  const { id } = useParams();
  const order = useOrder(Number(id));
  const returns = useReturns();
  const cancel = useCancelOrder();
  const [openReturn, setOpenReturn] = useState<number | null>(null);
  const [openReview, setOpenReview] = useState<number | null>(null);
  const myReviews = useMyReviews();

  if (order.isLoading) return <Skeleton className="h-96" />;
  if (order.isError || !order.data) {
    return <ErrorState message={order.error?.message ?? t("error_generic")} onRetry={() => order.refetch()} retryLabel={t("retry")} />;
  }

  const o = order.data;
  const daysLeft = daysLeftToReturn(o);
  const returnByItem = new Map((returns.data ?? []).map((r) => [r.order_item_id, r]));
  const reviewByItem = new Map((myReviews.data ?? []).map((r) => [r.order_item_id, r]));

  const onCancel = () => {
    if (!window.confirm(t("cancel_confirm"))) return;
    cancel.mutate(o.id, {
      onSuccess: () => toast.success(t("order_cancelled")),
      onError: (error) => toast.error(error.message),
    });
  };

  return (
    <div>
      <Link to="/orders" className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted hover:text-fg">
        <ArrowLeft className="h-4 w-4" /> {t("all_orders")}
      </Link>

      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold">{t("order_no", { id: o.id })}</h1>
            <OrderStatusBadge status={o.status} />
            <PaymentStatusBadge status={o.payment_status} />
          </div>
          <p className="mt-1 text-sm text-muted">
            {t("placed_on", { d: formatDate(o.created_at, lang, true) })} · {t("sold_by", { name: o.seller.business_name })}
          </p>
        </div>
        {o.status === "placed" && (
          <Button variant="danger" onClick={onCancel} loading={cancel.isPending}>
            {cancel.isPending ? t("cancelling") : t("cancel_order")}
          </Button>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div className="space-y-6">
          <Card className="p-5">
            <h2 className="mb-3 font-semibold">{t("items")}</h2>
            {o.status === "delivered" && (
              <p className="mb-3 flex items-center gap-1.5 text-sm text-muted">
                <Clock className="h-4 w-4" aria-hidden />
                {daysLeft > 0 ? t("days_left", { n: daysLeft }) : t("return_window_closed")}
              </p>
            )}
            <ul className="divide-y divide-line">
              {o.items.map((item) => {
                const existing = returnByItem.get(item.id);
                return (
                  <li key={item.id} className="py-3 first:pt-0 last:pb-0">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        {item.product_id ? (
                          <Link to={`/products/${item.product_id}`} className="font-medium hover:text-brand">
                            {item.title}
                          </Link>
                        ) : (
                          <span className="font-medium">{item.title}</span>
                        )}
                        <p className="text-sm text-muted tabular">
                          {formatINR(item.unit_price.final_price)} × {item.quantity}
                        </p>
                      </div>
                      <span className="font-semibold tabular">{formatINR(item.line_total)}</span>
                    </div>

                    {o.status === "delivered" && item.product_id !== null && (
                      <div className="mt-2">
                        {reviewByItem.has(item.id) ? (
                          <span className="inline-flex items-center gap-2 text-sm text-muted">
                            <Stars value={reviewByItem.get(item.id)!.rating} />
                            {t("you_rated", { n: reviewByItem.get(item.id)!.rating })}
                            {reviewByItem.get(item.id)!.status === "flagged" && <Badge tone="warn">{t("review_pending")}</Badge>}
                          </span>
                        ) : openReview === item.id ? (
                          <ReviewForm productId={item.product_id} onDone={() => setOpenReview(null)} />
                        ) : (
                          <Button variant="secondary" size="sm" onClick={() => setOpenReview(item.id)}>
                            <Star className="h-4 w-4" /> {t("write_review")}
                          </Button>
                        )}
                      </div>
                    )}

                    {existing ? (
                      <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
                        <Badge tone="info">{t("return_requested_badge")}</Badge>
                        <ReturnStatusBadge status={existing.status} />
                        {existing.resolution_note && <span className="text-muted">“{existing.resolution_note}”</span>}
                      </div>
                    ) : (
                      o.status === "delivered" &&
                      daysLeft > 0 &&
                      (openReturn === item.id ? (
                        <ReturnForm item={item} onDone={() => setOpenReturn(null)} />
                      ) : (
                        <Button variant="outline" size="sm" className="mt-2" onClick={() => setOpenReturn(item.id)}>
                          <RotateCcw className="h-4 w-4" /> {t("report_problem")}
                        </Button>
                      ))
                    )}
                  </li>
                );
              })}
            </ul>
          </Card>

          <Card className="p-5">
            <h2 className="mb-4 font-semibold">{t("order_timeline")}</h2>
            <OrderTimeline order={o} />
          </Card>
        </div>

        <aside className="space-y-6 lg:sticky lg:top-24 lg:self-start">
          <Card className="p-5">
            <h2 className="mb-3 font-semibold">{t("payment")}</h2>
            <TotalsBreakdown totals={o.totals} />
            <p className="mt-3 text-sm text-muted">{t(`pay_${o.payment_method}` as "pay_upi")}</p>
          </Card>
          <Card className="p-5">
            <h2 className="mb-2 flex items-center gap-2 font-semibold">
              <MapPin className="h-4 w-4 text-muted" aria-hidden /> {t("ship_to")}
            </h2>
            <p className="whitespace-pre-line text-sm text-muted">{o.shipping_address}</p>
          </Card>
          <Link to={`/help/new?order=${o.id}`} className={buttonVariants({ variant: "outline", className: "w-full" })}>
            <LifeBuoy className="h-4 w-4" /> {t("need_help_order")}
          </Link>
        </aside>
      </div>
    </div>
  );
}
