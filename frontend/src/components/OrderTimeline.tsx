import { CircleCheck, CircleX, Package, Truck } from "lucide-react";

import { useI18n } from "../i18n/I18nProvider";
import { formatDate } from "../lib/format";
import type { Order, OrderStatus } from "../lib/types";
import { cn } from "../lib/utils";

const STEPS: OrderStatus[] = ["placed", "shipped", "delivered"];
const ICONS = { placed: Package, shipped: Truck, delivered: CircleCheck, cancelled: CircleX };

/** Vertical status timeline: completed steps show when they happened and the note recorded. */
export function OrderTimeline({ order }: { order: Order }) {
  const { t, lang } = useI18n();
  const events = new Map(order.timeline.map((e) => [e.status, e]));
  const steps: OrderStatus[] = order.status === "cancelled" ? [...order.timeline.map((e) => e.status)] : STEPS;

  return (
    <ol className="relative">
      {steps.map((step, index) => {
        const event = events.get(step);
        const done = Boolean(event);
        const Icon = ICONS[step];
        const last = index === steps.length - 1;
        return (
          <li key={step} className="relative flex gap-4 pb-6 last:pb-0">
            {!last && (
              <span
                className={cn("absolute left-[17px] top-9 h-[calc(100%-2.25rem)] w-0.5", done ? "bg-brand" : "bg-line")}
                aria-hidden
              />
            )}
            <span
              className={cn(
                "flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2",
                step === "cancelled"
                  ? "border-muted bg-surface-2 text-muted"
                  : done
                    ? "border-brand bg-brand text-on-brand"
                    : "border-line bg-surface text-muted",
              )}
            >
              <Icon className="h-4 w-4" aria-hidden />
            </span>
            <div className="pt-1.5">
              <p className={cn("font-semibold", !done && "text-muted")}>{t(`status_${step}`)}</p>
              {event && (
                <>
                  <p className="text-xs text-muted">{formatDate(event.created_at, lang, true)}</p>
                  {event.note && <p className="mt-1 text-sm text-muted">{event.note}</p>}
                </>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
