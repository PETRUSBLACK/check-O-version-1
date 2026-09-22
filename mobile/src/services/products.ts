import { api } from "../config/api";

// Mirrors apps/products ProductSerializer (fields the app uses)
export interface Product {
  id: string;
  business: string;
  category: string | null;
  name: string;
  slug: string;
  description: string;
  currency: string;
  price: string; // decimal as string, e.g. "4500.00"
  available_stock: number;
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
};
