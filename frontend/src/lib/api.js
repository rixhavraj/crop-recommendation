import axios from "axios";

const DEFAULT_API_BASE_URL = "/api";

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, "");

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});
