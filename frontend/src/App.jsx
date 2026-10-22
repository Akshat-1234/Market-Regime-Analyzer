import { Route, Routes } from "react-router-dom";
import Sidebar from "./components/layout/Sidebar.jsx";
import Topbar from "./components/layout/Topbar.jsx";
import Footer from "./components/layout/Footer.jsx";
import StrategyLab from "./pages/StrategyLab.jsx";
import Performance from "./pages/Performance.jsx";
import DataExplorer from "./pages/DataExplorer.jsx";
import NotFound from "./pages/NotFound.jsx";

export default function App() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <Topbar />
        <div className="page-body">
          <Routes>
            <Route path="/" element={<StrategyLab />} />
            <Route path="/performance" element={<Performance />} />
            <Route path="/data" element={<DataExplorer />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </div>
        <Footer />
      </main>
    </div>
  );
}
