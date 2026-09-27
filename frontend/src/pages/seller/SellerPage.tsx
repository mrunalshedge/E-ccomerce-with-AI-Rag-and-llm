import { AlertTriangle, BadgeCheck, IndianRupee, LayoutDashboard, MessageSquareText, Package, PackageCheck, Pencil, Plus, RotateCcw, Star, Store, Truck, type LucideIcon } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";
import { Link, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { toast } from "sonner";

import { useAuth } from "../../auth/AuthProvider";
import { ProductImage } from "../../components/ProductImage";
import { Stars } from "../../components/reviews/Stars";
import { ProductForm } from "../../components/seller/ProductForm";
import { OrderStatusBadge, PaymentStatusBadge, ReturnStatusBadge } from "../../components/StatusBadges";
import { TrustMeter } from "../../components/TrustScore";
import { Button } from "../../components/ui/button";
import { Badge, Card, EmptyState, ErrorState, Field, Input, Skeleton, Textarea } from "../../components/ui/primitives";
import { useI18n } from "../../i18n/I18nProvider";
import type { StringKey } from "../../i18n/strings";
import { formatDate, formatINR } from "../../lib/format";
import {
  useCreateProduct,
  useCreateSellerProfile,
  useSellerDashboard,
  useSellerOrders,
  useSellerProducts,
  useSellerProfile,
  useSellerReturns,
  useSellerReviews,
  useUpdateOrderStatus,
  useUpdateProduct,
} from "../../lib/queries";
import type { Order, SellerProfileInput } from "../../lib/types";
import { cn } from "../../lib/utils";

function Loading({ error, retry }: { error?: Error | null; retry: () => void }) {
  const { t } = useI18n();
  return error ? <ErrorState message={error.message} onRetry={retry} retryLabel={t("retry")} /> : <Skeleton className="h-48" />;
}

// ---------- onboarding ----------

function Onboarding() {
  const { t } = useI18n();
  const create = useCreateSellerProfile();
  const [form, setForm] = useState<SellerProfileInput>({
    business_name: "",
    contact_email: "",
    phone: "",
    address: "",
    gstin: null,
    grievance_officer_name: "",
    grievance_officer_email: "",
  });
  const field = (key: keyof SellerProfileInput, label: StringKey, type = "text") => (
    <Field id={key} label={t(label)}>
      <Input id={key} type={type} value={form[key] ?? ""} onChange={(e) => setForm({ ...form, [key]: e.target.value })} />
    </Field>
  );
  const submit = (e: FormEvent) => {
    e.preventDefault();
    create.mutate(
      { ...form, gstin: form.gstin?.trim() || null },
      { onSuccess: () => toast.success(t("seller_saved")), onError: (error) => toast.error(error.message) },
    );
  };
  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-5 flex items-center gap-3">
        <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand text-on-brand">
          <Store className="h-6 w-6" aria-hidden />
        </span>
        <div>
          <h1 className="text-2xl font-bold">{t("seller_onboarding_title")}</h1>
          <p className="text-sm text-muted">{t("seller_onboarding_body")}</p>
        </div>
      </div>
      <Card className="p-5">
        <form onSubmit={submit} className="space-y-4">
          {field("business_name", "seller_business_name")}
          <div className="grid gap-4 sm:grid-cols-2">
            {field("contact_email", "seller_contact_email", "email")}
            {field("phone", "seller_phone", "tel")}
          </div>
          <Field id="address" label={t("seller_address")}>
            <Textarea id="address" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          </Field>
          {field("gstin", "seller_gstin")}
          <div className="grid gap-4 sm:grid-cols-2">
            {field("grievance_officer_name", "seller_grievance_name")}
            {field("grievance_officer_email", "seller_grievance_email", "email")}
          </div>
          <Button type="submit" size="lg" className="w-full" loading={create.isPending}>
            {t("seller_create_profile")}
          </Button>
        </form>
      </Card>
    </div>
  );
}

// ---------- overview ----------

function Stat({ icon: Icon, label, value, tone, to }: { icon: LucideIcon; label: string; value: ReactNode; tone?: "warn"; to?: string }) {
  const body = (
    <Card className={cn("p-4", to && "transition hover:border-brand/40")}>
      <div className="flex items-center gap-2 text-sm text-muted">
        <Icon className={cn("h-4 w-4", tone === "warn" ? "text-warn" : "text-brand")} aria-hidden /> {label}
      </div>
      <div className="mt-2 text-2xl font-bold tabular">{value}</div>
    </Card>
  );
  return to ? <Link to={to}>{body}</Link> : body;
}

function OverviewTab() {
  const { t } = useI18n();
  const dash = useSellerDashboard();
  if (!dash.data) return <Loading error={dash.error} retry={() => dash.refetch()} />;
  const d = dash.data;
  const trust = d.trust;
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-4 lg:self-start">
        <Stat icon={Package} label={t("seller_to_ship")} value={d.to_ship} tone={d.to_ship ? "warn" : undefined} to="/seller/orders" />
        <Stat icon={Truck} label={t("seller_in_transit")} value={d.in_transit} to="/seller/orders" />
        <Stat icon={PackageCheck} label={t("seller_delivered_30d")} value={d.delivered_30d} />
        <Stat icon={IndianRupee} label={t("seller_revenue_30d")} value={formatINR(d.revenue_30d)} />
        <Stat icon={RotateCcw} label={t("seller_open_returns")} value={d.open_returns} tone={d.open_returns ? "warn" : undefined} to="/seller/feedback" />
        <Stat icon={AlertTriangle} label={t("seller_low_stock")} value={`${d.low_stock} / ${d.products}`} tone={d.low_stock ? "warn" : undefined} to="/seller/products" />
        <Stat icon={Star} label={t("seller_rating")} value={d.average_rating ? `${d.average_rating.toFixed(1)}★ (${d.review_count})` : "—"} to="/seller/feedback" />
      </div>
      <Card className="p-5">
        <h2 className="mb-1 flex items-center gap-2 font-semibold">
          <BadgeCheck className="h-5 w-5 text-brand" aria-hidden /> {t("seller_trust_title")}
        </h2>
        <p className="mb-4 text-xs text-muted">{t("seller_trust_explainer")}</p>
        <TrustMeter score={trust.score} label={t("trust_score")} help="" />
        <dl className="mt-4 space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-muted">{t("seller_trust_returns", { n: trust.wrong_or_fake_returns })}</dt>
            <dd className="tabular">−{trust.return_penalty}</dd>
          </div>
          <div className="flex justify-between gap-3">
            <dt className="text-muted">
              {trust.review_count >= trust.min_reviews_for_rating_penalty
                ? t("seller_trust_rating", { target: trust.rating_target, min: trust.min_reviews_for_rating_penalty })
                : t("seller_trust_rating_pending", { min: trust.min_reviews_for_rating_penalty, n: trust.review_count })}
            </dt>
            <dd className="tabular">−{trust.rating_penalty}</dd>
          </div>
        </dl>
      </Card>
    </div>
  );
}

// ---------- products ----------

function ProductsTab() {
  const { t } = useI18n();
  const products = useSellerProducts();
  const create = useCreateProduct();
  const update = useUpdateProduct();
  const [editing, setEditing] = useState<number | "new" | null>(null);
  if (!products.data) return <Loading error={products.error} retry={() => products.refetch()} />;

  if (editing !== null) {
    const product = editing === "new" ? undefined : products.data.find((p) => p.id === editing);
    return (
      <Card className="p-5">
        <h2 className="mb-4 text-lg font-semibold">{product ? t("seller_edit_product") : t("seller_add_product")}</h2>
        <ProductForm
          product={product}
          pending={create.isPending || update.isPending}
          onCancel={() => setEditing(null)}
          onSubmit={(input) => {
            const done = { onSuccess: () => { toast.success(product ? t("seller_saved") : t("seller_published")); setEditing(null); }, onError: (e: Error) => toast.error(e.message) };
            if (product) update.mutate({ id: product.id, changes: input }, done);
            else create.mutate(input, done);
          }}
        />
      </Card>
    );
  }

  return (
    <div>
      <div className="mb-4 flex justify-end">
        <Button onClick={() => setEditing("new")}>
          <Plus className="h-4 w-4" /> {t("seller_add_product")}
        </Button>
      </div>
      {products.data.length === 0 ? (
        <EmptyState icon={<Package className="h-6 w-6" />} title={t("seller_no_products")} />
      ) : (
        <ul className="space-y-3">
          {products.data.map((p) => (
            <li key={p.id}>
              <Card className="flex items-center gap-4 p-3">
                <div className="w-16 shrink-0">
                  <ProductImage src={p.image_url} title={p.title} category={p.category} />
                </div>
                <div className="min-w-0 flex-1">
                  <Link to={`/products/${p.id}`} className="block truncate font-semibold hover:text-brand">
                    {p.title}
                  </Link>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
                    <span className="font-semibold text-fg tabular">{formatINR(p.price.final_price)}</span>
                    <Badge tone={p.stock === 0 ? "danger" : p.stock <= 5 ? "warn" : "neutral"}>{t("seller_stock_left", { n: p.stock })}</Badge>
                    {p.rating.count > 0 && p.rating.average !== null && (
                      <span className="inline-flex items-center gap-1">
                        <Stars value={p.rating.average} /> ({p.rating.count})
                      </span>
                    )}
                  </div>
                </div>
                <Button variant="outline" size="sm" onClick={() => setEditing(p.id)} aria-label={`${t("seller_edit_product")}: ${p.title}`}>
                  <Pencil className="h-4 w-4" /> <span className="hidden sm:inline">{t("seller_edit_product")}</span>
                </Button>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------- orders ----------

const NEXT: Partial<Record<Order["status"], "shipped" | "delivered">> = { placed: "shipped", shipped: "delivered" };
const STATUS_ORDER: Record<Order["status"], number> = { placed: 0, shipped: 1, delivered: 2, cancelled: 3 };

function OrdersTab() {
  const { t, lang } = useI18n();
  const orders = useSellerOrders();
  const update = useUpdateOrderStatus();
  if (!orders.data) return <Loading error={orders.error} retry={() => orders.refetch()} />;
  if (orders.data.length === 0) return <EmptyState icon={<Package className="h-6 w-6" />} title={t("seller_no_orders")} />;
  const sorted = [...orders.data].sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status] || a.id - b.id);

  return (
    <ul className="space-y-3">
      {sorted.map((o) => {
        const next = NEXT[o.status];
        return (
          <li key={o.id}>
            <Card className="p-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">{t("order_no", { id: o.id })}</span>
                <OrderStatusBadge status={o.status} />
                <PaymentStatusBadge status={o.payment_status} />
                <span className="ml-auto font-bold tabular">{formatINR(o.totals.grand_total)}</span>
              </div>
              <p className="mt-1 text-sm">{o.items.map((i) => `${i.title} × ${i.quantity}`).join(", ")}</p>
              <p className="mt-1 text-xs text-muted">
                {formatDate(o.created_at, lang, true)} · {t("seller_ship_to")}: {o.shipping_address}
              </p>
              {next && (
                <Button
                  size="sm"
                  className="mt-3"
                  loading={update.isPending && update.variables?.id === o.id}
                  onClick={() =>
                    update.mutate(
                      { id: o.id, status: next },
                      { onSuccess: () => toast.success(t("seller_status_updated")), onError: (e) => toast.error(e.message) },
                    )
                  }
                >
                  {next === "shipped" ? <Truck className="h-4 w-4" /> : <PackageCheck className="h-4 w-4" />}
                  {next === "shipped" ? t("seller_mark_shipped") : t("seller_mark_delivered")}
                </Button>
              )}
            </Card>
          </li>
        );
      })}
    </ul>
  );
}

// ---------- returns & reviews ----------

function FeedbackTab() {
  const { t, lang } = useI18n();
  const returns = useSellerReturns();
  const reviews = useSellerReviews();
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section>
        <h2 className="mb-3 font-semibold">{t("seller_returns")}</h2>
        {!returns.data ? (
          <Loading error={returns.error} retry={() => returns.refetch()} />
        ) : returns.data.length === 0 ? (
          <Card className="p-4 text-sm text-muted">{t("seller_no_returns")}</Card>
        ) : (
          <ul className="space-y-3">
            {returns.data.map((r) => (
              <li key={r.id}>
                <Card className="p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold">{r.product_title}</span>
                    <ReturnStatusBadge status={r.status} />
                  </div>
                  <p className="mt-1 text-xs text-muted">
                    {t(`reason_${r.reason}` as StringKey)} · {t("order_no", { id: r.order_id })} · {formatDate(r.created_at, lang)}
                  </p>
                  <p className="mt-2 text-sm">“{r.description}”</p>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section>
        <h2 className="mb-3 font-semibold">{t("seller_reviews")}</h2>
        {!reviews.data ? (
          <Loading error={reviews.error} retry={() => reviews.refetch()} />
        ) : reviews.data.length === 0 ? (
          <Card className="p-4 text-sm text-muted">{t("seller_no_reviews")}</Card>
        ) : (
          <ul className="space-y-3">
            {reviews.data.map((r) => (
              <li key={r.id}>
                <Card className="p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Stars value={r.rating} />
                    <Link to={`/products/${r.product_id}`} className="text-sm font-semibold hover:text-brand">
                      {r.product_title}
                    </Link>
                  </div>
                  <p className="mt-1.5 text-sm">{r.body}</p>
                  <p className="mt-1 text-xs text-muted">
                    {r.reviewer} · {formatDate(r.created_at, lang)}
                  </p>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

// ---------- layout ----------

const TABS: { to: string; label: StringKey; icon: LucideIcon }[] = [
  { to: "/seller", label: "seller_tab_overview", icon: LayoutDashboard },
  { to: "/seller/products", label: "seller_tab_products", icon: Package },
  { to: "/seller/orders", label: "seller_tab_orders", icon: Truck },
  { to: "/seller/feedback", label: "seller_tab_feedback", icon: MessageSquareText },
];

export function SellerPage() {
  const { t } = useI18n();
  const { user, isLoading } = useAuth();
  const profile = useSellerProfile();
  if (isLoading) return <Skeleton className="h-64" />;
  if (!user) return <Navigate to="/login" replace state={{ from: "/seller" }} />;
  if (user.role !== "seller") return <p className="rounded-2xl bg-info-soft p-5 text-info">{t("seller_only")}</p>;
  if (profile.isLoading) return <Skeleton className="h-64" />;
  if (profile.isError) return <ErrorState message={profile.error.message} onRetry={() => profile.refetch()} retryLabel={t("retry")} />;
  if (profile.data === null) return <Onboarding />;

  return (
    <div>
      <div className="mb-4">
        <h1 className="text-2xl font-bold">{t("seller_dashboard")}</h1>
        <p className="text-sm text-muted">{profile.data?.business_name}</p>
      </div>
      <nav className="-mx-4 mb-6 flex gap-1 overflow-x-auto border-b border-line px-4" aria-label={t("seller_dashboard")}>
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
        <Route path="products" element={<ProductsTab />} />
        <Route path="orders" element={<OrdersTab />} />
        <Route path="feedback" element={<FeedbackTab />} />
      </Routes>
    </div>
  );
}
