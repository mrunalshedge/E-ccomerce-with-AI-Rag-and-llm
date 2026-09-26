import "./index.css";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "sonner";

import App from "./App";
import { AuthProvider } from "./auth/AuthProvider";
import { I18nProvider } from "./i18n/I18nProvider";
import { ApiError } from "./lib/api";
import { ThemeProvider, useTheme } from "./theme/ThemeProvider";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // Don't retry client errors (404, 403…); retry network/server hiccups once.
      retry: (count, error) => !(error instanceof ApiError && error.status >= 400 && error.status < 500) && count < 1,
    },
  },
});

function ThemedToaster() {
  const { theme } = useTheme();
  return <Toaster theme={theme} position="top-center" richColors closeButton />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <I18nProvider>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <AuthProvider>
              <App />
              <ThemedToaster />
            </AuthProvider>
          </BrowserRouter>
        </QueryClientProvider>
      </I18nProvider>
    </ThemeProvider>
  </StrictMode>,
);
