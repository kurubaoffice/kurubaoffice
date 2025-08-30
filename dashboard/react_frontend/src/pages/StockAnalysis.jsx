import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getStockAnalysis, getStockList } from "../api/tidder-api.js";

import Loader from "../components/Loader";
import StockCard from "../components/StockCard";
import Chart from "../components/Chart";

// uvicorn api.main:app --reload --port 8000
export default function StockAnalysis() {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [stockList, setStockList] = useState([]);
  const [loadingList, setLoadingList] = useState(true);

  // Fetch stock list on mount
  useEffect(() => {
    getStockList()
      .then((list) => {
        console.log("Fetched stock list:", list);
        setStockList(list || []);
      })
      .catch((err) => {
        console.error("Error fetching stock list:", err);
        setStockList([]);
      })
      .finally(() => setLoadingList(false));
  }, []);

  // Fetch stock analysis when symbol changes
  useEffect(() => {
    if (!symbol) return;
    async function fetchData() {
      try {
        const result = await getStockAnalysis(symbol);
        setData(result);
      } catch (err) {
        console.error("Error fetching stock data:", err);
      }
    }
    fetchData();
  }, [symbol]);

  // Case: no symbol selected yet
  if (!symbol) {
    return (
      <div className="p-6">
        <h1 className="text-3xl font-bold mb-4">Stock Analysis</h1>

        {loadingList ? (
          <p>Loading stock list...</p>
        ) : (
          <select
            defaultValue=""
            onChange={(e) => navigate(`/stock/${e.target.value}`)}
            className="border rounded-lg px-3 py-2 shadow-sm"
          >
            <option value="" disabled>
              -- Select Stock --
            </option>
            {stockList.map((s) => (
              <option key={s.symbol} value={s.symbol}>
                {s.name} ({s.symbol})
              </option>
            ))}
          </select>
        )}
      </div>
    );
  }

  // Case: symbol selected but still loading data
  if (!data) return <Loader />;

  const {
    price,
    changePercent,
    dayHigh,
    dayLow,
    yearHigh,
    yearLow,
    marketCap,
    volume,
    avgVolume,
    history,
    indicators,
    insights,
  } = data;

  return (
    <div className="p-6 space-y-10">
      {/* Heading + Dropdown */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-gray-800">
          Stock Analysis: <span className="text-blue-600">{symbol}</span>
        </h1>

        <select
          value={symbol}
          onChange={(e) => navigate(`/stock/${e.target.value}`)}
          className="border rounded-lg px-3 py-2 shadow-sm focus:ring focus:ring-blue-300"
        >
          <option value="" disabled>
            -- Select Stock --
          </option>
          {stockList.map((s) => (
            <option key={s.symbol} value={s.symbol}>
              {s.name} ({s.symbol})
            </option>
          ))}
        </select>
      </div>

      {/* Overview Card */}
      {/* Overview Card */}
      <div className="bg-white shadow-lg rounded-xl p-6">
        <h2 className="text-xl font-bold text-gray-800 mb-4">Overview</h2>

        <div className="grid grid-cols-3 gap-6 text-gray-700">
          <div>
            <p className="font-medium">Price</p>
            <p className="font-bold">₹{price}</p>
          </div>
          <div>
            <p className="font-medium">Change</p>
            <p
              className={`font-bold ${
                changePercent > 0 ? "text-green-600" : "text-red-600"
              }`}
            >
              {changePercent}%
            </p>
          </div>
          <div>
            <p className="font-medium">Day High</p>
            <p className="font-bold">₹{dayHigh}</p>
          </div>
          <div>
            <p className="font-medium">Day Low</p>
            <p className="font-bold">₹{dayLow}</p>
          </div>
          <div>
            <p className="font-medium">52W High</p>
            <p className="font-bold">₹{yearHigh}</p>
          </div>
          <div>
            <p className="font-medium">52W Low</p>
            <p className="font-bold">₹{yearLow}</p>
          </div>
          <div>
            <p className="font-medium">Market Cap</p>
            <p className="font-bold">{marketCap}</p>
          </div>
          <div>
            <p className="font-medium">Volume</p>
            <p className="font-bold">{volume}</p>
          </div>
          <div>
            <p className="font-medium">Avg. Volume</p>
            <p className="font-bold">{avgVolume}</p>
          </div>
        </div>
      </div>


      {/* Later: Indicators, Chart, Insights, etc. */}
    </div>
  );
}
