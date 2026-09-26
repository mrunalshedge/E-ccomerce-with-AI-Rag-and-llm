import { useI18n } from "../i18n/I18nProvider";
import { formatINR, isZero } from "../lib/format";
import type { PriceBreakdown as Breakdown, Totals } from "../lib/types";

function Row({ label, value, free, freeLabel }: { label: string; value: string; free?: boolean; freeLabel?: string }) {
  return (
    <div className="flex items-center justify-between py-1 text-sm">
      <dt className="text-muted">{label}</dt>
      <dd className="tabular">{free ? <span className="font-medium text-brand">{freeLabel}</span> : formatINR(value)}</dd>
    </div>
  );
}

/** Per-unit breakdown on the product page: every rupee accounted for. */
export function PriceBreakdown({ price }: { price: Breakdown }) {
  const { t } = useI18n();
  return (
    <dl>
      <Row label={t("base_price")} value={price.base_price} />
      <Row label={t("delivery")} value={price.delivery_fee} free={isZero(price.delivery_fee)} freeLabel={t("free")} />
      {!isZero(price.platform_fee) && <Row label={t("platform_fee")} value={price.platform_fee} />}
      <Row label={t("gst", { p: Number(price.gst_percent) })} value={price.gst_amount} />
      <div className="mt-2 flex items-center justify-between border-t border-line pt-3">
        <dt className="font-semibold">{t("you_pay")}</dt>
        <dd className="text-lg font-bold tabular">{formatINR(price.final_price)}</dd>
      </div>
    </dl>
  );
}

/** Cart / order totals with the same line structure. */
export function TotalsBreakdown({ totals }: { totals: Totals }) {
  const { t } = useI18n();
  return (
    <dl>
      <Row label={t("items_total", { n: totals.items_count })} value={totals.total_base} />
      <Row label={t("total_delivery")} value={totals.total_delivery} free={isZero(totals.total_delivery)} freeLabel={t("free")} />
      {!isZero(totals.total_platform_fee) && <Row label={t("total_platform")} value={totals.total_platform_fee} />}
      <Row label={t("total_gst")} value={totals.total_gst} />
      <div className="mt-2 flex items-center justify-between border-t border-line pt-3">
        <dt className="font-semibold">{t("total_payable")}</dt>
        <dd className="text-xl font-bold tabular">{formatINR(totals.grand_total)}</dd>
      </div>
    </dl>
  );
}
