'use client';

import { useState } from 'react';
import Link from 'next/link';
import { type User } from '@/lib/types';
import WineCatalog from '@/components/WineCatalog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";

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

export default function Home() {
  const [currentUser, setCurrentUser] = useState<User>(USERS[0]);

  const handleUserChange = (username: string) => {
    const newUser = USERS.find(u => u.username === username) || USERS[0];
    setCurrentUser(newUser);
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Card className="mb-8">
          <CardContent className="flex justify-between items-center p-4">
            <div className="flex items-center space-x-4">
              <Link
                href="/"
                className="text-xl font-semibold hover:text-muted-foreground"
              >
                Wine Catalog
              </Link>
            </div>

            <div className="flex items-center space-x-4">
              <Select
                value={currentUser.username}
                onValueChange={handleUserChange}
              >
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Select user" />
                </SelectTrigger>
                <SelectContent>
                  {USERS.map((user) => (
                    <SelectItem key={user.username} value={user.username}>
                      {user.username}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
        <WineCatalog user={currentUser.username === "Anonymous" ? undefined : currentUser} />
      </div>
    </div>
  );
}