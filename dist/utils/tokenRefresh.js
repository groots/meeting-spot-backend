"use strict";
/**
 * Token refresh utility for frontend
 *
 * This file contains functions to help the frontend handle token expiration and refresh
 * Can be imported and used in frontend JavaScript/TypeScript code
 */
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.authenticatedFetch = exports.getValidToken = exports.refreshToken = exports.isTokenExpiringSoon = exports.isTokenExpired = exports.parseToken = exports.setToken = exports.getToken = void 0;
// Configuration (should be updated to match your deployment)
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
const TOKEN_KEY = 'auth_token';
const REFRESH_ENDPOINT = '/api/v1/auth/refresh';
/**
 * Get the current token from localStorage
 */
const getToken = () => {
    return localStorage.getItem(TOKEN_KEY);
};
exports.getToken = getToken;
/**
 * Set a token in localStorage
 */
const setToken = (token) => {
    localStorage.setItem(TOKEN_KEY, token);
};
exports.setToken = setToken;
/**
 * Parse a JWT token to get payload data
 */
const parseToken = (token) => {
    if (!token)
        return null;
    try {
        // Get the payload part of the JWT (second segment)
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64)
            .split('')
            .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
            .join(''));
        return JSON.parse(jsonPayload);
    }
    catch (error) {
        console.error('Error parsing token:', error);
        return null;
    }
};
exports.parseToken = parseToken;
/**
 * Check if a token is expired
 */
const isTokenExpired = (token) => {
    if (!token)
        return true;
    try {
        const payload = (0, exports.parseToken)(token);
        if (!payload || !payload.exp)
            return true;
        // Check if token is expired
        const currentTime = Math.floor(Date.now() / 1000);
        return payload.exp < currentTime;
    }
    catch (error) {
        console.error('Error checking token expiration:', error);
        return true;
    }
};
exports.isTokenExpired = isTokenExpired;
/**
 * Check if a token is about to expire (within 5 minutes)
 */
const isTokenExpiringSoon = (token) => {
    if (!token)
        return true;
    try {
        const payload = (0, exports.parseToken)(token);
        if (!payload || !payload.exp)
            return true;
        // Check if token expires within the next 5 minutes
        const currentTime = Math.floor(Date.now() / 1000);
        const fiveMinutes = 5 * 60; // 5 minutes in seconds
        return payload.exp < currentTime + fiveMinutes;
    }
    catch (error) {
        console.error('Error checking token expiration:', error);
        return true;
    }
};
exports.isTokenExpiringSoon = isTokenExpiringSoon;
/**
 * Attempt to refresh the token
 */
const refreshToken = () => __awaiter(void 0, void 0, void 0, function* () {
    const currentToken = (0, exports.getToken)();
    if (!currentToken)
        return null;
    try {
        const response = yield fetch(`${API_URL}${REFRESH_ENDPOINT}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${currentToken}`,
            },
            body: JSON.stringify({ token: currentToken }),
        });
        if (!response.ok) {
            // If refresh fails, clear the token
            if (response.status === 401) {
                console.log('Token refresh failed - clearing token');
                localStorage.removeItem(TOKEN_KEY);
            }
            return null;
        }
        const data = yield response.json();
        const newToken = data.access_token;
        if (newToken) {
            // Save the new token
            (0, exports.setToken)(newToken);
            return newToken;
        }
        return null;
    }
    catch (error) {
        console.error('Error refreshing token:', error);
        return null;
    }
});
exports.refreshToken = refreshToken;
/**
 * Get a valid token, refreshing if necessary
 */
const getValidToken = () => __awaiter(void 0, void 0, void 0, function* () {
    const token = (0, exports.getToken)();
    if (!token)
        return null;
    // If token is expired or about to expire, refresh it
    if ((0, exports.isTokenExpired)(token) || (0, exports.isTokenExpiringSoon)(token)) {
        console.log('Token expired or expiring soon, attempting refresh');
        return yield (0, exports.refreshToken)();
    }
    return token;
});
exports.getValidToken = getValidToken;
/**
 * Make an authenticated API request with automatic token refresh
 */
const authenticatedFetch = (url_1, ...args_1) => __awaiter(void 0, [url_1, ...args_1], void 0, function* (url, options = {}) {
    // Get a valid token
    const token = yield (0, exports.getValidToken)();
    if (!token) {
        // Redirect to login page or handle unauthenticated state
        console.error('No valid authentication token available');
        window.location.href = '/auth/login';
        return null;
    }
    // Set up headers with authentication
    const headers = Object.assign(Object.assign({}, options.headers), { Authorization: `Bearer ${token}` });
    // Make the request
    try {
        const response = yield fetch(url, Object.assign(Object.assign({}, options), { headers }));
        // If unauthorized and we have a token, try refreshing once
        if (response.status === 401 && token) {
            console.log('Request unauthorized, trying with fresh token');
            const newToken = yield (0, exports.refreshToken)();
            if (newToken) {
                // Retry with new token
                return fetch(url, Object.assign(Object.assign({}, options), { headers: Object.assign(Object.assign({}, options.headers), { Authorization: `Bearer ${newToken}` }) }));
            }
        }
        return response;
    }
    catch (error) {
        console.error('Error making authenticated request:', error);
        throw error;
    }
});
exports.authenticatedFetch = authenticatedFetch;
