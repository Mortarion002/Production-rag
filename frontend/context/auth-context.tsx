'use client'

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import axios from '@/lib/axios';

interface User {
    email: string;
    role: string;
}

interface AuthContextType {
    user: User | null;
    login: (email: string, password: str) => Promise<void>;
    signup: (email: string, password: str) => Promise<void>;
    logout: () => void;
    loading: bool;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        // hydrating user from token would require an endpoint /me
        // optimization: decode token client side or call /me
        // for now, we leave it simple: if token exists, we assume logged in? 
        // better to decode JWT payload locally to get role/email immediately
        const token = document.cookie.replace(/(?:(?:^|.*;\s*)token\s*\=\s*([^;]*).*$)|^.*$/, "$1");
        if (token) {
            try {
                const base64Url = token.split('.')[1];
                const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
                const jsonPayload = decodeURIComponent(atob(base64).split('').map(function (c) {
                    return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                }).join(''));
                const payload = JSON.parse(jsonPayload);
                setUser({ email: payload.sub, role: payload.role });
            } catch (e) {
                console.error("Failed to decode token", e);
            }
        }
        setLoading(false);
    }, []);

    const login = async (email: str, password: str) => {
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

            // Decode and set user
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(atob(base64).split('').map(function (c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));
            const payload = JSON.parse(jsonPayload);
            setUser({ email: payload.sub, role: payload.role });

            router.push('/chat');
        } catch (error) {
            console.error('Login failed', error);
            throw error;
        }
    };

    const signup = async (email: str, password: str) => {
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
