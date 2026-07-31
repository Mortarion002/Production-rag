'use client'

import { useState, useRef, useEffect } from 'react'
import { useAuth } from '@/context/auth-context'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { API_BASE_URL, getAuthToken } from '@/lib/axios'
import { parseSSEEvents } from '@/lib/sse'
import { Send, User as UserIcon, Bot, LogOut } from 'lucide-react'

interface Message {
    role: 'user' | 'assistant';
    content: string;
    steps?: string[];
}

export default function ChatPage() {
    const { user, logout } = useAuth()
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const [liveSteps, setLiveSteps] = useState<string[]>([])
    const scrollRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollIntoView({ behavior: 'smooth' })
        }
    }, [messages])

    const handleSend = async () => {
        if (!input.trim()) return

        const userMsg: Message = { role: 'user', content: input }
        setMessages(prev => [...prev, userMsg])
        setInput('')
        setLoading(true)
        setLiveSteps([])

        try {
            const token = getAuthToken()
            const response = await fetch(`${API_BASE_URL}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({ question: userMsg.content }),
            })

            if (!response.ok || !response.body) {
                throw new Error(`Request failed with status ${response.status}`)
            }

            const reader = response.body.getReader()
            const decoder = new TextDecoder()
            let buffer = ''
            let streamDone = false

            while (!streamDone) {
                const { value, done: readerDone } = await reader.read()
                streamDone = readerDone
                if (!value) continue

                buffer += decoder.decode(value, { stream: true })
                const { events, remainder } = parseSSEEvents(buffer)
                buffer = remainder

                for (const evt of events) {
                    if (evt.event === 'step') {
                        const { label } = JSON.parse(evt.data) as { node: string; label: string }
                        setLiveSteps(prev => [...prev, label])
                    } else if (evt.event === 'done') {
                        const data = JSON.parse(evt.data) as { answer: string | null; steps: string[] }
                        const botMsg: Message = {
                            role: 'assistant',
                            content: data.answer || "Sorry, I couldn't generate an answer.",
                            steps: data.steps,
                        }
                        setMessages(prev => [...prev, botMsg])
                    } else if (evt.event === 'error') {
                        const { detail } = JSON.parse(evt.data) as { detail: string }
                        throw new Error(detail)
                    }
                }
            }
        } catch (error) {
            console.error(error)
            const errorMsg: Message = { role: 'assistant', content: "Error communicating with server." }
            setMessages(prev => [...prev, errorMsg])
        } finally {
            setLoading(false)
            setLiveSteps([])
        }
    }

    return (
        <div className="flex flex-col h-screen bg-background">
            {/* Header */}
            <header className="flex items-center justify-between px-6 py-4 border-b">
                <h1 className="text-xl font-bold">Advanced RAG Chat</h1>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2">
                        <Avatar className="h-8 w-8">
                            <AvatarFallback>{user?.email[0].toUpperCase()}</AvatarFallback>
                        </Avatar>
                        <span className="text-sm font-medium">{user?.email}</span>
                        {user?.role === 'admin' && <Badge variant="secondary">Admin</Badge>}
                    </div>
                    <Button variant="ghost" size="icon" onClick={logout}>
                        <LogOut className="h-5 w-5" />
                    </Button>
                </div>
            </header>

            {/* Chat Area */}
            <div className="flex-1 overflow-hidden p-4">
                <ScrollArea className="h-full pr-4">
                    <div className="flex flex-col gap-4 max-w-3xl mx-auto">
                        {messages.map((m, i) => (
                            <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                                <Avatar className="h-8 w-8">
                                    {m.role === 'user' ? (
                                        <AvatarFallback>U</AvatarFallback>
                                    ) : (
                                        <AvatarFallback className="bg-primary text-primary-foreground">AI</AvatarFallback>
                                    )}
                                </Avatar>
                                <div className={`space-y-2 ${m.role === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
                                    <Card className={`p-3 max-w-[80%] ${m.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>
                                        <div className="whitespace-pre-wrap text-sm">{m.content}</div>
                                    </Card>
                                    {m.steps && (
                                        <div className="flex flex-wrap gap-2">
                                            {m.steps.map((step, idx) => (
                                                <Badge key={idx} variant="outline" className="text-xs text-muted-foreground">{step}</Badge>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                        <div ref={scrollRef} />
                        {loading && (
                            <div className="flex gap-3">
                                <Avatar className="h-8 w-8"><AvatarFallback className="bg-primary text-primary-foreground">AI</AvatarFallback></Avatar>
                                <Card className="p-3 bg-muted space-y-1">
                                    {liveSteps.length === 0 ? (
                                        <div className="text-sm animate-pulse">Thinking...</div>
                                    ) : (
                                        liveSteps.map((step, idx) => (
                                            <div
                                                key={idx}
                                                className={`text-sm ${idx === liveSteps.length - 1 ? 'animate-pulse' : 'text-muted-foreground'}`}
                                            >
                                                {step}
                                            </div>
                                        ))
                                    )}
                                </Card>
                            </div>
                        )}
                    </div>
                </ScrollArea>
            </div>

            {/* Input Area */}
            <div className="p-4 border-t">
                <div className="max-w-3xl mx-auto flex gap-2">
                    <Input
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleSend()}
                        placeholder="Ask a question..."
                        disabled={loading}
                    />
                    <Button onClick={handleSend} disabled={loading}>
                        <Send className="h-4 w-4" />
                    </Button>
                </div>
            </div>
        </div>
    )
}
