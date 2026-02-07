import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import HomePage from "@/pages/HomePage";
import QueryPage from "@/pages/QueryPage";
import ResponsePage from "@/pages/ResponsePage";
import StudentPortal from "@/pages/StudentPortal";
import DocumentsPage from "@/pages/DocumentsPage";

function App() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <BrowserRouter>
        <Navbar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/query" element={<QueryPage />} />
            <Route path="/response/:queryId" element={<ResponsePage />} />
            <Route path="/students" element={<StudentPortal />} />
            <Route path="/documents" element={<DocumentsPage />} />
          </Routes>
        </main>
        <Footer />
        <Toaster position="top-right" richColors />
      </BrowserRouter>
    </div>
  );
}

export default App;
