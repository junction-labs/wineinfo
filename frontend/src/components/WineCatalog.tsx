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
		<div className="flex gap-3 mb-4">
			<div className="flex-1 flex gap-3">
				<div className="flex-1 relative">
					<Input
						placeholder={placeholder}
						value={value}
						onChange={(
							e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
						) => onChange(e.target.value)}
						onKeyPress={(e: React.KeyboardEvent) => e.key === "Enter" && onSearch()}
						className="h-10 text-base pl-4 pr-12 transition-all duration-200 focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
					/>
					<div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400">
						🔍
					</div>
				</div>
				<Select value={searchType} onValueChange={onSearchTypeChange}>
					<SelectTrigger className="w-32 h-10 text-base">
						<SelectValue />
					</SelectTrigger>
					<SelectContent>
						<SelectItem value="exact">🔍 Exact</SelectItem>
						<SelectItem value="semantic">🧠 Semantic</SelectItem>
					</SelectContent>
				</Select>
			</div>
			<Button
				onClick={onSearch}
				disabled={loading}
				className="h-10 px-6 text-base font-semibold bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 transition-all duration-200 shadow-lg hover:shadow-xl"
			>
				{loading ? (
					<div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
				) : (
						"Search"
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
	const [descriptionExpanded, setDescriptionExpanded] = useState(false);
	const getWineType = (variety: string) => {
		const lowerVariety = variety.toLowerCase();
		if (lowerVariety.includes('pinot noir') || lowerVariety.includes('cabernet') || lowerVariety.includes('merlot') || lowerVariety.includes('syrah') || lowerVariety.includes('malbec')) {
			return 'red';
		} else if (lowerVariety.includes('chardonnay') || lowerVariety.includes('sauvignon blanc') || lowerVariety.includes('riesling') || lowerVariety.includes('pinot grigio')) {
			return 'white';
		} else if (lowerVariety.includes('rose') || lowerVariety.includes('rosé')) {
			return 'rose';
		}
		return 'other';
	};

	const wineType = getWineType(wine.variety);
	const wineTypeColors = {
		red: 'border-l-red-500 bg-red-50/50',
		white: 'border-l-yellow-500 bg-yellow-50/50',
		rose: 'border-l-pink-500 bg-pink-50/50',
		other: 'border-l-gray-500 bg-gray-50/50'
	};

	const wineTypeIcons = {
		red: '🍷',
		white: '🥂',
		rose: '🌸',
		other: '🍇'
	};

	return (
		<Card className={`transition-all duration-300 hover:shadow-lg hover:scale-[1.02] border-l-4 ${wineTypeColors[wineType]} group`}>
			<CardContent className="p-4">
				<div className="mb-3">
					<div className="flex items-start gap-2 mb-2">
						<span className="text-lg flex-shrink-0">{wineTypeIcons[wineType]}</span>
						<CardTitle
							className="text-lg font-bold text-gray-900 group-hover:text-primary transition-colors leading-tight"
						>
							{wine.title}
						</CardTitle>
					</div>
					<div className="flex items-center justify-between">
						<div className="text-sm text-muted-foreground flex items-center gap-2">
							<span className="font-medium text-gray-900 truncate" title={wine.variety}>{wine.variety}</span>
						</div>
						<div className="text-right flex-shrink-0 ml-2">
							<div className="font-medium text-gray-900">
								${wine.price}
							</div>
						</div>
					</div>
				</div>

				<div className="grid grid-cols-2 gap-3 mb-3 text-sm">
					<div className="space-y-1">
						<div className="flex items-center gap-1">
							<span className="text-muted-foreground">🌍</span>
							<span className="font-medium">{wine.country}</span>
						</div>
						<div className="flex items-center gap-1">
							<span className="text-muted-foreground">🏛️</span>
							<span className="font-medium">{wine.province}</span>
						</div>
					</div>
					<div className="space-y-1">
						<div className="flex items-center gap-1">
							<span className="text-muted-foreground">🗺️</span>
							<span className="font-medium">{wine.region_1}</span>
						</div>
						<div className="flex items-center gap-1">
							<span className="text-muted-foreground">⭐</span>
							<span className="font-medium">{wine.points} points</span>
						</div>
					</div>
				</div>

				{wine.description && (
					<div className="mb-3">
						<p className={`text-sm text-muted-foreground italic ${descriptionExpanded ? '' : 'line-clamp-2'}`}>
							"{wine.description}"
						</p>
						{wine.description.length > 100 && (
							<button
								onClick={() => setDescriptionExpanded(!descriptionExpanded)}
								className="text-xs text-purple-600 hover:text-purple-700 font-medium mt-1 transition-colors"
							>
								{descriptionExpanded ? 'Show less' : 'Read more'}
							</button>
						)}
					</div>
				)}

				{isLoggedIn && (
					<Button
						onClick={() => onCellarToggle(wine)}
						variant={inCellar ? "outline" : "default"}
						size="sm"
						className={`w-full h-9 transition-all duration-200 ${inCellar
							? 'border-red-200 text-red-700 hover:bg-red-50 hover:border-red-300'
							: 'bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700'
							}`}
					>
						{inCellar ? "🗑️ Remove" : "🍷 Add to Cellar"}
					</Button>
				)}
			</CardContent>
		</Card>
	);
}


function LoadTestingSection() {
	const [isRunning, setIsRunning] = useState(false);
	const [duration, setDuration] = useState(10);
	const [stats, setStats] = useState<{ [key: number]: number }>({});
	const [startTime, setStartTime] = useState<number | null>(null);
	const intervalRefs = useRef<NodeJS.Timeout[]>([]);

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

		intervalRefs.current.forEach(clearInterval);
		intervalRefs.current = [];

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
						[0]: (prev[0] || 0) + 1,
					}));
				}
			};

			makeRequest();
			const interval = setInterval(makeRequest, REQUEST_INTERVAL);
			intervalRefs.current.push(interval);
		});

		setTimeout(() => {
			stopLoadTest();
		}, duration * REQUEST_INTERVAL);
	};

	const stopLoadTest = () => {
		setIsRunning(false);
		intervalRefs.current.forEach(clearInterval);
		intervalRefs.current = [];
	};

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

export default function WineCatalog({ isLoggedIn }: WineCatalogProps) {
	const { data: session } = useSession();
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
		<div className="w-full max-w-6xl mx-auto p-6">
			<div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-6">
				<nav className="flex space-x-1 p-1" aria-label="Tabs">
					{tabs.map(
						(tab) =>
							!tab.hidden && (
								<Button
									key={tab.id}
									onClick={() => setActiveTab(tab.id)}
									variant="ghost"
									className={`flex-1 h-10 text-base font-medium transition-all duration-200 rounded-md ${activeTab === tab.id
										? "bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow-lg"
										: "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
										}`}
								>
									{tab.name}
								</Button>
							),
					)}
				</nav>
			</div>

			{notification && (
				<div className={`mb-4 p-3 rounded-lg border-l-4 shadow-md transition-all duration-300 ${notification.type === 'error'
					? 'bg-red-50 border-red-500 text-red-800'
					: 'bg-green-50 border-green-500 text-green-800'
					}`}>
					<div className="flex items-center gap-2">
						<span className="text-lg">
							{notification.type === 'error' ? '❌' : '✅'}
						</span>
						<span className="font-medium text-sm">{notification.message}</span>
					</div>
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
						)}

						{activeTab === 'cellar' && (
							<div className="mb-3 text-sm text-gray-600 flex items-center gap-2">
								<span>🍷</span>
								<span>Your Cellar</span>
							</div>
						)}

						{wines.length > 0 && totalPages > 1 && (
							<div className="mb-4 text-sm text-gray-500">
								Showing {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, total)} of {total} results (Page {currentPage}/{totalPages})
							</div>
						)}

						<div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
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
							<div className="flex items-center justify-center gap-2 mt-6">
								{[
									{ label: '«', page: 1, icon: '⏮️' },
									{ label: '‹', page: currentPage - 1, icon: '◀️' },
									...Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
										let page: number;
										if (totalPages <= 5) page = i + 1;
										else if (currentPage <= 3) page = i + 1;
										else if (currentPage >= totalPages - 2) page = totalPages - 4 + i;
										else page = currentPage - 2 + i;
										return { label: page.toString(), page, icon: null };
									}),
									{ label: '›', page: currentPage + 1, icon: '▶️' },
									{ label: '»', page: totalPages, icon: '⏭️' }
								].map(({ label, page, icon }) => (
									<Button
										key={label}
										onClick={() => page >= 1 && page <= totalPages && page !== currentPage && fetchData(page)}
										disabled={loading || page === currentPage || page < 1 || page > totalPages}
										variant={currentPage === page ? "default" : "outline"}
										size="sm"
										className={`h-10 px-4 font-medium transition-all duration-200 ${currentPage === page
											? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow-lg'
											: 'hover:bg-gray-50 border-gray-300'
											}`}
									>
										{icon ? icon : label}
									</Button>
								))}
							</div>
						)}
					</>
				)}
			</div>

			{/* Load Testing Section for Admin Users */}
			{session?.user?.name === "admin" && <LoadTestingSection />}
		</div>
	);
}
