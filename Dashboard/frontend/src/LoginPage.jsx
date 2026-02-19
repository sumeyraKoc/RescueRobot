import { useState } from "react";
import { login } from "./auth.js";

export default function LoginPage({ onLogin }) {

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  function handleLogin() {

    if (login(username, password)) {
      onLogin();
    } else {
      setError("Invalid credentials");
    }

  }

  return (

    <div style={styles.container}>

      <div style={styles.overlay}></div>

      <div style={styles.card}>

        <h1 style={styles.title}>Duckie Dashboard</h1>

        <p style={styles.subtitle}>Robot Monitoring System</p>

        <input
          placeholder="Username"
          value={username}
          onChange={e => setUsername(e.target.value)}
          style={styles.input}
        />

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          style={styles.input}
        />

        <button onClick={handleLogin} style={styles.button}>
          Login
        </button>

        {error && (
          <div style={styles.error}>{error}</div>
        )}

      </div>

    </div>

  );

}

const styles = {

  container: {

    position: "fixed",
    top: 0,
    left: 0,

    width: "100vw",
    height: "100vh",

    display: "flex",
    justifyContent: "center",
    alignItems: "center",

    background: "linear-gradient(135deg, #0f172a, #1e293b)",

    padding: "20px",
    boxSizing: "border-box"

  },

  overlay: {

    position: "absolute",
    width: "100%",
    height: "100%",
    background: "rgba(0,0,0,0.3)",
    zIndex: 0

  },

  card: {

    position: "relative",
    zIndex: 1,

    width: "100%",
    maxWidth: "400px",

    background: "white",

    padding: "40px 30px",

    borderRadius: "12px",

    boxShadow: "0 10px 30px rgba(0,0,0,0.3)",

    display: "flex",
    flexDirection: "column",
    gap: "15px"

  },

  title: {

    margin: 0,
    textAlign: "center",
    fontSize: "clamp(22px, 4vw, 28px)"

  },

  subtitle: {

    margin: 0,
    textAlign: "center",
    color: "#64748b",
    fontSize: "clamp(14px, 3vw, 16px)"

  },

  input: {

    padding: "12px",

    fontSize: "16px",

    borderRadius: "6px",

    border: "1px solid #cbd5e1",

    outline: "none"

  },

  button: {

    padding: "12px",

    fontSize: "16px",

    borderRadius: "6px",

    border: "none",

    background: "#0f172a",

    color: "white",

    cursor: "pointer",

    transition: "0.2s"

  },

  error: {

    color: "red",
    textAlign: "center",
    fontSize: "14px"

  }

};
