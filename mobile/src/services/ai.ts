import { api } from "../config/api";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export const aiService = {
  // POST /api/ai/chat/ — customer assistant
  async chat(message: string, history: ChatMessage[] = []) {
    const { data } = await api.post("/ai/chat/", {
      message,
      history,
    });
    return data.reply as string;
  },

  // POST /api/ai/vendor-chat/ — vendor assistant
  async vendorChat(message: string, history: ChatMessage[] = []) {
    const { data } = await api.post("/ai/vendor-chat/", {
      message,
      history,
    });
    return data.reply as string;
  },

  // GET /api/ai/search/?q=&lat=&lng=
  async search(query: string, lat: number, lng: number) {
    const { data } = await api.get("/ai/search/", {
      params: { q: query, lat, lng },
    });
    return data.results ?? data;
  },
};