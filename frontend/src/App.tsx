import { SearchX } from "lucide-react";
import { Link, Route, Routes } from "react-router-dom";

import { RequireCustomer } from "./auth/RequireCustomer";
import { Layout } from "./components/layout/Layout";
import { buttonVariants } from "./components/ui/button";
import { EmptyState } from "./components/ui/primitives";
import { useI18n } from "./i18n/I18nProvider";
import { LoginPage, RegisterPage } from "./pages/AuthPages";
import { CartPage } from "./pages/CartPage";
import { CheckoutPage } from "./pages/CheckoutPage";
import { HomePage } from "./pages/HomePage";
import { OrderDetailPage } from "./pages/OrderDetailPage";
import { OrdersPage } from "./pages/OrdersPage";
import { ProductPage } from "./pages/ProductPage";
import { ReturnsPage } from "./pages/ReturnsPage";

function NotFound() {
  const { t } = useI18n();
  return (
    <EmptyState
      icon={<SearchX className="h-6 w-6" />}
      title={t("not_found")}
      action={<Link to="/" className={buttonVariants()}>{t("go_home")}</Link>}
    />
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="products/:id" element={<ProductPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="cart" element={<RequireCustomer><CartPage /></RequireCustomer>} />
        <Route path="checkout" element={<RequireCustomer><CheckoutPage /></RequireCustomer>} />
        <Route path="orders" element={<RequireCustomer><OrdersPage /></RequireCustomer>} />
        <Route path="orders/:id" element={<RequireCustomer><OrderDetailPage /></RequireCustomer>} />
        <Route path="returns" element={<RequireCustomer><ReturnsPage /></RequireCustomer>} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
