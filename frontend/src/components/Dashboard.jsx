import React, {useEffect, useState} from "react";
import axios from "axios";
import { BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts';

export default function Dashboard({token}){
  const [metrics, setMetrics] = useState([]);
  useEffect(() => {
    axios.get("/api/metrics/current", {headers:{Authorization:token}}).then(r => setMetrics(r.data.items));
  }, [token]);

  const summary = metrics.reduce((acc, m) => {
    acc[m.provider] = (acc[m.provider] || 0) + 1;
    return acc;
  }, {});

  const chartData = Object.keys(summary).map(k => ({name:k, value:summary[k]}));

  return (
    <div>
      <h2>Inventory Summary</h2>
      <BarChart width={400} height={200} data={chartData}><XAxis dataKey="name"/><YAxis/><Tooltip/><Bar dataKey="value" /></BarChart>
    </div>
  );
}