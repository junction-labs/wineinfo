export interface Wine {
    id: number;
    title: string;
    country: string;
    description: string;
    designation: string;
    points: string;
    price: string;
    province: string;
    region_1: string;
    region_2: string;
    taster_name: string;
    taster_twitter_handle: string;
    variety: string;
    winery: string;
}

export interface PaginatedList<T> {
    items: T[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export interface SearchRequest {
    query: string;
    page: number;
    page_size: number;
}

export interface EmbeddingsSearchRequest {
    query: string;
    limit: number;
}

export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}

export interface SommelierChatRequest {
    message: string;
    conversation_history: ChatMessage[];
    cellar_wine_ids: number[];
}

export interface SommelierChatResponse {
    response: string;
    recommended_wines: Wine[];
}
