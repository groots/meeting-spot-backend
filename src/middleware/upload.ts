// Multer storage for profile pictures (single 'file' field, image types, ≤5MB).
// Files land on the configured (ephemeral on Render) directory.
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import multer from 'multer';
import { env } from '../config/env.js';
import { MAX_FILE_SIZE_MB, ALLOWED_IMAGE_EXTENSIONS } from '../utils/constants.js';

export const profilePicturesDir = path.resolve(env.profilePicturesDir);

fs.mkdirSync(profilePicturesDir, { recursive: true });

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, profilePicturesDir),
  filename: (_req, file, cb) => {
    const ext = path.extname(file.originalname).slice(1).toLowerCase();
    cb(null, `${crypto.randomBytes(16).toString('hex')}.${ext}`);
  },
});

export const uploadProfilePicture = multer({
  storage,
  limits: { fileSize: MAX_FILE_SIZE_MB * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const ext = path.extname(file.originalname).slice(1).toLowerCase();
    if (ALLOWED_IMAGE_EXTENSIONS.includes(ext)) {
      cb(null, true);
    } else {
      cb(new Error('Invalid file type'));
    }
  },
}).single('file');
