import { useEffect, useState } from 'react';

import { ErrorApi, api, formatearPrecio } from '../api/cliente';
import { imagenDeServicio } from '../api/imagenes';
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

            {cargando && (
                <section className="rejilla" aria-hidden="true">
                    {[0, 1, 2].map(indice => (
                        <article className="servicio" key={indice}>
                            <div className="esqueleto esqueleto-imagen" />
                            <div className="servicio-cuerpo">
                                <div className="esqueleto esqueleto-linea" />
                                <div className="esqueleto esqueleto-linea corta" />
                                <div className="esqueleto esqueleto-linea precio" />
                            </div>
                        </article>
                    ))}
                </section>
            )}

            {!cargando && !error && servicios.length === 0 && (
                <p className="vacio">Todavía no hay servicios publicados.</p>
            )}

            {servicios.length > 0 && (
                <section className="rejilla">
                    {servicios.map(servicio => (
                        <article className="servicio" key={servicio.id_servicio}>
                            <img
                                className="servicio-imagen"
                                src={imagenDeServicio(servicio.nombre)}
                                alt=""
                                loading="lazy"
                                width="600"
                                height="450"
                            />
                            <div className="servicio-cuerpo">
                                <h2>{servicio.nombre}</h2>
                                <p className="duracion">{servicio.duracion_min} minutos</p>
                                <p className="precio">{formatearPrecio(servicio.precio)}</p>
                            </div>
                        </article>
                    ))}
                </section>
            )}

            <p className="nota">Atendemos de lunes a sábado, de 9:00 a 19:00.</p>
        </main>
    );
}
