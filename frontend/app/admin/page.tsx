'use client'

import { useState } from 'react'
import { useAuth } from '@/context/auth-context'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import api from '@/lib/axios'
import { toast } from "sonner"
import Link from 'next/link'

export default function AdminPage() {
    const { user } = useAuth()
    const [text, setText] = useState('')
    const [filename, setFilename] = useState('')
    const [file, setFile] = useState<File | null>(null)
    const [activeTab, setActiveTab] = useState<'text' | 'file'>('text')
    const [loading, setLoading] = useState(false)

    if (user?.role !== 'admin') {
        return <div className="p-10">Access Denied. You are not an admin. <Link href="/chat" className="underline">Go to Chat</Link></div>
    }

    const handleIngest = async () => {
        setLoading(true)
        try {
            await api.post('/ingest', { text, filename })
            toast.success("Ingestion Successful", { description: `Ingested ${filename}` })
            setText('')
            setFilename('')
        } catch {
            toast.error("Ingestion Failed")
        } finally {
            setLoading(false)
        }
    }

    const handleFileIngest = async () => {
        if (!file) return
        setLoading(true)
        const formData = new FormData()
        formData.append('file', file)

        try {
            await api.post('/ingest/file', formData, {
                headers: {
                    'Content-Type': null as any // Allow browser to set boundary
                }
            })
            toast.success("Ingestion Successful", { description: `Ingested ${file.name}` })
            setFile(null)
            // Reset file input value manually if needed, or rely on key reset
        } catch {
            toast.error("Ingestion Failed")
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="container mx-auto p-10">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-3xl font-bold">Admin Dashboard</h1>
                <Link href="/chat"><Button variant="outline">Back to Chat</Button></Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Card>
                    <CardHeader><CardTitle>Ingest Document</CardTitle></CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex gap-4 mb-4">
                            <Button variant={activeTab === 'text' ? 'default' : 'outline'} onClick={() => setActiveTab('text')}>Text</Button>
                            <Button variant={activeTab === 'file' ? 'default' : 'outline'} onClick={() => setActiveTab('file')}>File</Button>
                        </div>

                        {activeTab === 'text' ? (
                            <>
                                <div className="space-y-2">
                                    <Label>Filename / Title</Label>
                                    <Input value={filename} onChange={e => setFilename(e.target.value)} placeholder="e.g. quarterly_report_q1.txt" />
                                </div>
                                <div className="space-y-2">
                                    <Label>Content</Label>
                                    <Textarea value={text} onChange={e => setText(e.target.value)} placeholder="Paste document text here..." rows={10} />
                                </div>
                                <Button onClick={handleIngest} disabled={loading || !text || !filename}>
                                    {loading ? 'Ingesting...' : 'Ingest Text'}
                                </Button>
                            </>
                        ) : (
                            <>
                                <div className="space-y-2">
                                    <Label>Upload File (PDF, TXT, MD)</Label>
                                    <Input
                                        type="file"
                                        accept=".pdf,.txt,.md"
                                        onChange={(e) => setFile(e.target.files?.[0] || null)}
                                    />
                                </div>
                                <Button onClick={handleFileIngest} disabled={loading || !file}>
                                    {loading ? 'Uploading...' : 'Upload & Ingest'}
                                </Button>
                            </>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
