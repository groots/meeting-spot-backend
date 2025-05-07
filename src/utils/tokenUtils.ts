import jwt from 'jsonwebtoken';

/**
 * Parse a JWT token to get payload data
 */
export const parseToken = (token: string): any | null => {
  if (!token) return null;
  
  try {
    // Decode the token
    return jwt.decode(token);
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
 * Verify a token and extract user ID
 */
export const getUserIdFromToken = (token: string): string | null => {
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET || 'default_secret') as jwt.JwtPayload;
    return decoded.sub as string;
  } catch (error) {
    return null;
  }
}; 