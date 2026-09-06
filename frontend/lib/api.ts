import axios from "axios";
import { getToken, clearAuth, isPublicPath } from "./auth";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const api = axios.create({ baseURL: BASE, timeout: 15000 });

// Attach the staff JWT to every request so the backend can authorize it.
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    const status = err?.response?.status;
    // Session expired / not authenticated → drop creds and send to login,
    // unless we're already on a public (candidate/login) page.
    if (status === 401 && typeof window !== "undefined" && !isPublicPath(window.location.pathname)) {
      clearAuth();
      window.location.href = "/login";
    }
    const msg = err?.response?.data?.detail || err?.message || "Something went wrong";
    return Promise.reject(new Error(msg));
  }
);

// --- Auth ---
export const login = (email: string, password: string) =>
  api.post("/auth/login", { email, password }).then((r) => r.data);
export const fetchMe = () => api.get("/auth/me").then((r) => r.data);

// --- Panelists ---
export const getPanelists = () => api.get("/panelists").then((r) => r.data);
export const createPanelist = (data: any) => api.post("/panelists", data).then((r) => r.data);
export const updatePanelist = (id: string, data: any) => api.patch(`/panelists/${id}`, data).then((r) => r.data);
export const deletePanelist = (id: string) => api.delete(`/panelists/${id}`);
export const getCalendarAuthUrl = (id: string) => api.get(`/panelists/${id}/calendar-auth-url`).then((r) => r.data);

// --- Interviews ---
export const getInterviews = (status?: string) =>
  api.get("/interviews", { params: status ? { status } : {} }).then((r) => r.data);
export const createInterview = (data: any) => api.post("/interviews", data).then((r) => r.data);
export const getInterview = (id: string) => api.get(`/interviews/${id}`).then((r) => r.data);
export const updateInterview = (id: string, data: any) => api.patch(`/interviews/${id}`, data).then((r) => r.data);
export const cancelInterview = (id: string) => api.delete(`/interviews/${id}`);
export const resendInvite = (id: string) => api.post(`/interviews/${id}/resend-invite`).then((r) => r.data);

// --- Availability ---
export const getCandidateLinkData = (token: string) =>
  api.get(`/availability/candidate/${token}`).then((r) => r.data);
export const submitCandidateAvailability = (data: {
  token: string;
  selected_slot_ids: string[];
  candidate_timezone: string;
}) => api.post("/availability/candidate/submit", data).then((r) => r.data);

// --- Bookings ---
export const createBooking = (data: { interview_request_id: string; slot_id: string }) =>
  api.post("/bookings", data).then((r) => r.data);
export const getBooking = (id: string) => api.get(`/bookings/${id}`).then((r) => r.data);
export const getBookingByToken = (token: string) => api.get(`/bookings/confirm/${token}`).then((r) => r.data);
export const cancelBooking = (id: string) => api.post(`/bookings/${id}/cancel`).then((r) => r.data);
export const rescheduleBooking = (id: string) => api.post(`/bookings/${id}/reschedule`).then((r) => r.data);

// --- Analytics ---
export const getAnalytics = () => api.get("/analytics").then((r) => r.data);
export const getNotifications = () => api.get("/notifications").then((r) => r.data);
