import axios from 'axios';
import { deleteCookie, getCookie } from 'cookies-next'; // We need cookies-next or manual cookie parsing

// Since we are using standard fetch in Next.js usually, but axios is requested.
// We'll use a simple axios instance.

const api = axios.create({
  baseURL: 'http://localhost:8000', // FastAPI backend
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    // Client-side: Read token from document.cookie or storage
    // For now simple regex or library
    const token = document.cookie
      .split('; ')
      .find((row) => row.startsWith('token='))
      ?.split('=')[1];

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default api;
