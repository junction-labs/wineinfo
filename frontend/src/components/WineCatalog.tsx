"use client";
import { useSession } from "next-auth/react";
import type React from "react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
	addToCellar,
	getCellarWines,
	recommendWines,
	removeFromCellar,
	searchWines,
} from "@/lib/actions/wineActions";
import type { Wine } from "@/lib/api_types";

type TabType = "catalog" | "cellar" | "recommendations";

type NotificationType = "success" | "error";

interface WineCatalogProps {
	isLoggedIn: boolean;
}

interface Notification {
	message: string;
	type: NotificationType;
}

interface SearchInputProps {
	value: string;
	onChange: (value: string) => void;
	onSearch: () => void;
	loading: boolean;
	placeholder: string;
	isTextArea?: boolean;
}

interface WineCardProps {
	wine: Wine;
	inCellar: boolean;
	onCellarToggle: (wine: Wine) => void;
	isLoggedIn: boolean;
}

function SearchInput({
	value,
	onChange,
	onSearch,
	loading,
	placeholder,
	isTextArea = false,
}: SearchInputProps) {
	const InputComponent = isTextArea ? Textarea : Input;

	return (
		<div className="flex gap-2 mb-4">
			<Input
				placeholder={placeholder}
				value={value}
				onChange={(
					e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
				) => onChange(e.target.value)}
				onKeyPress={(e: React.KeyboardEvent) => e.key === "Enter" && onSearch()}
			/>
			<Button onClick={onSearch} disabled={loading}>
				{loading ? (
					<div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
				) : (
					"🔍 Search"
				)}
			</Button>
		</div>
	);
}

function WineCard({
	wine,
	inCellar,
	onCellarToggle,
	isLoggedIn,
}: WineCardProps) {
	return (
		<Card>
			<CardContent className="p-4">
				<div className="mb-2">
					<CardTitle className="text-lg">{wine.title}</CardTitle>
					<div className="text-sm text-muted-foreground flex items-center gap-2">
						<span className="font-semibold">{wine.winery}</span>
						<span>•</span>
						<span>{wine.variety}</span>
					</div>
				</div>

				<div className="grid grid-cols-3 gap-y-2 text-sm mb-4">
					<div>
						<span className="text-muted-foreground">Country:</span>{" "}
						{wine.country}
					</div>
					<div>
						<span className="text-muted-foreground">Province:</span>{" "}
						{wine.province}
					</div>
					<div>
						<span className="text-muted-foreground">Region:</span>{" "}
						{wine.region_1}
					</div>
					<div>
						<span className="text-muted-foreground">Price:</span> ${wine.price}
					</div>
					<div>
						<span className="text-muted-foreground">Points:</span> {wine.points}
					</div>
				</div>

				<p className="text-sm text-muted-foreground mb-4 line-clamp-3">
					{wine.description}
				</p>

				{isLoggedIn && (
					<Button
						onClick={() => onCellarToggle(wine)}
						variant={inCellar ? "outline" : "default"}
						className="w-full"
					>
						{inCellar ? "Remove from Cellar" : "Add to Cellar"}
					</Button>
				)}
			</CardContent>
		</Card>
	);
}

// Load Testing Component
function LoadTestingSection() {
	const { data: session } = useSession();
	const [isRunning, setIsRunning] = useState(false);
	const [duration, setDuration] = useState(10);
	const [stats, setStats] = useState<{ [key: number]: number }>({});
	const [startTime, setStartTime] = useState<number | null>(null);
	const intervalRefs = useRef<NodeJS.Timeout[]>([]);

	// Only show for admin user
	if (!session?.user?.name || session.user.name !== "admin") {
		return null;
	}

	const queries = [
		"red",
		"white",
		"rose",
		"pinot noir",
		"france",
		"italy",
		"germany",
		"greece",
		"australia",
		"portugal",
	];
	const REQUEST_INTERVAL = 1000;

	const startLoadTest = () => {
		if (isRunning) return;

		setIsRunning(true);
		setStats({});
		setStartTime(Date.now());

		// Clear any existing intervals
		intervalRefs.current.forEach(clearInterval);
		intervalRefs.current = [];

		// Start a request loop for each query
		queries.forEach((query) => {
			const makeRequest = async () => {
				try {
					const response = await fetch(
						`/api/wine/recs?query=${encodeURIComponent(query)}`,
					);
					setStats((prev) => ({
						...prev,
						[response.status]: (prev[response.status] || 0) + 1,
					}));
				} catch (error) {
					setStats((prev) => ({
						...prev,
						[0]: (prev[0] || 0) + 1, // 0 for network errors
					}));
				}
			};

			// Make initial request
			makeRequest();

			// Set up interval for repeated requests (every 1 second)
			const interval = setInterval(makeRequest, REQUEST_INTERVAL);
			intervalRefs.current.push(interval);
		});

		// Stop after duration
		setTimeout(() => {
			stopLoadTest();
		}, duration * REQUEST_INTERVAL);
	};

	const stopLoadTest = () => {
		setIsRunning(false);
		intervalRefs.current.forEach(clearInterval);
		intervalRefs.current = [];
	};

	// Clear intervals on unmount
	useEffect(() => {
		return stopLoadTest;
	}, []);

	const resetStats = () => {
		setStats({});
		setStartTime(null);
	};

	return (
		<Card className="mb-4">
			<CardContent className="p-4">
				<CardTitle className="text-lg mb-4">Load Testing</CardTitle>
				<div className="flex items-center gap-4 mb-4">
					<div className="flex items-center gap-2">
						<label htmlFor="duration" className="text-sm font-medium">
							Duration (seconds):
						</label>
						<Input
							id="duration"
							type="number"
							value={duration}
							onChange={(e) => setDuration(parseInt(e.target.value) || 10)}
							className="w-20"
							min="1"
							max="300"
							disabled={isRunning}
						/>
					</div>
					<Button
						onClick={startLoadTest}
						disabled={isRunning}
						className="bg-yellow-600 hover:bg-yellow-700"
					>
						{isRunning ? "Running..." : "Start Load Test"}
					</Button>
					<Button
						onClick={stopLoadTest}
						disabled={!isRunning}
						variant="outline"
					>
						Stop
					</Button>
					<Button onClick={resetStats} variant="outline" disabled={isRunning}>
						Reset
					</Button>
				</div>

				<div className="text-sm text-gray-600 mb-2">
					Queries: {queries.join(", ")}
				</div>

				{startTime && (
					<div className="text-sm text-gray-600 mb-2">
						Running for:{" "}
						{Math.floor((Date.now() - startTime) / REQUEST_INTERVAL)}s
					</div>
				)}

				{Object.keys(stats).length > 0 && (
					<div className="mt-4">
						<h4 className="font-medium mb-2">Response Statistics:</h4>
						<div className="grid grid-cols-2 gap-2 text-sm">
							{Object.entries(stats).map(([code, count]) => (
								<div key={code} className="flex justify-between">
									<span>
										{code === "0" ? "Network Error" : `HTTP ${code}`}:
									</span>
									<span>{count}</span>
								</div>
							))}
						</div>
					</div>
				)}
			</CardContent>
		</Card>
	);
}

// Main Page Component
export default function WineCatalog({ isLoggedIn }: WineCatalogProps) {
	const [activeTab, setActiveTab] = useState<TabType>("catalog");
	const [searchTerm, setSearchTerm] = useState("");
	const [wines, setWines] = useState<Wine[]>([]);
	const [loading, setLoading] = useState(false);
	const [currentPage, setCurrentPage] = useState(1);
	const [totalPages, setTotalPages] = useState(1);
	const [total, setTotal] = useState(0);
	const [cellarWines, setCellarWines] = useState(new Set<number>());
	const [notification, setNotification] = useState<Notification | null>(null);

	const pageSize = 12;

	const showNotification = (
		message: string,
		type: NotificationType = "success",
	) => {
		setNotification({ message, type });
		setTimeout(() => setNotification(null), 10000);
	};

	const fetchData = async (page: number = 1) => {
		if (activeTab === "recommendations" && !searchTerm.trim()) {
			setWines([]);
			setCurrentPage(1);
			setTotalPages(1);
			setTotal(0);
			return;
		}

		setLoading(true);
		try {
			let wineData: Wine[], totalPages: number, total: number;

			let cellarWines: Wine[] = [];
			if (isLoggedIn) {
				cellarWines = await getCellarWines();
			}
			if (activeTab === "catalog") {
				const data = await searchWines({
					query: searchTerm,
					page,
					page_size: pageSize,
				});
				wineData = data.items;
				totalPages = data.total_pages;
				total = data.total;
			} else if (activeTab === "recommendations") {
				wineData = await recommendWines(searchTerm);
				totalPages = 1;
				total = wineData.length;
			} else {
				wineData = cellarWines;
				totalPages = 1;
				total = cellarWines.length;
			}

			setWines(wineData);
			setCurrentPage(page);
			setTotalPages(totalPages);
			setTotal(total);
			setCellarWines(new Set(cellarWines.map((wine) => wine.id)));
		} catch (err) {
			showNotification(`Failed to load data: ${err}`, "error");
		} finally {
			setLoading(false);
		}
	};

	const handleCellarToggle = async (wine: Wine) => {
		try {
			if (!isLoggedIn) return;

			if (cellarWines.has(wine.id)) {
				await removeFromCellar(wine.id);
				setCellarWines((prev) => {
					const next = new Set(prev);
					next.delete(wine.id);
					return next;
				});
				if (activeTab === "cellar") {
					setWines((prev) => prev.filter((w) => w.id !== wine.id));
					setTotal((prev) => prev - 1);
				}
				showNotification(`${wine.title} has been removed from your cellar.`);
			} else {
				await addToCellar(wine.id);
				setCellarWines((prev) => new Set([...prev, wine.id]));
				showNotification(`${wine.title} has been added to your cellar.`);
			}
		} catch (err) {
			showNotification(`Failed to update cellar: ${err}`, "error");
		}
	};

	useEffect(() => {
		setSearchTerm("");
		setWines([]);
		setTotalPages(0);
		fetchData(1);
	}, [activeTab, isLoggedIn]);

	const tabs = [
		{ id: "catalog" as TabType, name: "Wine Catalog" },
		{ id: "cellar" as TabType, name: "My Cellar", hidden: !isLoggedIn },
		{ id: "recommendations" as TabType, name: "Recommendations" },
	];

	return (
		<div className="w-full max-w-4xl mx-auto p-4">
			<div className="border-b">
				<nav className="flex space-x-8" aria-label="Tabs">
					{tabs.map(
						(tab) =>
							!tab.hidden && (
								<Button
									key={tab.id}
									onClick={() => setActiveTab(tab.id)}
									variant="ghost"
									className={
										activeTab === tab.id ? "border-b-2 border-primary" : ""
									}
								>
									{tab.name}
								</Button>
							),
					)}
				</nav>
			</div>

			{notification && (
				<div
					className={`mb-4 p-4 rounded-lg ${
						notification.type === "error"
							? "bg-destructive/10"
							: "bg-primary/10"
					}`}
				>
					{notification.message}
				</div>
			)}

			<div className="p-4">
				{(activeTab === "catalog" || activeTab === "recommendations") && (
					<SearchInput
						value={searchTerm}
						onChange={setSearchTerm}
						onSearch={() => fetchData(1)}
						loading={loading}
						placeholder={
							activeTab === "catalog"
								? "Search wines..."
								: "Describe what you would like..."
						}
						isTextArea={activeTab === "recommendations"}
					/>
				)}

				{activeTab === "recommendations" && <LoadTestingSection />}

				{wines.length > 0 && totalPages > 1 && (
					<div className="text-sm text-muted-foreground mb-4">
						Showing {(currentPage - 1) * pageSize + 1}-
						{Math.min(currentPage * pageSize, total)} of {total} results
					</div>
				)}

				<div className="grid gap-4">
					{wines.map((wine) => (
						<WineCard
							key={wine.id}
							wine={wine}
							inCellar={cellarWines.has(wine.id)}
							onCellarToggle={handleCellarToggle}
							isLoggedIn={isLoggedIn}
						/>
					))}
				</div>

				{wines.length > 0 && totalPages > 1 && (
					<div className="flex items-center justify-center gap-2 mt-4">
						{[
							{ label: "«", page: 1 },
							{ label: "‹", page: currentPage - 1 },
							...Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
								let page: number;
								if (totalPages <= 5) page = i + 1;
								else if (currentPage <= 3) page = i + 1;
								else if (currentPage >= totalPages - 2)
									page = totalPages - 4 + i;
								else page = currentPage - 2 + i;
								return { label: page.toString(), page };
							}),
							{ label: "›", page: currentPage + 1 },
							{ label: "»", page: totalPages },
						].map(({ label, page }) => (
							<Button
								key={label}
								onClick={() =>
									page >= 1 &&
									page <= totalPages &&
									page !== currentPage &&
									fetchData(page)
								}
								disabled={
									loading ||
									page === currentPage ||
									page < 1 ||
									page > totalPages
								}
								variant={currentPage === page ? "default" : "outline"}
								size="sm"
							>
								{label}
							</Button>
						))}
					</div>
				)}
			</div>
		</div>
	);
}
