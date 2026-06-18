import express from 'express';
import { geocode } from '../controllers/geocodingController.js';
import { geocodeLimiter } from '../middleware/rateLimit.js';

const router = express.Router();

// Public proxy: forward ({ address }) or reverse ({ lat, lng }) geocoding.
// Keeps the Google Maps API key server-side. Rate-limited to protect the
// Google Maps key/cost from abuse.
router.post('/', geocodeLimiter, geocode);

export default router;
