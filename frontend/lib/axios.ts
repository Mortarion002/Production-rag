import axios from 'axios';
import { deleteCookie, getCookie } from 'cookies-next'; // We need cookies-next or manual cookie parsing

// Since we are using standard fetch in Next.js usually, but axios is requested.
// We'll use a simple axios instance.

export const API_BASE_URL = 'http://localhost:8000'; // FastAPI backend

export function getAuthToken(): string | undefined {
  return document.cookie
    .split('; ')
    .find((row) => row.startsWith('token='))
    ?.split('=')[1];
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = getAuthToken();

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default api;
