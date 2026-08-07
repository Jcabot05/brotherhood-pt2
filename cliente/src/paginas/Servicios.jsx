/* HU-01: catálogo de servicios, de acceso público.

   No requiere sesión: el visitante debe poder ver qué se ofrece y cuánto
   cuesta antes de decidirse a crear una cuenta (RN-01). */

import { useEffect, useState } from 'react';

import { ErrorApi, api, formatearPrecio } from '../api/cliente';
import Mensaje from '../componentes/Mensaje';

export default function Servicios() {
    const [servicios, setServicios] = useState([]);
    const [cargando, setCargando] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        api.servicios()
            .then(setServicios)
            .catch(fallo =>
                setError(
                    fallo instanceof ErrorApi
                        ? fallo.mensaje
                        : 'No pudimos cargar el catálogo. Intente de nuevo.'
                )
            )
            .finally(() => setCargando(false));
    }, []);

    return (
        <main className="contenido">
            <div className="encabezado">
                <h1>Nuestros servicios</h1>
                <p>Elija el servicio que necesita y reserve su cita en línea.</p>
            </div>

            <Mensaje tipo="error" texto={error} />

            {cargando && <p className="vacio">Cargando el catálogo…</p>}

            {/* Un catálogo vacío no es un error: se informa y ya. */}
            {!cargando && !error && servicios.length === 0 && (
                <p className="vacio">Todavía no hay servicios publicados.</p>
            )}

            {servicios.length > 0 && (
                <section className="rejilla">
                    {servicios.map(servicio => (
                        <article className="servicio" key={servicio.id_servicio}>
                            <h2>{servicio.nombre}</h2>
                            <p className="duracion">{servicio.duracion_min} minutos</p>
                            <p className="precio">{formatearPrecio(servicio.precio)}</p>
                        </article>
                    ))}
                </section>
            )}

            <p className="nota">Atendemos de lunes a sábado, de 9:00 a 19:00.</p>
        </main>
    );
}
