import express from 'express';
import { geocode } from '../controllers/geocodingController.js';

const router = express.Router();

// Public proxy: forward ({ address }) or reverse ({ lat, lng }) geocoding.
// Keeps the Google Maps API key server-side.
router.post('/', geocode);

export default router;
