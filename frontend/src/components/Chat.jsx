import React, {useState} from "react";
import axios from "axios";

export default function Chat({token}){
  const [q,setQ] = useState("");
  const [resp,setResp] = useState("");
  async function ask(){
    const r = await axios.post("/api/chat", {query:q}, {headers:{Authorization:token}});
    setResp(r.data.answer || JSON.stringify(r.data));
  }
  return (
    <div>
      <h2>Chat</h2>
      <textarea value={q} onChange={e=>setQ(e.target.value)} />
      <button onClick={ask}>Ask</button>
      <pre>{resp}</pre>
    </div>
  );
}