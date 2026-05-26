import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  cancelCita,
  clearSession,
  getCitas,
  getDisponibilidad,
  getStoredUser,
  rescheduleCita,
} from "../services/api"

const today = new Date().toISOString().slice(0, 10)

function formatDay(fecha) {
  return new Date(`${fecha}T00:00:00`).toLocaleDateString("es-MX", {
    day: "2-digit",
    month: "short",
  })
}

function formatLongDate(fecha) {
  return new Date(`${fecha}T00:00:00`).toLocaleDateString("es-MX", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  })
}

function timeText(value) {
  return String(value || "").slice(0, 5)
}

function addMinutes(time, minutes) {
  const [hours, mins] = time.split(":").map(Number)
  const date = new Date()
  date.setHours(hours, mins + minutes, 0, 0)
  return date.toTimeString().slice(0, 5)
}

function statusLabel(estado) {
  if (estado === "completada") return "Finalizada"
  if (estado === "cancelada") return "Cancelada"
  return "Pendiente"
}

function statusClass(estado) {
  if (estado === "completada") return "bg-emerald-50 text-emerald-700"
  if (estado === "cancelada") return "bg-red-50 text-red-600"
  return "bg-indigo-50 text-indigo-700"
}

export default function CitasDoctor() {
  const navigate = useNavigate()
  const user = getStoredUser()
  const [citas, setCitas] = useState([])
  const [query, setQuery] = useState("")
  const [viewMode, setViewMode] = useState("hoy")
  const [selectedCita, setSelectedCita] = useState(null)
  const [modalCita, setModalCita] = useState(null)
  const [notaMedica, setNotaMedica] = useState("")
  const [nuevaFecha, setNuevaFecha] = useState(today)
  const [nuevaHora, setNuevaHora] = useState("")
  const [duracion, setDuracion] = useState("30")
  const [horarios, setHorarios] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [loadingHorarios, setLoadingHorarios] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")

  const sortedCitas = useMemo(
    () =>
      [...citas].sort((a, b) =>
        `${a.fecha} ${a.hora_inicio}`.localeCompare(`${b.fecha} ${b.hora_inicio}`),
      ),
    [citas],
  )

  const visibleCitas = useMemo(() => {
    const search = query.trim().toLowerCase()
    const byDate =
      viewMode === "hoy"
        ? sortedCitas.filter((cita) => cita.fecha === today)
        : sortedCitas

    if (!search) return byDate

    return byDate.filter((cita) =>
      [
        cita.paciente?.nombre_completo,
        cita.doctor?.especialidad,
        cita.motivo,
        cita.estado,
      ]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(search)),
    )
  }, [query, sortedCitas, viewMode])

  const pendingCitas = sortedCitas.filter((cita) => cita.estado === "pendiente")
  const todayCitas = sortedCitas.filter((cita) => cita.fecha === today)
  const nextCita = pendingCitas.find((cita) => `${cita.fecha}T${timeText(cita.hora_inicio)}` >= `${today}T00:00`)

  async function loadCitas() {
    setLoading(true)
    setError("")

    try {
      // Contrato backend para rol doctor: GET /citas/me regresa solo sus citas.
      setCitas(await getCitas())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    queueMicrotask(() => {
      loadCitas()
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
        // Para reagendar se consulta disponibilidad del mismo doctor y nueva fecha.
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

  function openReschedule(cita) {
    setSelectedCita(null)
    setModalCita(cita)
    setNuevaFecha(cita.fecha >= today ? cita.fecha : today)
    setNuevaHora("")
    setDuracion("30")
    setHorarios([])
    setNotice("")
    setError("")
  }

  function openDetail(cita) {
    setSelectedCita(cita)
    setNotaMedica("")
    setNotice("")
    setError("")
  }

  async function handleCancel(cita) {
    setError("")
    setNotice("")

    try {
      // Contrato backend: PATCH /citas/{id}/cancelar no manda body.
      await cancelCita(cita.id_cita)
      setNotice("Cita cancelada correctamente.")
      setSelectedCita(null)
      await loadCitas()
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleReschedule(event) {
    event.preventDefault()
    setError("")
    setNotice("")

    if (!modalCita || !nuevaFecha || !nuevaHora) {
      setError("Selecciona nueva fecha y horario para reagendar.")
      return
    }

    setSaving(true)

    try {
      // Contrato backend para doctor: PATCH /citas/{id}/reprogramar.
      // El doctor puede mandar hora_fin para ajustar duracion si lo necesita.
      await rescheduleCita(modalCita.id_cita, {
        fecha: nuevaFecha,
        hora_inicio: nuevaHora,
        hora_fin: addMinutes(nuevaHora, Number(duracion)),
      })
      setNotice("Cita reagendada correctamente.")
      setModalCita(null)
      await loadCitas()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#f8f7fc] text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-7xl bg-white shadow-sm">
        <aside className="flex w-72 flex-col justify-between border-r border-slate-100 bg-white px-6 py-8">
          <div>
            <h1 className="mb-10 text-lg font-bold tracking-tight">Clinica San Rafael</h1>

            <div className="mb-8 flex items-center gap-3 rounded-2xl bg-slate-50 p-4">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-100 text-xl font-bold text-indigo-700">
                +
              </div>
              <div>
                <p className="text-sm font-bold">Panel Medico</p>
                <p className="text-xs font-semibold uppercase text-slate-400">
                  {user?.rol || "doctor"}
                </p>
              </div>
            </div>

            <nav className="space-y-3">
              <button className="flex w-full items-center gap-3 rounded-xl bg-blue-50 px-4 py-3 text-left text-sm font-bold text-blue-700">
                <span className="flex h-6 w-6 items-center justify-center rounded-md bg-blue-600 text-xs text-white">
                  A
                </span>
                Agenda Medica
              </button>
              <button className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left text-sm font-semibold text-slate-500 hover:bg-slate-50">
                <span className="flex h-6 w-6 items-center justify-center rounded-md bg-slate-100 text-xs text-slate-600">
                  C
                </span>
                Configuracion
              </button>
            </nav>
          </div>

          <button
            type="button"
            onClick={logout}
            className="rounded-xl bg-indigo-700 px-4 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-100 hover:bg-indigo-800"
          >
            Cerrar sesion
          </button>
        </aside>

        <main className="flex-1 bg-[#fbfaff]">
          <header className="flex items-center justify-between border-b border-slate-100 bg-white px-8 py-6">
            <div className="flex items-center gap-4">
              <h2 className="text-2xl font-bold">Mi Agenda del Dia</h2>
              <span className="rounded-full bg-purple-100 px-3 py-1 text-xs font-bold uppercase text-purple-700">
                {formatDay(today)}
              </span>
            </div>

            <div className="flex items-center gap-4">
              <div className="relative">
                <input
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Buscar paciente..."
                  className="w-64 rounded-full border border-slate-100 bg-slate-50 px-5 py-3 text-sm outline-none focus:ring-2 focus:ring-indigo-200"
                />
              </div>
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-50 text-slate-500">
                !
              </span>
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-50 text-slate-500">
                *
              </span>
            </div>
          </header>

          <section className="px-8 py-8">
            {error && (
              <p className="mb-5 rounded-xl bg-red-50 px-4 py-3 text-sm font-semibold text-red-600">
                {error}
              </p>
            )}
            {notice && (
              <p className="mb-5 rounded-xl bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700">
                {notice}
              </p>
            )}

            <div className="mb-10 grid grid-cols-1 gap-5 lg:grid-cols-4">
              <article className="rounded-2xl bg-white p-6 shadow-sm lg:col-span-2">
                <p className="mb-2 text-sm font-semibold text-slate-500">Proxima Consulta</p>
                {nextCita ? (
                  <div className="flex items-end justify-between">
                    <div>
                      <p className="text-4xl font-black text-indigo-900">
                        {timeText(nextCita.hora_inicio)}
                      </p>
                      <p className="mt-1 font-bold">{nextCita.paciente?.nombre_completo}</p>
                      <p className="text-sm text-slate-400 capitalize">{formatLongDate(nextCita.fecha)}</p>
                    </div>
                    <span className="rounded-md bg-indigo-100 px-3 py-2 text-xs font-bold uppercase text-indigo-700">
                      Confirmada
                    </span>
                  </div>
                ) : (
                  <p className="text-sm text-slate-500">No hay consultas pendientes.</p>
                )}
              </article>

              <article className="rounded-2xl bg-white p-6 shadow-sm">
                <p className="mb-8 text-sm font-semibold text-slate-500">Total Citas</p>
                <p className="text-4xl font-black">{viewMode === "hoy" ? todayCitas.length : sortedCitas.length}</p>
              </article>

              <article className="rounded-2xl bg-indigo-50 p-6 shadow-sm">
                <p className="mb-8 text-sm font-semibold text-slate-500">Pendientes</p>
                <p className="text-4xl font-black text-indigo-800">{pendingCitas.length}</p>
              </article>
            </div>

            <div className="mb-5 flex items-center justify-between">
              <h3 className="text-xl font-bold">Cronograma</h3>
              <div className="flex rounded-full bg-white p-1 text-sm font-bold shadow-sm">
                <button
                  type="button"
                  onClick={() => setViewMode("hoy")}
                  className={`rounded-full px-4 py-2 ${viewMode === "hoy" ? "bg-indigo-700 text-white" : "text-slate-500"}`}
                >
                  Hoy
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode("semana")}
                  className={`rounded-full px-4 py-2 ${viewMode === "semana" ? "bg-indigo-700 text-white" : "text-slate-500"}`}
                >
                  Semana
                </button>
              </div>
            </div>

            {loading ? (
              <div className="rounded-2xl bg-white p-8 text-slate-500 shadow-sm">Cargando agenda...</div>
            ) : visibleCitas.length > 0 ? (
              <div className="space-y-4">
                {visibleCitas.map((cita) => {
                  const isPending = cita.estado === "pendiente"

                  return (
                    <article
                      key={cita.id_cita}
                      className="rounded-2xl bg-white shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
                    >
                      <button
                        type="button"
                        onClick={() => openDetail(cita)}
                        className="flex w-full items-center gap-5 p-5 text-left"
                      >
                        <div className="w-20 text-center">
                          <p className={`text-lg font-black ${isPending ? "text-indigo-800" : "text-slate-400"}`}>
                            {timeText(cita.hora_inicio)}
                          </p>
                          <p className="text-[10px] font-bold uppercase text-slate-400">
                            {cita.fecha === today ? "Hoy" : formatDay(cita.fecha)}
                          </p>
                        </div>

                        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50 text-sm font-black text-indigo-700">
                          {cita.paciente?.nombre?.[0] || "P"}
                        </div>

                        <div className="min-w-0 flex-1">
                          <h4 className="font-black">{cita.paciente?.nombre_completo}</h4>
                          <p className="truncate text-sm text-slate-500">{cita.motivo}</p>
                        </div>

                        <span className={`rounded-md px-3 py-2 text-xs font-bold uppercase ${statusClass(cita.estado)}`}>
                          {statusLabel(cita.estado)}
                        </span>

                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation()
                            openDetail(cita)
                          }}
                          className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-700 text-lg font-black text-white hover:bg-indigo-800"
                          aria-label="Ver detalle de cita"
                        >
                          &gt;
                        </button>
                      </button>
                    </article>
                  )
                })}
              </div>
            ) : (
              <div className="rounded-2xl border-2 border-dashed border-slate-200 bg-white p-10 text-center">
                <h4 className="text-lg font-black">No hay citas para mostrar</h4>
                <p className="mt-2 text-sm text-slate-500">Cambia el filtro o busca otro paciente.</p>
              </div>
            )}
          </section>
        </main>
      </div>

      {selectedCita && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/35 p-6">
          <section className="max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-[2rem] bg-[#fbfaff] shadow-2xl">
            <header className="flex items-center justify-between border-b border-slate-100 bg-white px-8 py-5">
              <div className="flex items-center gap-4">
                <button
                  type="button"
                  onClick={() => setSelectedCita(null)}
                  className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-50 text-xl font-black text-slate-600 hover:bg-slate-100"
                  aria-label="Volver a agenda"
                >
                  &lt;
                </button>
                <h2 className="text-2xl font-black">Detalle de Cita</h2>
              </div>

              <div className="flex items-center gap-3">
                <span className="rounded-full bg-purple-50 px-4 py-2 text-xs font-bold text-purple-700">
                  Proxima: {timeText(nextCita?.hora_inicio) || "--:--"} hs
                </span>
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-50 text-slate-500">
                  !
                </span>
              </div>
            </header>

            <div className="grid gap-6 p-8 lg:grid-cols-[2fr_1fr]">
              <div className="space-y-6">
                <article className="rounded-3xl bg-white p-8 shadow-sm">
                  <div className="mb-8 flex items-center gap-5">
                    <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100 text-2xl font-black text-indigo-700">
                      {selectedCita.paciente?.nombre?.[0] || "P"}
                    </div>
                    <div>
                      <h3 className="text-3xl font-black">{selectedCita.paciente?.nombre_completo}</h3>
                      <p className="text-sm font-semibold text-slate-400">
                        ID: {selectedCita.paciente?.id_paciente?.slice(0, 8) || "N/A"} - Paciente
                      </p>
                    </div>
                  </div>

                  <div className="grid gap-6 md:grid-cols-2">
                    <div>
                      <p className="mb-2 text-xs font-black uppercase tracking-[0.18em] text-slate-400">
                        Motivo de consulta
                      </p>
                      <p className="text-lg font-bold leading-relaxed text-slate-800">
                        {selectedCita.motivo || "Sin motivo registrado."}
                      </p>
                    </div>
                    <div>
                      <p className="mb-2 text-xs font-black uppercase tracking-[0.18em] text-slate-400">
                        Ultima visita
                      </p>
                      <p className="text-lg font-bold text-slate-800">
                        {selectedCita.estado === "completada" ? formatDay(selectedCita.fecha) : "Sin registro"}
                      </p>
                    </div>
                  </div>
                </article>

                <div className="grid grid-cols-2 gap-4 rounded-3xl bg-white p-2 shadow-sm">
                  <button
                    type="button"
                    className="rounded-2xl bg-white px-5 py-5 text-sm font-black text-indigo-800 shadow-sm ring-1 ring-slate-100"
                  >
                    Completar Cita
                  </button>
                  <button
                    type="button"
                    onClick={() => handleCancel(selectedCita)}
                    className="rounded-2xl px-5 py-5 text-sm font-black text-red-600 hover:bg-red-50"
                  >
                    Cancelar
                  </button>
                </div>

                <article className="rounded-3xl bg-white p-8 shadow-sm">
                  <label className="mb-4 block text-xs font-black uppercase tracking-[0.18em] text-slate-400">
                    Nota medica (opcional)
                  </label>
                  <textarea
                    value={notaMedica}
                    onChange={(event) => setNotaMedica(event.target.value)}
                    rows="7"
                    placeholder="Ingrese observaciones, diagnostico preventivo o derivaciones..."
                    className="w-full resize-none rounded-2xl bg-slate-100 p-5 text-sm outline-none focus:ring-2 focus:ring-indigo-200"
                  />
                  <div className="mt-5 flex justify-end gap-3">
                    <button
                      type="button"
                      onClick={() => openReschedule(selectedCita)}
                      className="rounded-xl bg-blue-600 px-6 py-4 text-sm font-black text-white shadow-lg shadow-blue-100 hover:bg-blue-700"
                    >
                      Reagendar emergencia
                    </button>
                    <button
                      type="button"
                      onClick={() => setNotice("Nota guardada visualmente. Falta endpoint de nota medica.")}
                      className="rounded-xl bg-indigo-700 px-6 py-4 text-sm font-black text-white shadow-lg shadow-indigo-100 hover:bg-indigo-800"
                    >
                      Guardar y Finalizar
                    </button>
                  </div>
                </article>
              </div>

              <aside className="space-y-6">
                <article className="rounded-3xl bg-indigo-100 p-8 text-center shadow-sm">
                  <p className="mb-4 text-xs font-black uppercase tracking-[0.18em] text-indigo-400">
                    Estado actual
                  </p>
                  <span className="inline-flex rounded-full bg-white px-5 py-3 font-black text-indigo-700">
                    {statusLabel(selectedCita.estado)}
                  </span>
                  <p className="mt-5 text-sm font-bold text-indigo-500">
                    {selectedCita.fecha === today ? "Hoy" : formatLongDate(selectedCita.fecha)},{" "}
                    {timeText(selectedCita.hora_inicio)} hs
                  </p>
                </article>

                <article className="rounded-3xl bg-white p-6 shadow-sm">
                  <h3 className="mb-5 text-lg font-black">Historial Rapido</h3>
                  <div className="space-y-3">
                    <div className="rounded-xl bg-slate-50 p-4">
                      <p className="text-[10px] font-black uppercase text-slate-400">20 May 2023</p>
                      <p className="mt-1 text-sm font-bold">Consulta previa - Seguimiento</p>
                    </div>
                    <div className="rounded-xl bg-slate-50 p-4">
                      <p className="text-[10px] font-black uppercase text-slate-400">15 Ene 2023</p>
                      <p className="mt-1 text-sm font-bold">Control rutinario - OK</p>
                    </div>
                  </div>
                  <button type="button" className="mt-5 w-full text-sm font-black text-indigo-700">
                    Ver todo el historial
                  </button>
                </article>

                <article className="rounded-3xl bg-purple-50 p-6 shadow-sm">
                  <h3 className="mb-3 text-lg font-black text-purple-900">Recordatorio</h3>
                  <p className="text-sm font-semibold italic text-purple-700">
                    "Paciente solicita copia de resultados por email tras la consulta."
                  </p>
                </article>
              </aside>
            </div>
          </section>
        </div>
      )}

      {modalCita && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-6">
          <form onSubmit={handleReschedule} className="w-full max-w-2xl rounded-3xl bg-white p-8 shadow-2xl">
            <h2 className="text-3xl font-black">Reagendar por emergencia</h2>
            <p className="mt-2 text-sm text-slate-500">
              {modalCita.paciente?.nombre_completo} - {modalCita.motivo}
            </p>

            <div className="mt-8 grid grid-cols-1 gap-5 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-bold text-slate-600">Nueva fecha</label>
                <input
                  type="date"
                  value={nuevaFecha}
                  min={today}
                  onChange={(event) => setNuevaFecha(event.target.value)}
                  className="w-full rounded-xl bg-slate-100 px-4 py-3 outline-none focus:ring-2 focus:ring-indigo-200"
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-bold text-slate-600">Duracion</label>
                <select
                  value={duracion}
                  onChange={(event) => setDuracion(event.target.value)}
                  className="w-full rounded-xl bg-slate-100 px-4 py-3 outline-none focus:ring-2 focus:ring-indigo-200"
                >
                  <option value="30">30 minutos</option>
                  <option value="60">60 minutos</option>
                  <option value="90">90 minutos</option>
                </select>
              </div>
            </div>

            <div className="mt-6">
              <p className="mb-3 text-sm font-bold text-slate-600">Horario disponible</p>
              {loadingHorarios ? (
                <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">Consultando horarios...</p>
              ) : horarios.length > 0 ? (
                <div className="grid grid-cols-3 gap-3">
                  {horarios.map((horario) => (
                    <button
                      type="button"
                      key={`${horario.hora_inicio}-${horario.hora_fin}`}
                      onClick={() => setNuevaHora(horario.hora_inicio)}
                      className={`rounded-xl border py-3 text-sm font-bold ${
                        nuevaHora === horario.hora_inicio
                          ? "border-indigo-700 bg-indigo-700 text-white"
                          : "border-slate-200 text-slate-600 hover:border-indigo-300"
                      }`}
                    >
                      {horario.hora_inicio}
                    </button>
                  ))}
                </div>
              ) : (
                <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">
                  No hay horarios disponibles para esta fecha.
                </p>
              )}
            </div>

            <div className="mt-8 grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setModalCita(null)}
                className="rounded-xl bg-slate-100 py-4 font-bold text-slate-700 hover:bg-slate-200"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={saving}
                className="rounded-xl bg-indigo-700 py-4 font-bold text-white shadow-lg shadow-indigo-100 hover:bg-indigo-800 disabled:bg-indigo-300"
              >
                {saving ? "Guardando..." : "Guardar cambio"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
