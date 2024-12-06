import { useState, useEffect } from 'react';
import { Layout } from '../common/Layout';
import { wineService } from '../common/wineService';

interface FeatureFlag {
    key: string;
    value: string;
}

interface Notification {
    message: string;
    type: 'success' | 'error';
}

export default function AdminPanel() {
    const [flags, setFlags] = useState<FeatureFlag[]>([]);
    const [newFlag, setNewFlag] = useState<FeatureFlag>({
        key: '',
        value: ''
    });
    const [editingFlag, setEditingFlag] = useState<string | null>(null);
    const [notification, setNotification] = useState<Notification | null>(null);

    useEffect(() => {
        loadFlags();
    }, []);

    const loadFlags = async () => {
        try {
            const flagsData = await wineService.getFeatureFlags();
            const flagsArray = Object.entries(flagsData).map(([key, value]) => ({
                key,
                value: String(value)
            }));
            setFlags(flagsArray);
        } catch (error) {
            showNotification('Failed to load feature flags', 'error');
        }
    };

    const showNotification = (message: string, type: 'success' | 'error' = 'success') => {
        setNotification({ message, type });
        setTimeout(() => setNotification(null), 3000);
    };

    const handleSaveFlag = async (flag: FeatureFlag): Promise<void> => {
        try {
            await wineService.setFeatureFlag(flag.key, flag.value);
            showNotification(`Feature flag "${flag.key}" updated successfully`);
            setEditingFlag(null);
            await loadFlags();
        } catch (error) {
            showNotification(`Failed to update feature flag "${flag.key}"`, 'error');
        }
    };

    const handleAddFlag = async (): Promise<void> => {
        if (!newFlag.key || !newFlag.value) {
            showNotification('Please fill in both flag name and value', 'error');
            return;
        }

        try {
            await wineService.setFeatureFlag(newFlag.key, newFlag.value);
            setNewFlag({ key: '', value: '' });
            showNotification('Feature flag added successfully');
            await loadFlags();
        } catch (error) {
            showNotification('Failed to add feature flag', 'error');
        }
    };

    return (
        <Layout>
            <div className="bg-white rounded-xl shadow-lg overflow-hidden">
                {/* Header */}
                <div className="border-b border-gray-200 px-6 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                            <span className="text-xl">⚙️</span>
                            <h1 className="text-xl font-semibold text-gray-900">Feature Flags Administration</h1>
                        </div>
                        <button
                            onClick={loadFlags}
                            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
                        >
                            🔄 Refresh
                        </button>
                    </div>
                </div>

                {/* Notifications */}
                {notification && (
                    <div className={`mx-6 mt-4 p-4 rounded-lg border ${notification.type === 'error'
                            ? 'bg-red-50 border-red-200 text-red-700'
                            : 'bg-green-50 border-green-200 text-green-700'
                        }`}>
                        {notification.message}
                    </div>
                )}

                {/* Existing Flags */}
                <div className="p-6">
                    <h2 className="text-lg font-medium text-gray-900 mb-4">Existing Feature Flags</h2>
                    <div className="space-y-2">
                        {flags.map(flag => (
                            <div key={flag.key} className="grid grid-cols-12 gap-2">
                                <input
                                    type="text"
                                    value={flag.key}
                                    disabled
                                    className="col-span-5 rounded-lg border-gray-300 bg-gray-50"
                                />
                                {editingFlag === flag.key ? (
                                    <>
                                        <input
                                            type="text"
                                            value={flag.value}
                                            onChange={e => setFlags(prev =>
                                                prev.map(f =>
                                                    f.key === flag.key ? { ...f, value: e.target.value } : f
                                                )
                                            )}
                                            className="col-span-5 rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                                        />
                                        <button
                                            onClick={() => handleSaveFlag(flag)}
                                            className="col-span-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-colors"
                                        >
                                            Save
                                        </button>
                                    </>
                                ) : (
                                    <>
                                        <input
                                            type="text"
                                            value={flag.value}
                                            disabled
                                            className="col-span-5 rounded-lg border-gray-300 bg-gray-50"
                                        />
                                        <button
                                            onClick={() => setEditingFlag(flag.key)}
                                            className="col-span-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
                                        >
                                            Edit
                                        </button>
                                    </>
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Add New Flag */}
                <div className="p-6 border-t border-gray-200 bg-gray-50">
                    <h2 className="text-lg font-medium text-gray-900 mb-4">Add New Feature Flag</h2>
                    <div className="grid grid-cols-12 gap-2">
                        <input
                            type="text"
                            placeholder="Flag name"
                            value={newFlag.key}
                            onChange={e => setNewFlag(prev => ({ ...prev, key: e.target.value }))}
                            className="col-span-5 rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                        />
                        <input
                            type="text"
                            placeholder="Flag value"
                            value={newFlag.value}
                            onChange={e => setNewFlag(prev => ({ ...prev, value: e.target.value }))}
                            className="col-span-5 rounded-lg border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                        />
                        <button
                            onClick={handleAddFlag}
                            className="col-span-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-colors"
                        >
                            Add
                        </button>
                    </div>
                </div>
            </div>
        </Layout>
    );
}

