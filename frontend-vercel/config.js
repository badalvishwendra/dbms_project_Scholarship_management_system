// Public FastAPI API deployed on Render (fallback to localhost when testing locally)
if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
  window.SCHOLARSHIP_API_URL = "http://localhost:8000";
} else {
  window.SCHOLARSHIP_API_URL = "https://scholarship-management-api-02y1.onrender.com";
}
