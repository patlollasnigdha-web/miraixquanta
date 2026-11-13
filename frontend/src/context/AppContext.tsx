import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from '../services/api';
import { SystemHealthReport } from '../types/api';

export type PageId =
  | 'overview'
  | 'explorer'
  | 'stock_detail'
  | 'watchlist'
  | 'stocks'
  | 'decision'
  | 'assistant'
  | 'portfolio'
  | 'risk'
  | 'backtest'
  | 'papertrading'
  | 'monitoring'
  | 'settings'
  | 'login'
  | 'register'
  | 'profile'
  | 'forgot_password';

export interface CompanyMetadata {
  symbol: string;
  name: string;
  sector?: string;
  exchange: string;
  has_intraday?: boolean;
  latest_price?: number;
  change_pct?: number;
  previous_close?: number;
  open?: number;
  high?: number;
  low?: number;
  volume?: number;
  bars_count?: number;
  start_date?: string;
  end_date?: string;
}

interface AppContextType {
  selectedSymbol: string;
  setSelectedSymbol: (symbol: string) => void;
  selectedPipeline: string;
  setSelectedPipeline: (pipeline: string) => void;
  availableSymbols: string[];
  backendStatus: 'ONLINE' | 'DEGRADED' | 'OFFLINE';
  ollamaStatus: 'ONLINE' | 'OFFLINE';
  healthReport: SystemHealthReport | null;
  activeSessionId: string | null;
  setActiveSessionId: (id: string | null) => void;
  refreshKey: number;
  triggerRefresh: () => void;
  lastUpdated: Date;

  // UI & Design System Extensions
  theme: 'dark' | 'light';
  toggleTheme: () => void;
  activePage: PageId;
  setActivePage: (page: PageId) => void;
  searchOpen: boolean;
  setSearchOpen: (open: boolean) => void;
  navigateToStock: (symbol: string) => void;
  recentlyViewed: string[];
  addRecentlyViewed: (symbol: string) => void;
  mobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
  companiesInventory: CompanyMetadata[];
  setCompaniesInventory: (comps: CompanyMetadata[]) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

const safeStorage = {
  getItem: (key: string): string | null => {
    try {
      if (typeof window !== 'undefined' && window.localStorage && typeof window.localStorage.getItem === 'function') {
        return window.localStorage.getItem(key);
      }
    } catch {}
    return null;
  },
  setItem: (key: string, val: string): void => {
    try {
      if (typeof window !== 'undefined' && window.localStorage && typeof window.localStorage.setItem === 'function') {
        window.localStorage.setItem(key, val);
      }
    } catch {}
  },
};

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('TCS');
  const [selectedPipeline, setSelectedPipeline] = useState<string>('pipeline_b_nifty');
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([
    'TCS', 'INFY', 'RELIANCE', 'HDFCBANK', 'ICICIBANK', 'SBIN',
    'BHARTIARTL', 'ITC', 'KOTAKBANK', 'LT', 'HINDUNILVR', 'TATAMOTORS'
  ]);
  const [backendStatus, setBackendStatus] = useState<'ONLINE' | 'DEGRADED' | 'OFFLINE'>('ONLINE');
  const [ollamaStatus, setOllamaStatus] = useState<'ONLINE' | 'OFFLINE'>('ONLINE');
  const [healthReport, setHealthReport] = useState<SystemHealthReport | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState<number>(0);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  // UI state
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const saved = safeStorage.getItem('mirai_theme');
    return (saved === 'light' || saved === 'dark') ? saved : 'dark';
  });
  const [activePage, setActivePage] = useState<PageId>('overview');
  const [searchOpen, setSearchOpen] = useState<boolean>(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);
  const [companiesInventory, setCompaniesInventory] = useState<CompanyMetadata[]>([]);
  const [recentlyViewed, setRecentlyViewed] = useState<string[]>(() => {
    try {
      const saved = safeStorage.getItem('mirai_recent_stocks');
      return saved ? JSON.parse(saved) : ['TCS', 'RELIANCE', 'INFY'];
    } catch {
      return ['TCS', 'RELIANCE', 'INFY'];
    }
  });

  // Apply theme class to HTML root
  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
      root.classList.remove('light');
    } else {
      root.classList.add('light');
      root.classList.remove('dark');
    }
    safeStorage.setItem('mirai_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const addRecentlyViewed = (symbol: string) => {
    const sym = symbol.toUpperCase().trim();
    setRecentlyViewed((prev) => {
      const filtered = prev.filter((s) => s !== sym);
      const updated = [sym, ...filtered].slice(0, 10);
      try {
        safeStorage.setItem('mirai_recent_stocks', JSON.stringify(updated));
      } catch {}
      return updated;
    });
  };

  const navigateToStock = (symbol: string) => {
    const sym = symbol.toUpperCase().trim();
    setSelectedSymbol(sym);
    addRecentlyViewed(sym);
    setActivePage('stock_detail');
    setSearchOpen(false);
    setMobileMenuOpen(false);
  };

  const triggerRefresh = () => {
    setRefreshKey((prev) => prev + 1);
    setLastUpdated(new Date());
  };

  // Poll health and symbols periodically
  useEffect(() => {
    let isMounted = true;

    const checkSystem = async () => {
      try {
        const health = await api.getHealth();
        if (!isMounted) return;
        setHealthReport(health);
        setBackendStatus(health.overall_status === 'HEALTHY' ? 'ONLINE' : 'DEGRADED');

        const ollamaComponent = health.components?.ollama || health.components?.ollama_service;
        if (ollamaComponent && (ollamaComponent.status === 'HEALTHY' || (ollamaComponent.status as string) === 'ONLINE')) {
          setOllamaStatus('ONLINE');
        } else {
          setOllamaStatus('OFFLINE');
        }
      } catch {
        if (!isMounted) return;
        setBackendStatus('OFFLINE');
        setOllamaStatus('OFFLINE');
      }

      try {
        const symsRes = await api.getSymbols();
        if (isMounted && symsRes.symbols && symsRes.symbols.length > 0) {
          setAvailableSymbols(symsRes.symbols);
        }
      } catch {
        // preserve fallback symbols
      }
    };

    checkSystem();
    const interval = setInterval(checkSystem, 30000); // Check every 30s
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [refreshKey]);

  // Global keyboard shortcut: Ctrl+K or / to open search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen((prev) => !prev);
      } else if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <AppContext.Provider
      value={{
        selectedSymbol,
        setSelectedSymbol,
        selectedPipeline,
        setSelectedPipeline,
        availableSymbols,
        backendStatus,
        ollamaStatus,
        healthReport,
        activeSessionId,
        setActiveSessionId,
        refreshKey,
        triggerRefresh,
        lastUpdated,
        theme,
        toggleTheme,
        activePage,
        setActivePage,
        searchOpen,
        setSearchOpen,
        navigateToStock,
        recentlyViewed,
        addRecentlyViewed,
        mobileMenuOpen,
        setMobileMenuOpen,
        companiesInventory,
        setCompaniesInventory,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = (): AppContextType => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
