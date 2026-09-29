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
  model_url: string | null; // glTF 3D model for the 3D viewer and AR
  model_credit: string | null;
  try_on: WristTryOn | null; // live camera try-on (watches)
  created_at: string;
  price: PriceBreakdown;
  seller: SellerCard;
  rating: RatingSummary;
  sizes: SizeStock[]; // empty = the product doesn't come in sizes
  size_chart: SizeChartRow[] | null;
  fit: FitSummary | null;
}

export interface WristTryOn {
  kind: "wrist";
  case_mm: number;
  dial_color: string; // #rrggbb
  case_color: string;
  strap_color: string;
}

export interface SizeStock {
  size: string;
  stock: number;
}

/** Garment measurements in cm, e.g. { size: "M", chest: 102, length: 106 }. */
export type SizeChartRow = { size: string } & Partial<Record<Measurement, number>>;
export const MEASUREMENTS = ["chest", "waist", "hip", "length", "shoulder", "sleeve", "inseam"] as const;
export type Measurement = (typeof MEASUREMENTS)[number];

export type ReviewFit = "runs_small" | "true_to_size" | "runs_large";
export interface FitSummary {
  runs_small: number;
  true_to_size: number;
  runs_large: number;
  verdict: ReviewFit | "mixed" | null; // null = fewer than 3 answers
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
  size: string | null;
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
  size: string | null;
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

export type ReturnReason = "wrong_item" | "counterfeit" | "damaged" | "wrong_size" | "other";
export type ReturnStatus = "requested" | "approved" | "rejected";

export interface ReturnRequest {
  id: number;
  order_id: number;
  order_item_id: number;
  product_title: string;
  size: string | null;
  reason: ReturnReason;
  exchange_size: string | null;
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
  fit: ReviewFit | null;
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

export type GrievanceStatus = "open" | "in_progress" | "ai_resolved" | "resolved";
export type GrievanceCategory =
  | "delivery"
  | "wrong_or_fake_item"
  | "damaged"
  | "refund"
  | "payment"
  | "seller"
  | "account"
  | "other";
export type GrievancePriority = "low" | "medium" | "high" | "urgent";

export interface GrievanceEvent {
  status: GrievanceStatus;
  actor: "customer" | "ai" | "admin";
  note: string;
  created_at: string;
}

export interface Grievance {
  id: number;
  order_id: number | null;
  subject: string;
  description: string;
  category: GrievanceCategory;
  priority: GrievancePriority;
  status: GrievanceStatus;
  ai_reply: string | null;
  created_at: string;
  acknowledged_at: string | null;
  resolve_by: string;
  resolved_at: string | null;
  overdue: boolean;
  can_reopen: boolean;
  timeline: GrievanceEvent[];
}

export interface AdminGrievance extends Grievance {
  customer_name: string;
  customer_email: string;
  ai_summary: string | null;
  triaged_by: "ai" | "rules";
}

export interface AdminOverview {
  open_grievances: number;
  urgent_or_high: number;
  overdue_grievances: number;
  flagged_reviews: number;
  pending_returns: number;
  orders_today: number;
  revenue_today: Money;
}

export interface AdminReview extends Review {
  suspicion_score: number;
  suspicion_reasons: string[];
  moderation_note: string | null;
  product_title: string;
}

export interface SearchSuggestion {
  text: string;
  kind: "product" | "category" | "seller";
  product_id: number | null;
  category: string | null;
}

export type RecommendationReason = "bought_together" | "similar_interest" | "popular";

export interface Recommendation {
  product: Product;
  reason: RecommendationReason;
}

export interface SellerProfile extends SellerCard {
  user_id: number;
  created_at: string;
}

export interface TrustBreakdown {
  score: number;
  wrong_or_fake_returns: number;
  return_penalty: number;
  average_rating: number | null;
  review_count: number;
  rating_penalty: number;
  min_reviews_for_rating_penalty: number;
  rating_target: number;
}

export interface SellerDashboard {
  to_ship: number;
  in_transit: number;
  delivered_30d: number;
  revenue_30d: Money;
  open_returns: number;
  products: number;
  low_stock: number;
  average_rating: number | null;
  review_count: number;
  trust: TrustBreakdown;
}

export interface SellerReview {
  id: number;
  product_id: number;
  product_title: string;
  rating: number;
  title: string | null;
  body: string;
  reviewer: string;
  created_at: string;
}

/** Fields a seller edits (money as strings, exactly as typed). */
export interface ProductInput {
  title: string;
  description: string;
  category: string;
  base_price: string;
  delivery_fee: string;
  platform_fee: string;
  gst_percent: string;
  stock: number;
  is_returnable: boolean;
  country_of_origin: string;
  image_url: string | null;
  model_url: string | null;
  model_credit: string | null;
  try_on: WristTryOn | null;
  sizes: SizeStock[] | null;
  size_chart: SizeChartRow[] | null;
}

export interface SellerProfileInput {
  business_name: string;
  contact_email: string;
  phone: string;
  address: string;
  gstin: string | null;
  grievance_officer_name: string;
  grievance_officer_email: string;
}
