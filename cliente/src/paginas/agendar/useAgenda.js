/* Estado y operaciones de la página de agendar.

   Reúne las opciones del formulario, los horarios libres y las citas del
   cliente, de modo que la página se ocupe sólo de presentarlos. */

import { useCallback, useEffect, useState } from 'react';

import { api, hoyLocal } from '../../api/cliente';
import { useFalloApi } from '../../api/useFalloApi';

export function useAgenda(usuario, refrescarSesion) {
    const { error, detalles, manejarFallo, limpiar } = useFalloApi(refrescarSesion);

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
    const [exito, setExito] = useState(null);

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
        limpiar();
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
        limpiar();
        setExito(null);
        try {
            await api.cancelar(idCita);
            setExito('Cita cancelada.');
            await Promise.all([cargarCitas(), cargarHorarios()]);
        } catch (fallo) {
            await manejarFallo(fallo);
        }
    }

    return {
        barberos,
        servicios,
        citas,
        idBarbero,
        setIdBarbero,
        idServicio,
        setIdServicio,
        fecha,
        setFecha,
        horarios,
        elegido,
        setElegido,
        ayuda,
        enviando,
        error,
        detalles,
        exito,
        agendar,
        cancelar,
    };
}
