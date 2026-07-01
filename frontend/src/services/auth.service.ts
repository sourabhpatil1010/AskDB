import apiClient from '../lib/apiClient';
import type { User, LoginRequest, RegisterRequest, TokenResponse, UpdateProfileRequest } from '../types/auth';

export const authApi = {
  /**
   * Register a new user account.
   * Returns the created user (without password).
   */
  register: async (data: RegisterRequest): Promise<User> => {
    const res = await apiClient.post<User>('/auth/register', data);
    return res.data;
  },

  /**
   * Login with email + password.
   * Returns a JWT access token.
   */
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const res = await apiClient.post<TokenResponse>('/auth/login', data);
    return res.data;
  },

  /**
   * Logout — server-side is a no-op (JWT is stateless).
   * The store clears the token client-side.
   */
  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout');
  },

  /**
   * Fetch the currently authenticated user using the stored token.
   * Used on page refresh to rehydrate the auth state.
   */
  getMe: async (): Promise<User> => {
    const res = await apiClient.get<User>('/auth/me');
    return res.data;
  },

  /**
   * Update the authenticated user's profile (name and/or password).
   */
  updateProfile: async (data: UpdateProfileRequest): Promise<User> => {
    const res = await apiClient.put<User>('/users/profile', data);
    return res.data;
  },
};
