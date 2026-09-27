import { AlertTriangle, ArrowLeft, CalendarClock, Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";

import { RichText } from "../../components/assistant/RichText";
import { GrievancePriorityBadge, GrievanceStatusBadge, GrievanceTimeline } from "../../components/grievances/GrievanceParts";
import { Button } from "../../components/ui/button";
import { Card, ErrorState, Skeleton, Textarea } from "../../components/ui/primitives";
import { useI18n } from "../../i18n/I18nProvider";
import type { StringKey } from "../../i18n/strings";
import { formatDate } from "../../lib/format";
import { useGrievance, useGrievanceComment, useReopenGrievance } from "../../lib/queries";

export function ComplaintPage() {
  const { t, lang } = useI18n();
  const { id } = useParams();
  const grievance = useGrievance(Number(id));
  const comment = useGrievanceComment();
  const reopen = useReopenGrievance();
  const [message, setMessage] = useState("");
  const [showReopen, setShowReopen] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  if (grievance.isLoading) return <Skeleton className="h-96" />;
  if (grievance.isError || !grievance.data) {
    return <ErrorState message={grievance.error?.message ?? t("error_generic")} onRetry={() => grievance.refetch()} retryLabel={t("retry")} />;
  }
  const g = grievance.data;
  const isOpen = g.status === "open" || g.status === "in_progress";

  const send = (e: FormEvent) => {
    e.preventDefault();
    const text = message.trim();
    if (text.length < 2) return;
    const mutation = showReopen ? reopen : comment;
    mutation.mutate(
      { id: g.id, message: text },
      {
        onSuccess: () => {
          setMessage("");
          if (showReopen) {
            toast.success(t("reopened"));
            setShowReopen(false);
          }
        },
        onError: (error) => toast.error(error.message),
      },
    );
  };

  return (
    <div className="mx-auto max-w-3xl">
      <Link to="/help" className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted hover:text-fg">
        <ArrowLeft className="h-4 w-4" /> {t("help_title")}
      </Link>

      <div className="mb-5">
        <p className="text-sm text-muted">
          {t("complaint_no", { id: g.id })} · {t(`g_cat_${g.category}` as StringKey)}
          {g.order_id && (
            <>
              {" · "}
              <Link to={`/orders/${g.order_id}`} className="hover:text-brand hover:underline">
                {t("order_no", { id: g.order_id })}
              </Link>
            </>
          )}
        </p>
        <h1 className="mt-1 text-2xl font-bold">{g.subject}</h1>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <GrievanceStatusBadge status={g.status} />
          <GrievancePriorityBadge priority={g.priority} />
          {isOpen && (
            <span className={`inline-flex items-center gap-1 text-xs ${g.overdue ? "font-semibold text-danger" : "text-muted"}`}>
              {g.overdue ? <AlertTriangle className="h-3.5 w-3.5" /> : <CalendarClock className="h-3.5 w-3.5" />}
              {g.overdue ? t("overdue") : t("resolve_by", { d: formatDate(g.resolve_by, lang) })}
            </span>
          )}
        </div>
      </div>

      {g.status === "ai_resolved" && g.ai_reply && (
        <Card className="mb-5 border-brand/30 bg-gradient-to-br from-brand-soft/60 to-surface p-5">
          <div className="mb-2 flex items-center gap-2 font-semibold">
            <Sparkles className="h-4 w-4 text-brand" aria-hidden /> {t("instant_answer")}
          </div>
          <div className="text-sm leading-relaxed">
            <RichText text={g.ai_reply} />
          </div>
          {g.can_reopen && !dismissed && !showReopen && (
            <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-4 text-sm">
              <span className="mr-1 font-medium">{t("did_this_help")}</span>
              <Button size="sm" variant="secondary" onClick={() => setDismissed(true)}>
                {t("yes_solved")}
              </Button>
              <Button size="sm" variant="outline" onClick={() => setShowReopen(true)}>
                {t("no_talk_to_person")}
              </Button>
            </div>
          )}
        </Card>
      )}

      <Card className="p-5">
        <h2 className="mb-4 font-semibold">{t("updates")}</h2>
        <div className="mb-4 rounded-xl bg-surface-2 p-3 text-sm">
          <RichText text={g.description} />
        </div>
        <GrievanceTimeline events={g.timeline} />

        {(isOpen || showReopen) && (
          <form onSubmit={send} className="mt-5 space-y-2 border-t border-line pt-4">
            <label htmlFor="message" className="text-sm font-medium">
              {showReopen ? t("no_talk_to_person") : t("add_details")}
            </label>
            <Textarea
              id="message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder={showReopen ? t("reopen_placeholder") : undefined}
              maxLength={2000}
            />
            <div className="flex gap-2">
              <Button type="submit" disabled={message.trim().length < 2} loading={comment.isPending || reopen.isPending}>
                {t("send")}
              </Button>
              {showReopen && (
                <Button type="button" variant="ghost" onClick={() => setShowReopen(false)}>
                  {t("close")}
                </Button>
              )}
            </div>
          </form>
        )}
      </Card>
    </div>
  );
}
