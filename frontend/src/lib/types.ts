// Shapes returned by the FastAPI backend. Money is a decimal string (e.g. "1239.00").
export type Money = string;
export type Role = "customer" | "seller" | "admin";
export type Language = "en" | "hi" | "mr";

export interface PriceBreakdown {
  base_price: Money;
  delivery_fee: Money;
  platform_fee: Money;
  taxable_value: Money;
  gst_percent: Money;
  gst_amount: Money;
  final_price: Money;
  currency: string;
}

export interface SellerCard {
  id: number;
  business_name: string;
  contact_email: string;
  phone: string;
  address: string;
  gstin: string | null;
  grievance_officer_name: string;
  grievance_officer_email: string;
  trust_score: number;
}

export interface Product {
  id: number;
  title: string;
  description: string;
  category: string;
  stock: number;
  is_returnable: boolean;
  country_of_origin: string;
  image_url: string | null;
  created_at: string;
  price: PriceBreakdown;
  seller: SellerCard;
  rating: RatingSummary;
}

export interface ProductList {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
}

export interface CategoryCount {
  category: string;
  count: number;
}

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  preferred_language: string;
  created_at: string;
}

export interface Totals {
  items_count: number;
  total_base: Money;
  total_delivery: Money;
  total_platform_fee: Money;
  total_gst: Money;
  grand_total: Money;
  currency: string;
}

export interface CartLine {
  product_id: number;
  title: string;
  category: string;
  image_url: string | null;
  seller_id: number;
  seller_name: string;
  quantity: number;
  available_stock: number;
  unit_price: PriceBreakdown;
  line_total: Money;
}

export interface Cart {
  items: CartLine[];
  totals: Totals;
}

export type OrderStatus = "placed" | "shipped" | "delivered" | "cancelled";
export type PaymentMethod = "upi" | "card" | "cod";
export type PaymentStatus = "pending" | "paid" | "refunded" | "void";

export interface OrderItem {
  id: number;
  product_id: number | null;
  title: string;
  quantity: number;
  unit_price: PriceBreakdown;
  line_total: Money;
  is_returnable: boolean;
}

export interface OrderEvent {
  status: OrderStatus;
  note: string | null;
  created_at: string;
}

export interface Order {
  id: number;
  status: OrderStatus;
  payment_method: PaymentMethod;
  payment_status: PaymentStatus;
  shipping_address: string;
  seller: { id: number; business_name: string };
  items: OrderItem[];
  totals: Totals;
  timeline: OrderEvent[];
  created_at: string;
  delivered_at: string | null;
}

export interface CheckoutResponse {
  orders: Order[];
  grand_total: Money;
}

export type ReturnReason = "wrong_item" | "counterfeit" | "damaged" | "other";
export type ReturnStatus = "requested" | "approved" | "rejected";

export interface ReturnRequest {
  id: number;
  order_id: number;
  order_item_id: number;
  product_title: string;
  reason: ReturnReason;
  description: string;
  status: ReturnStatus;
  refund_amount: Money;
  resolution_note: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface SearchResponse {
  query: string;
  items: Product[];
  total: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
  products: Product[];
}

export interface RatingSummary {
  average: number | null;
  count: number;
}

export type ReviewStatus = "published" | "flagged" | "removed";
export type ReviewSort = "recent" | "highest" | "lowest";

export interface Review {
  id: number;
  product_id: number;
  rating: number;
  title: string | null;
  body: string;
  reviewer: string;
  verified_purchase: boolean;
  status: ReviewStatus;
  created_at: string;
}

export interface ReviewList {
  items: Review[];
  total: number;
  page: number;
  page_size: number;
  stats: RatingSummary & { distribution: Record<string, number>; under_review: number };
}

export interface ReviewSummary {
  status: "ready" | "not_enough_reviews" | "unavailable";
  summary: string | null;
  review_count: number;
  generated_at: string | null;
}

export interface MyReview {
  id: number;
  product_id: number;
  order_item_id: number;
  rating: number;
  status: ReviewStatus;
}
