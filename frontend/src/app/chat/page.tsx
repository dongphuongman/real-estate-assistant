"use client";

import { useState, useRef, useEffect } from "react";
import { Send, User, Bot, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { streamChatMessage } from "@/lib/api";
import type { ChatResponse } from "@/lib/types";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: ChatResponse["sources"];
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Hello! I'm your AI Real Estate Assistant. How can I help you find your dream property today?" }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [requestId, setRequestId] = useState<string | undefined>(undefined);
  const [lastUserMessage, setLastUserMessage] = useState<string | undefined>(undefined);
  const [errorMessage, setErrorMessage] = useState<string | undefined>(undefined);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const applyStreamError = (error: unknown) => {
    const message = error instanceof Error ? error.message : "Unknown error";
    setErrorMessage(message);
    const match = message.match(/request_id=([A-Za-z0-9_-]+)/i);
    if (match && match[1]) {
      setRequestId(match[1]);
    }
    setMessages(prev => {
      const updated = [...prev];
      const lastIdx = updated.length - 1;
      if (lastIdx >= 0 && updated[lastIdx].role === "assistant" && !updated[lastIdx].content) {
        updated[lastIdx] = {
          ...updated[lastIdx],
          content: "I apologize, but I encountered an error. Please try again.",
        };
        return updated;
      }
      return [
        ...updated,
        { role: "assistant", content: "I apologize, but I encountered an error. Please try again." },
      ];
    });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);
    setErrorMessage(undefined);
    setLastUserMessage(userMessage);

    try {
      const sid = sessionId ?? (typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : undefined);
      if (sid && !sessionId) {
        setSessionId(sid);
      }

      setMessages(prev => [...prev, { role: "assistant", content: "" }]);

      await streamChatMessage(
        { message: userMessage, session_id: sid },
        (chunk) => {
          setMessages(prev => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
              updated[lastIdx] = { ...updated[lastIdx], content: updated[lastIdx].content + chunk };
            }
            return updated;
          });
        },
        ({ requestId }) => {
          if (requestId) setRequestId(requestId);
        }
      );

    } catch (error) {
      console.warn("Chat error:", error);
      applyStreamError(error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto max-w-4xl p-4 h-[calc(100vh-4rem)] flex flex-col">
      <div className="flex-1 overflow-y-auto space-y-4 p-4 rounded-lg border bg-card shadow-sm mb-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={cn(
              "flex w-full items-start gap-4 p-4 rounded-lg",
              message.role === "user" ? "bg-muted/50" : "bg-background border"
            )}
          >
            <div className={cn(
              "flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-md border shadow",
              message.role === "user" ? "bg-background" : "bg-primary text-primary-foreground"
            )}>
              {message.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </div>
            <div className="flex-1 space-y-2 overflow-hidden">
              <div className="prose break-words dark:prose-invert text-sm leading-relaxed">
                {message.content}
              </div>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex w-full items-start gap-4 p-4 rounded-lg bg-background border" role="status" aria-label="Loading">
            <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-md border shadow bg-primary text-primary-foreground">
              <Bot className="h-4 w-4" />
            </div>
            <div className="flex items-center h-full">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          </div>
        )}
        {errorMessage && (
          <div className="flex w-full items-start gap-4 p-4 rounded-lg bg-background border">
            <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-md border shadow bg-primary text-primary-foreground">
              <Bot className="h-4 w-4" />
            </div>
            <div className="flex-1 space-y-2">
              <div className="text-sm text-red-600">{errorMessage}</div>
              <div className="text-xs text-muted-foreground">{requestId ? `request_id=${requestId}` : ""}</div>
              <button
                type="button"
                onClick={() => {
                  if (!lastUserMessage || isLoading) return;
                  setErrorMessage(undefined);
                  setIsLoading(true);
                  setMessages(prev => [...prev, { role: "assistant", content: "" }]);
                  streamChatMessage(
                    { message: lastUserMessage, session_id: sessionId },
                    (chunk) => {
                      setMessages(prev => {
                        const updated = [...prev];
                        const lastIdx = updated.length - 1;
                        if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                          updated[lastIdx] = { ...updated[lastIdx], content: updated[lastIdx].content + chunk };
                        }
                        return updated;
                      });
                    },
                    ({ requestId }) => {
                      if (requestId) setRequestId(requestId);
                    }
                  ).catch(err => {
                    console.warn("Chat retry error:", err);
                    applyStreamError(err);
                  }).finally(() => setIsLoading(false));
                }}
                className="inline-flex items-center justify-center rounded-md border px-3 py-1 text-xs font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                Retry
              </button>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex gap-4">
        <input
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
          placeholder="Ask about properties, market trends, or investment advice..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isLoading}
        />
        <button
          type="submit"
          aria-label="Send message"
          disabled={isLoading || !input.trim()}
          className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 w-12"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
