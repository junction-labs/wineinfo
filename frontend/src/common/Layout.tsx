import { useState, ReactNode } from 'react';
import { wineService } from './wineService';
import { Link } from 'react-router-dom';

interface User {
    username: string;
    isAdmin: boolean;
}

interface LayoutProps {
    children: ReactNode;
    onUserChange?: (user: User | undefined) => void;
}

const USERS: User[] = [
    { username: "Anonymous", isAdmin: false },
    { username: "admin", isAdmin: true },
    { username: "customer1", isAdmin: false },
    { username: "customer2", isAdmin: false },
    { username: "customer3", isAdmin: false },
    { username: "customer4", isAdmin: false },
    { username: "customer5", isAdmin: false },
    { username: "customer6", isAdmin: false },
    { username: "customer7", isAdmin: false },
    { username: "customer8", isAdmin: false },
];

export function Layout({ children, onUserChange }: LayoutProps) {
    const [currentUser, setCurrentUser] = useState<User>(USERS[0]);

    const handleUserChange = (username: string) => {
        const newUser = USERS.find(u => u.username === username) || USERS[0];
        setCurrentUser(newUser);
        wineService.setUser(newUser.username === "Anonymous" ? undefined : newUser);
        onUserChange?.(newUser.username === "Anonymous" ? undefined : newUser);
    };

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="bg-white rounded-lg shadow-sm p-4 mb-8">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center space-x-4">
                            <Link to="/" className="text-xl font-semibold text-gray-900 hover:text-gray-700">
                                Wine Catalog
                            </Link>
                        </div>

                        <div className="flex items-center space-x-4">
                            <select
                                value={currentUser.username}
                                onChange={(e) => handleUserChange(e.target.value)}
                                className="block w-48 px-3 py-2 text-sm bg-white border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                            >
                                {USERS.map((user) => (
                                    <option key={user.username} value={user.username}>
                                        {user.username}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>
                </div>
                {children}
            </div>
        </div>
    );
}