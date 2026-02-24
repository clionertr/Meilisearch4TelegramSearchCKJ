import { GoogleGenAI } from "@google/genai";

// This service handles interactions with the Gemini API for summaries and semantic search.
// Note: In a real deployment, the API key should be handled securely.

export class GeminiService {
  private ai: GoogleGenAI | null = null;

  constructor(apiKey?: string) {
    if (apiKey) {
      this.ai = new GoogleGenAI({ apiKey });
    }
  }

  public isConfigured(): boolean {
    return this.ai !== null;
  }

  // Example method to generate a daily brief
  public async generateDailyBrief(context: string): Promise<string> {
    if (!this.ai) throw new Error("API Key not configured");
    
    try {
      const response = await this.ai.models.generateContent({
        model: 'gemini-3-flash-preview',
        contents: `Summarize the following chat context into a daily brief: ${context}`,
      });
      return response.text || "No summary available.";
    } catch (error) {
      console.error("Gemini API Error:", error);
      throw error;
    }
  }
}

export const geminiService = new GeminiService(process.env.API_KEY);