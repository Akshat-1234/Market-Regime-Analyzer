import { useLocation } from "react-router-dom";

const TITLES = {
  "/": "Strategy Lab",
  "/performance": "Performance",
  "/data": "Data Explorer",
};

export default function Topbar() {
  const { pathname } = useLocation();
  const title = TITLES[pathname] ?? "Regime Explorer";

  return (
    <header className="topbar">
      <div className="breadcrumb">
        Workspace <span>/</span> <strong>{title}</strong>
      </div>
    </header>
  );
}
