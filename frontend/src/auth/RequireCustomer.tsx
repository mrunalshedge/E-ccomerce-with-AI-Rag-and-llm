import { LoaderCircle } from "lucide-react";
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useI18n } from "../i18n/I18nProvider";
import { useAuth } from "./AuthProvider";

/** Customer-only pages: logged-out users go to login and come back afterwards. */
export function RequireCustomer({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const { t } = useI18n();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex justify-center py-20 text-muted" aria-live="polite">
        <LoaderCircle className="h-6 w-6 animate-spin" aria-label={t("loading")} />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (user.role !== "customer") {
    return <p className="rounded-2xl bg-info-soft p-5 text-info">{t("sellers_cannot_buy")}</p>;
  }
  return <>{children}</>;
}
