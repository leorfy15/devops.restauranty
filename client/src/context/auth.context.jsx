import React, { useState, useEffect } from "react";
import authService from "../services/auth.service";

const AuthContext = React.createContext();

function AuthProviderWrapper(props) {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);

  const storeToken = (token) => {
    localStorage.setItem("authToken", token);
  };

  const authenticateUser = () => {
    const storedToken = localStorage.getItem("authToken");

    if (!storedToken) {
      setIsLoggedIn(false);
      setIsLoading(false);
      setUser(null);
      setIsAdmin(false);
      return;
    }

    authService
      .verify()
      .then((response) => {
        const verifiedUser = response.data;

        console.log("Verified user:", verifiedUser);

        setUser(verifiedUser);
        setIsLoggedIn(true);
        setIsAdmin(verifiedUser.role === "admin");
        setIsLoading(false);
      })
      .catch((error) => {
        console.error("Authentication verification failed:", error);

        localStorage.removeItem("authToken");

        setIsLoggedIn(false);
        setIsLoading(false);
        setUser(null);
        setIsAdmin(false);
      });
  };

  const removeToken = () => {
    localStorage.removeItem("authToken");
  };

  const logOutUser = () => {
    removeToken();

    setIsLoggedIn(false);
    setUser(null);
    setIsAdmin(false);
  };

  useEffect(() => {
    authenticateUser();
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isLoggedIn,
        isLoading,
        user,
        isAdmin,
        storeToken,
        authenticateUser,
        logOutUser,
      }}
    >
      {props.children}
    </AuthContext.Provider>
  );
}

export { AuthProviderWrapper, AuthContext };