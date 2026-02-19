import { useEffect, useRef, useState } from "react";

import duckiebot from "./assets/duckiebot.png";
import humanIcon from "./assets/person.png";

import Header from "./Header";
import Footer from "./Footer";

export default function Dashboard() {

  const [frame, setFrame] = useState(null);

  const canvasRef = useRef(null);

  const duckImage = useRef(new Image());
  const humanImage = useRef(new Image());

  useEffect(() => {

    duckImage.current.src = duckiebot;
    humanImage.current.src = humanIcon;

    const ws = new WebSocket("ws://127.0.0.1:8000/ws");

    ws.onmessage = (event) => {

      const data = JSON.parse(event.data);

      setFrame(data.frame);

      drawMap(data.pose, data.humans);

    };

  }, []);

  return (

    <div style={styles.container}>

      <Header />

      <div style={styles.main}>

        <div style={styles.card}>

          <h3>Camera Feed</h3>

          {frame &&
            <img
              src={`data:image/jpeg;base64,${frame}`}
              style={styles.camera}
            />
          }

        </div>

        <div style={styles.card}>

          <h3>Live Map</h3>

          <canvas
            width="600"
            height="600"
            style={styles.canvas}
          />

        </div>

      </div>

      <Footer />

    </div>

  );

}

const styles = {

  container: {
    display: "flex",
    width: "99vw",
    flexDirection: "column",
    backgroundColor: "#9eb9d5"
  },

  main: {
    flex: 1,
    display: "flex",
    flexWrap: "wrap",
    justifyContent: "center",
    alignItems: "center",
    gap: "20px",
    padding: "20px"
  },

  card: {
    backgroundColor: "lightgray",
    color: "black",
    padding: "15px",
    borderRadius: "10px",
    boxShadow: "0 4px 10px rgba(0,0,0,0.1)"
  },

  camera: {
    width: "640px",
    maxWidth: "90vw",
    borderRadius: "8px"
  },

  canvas: {
    border: "1px solid #ccc",
    borderRadius: "8px",
    maxWidth: "90vw"
  }

};
