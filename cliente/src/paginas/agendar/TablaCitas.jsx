import { useState } from 'react';

import { formatearFecha } from '../../api/cliente';
import Dialogo from '../../componentes/Dialogo';

export default function TablaCitas({ citas, barberos, servicios, onCancelar }) {
    const [porCancelar, setPorCancelar] = useState(null);

    if (citas.length === 0) {
        return (
            <p className="vacio">
                Todavía no tiene citas agendadas. Elija un horario para reservar la
                primera.
            </p>
        );
    }

    const nombreServicio = id =>
        servicios.find(s => s.id_servicio === id)?.nombre ?? 'Servicio';
    const nombreBarbero = id =>
        barberos.find(b => b.id_barbero === id)?.nombre ?? 'Barbero';

    function confirmar() {
        const cita = porCancelar;
        setPorCancelar(null);
        onCancelar(cita.id_cita);
    }

    return (
        <>
            <div className="tabla-envoltura">
                <table>
                    <thead>
                        <tr>
                            <th>Fecha y hora</th>
                            <th>Servicio</th>
                            <th>Barbero</th>
                            <th>Estado</th>
                            <th className="columna-accion"></th>
                        </tr>
                    </thead>
                    <tbody>
                        {citas.map(cita => (
                            <tr key={cita.id_cita}>
                                <td>{formatearFecha(cita.fecha_hora)}</td>
                                <td>{nombreServicio(cita.id_servicio)}</td>
                                <td>{nombreBarbero(cita.id_barbero)}</td>
                                <td>
                                    <span className={`etiqueta ${cita.estado}`}>
                                        {cita.estado}
                                    </span>
                                </td>
                                <td className="columna-accion">
                                    {cita.estado === 'agendada' && (
                                        <button
                                            type="button"
                                            className="boton boton-secundario boton-peligro boton-compacto"
                                            onClick={() => setPorCancelar(cita)}
                                        >
                                            Cancelar
                                        </button>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <Dialogo
                abierto={porCancelar !== null}
                titulo="¿Cancelar esta cita?"
                descripcion="La cita quedará registrada como cancelada y su horario volverá a estar disponible."
                detalle={
                    porCancelar && [
                        { etiqueta: 'Servicio', valor: nombreServicio(porCancelar.id_servicio) },
                        { etiqueta: 'Barbero', valor: nombreBarbero(porCancelar.id_barbero) },
                        { etiqueta: 'Fecha', valor: formatearFecha(porCancelar.fecha_hora) },
                    ]
                }
                textoConfirmar="Sí, cancelar"
                textoCancelar="Volver"
                peligroso
                onConfirmar={confirmar}
                onCerrar={() => setPorCancelar(null)}
            />
        </>
    );
}
