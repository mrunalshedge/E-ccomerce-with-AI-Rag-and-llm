// Data hooks: one place that knows the API routes and which caches to refresh after a change.
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../auth/AuthProvider";
import { api } from "./api";
import type {
  Cart,
  CategoryCount,
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
  ReviewSummary,
  SearchResponse,
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
