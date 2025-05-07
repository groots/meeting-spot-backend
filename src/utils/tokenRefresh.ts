/**
 * Token refresh utility for frontend
 * 
 * This file contains functions to help the frontend handle token expiration and refresh
 * Can be imported and used in frontend JavaScript/TypeScript code
 */

// Configuration (should be updated to match your deployment)
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
const TOKEN_KEY = 'auth_token'; 
const REFRESH_ENDPOINT = '/api/v1/auth/refresh';

/**
 * Get the current token from localStorage
 */
export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

/**
 * Set a token in localStorage
 */
export const setToken = (token: string): void => {
  localStorage.setItem(TOKEN_KEY, token);
};

/**
 * Parse a JWT token to get payload data
 */
export const parseToken = (token: string): any => {
  if (!token) return null;
  
  try {
    // Get the payload part of the JWT (second segment)
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (error) {
    console.error('Error parsing token:', error);
    return null;
  }
};

/**
 * Check if a token is expired
 */
export const isTokenExpired = (token: string): boolean => {
  if (!token) return true;
  
  try {
    const payload = parseToken(token);
    if (!payload || !payload.exp) return true;
    
    // Check if token is expired
    const currentTime = Math.floor(Date.now() / 1000);
    return payload.exp < currentTime;
  } catch (error) {
    console.error('Error checking token expiration:', error);
    return true;
  }
};

/**
 * Check if a token is about to expire (within 5 minutes)
 */
export const isTokenExpiringSoon = (token: string): boolean => {
  if (!token) return true;
  
  try {
    const payload = parseToken(token);
    if (!payload || !payload.exp) return true;
    
    // Check if token expires within the next 5 minutes
    const currentTime = Math.floor(Date.now() / 1000);
    const fiveMinutes = 5 * 60; // 5 minutes in seconds
    return payload.exp < (currentTime + fiveMinutes);
  } catch (error) {
    console.error('Error checking token expiration:', error);
    return true;
  }
};

/**
 * Attempt to refresh the token
 */
export const refreshToken = async (): Promise<string | null> => {
  const currentToken = getToken();
  if (!currentToken) return null;
  
  try {
    const response = await fetch(`${API_URL}${REFRESH_ENDPOINT}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${currentToken}`
      },
      body: JSON.stringify({ token: currentToken })
    });
    
    if (!response.ok) {
      // If refresh fails, clear the token
      if (response.status === 401) {
        console.log('Token refresh failed - clearing token');
        localStorage.removeItem(TOKEN_KEY);
      }
      return null;
    }
    
    const data = await response.json();
    const newToken = data.access_token;
    
    if (newToken) {
      // Save the new token
      setToken(newToken);
      return newToken;
    }
    
    return null;
  } catch (error) {
    console.error('Error refreshing token:', error);
    return null;
  }
};

/**
 * Get a valid token, refreshing if necessary
 */
export const getValidToken = async (): Promise<string | null> => {
  const token = getToken();
  
  if (!token) return null;
  
  // If token is expired or about to expire, refresh it
  if (isTokenExpired(token) || isTokenExpiringSoon(token)) {
    console.log('Token expired or expiring soon, attempting refresh');
    return await refreshToken();
  }
  
  return token;
};

/**
 * Make an authenticated API request with automatic token refresh
 */
export const authenticatedFetch = async (url: string, options: RequestInit = {}): Promise<Response | null> => {
  // Get a valid token
  const token = await getValidToken();
  
  if (!token) {
    // Redirect to login page or handle unauthenticated state
    console.error('No valid authentication token available');
    window.location.href = '/auth/login';
    return null;
  }
  
  // Set up headers with authentication
  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${token}`
  };
  
  // Make the request
  try {
    const response = await fetch(url, {
      ...options,
      headers
    });
    
    // If unauthorized and we have a token, try refreshing once
    if (response.status === 401 && token) {
      console.log('Request unauthorized, trying with fresh token');
      const newToken = await refreshToken();
      
      if (newToken) {
        // Retry with new token
        return fetch(url, {
          ...options,
          headers: {
            ...options.headers,
            'Authorization': `Bearer ${newToken}`
          }
        });
      }
    }
    
    return response;
  } catch (error) {
    console.error('Error making authenticated request:', error);
    throw error;
  }
}; 