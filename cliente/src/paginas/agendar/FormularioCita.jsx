import { formatearPrecio, hoyLocal } from '../../api/cliente';

export default function FormularioCita({
    barberos,
    servicios,
    idBarbero,
    onBarbero,
    idServicio,
    onServicio,
    fecha,
    onFecha,
    horarios,
    elegido,
    onElegir,
    ayuda,
    enviando,
    onEnviar,
}) {
    return (
        <form className="formulario tarjeta" onSubmit={onEnviar}>
            <div className="campo">
                <label htmlFor="barbero">Barbero</label>
                <select
                    id="barbero"
                    value={idBarbero}
                    onChange={e => onBarbero(e.target.value)}
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
                    onChange={e => onServicio(e.target.value)}
                    required
                >
                    {servicios.map(servicio => (
                        <option key={servicio.id_servicio} value={servicio.id_servicio}>
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
                    onChange={e => onFecha(e.target.value)}
                    required
                />
            </div>

            <div className="campo">
                <label>Horario</label>
                {horarios.length > 0 ? (
                    <>
                        <div className="horarios">
                            {horarios.map(horario => (
                                <button
                                    key={horario.inicio}
                                    type="button"
                                    aria-pressed={elegido === horario.inicio}
                                    className={`horario ${
                                        elegido === horario.inicio ? 'elegido' : ''
                                    }`}
                                    onClick={() => onElegir(horario.inicio)}
                                >
                                    {horario.etiqueta}
                                </button>
                            ))}
                        </div>
                        <p className="ayuda">{ayuda}</p>
                    </>
                ) : (
                    <p className="horarios-vacio">{ayuda}</p>
                )}
            </div>

            <button className="boton" disabled={!elegido || enviando}>
                {enviando ? 'Agendando…' : 'Agendar cita'}
            </button>
        </form>
    );
}
