import { logout } from "./auth";


export default function Header() {

  return (

    <header style={styles.header}>

      <div style={styles.left}>
        🤖 Duckie Rescue Dashboard
      </div>

      <div style={styles.right}>
        <span style={styles.statusDot}></span>
        Connected
      </div>

      <button
        onClick={() => {
          logout();
          window.location.reload();
        }}
      >
        Logout
      </button>

    </header>

  );

}

const styles = {

  header: {
    height: "60px",
    backgroundColor: "#0f172a",
    color: "white",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0 20px",
    fontSize: "18px",
    fontWeight: "bold"
  },

  left: {},

  right: {
    display: "flex",
    alignItems: "center",
    gap: "10px"
  },

  statusDot: {
    width: "10px",
    height: "10px",
    backgroundColor: "lime",
    borderRadius: "50%"
  }

};
