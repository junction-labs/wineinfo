import CredentialsProvider from "next-auth/providers/credentials"
import type { NextAuthOptions } from 'next-auth'


export const USERS: string[] = [
    "admin",
    "customer1",
    "customer2",
    "customer3",
    "customer4",
    "customer5"
]

export const authOptions: NextAuthOptions = {
    providers: [
        CredentialsProvider({
            name: 'Credentials',
            credentials: {
                username: { label: "Username", type: "text" },
                password: { label: "Password", type: "password" }
            },
            async authorize(credentials) {
                if (!credentials?.username) return null;
                if (!USERS.includes(credentials.username)) return null;
                const user = {
                    name: credentials.username,
                    email: `${credentials.username}@example.com`,
                    id: USERS.indexOf(credentials.username).toString()
                };
                return user;
            }
        })
    ],
    pages: {
        signIn: '/auth/signin',
    },
    callbacks: {
        session: async ({ session, token }) => {
            if (session?.user) {
                session.user.id = token.sub;
            }
            return session;
        },
        jwt: async ({ user, token }) => {
            if (user) {
                token.uid = user.id;
            }
            return token;
        },
    },
    secret: "my-jwt-secret-123",
    session: {
        strategy: "jwt"
    }
}
