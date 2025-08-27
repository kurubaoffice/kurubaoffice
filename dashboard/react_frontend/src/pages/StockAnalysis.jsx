
import Dashboard from "../pages/Dashboard.jsx";
import { getStockAnalysis } from "../api/tidder-api.js";
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import Loader from "../components/Loader";
import StockCard from "../components/StockCard";
import Chart from "../components/Chart";

export default function StockAnalysis() {
  const { symbol } = useParams();
  const [data, setData] = useState(null);

  useEffect(() => {
    getStockAnalysis(symbol).then(setData);
  }, [symbol]);

  if (!data) return <Loader />;

  const { price, changePercent, history, indicators } = data;

  return (
    <div style={{ padding: "1rem" }}>
      <h1>Stock Analysis: {symbol}</h1>

      <div style={{ display: "flex", flexWrap: "wrap" }}>
        <StockCard title="Current Price" value={price} change={changePercent} />
        {indicators && Object.keys(indicators).map((key) => (
          <StockCard
            key={key}
            title={key}
            value={indicators[key].value}
            change={indicators[key].change}
          />
        ))}
      </div>

      {history && <Chart data={history} dataKey="close" />}
    </div>
  );
}
