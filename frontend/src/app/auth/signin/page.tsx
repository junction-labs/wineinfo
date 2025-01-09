'use client';

import { signIn } from "next-auth/react"
import { useState } from "react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useRouter } from 'next/navigation'
import { USERS } from "@/lib/auth";

export default function SignIn() {
    const [error, setError] = useState("")
    const router = useRouter()

    const handleSubmit = async (username: string) => {
        setError("")
        try {
            const result = await signIn("credentials", {
                username,
                password: "dummy",
                redirect: false
            })
            if (result?.error) {
                setError("Invalid username")
            } else {
                router.push("/")
            }
        } catch (err) {
            console.error("Sign in error:", err)
            setError("An error occurred during sign in")
        }
    }

    return (
        <div className="flex items-center justify-center min-h-screen bg-background">
            <Card className="w-[400px]">
                <CardHeader>
                    <CardTitle>Sign In</CardTitle>
                </CardHeader>
                <CardContent>
                    <Select
                        onValueChange={handleSubmit}
                    >
                        <SelectTrigger className="w-48">
                            <SelectValue placeholder="Select user" />
                        </SelectTrigger>
                        <SelectContent>
                            {USERS.map((user) => (
                                <SelectItem key={user} value={user}>
                                    {user}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    {error && (
                        <div className="text-red-500 text-sm">{error}</div>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}