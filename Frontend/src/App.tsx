import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

// Pages
import Landing from "./pages/Landing";
import Onboarding from "./pages/Onboarding";
import Dashboard from "./pages/Dashboard";
import Circles from "./pages/Circles";
import Analytics from "./pages/Analytics";
import Settings from "./pages/Settings";
import NotFound from "./pages/NotFound";
import Plans from "./pages/Plans";
import News from "./pages/News";
import Widgets from "./pages/Widgets"; // ✅ Widget Manager

// Context
import { WidgetProvider } from "@/context/WidgetContext"; // ✅ Global Context
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";
import Auth from "@/pages/Auth";

// Create query client for Tanstack React Query
const queryClient = new QueryClient();

const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <AuthProvider>
            <WidgetProvider>
              <Routes>
                <Route path="/" element={<Landing />} />
                <Route path="/auth" element={<Auth />} />
                
                {/* Protected Routes */}
                <Route path="/onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />
                <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                <Route path="/circles" element={<ProtectedRoute><Circles /></ProtectedRoute>} />
                <Route path="/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
                <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
                <Route path="/plans" element={<ProtectedRoute><Plans /></ProtectedRoute>} />
                <Route path="/news" element={<ProtectedRoute><News /></ProtectedRoute>} />
                <Route path="/widgets" element={<ProtectedRoute><Widgets /></ProtectedRoute>} />
                
                {/* Redirects for unused paths */}
                <Route path="/inbox" element={<Navigate to="/dashboard" replace />} />
                <Route path="/reports" element={<Navigate to="/analytics" replace />} />
                <Route path="/trends" element={<Navigate to="/analytics" replace />} />
                <Route path="*" element={<NotFound />} />
              </Routes>

              {/* ✅ Keep global toasters *outside* router for consistent access */}
              <Toaster />
              <Sonner />
            </WidgetProvider>
          </AuthProvider>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  );
};

export default App;
