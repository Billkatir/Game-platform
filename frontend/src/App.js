import React from "react";
import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate,
} from "react-router-dom";
import Register from "./components/Register";
import Login from "./components/Login";
import Lobby from "./components/Lobby"; // <-- import Lobby here

function App() {
  const isLoggedIn = () => {
    return !!localStorage.getItem("authToken"); // Check if user is logged in
  };

  return (
    <Router>
      <Routes>
        {/* Default route redirects to login */}
        <Route path="/" element={<Navigate to="/login" />} />
        <Route path="/register" element={<Register />} />
        <Route path="/login" element={<Login />} />

        {/* Add Lobby route here */}
        <Route
          path="/Lobby"
          element={isLoggedIn() ? <Lobby /> : <Navigate to="/login" />}
        />
      </Routes>
    </Router>
  );
}

export default App;
