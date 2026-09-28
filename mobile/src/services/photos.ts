import { api } from "../config/api";

export interface ProductPhoto {
  id: string;
  product: string;
  /** Absolute URL, built by the backend, ready to drop into <Image source>. */
  image: string;
  alt_text: string;
  is_cover: boolean;
  display_order: number;
  is_active: boolean;
}

/** What expo-image-picker hands back for a chosen photo, narrowed to what we send. */
export interface PickedPhoto {
  uri: string;
  mimeType?: string;
  fileName?: string;
  fileSize?: number;
}

function fileNameFor(picked: PickedPhoto): string {
  if (picked.fileName) return picked.fileName;
  // Android's camera often gives no name. Take one from the uri, or invent one —
  // the backend runs the bytes through Pillow, but it still wants an extension.
  const tail = picked.uri.split("/").pop() ?? "";
  return /\.(jpe?g|png|webp|heic)$/i.test(tail) ? tail : `photo-${Date.now()}.jpg`;
}

export const photosService = {
  /** Photos on a product, cover first — the order the vendor should see them in. */
  async forProduct(productId: string): Promise<ProductPhoto[]> {
    const { data } = await api.get<{ results: ProductPhoto[] } | ProductPhoto[]>(
      "/product-images/",
      { params: { product: productId, is_active: true } },
    );
    const list = Array.isArray(data) ? data : data.results;
    return [...list].sort((a, b) => Number(b.is_cover) - Number(a.is_cover));
  },

  /**
   * Upload one photo. Sent as multipart because it carries a file, which means
   * overriding the client's default JSON content type for this request only.
   */
  async upload(productId: string, picked: PickedPhoto, altText = ""): Promise<ProductPhoto> {
    const form = new FormData();
    form.append("product", productId);
    form.append("alt_text", altText);
    // React Native's FormData takes this {uri, name, type} shape for a file.
    form.append("image", {
      uri: picked.uri,
      name: fileNameFor(picked),
      type: picked.mimeType ?? "image/jpeg",
    } as unknown as Blob);

    const { data } = await api.post<ProductPhoto>("/product-images/", form, {
      headers: { "Content-Type": "multipart/form-data" },
      // A photo on a slow Asaba connection needs longer than an ordinary call.
      timeout: 60000,
    });
    return data;
  },

  /** Make this the photo shoppers see first. The backend demotes the previous cover. */
  async makeCover(photoId: string): Promise<ProductPhoto> {
    const { data } = await api.patch<ProductPhoto>(`/product-images/${photoId}/`, {
      is_cover: true,
    });
    return data;
  },

  async remove(photoId: string): Promise<void> {
    await api.delete(`/product-images/${photoId}/`);
  },
};
