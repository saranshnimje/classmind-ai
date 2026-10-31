import { lazy } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { ThemeProvider } from "./lib/theme";

const DashboardPage = lazy(() =>
  import("./pages/Dashboard").then((module) => ({ default: module.DashboardPage })),
);
const SessionsPage = lazy(() =>
  import("./pages/Sessions").then((module) => ({ default: module.SessionsPage })),
);
const CreateSessionPage = lazy(() =>
  import("./pages/CreateSession").then((module) => ({ default: module.CreateSessionPage })),
);
const SessionAnalysisPage = lazy(() =>
  import("./pages/SessionAnalysis").then((module) => ({ default: module.SessionAnalysisPage })),
);
const AttendancePage = lazy(() =>
  import("./pages/Attendance").then((module) => ({ default: module.AttendancePage })),
);
const AnalyticsPage = lazy(() =>
  import("./pages/Analytics").then((module) => ({ default: module.AnalyticsPage })),
);
const RecommendationsPage = lazy(() =>
  import("./pages/Recommendations").then((module) => ({ default: module.RecommendationsPage })),
);
const SettingsPage = lazy(() =>
  import("./pages/Settings").then((module) => ({ default: module.SettingsPage })),
);
const AboutPage = lazy(() =>
  import("./pages/About").then((module) => ({ default: module.AboutPage })),
);
const NotFoundPage = lazy(() =>
  import("./pages/NotFound").then((module) => ({ default: module.NotFoundPage })),
);

export function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<DashboardPage />} />
            <Route path="sessions" element={<SessionsPage />} />
            <Route path="sessions/new" element={<CreateSessionPage />} />
            <Route path="sessions/:id" element={<SessionAnalysisPage />} />
            <Route path="attendance" element={<AttendancePage />} />
            <Route path="attendance/:id" element={<AttendancePage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="analytics/:id" element={<AnalyticsPage />} />
            <Route path="recommendations" element={<RecommendationsPage />} />
            <Route path="recommendations/:id" element={<RecommendationsPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="about" element={<AboutPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
