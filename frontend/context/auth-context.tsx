'use client'

import React, { createContext, useContext, useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from '@/lib/axios';

interface User {
    email: string;
    role: string;
}

interface AuthContextType {
    user: User | null;
    login: (email: string, password: string) => Promise<void>;
    signup: (email: string, password: string) => Promise<void>;
    logout: () => void;
    loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function decodeUserFromToken(token: string): User | null {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(function (c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        const payload = JSON.parse(jsonPayload);
        return { email: payload.sub, role: payload.role };
    } catch (e) {
        console.error("Failed to decode token", e);
        return null;
    }
}

function getUserFromCookie(): User | null {
    if (typeof document === 'undefined') return null;
    const token = document.cookie.replace(/(?:(?:^|.*;\s*)token\s*\=\s*([^;]*).*$)|^.*$/, "$1");
    return token ? decodeUserFromToken(token) : null;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
    // Lazy initializer instead of an effect+setState roundtrip: this needs to
    // be SSR-safe (no `document` on the server), so getUserFromCookie() guards
    // on typeof document, and the client's first render already has the
    // decoded user available instead of one extra render later.
    const [user, setUser] = useState<User | null>(getUserFromCookie);
    // Kept for AuthContextType compatibility; always false since the user is
    // now resolved synchronously by the lazy initializer above, no async gap.
    const loading = false;
    const router = useRouter();

    const login = async (email: string, password: string) => {
        try {
            const formData = new FormData();
            formData.append('username', email);
            formData.append('password', password);

            const res = await axios.post('/auth/token', formData, {
                headers: { 'Content-Type': 'multipart/form-data' } // OAuth2PasswordRequestForm expects form data
            });

            const token = res.data.access_token;
            // Set cookie
            document.cookie = `token=${token}; path=/; max-age=1800; SameSite=Strict`; // 30 mins

            setUser(decodeUserFromToken(token));

            router.push('/chat');
        } catch (error) {
            console.error('Login failed', error);
            throw error;
        }
    };

    const signup = async (email: string, password: string) => {
        try {
            await axios.post('/auth/signup', { email, password });
            // Auto login or redirect to login? Redirect to login for now.
            router.push('/login');
        } catch (error) {
            console.error('Signup failed', error);
            throw error;
        }
    };

    const logout = () => {
        document.cookie = "token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT";
        setUser(null);
        router.push('/login');
    };

    return (
        <AuthContext.Provider value={{ user, login, signup, logout, loading }}>
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
