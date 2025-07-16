"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const authController_1 = require("../controllers/authController");
const authMiddleware_1 = require("../middleware/authMiddleware");
const router = express_1.default.Router();
// Authentication routes - using the same paths as the Python backend
router.post('/register', authController_1.register);
router.post('/register/direct', authController_1.register); // Legacy endpoint, uses same handler
router.post('/login', authController_1.login);
router.post('/login/direct', authController_1.login); // Legacy endpoint, uses same handler
router.post('/direct-login', authController_1.login); // Another legacy endpoint
// Google authentication
router.post('/google/callback', authController_1.googleCallback);
// Token refresh
router.post('/refresh', authController_1.refreshToken);
// Get current user - requires authentication
router.get('/me', authMiddleware_1.authenticate, authController_1.getCurrentUser);
exports.default = router;
