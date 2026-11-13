import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import { StatusBadge } from '../components/common/StatusBadge';
import {
  Send,
  RotateCcw,
  Bot,
  User,
  Wrench,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

interface ChatEntry {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  toolsCalled?: string[];
  verdict?: string;
  disclaimer?: string;
  timestamp: string;
}

export const AssistantPage: React.FC = () => {
  const { ollamaStatus } = useApp();
  const [conversationId, setConversationId] = useState<string>(() => `conv_${Date.now().toString(36)}`);
  const [inputQuery, setInputQuery] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [messages, setMessages] = useState<ChatEntry[]>([
    {
      id: 'welcome_1',
      role: 'assistant',
      content:
        'Greetings. I am the MIRAI Institutional Quantitative Trading Assistant. I can evaluate stocks, inspect market regimes, query portfolio holdings, simulate execution, and explain algorithmic verdicts. How can I assist you?',
      disclaimer: 'Trading financial markets involves substantial risk of loss.',
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (typeof messagesEndRef.current?.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (queryToSend?: string) => {
    const q = (queryToSend || inputQuery).trim();
    if (!q || loading) return;

    const userEntry: ChatEntry = {
      id: `usr_${Date.now()}`,
      role: 'user',
      content: q,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userEntry]);
    setInputQuery('');
    setLoading(true);

    try {
      const res = await api.askAssistant(q, conversationId);
      const botEntry: ChatEntry = {
        id: `bot_${Date.now()}`,
        role: 'assistant',
        content: res.message,
        intent: res.intent,
        toolsCalled: res.tools_called,
        verdict: res.verdict,
        disclaimer: res.disclaimer,
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, botEntry]);
    } catch (err: any) {
      const errorEntry: ChatEntry = {
        id: `err_${Date.now()}`,
        role: 'assistant',
        content: `Error communicating with MIRAI assistant: ${err.message || 'Service unavailable'}. Please verify backend status.`,
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, errorEntry]);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    try {
      await api.resetConversation(conversationId);
    } catch {
      // ignore
    }
    const newId = `conv_${Date.now().toString(36)}`;
    setConversationId(newId);
    setMessages([
      {
        id: `welcome_${Date.now()}`,
        role: 'assistant',
        content: 'Conversation history reset. You are now in a fresh trading context.',
        timestamp: new Date().toLocaleTimeString(),
      },
    ]);
  };

  const quickPrompts = [
    'Should I invest in TCS?',
    'What is the current strength of RELIANCE?',
    'Compare INFY and TCS.',
    'Explain the current market regime.',
    'How is my portfolio performing?',
    'What are the active risk limits?',
  ];

  return (
    <div className="h-[calc(100vh-6.5rem)] flex flex-col terminal-card overflow-hidden">
      {/* Assistant Header */}
      <div className="p-4 border-b border-slate-800 bg-[#111827] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-mono font-bold text-slate-100">MIRAI Quantitative Copilot</h3>
              <StatusBadge status={ollamaStatus === 'ONLINE' ? 'LLM ACTIVE' : 'DETERMINISTIC FALLBACK'} />
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Session: <span className="text-slate-300">{conversationId}</span> | 14 Backend Tools Bound
            </p>
          </div>
        </div>

        <button
          onClick={handleReset}
          title="Reset Conversation Context"
          className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-mono flex items-center gap-1.5 transition"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>New Chat</span>
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex gap-3 max-w-3xl ${m.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}
          >
            <div
              className={`w-7 h-7 rounded-full shrink-0 flex items-center justify-center text-xs font-mono font-bold ${
                m.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-800 border border-slate-700 text-blue-400'
              }`}
            >
              {m.role === 'user' ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
            </div>

            <div
              className={`rounded-lg p-4 text-xs space-y-2 ${
                m.role === 'user'
                  ? 'bg-blue-600/90 text-white shadow-md'
                  : 'bg-[#131C2E] border border-slate-800 text-slate-200'
              }`}
            >
              {/* Tool Execution Tag */}
              {m.toolsCalled && m.toolsCalled.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5 pb-2 border-b border-slate-800/80">
                  <span className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
                    <Wrench className="w-3 h-3 text-amber-400" /> Evidence Collected:
                  </span>
                  {m.toolsCalled.map((t, idx) => (
                    <span
                      key={idx}
                      className="px-1.5 py-0.5 rounded bg-slate-800 text-amber-300 text-[10px] font-mono border border-slate-700"
                    >
                      {t}
                    </span>
                  ))}
                  {m.verdict && (
                    <span className="ml-auto">
                      <StatusBadge status={m.verdict} type="verdict" />
                    </span>
                  )}
                </div>
              )}

              {/* Message Content */}
              <div className="whitespace-pre-line leading-relaxed font-sans">{m.content}</div>

              {/* Disclaimer */}
              {m.disclaimer && (
                <div className="pt-2 text-[10px] text-slate-400 font-mono border-t border-slate-800/60 italic flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3 text-slate-500" />
                  <span>{m.disclaimer}</span>
                </div>
              )}

              <div className="text-[9px] text-slate-500 font-mono text-right">{m.timestamp}</div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3 max-w-3xl">
            <div className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-blue-400">
              <Bot className="w-3.5 h-3.5" />
            </div>
            <div className="bg-[#131C2E] border border-slate-800 rounded-lg p-3 text-xs text-slate-400 flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-blue-400 animate-spin" />
              <span>Querying quantitative backend & reasoning...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Quick Prompts */}
      <div className="px-4 py-2 border-t border-slate-800 bg-[#0B0F19]/50 flex items-center gap-2 overflow-x-auto">
        <span className="text-[10px] text-slate-500 font-mono shrink-0 uppercase tracking-wider">
          Suggested:
        </span>
        {quickPrompts.map((p, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(p)}
            disabled={loading}
            className="px-2.5 py-1 rounded-full bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 text-[11px] font-mono whitespace-nowrap transition"
          >
            {p}
          </button>
        ))}
      </div>

      {/* Input Form */}
      <div className="p-3 border-t border-slate-800 bg-[#111827]">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            disabled={loading}
            placeholder="Ask about stock strength, market regimes, or investment verdicts (e.g. 'Should I invest in TCS?')..."
            className="flex-1 bg-[#0B0F19] border border-slate-700 rounded-md px-3.5 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 font-sans"
          />
          <button
            type="submit"
            disabled={!inputQuery.trim() || loading}
            className="px-4 py-2.5 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-900/40 text-white rounded-md text-xs font-mono font-semibold flex items-center gap-1.5 transition"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Send</span>
          </button>
        </form>
      </div>
    </div>
  );
};
