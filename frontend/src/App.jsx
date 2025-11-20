import React, {useState, useEffect} from "react";
import axios from "axios";
import Dashboard from "./components/Dashboard";
import Chat from "./components/Chat";

export default function App(){
  const [token, setToken] = useState(localStorage.getItem("token"));
  async function loginDemo(){
    const r = await axios.post("/api/auth/login", {username:"admin", password:"password"});
    localStorage.setItem("token", r.data.access_token);
    setToken(r.data.access_token);
  }

  return (
    <div style={{padding:20}}>
      <h1>CloudOpt Dashboard</h1>
      {!token ? <button onClick={loginDemo}>Login (demo)</button> : <>
        <Dashboard token={token} />
        <Chat token={token} />
      </>}
    </div>
  );
}