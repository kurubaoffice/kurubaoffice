import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function StockSearch({ stockList }) {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const handleSelect = (symbol) => {
    navigate(`/stock/${symbol}`);
  };

  const filtered = stockList.filter(
    (s) => s.toLowerCase().includes(query.toLowerCase())
  ).slice(0, 5);

  return (
    <div style={{ position: "relative" }}>
      <input
        type="text"
        placeholder="Search stock symbol..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        style={{ padding: "0.5rem", width: "200px" }}
      />
      {query && (
        <ul style={{
          position: "absolute",
          background: "white",
          border: "1px solid #ccc",
          margin: 0,
          padding: "0.5rem",
          listStyle: "none",
          width: "200px",
          zIndex: 10
        }}>
          {filtered.map((s) => (
            <li key={s} onClick={() => handleSelect(s)} style={{ cursor: "pointer", padding: "0.25rem 0" }}>
              {s}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
