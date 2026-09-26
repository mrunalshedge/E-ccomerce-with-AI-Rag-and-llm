import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";

import { useI18n } from "../../i18n/I18nProvider";
import { AssistantWidget } from "../assistant/AssistantWidget";
import { Header, Logo } from "./Header";

export function Layout() {
  const { t } = useI18n();
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return (
    <div className="flex min-h-dvh flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-3 focus:py-2">
        Skip to content
      </a>
      <Header />
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:py-8">
        <Outlet />
      </main>
      <footer className="border-t border-line bg-surface">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-6 text-sm text-muted sm:flex-row sm:items-center sm:justify-between">
          <Logo />
          <p>{t("footer_note")}</p>
        </div>
      </footer>
      <AssistantWidget />
    </div>
  );
}
