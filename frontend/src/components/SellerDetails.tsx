import { BadgeCheck, Mail, MapPin, Phone, Receipt, UserRound } from "lucide-react";
import type { ReactNode } from "react";

import { useI18n } from "../i18n/I18nProvider";
import type { SellerCard } from "../lib/types";
import { TrustMeter } from "./TrustScore";
import { Card } from "./ui/primitives";

function Detail({ icon, label, children }: { icon: ReactNode; label: string; children: ReactNode }) {
  return (
    <div className="flex gap-3">
      <span className="mt-0.5 text-muted">{icon}</span>
      <div className="min-w-0">
        <div className="text-xs text-muted">{label}</div>
        <div className="break-words text-sm">{children}</div>
      </div>
    </div>
  );
}

/** Full seller disclosure shown on every product page (addresses "hidden seller details"). */
export function SellerDetails({ seller }: { seller: SellerCard }) {
  const { t } = useI18n();
  return (
    <Card className="p-5">
      <div className="flex items-center gap-2">
        <BadgeCheck className="h-5 w-5 text-brand" aria-hidden />
        <h2 className="font-semibold">{t("seller_details")}</h2>
      </div>
      <p className="mt-1 text-lg font-semibold">{seller.business_name}</p>

      <div className="mt-4">
        <TrustMeter score={seller.trust_score} label={t("trust_score")} help={t("trust_score_help")} />
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        <Detail icon={<MapPin className="h-4 w-4" />} label={t("address")}>
          {seller.address}
        </Detail>
        {seller.gstin && (
          <Detail icon={<Receipt className="h-4 w-4" />} label={t("gstin")}>
            <span className="font-mono">{seller.gstin}</span>
          </Detail>
        )}
        <Detail icon={<Phone className="h-4 w-4" />} label={t("contact")}>
          <a className="hover:text-brand" href={`tel:${seller.phone}`}>
            {seller.phone}
          </a>
          <br />
          <a className="hover:text-brand" href={`mailto:${seller.contact_email}`}>
            {seller.contact_email}
          </a>
        </Detail>
        <Detail icon={<UserRound className="h-4 w-4" />} label={t("grievance_officer")}>
          {seller.grievance_officer_name}
          <br />
          <a className="inline-flex items-center gap-1 hover:text-brand" href={`mailto:${seller.grievance_officer_email}`}>
            <Mail className="h-3.5 w-3.5" aria-hidden />
            {seller.grievance_officer_email}
          </a>
        </Detail>
      </div>
    </Card>
  );
}
