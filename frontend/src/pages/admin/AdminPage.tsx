import { AlertTriangle, CheckCircle2, ClipboardList, Gauge, IndianRupee, MessageSquareWarning, PackageOpen, RotateCcw, ShieldAlert, ShoppingBag, type LucideIcon } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { toast } from "sonner";

import { useAuth } from "../../auth/AuthProvider";
import { GrievancePriorityBadge, GrievanceStatusBadge, GrievanceTimeline } from "../../components/grievances/GrievanceParts";
import { Stars } from "../../components/reviews/Stars";
import { Button } from "../../components/ui/button";
import { Badge, Card, EmptyState, ErrorState, Skeleton, Textarea } from "../../components/ui/primitives";
import { useI18n } from "../../i18n/I18nProvider";
import type { StringKey } from "../../i18n/strings";
import { formatDate, formatINR } from "../../lib/format";
import {
  useAdminGrievances,
  useAdminOverview,
  useAdminReturns,
  useAdminReviews,
  useAdminUpdateGrievance,
  useModerateReview,
  useResolveReturn,
} from "../../lib/queries";
import { cn } from "../../lib/utils";

// ---------- shared ----------

/** A required note plus action buttons (every admin decision is explained to the customer). */
function DecisionBox({
  actions,
  pending,
}: {
  actions: { label: string; variant?: "primary" | "outline" | "danger"; onRun: (note: string) => Promise<unknown> }[];
  pending: boolean;
}) {
  const { t } = useI18n();
  const [note, setNote] = useState("");
  const ok = note.trim().length >= 3;
  return (
    <div className="mt-4 space-y-2 border-t border-line pt-4">
      <Textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder={t("admin_note_placeholder")} className="min-h-16" maxLength={2000} />
      <div className="flex flex-wrap gap-2">
        {actions.map((a) => (
          <Button
            key={a.label}
            size="sm"
            variant={a.variant ?? "primary"}
            disabled={!ok}
            loading={pending}
            onClick={() =>
              a.onRun(note.trim()).then(
                () => {
                  toast.success(t("admin_updated"));
                  setNote("");
                },
                (error: Error) => toast.error(error.message),
              )
            }
          >
            {a.label}
          </Button>
        ))}
      </div>
    </div>
  );
}

function QueueState({ loading, error, empty, retry }: { loading: boolean; error?: Error | null; empty: boolean; retry: () => void }) {
  const { t } = useI18n();
  if (loading) return <Skeleton className="h-40" />;
  if (error) return <ErrorState message={error.message} onRetry={retry} retryLabel={t("retry")} />;
  if (empty) return <EmptyState icon={<CheckCircle2 className="h-6 w-6" />} title={t("admin_all_clear")} />;
  return null;
}

// ---------- overview ----------

function Stat({ icon: Icon, label, value, tone, to }: { icon: LucideIcon; label: string; value: ReactNode; tone?: "danger" | "warn"; to?: string }) {
  const body = (
    <Card className={cn("p-4 transition", to && "hover:border-brand/40")}>
      <div className="flex items-center gap-2 text-sm text-muted">
        <Icon className={cn("h-4 w-4", tone === "danger" ? "text-danger" : tone === "warn" ? "text-warn" : "text-brand")} aria-hidden />
        {label}
      </div>
      <div className={cn("mt-2 text-3xl font-bold tabular", tone === "danger" && "text-danger")}>{value}</div>
    </Card>
  );
  return to ? <Link to={to}>{body}</Link> : body;
}

function OverviewTab() {
  const { t } = useI18n();
  const overview = useAdminOverview();
  if (overview.isLoading || !overview.data) {
    return <QueueState loading={overview.isLoading} error={overview.error} empty={false} retry={() => overview.refetch()} />;
  }
  const o = overview.data;
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <Stat icon={MessageSquareWarning} label={t("admin_open_complaints")} value={o.open_grievances} to="/admin/complaints" />
      <Stat icon={AlertTriangle} label={t("admin_urgent")} value={o.urgent_or_high} tone={o.urgent_or_high ? "warn" : undefined} to="/admin/complaints" />
      <Stat icon={ClipboardList} label={t("admin_overdue")} value={o.overdue_grievances} tone={o.overdue_grievances ? "danger" : undefined} to="/admin/complaints" />
      <Stat icon={ShieldAlert} label={t("admin_flagged_reviews")} value={o.flagged_reviews} tone={o.flagged_reviews ? "warn" : undefined} to="/admin/reviews" />
      <Stat icon={RotateCcw} label={t("admin_pending_returns")} value={o.pending_returns} to="/admin/returns" />
      <Stat icon={ShoppingBag} label={t("admin_orders_today")} value={o.orders_today} />
      <Stat icon={IndianRupee} label={t("admin_revenue_today")} value={formatINR(o.revenue_today)} />
    </div>
  );
}

// ---------- complaints ----------

function ComplaintsTab() {
  const { t, lang } = useI18n();
  const queue = useAdminGrievances();
  const update = useAdminUpdateGrievance();
  const [open, setOpen] = useState<number | null>(null);
  const state = <QueueState loading={queue.isLoading} error={queue.error} empty={!queue.data?.length} retry={() => queue.refetch()} />;
  if (!queue.data?.length) return state;

  return (
    <ul className="space-y-3">
      {queue.data.map((g) => (
        <li key={g.id}>
          <Card className="p-4">
            <button className="flex w-full flex-wrap items-center gap-2 text-left" onClick={() => setOpen(open === g.id ? null : g.id)} aria-expanded={open === g.id}>
              <GrievancePriorityBadge priority={g.priority} />
              <span className="font-semibold">{g.subject}</span>
              <GrievanceStatusBadge status={g.status} />
              <span className="ml-auto text-xs text-muted">
                #{g.id} · {t(`g_cat_${g.category}` as StringKey)} ·{" "}
                <span className={g.overdue ? "font-semibold text-danger" : undefined}>
                  {g.overdue ? t("overdue") : t("resolve_by", { d: formatDate(g.resolve_by, lang) })}
                </span>
              </span>
            </button>
            {g.ai_summary && <p className="mt-2 text-sm text-muted">{t("admin_ai_summary")}: {g.ai_summary}</p>}

            {open === g.id && (
              <div className="mt-4">
                <p className="text-sm">
                  <span className="text-muted">{t("admin_customer")}:</span> {g.customer_name} · {g.customer_email}
                  {g.order_id && <> · {t("order_no", { id: g.order_id })}</>}
                </p>
                <Badge className="mt-2">{g.triaged_by === "ai" ? t("admin_triaged_by_ai") : t("admin_triaged_by_rules")}</Badge>
                <div className="mt-3 rounded-xl bg-surface-2 p-3 text-sm whitespace-pre-line">{g.description}</div>
                <div className="mt-4">
                  <GrievanceTimeline events={g.timeline} />
                </div>
                <DecisionBox
                  pending={update.isPending}
                  actions={[
                    ...(g.status !== "in_progress"
                      ? [{ label: t("admin_mark_in_progress"), variant: "outline" as const, onRun: (note: string) => update.mutateAsync({ id: g.id, status: "in_progress", note }) }]
                      : []),
                    { label: t("admin_resolve"), onRun: (note: string) => update.mutateAsync({ id: g.id, status: "resolved", note }) },
                  ]}
                />
              </div>
            )}
          </Card>
        </li>
      ))}
    </ul>
  );
}

// ---------- reviews ----------

function ReviewsTab() {
  const { t, lang } = useI18n();
  const queue = useAdminReviews();
  const moderate = useModerateReview();
  const state = <QueueState loading={queue.isLoading} error={queue.error} empty={!queue.data?.length} retry={() => queue.refetch()} />;
  if (!queue.data?.length) return state;

  return (
    <ul className="space-y-3">
      {queue.data.map((r) => (
        <li key={r.id}>
          <Card className="p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Stars value={r.rating} />
              <span className="font-semibold">{r.product_title}</span>
              <Badge tone="warn" className="ml-auto">{t("admin_suspicion", { s: r.suspicion_score.toFixed(2) })}</Badge>
            </div>
            <p className="mt-2 text-sm">“{r.body}”</p>
            <p className="mt-1 text-xs text-muted">
              {r.reviewer} · {formatDate(r.created_at, lang, true)}
            </p>
            <div className="mt-3">
              <p className="text-xs font-medium uppercase tracking-wide text-muted">{t("admin_why_flagged")}</p>
              <ul className="mt-1 flex flex-wrap gap-1.5">
                {r.suspicion_reasons.map((reason) => (
                  <li key={reason}>
                    <Badge tone="danger">{t(`reason_${reason}` as StringKey)}</Badge>
                  </li>
                ))}
              </ul>
            </div>
            <DecisionBox
              pending={moderate.isPending}
              actions={[
                { label: t("admin_approve"), variant: "outline", onRun: (note) => moderate.mutateAsync({ id: r.id, action: "approve", note }) },
                { label: t("admin_remove"), variant: "danger", onRun: (note) => moderate.mutateAsync({ id: r.id, action: "remove", note }) },
              ]}
            />
          </Card>
        </li>
      ))}
    </ul>
  );
}

// ---------- returns ----------

function ReturnsTab() {
  const { t, lang } = useI18n();
  const queue = useAdminReturns();
  const resolve = useResolveReturn();
  const state = <QueueState loading={queue.isLoading} error={queue.error} empty={!queue.data?.length} retry={() => queue.refetch()} />;
  if (!queue.data?.length) return state;

  return (
    <ul className="space-y-3">
      {queue.data.map((r) => (
        <li key={r.id}>
          <Card className="p-4">
            <div className="flex flex-wrap items-center gap-2">
              <PackageOpen className="h-4 w-4 text-muted" aria-hidden />
              <span className="font-semibold">{r.product_title}</span>
              <Badge tone={r.reason === "wrong_item" || r.reason === "counterfeit" ? "danger" : "neutral"}>
                {t(`reason_${r.reason}` as StringKey)}
              </Badge>
              {r.exchange_size && <Badge tone="brand">{t("exchange_label", { s: r.exchange_size })}</Badge>}
              <span className="ml-auto text-sm font-semibold tabular">{t("admin_refund", { amt: formatINR(r.refund_amount) })}</span>
            </div>
            <p className="mt-2 text-sm">“{r.description}”</p>
            <p className="mt-1 text-xs text-muted">
              {t("order_no", { id: r.order_id })} · {formatDate(r.created_at, lang, true)}
            </p>
            <DecisionBox
              pending={resolve.isPending}
              actions={[
                { label: t("admin_approve"), onRun: (note) => resolve.mutateAsync({ id: r.id, decision: "approve", note }) },
                { label: t("admin_reject"), variant: "danger", onRun: (note) => resolve.mutateAsync({ id: r.id, decision: "reject", note }) },
              ]}
            />
          </Card>
        </li>
      ))}
    </ul>
  );
}

// ---------- layout ----------

const TABS: { to: string; label: StringKey; icon: LucideIcon }[] = [
  { to: "/admin", label: "admin_overview", icon: Gauge },
  { to: "/admin/complaints", label: "admin_complaints", icon: MessageSquareWarning },
  { to: "/admin/reviews", label: "admin_reviews", icon: ShieldAlert },
  { to: "/admin/returns", label: "admin_returns", icon: RotateCcw },
];

export function AdminPage() {
  const { t } = useI18n();
  const { user, isLoading } = useAuth();
  if (isLoading) return <Skeleton className="h-64" />;
  if (!user) return <Navigate to="/login" replace state={{ from: "/admin" }} />;
  if (user.role !== "admin") return <p className="rounded-2xl bg-info-soft p-5 text-info">{t("admin_only")}</p>;

  return (
    <div>
      <h1 className="mb-4 text-2xl font-bold">{t("admin_panel")}</h1>
      <nav className="-mx-4 mb-6 flex gap-1 overflow-x-auto border-b border-line px-4" aria-label={t("admin_panel")}>
        {TABS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end
            className={({ isActive }) =>
              cn(
                "flex shrink-0 items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium transition",
                isActive ? "border-brand text-brand" : "border-transparent text-muted hover:text-fg",
              )
            }
          >
            <Icon className="h-4 w-4" aria-hidden /> {t(label)}
          </NavLink>
        ))}
      </nav>
      <Routes>
        <Route index element={<OverviewTab />} />
        <Route path="complaints" element={<ComplaintsTab />} />
        <Route path="reviews" element={<ReviewsTab />} />
        <Route path="returns" element={<ReturnsTab />} />
      </Routes>
    </div>
  );
}
