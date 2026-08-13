import { formatearFecha } from '../../api/cliente';

export default function TablaCitas({ citas, barberos, servicios, onCancelar }) {
    if (citas.length === 0) {
        return <p className="vacio">Todavía no tiene citas agendadas.</p>;
    }

    return (
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
                                            onClick={() => onCancelar(cita.id_cita)}
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
    );
}
