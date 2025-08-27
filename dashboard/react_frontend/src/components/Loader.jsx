import React from "react";

export default function Loader() {
  return (
    <div className="flex items-center justify-center h-40 w-full">
      <div className="w-10 h-10 border-4 border-gray-200 border-t-blue-500 rounded-full animate-spin"></div>
    </div>
  );
}
