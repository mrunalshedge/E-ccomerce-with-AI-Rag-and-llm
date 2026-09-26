import { useI18n } from "../i18n/I18nProvider";
import type { OrderStatus, PaymentStatus, ReturnStatus } from "../lib/types";
import { Badge } from "./ui/primitives";

const ORDER_TONE = { placed: "info", shipped: "warn", delivered: "brand", cancelled: "neutral" } as const;
const PAYMENT_TONE = { pending: "warn", paid: "brand", refunded: "info", void: "neutral" } as const;
const RETURN_TONE = { requested: "warn", approved: "brand", rejected: "danger" } as const;

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  const { t } = useI18n();
  return <Badge tone={ORDER_TONE[status]}>{t(`status_${status}`)}</Badge>;
}

export function PaymentStatusBadge({ status }: { status: PaymentStatus }) {
  const { t } = useI18n();
  return <Badge tone={PAYMENT_TONE[status]}>{t(`pay_${status}`)}</Badge>;
}

export function ReturnStatusBadge({ status }: { status: ReturnStatus }) {
  const { t } = useI18n();
  return <Badge tone={RETURN_TONE[status]}>{t(`ret_${status}`)}</Badge>;
}
