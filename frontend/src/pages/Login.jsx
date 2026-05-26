import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { getMe, login, saveSession } from "../services/api"

export default function Login() {
  const navigate = useNavigate()
  const [correo, setCorreo] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError("")
    setLoading(true)

    try {
      // Guia: primero se hace POST /auth/login con correo y password.
      // El backend responde el JWT access_token.
      const authData = await login(correo, password)
      saveSession(authData)

      // Guia: despues del login se consulta GET /auth/me para traer rol y usuario.
      const userData = await getMe()
      saveSession(authData, userData)
      navigate(userData.rol === "doctor" ? "/doctor" : "/cita", { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-6">
      <div className="w-full max-w-5xl bg-white rounded-3xl shadow-xl overflow-hidden grid grid-cols-1 md:grid-cols-2">
        <div className="bg-blue-700 flex items-center justify-center p-10">
          <div className="w-full h-full rounded-2xl bg-white/10 p-8 text-white">
            <h2 className="text-3xl font-bold">Clinica San Rafael</h2>
            <p className="mt-4 text-sm leading-6 text-white/85">
              Sistema institucional para la gestion de citas medicas,
              pacientes y agenda clinica.
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-10 flex flex-col justify-center">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">Bienvenido</h1>
          <p className="text-gray-500 mb-8">Ingresa tus datos para continuar</p>

          <div className="mb-5">
            <label className="block text-sm font-semibold text-gray-600 mb-2">
              CORREO ELECTRONICO
            </label>
            <input
              type="email"
              value={correo}
              onChange={(event) => setCorreo(event.target.value)}
              placeholder="nombre@ejemplo.com"
              required
              className="w-full bg-gray-100 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="mb-2">
            <div className="flex justify-between mb-2">
              <label className="text-sm font-semibold text-gray-600">
                CONTRASENA
              </label>
              <span className="text-sm text-gray-400">Sistema de citas</span>
            </div>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="********"
              required
              className="w-full bg-gray-100 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {error && (
            <p className="my-4 rounded-xl bg-red-50 px-4 py-3 text-sm font-semibold text-red-600">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 transition-all text-white py-4 rounded-xl font-semibold shadow-lg mt-6"
          >
            {loading ? "Iniciando..." : "Iniciar sesion"}
          </button>

          <p className="text-center text-gray-500 mt-8">
            No tienes una cuenta todavia?{" "}
            <Link to="/register" className="text-blue-600 font-semibold">
              Crear una cuenta nueva
            </Link>
          </p>
        </form>
      </div>
    </div>
  )
}
