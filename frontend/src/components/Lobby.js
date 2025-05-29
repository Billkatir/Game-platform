import React, { useEffect, useState } from "react";

const BACKEND_URL = process.env.REACT_APP_API_URL;

export default function Lobby() {
  const [games, setGames] = useState([]);
  const [expandedGameId, setExpandedGameId] = useState(null);
  const [rooms, setRooms] = useState([]);
  const [myRoom, setMyRoom] = useState(null);
  const [creatingRoomPassword, setCreatingRoomPassword] = useState("");
  const [joinPasswords, setJoinPasswords] = useState({});
  const [loadingRooms, setLoadingRooms] = useState(false);
  const [message, setMessage] = useState("");
  const [roomCounts, setRoomCounts] = useState({});
  // NEW STATE: To store the dynamically fetched user count for *my* room
  const [myRoomUserCount, setMyRoomUserCount] = useState({
    user_count: 0,
    max_players: 0,
  });

  const token = localStorage.getItem("authToken");
  const authHeaders = {
    "Content-Type": "application/json",
    Accept: "application/json",
    "Cache-Control": "no-cache",
    Authorization: `Bearer ${token}`,
  };

  useEffect(() => {
    fetch(`${BACKEND_URL}/available_games`, { headers: authHeaders })
      .then((res) => res.json())
      .then(setGames)
      .catch(() => setMessage("Failed to load games."));
  }, []);

  useEffect(() => {
    if (!expandedGameId) {
      setRooms([]);
      setRoomCounts({});
      return;
    }
    const selectedGame = games.find((g) => g.id === expandedGameId);
    if (!selectedGame) return;

    setLoadingRooms(true);
    fetch(`${BACKEND_URL}/available_rooms/${selectedGame.name}`, {
      headers: authHeaders,
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load rooms");
        return res.json();
      })
      .then(async (data) => {
        setRooms(Array.isArray(data) ? data : []);
        setLoadingRooms(false);

        const newRoomCounts = {};
        const fetchPromises = (Array.isArray(data) ? data : []).map(
          async (room) => {
            try {
              const countRes = await fetch(
                `${BACKEND_URL}/user_count/${room.id}`,
                { headers: authHeaders }
              );
              if (countRes.ok) {
                const countData = await countRes.json();
                newRoomCounts[room.id] = {
                  user_count: countData.user_count,
                  max_players: countData.max_players,
                };
              } else {
                console.warn(
                  `Failed to fetch user count for room ${room.id}:`,
                  countRes.status
                );
                newRoomCounts[room.id] = {
                  user_count: 0,
                  max_players: room.game?.number_of_players || 0,
                };
              }
            } catch (error) {
              console.error(
                `Error fetching user count for room ${room.id}:`,
                error
              );
              newRoomCounts[room.id] = {
                user_count: 0,
                max_players: room.game?.number_of_players || 0,
              };
            }
          }
        );

        await Promise.all(fetchPromises);
        setRoomCounts(newRoomCounts);
      })
      .catch(() => {
        setMessage("Failed to load rooms.");
        setLoadingRooms(false);
      });
  }, [expandedGameId, games]);

  const fetchMyRoom = () => {
    fetch(`${BACKEND_URL}/my_room`, { headers: authHeaders })
      .then((res) => (res.ok ? res.json() : null))
      .then(setMyRoom)
      .catch(() => setMyRoom(null));
  };

  useEffect(() => {
    fetchMyRoom();
  }, []);

  // NEW useEffect: Fetch user count for myRoom when myRoom state changes
  useEffect(() => {
    if (myRoom && myRoom.id) {
      fetch(`${BACKEND_URL}/user_count/${myRoom.id}`, { headers: authHeaders })
        .then((res) => res.json())
        .then((data) => {
          if (data.user_count !== undefined) {
            setMyRoomUserCount({
              user_count: data.user_count,
              max_players:
                data.max_players || myRoom.game?.number_of_players || 0,
            });
          }
        })
        .catch((error) => {
          console.error("Error fetching my room user count:", error);
          setMyRoomUserCount({
            user_count: 0,
            max_players: myRoom.game?.number_of_players || 0,
          });
        });
    } else {
      setMyRoomUserCount({ user_count: 0, max_players: 0 }); // Reset if not in a room
    }
  }, [myRoom, authHeaders]); // Depend on myRoom and authHeaders

  const createRoom = () => {
    if (!expandedGameId) {
      setMessage("Select a game first.");
      return;
    }
    const selectedGame = games.find((g) => g.id === expandedGameId);
    if (!selectedGame) return;

    fetch(`${BACKEND_URL}/create_room/${selectedGame.name}`, {
      method: "POST",
      headers: authHeaders,
      body: JSON.stringify({ password: creatingRoomPassword || null }),
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to create room");
        return res.json();
      })
      .then((room) => {
        setMessage(`Room created! ID: ${room.id}`);
        setCreatingRoomPassword("");
        fetchMyRoom();
      })
      .catch(() => setMessage("Failed to create room."));
  };

  const joinRoom = (roomId) => {
    fetch(`${BACKEND_URL}/join_room/${roomId}`, {
      method: "POST",
      headers: authHeaders,
      body: JSON.stringify({ password: joinPasswords[roomId] || null }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || "Failed to join room");
        }
        return res.json();
      })
      .then((room) => {
        setMessage(`Joined room ID: ${room.id}`);
        setJoinPasswords((prev) => ({ ...prev, [roomId]: "" }));
        fetchMyRoom();
      })
      .catch((e) => setMessage(e.message));
  };

  const leaveRoom = () => {
    fetch(`${BACKEND_URL}/leave_room`, {
      method: "POST",
      headers: authHeaders,
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to leave room");
        return res.json();
      })
      .then(() => {
        setMessage("Left the room.");
        fetchMyRoom();
      })
      .catch(() => setMessage("Failed to leave room."));
  };

  return (
    <div
      style={{
        maxWidth: 700,
        margin: "auto",
        padding: 20,
        fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
        color: "#222",
      }}
    >
      <h2 style={{ textAlign: "center" }}>Lobby</h2>
      {message && (
        <p
          style={{
            backgroundColor: "#ffdddd",
            padding: 10,
            borderRadius: 5,
            color: "#a00",
          }}
        >
          {message}
        </p>
      )}

      <section>
        <h3>Available Games</h3>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 12,
            marginBottom: 20,
          }}
        >
          {games.map((game) => (
            <button
              key={game.id}
              onClick={() =>
                setExpandedGameId((id) => (id === game.id ? null : game.id))
              }
              style={{
                padding: "10px 20px",
                borderRadius: 8,
                border:
                  expandedGameId === game.id
                    ? "2px solid #007bff"
                    : "2px solid #ccc",
                backgroundColor:
                  expandedGameId === game.id ? "#cce5ff" : "white",
                cursor: "pointer",
                fontWeight: "600",
                minWidth: 120,
                transition: "background-color 0.3s, border-color 0.3s",
              }}
            >
              {game.name}
            </button>
          ))}
        </div>
      </section>

      {expandedGameId && (
        <section
          style={{
            padding: 20,
            border: "1px solid #ddd",
            borderRadius: 8,
            marginBottom: 40,
            backgroundColor: "#f9f9f9",
          }}
        >
          <h3>
            Rooms for{" "}
            {games.find((g) => g.id === expandedGameId)?.name ||
              "Selected Game"}
          </h3>

          {loadingRooms ? (
            <p>Loading rooms...</p>
          ) : !Array.isArray(rooms) || rooms.length === 0 ? (
            <p>No rooms available.</p>
          ) : (
            <ul style={{ listStyleType: "none", paddingLeft: 0 }}>
              {rooms.map((room) => {
                const playerCount = roomCounts[room.id]?.user_count || 0;
                const maxPlayers =
                  roomCounts[room.id]?.max_players ||
                  games.find((g) => g.id === expandedGameId)
                    ?.number_of_players ||
                  0;

                return (
                  <li
                    key={room.id}
                    style={{
                      padding: 12,
                      borderBottom: "1px solid #ddd",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      flexWrap: "wrap",
                    }}
                  >
                    <div>
                      <strong>Room ID:</strong> {room.id} |{" "}
                      <strong>Players:</strong> {playerCount}/{maxPlayers}{" "}
                      {room.password ? "🔒" : "🔓"}
                    </div>
                    <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
                      <input
                        type="password"
                        placeholder="Password"
                        value={joinPasswords[room.id] || ""}
                        onChange={(e) =>
                          setJoinPasswords((prev) => ({
                            ...prev,
                            [room.id]: e.target.value,
                          }))
                        }
                        style={{
                          padding: "6px 10px",
                          borderRadius: 4,
                          border: "1px solid #ccc",
                          minWidth: 120,
                        }}
                      />
                      <button
                        onClick={() => joinRoom(room.id)}
                        style={{
                          backgroundColor: "#007bff",
                          color: "white",
                          border: "none",
                          borderRadius: 5,
                          padding: "7px 15px",
                          cursor: "pointer",
                          fontWeight: "600",
                        }}
                      >
                        Join Room
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}

          <div
            style={{
              marginTop: 20,
              paddingTop: 10,
              borderTop: "1px solid #ccc",
              display: "flex",
              gap: 12,
              flexWrap: "wrap",
              alignItems: "center",
            }}
          >
            <input
              type="password"
              placeholder="Room Password (optional)"
              value={creatingRoomPassword}
              onChange={(e) => setCreatingRoomPassword(e.target.value)}
              style={{
                flexGrow: 1,
                padding: "8px 12px",
                borderRadius: 6,
                border: "1px solid #ccc",
                minWidth: 200,
              }}
            />
            <button
              onClick={createRoom}
              style={{
                backgroundColor: "#28a745",
                color: "white",
                border: "none",
                borderRadius: 6,
                padding: "10px 20px",
                fontWeight: "700",
                cursor: "pointer",
                minWidth: 120,
              }}
            >
              Create Room
            </button>
          </div>
        </section>
      )}

      {myRoom && (
        <section
          style={{
            padding: 20,
            border: "1px solid #ddd",
            borderRadius: 8,
            backgroundColor: "#fff3cd",
          }}
        >
          <h3>Your Current Room</h3>
          <p>
            <strong>Room ID:</strong> {myRoom.id} | <strong>Game:</strong>{" "}
            {myRoom.game?.name} | <strong>Players:</strong>{" "}
            {/* USE myRoomUserCount HERE */}
            {myRoomUserCount.user_count}/{myRoomUserCount.max_players}
          </p>
          <button
            onClick={leaveRoom}
            style={{
              backgroundColor: "#dc3545",
              color: "white",
              border: "none",
              borderRadius: 6,
              padding: "10px 20px",
              fontWeight: "700",
              cursor: "pointer",
            }}
          >
            Leave Room
          </button>
        </section>
      )}
    </div>
  );
}
