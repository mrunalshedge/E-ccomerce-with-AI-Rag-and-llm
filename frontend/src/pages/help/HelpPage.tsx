import { AlertTriangle, ChevronRight, LifeBuoy, Plus } from "lucide-react";
import { Link } from "react-router-dom";

import { GrievancePriorityBadge, GrievanceStatusBadge } from "../../components/grievances/GrievanceParts";
import { buttonVariants } from "../../components/ui/button";
import { Card, EmptyState, ErrorState, Skeleton } from "../../components/ui/primitives";
import { useI18n } from "../../i18n/I18nProvider";
import type { StringKey } from "../../i18n/strings";
import { formatDate } from "../../lib/format";
import { useGrievances } from "../../lib/queries";

export function HelpPage() {
  const { t, lang } = useI18n();
  const grievances = useGrievances();

  const header = (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold">{t("help_title")}</h1>
        <p className="mt-1 max-w-xl text-sm text-muted">{t("help_subtitle")}</p>
      </div>
      <Link to="/help/new" className={buttonVariants()}>
        <Plus className="h-4 w-4" /> {t("raise_complaint")}
      </Link>
    </div>
  );

  if (grievances.isLoading) return <>{header}<Skeleton className="h-48" /></>;
  if (grievances.isError || !grievances.data) {
    return <ErrorState message={grievances.error?.message ?? t("error_generic")} onRetry={() => grievances.refetch()} retryLabel={t("retry")} />;
  }

  return (
    <div>
      {header}
      {grievances.data.length === 0 ? (
        <EmptyState icon={<LifeBuoy className="h-6 w-6" />} title={t("no_complaints")} body={t("no_complaints_hint")} />
      ) : (
        <ul className="space-y-3">
          {grievances.data.map((g) => (
            <li key={g.id}>
              <Link to={`/help/${g.id}`} className="block">
                <Card className="flex items-center gap-4 p-4 transition hover:border-brand/40">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold">{g.subject}</span>
                      <GrievanceStatusBadge status={g.status} />
                      {g.overdue && (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-danger">
                          <AlertTriangle className="h-3.5 w-3.5" /> {t("overdue")}
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-muted">
                      {t("complaint_no", { id: g.id })} · {t(`g_cat_${g.category}` as StringKey)} · {formatDate(g.created_at, lang)}
                    </p>
                  </div>
                  <GrievancePriorityBadge priority={g.priority} />
                  <ChevronRight className="h-5 w-5 text-muted" aria-hidden />
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
