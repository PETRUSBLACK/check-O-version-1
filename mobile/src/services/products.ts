import { api } from "../config/api";

// Mirrors apps/products ProductSerializer (the fields a shopper is allowed to see).
// cost_price, stock, smartmall_allocation and low_stock_threshold are vendor-only
// and are not sent to customers, so they are deliberately absent here.
export interface Product {
  id: string;
  business: string;
  business_name: string;
  category: string | null;
  cover_image: string | null;
  name: string;
  slug: string;
  description: string;
  currency: string;
  price: string; // decimal as string, e.g. "4500.00"
  available_stock: number;
  uses_channel_allocation: boolean;
  is_active: boolean;
}

interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export const productsService = {
  // GET /api/products/?search=&business=
  async list(params: { search?: string; business?: string } = {}): Promise<Product[]> {
    const { data } = await api.get<Page<Product> | Product[]>("/products/", { params });
    return Array.isArray(data) ? data : data.results;
  },

  // GET /api/products/{id}/
  async get(id: string): Promise<Product> {
    const { data } = await api.get<Product>(`/products/${id}/`);
    return data;
  },
};
