import { ArrowLeft } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "../../components/ui/button";
import { Card, Field, Input, Textarea } from "../../components/ui/primitives";
import { useI18n } from "../../i18n/I18nProvider";
import { formatDate } from "../../lib/format";
import { useCreateGrievance, useOrders } from "../../lib/queries";

export function NewComplaintPage() {
  const { t, lang } = useI18n();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const orders = useOrders();
  const create = useCreateGrievance();
  const [orderId, setOrderId] = useState<string>(params.get("order") ?? "");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const valid = subject.trim().length >= 5 && description.trim().length >= 10;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!valid) return;
    create.mutate(
      { orderId: orderId ? Number(orderId) : null, subject: subject.trim(), description: description.trim(), language: lang },
      {
        onSuccess: (g) => {
          toast.success(t("complaint_submitted"));
          navigate(`/help/${g.id}`, { replace: true });
        },
        onError: (error) => toast.error(error.message),
      },
    );
  };

  return (
    <div className="mx-auto max-w-2xl">
      <Link to="/help" className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted hover:text-fg">
        <ArrowLeft className="h-4 w-4" /> {t("help_title")}
      </Link>
      <h1 className="mb-1 text-2xl font-bold">{t("raise_complaint")}</h1>
      <p className="mb-6 text-sm text-muted">{t("help_subtitle")}</p>

      <Card className="p-5">
        <form onSubmit={submit} className="space-y-4">
          <Field id="order" label={t("complaint_order")}>
            <select
              id="order"
              value={orderId}
              onChange={(e) => setOrderId(e.target.value)}
              className="h-11 w-full rounded-xl border border-line bg-surface px-3 text-sm focus:border-brand focus:outline-none focus:ring-4 focus:ring-ring"
            >
              <option value="">{t("complaint_no_order")}</option>
              {orders.data?.map((o) => (
                <option key={o.id} value={o.id}>
                  {t("order_no", { id: o.id })} · {o.items.map((i) => i.title).join(", ")} · {formatDate(o.created_at, lang)}
                </option>
              ))}
            </select>
          </Field>
          <Field id="subject" label={t("complaint_subject")}>
            <Input id="subject" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder={t("complaint_subject_placeholder")} maxLength={150} />
          </Field>
          <Field id="description" label={t("complaint_description")}>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("complaint_description_placeholder")}
              maxLength={3000}
              className="min-h-32"
            />
          </Field>
          <Button type="submit" size="lg" className="w-full" disabled={!valid} loading={create.isPending}>
            {create.isPending ? t("submitting") : t("submit_complaint")}
          </Button>
        </form>
      </Card>
    </div>
  );
}
