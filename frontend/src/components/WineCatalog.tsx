'use client';
import React, { useRef } from 'react';
import { useState, useEffect } from 'react';
import { getCellarWineIds, getWinesByIds, addToCellar, removeFromCellar, searchWines, searchWinesSemantic } from '@/lib/actions/wineActions';
import { type Wine } from '@/lib/api_types';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import SommelierChat from './SommelierChat';
import { useSession } from 'next-auth/react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

type TabType = 'catalog' | 'cellar' | 'chat';

type NotificationType = 'success' | 'error';

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
	searchType: 'exact' | 'semantic';
	onSearchTypeChange: (type: 'exact' | 'semantic') => void;
	isTextArea?: boolean;
}

function SearchInput({
	value,
	onChange,
	onSearch,
	loading,
	placeholder,
	searchType,
	onSearchTypeChange,
	isTextArea = false,
}: SearchInputProps) {
	return (
		<div className="flex gap-2 mb-4">
			<div className="flex-1 flex gap-2">
				<Input
					placeholder={placeholder}
					value={value}
					onChange={(
						e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
					) => onChange(e.target.value)}
					onKeyPress={(e: React.KeyboardEvent) => e.key === "Enter" && onSearch()}
				/>
				<Select value={searchType} onValueChange={onSearchTypeChange}>
					<SelectTrigger className="w-32">
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						<SelectItem value="exact">Exact</SelectItem>
						<SelectItem value="semantic">Semantic</SelectItem>
					</SelectContent>
				</Select>
			</div>
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
}: {
	wine: Wine;
	inCellar: boolean;
	onCellarToggle: (wine: Wine) => void;
	isLoggedIn: boolean;
}) {
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
						`/api/wine/embeddings?query=${encodeURIComponent(query)}`,
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
	const [searchType, setSearchType] = useState<'exact' | 'semantic'>('exact');
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
		setLoading(true);
		try {
			let wineData: Wine[], totalPages: number, total: number;

			if (activeTab === 'catalog') {
				// Choose search method based on search type
				const data = searchType === 'semantic'
					? await searchWinesSemantic({
						query: searchTerm,
						page,
						page_size: pageSize
					})
					: await searchWines({
						query: searchTerm,
						page,
						page_size: pageSize
					});
				wineData = data.items;
				totalPages = data.total_pages;
				total = data.total;
			} else {
				let cellarWineIds: number[] = [];
				if (isLoggedIn) {
					cellarWineIds = await getCellarWineIds();
				}

				const startIndex = (page - 1) * pageSize;
				const endIndex = startIndex + pageSize;
				const pageWineIds = cellarWineIds.slice(startIndex, endIndex);

				wineData = await getWinesByIds(pageWineIds);
				totalPages = Math.ceil(cellarWineIds.length / pageSize);
				total = cellarWineIds.length;

				setCellarWines(new Set(cellarWineIds));
			}

			setWines(wineData);
			setCurrentPage(page);
			setTotalPages(totalPages);
			setTotal(total);
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
					// Recalculate pagination after removing a wine
					const newTotal = total - 1;
					const newTotalPages = Math.ceil(newTotal / pageSize);
					setTotal(newTotal);
					setTotalPages(newTotalPages);

					// If current page is now empty and not the first page, go to previous page
					if (wines.length === 1 && currentPage > 1) {
						fetchData(currentPage - 1);
					} else {
						fetchData(currentPage);
					}
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
		if (activeTab !== 'chat') {
			setSearchTerm('');
			setWines([]);
			setTotalPages(0);
			fetchData(1);
		}
	}, [activeTab]);

	const tabs = [
		{ id: 'catalog' as TabType, name: 'Wine Catalog' },
		{ id: 'cellar' as TabType, name: 'My Cellar', hidden: !isLoggedIn },
		{ id: 'chat' as TabType, name: 'Sommelier Chat' }
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
				<div className={`mb-4 p-4 rounded-lg ${notification.type === 'error' ? 'bg-destructive/10' : 'bg-primary/10'}`}>
					{notification.message}
				</div>
			)}

			<div className="mt-4">
				{/* Chat tab content */}
				{activeTab === 'chat' && (
					<SommelierChat isLoggedIn={isLoggedIn} />
				)}

				{/* Other tab content */}
				{activeTab !== 'chat' && (
					<>
						{activeTab === 'catalog' && (
							<>
								<div className="mb-2 text-sm text-muted-foreground">
									{searchType === 'exact' ? (
										"🔍 Exact Search: Find wines by specific terms, names, or regions"
									) : (
										"🧠 Semantic Search: Find wines by description, style, or preferences"
									)}
								</div>
								<SearchInput
									value={searchTerm}
									onChange={setSearchTerm}
									onSearch={() => fetchData(1)}
									loading={loading}
									placeholder="Search wines..."
									searchType={searchType}
									onSearchTypeChange={setSearchType}
									isTextArea={false}
								/>
							</>
						)}

						{activeTab === 'cellar' && (
							<div className="mb-2 text-sm text-muted-foreground">
								🍷 Your Cellar: Browse and manage your collection of wines
							</div>
						)}

						{wines.length > 0 && totalPages > 1 && (
							<div className="text-sm text-muted-foreground mb-4">
								Showing {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, total)} of {total} results
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
									{ label: '«', page: 1 },
									{ label: '‹', page: currentPage - 1 },
									...Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
										let page: number;
										if (totalPages <= 5) page = i + 1;
										else if (currentPage <= 3) page = i + 1;
										else if (currentPage >= totalPages - 2) page = totalPages - 4 + i;
										else page = currentPage - 2 + i;
										return { label: page.toString(), page };
									}),
									{ label: '›', page: currentPage + 1 },
									{ label: '»', page: totalPages }
								].map(({ label, page }) => (
									<Button
										key={label}
										onClick={() => page >= 1 && page <= totalPages && page !== currentPage && fetchData(page)}
										disabled={loading || page === currentPage || page < 1 || page > totalPages}
										variant={currentPage === page ? "default" : "outline"}
										size="sm"
									>
										{label}
									</Button>
								))}
							</div>
						)}
					</>
				)}
			</div>
		</div>
	);
}
