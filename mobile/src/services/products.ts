import { api } from "../config/api";

export interface Product {
  id: string;
  business: string;
  business_name: string;
  name: string;
  description: string;
  price: number;
  stock: number;
  category: string;
  image?: string;
  is_active: boolean;
}

export const productsService = {
  // GET /api/products/
  async list(params?: { business?: string; category?: string; search?: string }) {
    const { data } = await api.get("/products/", { params });
    return data.results ?? data;
  },

  // GET /api/products/{id}/
  async get(id: string): Promise<Product> {
    const { data } = await api.get(`/products/${id}/`);
    return data;
  },
};