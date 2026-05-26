import { useEffect, useMemo, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import {
  cancelCita,
  clearSession,
  getCitas,
  getDisponibilidad,
  getStoredUser,
  rescheduleCita,
} from "../services/api"

function formatDate(fecha) {
  if (!fecha) return ""

  return new Date(`${fecha}T00:00:00`).toLocaleDateString("es-MX", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  })
}

function statusClass(estado) {
  if (estado === "cancelada") return "bg-red-100 text-red-600"
  if (estado === "completada") return "bg-purple-100 text-purple-600"
  return "bg-blue-100 text-blue-600"
}

export default function Historial() {
  const navigate = useNavigate()
  const user = getStoredUser()
  const [citas, setCitas] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [modalCita, setModalCita] = useState(null)
  const [nuevaFecha, setNuevaFecha] = useState("")
  const [nuevaHora, setNuevaHora] = useState("")
  const [horarios, setHorarios] = useState([])
  const [loadingHorarios, setLoadingHorarios] = useState(false)

  const proximas = useMemo(
    () => citas.filter((cita) => cita.estado === "pendiente"),
    [citas],
  )
  const historial = useMemo(
    () => citas.filter((cita) => cita.estado !== "pendiente"),
    [citas],
  )

  async function loadCitas({ showLoading = true } = {}) {
    if (showLoading) {
      setLoading(true)
    }
    setError("")

    try {
      // Guia: GET /citas/me regresa las citas segun el rol del usuario.
      setCitas(await getCitas())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    queueMicrotask(() => {
      loadCitas({ showLoading: false })
    })
  }, [])

  useEffect(() => {
    async function loadAvailability() {
      if (!modalCita || !nuevaFecha) {
        setHorarios([])
        setNuevaHora("")
        return
      }

      setLoadingHorarios(true)
      setError("")

      try {
        // Guia: para reprogramar primero se consulta disponibilidad
        // del mismo doctor en la nueva fecha.
        const data = await getDisponibilidad(modalCita.doctor.id_doctor, nuevaFecha)
        setHorarios(data.horarios_disponibles || [])
        setNuevaHora("")
      } catch (err) {
        setHorarios([])
        setError(err.message)
      } finally {
        setLoadingHorarios(false)
      }
    }

    loadAvailability()
  }, [modalCita, nuevaFecha])

  function logout() {
    clearSession()
    navigate("/", { replace: true })
  }

  async function handleCancel(cita) {
    setError("")
    setNotice("")

    try {
      // Guia: PATCH /citas/{id_cita}/cancelar no requiere body.
      await cancelCita(cita.id_cita)
      setNotice("Cita cancelada correctamente.")
      await loadCitas()
    } catch (err) {
      setError(err.message)
    }
  }

  function openReschedule(cita) {
    setModalCita(cita)
    setNuevaFecha("")
    setNuevaHora("")
    setHorarios([])
  }

  async function handleReschedule(event) {
    event.preventDefault()
    setError("")
    setNotice("")

    if (!modalCita || !nuevaFecha || !nuevaHora) {
      setError("Selecciona una nueva fecha y horario.")
      return
    }

    try {
      // Guia: para cliente solo se manda fecha y hora_inicio.
      // El backend calcula hora_fin automaticamente.
      await rescheduleCita(modalCita.id_cita, {
        fecha: nuevaFecha,
        hora_inicio: nuevaHora,
      })
      setNotice("Cita reprogramada correctamente.")
      setModalCita(null)
      await loadCitas()
    } catch (err) {
      setError(err.message)
    }
  }

  function CitaRow({ cita, allowActions = false }) {
    return (
      <div className="bg-white rounded-2xl shadow-sm p-5 border-l-4 border-blue-500 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-5">
          <div className="bg-gray-50 rounded-xl p-4 text-center min-w-28">
            <p className="text-sm font-semibold text-gray-500">{formatDate(cita.fecha)}</p>
            <p className="text-2xl font-bold text-gray-700">{String(cita.hora_inicio).slice(0, 5)}</p>
          </div>
          <div>
            <h3 className="font-bold text-gray-800">{cita.paciente?.nombre_completo}</h3>
            <p className="text-sm text-gray-500">
              {cita.doctor?.nombre_completo} - {cita.doctor?.especialidad}
            </p>
            <p className="text-sm text-gray-400">{cita.motivo}</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <span className={`${statusClass(cita.estado)} text-xs font-bold px-4 py-2 rounded-full uppercase`}>
            {cita.estado}
          </span>
          {allowActions && (
            <>
              <button
                type="button"
                onClick={() => openReschedule(cita)}
                className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-xl font-semibold"
              >
                Reprogramar
              </button>
              <button
                type="button"
                onClick={() => handleCancel(cita)}
                className="bg-red-50 hover:bg-red-100 text-red-600 px-4 py-2 rounded-xl font-semibold"
              >
                Cancelar
              </button>
            </>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-100 flex">
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
              className="block w-full text-left text-gray-600 hover:bg-gray-100 px-4 py-3 rounded-xl"
            >
              Agendar Cita
            </Link>
            <Link
              to="/historial"
              className="block w-full text-left bg-blue-100 text-blue-700 font-semibold px-4 py-3 rounded-xl"
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
        <div className="max-w-5xl mx-auto space-y-8">
          <div>
            <h1 className="text-4xl font-bold text-gray-800">Historial de Consultas</h1>
            <p className="text-gray-500 mt-2">Consulta tus citas agendadas y anteriores</p>
          </div>

          {error && (
            <p className="rounded-xl bg-red-50 px-4 py-3 text-sm font-semibold text-red-600">
              {error}
            </p>
          )}
          {notice && (
            <p className="rounded-xl bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700">
              {notice}
            </p>
          )}

          {loading ? (
            <div className="bg-white rounded-3xl p-8 shadow-sm">Cargando citas...</div>
          ) : (
            <>
              <section>
                <h2 className="text-2xl font-bold text-gray-800 mb-5">Proximas Citas</h2>
                <div className="space-y-5">
                  {proximas.length > 0 ? (
                    proximas.map((cita) => (
                      <CitaRow key={cita.id_cita} cita={cita} allowActions />
                    ))
                  ) : (
                    <div className="border-2 border-dashed border-gray-200 rounded-3xl p-12 text-center">
                      <h3 className="text-xl font-bold text-gray-800">No hay citas pendientes</h3>
                      <p className="text-gray-500 mt-2 mb-6">Agenda tu proxima cita medica</p>
                      <Link
                        to="/cita"
                        className="inline-block bg-blue-700 hover:bg-blue-800 text-white px-8 py-4 rounded-xl font-semibold shadow-lg"
                      >
                        Nueva cita medica
                      </Link>
                    </div>
                  )}
                </div>
              </section>

              <section>
                <h2 className="text-2xl font-bold text-gray-800 mb-5">Citas Anteriores</h2>
                <div className="space-y-5">
                  {historial.length > 0 ? (
                    historial.map((cita) => <CitaRow key={cita.id_cita} cita={cita} />)
                  ) : (
                    <p className="bg-white rounded-2xl p-6 text-gray-500 shadow-sm">
                      Aun no hay citas completadas o canceladas.
                    </p>
                  )}
                </div>
              </section>
            </>
          )}
        </div>
      </main>

      {modalCita && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-6 z-50">
          <form onSubmit={handleReschedule} className="bg-white rounded-3xl shadow-xl p-8 w-full max-w-xl">
            <h2 className="text-3xl font-bold text-gray-800 mb-2">Reprogramar cita</h2>
            <p className="text-gray-500 mb-8">
              {modalCita.doctor?.nombre_completo} - {modalCita.doctor?.especialidad}
            </p>

            <label className="block text-sm font-semibold text-gray-600 mb-2">Nueva fecha</label>
            <input
              type="date"
              value={nuevaFecha}
              min={new Date().toISOString().slice(0, 10)}
              onChange={(event) => setNuevaFecha(event.target.value)}
              required
              className="w-full bg-gray-100 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500 mb-6"
            />

            <label className="block text-sm font-semibold text-gray-600 mb-3">Nuevo horario</label>
            {loadingHorarios ? (
              <p className="text-gray-500 mb-6">Consultando horarios...</p>
            ) : (
              <div className="grid grid-cols-2 gap-3 mb-8">
                {horarios.map((horario) => (
                  <button
                    type="button"
                    key={`${horario.hora_inicio}-${horario.hora_fin}`}
                    onClick={() => setNuevaHora(horario.hora_inicio)}
                    className={`border rounded-xl py-3 ${
                      nuevaHora === horario.hora_inicio
                        ? "bg-blue-600 text-white border-blue-600"
                        : "hover:border-blue-500 hover:text-blue-600"
                    }`}
                  >
                    {horario.hora_inicio}
                  </button>
                ))}
                {nuevaFecha && horarios.length === 0 && (
                  <p className="col-span-2 rounded-xl bg-gray-50 p-4 text-sm text-gray-500">
                    No hay horarios disponibles para esta fecha.
                  </p>
                )}
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setModalCita(null)}
                className="bg-gray-100 hover:bg-gray-200 text-gray-700 py-4 rounded-xl font-semibold"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-xl font-semibold shadow-lg"
              >
                Guardar cambio
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
