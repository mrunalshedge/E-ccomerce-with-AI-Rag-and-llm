import { ShieldCheck } from "lucide-react";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { useI18n } from "../i18n/I18nProvider";
import type { StringKey } from "../i18n/strings";
import { useCreateReturn } from "../lib/queries";
import type { OrderItem, ReturnReason } from "../lib/types";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";
import { Badge, Field, Textarea } from "./ui/primitives";

const REASONS: { value: ReturnReason; guaranteed: boolean }[] = [
  { value: "wrong_item", guaranteed: true },
  { value: "counterfeit", guaranteed: true },
  { value: "damaged", guaranteed: false },
  { value: "other", guaranteed: false },
];

/** Guided return request. Wrong/fake reasons are always available; others only for returnable items. */
export function ReturnForm({ item, onDone }: { item: OrderItem; onDone: () => void }) {
  const { t } = useI18n();
  const createReturn = useCreateReturn();
  const [reason, setReason] = useState<ReturnReason | null>(null);
  const [description, setDescription] = useState("");
  const descriptionOk = description.trim().length >= 10;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!reason || !descriptionOk) return;
    createReturn.mutate(
      { orderItemId: item.id, reason, description: description.trim() },
      {
        onSuccess: () => {
          toast.success(t("return_submitted"));
          onDone();
        },
        onError: (error) => toast.error(error.message),
      },
    );
  };

  return (
    <form onSubmit={submit} className="mt-3 space-y-4 rounded-xl border border-line bg-surface-2 p-4">
      {!item.is_returnable && <p className="text-sm text-muted">{t("not_returnable_note")}</p>}
      <fieldset>
        <legend className="mb-2 text-sm font-medium">{t("return_reason")}</legend>
        <div className="grid gap-2 sm:grid-cols-2">
          {REASONS.map(({ value, guaranteed }) => {
            const allowed = guaranteed || item.is_returnable;
            const selected = reason === value;
            return (
              <label
                key={value}
                className={cn(
                  "flex items-center justify-between gap-2 rounded-xl border-2 bg-surface px-3 py-2.5 text-sm",
                  !allowed ? "cursor-not-allowed opacity-50" : "cursor-pointer",
                  selected ? "border-brand" : "border-line",
                )}
              >
                <input type="radio" name={`reason-${item.id}`} className="sr-only" disabled={!allowed} checked={selected} onChange={() => setReason(value)} />
                <span className="font-medium">{t(`reason_${value}` as StringKey)}</span>
                {guaranteed && (
                  <Badge tone="brand">
                    <ShieldCheck className="h-3 w-3" /> {t("guaranteed")}
                  </Badge>
                )}
              </label>
            );
          })}
        </div>
      </fieldset>
      <Field id={`desc-${item.id}`} label={t("describe_problem")}>
        <Textarea id={`desc-${item.id}`} value={description} onChange={(e) => setDescription(e.target.value)} placeholder={t("describe_placeholder")} maxLength={2000} />
      </Field>
      <Button type="submit" disabled={!reason || !descriptionOk} loading={createReturn.isPending}>
        {createReturn.isPending ? t("submitting") : t("submit_return")}
      </Button>
    </form>
  );
}
