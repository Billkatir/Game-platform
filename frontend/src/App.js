import React from "react";
import {
  BrowserRouter as Router,
  Route,
  Routes,
  Navigate,
} from "react-router-dom";
import Register from "./components/Register";
import Login from "./components/Login";
import Lobby from "./components/Lobby";
import TicTacToe from "./components/Games/tictactoe";

function App() {
  const isLoggedIn = () => {
    return !!localStorage.getItem("authToken");
  };

  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/login" />} />
        <Route path="/register" element={<Register />} />
        <Route path="/login" element={<Login />} />

        <Route
          path="/lobby" // Lowercase 'lobby' for consistency, though 'Lobby' works
          element={isLoggedIn() ? <Lobby /> : <Navigate to="/login" />}
        />

        <Route
          // Changed for consistency with common URL patterns and TicTacToe.jsx
          path="/game/:roomId"
          element={isLoggedIn() ? <TicTacToe /> : <Navigate to="/login" />}
        />
      </Routes>
    </Router>
  );
}

export default App;
