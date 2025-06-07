import React, { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";

const BACKEND_URL = process.env.REACT_APP_API_URL;

export default function TicTacToe() {
  const { roomId } = useParams();
  const navigate = useNavigate();
  const ws = useRef(null);

  const [board, setBoard] = useState(Array(9).fill(0));
  const [message, setMessage] = useState("Connecting to game...");
  const [turn, setTurn] = useState(null);
  const [playerIndex, setPlayerIndex] = useState(null);
  const [gameResult, setGameResult] = useState(null);
  const [winner, setWinner] = useState(null);
  const [showDrawOfferDialog, setShowDrawOfferDialog] = useState(false);
  const [drawOfferer, setDrawOfferer] = useState(null);

  const token = localStorage.getItem("authToken");

  const sendWsMessage = useCallback((action, payload = {}) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ action, ...payload }));
    } else {
      console.warn("WebSocket not open. Message not sent:", {
        action,
        payload,
      });
      setMessage("Connection lost. Please refresh or return to lobby.");
    }
  }, []);

  // NEW: Function to send HTTP POST request
  const sendHttpPostMove = useCallback(
    async (position, playerIndex) => {
      const url = `${BACKEND_URL}/room/${roomId}/make_move`;
      try {
        const response = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            // You might need an Authorization header here if your POST endpoint is secured
            // "Authorization": `Bearer ${token}` // Uncomment if your POST endpoint requires auth
          },
          body: JSON.stringify({ position, player_index: playerIndex }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          console.error(
            "HTTP POST Move Error:",
            errorData.detail || response.statusText
          );
          // You might want to update the UI with this error
          setMessage(`${errorData.detail || response.statusText}`);
        } else {
          const responseData = await response.json();
          console.log("HTTP POST Move Success:", responseData);
          // The WebSocket should ideally update the board, but you could use this
          // to verify or update if the WebSocket fails.
          // setBoard(responseData.new_board); // Only uncomment if you want to use HTTP response for UI update
        }
      } catch (error) {
        console.error("Failed to send HTTP POST for move:", error);
        setMessage(`Network error saving move: ${error.message}`);
      }
    },
    [BACKEND_URL, roomId] // Removed 'token' as it's commented out in usage. Add it if you enable auth.
  );

  useEffect(() => {
    if (!token || !roomId) {
      setMessage(
        "Authentication token or Room ID missing. Redirecting to lobby."
      );
      navigate("/lobby");
      return;
    }

    const wsUrl = `${BACKEND_URL.replace(/^http/, "ws")}/ws/game/${roomId}`;

    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log("WebSocket connection opened.");
      setMessage("Connected to game room. Waiting for opponent...");
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("Received data from WebSocket:", data); // Increased verbosity for debugging

      if (data.error) {
        setMessage(`Error: ${data.error}`);
        if (
          data.error === "Room full." ||
          data.error === "Invalid room ID." ||
          data.error === "Game configuration not found for this room."
        ) {
          setGameResult("error");
          if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.close(1008, data.error);
          }
        }
      } else if (data.action === "initial_state") {
        setPlayerIndex(data.player_index);
        setBoard([...data.board]); // CRITICAL: Create new array for state update
        setTurn(data.turn);
        setGameResult(null);
        setWinner(null);
        setMessage(
          `You are Player ${
            data.player_index === 0 ? "X (Player 0)" : "O (Player 1)"
          }. Player ${getSymbol(data.turn, true)}'s turn.`
        );
      } else if (data.action === "game_ready") {
        setMessage(data.message);
        if (data.current_board) setBoard([...data.current_board]); // CRITICAL: Create new array for state update
        if (data.current_turn !== undefined) setTurn(data.current_turn);
        setGameResult(null);
        setWinner(null);
        setMessage(
          `Both players connected. Game can start! Player ${getSymbol(
            data.current_turn,
            true
          )}'s turn.`
        );
      } else if (data.action === "update") {
        if (data.board) {
          console.log("Updating board with:", data.board); // Debugging: See the incoming board
          setBoard([...data.board]); // CRITICAL: Create new array for state update
        }
        if (data.current_turn !== undefined) {
          setTurn(data.current_turn);
          setMessage(`Player ${getSymbol(data.current_turn, true)}'s turn.`);
        }
        setGameResult(null);
        setWinner(null);
        setShowDrawOfferDialog(false);
        setDrawOfferer(null);
      } else if (data.action === "game_over") {
        if (data.board) setBoard([...data.board]); // CRITICAL: Create new array for state update
        setGameResult(data.result);
        if (data.result && data.result.includes("wins!")) {
          // More robust check for win message
          const winnerPlayerNum = parseInt(data.result.match(/\d+/)[0]); // Extract player number from message
          setWinner(winnerPlayerNum); // Set winner as player number (0 or 1)
          setMessage(
            `Game Over! Player ${getSymbol(winnerPlayerNum, true)} wins!`
          );
        } else if (
          data.result === "tie" ||
          data.result === "draw_agreed" ||
          data.result.includes("draw!")
        ) {
          setMessage("Game Over! It's a tie!");
        }
        setShowDrawOfferDialog(false);
        setDrawOfferer(null);
      } else if (data.action === "player_left") {
        setMessage(
          `Player ${getSymbol(
            data.player,
            true
          )} has left the room. Game ended.`
        );
        setGameResult("player_left");
      } else if (data.action === "draw_offer") {
        setDrawOfferer(data.from_player);
        setShowDrawOfferDialog(true);
        setMessage(
          `Player ${getSymbol(data.from_player, true)} has offered a draw.`
        );
      } else if (data.action === "draw_declined") {
        setMessage(
          `Player ${getSymbol(data.from_player, true)} declined the draw offer.`
        );
        setShowDrawOfferDialog(false);
        setDrawOfferer(null);
      } else if (data.action === "game_restart") {
        setBoard([...data.board]); // CRITICAL: Create new array for state update
        setTurn(0);
        setGameResult(null);
        setWinner(null);
        setShowDrawOfferDialog(false);
        setDrawOfferer(null);
        setMessage("Game restarted! Player X's turn.");
      }
    };

    ws.current.onclose = (event) => {
      console.log("WebSocket connection closed:", event);
      if (event.code === 1000) {
        setMessage("Disconnected cleanly from game.");
      } else if (event.code === 1008) {
        setMessage(`Error: ${event.reason}. Please return to lobby.`);
      } else {
        setMessage(
          `Disconnected from game. Code: ${event.code}. Reason: ${
            event.reason || "Unknown"
          }. Please return to lobby.`
        );
      }
      setGameResult("disconnected");
    };

    ws.current.onerror = (error) => {
      console.error("WebSocket error:", error);
      setMessage(
        "WebSocket error. Attempting to reconnect or return to lobby."
      );
    };

    return () => {
      if (ws.current) {
        if (ws.current.readyState === WebSocket.OPEN) {
          sendWsMessage("leave_room");
          ws.current.close(1000, "Leaving room");
        } else if (ws.current.readyState === WebSocket.CONNECTING) {
          ws.current.close();
        }
        ws.current = null;
      }
    };
  }, [roomId, navigate, sendWsMessage, token, BACKEND_URL]); // Added BACKEND_URL to dependencies

  const getSymbol = useCallback((value, isPlayerIndex = false) => {
    // Backend sends player 0 (X) and player 1 (O) for player_index.
    // Board values are 1 (X) and 2 (O).
    if (isPlayerIndex) {
      return value === 0 ? "X" : "O"; // Convert player_index (0, 1) to symbol (X, O)
    } else {
      return value === 1 ? "X" : value === 2 ? "O" : ""; // Convert board value (1, 2) to symbol (X, O)
    }
  }, []);

  const handleSquareClick = (index) => {
    if (gameResult !== null) {
      setMessage("Game is over. Cannot make a move.");
      return;
    }
    if (board[index] !== 0) {
      setMessage("This position is already taken.");
      return;
    }
    if (playerIndex === null || turn === null) {
      setMessage("Waiting for game to start or players to connect.");
      return;
    }
    if (playerIndex !== turn) {
      setMessage("It's not your turn!");
      return;
    }

    sendWsMessage("make_move", { position: index });

    // 2. Also send an HTTP POST request to explicitly update the DB (as requested)
    //    Note: The backend's WebSocket logic *already* saves to DB.
    //    This HTTP POST is redundant for core game logic but serves
    //    your request to ensure the POST router is called.
    //    If you use this, consider if you still need the DB save in the WS handler.
    sendHttpPostMove(index, playerIndex);
  };

  const handleLeaveRoom = () => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      sendWsMessage("leave_room");
    }
    navigate("/lobby");
  };

  const handleOfferDraw = () => {
    if (gameResult !== null) {
      setMessage("Game is not ongoing. Cannot offer a draw.");
      return;
    }
    if (showDrawOfferDialog) {
      setMessage("A draw offer is already pending.");
      return;
    }
    sendWsMessage("offer_draw");
  };

  const handleRespondDraw = (accept) => {
    sendWsMessage("respond_draw", { accept });
    setShowDrawOfferDialog(false);
    setDrawOfferer(null);
  };

  const handlePlayAgain = () => {
    if (
      gameResult !== "win" &&
      gameResult !== "tie" &&
      gameResult !== "draw_agreed" &&
      gameResult !== "player_left" &&
      gameResult !== "player_disconnected"
    ) {
      setMessage("Cannot restart. Game is not in a finished state.");
      return;
    }
    sendWsMessage("play_again");
  };

  const commonButtonStyles = {
    backgroundColor: "#007bff",
    color: "white",
    border: "none",
    borderRadius: 5,
    padding: "7px 15px",
    cursor: "pointer",
    fontWeight: "600",
    margin: "5px",
    transition: "background-color 0.3s",
  };

  const dangerButtonStyles = {
    ...commonButtonStyles,
    backgroundColor: "#dc3545",
  };

  const successButtonStyles = {
    ...commonButtonStyles,
    backgroundColor: "#28a745",
  };

  const squareStyle = {
    width: "100px",
    height: "100px",
    backgroundColor: "#eee",
    border: "1px solid #ccc",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    fontSize: "3em",
    fontWeight: "bold",
    cursor: gameResult ? "not-allowed" : "pointer",
    userSelect: "none",
    transition: "background-color 0.2s",
  };

  const boardStyle = {
    display: "grid",
    gridTemplateColumns: "repeat(3, 100px)",
    gridTemplateRows: "repeat(3, 100px)",
    gap: "5px",
    width: "315px",
    margin: "20px auto",
    border: "1px solid #aaa",
    padding: "5px",
    backgroundColor: "#fff",
    borderRadius: "8px",
    boxShadow: "0 2px 10px rgba(0,0,0,0.1)",
  };

  return (
    <div
      style={{
        maxWidth: 700,
        margin: "auto",
        padding: 20,
        fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
        color: "#222",
        textAlign: "center",
      }}
    >
      <h2 style={{ textAlign: "center" }}>Tic-Tac-Toe Game (Room: {roomId})</h2>
      {playerIndex !== null && (
        <p>
          You are Player:{" "}
          <strong style={{ color: playerIndex === 0 ? "#007bff" : "#dc3545" }}>
            {getSymbol(playerIndex, true)}
          </strong>{" "}
          (Player {playerIndex})
        </p>
      )}

      {message && (
        <p
          style={{
            backgroundColor: message.includes("Error") ? "#ffdddd" : "#e0f7fa",
            padding: 10,
            borderRadius: 5,
            color: message.includes("Error") ? "#a00" : "#00796b",
            marginBottom: 20,
          }}
        >
          {message}
        </p>
      )}

      <div style={boardStyle}>
        {board.map((cell, index) => (
          <div
            key={index}
            style={{
              ...squareStyle,
              color: cell === 1 ? "#007bff" : "#dc3545",
              cursor:
                gameResult || cell !== 0 || playerIndex !== turn
                  ? "not-allowed"
                  : "pointer",
            }}
            onClick={() => handleSquareClick(index)}
          >
            {getSymbol(cell, false)}
          </div>
        ))}
      </div>

      {gameResult && (
        <div style={{ marginTop: "20px" }}>
          {/* Refined winner message display based on player index mapping */}
          {gameResult.includes("win") && winner !== null && (
            <h3>Game Over! Player {getSymbol(winner, true)} wins!</h3>
          )}
          {gameResult === "tie" && <h3>It's a Tie!</h3>}
          {gameResult === "draw_agreed" && <h3>Draw agreed!</h3>}
          {gameResult === "player_left" && <h3>Opponent left the game.</h3>}
          {gameResult === "disconnected" && <h3>Disconnected from game.</h3>}
          {gameResult === "error" && <h3>A critical error occurred.</h3>}

          {(gameResult === "win" ||
            gameResult === "tie" ||
            gameResult === "draw_agreed" ||
            gameResult === "player_left" ||
            gameResult === "player_disconnected") && (
            <button onClick={handlePlayAgain} style={successButtonStyles}>
              Play Again
            </button>
          )}
        </div>
      )}

      {!gameResult && !showDrawOfferDialog && (
        <div style={{ marginTop: "20px" }}>
          <button onClick={handleOfferDraw} style={commonButtonStyles}>
            Offer Draw
          </button>
        </div>
      )}

      {showDrawOfferDialog && (
        <div
          style={{
            marginTop: "20px",
            padding: "15px",
            border: "1px solid #ffc107",
            borderRadius: "8px",
            backgroundColor: "#fff3cd",
            color: "#856404",
          }}
        >
          <p>
            Player {getSymbol(drawOfferer, true)} has offered a draw. Accept?
          </p>
          <button
            onClick={() => handleRespondDraw(true)}
            style={successButtonStyles}
          >
            Accept
          </button>
          <button
            onClick={() => handleRespondDraw(false)}
            style={dangerButtonStyles}
          >
            Decline
          </button>
        </div>
      )}

      <hr style={{ margin: "30px 0", borderColor: "#ddd" }} />

      <button onClick={handleLeaveRoom} style={dangerButtonStyles}>
        Leave Room
      </button>
    </div>
  );
}
