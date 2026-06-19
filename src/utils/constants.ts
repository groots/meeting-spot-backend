// Place category definitions and food subcategory filters.
// Ported verbatim from the Python reference (app/utils/constants.py +
// the PLACE_CATEGORIES / FOOD_SUBCATEGORIES in app/utils/location.py).

export const PLACE_CATEGORIES: Record<string, string[]> = {
  Accommodation: ['lodging', 'hotel', 'campground', 'rv_park'],
  'Food & Drink': ['restaurant', 'cafe', 'bakery', 'bar', 'meal_takeaway', 'meal_delivery'],
  'Night Life': ['bar', 'night_club', 'casino'],
  'Fun & Family': ['amusement_park', 'aquarium', 'park', 'bowling_alley', 'movie_theater', 'zoo'],
  Cultural: ['museum', 'art_gallery', 'library', 'tourist_attraction', 'place_of_worship'],
  Shopping: ['shopping_mall', 'department_store', 'supermarket', 'clothing_store', 'electronics_store'],
  Transport: ['transit_station', 'train_station', 'subway_station', 'bus_station', 'airport'],

  // Labels emitted by the frontend LocationTypeSelector. Only the first type is
  // used for the Nearby Search query, so the leading entry is the primary match.
  'Restaurant / Food': ['restaurant'],
  Cafe: ['cafe'],
  Bar: ['bar'],
  'Meeting Space': ['cafe'],
  Hotel: ['lodging'],
  Park: ['park'],
  Library: ['library'],
  Other: ['point_of_interest'],
};

export interface FoodSubcategoryFilter {
  min_price_level?: number;
  max_price_level?: number;
  min_rating?: number;
  max_rating?: number;
  types: string[];
  keywords: string[];
}

export const FOOD_SUBCATEGORIES: Record<string, FoodSubcategoryFilter> = {
  'fine dining': {
    min_price_level: 3,
    min_rating: 4.0,
    types: ['restaurant'],
    keywords: ['fine dining', 'upscale', 'gourmet'],
  },
  'hole in the wall': {
    max_price_level: 2,
    min_rating: 3.0,
    max_rating: 4.5,
    types: ['restaurant', 'cafe', 'meal_takeaway'],
    keywords: ['local', 'authentic', 'hidden gem'],
  },
  'cheap eats': {
    max_price_level: 1,
    min_rating: 3.5,
    types: ['restaurant', 'cafe', 'meal_takeaway', 'meal_delivery'],
    keywords: ['cheap', 'affordable', 'budget'],
  },
  vegetarian: {
    types: ['restaurant', 'cafe'],
    keywords: ['vegetarian', 'vegan', 'plant based'],
  },
  'outdoor seating': {
    types: ['restaurant', 'cafe', 'bar'],
    keywords: ['outdoor', 'patio', 'terrace', 'alfresco'],
  },
  'quick bite': {
    max_price_level: 2,
    types: ['fast_food', 'cafe', 'meal_takeaway'],
    keywords: ['fast', 'quick', 'express'],
  },
};

// File upload limits (profile pictures)
export const MAX_FILE_SIZE_MB = 5;
export const ALLOWED_IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif'];

// Auth
export const TOKEN_EXPIRY_HOURS = 24;

// Google Maps API endpoints
export const GEOCODING_API_URL = 'https://maps.googleapis.com/maps/api/geocode/json';
export const PLACES_NEARBY_URL = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json';
export const PLACE_PHOTO_URL = 'https://maps.googleapis.com/maps/api/place/photo';
