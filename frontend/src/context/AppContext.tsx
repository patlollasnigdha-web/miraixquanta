import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from '../services/api';
import { SystemHealthReport } from '../types/api';

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
}

const AppContext = createContext<AppContextType | undefined>(undefined);

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
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
