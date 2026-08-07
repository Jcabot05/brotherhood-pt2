/* HU-02: agendar una cita y consultar las propias.

   Exige sesión (RN-02). La cita se asocia siempre al dueño de la sesión, así
   que el formulario no envía `id_cliente`: lo resuelve el servidor a partir
   de la cookie (RN-03). */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import {
    ErrorApi,
    api,
    formatearFecha,
    formatearPrecio,
    hoyLocal,
} from '../api/cliente';
import { useSesion } from '../api/sesion';
import Mensaje from '../componentes/Mensaje';

export default function Agendar() {
    const { usuario, cargando: cargandoSesion, refrescar } = useSesion();

    const [barberos, setBarberos] = useState([]);
    const [servicios, setServicios] = useState([]);
    const [citas, setCitas] = useState([]);

    const [idBarbero, setIdBarbero] = useState('');
    const [idServicio, setIdServicio] = useState('');
    const [fecha, setFecha] = useState(hoyLocal());
    const [horarios, setHorarios] = useState([]);
    const [elegido, setElegido] = useState(null);
    const [ayuda, setAyuda] = useState('Elija barbero, servicio y día.');

    const [enviando, setEnviando] = useState(false);
    const [error, setError] = useState(null);
    const [detalles, setDetalles] = useState([]);
    const [exito, setExito] = useState(null);

    /* Un 401 en cualquier operación significa que la sesión caducó: se
       revalida contra el servidor para que la interfaz refleje la realidad. */
    const manejarFallo = useCallback(
        async fallo => {
            if (fallo instanceof ErrorApi && fallo.codigo === 401) {
                setError('Su sesión expiró. Vuelva a iniciar sesión para continuar.');
                await refrescar();
                return;
            }
            if (fallo instanceof ErrorApi) {
                setError(fallo.mensaje);
                setDetalles(fallo.camposInvalidos);
                return;
            }
            setError('No pudimos completar la operación. Intente de nuevo.');
        },
        [refrescar]
    );

    const cargarCitas = useCallback(async () => {
        try {
            setCitas(await api.misCitas());
        } catch (fallo) {
            await manejarFallo(fallo);
        }
    }, [manejarFallo]);

    // Opciones del formulario y citas ya agendadas.
    useEffect(() => {
        if (!usuario) return;

        Promise.all([api.barberos(), api.servicios()])
            .then(([listaBarberos, listaServicios]) => {
                setBarberos(listaBarberos);
                setServicios(listaServicios);
                if (listaBarberos.length > 0) {
                    setIdBarbero(String(listaBarberos[0].id_barbero));
                }
                if (listaServicios.length > 0) {
                    setIdServicio(String(listaServicios[0].id_servicio));
                }
            })
            .catch(manejarFallo);

        cargarCitas();
    }, [usuario, cargarCitas, manejarFallo]);

    /* Horarios libres. Se recalculan al cambiar barbero, servicio o día: así
       quien reserva elige entre opciones válidas en lugar de descubrir el
       conflicto al enviar el formulario. */
    const cargarHorarios = useCallback(async () => {
        if (!idBarbero || !idServicio || !fecha) return;

        setElegido(null);
        setHorarios([]);
        setAyuda('Buscando horarios…');

        try {
            const datos = await api.disponibilidad(idBarbero, idServicio, fecha);

            if (!datos.atiende) {
                setAyuda(`La barbería no atiende ese día. ${datos.horario_atencion}.`);
                return;
            }
            if (datos.horarios.length === 0) {
                setAyuda('No quedan horarios libres ese día. Pruebe con otra fecha.');
                return;
            }

            setHorarios(datos.horarios);
            setAyuda(
                `${datos.horarios.length} horarios libres · ${datos.duracion_min} minutos por cita.`
            );
        } catch (fallo) {
            setAyuda('');
            await manejarFallo(fallo);
        }
    }, [idBarbero, idServicio, fecha, manejarFallo]);

    useEffect(() => {
        if (usuario) cargarHorarios();
    }, [usuario, cargarHorarios]);

    async function agendar(evento) {
        evento.preventDefault();
        if (!elegido) return;

        setEnviando(true);
        setError(null);
        setDetalles([]);
        setExito(null);

        try {
            // `fecha_hora` se devuelve tal cual la entregó el servidor, en UTC
            // (RN-17). El cuerpo no lleva `id_cliente`: lo deduce la API de la
            // sesión.
            await api.agendar({
                id_barbero: Number(idBarbero),
                id_servicio: Number(idServicio),
                fecha_hora: elegido,
            });
            setExito('Cita agendada correctamente.');
            await Promise.all([cargarCitas(), cargarHorarios()]);
        } catch (fallo) {
            await manejarFallo(fallo);
        } finally {
            setEnviando(false);
        }
    }

    async function cancelar(idCita) {
        setError(null);
        setExito(null);
        try {
            await api.cancelar(idCita);
            setExito('Cita cancelada.');
            await Promise.all([cargarCitas(), cargarHorarios()]);
        } catch (fallo) {
            await manejarFallo(fallo);
        }
    }

    if (cargandoSesion) {
        return (
            <main className="contenido">
                <p className="vacio">Comprobando su sesión…</p>
            </main>
        );
    }

    // Sin sesión no se muestra el formulario. El servidor lo rechazaría de
    // todos modos (RN-02); esto evita el viaje en balde.
    if (!usuario) {
        return (
            <main className="contenido">
                <div className="encabezado">
                    <h1>Agendar una cita</h1>
                </div>
                <div className="tarjeta">
                    <p>Necesita iniciar sesión para agendar una cita.</p>
                    <Link className="boton" to="/login?destino=/agendar">
                        Acceder
                    </Link>
                </div>
            </main>
        );
    }

    return (
        <main className="contenido">
            <div className="encabezado">
                <h1>Agendar una cita</h1>
                <p>Elija barbero, servicio y uno de los horarios disponibles.</p>
            </div>

            <Mensaje tipo="error" texto={error} detalles={detalles} />
            <Mensaje tipo="exito" texto={exito} />

            <form className="formulario tarjeta" onSubmit={agendar}>
                <div className="campo">
                    <label htmlFor="barbero">Barbero</label>
                    <select
                        id="barbero"
                        value={idBarbero}
                        onChange={e => setIdBarbero(e.target.value)}
                        required
                    >
                        {barberos.map(barbero => (
                            <option key={barbero.id_barbero} value={barbero.id_barbero}>
                                {barbero.nombre}
                                {barbero.especialidad ? ` — ${barbero.especialidad}` : ''}
                            </option>
                        ))}
                    </select>
                </div>

                <div className="campo">
                    <label htmlFor="servicio">Servicio</label>
                    <select
                        id="servicio"
                        value={idServicio}
                        onChange={e => setIdServicio(e.target.value)}
                        required
                    >
                        {servicios.map(servicio => (
                            <option
                                key={servicio.id_servicio}
                                value={servicio.id_servicio}
                            >
                                {servicio.nombre} — {formatearPrecio(servicio.precio)} ·{' '}
                                {servicio.duracion_min} min
                            </option>
                        ))}
                    </select>
                </div>

                <div className="campo">
                    <label htmlFor="fecha">Día</label>
                    <input
                        id="fecha"
                        type="date"
                        value={fecha}
                        min={hoyLocal()}
                        onChange={e => setFecha(e.target.value)}
                        required
                    />
                </div>

                <div className="campo">
                    <label>Horario</label>
                    <div className="horarios">
                        {horarios.map(horario => (
                            <button
                                key={horario.inicio}
                                type="button"
                                className={`horario ${
                                    elegido === horario.inicio ? 'elegido' : ''
                                }`}
                                onClick={() => setElegido(horario.inicio)}
                            >
                                {horario.etiqueta}
                            </button>
                        ))}
                    </div>
                    <p className="ayuda">{ayuda}</p>
                </div>

                <button className="boton" disabled={!elegido || enviando}>
                    {enviando ? 'Agendando…' : 'Agendar cita'}
                </button>
            </form>

            <h2>Mis citas</h2>

            {citas.length === 0 ? (
                <p className="vacio">Todavía no tiene citas agendadas.</p>
            ) : (
                <div className="tabla-envoltura">
                    <table>
                        <thead>
                            <tr>
                                <th>Fecha y hora</th>
                                <th>Servicio</th>
                                <th>Barbero</th>
                                <th>Estado</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {citas.map(cita => {
                                const servicio = servicios.find(
                                    s => s.id_servicio === cita.id_servicio
                                );
                                const barbero = barberos.find(
                                    b => b.id_barbero === cita.id_barbero
                                );
                                return (
                                    <tr key={cita.id_cita}>
                                        <td>{formatearFecha(cita.fecha_hora)}</td>
                                        <td>{servicio ? servicio.nombre : '—'}</td>
                                        <td>{barbero ? barbero.nombre : '—'}</td>
                                        <td>
                                            <span className={`etiqueta ${cita.estado}`}>
                                                {cita.estado}
                                            </span>
                                        </td>
                                        <td className="acciones">
                                            {cita.estado === 'agendada' && (
                                                <button
                                                    className="boton-secundario"
                                                    onClick={() => cancelar(cita.id_cita)}
                                                    type="button"
                                                >
                                                    Cancelar
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </main>
    );
}
