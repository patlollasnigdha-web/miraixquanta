import {Navigate,useLocation} from 'react-router-dom'; import {useAuth} from '../context/AuthContext';
export function RequireAuth({children}:{children:React.ReactNode}){const {user,ready}=useAuth();const location=useLocation();if(!ready)return <div className="auth-loading">Loading MIRAI…</div>;return user?children:<Navigate to="/login" replace state={{from:location.pathname}}/>}
export function GuestOnly({children}:{children:React.ReactNode}){const {user,ready}=useAuth();if(!ready)return <div className="auth-loading">Loading MIRAI…</div>;return user?<Navigate to="/" replace/>:children}
