import { BrowserRouter, Navigate, Routes, Route } from "react-router-dom"

import Login from "./pages/Login"
import Register from "./pages/Register"
import Cita from "./pages/Cita"
import Historial from "./pages/Historial"
import Confirmacion from "./pages/Confirmacion"
import CitasDoctor from "./doctor/CitasDoctor"
import { getStoredUser, getToken } from "./services/api"

function ProtectedRoute({ children }) {
  // Las rutas principales son protegidas: si no hay token JWT, vuelve al login.
  return getToken() ? children : <Navigate to="/" replace />
}

function DoctorRoute({ children }) {
  const user = getStoredUser()

  if (!getToken()) return <Navigate to="/" replace />
  return user?.rol === "doctor" ? children : <Navigate to="/cita" replace />
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route
          path="/confirmacion"
          element={
            <ProtectedRoute>
              <Confirmacion />
            </ProtectedRoute>
          }
        />
        <Route path="/register" element={<Register />} />
        <Route
          path="/cita"
          element={
            <ProtectedRoute>
              <Cita />
            </ProtectedRoute>
          }
        />
        <Route
          path="/historial"
          element={
            <ProtectedRoute>
              <Historial />
            </ProtectedRoute>
          }
        />
        <Route
          path="/doctor"
          element={
            <DoctorRoute>
              <CitasDoctor />
            </DoctorRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}

export default App
