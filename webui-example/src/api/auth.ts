import { api } from './client';

export interface SendCodeRequest { 
  phone_number: string; 
  force_sms?: boolean; 
}

export interface SendCodeResponse { 
  auth_session_id: string; 
  expires_in: number; 
  phone_number_masked: string; 
}

export interface SignInRequest { 
  auth_session_id: string; 
  phone_number: string; 
  code: string; 
  password?: string; 
}

export interface UserInfo { 
  id: number; 
  username?: string; 
  first_name?: string; 
  last_name?: string; 
}

export interface SignInResponse { 
  token: string; 
  token_type: string; 
  expires_in: number; 
  user: UserInfo; 
}

export const authApi = {
  sendCode: (data: SendCodeRequest) => api.post<{data: SendCodeResponse}>('/auth/send-code', data),
  signIn: (data: SignInRequest) => api.post<{data: SignInResponse}>('/auth/signin', data),
  me: () => api.get<{data: {user: UserInfo, token_expires_at: string}}>('/auth/me'),
  logout: () => api.post<{data: {revoked: boolean}}>('/auth/logout'),
};
