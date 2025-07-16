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
exports.query = exports.connectToDatabase = void 0;
const pg_1 = require("pg");
const dotenv_1 = __importDefault(require("dotenv"));
dotenv_1.default.config();
// Create a pool of connections
const pool = new pg_1.Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false,
});
// Function to connect to the database
const connectToDatabase = () => __awaiter(void 0, void 0, void 0, function* () {
    try {
        // Test database connection
        const client = yield pool.connect();
        console.log('Connected to PostgreSQL database');
        client.release();
    }
    catch (error) {
        console.error('Database connection error:', error);
        throw error;
    }
});
exports.connectToDatabase = connectToDatabase;
// Function to execute a query
const query = (text_1, ...args_1) => __awaiter(void 0, [text_1, ...args_1], void 0, function* (text, params = []) {
    try {
        const start = Date.now();
        const result = yield pool.query(text, params);
        const duration = Date.now() - start;
        console.log('Executed query', { text, duration: `${duration}ms`, rows: result.rowCount });
        return result;
    }
    catch (error) {
        console.error('Query error:', error);
        throw error;
    }
});
exports.query = query;
