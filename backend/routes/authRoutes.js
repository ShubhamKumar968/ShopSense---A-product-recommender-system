import { Router } from 'express';
import { register, login, refreshToken } from '../controllers/authController.js';

const router = Router();

// Public auth routes — no JWT required
router.post('/register', register);
router.post('/login', login);
router.post('/refresh', refreshToken);

export default router;
