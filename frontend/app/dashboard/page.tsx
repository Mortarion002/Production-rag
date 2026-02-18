'use client'

import { useAuth } from '@/context/auth-context'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import Link from 'next/link'
import { MessageSquare, Upload, Lock } from 'lucide-react'

export default function Dashboard() {
    const { user, logout } = useAuth()

    return (
        <div className="container mx-auto p-10">
            <div className="flex justify-between items-center mb-10">
                <h1 className="text-3xl font-bold">Dashboard</h1>
                <div className="flex items-center gap-4">
                    <span>Welcome, {user?.email}</span>
                    <Button variant="outline" onClick={logout}>Sign Out</Button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card className="hover:shadow-lg transition-shadow cursor-pointer border-primary/20">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <MessageSquare className="w-6 h-6 text-primary" />
                            Start Chatting
                        </CardTitle>
                        <CardDescription>
                            Interact with your uploaded PDF documents using AI. Ask questions and get instant answers.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Link href="/chat">
                            <Button className="w-full">Open Chat &rarr;</Button>
                        </Link>
                    </CardContent>
                </Card>

                <Card className={`hover:shadow-lg transition-shadow border-primary/20 ${user?.role !== 'admin' ? 'opacity-80' : 'cursor-pointer'}`}>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            {user?.role === 'admin' ? (
                                <Upload className="w-6 h-6 text-primary" />
                            ) : (
                                <Lock className="w-6 h-6 text-muted-foreground" />
                            )}
                            Upload Documents
                        </CardTitle>
                        <CardDescription>
                            Add new documents to your knowledge base. Supported formats: PDF, TXT, MD.
                            {user?.role !== 'admin' && <span className="block mt-2 text-red-500 font-semibold text-xs">Admin Access Only</span>}
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {user?.role === 'admin' ? (
                            <Link href="/admin">
                                <Button className="w-full" variant="secondary">Upload Files &rarr;</Button>
                            </Link>
                        ) : (
                            <Button className="w-full" variant="ghost" disabled>Locked</Button>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
