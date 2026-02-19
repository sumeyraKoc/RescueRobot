import { useState } from "react";
import Dashboard from "./Dashboard";
import LoginPage from "./LoginPage";
import { isAuthenticated } from "./auth";

function App() {

  const [loggedIn, setLoggedIn] = useState(isAuthenticated());

  if (!loggedIn) {

    return <LoginPage onLogin={() => setLoggedIn(true)} />;

  }

  return <Dashboard />;

}

export default App;
