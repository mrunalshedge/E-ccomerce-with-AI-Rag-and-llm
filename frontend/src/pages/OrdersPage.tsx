import { ChevronRight, Package } from "lucide-react";
import { Link } from "react-router-dom";

import { OrderStatusBadge, PaymentStatusBadge } from "../components/StatusBadges";
import { buttonVariants } from "../components/ui/button";
import { Card, EmptyState, ErrorState, Skeleton } from "../components/ui/primitives";
import { useI18n } from "../i18n/I18nProvider";
import { formatDate, formatINR } from "../lib/format";
import { useOrders } from "../lib/queries";

export function OrdersPage() {
  const { t, lang } = useI18n();
  const orders = useOrders();

  if (orders.isLoading) return <Skeleton className="h-64" />;
  if (orders.isError || !orders.data) {
    return <ErrorState message={orders.error?.message ?? t("error_generic")} onRetry={() => orders.refetch()} retryLabel={t("retry")} />;
  }
  if (orders.data.length === 0) {
    return (
      <EmptyState
        icon={<Package className="h-6 w-6" />}
        title={t("no_orders")}
        body={t("no_orders_hint")}
        action={<Link to="/" className={buttonVariants()}>{t("continue_shopping")}</Link>}
      />
    );
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">{t("my_orders")}</h1>
      <ul className="space-y-3">
        {orders.data.map((order) => (
          <li key={order.id}>
            <Link to={`/orders/${order.id}`} className="block">
              <Card className="flex items-center gap-4 p-4 transition hover:border-brand/40">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold">{t("order_no", { id: order.id })}</span>
                    <OrderStatusBadge status={order.status} />
                    <PaymentStatusBadge status={order.payment_status} />
                  </div>
                  <p className="mt-1 truncate text-sm text-muted">
                    {order.items.map((i) => `${i.title} × ${i.quantity}`).join(", ")}
                  </p>
                  <p className="mt-0.5 text-xs text-muted">
                    {t("placed_on", { d: formatDate(order.created_at, lang) })} · {order.seller.business_name}
                  </p>
                </div>
                <div className="text-right">
                  <div className="font-bold tabular">{formatINR(order.totals.grand_total)}</div>
                </div>
                <ChevronRight className="h-5 w-5 text-muted" aria-hidden />
              </Card>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
