import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import ModelHistory from "./pages/ModelHistory";
import Models from "./pages/Models";
import NewScan from "./pages/NewScan";
import ScanDetail from "./pages/ScanDetail";
import { useIsAuthed } from "./store/auth";

function RequireAuth({ children }) {
  return useIsAuthed() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  const authed = useIsAuthed();

  return (
    <>
    {import.meta.env.VITE_FREE_DEMO === "true" && (
      <div role="note" className="border-b border-rule bg-paper px-6 py-3 text-sm">
        Free demo: accounts, uploads and scan history reset when the server restarts or sleeps.
        Download your reports before leaving. The first visit after inactivity may take about a minute.
      </div>
    )}
    <Routes>
      <Route path="/login" element={authed ? <Navigate to="/models" replace /> : <Login />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/models" element={<Models />} />
        <Route path="/models/:modelId" element={<ModelHistory />} />
        <Route path="/scans/new" element={<NewScan />} />
        <Route path="/scans/:scanId" element={<ScanDetail />} />
      </Route>
      <Route path="*" element={<Navigate to={authed ? "/models" : "/login"} replace />} />
    </Routes>
    </>
  );
}
