"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getUserIdFromToken = exports.isTokenExpiringSoon = exports.isTokenExpired = exports.parseToken = void 0;
const jsonwebtoken_1 = __importDefault(require("jsonwebtoken"));
/**
 * Parse a JWT token to get payload data
 */
const parseToken = (token) => {
    if (!token)
        return null;
    try {
        // Decode the token
        return jsonwebtoken_1.default.decode(token);
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
 * Verify a token and extract user ID
 */
const getUserIdFromToken = (token) => {
    try {
        const decoded = jsonwebtoken_1.default.verify(token, process.env.JWT_SECRET || 'default_secret');
        return decoded.sub;
    }
    catch (error) {
        return null;
    }
};
exports.getUserIdFromToken = getUserIdFromToken;
