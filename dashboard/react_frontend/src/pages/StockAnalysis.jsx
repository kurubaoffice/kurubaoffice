import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getStockAnalysis } from "../api/tidder-api.js";

import Loader from "../components/Loader";
import StockCard from "../components/StockCard";
import Chart from "../components/Chart";

export default function StockAnalysis() {
  const { symbol } = useParams();
  const [data, setData] = useState(null);

  useEffect(() => {
  // Mock data
  setData({
    price: 1620.1,
    changePercent: +2.3,
    history: [
      { date: "2023-08-01", close: 1600 },
      { date: "2023-08-02", close: 1620 },
      { date: "2023-08-03", close: 1610 },
    ],
    indicators: {
      RSI: { value: 68.5, change: -0.3 },
      MACD: { value: 1.2, change: +0.4 },
    },
  });
}, [symbol]);


  if (!data) return <Loader />;

  const { price, changePercent, history, indicators } = data;

  return (
    <div className="p-6 space-y-8">
      {/* Heading */}
      <h1 className="text-3xl font-bold text-gray-800">
        Stock Analysis: <span className="text-blue-600">{symbol}</span>
      </h1>

      {/* Current Price + Indicators */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <StockCard title="Current Price" value={price} change={changePercent} />
        {indicators &&
          Object.keys(indicators).map((key) => (
            <StockCard
              key={key}
              title={key}
              value={indicators[key].value}
              change={indicators[key].change}
            />
          ))}
      </div>

      {/* Historical Chart */}
      {history && (
        <div className="bg-white p-6 rounded-xl shadow-md">
          <h2 className="text-xl font-semibold mb-4">Price History</h2>
          <Chart data={history} dataKey="close" />
        </div>
      )}
    </div>
  );
}
