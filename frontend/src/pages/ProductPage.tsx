import { ArrowLeft, Globe, Link2, PackageCheck, PackageX, ShieldCheck, ShoppingCart } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { useAuth } from "../auth/AuthProvider";
import { PriceBreakdown } from "../components/PriceBreakdown";
import { ProductRail } from "../components/ProductRail";
import { ProductImage } from "../components/ProductImage";
import { QuantityStepper } from "../components/QuantityStepper";
import { ReviewsSection } from "../components/reviews/ReviewsSection";
import { Stars } from "../components/reviews/Stars";
import { SellerDetails } from "../components/SellerDetails";
import { Button } from "../components/ui/button";
import { Badge, Card, ErrorState, Skeleton } from "../components/ui/primitives";
import { useI18n } from "../i18n/I18nProvider";
import { formatINR } from "../lib/format";
import { useAddToCart, useBoughtTogether, useProduct, useRecordView } from "../lib/queries";

const MAX_PER_ITEM = 10;

export function ProductPage() {
  const { t, category } = useI18n();
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isCustomer } = useAuth();
  const product = useProduct(Number(id));
  const addToCart = useAddToCart();
  const [quantity, setQuantity] = useState(1);
  const recordView = useRecordView();
  const together = useBoughtTogether(Number(id));
  const productId = product.data?.id;
  useEffect(() => {
    if (productId) recordView(productId);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once per product
  }, [productId]);

  if (product.isLoading) {
    return (
      <div className="grid gap-8 md:grid-cols-2">
        <Skeleton className="aspect-square" />
        <div className="space-y-4">
          <Skeleton className="h-8 w-3/4" />
          <Skeleton className="h-12 w-1/3" />
          <Skeleton className="h-48" />
        </div>
      </div>
    );
  }
  if (product.isError || !product.data) {
    return <ErrorState message={product.error?.message ?? t("error_generic")} onRetry={() => product.refetch()} retryLabel={t("retry")} />;
  }

  const p = product.data;
  const soldOut = p.stock === 0;
  const maxQty = Math.min(MAX_PER_ITEM, p.stock);

  const onAdd = () => {
    if (!user) {
      navigate("/login", { state: { from: location.pathname } });
      return;
    }
    addToCart.mutate(
      { productId: p.id, quantity },
      {
        onSuccess: () =>
          toast.success(t("added_to_cart"), {
            description: `${p.title} × ${quantity}`,
            action: { label: t("view_cart"), onClick: () => navigate("/cart") },
          }),
        onError: (error) => toast.error(error.message),
      },
    );
  };

  return (
    <div>
      <button onClick={() => navigate(-1)} className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted hover:text-fg">
        <ArrowLeft className="h-4 w-4" /> {t("back")}
      </button>

      <div className="grid gap-8 md:grid-cols-2">
        <div className="md:sticky md:top-24 md:self-start">
          <ProductImage src={p.image_url} title={p.title} category={p.category} large className="rounded-3xl" />
        </div>

        <div>
          <Link to={`/?category=${p.category}`} className="text-sm font-medium uppercase tracking-wide text-brand hover:underline">
            {category(p.category)}
          </Link>
          <h1 className="mt-1 text-2xl font-bold leading-tight sm:text-3xl">{p.title}</h1>
          <p className="mt-1 text-sm text-muted">{t("sold_by", { name: p.seller.business_name })}</p>
          {p.rating.count > 0 && p.rating.average !== null && (
            <a href="#reviews-heading" className="mt-2 inline-flex items-center gap-2 text-sm hover:underline">
              <Stars value={p.rating.average} />
              <span className="font-semibold tabular">{p.rating.average.toFixed(1)}</span>
              <span className="text-muted">({t("reviews_count", { n: p.rating.count })})</span>
            </a>
          )}

          <div className="mt-5">
            <div className="text-3xl font-bold tabular sm:text-4xl">{formatINR(p.price.final_price)}</div>
            <p className="text-sm text-muted">{t("incl_all")}</p>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {soldOut ? (
              <Badge tone="danger">{t("out_of_stock")}</Badge>
            ) : p.stock <= 5 ? (
              <Badge tone="warn">{t("only_left", { n: p.stock })}</Badge>
            ) : (
              <Badge tone="brand">{t("in_stock")}</Badge>
            )}
            <Badge tone={p.is_returnable ? "brand" : "neutral"}>
              {p.is_returnable ? <PackageCheck className="h-3.5 w-3.5" /> : <PackageX className="h-3.5 w-3.5" />}
              {p.is_returnable ? t("returnable") : t("non_returnable")}
            </Badge>
            <Badge>
              <Globe className="h-3.5 w-3.5" /> {t("made_in", { c: p.country_of_origin })}
            </Badge>
          </div>

          <Card className="mt-6 p-5">
            <h2 className="font-semibold">{t("price_breakdown")}</h2>
            <p className="mb-3 text-xs text-muted">{t("nothing_added")}</p>
            <PriceBreakdown price={p.price} />
          </Card>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            {!soldOut && (isCustomer || !user) && (
              <QuantityStepper value={quantity} max={maxQty} onChange={setQuantity} label={t("quantity")} />
            )}
            <Button
              size="lg"
              className="flex-1"
              onClick={onAdd}
              loading={addToCart.isPending}
              disabled={soldOut || (Boolean(user) && !isCustomer)}
            >
              <ShoppingCart className="h-5 w-5" />
              {!user ? t("login_to_buy") : addToCart.isPending ? t("adding") : t("add_to_cart")}
            </Button>
          </div>
          {user && !isCustomer && <p className="mt-2 text-sm text-muted">{t("sellers_cannot_buy")}</p>}

          <div className="mt-4 flex items-start gap-2 rounded-xl bg-brand-soft p-3 text-sm text-brand">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            <span>{t("wrong_fake_guarantee")}</span>
          </div>

          <section className="mt-8">
            <h2 className="font-semibold">{t("description")}</h2>
            <p className="mt-2 whitespace-pre-line leading-relaxed text-muted">{p.description}</p>
          </section>

          <div className="mt-8">
            <SellerDetails seller={p.seller} />
          </div>

          <div className="mt-10">
            <ReviewsSection productId={p.id} />
          </div>
        </div>
      </div>

      <div className="mt-12">
        <ProductRail
          title={t("bought_together_title")}
          icon={<Link2 className="h-5 w-5 text-brand" aria-hidden />}
          products={together.data ?? []}
        />
      </div>
    </div>
  );
}
