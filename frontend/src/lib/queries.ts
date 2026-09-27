// Data hooks: one place that knows the API routes and which caches to refresh after a change.
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../auth/AuthProvider";
import { ApiError, api } from "./api";
import { getRecentLocal, rememberRecentLocal } from "./recent";
import type {
  Cart,
  AdminGrievance,
  AdminOverview,
  AdminReview,
  CategoryCount,
  Grievance,
  ChatMessage,
  ChatResponse,
  CheckoutResponse,
  Order,
  PaymentMethod,
  Product,
  ProductList,
  ReturnReason,
  ReturnRequest,
  Language,
  MyReview,
  Review,
  ReviewList,
  ReviewSort,
  Recommendation,
  ReviewSummary,
  SearchResponse,
  SearchSuggestion,
  PriceBreakdown,
  ProductInput,
  SellerDashboard,
  SellerProfile,
  SellerProfileInput,
  SellerReview,
  OrderStatus,
} from "./types";

export const PAGE_SIZE = 12;

export function useProducts(params: { category?: string; page: number }) {
  const search = new URLSearchParams({ page: String(params.page), page_size: String(PAGE_SIZE) });
  if (params.category) search.set("category", params.category);
  return useQuery({
    queryKey: ["products", params],
    queryFn: () => api<ProductList>(`/products?${search}`),
    placeholderData: keepPreviousData,
  });
}

/** Smart (semantic + keyword) search. Returns up to 24 best matches. */
export function useSearch(params: { q: string; category?: string }) {
  const search = new URLSearchParams({ q: params.q, limit: "24" });
  if (params.category) search.set("category", params.category);
  return useQuery({
    queryKey: ["search", params],
    queryFn: () => api<SearchResponse>(`/search?${search}`),
    enabled: params.q.length > 0,
    placeholderData: keepPreviousData,
  });
}

export function useAssistantChat() {
  return useMutation({
    mutationFn: (input: { message: string; history: ChatMessage[]; language: Language }) =>
      api<ChatResponse>("/assistant/chat", { method: "POST", json: input }),
  });
}

export function useCategories() {
  return useQuery({
    queryKey: ["categories"],
    queryFn: () => api<CategoryCount[]>("/products/categories"),
    staleTime: 5 * 60_000,
  });
}

export function useProduct(id: number) {
  return useQuery({ queryKey: ["product", id], queryFn: () => api<Product>(`/products/${id}`) });
}

// ---------- cart (customers only) ----------

export function useCart() {
  const { isCustomer } = useAuth();
  return useQuery({ queryKey: ["cart"], queryFn: () => api<Cart>("/cart"), enabled: isCustomer });
}

function useCartMutation<T>(fn: (input: T) => Promise<Cart>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (cart) => queryClient.setQueryData(["cart"], cart),
  });
}

export const useAddToCart = () =>
  useCartMutation((input: { productId: number; quantity: number }) =>
    api<Cart>("/cart/items", { method: "POST", json: { product_id: input.productId, quantity: input.quantity } }),
  );

export const useUpdateCartItem = () =>
  useCartMutation((input: { productId: number; quantity: number }) =>
    api<Cart>(`/cart/items/${input.productId}`, { method: "PATCH", json: { quantity: input.quantity } }),
  );

export const useRemoveCartItem = () =>
  useCartMutation((productId: number) => api<Cart>(`/cart/items/${productId}`, { method: "DELETE" }));

// ---------- orders ----------

export function useCheckout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { paymentMethod: PaymentMethod; address: string; expectedTotal: string }) =>
      api<CheckoutResponse>("/orders", {
        method: "POST",
        json: {
          payment_method: input.paymentMethod,
          shipping_address: input.address,
          expected_total: input.expectedTotal,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cart"] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["product"] });
    },
    // A 409 means prices/stock changed: refresh the cart so the customer sees the new total.
    onError: () => queryClient.invalidateQueries({ queryKey: ["cart"] }),
  });
}

export function useOrders() {
  const { isCustomer } = useAuth();
  return useQuery({ queryKey: ["orders"], queryFn: () => api<Order[]>("/orders"), enabled: isCustomer });
}

export function useOrder(id: number) {
  const { user } = useAuth();
  return useQuery({ queryKey: ["orders", id], queryFn: () => api<Order>(`/orders/${id}`), enabled: Boolean(user) });
}

export function useCancelOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (orderId: number) => api<Order>(`/orders/${orderId}/cancel`, { method: "POST" }),
    onSuccess: (order) => {
      queryClient.setQueryData(["orders", order.id], order);
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });
}

// ---------- returns ----------

export function useReturns() {
  const { isCustomer } = useAuth();
  return useQuery({ queryKey: ["returns"], queryFn: () => api<ReturnRequest[]>("/returns"), enabled: isCustomer });
}

export function useCreateReturn() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { orderItemId: number; reason: ReturnReason; description: string }) =>
      api<ReturnRequest>("/returns", {
        method: "POST",
        json: { order_item_id: input.orderItemId, reason: input.reason, description: input.description },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["returns"] }),
  });
}

// ---------- reviews ----------

export function useReviews(productId: number, sort: ReviewSort, pageSize: number) {
  return useQuery({
    queryKey: ["reviews", productId, sort, pageSize],
    queryFn: () => api<ReviewList>(`/products/${productId}/reviews?sort=${sort}&page_size=${pageSize}`),
    placeholderData: keepPreviousData,
  });
}

export function useReviewSummary(productId: number, language: Language, enabled: boolean) {
  return useQuery({
    queryKey: ["review-summary", productId, language],
    queryFn: () => api<ReviewSummary>(`/products/${productId}/reviews/summary?language=${language}`),
    enabled,
    staleTime: 10 * 60_000,
    retry: false,
  });
}

export function useMyReviews() {
  const { isCustomer } = useAuth();
  return useQuery({ queryKey: ["my-reviews"], queryFn: () => api<MyReview[]>("/reviews/mine"), enabled: isCustomer });
}

export function useCreateReview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { productId: number; rating: number; title: string; body: string }) =>
      api<Review>(`/products/${input.productId}/reviews`, {
        method: "POST",
        json: { rating: input.rating, title: input.title || null, body: input.body },
      }),
    onSuccess: (review) => {
      queryClient.invalidateQueries({ queryKey: ["my-reviews"] });
      queryClient.invalidateQueries({ queryKey: ["reviews", review.product_id] });
      queryClient.invalidateQueries({ queryKey: ["review-summary", review.product_id] });
      queryClient.invalidateQueries({ queryKey: ["product", review.product_id] });
    },
  });
}

// ---------- grievances ----------

export function useGrievances() {
  const { isCustomer } = useAuth();
  return useQuery({ queryKey: ["grievances"], queryFn: () => api<Grievance[]>("/grievances"), enabled: isCustomer });
}

export function useGrievance(id: number) {
  const { user } = useAuth();
  return useQuery({ queryKey: ["grievances", id], queryFn: () => api<Grievance>(`/grievances/${id}`), enabled: Boolean(user) });
}

function useGrievanceMutation<T>(fn: (input: T) => Promise<Grievance>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (g) => {
      queryClient.setQueryData(["grievances", g.id], g);
      queryClient.invalidateQueries({ queryKey: ["grievances"], exact: true });
    },
  });
}

export const useCreateGrievance = () =>
  useGrievanceMutation((input: { orderId: number | null; subject: string; description: string; language: Language }) =>
    api<Grievance>("/grievances", {
      method: "POST",
      json: { order_id: input.orderId, subject: input.subject, description: input.description, language: input.language },
    }),
  );

export const useGrievanceComment = () =>
  useGrievanceMutation((input: { id: number; message: string }) =>
    api<Grievance>(`/grievances/${input.id}/comments`, { method: "POST", json: { message: input.message } }),
  );

export const useReopenGrievance = () =>
  useGrievanceMutation((input: { id: number; message: string }) =>
    api<Grievance>(`/grievances/${input.id}/reopen`, { method: "POST", json: { message: input.message } }),
  );

// ---------- admin ----------

function useIsAdmin(): boolean {
  return useAuth().user?.role === "admin";
}

export function useAdminOverview() {
  return useQuery({ queryKey: ["admin", "overview"], queryFn: () => api<AdminOverview>("/admin/overview"), enabled: useIsAdmin() });
}

export function useAdminGrievances() {
  return useQuery({ queryKey: ["admin", "grievances"], queryFn: () => api<AdminGrievance[]>("/admin/grievances"), enabled: useIsAdmin() });
}

export function useAdminReviews() {
  return useQuery({ queryKey: ["admin", "reviews"], queryFn: () => api<AdminReview[]>("/admin/reviews"), enabled: useIsAdmin() });
}

export function useAdminReturns() {
  return useQuery({
    queryKey: ["admin", "returns"],
    queryFn: () => api<ReturnRequest[]>("/admin/returns?status=requested"),
    enabled: useIsAdmin(),
  });
}

/** Admin actions refresh every admin list plus the overview numbers. */
function useAdminMutation<T, R>(fn: (input: T) => Promise<R>) {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: fn, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin"] }) });
}

export const useAdminUpdateGrievance = () =>
  useAdminMutation((input: { id: number; status: "in_progress" | "resolved"; note: string }) =>
    api<AdminGrievance>(`/admin/grievances/${input.id}/update`, { method: "POST", json: { status: input.status, note: input.note } }),
  );

export const useModerateReview = () =>
  useAdminMutation((input: { id: number; action: "approve" | "remove"; note: string }) =>
    api<AdminReview>(`/admin/reviews/${input.id}/moderate`, { method: "POST", json: { action: input.action, note: input.note } }),
  );

export const useResolveReturn = () =>
  useAdminMutation((input: { id: number; decision: "approve" | "reject"; note: string }) =>
    api<ReturnRequest>(`/admin/returns/${input.id}/resolve`, { method: "POST", json: { decision: input.decision, note: input.note } }),
  );

// ---------- discovery ----------

export function useSuggestions(prefix: string) {
  return useQuery({
    queryKey: ["suggest", prefix],
    queryFn: () => api<SearchSuggestion[]>(`/search/suggest?q=${encodeURIComponent(prefix)}&limit=8`),
    enabled: prefix.trim().length > 0,
    staleTime: 60_000,
    placeholderData: keepPreviousData,
  });
}

export function useRecommendations(limit = 8) {
  const { user } = useAuth();
  // Guests are personalised from what they viewed in this browser.
  const seen = user ? "" : getRecentLocal().slice(0, 12).join(",");
  return useQuery({
    queryKey: ["recommendations", user?.id ?? "guest", seen, limit],
    queryFn: () => api<Recommendation[]>(`/recommendations?limit=${limit}${seen ? `&seen=${seen}` : ""}`),
    staleTime: 60_000,
  });
}

export function useBoughtTogether(productId: number) {
  return useQuery({
    queryKey: ["bought-together", productId],
    queryFn: () => api<Product[]>(`/products/${productId}/bought-together?limit=4`),
    staleTime: 5 * 60_000,
  });
}

/** Recently viewed: from the account when logged in, else from this browser. */
export function useRecentlyViewed(excludeId?: number) {
  const { user } = useAuth();
  const localIds = user ? [] : getRecentLocal();
  return useQuery({
    queryKey: ["recently-viewed", user?.id ?? "guest", localIds.join(",")],
    queryFn: async () => {
      const products = user
        ? await api<Product[]>("/me/recently-viewed")
        : (await Promise.all(localIds.slice(0, 8).map((id) => api<Product>(`/products/${id}`).catch(() => null)))).filter(
            (p): p is Product => p !== null,
          );
      return products.filter((p) => p.id !== excludeId);
    },
    staleTime: 30_000,
  });
}

export function useRecordView() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  return (productId: number) => {
    rememberRecentLocal(productId);
    if (user) {
      api<null>(`/me/recently-viewed/${productId}`, { method: "POST" })
        .then(() => queryClient.invalidateQueries({ queryKey: ["recently-viewed"] }))
        .catch(() => undefined);
    }
  };
}

// ---------- seller portal ----------

function useIsSeller(): boolean {
  return useAuth().user?.role === "seller";
}

/** The seller's profile, or null if they haven't created one yet (404). */
export function useSellerProfile() {
  return useQuery({
    queryKey: ["seller", "profile"],
    queryFn: () =>
      api<SellerProfile>("/sellers/me").catch((error: unknown) => {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }),
    enabled: useIsSeller(),
  });
}

function useSellerMutation<T, R>(fn: (input: T) => Promise<R>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["seller"] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["product"] });
    },
  });
}

export const useCreateSellerProfile = () =>
  useSellerMutation((input: SellerProfileInput) => api<SellerProfile>("/sellers/me", { method: "POST", json: input }));

export function useSellerDashboard() {
  return useQuery({ queryKey: ["seller", "dashboard"], queryFn: () => api<SellerDashboard>("/sellers/me/dashboard"), enabled: useIsSeller() });
}

export function useSellerProducts() {
  return useQuery({ queryKey: ["seller", "products"], queryFn: () => api<Product[]>("/sellers/me/products"), enabled: useIsSeller() });
}

export const useCreateProduct = () =>
  useSellerMutation((input: ProductInput) => api<Product>("/products", { method: "POST", json: input }));

export const useUpdateProduct = () =>
  useSellerMutation((input: { id: number; changes: Partial<ProductInput> }) =>
    api<Product>(`/sellers/me/products/${input.id}`, { method: "PATCH", json: input.changes }),
  );

export function useSellerOrders() {
  return useQuery({ queryKey: ["seller", "orders"], queryFn: () => api<Order[]>("/sellers/me/orders"), enabled: useIsSeller() });
}

export const useUpdateOrderStatus = () =>
  useSellerMutation((input: { id: number; status: Extract<OrderStatus, "shipped" | "delivered"> }) =>
    api<Order>(`/sellers/me/orders/${input.id}/status`, { method: "PATCH", json: { status: input.status } }),
  );

export function useSellerReturns() {
  return useQuery({ queryKey: ["seller", "returns"], queryFn: () => api<ReturnRequest[]>("/sellers/me/returns"), enabled: useIsSeller() });
}

export function useSellerReviews() {
  return useQuery({ queryKey: ["seller", "reviews"], queryFn: () => api<SellerReview[]>("/sellers/me/reviews"), enabled: useIsSeller() });
}

/** Live customer price for the numbers being typed (the server's pricing rule, not a copy). */
export function usePricePreview(input: { base: string; delivery: string; platform: string; gst: string }) {
  const valid = [input.base, input.delivery, input.platform, input.gst].every((v) => v !== "" && Number(v) >= 0) && Number(input.base) > 0;
  const params = new URLSearchParams({
    base_price: input.base,
    delivery_fee: input.delivery,
    platform_fee: input.platform,
    gst_percent: input.gst,
  });
  return useQuery({
    queryKey: ["price-preview", params.toString()],
    queryFn: () => api<PriceBreakdown>(`/pricing/preview?${params}`),
    enabled: valid,
    placeholderData: keepPreviousData,
    retry: false,
  });
}
