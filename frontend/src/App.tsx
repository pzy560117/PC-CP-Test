import { Navigate, Route, Routes } from "react-router-dom"

import MainLayout from "@/components/layout/main-layout"
import AnalysisPage from "@/pages/analysis"
import DashboardPage from "@/pages/dashboard"
import HistoryPage from "@/pages/history"

/** 应用根路由，统一挂载布局与页面。 */
export default function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/analysis" element={<AnalysisPage />} />
        <Route path="/history" element={<HistoryPage />} />
      </Route>
    </Routes>
  )
}
