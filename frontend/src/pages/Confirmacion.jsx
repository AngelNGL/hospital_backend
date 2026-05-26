import { Link, useLocation, useNavigate } from "react-router-dom"
import { clearSession, getStoredUser } from "../services/api"

function formatDate(fecha) {
  if (!fecha) return "Fecha no disponible"

  return new Date(`${fecha}T00:00:00`).toLocaleDateString("es-MX", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  })
}

export default function Confirmacion() {
  const navigate = useNavigate()
  const location = useLocation()
  // La cita viene de la respuesta de POST /citas.
  // Se muestra lo que regresa el backend: paciente, doctor, fecha, hora y estado.
  const cita = location.state?.cita
  const user = getStoredUser()

  function logout() {
    clearSession()
    navigate("/", { replace: true })
  }

  return (
    <div className="min-h-screen bg-blue-50 flex">
      <aside className="w-64 bg-white shadow-lg p-6 flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-3 mb-10">
            <div className="w-12 h-12 rounded-full bg-blue-500" />
            <div>
              <h2 className="font-bold text-gray-800">{user?.correo || "Usuario"}</h2>
              <p className="text-sm text-gray-500">{user?.rol || "cliente"}</p>
            </div>
          </div>

          <nav className="space-y-3">
            <Link
              to="/cita"
              className="block w-full text-left bg-blue-100 text-blue-700 font-semibold px-4 py-3 rounded-xl"
            >
              Agendar Cita
            </Link>
            <Link
              to="/historial"
              className="block w-full text-left text-gray-600 hover:bg-gray-100 px-4 py-3 rounded-xl"
            >
              Historial
            </Link>
          </nav>
        </div>

        <button
          type="button"
          onClick={logout}
          className="block w-full text-left text-red-500 hover:bg-red-50 px-4 py-3 rounded-xl"
        >
          Cerrar sesion
        </button>
      </aside>

      <main className="flex-1 p-8">
        <div className="flex justify-between items-center mb-10">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Confirmacion</h1>
            <p className="text-gray-500">
              {cita ? "Tu cita ha sido registrada" : "No hay una cita reciente para mostrar"}
            </p>
          </div>
        </div>

        <div className="max-w-3xl mx-auto bg-white rounded-3xl shadow-sm p-8">
          <div className="flex flex-col items-center text-center mb-8">
            <div className="w-20 h-20 rounded-full bg-blue-100 flex items-center justify-center mb-5">
              <div className="w-12 h-12 rounded-full bg-blue-600 text-white flex items-center justify-center text-2xl font-bold">
                OK
              </div>
            </div>
            <h2 className="text-3xl font-bold text-gray-800">
              {cita ? "Cita agendada" : "Sin datos de confirmacion"}
            </h2>
          </div>

          {cita ? (
            <div className="bg-gray-100 rounded-3xl p-6 mb-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <p className="text-sm text-gray-500">PACIENTE</p>
                  <h3 className="font-bold text-gray-800">{cita.paciente?.nombre_completo}</h3>
                </div>
                <div>
                  <p className="text-sm text-gray-500">ESPECIALISTA</p>
                  <h3 className="font-bold text-gray-800">{cita.doctor?.nombre_completo}</h3>
                  <p className="text-sm text-gray-500">{cita.doctor?.especialidad}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">FECHA Y HORA</p>
                  <h3 className="font-bold text-gray-800 capitalize">{formatDate(cita.fecha)}</h3>
                  <p className="text-sm text-gray-500">{String(cita.hora_inicio).slice(0, 5)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">DURACION ESTIMADA</p>
                  <h3 className="font-bold text-gray-800">30 minutos</h3>
                </div>
                <div>
                  <p className="text-sm text-gray-500">ESTADO</p>
                  <h3 className="font-bold text-gray-800 uppercase">{cita.estado}</h3>
                </div>
                <div>
                  <p className="text-sm text-gray-500">MOTIVO</p>
                  <h3 className="font-bold text-gray-800">{cita.motivo}</h3>
                </div>
              </div>
            </div>
          ) : (
            <p className="bg-gray-100 rounded-3xl p-6 mb-6 text-gray-600">
              Vuelve a la agenda para crear una nueva cita.
            </p>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Link
              to="/historial"
              className="text-center bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-xl font-semibold shadow-lg"
            >
              Ver historial
            </Link>
            <Link
              to="/cita"
              className="text-center bg-gray-100 hover:bg-gray-200 text-gray-700 py-4 rounded-xl font-semibold"
            >
              Agendar otra cita
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
