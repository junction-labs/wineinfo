interface ServiceSettings {
    searchService: string;
    embeddingsService: string;
    persistService: string;
    sommelierService: string;
    useJunction: boolean;
}

export const settings: ServiceSettings = {
    sommelierService: process.env.SOMMELIER_SERVICE || "http://localhost:8001",
    searchService: process.env.SEARCH_SERVICE || "http://localhost:8002",
    embeddingsService: process.env.EMBEDDINGS_SERVICE || "http://localhost:8003",
    persistService: process.env.PERSIST_SERVICE || "http://localhost:8004",
    useJunction: process.env.USE_JUNCTION === "true"
};
