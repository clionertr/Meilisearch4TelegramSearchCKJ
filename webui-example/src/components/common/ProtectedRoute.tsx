import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';

export const ProtectedRoute: React.FC<{children: React.ReactNode}> = ({ children }) => {
  const { isLoggedIn } = useAuthStore();
  const navigate = useNavigate();
  
  useEffect(() => {
    if (!isLoggedIn) {
      navigate('/login');
    }
  }, [isLoggedIn, navigate]);
  
  if (!isLoggedIn) return null;
  return <>{children}</>;
};
