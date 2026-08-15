import axios from "axios";

class AuthService {
  constructor() {
    this.api = axios.create({
      baseURL:
        process.env.REACT_APP_SERVER_URL ||
        window.location.origin,
    });

    this.api.interceptors.request.use((config) => {
      const storedToken = localStorage.getItem("authToken");

      if (storedToken) {
        config.headers = {
          Authorization: `Bearer ${storedToken}`,
        };
      }

      return config;
    });
  }

  login(requestBody) {
    return this.api.post("/api/auth/login", requestBody);
  }

  signup(requestBody) {
    return this.api.post("/api/auth/signup", requestBody);
  }

  verify() {
    return this.api.get("/api/auth/verify");
  }
}

const authService = new AuthService();

export default authService;