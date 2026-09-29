import { Eye } from "lucide-react";
import { useState, type FormEvent } from "react";

import { useI18n } from "../../i18n/I18nProvider";
import { usePricePreview } from "../../lib/queries";
import type { Product, ProductInput } from "../../lib/types";
import { PriceBreakdown } from "../PriceBreakdown";
import { Button } from "../ui/button";
import { Card, Field, Input, Textarea } from "../ui/primitives";
import { SizeEditor, draftFrom, draftProblems, payloadFrom, type SizeDraft } from "./SizeEditor";

const GST_RATES = ["0", "5", "12", "18", "28"];

function fromProduct(p?: Product): ProductInput {
  return {
    title: p?.title ?? "",
    description: p?.description ?? "",
    category: p?.category ?? "",
    base_price: p ? String(Number(p.price.base_price)) : "",
    delivery_fee: p ? String(Number(p.price.delivery_fee)) : "0",
    platform_fee: p ? String(Number(p.price.platform_fee)) : "0",
    gst_percent: p ? String(Number(p.price.gst_percent)) : "18",
    stock: p?.stock ?? 10,
    is_returnable: p?.is_returnable ?? true,
    country_of_origin: p?.country_of_origin ?? "India",
    image_url: p?.image_url ?? null,
    sizes: null, // kept in the size editor's draft until submit
    size_chart: null,
  };
}

/** Add/edit form with a live "customers will see" price computed by the server's pricing rule. */
export function ProductForm({
  product,
  pending,
  onSubmit,
  onCancel,
}: {
  product?: Product;
  pending: boolean;
  onSubmit: (input: ProductInput) => void;
  onCancel: () => void;
}) {
  const { t } = useI18n();
  const [form, setForm] = useState<ProductInput>(() => fromProduct(product));
  const [sizeDraft, setSizeDraft] = useState<SizeDraft>(() => draftFrom(product?.sizes, product?.size_chart));
  const sized = sizeDraft.sizes.length > 0;
  const set = <K extends keyof ProductInput>(key: K, value: ProductInput[K]) => setForm((f) => ({ ...f, [key]: value }));
  const preview = usePricePreview({ base: form.base_price, delivery: form.delivery_fee, platform: form.platform_fee, gst: form.gst_percent });
  const valid = form.title.trim().length >= 2 && form.description.trim().length > 0 && form.category.trim().length >= 2 && Number(form.base_price) > 0 && !draftProblems(sizeDraft);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (valid) onSubmit({ ...form, image_url: form.image_url?.trim() || null, ...payloadFrom(sizeDraft) });
  };
  const money = (key: "base_price" | "delivery_fee" | "platform_fee") => (
    <Input id={key} inputMode="decimal" value={form[key]} onChange={(e) => set(key, e.target.value.replace(/[^\d.]/g, ""))} />
  );

  return (
    <form onSubmit={submit} className="grid gap-5 lg:grid-cols-[1fr_320px]">
      <div className="space-y-4">
        <Field id="title" label={t("seller_field_title")}>
          <Input id="title" value={form.title} onChange={(e) => set("title", e.target.value)} maxLength={200} />
        </Field>
        <Field id="description" label={t("seller_field_description")}>
          <Textarea id="description" value={form.description} onChange={(e) => set("description", e.target.value)} maxLength={5000} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="category" label={t("seller_field_category")}>
            <Input id="category" value={form.category} onChange={(e) => set("category", e.target.value)} placeholder="clothing" maxLength={100} />
          </Field>
          <Field id="country" label={t("seller_field_origin")}>
            <Input id="country" value={form.country_of_origin} onChange={(e) => set("country_of_origin", e.target.value)} maxLength={100} />
          </Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field id="base_price" label={t("seller_field_base_price")}>{money("base_price")}</Field>
          <Field id="delivery_fee" label={t("seller_field_delivery")}>{money("delivery_fee")}</Field>
          <Field id="platform_fee" label={t("seller_field_platform")}>{money("platform_fee")}</Field>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="gst" label={t("seller_field_gst")}>
            <select
              id="gst"
              value={form.gst_percent}
              onChange={(e) => set("gst_percent", e.target.value)}
              className="h-11 w-full rounded-xl border border-line bg-surface px-3 text-sm focus:border-brand focus:outline-none focus:ring-4 focus:ring-ring"
            >
              {(GST_RATES.includes(form.gst_percent) ? GST_RATES : [...GST_RATES, form.gst_percent]).map((r) => (
                <option key={r} value={r}>
                  {r}%
                </option>
              ))}
            </select>
          </Field>
          <Field id="stock" label={t("seller_field_stock")}>
            <Input
              id="stock"
              type="number"
              min={0}
              disabled={sized} // a sized product's stock is the sum of its sizes
              value={sized ? sizeDraft.sizes.reduce((sum, s) => sum + s.stock, 0) : form.stock}
              onChange={(e) => set("stock", Math.max(0, Number(e.target.value) || 0))}
            />
          </Field>
        </div>
        <SizeEditor draft={sizeDraft} onChange={setSizeDraft} />
        <Field id="image" label={t("seller_field_image")}>
          <Input id="image" type="url" value={form.image_url ?? ""} onChange={(e) => set("image_url", e.target.value)} placeholder="https://…" />
        </Field>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.is_returnable} onChange={(e) => set("is_returnable", e.target.checked)} className="h-4 w-4 accent-[var(--brand)]" />
          {t("seller_field_returnable")}
        </label>
        <div className="flex gap-2">
          <Button type="submit" disabled={!valid} loading={pending}>
            {product ? t("seller_save") : t("seller_create")}
          </Button>
          <Button type="button" variant="ghost" onClick={onCancel}>
            {t("close")}
          </Button>
        </div>
      </div>

      <aside className="lg:sticky lg:top-24 lg:self-start">
        <Card className="p-4">
          <h3 className="mb-1 flex items-center gap-2 font-semibold">
            <Eye className="h-4 w-4 text-brand" aria-hidden /> {t("seller_preview_title")}
          </h3>
          <p className="mb-3 text-xs text-muted">{t("seller_preview_note")}</p>
          {preview.data ? <PriceBreakdown price={preview.data} /> : <p className="text-sm text-muted">—</p>}
        </Card>
      </aside>
    </form>
  );
}
