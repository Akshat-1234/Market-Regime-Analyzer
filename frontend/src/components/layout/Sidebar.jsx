import { NavLink } from "react-router-dom";
import { useBacktest } from "../../context/BacktestContext.jsx";

const NAV = [
  { to: "/", label: "Strategy Lab", icon: "◫", end: true },
  { to: "/performance", label: "Performance", icon: "⌁" },
  { to: "/data", label: "Data Explorer", icon: "▤" },
  { to: "/regimes", label: "Regime Explorer", icon: "◉" },
];

export default function Sidebar() {
  const { apiStatus } = useBacktest();
  const statusText =
    apiStatus === "connected"
      ? "API connected"
      : apiStatus === "offline"
      ? "API unavailable"
      : "Connecting…";

  return (
    <aside className="sidebar">
      <NavLink className="brand" to="/" aria-label="QuantLab home">
        <span className="brand-mark">Q</span>
        <span>
          Quant<span className="brand-light">Lab</span>
        </span>
      </NavLink>
      <nav className="nav">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
          >
            <span>{item.icon}</span> {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}