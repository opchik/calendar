import { json, requireUser } from '../http.js';
import { HttpError } from '../tasks.js';
import { publicUser } from '../users.js';

/** GET /api/me — текущий пользователь. */
export function handleMe(req, res) {
  if (req.method !== 'GET') throw new HttpError(405, 'Method not allowed');
  json(res, 200, { user: publicUser(requireUser(req)) });
}
