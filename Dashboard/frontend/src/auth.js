export function login(username, password) {

  // demo credentials
  if (username === "admin" && password === "duckie123") {

    localStorage.setItem("auth", "true");
    return true;

  }

  return false;
}

export function logout() {

  localStorage.removeItem("auth");

}

export function isAuthenticated() {

  return localStorage.getItem("auth") === "true";

}
