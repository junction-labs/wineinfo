import { useState, useEffect } from 'react';
import { wineService, Wine } from './wineService';

type TabType = 'catalog' | 'cellar' | 'recommendations';

interface Notification {
  message: string;
  type: 'success' | 'error';
}

const users = [
  { id: "anonymous", name: "Logged Out" },
  { id: "customer", name: "Customer" },
  { id: "admin", name: "Admin" },
];

const App = () => {
  const [activeTab, setActiveTab] = useState<TabType>('catalog');
  const [searchTerm, setSearchTerm] = useState('');
  const [wines, setWines] = useState<Wine[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pageSize, _] = useState(12);
  const [total, setTotal] = useState(0);
  const [cellarWines, setCellarWines] = useState(new Set());
  const [notification, setNotification] = useState<Notification | null>(null);
  const [userId, setUserId] = useState(users[0].id);


  const initializeData = async () => {
    try {
      wineService.setUserId(userId);

      setSearchTerm("");
      setWines([]);
      setTotalPages(0);
      switch (activeTab) {
        case 'catalog':
          searchWines(1);
          break;

        case 'cellar':
          loadCellarWines(1);
          break;

        case 'recommendations':
          break;
      }
    } catch (err) {
      setError('Failed to load data');
      showNotification('Failed to load data', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { initializeData(); }, [activeTab]);

  const searchWines = async (page: number = 1) => {
    setLoading(true);
    setError('');

    try {
      const [data, cellarWineIds] = await Promise.all([
        wineService.searchWines({ query: searchTerm, page: page, pageSize: pageSize }),
        wineService.getAllCellarWineIds()
      ]);
      setWines(data.items);
      setCurrentPage(data.page);
      setTotalPages(data.total_pages);
      setTotal(data.total);
      setCellarWines(cellarWineIds);
    } finally {
      setLoading(false);
    }
  };

  //FIXME: Implement loadCellarWines function
  const loadCellarWines = async (page: number = 1) => {
    setLoading(true);
    setError('');

    try {
      const [data, cellarWineIds] = await Promise.all([
        wineService.searchWines({ query: searchTerm, page: page, pageSize: pageSize }),
        wineService.getAllCellarWineIds()
      ]);
      setWines(data.items);
      setCurrentPage(data.page);
      setTotalPages(data.total_pages);
      setTotal(data.total);
      setCellarWines(cellarWineIds);
    } finally {
      setLoading(false);
    }
  };

  const recommendWines = async () => {
    setLoading(true);
    setError('');

    try {
      const [data, cellarWineIds] = await Promise.all([
        wineService.recommendWines(searchTerm),
        wineService.getAllCellarWineIds()
      ]);
      setWines(data);
      setCurrentPage(1);
      setTotalPages(1);
      setTotal(data.length);
      setCellarWines(cellarWineIds);
    } finally {
      setLoading(false);
    }
  };

  const showNotification = (message: string, type: 'success' | 'error' = 'success') => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  };

  const addToCellar = async (wine: Wine): Promise<void> => {
    try {
      await wineService.addToCellar(wine.id);
      setCellarWines(prev => new Set([...prev, wine.id]));
      showNotification(`${wine.title} has been added to your cellar.`);
    } catch (err) {
      showNotification('Failed to add wine to cellar', 'error');
    }
  };

  const removeFromCellar = async (wine: Wine): Promise<void> => {
    try {
      await wineService.removeFromCellar(wine.id);
      setCellarWines(prev => {
        const next = new Set(prev);
        next.delete(wine.id);
        return next;
      });
      showNotification(`${wine.title} has been removed from your cellar.`);
    } catch (err) {
      showNotification('Failed to remove wine from cellar', 'error');
    }
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages && newPage !== currentPage) {
      switch (activeTab) {
        case 'catalog':
          searchWines(newPage);
          break;
        case 'cellar':
          loadCellarWines(newPage);
          break;
      }
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-4">
      <div className="bg-white flex justify-between">
        <div className="text-left">
          <p>Logged in as <span className="inline font-mono">{userId}</span></p>
        </div>
        <div className="text-right">
          <label htmlFor="authuser">View Page As:</label>
          <select name="authuser" defaultValue={userId} onChange={(e) => {
            setUserId(e.target.value);
            wineService.setUserId(e.target.value);
          }}>
            {
              users.map(({ id, name }) => (<option key={id} value={id}>{name}</option>))
            }
          </select>
        </div>
      </div>
      <div className="pb-10"></div>
      <div className="bg-white rounded-lg shadow-lg">
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8" aria-label="Tabs">
            {[
              { id: 'catalog', name: 'Wine Catalog' },
              { id: 'cellar', name: 'My Cellar' },
              { id: 'recommendations', name: 'Recommendations' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
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
        {error && (
          <div className={`p-4 rounded-md mb-4 'bg-red-100 text-red-800'}`}>
            <p className="text-sm">{error}</p>
          </div>
        )}

        <div className="p-4">
          {activeTab == 'catalog' && (
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                placeholder="Search wines..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && searchWines(1)}
                className="flex-1 w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={() => searchWines(1)}
                disabled={loading}
                className="w-24 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  '🔍 Search'
                )}
              </button>
            </div>
          )}
          {activeTab == 'recommendations' && (
            <div className="flex gap-2 mb-4">
              <textarea
                placeholder="Describe what you would like..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && recommendWines()}
                className="flex-1 w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={() => recommendWines()}
                disabled={loading}
                className="w-24 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  '🔍 Enter'
                )}
              </button>
            </div>
          )}

          {wines.length > 0 && totalPages > 1 && (
            <div className="text-sm text-gray-600 mb-4">
              Showing {(currentPage - 1) * pageSize + 1}-{Math.min(currentPage * pageSize, total)} of {total} results
            </div>
          )}
          <div className="grid gap-1">
            {wines.map((wine) => (
              <div key={wine.id} className="border rounded-lg p-4 hover:shadow-lg transition-shadow">
                <div className="mb-2">
                  <h3 className="text-lg font-bold">{wine.title}</h3>
                  <div className="text-sm text-gray-500 flex items-center gap-2">
                    <span className="font-semibold">{wine.winery}</span>
                    <span>•</span>
                    <span>{wine.variety}</span>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-y-2 text-sm mb-4">
                  <div>
                    <strong className="text-gray-600">Country:</strong> {wine.country}
                  </div>
                  <div>
                    <strong className="text-gray-600">Province:</strong> {wine.province}
                  </div>
                  <div>
                    <strong className="text-gray-600">Region:</strong> {wine.region_1}
                  </div>
                  <div>
                    <strong className="text-gray-600">Price:</strong>{' '}
                    <span className="text-green-600 font-semibold">${wine.price}</span>
                  </div>
                  <div>
                    <strong className="text-gray-600">Points:</strong>{' '}
                    <span className="text-purple-600 font-semibold">{wine.points}</span>
                  </div>
                </div>

                <p className="text-sm text-gray-600 mb-4 line-clamp-3">{wine.description}</p>

                <button
                  onClick={() => cellarWines.has(wine.id) ? removeFromCellar(wine) : addToCellar(wine)}
                  className={`w-full px-4 py-2 rounded-md transition-colors ${cellarWines.has(wine.id)
                    ? 'bg-gray-100 hover:bg-gray-200 text-gray-800'
                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                    }`}
                >
                  {cellarWines.has(wine.id) ? 'Remove from Cellar' : 'Add to Cellar'}
                </button>
              </div>
            ))}
          </div>
          {wines.length > 0 && totalPages > 1 && (
            <>
              <div className="flex items-center justify-center gap-2 mt-4">
                <button
                  onClick={() => handlePageChange(1)}
                  disabled={currentPage === 1 || loading}
                  className="px-3 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
                >
                  «
                </button>
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1 || loading}
                  className="px-3 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
                >
                  ‹
                </button>

                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let page;
                  if (totalPages <= 5) page = i + 1;
                  else if (currentPage <= 3) page = i + 1;
                  else if (currentPage >= totalPages - 2) page = totalPages - 4 + i;
                  else page = currentPage - 2 + i;

                  return (
                    <button
                      key={page}
                      onClick={() => handlePageChange(page)}
                      disabled={loading}
                      className={`px-3 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 ${currentPage === page ? 'bg-blue-700' : ''
                        }`}
                    >
                      {page}
                    </button>
                  );
                })}

                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages || loading}
                  className="px-3 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
                >
                  ›
                </button>
                <button
                  onClick={() => handlePageChange(totalPages)}
                  disabled={currentPage === totalPages || loading}
                  className="px-3 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
                >
                  »
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;
