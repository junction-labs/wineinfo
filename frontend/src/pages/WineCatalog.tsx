import { useState, useEffect } from 'react';
import { wineService, Wine } from '../common/wineService';
import { Layout } from '../common/Layout';

type TabType = 'catalog' | 'cellar' | 'recommendations';
type NotificationType = 'success' | 'error';

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

const SearchInput: React.FC<SearchInputProps> = ({
    value,
    onChange,
    onSearch,
    loading,
    placeholder,
    isTextArea = false
}) => {
    const InputComponent = isTextArea ? 'textarea' : 'input';

    return (
        <div className="flex gap-2 mb-4">
            <InputComponent
                placeholder={placeholder}
                value={value}
                onChange={(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => onChange(e.target.value)}
                onKeyPress={(e: React.KeyboardEvent) => e.key === 'Enter' && onSearch()}
                className="flex-1 w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
                onClick={onSearch}
                disabled={loading}
                className="w-24 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
            >
                {loading ? (
                    <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                    '🔍 Search'
                )}
            </button>
        </div>
    );
};

const WineCard: React.FC<WineCardProps> = ({ wine, inCellar, onCellarToggle, isLoggedIn }) => (
    <div className="border rounded-lg p-4 hover:shadow-lg transition-shadow">
        <div className="mb-2">
            <h3 className="text-lg font-bold">{wine.title}</h3>
            <div className="text-sm text-gray-500 flex items-center gap-2">
                <span className="font-semibold">{wine.winery}</span>
                <span>•</span>
                <span>{wine.variety}</span>
            </div>
        </div>

        <div className="grid grid-cols-3 gap-y-2 text-sm mb-4">
            <div><strong className="text-gray-600">Country:</strong> {wine.country}</div>
            <div><strong className="text-gray-600">Province:</strong> {wine.province}</div>
            <div><strong className="text-gray-600">Region:</strong> {wine.region_1}</div>
            <div><strong className="text-gray-600">Price:</strong> <span className="text-green-600 font-semibold">${wine.price}</span></div>
            <div><strong className="text-gray-600">Points:</strong> <span className="text-purple-600 font-semibold">{wine.points}</span></div>
        </div>

        <p className="text-sm text-gray-600 mb-4 line-clamp-3">{wine.description}</p>

        {isLoggedIn && (
            <button
                onClick={() => onCellarToggle(wine)}
                className={`w-full px-4 py-2 rounded-md transition-colors ${inCellar ? 'bg-gray-100 hover:bg-gray-200 text-gray-800' : 'bg-blue-600 hover:bg-blue-700 text-white'
                    }`}
            >
                {inCellar ? 'Remove from Cellar' : 'Add to Cellar'}
            </button>
        )}
    </div>
);

const WineCatalog: React.FC = () => {
    const [activeTab, setActiveTab] = useState<TabType>('catalog');
    const [searchTerm, setSearchTerm] = useState('');
    const [wines, setWines] = useState<Wine[]>([]);
    const [loading, setLoading] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [total, setTotal] = useState(0);
    const [cellarWines, setCellarWines] = useState(new Set<number>());
    const [notification, setNotification] = useState<Notification | null>(null);

    const pageSize = 12;
    const isLoggedIn: boolean = wineService.getUser() !== undefined;

    const showNotification = (message: string, type: NotificationType = 'success') => {
        setNotification({ message, type });
        setTimeout(() => setNotification(null), 10000);
    };

    const fetchData = async (page: number = 1) => {
        if (activeTab === 'recommendations' && !searchTerm.trim()) {
            setWines([]);
            setCurrentPage(1);
            setTotalPages(1);
            setTotal(0);
            return;
        }

        setLoading(true);
        try {
            let wineData: Wine[], totalPages: number, total: number;
            const cellarWines = await wineService.getCellarWines();

            if (activeTab === 'catalog') {
                const data = await wineService.searchWines({
                    query: searchTerm,
                    page,
                    pageSize
                });
                wineData = data.items;
                totalPages = data.total_pages;
                total = data.total;
            } else if (activeTab === 'recommendations') {
                wineData = await wineService.recommendWines(searchTerm);
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
            setCellarWines(new Set(cellarWines.map(wine => wine.id)));
        } catch (err) {
            showNotification(`Failed to load data: ${err}`, 'error');
        } finally {
            setLoading(false);
        }
    };

    const handleCellarToggle = async (wine: Wine) => {
        try {
            if (cellarWines.has(wine.id)) {
                await wineService.removeFromCellar(wine.id);
                setCellarWines(prev => {
                    const next = new Set(prev);
                    next.delete(wine.id);
                    return next;
                });
                if (activeTab === 'cellar') {
                    setWines(prev => prev.filter(w => w.id !== wine.id));
                    setTotal(prev => prev - 1);
                }
                showNotification(`${wine.title} has been removed from your cellar.`);
            } else {
                await wineService.addToCellar(wine.id);
                setCellarWines(prev => new Set([...prev, wine.id]));
                showNotification(`${wine.title} has been added to your cellar.`);
            }
        } catch (err) {
            showNotification(`Failed to update cellar: ${err}`, 'error');
        }
    };

    useEffect(() => {
        setSearchTerm('');
        setWines([]);
        setTotalPages(0);
        fetchData(1);
    }, [activeTab]);

    const tabs = [
        { id: 'catalog' as TabType, name: 'Wine Catalog' },
        { id: 'cellar' as TabType, name: 'My Cellar', hidden: !isLoggedIn },
        { id: 'recommendations' as TabType, name: 'Recommendations' }
    ];

    return (
        <Layout onUserChange={() => fetchData(1)}>
            <div className="w-full max-w-4xl mx-auto p-4">
                <div className="border-b border-gray-200">
                    <nav className="flex px-6 space-x-8" aria-label="Tabs">
                        {tabs.map((tab) => !tab.hidden && (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`
                  whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm
                  ${activeTab === tab.id
                                        ? 'border-blue-500 text-blue-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }
                `}
                            >
                                {tab.name}
                            </button>
                        ))}
                    </nav>
                </div>

                {notification && (
                    <div className={`mb-4 p-4 rounded-lg ${notification.type === 'error' ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'
                        }`}>
                        {notification.message}
                    </div>
                )}

                <div className="p-4">
                    {(activeTab === 'catalog' || activeTab === 'recommendations') && (
                        <SearchInput
                            value={searchTerm}
                            onChange={setSearchTerm}
                            onSearch={() => fetchData(1)}
                            loading={loading}
                            placeholder={activeTab === 'catalog' ? "Search wines..." : "Describe what you would like..."}
                            isTextArea={activeTab === 'recommendations'}
                        />
                    )}

                    {wines.length > 0 && totalPages > 1 && (
                        <div className="text-sm text-gray-600 mb-4">
                            Showing {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, total)} of {total} results
                        </div>
                    )}

                    <div className="grid gap-1">
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
                                <button
                                    key={label}
                                    onClick={() => page >= 1 && page <= totalPages && page !== currentPage && fetchData(page)}
                                    disabled={loading || page === currentPage || page < 1 || page > totalPages}
                                    className={`px-3 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 
                    ${currentPage === page ? 'bg-blue-700' : ''}`}
                                >
                                    {label}
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </Layout>
    );
};

export default WineCatalog;