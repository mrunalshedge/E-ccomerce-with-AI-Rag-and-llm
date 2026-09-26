import { Banknote, CircleCheck, CreditCard, Info, QrCode, type LucideIcon } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { TotalsBreakdown } from "../components/PriceBreakdown";
import { Button } from "../components/ui/button";
import { Card, Field, Skeleton, Textarea } from "../components/ui/primitives";
import { useI18n } from "../i18n/I18nProvider";
import { ApiError } from "../lib/api";
import { formatINR } from "../lib/format";
import { useCart, useCheckout } from "../lib/queries";
import type { PaymentMethod } from "../lib/types";
import { cn } from "../lib/utils";

const ADDRESS_KEY = "shopsense.address";

function lastAddress(): string {
  try {
    return localStorage.getItem(ADDRESS_KEY) ?? "";
  } catch {
    return "";
  }
}

export function CheckoutPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const cart = useCart();
  const checkout = useCheckout();
  const [address, setAddress] = useState(lastAddress);
  // Deliberately no default: the customer must choose (no silent COD).
  const [method, setMethod] = useState<PaymentMethod | null>(null);
  const [touched, setTouched] = useState(false);

  if (cart.isLoading) return <Skeleton className="h-96" />;
  if (!cart.data || cart.data.items.length === 0) return <Navigate to="/cart" replace />;

  const { totals, items } = cart.data;
  const sellers = new Set(items.map((i) => i.seller_id)).size;
  const addressOk = address.trim().length >= 10;
  const total = formatINR(totals.grand_total);

  const options: { value: PaymentMethod; icon: LucideIcon; title: string; hint: string }[] = [
    { value: "upi", icon: QrCode, title: t("pay_upi"), hint: t("pay_upi_hint") },
    { value: "card", icon: CreditCard, title: t("pay_card"), hint: t("pay_card_hint") },
    { value: "cod", icon: Banknote, title: t("pay_cod"), hint: t("pay_cod_hint") },
  ];

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (!addressOk || !method) return;
    checkout.mutate(
      { paymentMethod: method, address: address.trim(), expectedTotal: totals.grand_total },
      {
        onSuccess: (result) => {
          try {
            localStorage.setItem(ADDRESS_KEY, address.trim());
          } catch {
            /* ignore */
          }
          toast.success(t("order_placed"));
          navigate(result.orders.length === 1 ? `/orders/${result.orders[0].id}` : "/orders");
        },
        onError: (error) => {
          if (error instanceof ApiError && error.status === 409) {
            toast.error(t("price_changed_title"), { description: error.message, duration: 8000 });
            navigate("/cart");
          } else {
            toast.error(error.message);
          }
        },
      },
    );
  };

  return (
    <form onSubmit={submit} noValidate>
      <h1 className="mb-6 text-2xl font-bold">{t("checkout")}</h1>
      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="space-y-6">
          <Card className="p-5">
            <Field
              id="address"
              label={t("delivery_address")}
              hint={t("address_hint")}
              error={touched && !addressOk ? t("address_hint") : undefined}
            >
              <Textarea
                id="address"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder={t("address_placeholder")}
                autoComplete="street-address"
                aria-invalid={touched && !addressOk}
                maxLength={500}
              />
            </Field>
          </Card>

          <Card className="p-5">
            <fieldset>
              <legend className="font-semibold">{t("payment_method")}</legend>
              <p className="mb-4 text-sm text-muted">{t("payment_hint")}</p>
              <div className="grid gap-3 sm:grid-cols-3">
                {options.map(({ value, icon: Icon, title, hint }) => {
                  const selected = method === value;
                  return (
                    <label
                      key={value}
                      className={cn(
                        "relative flex cursor-pointer flex-col gap-2 rounded-xl border-2 p-4 transition",
                        selected ? "border-brand bg-brand-soft" : "border-line hover:border-brand/40",
                      )}
                    >
                      <input type="radio" name="payment" value={value} checked={selected} onChange={() => setMethod(value)} className="sr-only" />
                      <Icon className={cn("h-6 w-6", selected ? "text-brand" : "text-muted")} aria-hidden />
                      <span className="font-semibold">{title}</span>
                      <span className="text-xs text-muted">{hint}</span>
                      {selected && <CircleCheck className="absolute right-3 top-3 h-5 w-5 text-brand" aria-hidden />}
                    </label>
                  );
                })}
              </div>
              {touched && !method && (
                <p className="mt-3 text-sm text-danger" role="alert">
                  {t("choose_payment_first")}
                </p>
              )}
            </fieldset>
          </Card>
        </div>

        <aside className="lg:sticky lg:top-24 lg:self-start">
          <Card className="p-5">
            <h2 className="mb-3 font-semibold">{t("order_summary")}</h2>
            <ul className="mb-4 space-y-1.5 text-sm">
              {items.map((i) => (
                <li key={i.product_id} className="flex justify-between gap-3">
                  <span className="truncate text-muted">
                    {i.title} × {i.quantity}
                  </span>
                  <span className="tabular">{formatINR(i.line_total)}</span>
                </li>
              ))}
            </ul>
            <TotalsBreakdown totals={totals} />
            {sellers > 1 && <p className="mt-3 text-xs text-muted">{t("split_note", { n: sellers })}</p>}
            <Button type="submit" size="lg" className="mt-4 w-full" loading={checkout.isPending}>
              {checkout.isPending
                ? t("placing_order")
                : !method
                  ? t("choose_payment_first")
                  : method === "cod"
                    ? t("place_order_cod", { amt: total })
                    : t("place_order_pay", { amt: total })}
            </Button>
            <p className="mt-3 flex gap-2 text-xs text-muted">
              <Info className="h-4 w-4 shrink-0" aria-hidden /> {t("payments_simulated")}
            </p>
          </Card>
        </aside>
      </div>
    </form>
  );
}
