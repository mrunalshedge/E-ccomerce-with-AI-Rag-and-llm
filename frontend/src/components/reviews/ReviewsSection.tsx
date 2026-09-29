import { BadgeCheck, MessageSquareText, ShieldAlert, Sparkles } from "lucide-react";
import { useState } from "react";

import { useI18n } from "../../i18n/I18nProvider";
import { formatDate } from "../../lib/format";
import { useReviewSummary, useReviews } from "../../lib/queries";
import type { ReviewSort } from "../../lib/types";
import { RichText } from "../assistant/RichText";
import { Button } from "../ui/button";
import { Badge, Card, Skeleton } from "../ui/primitives";
import { Stars } from "./Stars";

const PAGE_SIZE = 5;

function Distribution({ distribution, count }: { distribution: Record<string, number>; count: number }) {
  return (
    <div className="space-y-1.5">
      {[5, 4, 3, 2, 1].map((stars) => {
        const n = distribution[String(stars)] ?? 0;
        const pct = count ? Math.round((n / count) * 100) : 0;
        return (
          <div key={stars} className="flex items-center gap-2 text-xs">
            <span className="w-3 tabular text-muted">{stars}</span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-2" aria-hidden>
              <div className="h-full rounded-full bg-amber-500" style={{ width: `${pct}%` }} />
            </div>
            <span className="w-8 text-right tabular text-muted">{n}</span>
          </div>
        );
      })}
    </div>
  );
}

function AiSummary({ productId }: { productId: number }) {
  const { t, lang } = useI18n();
  const summary = useReviewSummary(productId, lang, true);
  if (summary.isLoading) {
    return (
      <Card className="p-5">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="mt-3 h-16" />
      </Card>
    );
  }
  if (!summary.data || summary.data.status !== "ready" || !summary.data.summary) return null;
  return (
    <Card className="border-brand/30 bg-gradient-to-br from-brand-soft/60 to-surface p-5">
      <div className="mb-2 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-brand" aria-hidden />
        <h3 className="font-semibold">{t("ai_summary_title")}</h3>
        <Badge tone="brand" className="ml-auto">
          {t("ai_summary_based", { n: summary.data.review_count })}
        </Badge>
      </div>
      <div className="text-sm leading-relaxed">
        <RichText text={summary.data.summary} />
      </div>
      <p className="mt-3 text-xs text-muted">{t("ai_summary_disclaimer")}</p>
    </Card>
  );
}

/** Ratings, AI summary and every published verified review (good and bad). */
export function ReviewsSection({ productId }: { productId: number }) {
  const { t, lang } = useI18n();
  const [sort, setSort] = useState<ReviewSort>("recent");
  const [pageSize, setPageSize] = useState(PAGE_SIZE);
  const reviews = useReviews(productId, sort, pageSize);

  if (reviews.isLoading) return <Skeleton className="h-48" />;
  if (!reviews.data) return null;
  const { items, total, stats } = reviews.data;

  return (
    <section aria-labelledby="reviews-heading" className="space-y-5">
      <h2 id="reviews-heading" className="text-xl font-semibold">
        {t("reviews_title")}
      </h2>

      {stats.count === 0 ? (
        <Card className="flex items-center gap-3 p-5 text-sm">
          <MessageSquareText className="h-5 w-5 text-muted" aria-hidden />
          <div>
            <p className="font-medium">{t("no_reviews_yet")}</p>
            <p className="text-muted">{t("no_reviews_hint")}</p>
          </div>
        </Card>
      ) : (
        <Card className="grid gap-5 p-5 sm:grid-cols-[auto_1fr] sm:items-center sm:gap-8">
          <div className="text-center sm:text-left">
            <div className="text-4xl font-bold tabular">{stats.average?.toFixed(1)}</div>
            <Stars value={stats.average ?? 0} size="md" />
            <p className="mt-1 text-sm text-muted">{t("reviews_count", { n: stats.count })}</p>
          </div>
          <Distribution distribution={stats.distribution} count={stats.count} />
        </Card>
      )}

      {stats.under_review > 0 && (
        <p className="flex items-start gap-2 text-sm text-muted">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-warn" aria-hidden />
          {t("under_review_note", { n: stats.under_review })}
        </p>
      )}

      <AiSummary productId={productId} />

      {items.length > 0 && (
        <div>
          <div className="mb-3 flex items-center justify-end gap-2 text-sm">
            <label htmlFor="review-sort" className="text-muted">
              {t("sort_by")}
            </label>
            <select
              id="review-sort"
              value={sort}
              onChange={(e) => setSort(e.target.value as ReviewSort)}
              className="h-9 rounded-lg border border-line bg-surface px-2 text-sm focus:border-brand focus:outline-none"
            >
              <option value="recent">{t("sort_recent")}</option>
              <option value="highest">{t("sort_highest")}</option>
              <option value="lowest">{t("sort_lowest")}</option>
            </select>
          </div>
          <ul className="divide-y divide-line rounded-2xl border border-line bg-surface">
            {items.map((r) => (
              <li key={r.id} className="p-4">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <Stars value={r.rating} />
                  {r.title && <span className="font-semibold">{r.title}</span>}
                </div>
                <p className="mt-1.5 whitespace-pre-line text-sm leading-relaxed">{r.body}</p>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted">
                  <span className="font-medium text-fg">{r.reviewer}</span>
                  <span>·</span>
                  <span>{formatDate(r.created_at, lang)}</span>
                  <Badge tone="brand">
                    <BadgeCheck className="h-3 w-3" aria-hidden /> {t("verified_purchase")}
                  </Badge>
                  {r.fit && <Badge>{t(`fit_${r.fit}`)}</Badge>}
                </div>
              </li>
            ))}
          </ul>
          {total > items.length && (
            <Button variant="outline" className="mt-3 w-full" onClick={() => setPageSize((n) => n + PAGE_SIZE)} loading={reviews.isFetching}>
              {t("show_more_reviews")}
            </Button>
          )}
        </div>
      )}
    </section>
  );
}
