import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { useI18n } from "../../i18n/I18nProvider";
import { useCreateReview } from "../../lib/queries";
import type { ReviewFit } from "../../lib/types";
import { cn } from "../../lib/utils";
import { Button } from "../ui/button";
import { Field, Input, Textarea } from "../ui/primitives";
import { StarInput } from "./Stars";

const FITS: ReviewFit[] = ["runs_small", "true_to_size", "runs_large"];

/** ``sized``: the purchase was in a size, so ask "How does it fit?" (optional). */
export function ReviewForm({ productId, sized = false, onDone }: { productId: number; sized?: boolean; onDone: () => void }) {
  const { t } = useI18n();
  const create = useCreateReview();
  const [rating, setRating] = useState(0);
  const [fit, setFit] = useState<ReviewFit | null>(null);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const valid = rating > 0 && body.trim().length >= 10;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!valid) return;
    create.mutate(
      { productId, rating, fit: sized ? fit : null, title: title.trim(), body: body.trim() },
      {
        onSuccess: (review) => {
          toast.success(review.status === "published" ? t("review_posted") : t("review_under_check"));
          onDone();
        },
        onError: (error) => toast.error(error.message),
      },
    );
  };

  return (
    <form onSubmit={submit} className="mt-3 space-y-4 rounded-xl border border-line bg-surface-2 p-4">
      <fieldset>
        <legend className="mb-1.5 text-sm font-medium">{t("your_rating")}</legend>
        <StarInput value={rating} onChange={setRating} />
      </fieldset>
      {sized && (
        <fieldset>
          <legend className="mb-1.5 text-sm font-medium">{t("fit_title")}</legend>
          <div className="flex flex-wrap gap-2">
            {FITS.map((value) => (
              <label
                key={value}
                className={cn(
                  "cursor-pointer rounded-full border px-3 py-1.5 text-sm transition-colors focus-within:ring-2 focus-within:ring-brand",
                  fit === value ? "border-brand bg-brand-soft font-medium text-brand" : "border-line hover:border-brand",
                )}
              >
                <input
                  type="radio"
                  name={`fit-${productId}`}
                  className="sr-only"
                  checked={fit === value}
                  onChange={() => setFit(value)}
                  onClick={() => fit === value && setFit(null)}
                />
                {t(`fit_${value}`)}
              </label>
            ))}
          </div>
        </fieldset>
      )}
      <Field id={`review-title-${productId}`} label={t("review_title_label")}>
        <Input id={`review-title-${productId}`} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={120} />
      </Field>
      <Field id={`review-body-${productId}`} label={t("review_body_label")} hint={t("review_body_hint")}>
        <Textarea
          id={`review-body-${productId}`}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder={t("review_body_placeholder")}
          maxLength={2000}
        />
      </Field>
      <Button type="submit" disabled={!valid} loading={create.isPending}>
        {create.isPending ? t("submitting") : t("submit_review")}
      </Button>
    </form>
  );
}
