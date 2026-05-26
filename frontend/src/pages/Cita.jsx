import { useEffect, useMemo, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import {
  clearSession,
  createCita,
  createPaciente,
  getDisponibilidad,
  getDoctores,
  getParentescos,
  getPacientes,
  getStoredUser,
} from "../services/api"

const initialPatientForm = {
  nombre: "",
  apellido: "",
  sexo: "femenino",
  fecha_nacimiento: "",
  curp: "",
  parentesco: "hijo",
}

function formatDate(fecha) {
  if (!fecha) return "Selecciona una fecha"

  return new Date(`${fecha}T00:00:00`).toLocaleDateString("es-MX", {
    weekday: "long",
    day: "2-digit",
    month: "long",
    year: "numeric",
  })
}

function formatMoney(value) {
  if (value === null || value === undefined) return "Por definir"

  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
  }).format(value)
}

export default function Cita() {
  const navigate = useNavigate()
  const user = getStoredUser()
  const [fecha, setFecha] = useState("")
  const [hora, setHora] = useState("")
  const [motivo, setMotivo] = useState("")
  const [mostrarModal, setMostrarModal] = useState(false)
  const [patientForm, setPatientForm] = useState(initialPatientForm)
  const [pacienteSeleccionado, setPacienteSeleccionado] = useState("")
  const [doctorSeleccionado, setDoctorSeleccionado] = useState("")
  const [pacientes, setPacientes] = useState([])
  const [doctores, setDoctores] = useState([])
  const [parentescos, setParentescos] = useState([])
  const [horarios, setHorarios] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [loadingHorarios, setLoadingHorarios] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")

  const paciente = useMemo(
    () => pacientes.find((item) => item.id_paciente === pacienteSeleccionado),
    [pacienteSeleccionado, pacientes],
  )
  const doctor = useMemo(
    () => doctores.find((item) => item.id_doctor === doctorSeleccionado),
    [doctorSeleccionado, doctores],
  )
  const especialidades = useMemo(
    () => [...new Set(doctores.map((item) => item.especialidad).filter(Boolean))],
    [doctores],
  )

  const fechaFormateada = formatDate(fecha)

  useEffect(() => {
    async function loadInitialData() {
      setLoading(true)
      setError("")

      try {
        // Flujo de la guia para agendar:
        // 1. GET /pacientes/me
        // 2. GET /catalogos/doctores
        // 3. GET /catalogos/parentescos para el dropdown de paciente
        const [pacientesData, doctoresData, parentescosData] = await Promise.all([
          getPacientes(),
          getDoctores(),
          getParentescos(),
        ])
        const activos = pacientesData.filter((item) => item.activo)

        setPacientes(activos)
        setDoctores(doctoresData)
        setParentescos(parentescosData)
        setPacienteSeleccionado(activos[0]?.id_paciente || "")
        setDoctorSeleccionado(doctoresData[0]?.id_doctor || "")
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    loadInitialData()
  }, [])

  useEffect(() => {
    async function loadAvailability() {
      if (!doctorSeleccionado || !fecha) {
        setHorarios([])
        setHora("")
        return
      }

      setLoadingHorarios(true)
      setError("")

      try {
        // Guia: al elegir doctor y fecha se consulta disponibilidad.
        // El backend responde horarios_disponibles para pintarlos como botones.
        const disponibilidad = await getDisponibilidad(doctorSeleccionado, fecha)
        setHorarios(disponibilidad.horarios_disponibles || [])
        setHora("")
      } catch (err) {
        setHorarios([])
        setError(err.message)
      } finally {
        setLoadingHorarios(false)
      }
    }

    loadAvailability()
  }, [doctorSeleccionado, fecha])

  function logout() {
    clearSession()
    navigate("/", { replace: true })
  }

  function updatePatientForm(field, value) {
    setPatientForm((current) => ({ ...current, [field]: value }))
  }

  async function agregarPaciente(event) {
    event.preventDefault()
    setError("")
    setNotice("")

    try {
      // Guia: POST /pacientes recibe estos campos y el backend toma
      // id_usuario e id_clinica_tenant desde el token JWT.
      const created = await createPaciente({
        ...patientForm,
        curp: patientForm.curp.trim().toUpperCase(),
      })
      setPacientes((current) => [...current, created])
      setPacienteSeleccionado(created.id_paciente)
      setPatientForm(initialPatientForm)
      setMostrarModal(false)
      setNotice("Paciente agregado correctamente.")
    } catch (err) {
      setError(err.message)
    }
  }

  async function confirmarCita() {
    setError("")
    setNotice("")

    if (!pacienteSeleccionado || !doctorSeleccionado || !fecha || !hora || !motivo.trim()) {
      setError("Completa paciente, doctor, fecha, horario y motivo de consulta.")
      return
    }

    setSaving(true)

    try {
      // Guia: para cliente se manda id_paciente, id_doctor, fecha,
      // hora_inicio y motivo. No se manda hora_fin.
      const cita = await createCita({
        id_paciente: pacienteSeleccionado,
        id_doctor: doctorSeleccionado,
        fecha,
        hora_inicio: hora,
        motivo: motivo.trim(),
      })

      navigate("/confirmacion", { state: { cita } })
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 flex">
      <aside className="w-64 bg-white shadow-lg p-6 flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-3 mb-10">
            <div className="w-12 h-12 rounded-full bg-blue-500" />
            <div>
              <h2 className="font-bold text-gray-800">
                {user?.correo || "Usuario"}
              </h2>
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
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Agendar Nueva Cita</h1>
            <p className="text-gray-500">Completa los datos para confirmar tu cita medica</p>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-full bg-gray-300" />
            <span className="font-medium">{paciente?.nombre_completo || "Sin paciente"}</span>
          </div>
        </div>

        {error && (
          <p className="mb-6 rounded-xl bg-red-50 px-4 py-3 text-sm font-semibold text-red-600">
            {error}
          </p>
        )}
        {notice && (
          <p className="mb-6 rounded-xl bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700">
            {notice}
          </p>
        )}

        {loading ? (
          <div className="bg-white rounded-3xl p-8 shadow-sm">Cargando datos...</div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <section className="bg-white rounded-3xl p-6 shadow-sm">
                <h2 className="text-xl font-bold mb-6">Informacion de la cita</h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-sm font-semibold text-gray-600">
                        PARA QUIEN ES LA CITA?
                      </label>
                      <button
                        type="button"
                        onClick={() => setMostrarModal(true)}
                        className="w-9 h-9 rounded-full bg-blue-600 hover:bg-blue-700 text-white text-xl font-bold flex items-center justify-center"
                        aria-label="Agregar paciente"
                      >
                        +
                      </button>
                    </div>

                    <select
                      value={pacienteSeleccionado}
                      onChange={(event) => setPacienteSeleccionado(event.target.value)}
                      className="w-full bg-gray-100 rounded-xl px-4 py-3 outline-none"
                    >
                      <option value="">Selecciona un paciente</option>
                      {pacientes.map((item) => (
                        <option key={item.id_paciente} value={item.id_paciente}>
                          {item.nombre_completo} ({item.parentesco})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-sm font-semibold text-gray-600 block mb-2">
                      ESPECIALIDADES DISPONIBLES
                    </label>
                    <select className="w-full bg-gray-100 rounded-xl px-4 py-3 outline-none" value={doctor?.especialidad || ""} disabled>
                      <option>{doctor?.especialidad || especialidades[0] || "Sin especialidades"}</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="text-sm font-semibold text-gray-600 block mb-4">
                    SELECCIONA TU ESPECIALISTA
                  </label>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {doctores.map((item) => (
                      <button
                        type="button"
                        key={item.id_doctor}
                        onClick={() => setDoctorSeleccionado(item.id_doctor)}
                        className={`rounded-2xl p-4 flex items-center justify-between text-left cursor-pointer transition-all ${
                          doctorSeleccionado === item.id_doctor
                            ? "border-2 border-blue-500"
                            : "border border-gray-200"
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-12 h-12 rounded-full bg-blue-100" />
                          <div>
                            <h3 className="font-bold">{item.nombre_completo}</h3>
                            <p className="text-sm text-gray-500">{item.especialidad}</p>
                          </div>
                        </div>
                        {doctorSeleccionado === item.id_doctor && (
                          <div className="w-6 h-6 rounded-full bg-blue-500" />
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              </section>

              <section className="bg-white rounded-3xl p-6 shadow-sm">
                <h2 className="text-xl font-bold mb-6">Fecha y Hora</h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div>
                    <h3 className="font-semibold mb-4">Selecciona la fecha</h3>
                    <input
                      type="date"
                      value={fecha}
                      min={new Date().toISOString().slice(0, 10)}
                      onChange={(event) => setFecha(event.target.value)}
                      className="w-full bg-gray-100 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <p className="text-sm text-gray-500 mt-4">Fecha seleccionada:</p>
                    <p className="font-bold text-gray-800 capitalize">{fechaFormateada}</p>
                  </div>

                  <div>
                    <h3 className="font-semibold mb-4">Horarios Disponibles</h3>
                    {loadingHorarios ? (
                      <p className="text-gray-500">Consultando disponibilidad...</p>
                    ) : horarios.length > 0 ? (
                      <div className="grid grid-cols-2 gap-3">
                        {horarios.map((time) => (
                          <button
                            type="button"
                            key={`${time.hora_inicio}-${time.hora_fin}`}
                            onClick={() => setHora(time.hora_inicio)}
                            className={`border rounded-xl py-3 ${
                              hora === time.hora_inicio
                                ? "bg-blue-600 text-white border-blue-600"
                                : "hover:border-blue-500 hover:text-blue-600"
                            }`}
                          >
                            {time.hora_inicio}
                          </button>
                        ))}
                      </div>
                    ) : (
                      <p className="rounded-xl bg-gray-50 p-4 text-sm text-gray-500">
                        Selecciona doctor y fecha para ver horarios disponibles.
                      </p>
                    )}
                  </div>
                </div>
              </section>

              <section className="bg-white rounded-3xl p-6 shadow-sm">
                <h2 className="text-xl font-bold mb-6">Detalles Adicionales</h2>
                <label className="text-sm font-semibold text-gray-600 block mb-2">
                  DESCRIBE EL MOTIVO DE LA CONSULTA
                </label>
                <textarea
                  rows="5"
                  value={motivo}
                  onChange={(event) => setMotivo(event.target.value)}
                  placeholder="Describe brevemente el motivo de la consulta..."
                  className="w-full bg-gray-100 rounded-2xl p-4 outline-none resize-none"
                />
              </section>
            </div>

            <aside>
              <div className="bg-white rounded-3xl p-6 shadow-sm sticky top-6">
                <h2 className="text-2xl font-bold mb-6">Resumen de Cita</h2>
                <div className="space-y-5">
                  <div>
                    <p className="text-sm text-gray-500">PACIENTE</p>
                    <h3 className="font-bold">{paciente?.nombre_completo || "Sin seleccionar"}</h3>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">ESPECIALISTA</p>
                    <h3 className="font-bold">{doctor?.nombre_completo || "Sin seleccionar"}</h3>
                    <p className="text-sm text-gray-500">{doctor?.especialidad}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">FECHA Y HORA</p>
                    <h3 className="font-bold capitalize">{fechaFormateada}</h3>
                    <p className="text-gray-500">{hora || "Selecciona un horario"}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">DURACION ESTIMADA</p>
                    <h3 className="font-bold">30 minutos</h3>
                  </div>
                  <hr />
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="text-gray-500">Consulta General</p>
                      <p className="text-sm text-gray-400">Pago en consulta</p>
                    </div>
                    <h2 className="text-3xl font-bold text-blue-600">
                      {formatMoney(doctor?.precio_consulta)}
                    </h2>
                  </div>
                  <button
                    type="button"
                    onClick={confirmarCita}
                    disabled={saving}
                    className="block text-center w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white py-4 rounded-2xl font-semibold shadow-lg"
                  >
                    {saving ? "Agendando..." : "Confirmar y Agendar"}
                  </button>
                </div>
              </div>
            </aside>
          </div>
        )}
      </main>

      {mostrarModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-6 z-50">
          <form onSubmit={agregarPaciente} className="bg-white rounded-3xl shadow-xl p-8 w-full max-w-2xl">
            <h2 className="text-3xl font-bold text-gray-800 mb-2">Agregar paciente</h2>
            <p className="text-gray-500 mb-8">Registra los datos que solicita el backend.</p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
              <div>
                <label className="block text-sm font-semibold text-gray-600 mb-2">Nombre</label>
                <input
                  type="text"
                  value={patientForm.nombre}
                  onChange={(event) => updatePatientForm("nombre", event.target.value)}
                  placeholder="Ej. Ana"
                  required
                  className="w-full bg-gray-100 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-600 mb-2">Apellido</label>
                <input
                  type="text"
                  value={patientForm.apellido}
                  onChange={(event) => updatePatientForm("apellido", event.target.value)}
                  placeholder="Ej. Garcia Lopez"
                  required
                  className="w-full bg-gray-100 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
              <div>
                <label className="block text-sm font-semibold text-gray-600 mb-2">Fecha de nacimiento</label>
                <input
                  type="date"
                  value={patientForm.fecha_nacimiento}
                  onChange={(event) => updatePatientForm("fecha_nacimiento", event.target.value)}
                  required
                  className="w-full bg-gray-100 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-600 mb-2">CURP</label>
                <input
                  type="text"
                  value={patientForm.curp}
                  onChange={(event) => updatePatientForm("curp", event.target.value)}
                  placeholder="18 caracteres"
                  minLength={18}
                  maxLength={18}
                  required
                  className="w-full bg-gray-100 rounded-xl px-4 py-3 uppercase outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-8">
              <div>
                <label className="block text-sm font-semibold text-gray-600 mb-2">Parentesco</label>
                <select
                  value={patientForm.parentesco}
                  onChange={(event) => updatePatientForm("parentesco", event.target.value)}
                  className="w-full bg-gray-100 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {/* Guia: parentesco se obtiene de GET /catalogos/parentescos. */}
                  {(parentescos.length > 0 ? parentescos : [
                    { id_parentesco: "titular", parentesco: "titular" },
                    { id_parentesco: "hijo", parentesco: "hijo" },
                    { id_parentesco: "conyuge", parentesco: "conyuge" },
                  ]).map((item) => (
                    <option key={item.id_parentesco} value={item.parentesco}>
                      {item.parentesco}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-600 mb-2">Sexo</label>
                <select
                  value={patientForm.sexo}
                  onChange={(event) => updatePatientForm("sexo", event.target.value)}
                  className="w-full bg-gray-100 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {/* Guia: sexo solo acepta masculino, femenino u otro. */}
                  <option value="femenino">Femenino</option>
                  <option value="masculino">Masculino</option>
                  <option value="otro">Otro</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setMostrarModal(false)}
                className="bg-gray-100 hover:bg-gray-200 text-gray-700 py-4 rounded-xl font-semibold"
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-xl font-semibold shadow-lg"
              >
                Guardar Paciente
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
