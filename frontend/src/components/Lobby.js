// Lobby.jsx
import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";

const BACKEND_URL = process.env.REACT_APP_API_URL;

// --- Styles Definitions (that don't depend on component state) ---
const commonButtonStyles = {
  backgroundColor: "#007bff",
  color: "white",
  border: "none",
  borderRadius: "5px",
  padding: "8px 16px",
  cursor: "pointer",
  fontWeight: "600",
  margin: "5px",
  transition: "background-color 0.2s ease-in-out",
};

const successButtonStyles = {
  ...commonButtonStyles, // Inherit common styles
  backgroundColor: "#28a745", // Green color for success
};

const secondaryButtonStyles = {
  ...commonButtonStyles,
  backgroundColor: "#6c757d",
};

const warningButtonStyles = {
  ...commonButtonStyles,
  backgroundColor: "#ffc107",
  color: "#343a40",
};

const dangerButtonStyles = {
  ...commonButtonStyles,
  backgroundColor: "#dc3545",
};

const containerStyle = {
  maxWidth: "800px",
  margin: "40px auto",
  padding: "30px",
  backgroundColor: "#f9f9f9",
  borderRadius: "10px",
  boxShadow: "0 4px 20px rgba(0,0,0,0.1)",
  fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
  color: "#333",
  textAlign: "center",
};

const listContainerStyle = {
  display: "flex",
  justifyContent: "space-around",
  marginTop: "20px",
  flexWrap: "wrap",
};

const listColumnStyle = {
  flex: "1",
  minWidth: "300px",
  margin: "10px",
  padding: "20px",
  border: "1px solid #e0e0e0",
  borderRadius: "8px",
  backgroundColor: "#fff",
  boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
};

const listItemStyle = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "10px 0",
  borderBottom: "1px dashed #e9ecef",
};

const lastListItemStyle = {
  ...listItemStyle,
  borderBottom: "none",
};

const inputStyle = {
  padding: "8px",
  margin: "10px 0",
  borderRadius: "5px",
  border: "1px solid #ccc",
  width: "calc(100% - 22px)", // Adjust for padding/border
};

const dialogOverlayStyle = {
  position: "fixed",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: "rgba(0, 0, 0, 0.5)",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  zIndex: 1000,
};

const dialogContentStyle = {
  backgroundColor: "white",
  padding: "30px",
  borderRadius: "8px",
  boxShadow: "0 4px 20px rgba(0,0,0,0.2)",
  maxWidth: "400px",
  width: "90%",
  textAlign: "center",
};
// --- End Styles Definitions ---

export default function Lobby() {
  const [games, setGames] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [selectedGame, setSelectedGame] = useState(null);
  const [message, setMessage] = useState(""); // <-- message state declared here
  const [showPasswordInput, setShowPasswordInput] = useState(false);
  const [roomPassword, setRoomPassword] = useState("");
  const [roomToJoinId, setRoomToJoinId] = useState(null);
  const [confirmForceJoin, setConfirmForceJoin] = useState(false);
  const [pendingForceJoinRoomId, setPendingForceJoinRoomId] = useState(null);
  const [pendingForceJoinPassword, setPendingForceJoinPassword] = useState("");

  const navigate = useNavigate();
  const token = localStorage.getItem("authToken");

  // --- MOVE messageStyle HERE, AFTER message IS DECLARED ---
  const messageStyle = {
    backgroundColor:
      message.includes("Error") || message.includes("Failed")
        ? "#ffe0e0"
        : "#e0f7fa",
    padding: "10px",
    borderRadius: "5px",
    color:
      message.includes("Error") || message.includes("Failed")
        ? "#cc0000"
        : "#005662",
    marginBottom: "20px",
    marginTop: "10px",
  };
  // --- END MOVE ---

  const fetchAvailableGames = useCallback(async () => {
    if (!token) {
      setMessage("Authentication token missing. Please log in.");
      navigate("/login");
      return;
    }
    try {
      const response = await fetch(`${BACKEND_URL}/available_games`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setGames(data);
    } catch (error) {
      console.error("Error fetching available games:", error);
      setMessage("Failed to load available games. Please try again.");
    }
  }, [token, navigate]);

  const fetchAvailableRooms = useCallback(
    async (gameName) => {
      if (!token) return;
      try {
        const response = await fetch(
          `${BACKEND_URL}/available_rooms/${gameName}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setRooms(data);
      } catch (error) {
        console.error(`Error fetching rooms for ${gameName}:`, error);
        setMessage(`Failed to load rooms for ${gameName}.`);
      }
    },
    [token]
  );

  useEffect(() => {
    fetchAvailableGames();
    // Poll for room updates for the selected game every 5 seconds
    let roomPollingInterval;
    if (selectedGame) {
      roomPollingInterval = setInterval(() => {
        fetchAvailableRooms(selectedGame.name);
      }, 5000);
    }

    return () => {
      if (roomPollingInterval) {
        clearInterval(roomPollingInterval);
      }
    };
  }, [fetchAvailableGames, fetchAvailableRooms, selectedGame]);

  const handleCreateRoom = async () => {
    if (!token || !selectedGame) {
      setMessage("Please select a game to create a room.");
      return;
    }
    try {
      const response = await fetch(
        `${BACKEND_URL}/create_room/${selectedGame.name}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ password: roomPassword || null }),
        }
      );

      if (response.status === 409) {
        // Conflict means user is already in a room
        setMessage("You are currently in another room. Please leave it first.");
        return;
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || `HTTP error! status: ${response.status}`
        );
      }

      const newRoom = await response.json();
      setMessage(`Room ${newRoom.id} created successfully! Joining...`);
      navigate(`/game/${newRoom.id}`); // Navigate directly to the game room
    } catch (error) {
      console.error("Error creating room:", error);
      setMessage(`Failed to create room: ${error.message}`);
    }
  };

  const handleJoinRoom = async (roomId, password) => {
    if (!token) {
      setMessage("Authentication token missing. Please log in.");
      navigate("/login");
      return;
    }
    try {
      const response = await fetch(`${BACKEND_URL}/join_room/${roomId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ password: password || null }),
      });

      if (response.status === 409) {
        const errorData = await response.json();
        if (
          errorData.detail &&
          errorData.detail.includes("You are currently in another room")
        ) {
          setConfirmForceJoin(true);
          setPendingForceJoinRoomId(roomId);
          setPendingForceJoinPassword(password);
          setMessage(errorData.detail); // Display the confirmation message
          return;
        } else {
          throw new Error(
            errorData.detail || `HTTP error! status: ${response.status}`
          );
        }
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || `HTTP error! status: ${response.status}`
        );
      }

      const joinedRoom = await response.json();
      setMessage(`Joined room ${joinedRoom.id} successfully!`);
      navigate(`/game/${joinedRoom.id}`);
    } catch (error) {
      console.error("Error joining room:", error);
      setMessage(`Failed to join room: ${error.message}`);
    } finally {
      // Reset password input and dialog state after attempt
      setShowPasswordInput(false);
      setRoomPassword("");
      setRoomToJoinId(null);
    }
  };

  const handleForceJoinRoom = async () => {
    if (!token || pendingForceJoinRoomId === null) return;

    try {
      const response = await fetch(
        `${BACKEND_URL}/force_join_room/${pendingForceJoinRoomId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ password: pendingForceJoinPassword || null }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || `HTTP error! status: ${response.status}`
        );
      }

      const joinedRoom = await response.json();
      setMessage(`Force joined room ${joinedRoom.id} successfully!`);
      navigate(`/game/${joinedRoom.id}`);
    } catch (error) {
      console.error("Error force joining room:", error);
      setMessage(`Failed to force join room: ${error.message}`);
    } finally {
      setConfirmForceJoin(false);
      setPendingForceJoinRoomId(null);
      setPendingForceJoinPassword("");
      setShowPasswordInput(false);
      setRoomPassword("");
    }
  };

  const handleSelectGame = (game) => {
    setSelectedGame(game);
    setRooms([]); // Clear rooms when selecting a new game
    setMessage("");
    fetchAvailableRooms(game.name); // Fetch rooms for the selected game
  };

  const handleShowPasswordPrompt = (roomId) => {
    setRoomToJoinId(roomId);
    setShowPasswordInput(true);
  };

  const handleLogout = () => {
    localStorage.removeItem("authToken");
    navigate("/login");
  };

  return (
    <div style={containerStyle}>
      <h2 style={{ color: "#007bff" }}>Game Lobby</h2>

      {message && <p style={messageStyle}>{message}</p>}

      {/* Force Join Confirmation Dialog */}
      {confirmForceJoin && (
        <div style={dialogOverlayStyle}>
          <div style={dialogContentStyle}>
            <h3>Leave Current Room?</h3>
            <p>{message}</p> {/* Re-display the backend message */}
            <button onClick={handleForceJoinRoom} style={dangerButtonStyles}>
              Yes, Leave and Join
            </button>
            <button
              onClick={() => {
                setConfirmForceJoin(false);
                setPendingForceJoinRoomId(null);
                setPendingForceJoinPassword("");
                setMessage(""); // Clear the message
              }}
              style={secondaryButtonStyles}
            >
              No, Stay Here
            </button>
          </div>
        </div>
      )}

      <div style={listContainerStyle}>
        <div style={listColumnStyle}>
          <h3 style={{ color: "#28a745" }}>Available Games</h3>
          {games.length === 0 ? (
            <p>No games available.</p>
          ) : (
            <ul>
              {games.map((game) => (
                <li key={game.id} style={listItemStyle}>
                  <span>{game.name}</span>
                  <button
                    onClick={() => handleSelectGame(game)}
                    style={
                      selectedGame && selectedGame.id === game.id
                        ? secondaryButtonStyles
                        : commonButtonStyles
                    }
                    disabled={selectedGame && selectedGame.id === game.id}
                  >
                    {selectedGame && selectedGame.id === game.id
                      ? "Selected"
                      : "Select"}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div style={listColumnStyle}>
          <h3 style={{ color: "#17a2b8" }}>
            Rooms for {selectedGame ? selectedGame.name : "..."}
          </h3>
          {selectedGame ? (
            <>
              {rooms.length === 0 ? (
                <p>No rooms available for {selectedGame.name}. Create one!</p>
              ) : (
                <ul>
                  {rooms.map((room, index) => (
                    <li
                      key={room.id}
                      style={
                        index === rooms.length - 1
                          ? lastListItemStyle
                          : listItemStyle
                      }
                    >
                      <span>
                        Room #{room.id} ({room.password ? "Private" : "Public"})
                        - Players: {room.users ? room.users.length : 0}/
                        {room.game ? room.game.number_of_players : "?"}
                      </span>
                      <button
                        onClick={() => handleShowPasswordPrompt(room.id)}
                        style={commonButtonStyles}
                        disabled={
                          !room.available &&
                          (!room.users ||
                            room.users.length ===
                              (room.game ? room.game.number_of_players : 0))
                        }
                      >
                        {!room.available &&
                        room.users &&
                        room.users.length ===
                          (room.game ? room.game.number_of_players : 0)
                          ? "Full"
                          : "Join"}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              <div style={{ marginTop: "20px" }}>
                <h4>Create New Room</h4>
                {showPasswordInput &&
                  roomToJoinId === null && ( // Show password input for creation
                    <input
                      type="password"
                      placeholder="Set password (optional)"
                      value={roomPassword}
                      onChange={(e) => setRoomPassword(e.target.value)}
                      style={inputStyle}
                    />
                  )}
                {showPasswordInput &&
                  roomToJoinId && ( // Show password input for joining a specific room
                    <input
                      type="password"
                      placeholder="Enter password"
                      value={roomPassword}
                      onChange={(e) => setRoomPassword(e.target.value)}
                      style={inputStyle}
                    />
                  )}
                {roomToJoinId ? (
                  <>
                    <button
                      onClick={() => handleJoinRoom(roomToJoinId, roomPassword)}
                      style={commonButtonStyles}
                    >
                      Confirm Join
                    </button>
                    <button
                      onClick={() => {
                        setShowPasswordInput(false);
                        setRoomPassword("");
                        setRoomToJoinId(null);
                      }}
                      style={secondaryButtonStyles}
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={handleCreateRoom}
                      style={successButtonStyles}
                    >
                      Create Room
                    </button>
                    <button
                      onClick={() => setShowPasswordInput(!showPasswordInput)}
                      style={secondaryButtonStyles}
                    >
                      {showPasswordInput
                        ? "Hide Password Option"
                        : "Show Password Option"}
                    </button>
                  </>
                )}
              </div>
            </>
          ) : (
            <p>Select a game to see available rooms.</p>
          )}
        </div>
      </div>
      <hr style={{ margin: "30px 0", borderColor: "#eee" }} />
      <button onClick={handleLogout} style={dangerButtonStyles}>
        Logout
      </button>
    </div>
  );
}
