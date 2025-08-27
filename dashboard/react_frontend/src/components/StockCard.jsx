import React from "react";

export default function StockCard({ title, value, change }) {
  return (
    <div style={{
      border: "1px solid #ccc",
      borderRadius: "8px",
      padding: "1rem",
      margin: "0.5rem",
      width: "200px",
    }}>
      <h3>{title}</h3>
      <p style={{ fontSize: "1.2rem", margin: "0.5rem 0" }}>{value}</p>
      {change !== undefined && (
        <p style={{ color: change >= 0 ? "green" : "red" }}>
          {change >= 0 ? "+" : ""}{change}%
        </p>
      )}
    </div>
  );
}
