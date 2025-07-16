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
var __rest = (this && this.__rest) || function (s, e) {
    var t = {};
    for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p) && e.indexOf(p) < 0)
        t[p] = s[p];
    if (s != null && typeof Object.getOwnPropertySymbols === "function")
        for (var i = 0, p = Object.getOwnPropertySymbols(s); i < p.length; i++) {
            if (e.indexOf(p[i]) < 0 && Object.prototype.propertyIsEnumerable.call(s, p[i]))
                t[p[i]] = s[p[i]];
        }
    return t;
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.UserModel = void 0;
const uuid_1 = require("uuid");
const bcryptjs_1 = __importDefault(require("bcryptjs"));
const jsonwebtoken_1 = __importDefault(require("jsonwebtoken"));
const database_1 = require("../config/database");
class UserModel {
    /**
     * Create a new user
     */
    static create(userData) {
        return __awaiter(this, void 0, void 0, function* () {
            const id = userData.id || (0, uuid_1.v4)();
            const now = new Date();
            // Ensure email is lowercase
            const email = userData.email ? userData.email.toLowerCase() : '';
            // Hash password if provided
            let password_hash = userData.password_hash;
            if (!password_hash && 'password' in userData && userData.password) {
                const salt = yield bcryptjs_1.default.genSalt(10);
                password_hash = yield bcryptjs_1.default.hash(userData.password, salt);
            }
            // Create user columns and values
            const columns = ['id', 'email', 'created_at', 'updated_at'];
            const values = [id, email, now, now];
            const placeholders = ['$1', '$2', '$3', '$4'];
            let paramIndex = 5;
            // Add optional fields if provided
            const optionalFields = [
                'password_hash',
                'username',
                'first_name',
                'last_name',
                'phone',
                'profile_picture_url',
                'google_oauth_id',
            ];
            for (const field of optionalFields) {
                if (field === 'password_hash' && password_hash) {
                    columns.push(field);
                    values.push(password_hash);
                    placeholders.push(`$${paramIndex++}`);
                }
                else if (field in userData && userData[field] !== undefined) {
                    columns.push(field);
                    values.push(userData[field]);
                    placeholders.push(`$${paramIndex++}`);
                }
            }
            // Insert user
            const result = yield (0, database_1.query)(`INSERT INTO users (${columns.join(', ')}) 
       VALUES (${placeholders.join(', ')}) 
       RETURNING *`, values);
            return result.rows[0];
        });
    }
    /**
     * Find user by email
     */
    static findByEmail(email) {
        return __awaiter(this, void 0, void 0, function* () {
            const result = yield (0, database_1.query)('SELECT * FROM users WHERE email = $1', [email.toLowerCase()]);
            return result.rows[0] || null;
        });
    }
    /**
     * Find user by ID
     */
    static findById(id) {
        return __awaiter(this, void 0, void 0, function* () {
            const result = yield (0, database_1.query)('SELECT * FROM users WHERE id = $1', [id]);
            return result.rows[0] || null;
        });
    }
    /**
     * Find user by Google OAuth ID
     */
    static findByGoogleId(googleId) {
        return __awaiter(this, void 0, void 0, function* () {
            const result = yield (0, database_1.query)('SELECT * FROM users WHERE google_oauth_id = $1', [googleId]);
            return result.rows[0] || null;
        });
    }
    /**
     * Update a user's Google OAuth ID
     */
    static updateGoogleId(userId, googleId) {
        return __awaiter(this, void 0, void 0, function* () {
            yield (0, database_1.query)(`UPDATE users 
       SET google_oauth_id = $1, updated_at = $2
       WHERE id = $3`, [googleId, new Date(), userId]);
        });
    }
    /**
     * Verify password
     */
    static verifyPassword(password, hashedPassword) {
        return __awaiter(this, void 0, void 0, function* () {
            return yield bcryptjs_1.default.compare(password, hashedPassword);
        });
    }
    /**
     * Generate JWT token
     */
    static generateToken(user) {
        const secretEnv = process.env.JWT_SECRET;
        if (!secretEnv) {
            console.error('JWT_SECRET is not defined. Using a default, insecure secret.');
        }
        const secretString = secretEnv || 'default_very_insecure_secret_for_dev_only';
        const secretBuffer = Buffer.from(secretString);
        const payload = {
            sub: user.id,
            email: user.email,
        };
        const options = {
            expiresIn: '24h', // Temporarily hardcode to a simple string
            algorithm: 'HS256',
        };
        return jsonwebtoken_1.default.sign(payload, secretBuffer, options);
    }
    /**
     * Convert user to safe object (remove password)
     */
    static toSafeObject(user) {
        const { password_hash } = user, safeUser = __rest(user, ["password_hash"]);
        return safeUser;
    }
}
exports.UserModel = UserModel;
