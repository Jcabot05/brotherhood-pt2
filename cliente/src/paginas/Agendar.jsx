import { Link } from 'react-router-dom';

import { useSesion } from '../api/sesion';
import Mensaje from '../componentes/Mensaje';
import FormularioCita from './agendar/FormularioCita';
import TablaCitas from './agendar/TablaCitas';
import { useAgenda } from './agendar/useAgenda';

export default function Agendar() {
    const { usuario, cargando: cargandoSesion, refrescar } = useSesion();
    const agenda = useAgenda(usuario, refrescar);

    if (cargandoSesion) {
        return (
            <main className="contenido">
                <p className="vacio">Comprobando su sesión…</p>
            </main>
        );
    }

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

            <Mensaje tipo="error" texto={agenda.error} detalles={agenda.detalles} />
            <Mensaje tipo="exito" texto={agenda.exito} />

            <FormularioCita
                barberos={agenda.barberos}
                servicios={agenda.servicios}
                idBarbero={agenda.idBarbero}
                onBarbero={agenda.setIdBarbero}
                idServicio={agenda.idServicio}
                onServicio={agenda.setIdServicio}
                fecha={agenda.fecha}
                onFecha={agenda.setFecha}
                horarios={agenda.horarios}
                elegido={agenda.elegido}
                onElegir={agenda.setElegido}
                ayuda={agenda.ayuda}
                enviando={agenda.enviando}
                onEnviar={agenda.agendar}
            />

            <h2 className="seccion-titulo">Mis citas</h2>

            <TablaCitas
                citas={agenda.citas}
                barberos={agenda.barberos}
                servicios={agenda.servicios}
                onCancelar={agenda.cancelar}
            />
        </main>
    );
}
