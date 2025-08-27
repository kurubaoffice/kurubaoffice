import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function StockSearch({ stockList }) {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const handleSelect = (symbol) => {
    setQuery("");
    navigate(`/stock/${symbol}`);
  };

  const filtered = stockList
    .filter((s) => s.toLowerCase().includes(query.toLowerCase()))
    .slice(0, 8); // show top 8 matches

  return (
    <div className="relative w-80">
      {/* Input */}
      <input
        type="text"
        placeholder="Search stock symbol..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
      />

      {/* Dropdown */}
      {query && filtered.length > 0 && (
        <ul className="absolute mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto z-20">
          {filtered.map((s) => (
            <li
              key={s}
              onClick={() => handleSelect(s)}
              className="px-4 py-2 cursor-pointer hover:bg-blue-100"
            >
              {s}
            </li>
          ))}
        </ul>
      )}

      {/* No matches */}
      {query && filtered.length === 0 && (
        <div className="absolute mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg px-4 py-2 text-gray-500">
          No matches found
        </div>
      )}
    </div>
  );
}
