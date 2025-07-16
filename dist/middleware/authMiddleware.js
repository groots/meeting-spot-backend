"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.authenticate = void 0;
const jsonwebtoken_1 = __importDefault(require("jsonwebtoken"));
const User_1 = require("../models/User");
/**
 * Authentication middleware
 * Verifies JWT token and attaches user to request
 */
const authenticate = (req, res, next) => __awaiter(void 0, void 0, void 0, function* () {
    try {
        // Get token from headers
        const authHeader = req.headers.authorization;
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            res.status(401).json({
                error: 'Unauthorized',
                message: 'Missing or invalid token',
            });
            return;
        }
        // Extract token
        const token = authHeader.replace('Bearer ', '');
        try {
            // Verify token
            const decoded = jsonwebtoken_1.default.verify(token, process.env.JWT_SECRET || 'default_secret');
            // Get user ID
            const userId = decoded.sub;
            if (!userId) {
                res.status(401).json({
                    error: 'Unauthorized',
                    message: 'Invalid token',
                });
                return;
            }
            // Get user from database
            const user = yield User_1.UserModel.findById(userId);
            if (!user) {
                res.status(401).json({
                    error: 'Unauthorized',
                    message: 'User not found',
                });
                return;
            }
            // Attach user to request
            req.user = User_1.UserModel.toSafeObject(user);
            // Proceed to the next middleware/route handler
            next();
        }
        catch (error) {
            if (error.name === 'TokenExpiredError') {
                res.status(401).json({
                    error: 'Unauthorized',
                    message: 'Token has expired',
                });
            }
            else {
                res.status(401).json({
                    error: 'Unauthorized',
                    message: 'Invalid token',
                });
            }
        }
    }
    catch (error) {
        console.error('Auth middleware error:', error);
        res.status(500).json({
            error: 'Server error',
            message: 'Authentication error',
        });
    }
});
exports.authenticate = authenticate;
