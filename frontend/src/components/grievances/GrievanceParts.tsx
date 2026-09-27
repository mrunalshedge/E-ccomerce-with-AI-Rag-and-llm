import { ShieldCheck, Sparkles, UserRound } from "lucide-react";

import { useI18n } from "../../i18n/I18nProvider";
import type { StringKey } from "../../i18n/strings";
import { formatDate } from "../../lib/format";
import type { GrievanceEvent, GrievancePriority, GrievanceStatus } from "../../lib/types";
import { cn } from "../../lib/utils";
import { RichText } from "../assistant/RichText";
import { Badge } from "../ui/primitives";

const STATUS_TONE = { open: "warn", in_progress: "info", ai_resolved: "brand", resolved: "brand" } as const;
const PRIORITY_TONE = { low: "neutral", medium: "info", high: "warn", urgent: "danger" } as const;

export function GrievanceStatusBadge({ status }: { status: GrievanceStatus }) {
  const { t } = useI18n();
  return <Badge tone={STATUS_TONE[status]}>{t(`g_status_${status}` as StringKey)}</Badge>;
}

export function GrievancePriorityBadge({ priority }: { priority: GrievancePriority }) {
  const { t } = useI18n();
  return <Badge tone={PRIORITY_TONE[priority]}>{t(`g_priority_${priority}` as StringKey)}</Badge>;
}

const ACTOR_STYLE = {
  customer: { icon: UserRound, className: "bg-surface-2 text-muted" },
  ai: { icon: Sparkles, className: "bg-brand-soft text-brand" },
  admin: { icon: ShieldCheck, className: "bg-info-soft text-info" },
};

/** Conversation-style timeline: who did what, when. */
export function GrievanceTimeline({ events }: { events: GrievanceEvent[] }) {
  const { t, lang } = useI18n();
  return (
    <ol className="space-y-4">
      {events.map((event, i) => {
        const { icon: Icon, className } = ACTOR_STYLE[event.actor];
        return (
          <li key={i} className="flex gap-3">
            <span className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-full", className)}>
              <Icon className="h-4 w-4" aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline gap-x-2 text-sm">
                <span className="font-semibold">{t(`actor_${event.actor}` as StringKey)}</span>
                <span className="text-xs text-muted">{formatDate(event.created_at, lang, true)}</span>
              </div>
              <div className="mt-0.5 text-sm text-fg/90">
                <RichText text={event.note} />
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
