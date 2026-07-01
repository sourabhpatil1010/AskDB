// Auth types for the AskDB authentication system

export interface User {
  id: string;
  full_name: string | null;
  email: string;
  role: 'ADMIN' | 'USER';
  is_active: boolean;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  full_name: string;
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UpdateProfileRequest {
  full_name?: string;
  password?: string;
  confirm_password?: string;
}
