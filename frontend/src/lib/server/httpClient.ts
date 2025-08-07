import type { Session } from "next-auth";

export interface Fetcher {
	fetch(url: string, config: RequestInit): Promise<Response>;
}

export interface HttpClientOptions {
	additionalHeaders: Headers;
	baggage: Record<string, string>;
}

export function emptyOptions(): HttpClientOptions {
	return {
		additionalHeaders: new Headers(),
		baggage: {},
	};
}

export function sessionOptions(
	incomingHeaders: Headers,
	session: Session | null,
): HttpClientOptions {
	const requestId = incomingHeaders.get("x-request-id") || crypto.randomUUID();
	return {
		additionalHeaders: new Headers(),
		baggage: {
			"request-id": requestId,
			"user-id": session?.user?.id || "",
			username: session?.user?.name || "",
		},
	};
}

export class HttpClient {
	private junction: any;

	constructor(
		private baseUrl: string,
		useJunction: boolean,
	) {
		this.baseUrl = baseUrl.replace(/\/$/, "");
		if (useJunction) {
			this.junction = require("@junction-labs/client");
		}
	}

	private async fetch(
		input: string | URL | globalThis.Request,
		init?: RequestInit,
	): Promise<Response> {
		if (this.junction) {
			return this.junction.fetch(input, init);
		} else {
			return fetch(input, init);
		}
	}

	private async request<T>(
		method: "GET" | "POST",
		path: string,
		data?: any,
		options: HttpClientOptions = emptyOptions(),
	): Promise<T> {
		const response = await this.makeRequest(method, path, data, options);
		return response.json();
	}

	private async makeRequest(
		method: "GET" | "POST",
		path: string,
		data?: any,
		options: HttpClientOptions = emptyOptions(),
	): Promise<Response> {
		const headers: Headers = new Headers(options.additionalHeaders);
		if (method === "POST" && !headers.has("Content-Type")) {
			headers.set("Content-Type", "application/json");
		}
		headers.set(
			"baggage",
			Object.entries(options.baggage)
				.map(([key, value]) => `${key}=${value}`)
				.join(","),
		);
		const request: RequestInit = { method, headers };

		if (method === "GET" && data) {
			const params = new URLSearchParams();
			Object.entries(data).forEach(([key, value]) => {
				if (Array.isArray(value)) {
					value.forEach((v) => params.append(key, v.toString()));
				} else if (value !== undefined && value !== null) {
					params.append(key, value.toString());
				}
			});
			path = `${path}?${params.toString()}`;
		} else if (data) {
			request.body = JSON.stringify(data);
		}

		const response = await this.fetch(`${this.baseUrl}${path}`, request);
		if (!response.ok) {
			const errorText = await response.text();
			const error = new Error(
				errorText || `HTTP ${response.status}: ${response.statusText}`,
			);
			(error as any).status = response.status;
			(error as any).statusText = response.statusText;
			throw error;
		}
		return response;
	}

	async get<T>(
		path: string,
		data?: any,
		options: HttpClientOptions = emptyOptions(),
	): Promise<T> {
		return this.request<T>("GET", path, data, options);
	}

	async post<T>(
		path: string,
		data: any,
		options: HttpClientOptions = emptyOptions(),
	): Promise<T> {
		return this.request<T>("POST", path, data, options);
	}

	async postStream(
		path: string,
		data: any,
		options: HttpClientOptions = emptyOptions(),
	): Promise<Response> {
		return this.makeRequest("POST", path, data, options);
	}

	async getStream(
		path: string,
		data?: any,
		options: HttpClientOptions = emptyOptions(),
	): Promise<Response> {
		return this.makeRequest("GET", path, data, options);
	}
}
