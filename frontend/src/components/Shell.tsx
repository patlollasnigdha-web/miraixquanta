import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  Activity,
  BrainCircuit,
  BriefcaseBusiness,
  ChevronLeft,
  FlaskConical,
  LayoutDashboard,
  Settings2,
  Eye,
  UserRound,
  LogOut,
  TrendingUp,
  ShieldAlert,
  LineChart,
  Cpu,
} from 'lucide-react';
import { useState } from 'react';
import { useAuth } from '../context/AuthContext';

const links = [
  ['/', 'Dashboard', LayoutDashboard],
  ['/predictions', 'AI Predictions', BrainCircuit],
  ['/paper-trading', 'Live Paper Trading', TrendingUp],
  ['/risk', 'Risk Management', ShieldAlert],
  ['/performance', 'Performance Metrics', LineChart],
  ['/watchlist', 'Watchlist', Eye],
  ['/assistant', 'AI Assistant', BrainCircuit],
  ['/backtest', 'Backtesting Lab', FlaskConical],
  ['/markets', 'Market Analysis', Activity],
  ['/monitoring', 'Latency & Efficiency', Cpu],
  ['/portfolio', 'My Portfolio', BriefcaseBusiness],
  ['/profile', 'Profile', UserRound],
  ['/settings', 'Settings', Settings2],
] as const;
export default function Shell(){const [collapsed,setCollapsed]=useState(false);const {user,logout}=useAuth();const navigate=useNavigate();async function signOut(){await logout();navigate('/login',{replace:true})}return <div className="app-shell"><aside className={'sidebar '+(collapsed?'collapsed':'')}><div className="brand"><div className="brand-mark">M</div>{!collapsed&&<div><strong>MIRAI</strong><small>Where Intelligence Creates Wealth.</small></div>}</div><nav>{links.map(([to,label,Icon])=><NavLink key={to} to={to} end={to==='/'} className={({isActive})=>'nav-item '+(isActive?'active':'')}><Icon size={17}/>{!collapsed&&<span>{label}</span>}</NavLink>)}</nav><button className="collapse" onClick={()=>setCollapsed(!collapsed)}><ChevronLeft size={16}/>{!collapsed&&'Collapse'}</button><button className="side-logout" onClick={signOut}><LogOut size={16}/><span>Log out</span></button></aside><main className="main"><header className="topbar"><div className="crumb">MIRAI <span>/</span> <b>PRIVATE WORKSPACE</b></div><div className="top-status"><span className="live-dot"/> MARKET DATA <span className="top-divider"/> <NavLink className="top-user" to="/profile"><span className="avatar">{user?.full_name?.slice(0,1).toUpperCase()||'M'}</span>{user?.full_name||'Account'}</NavLink></div></header><Outlet/></main></div>}
