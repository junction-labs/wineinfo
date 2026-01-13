interface ServiceSettings {
    searchService: string;
    persistService: string;
    sommelierService: string;
    useJunction: boolean;
}

export const settings: ServiceSettings = {
    sommelierService: process.env.SOMMELIER_SERVICE || "http://localhost:8003",
    searchService: process.env.SEARCH_SERVICE || "http://localhost:8002",
    persistService: process.env.PERSIST_SERVICE || "http://localhost:8001",
    useJunction: process.env.USE_JUNCTION === "true"
};
