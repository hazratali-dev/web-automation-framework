import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ConfigPage } from "./pages/ConfigPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ProxiesPage } from "./pages/ProxiesPage";
import { TargetsPage } from "./pages/TargetsPage";
import { TasksPage } from "./pages/TasksPage";

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="targets" element={<TargetsPage />} />
        <Route path="tasks" element={<TasksPage />} />
        <Route path="proxies" element={<ProxiesPage />} />
        <Route path="config" element={<ConfigPage />} />
      </Route>
    </Routes>
  );
}

export default App;
