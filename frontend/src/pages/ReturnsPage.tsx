import { RotateCcw } from "lucide-react";
import { Link } from "react-router-dom";

import { ReturnStatusBadge } from "../components/StatusBadges";
import { buttonVariants } from "../components/ui/button";
import { Card, EmptyState, ErrorState, Skeleton } from "../components/ui/primitives";
import { useI18n } from "../i18n/I18nProvider";
import type { StringKey } from "../i18n/strings";
import { formatDate, formatINR } from "../lib/format";
import { useReturns } from "../lib/queries";

export function ReturnsPage() {
  const { t, lang } = useI18n();
  const returns = useReturns();

  if (returns.isLoading) return <Skeleton className="h-64" />;
  if (returns.isError || !returns.data) {
    return <ErrorState message={returns.error?.message ?? t("error_generic")} onRetry={() => returns.refetch()} retryLabel={t("retry")} />;
  }
  if (returns.data.length === 0) {
    return (
      <EmptyState
        icon={<RotateCcw className="h-6 w-6" />}
        title={t("no_returns")}
        body={t("no_returns_hint")}
        action={<Link to="/orders" className={buttonVariants({ variant: "outline" })}>{t("my_orders")}</Link>}
      />
    );
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">{t("my_returns")}</h1>
      <ul className="space-y-3">
        {returns.data.map((r) => (
          <li key={r.id}>
            <Card className="p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold">{r.product_title}</span>
                    <ReturnStatusBadge status={r.status} />
                  </div>
                  <p className="mt-1 text-sm text-muted">
                    {t(`reason_${r.reason}` as StringKey)}
                    {r.exchange_size && ` (${t("exchange_label", { s: r.exchange_size })})`} · {formatDate(r.created_at, lang)} ·{" "}
                    <Link to={`/orders/${r.order_id}`} className="hover:text-brand hover:underline">
                      {t("order_no", { id: r.order_id })}
                    </Link>
                  </p>
                  <p className="mt-2 text-sm">{r.description}</p>
                  {r.resolution_note && <p className="mt-1 text-sm text-muted">“{r.resolution_note}”</p>}
                </div>
                <span className="font-semibold tabular">{t("refund", { amt: formatINR(r.refund_amount) })}</span>
              </div>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
