/* Estado de la sesión.

   Como la cookie es httpOnly, el frontend no puede inspeccionar el token para
   saber si sigue vivo. En su lugar pregunta al servidor con `GET /auth/yo`,
   que además valida la firma y la vigencia. Esto corrige de paso un fallo de
   la versión anterior: comprobar sólo la presencia del token daba por buena
   una sesión ya expirada, y el error aparecía a mitad del flujo. */

import { createContext, useCallback, useContext, useEffect, useState } from 'react';

import { api } from './cliente';

const ContextoSesion = createContext(null);

export function ProveedorSesion({ children }) {
    const [usuario, setUsuario] = useState(null);
    const [cargando, setCargando] = useState(true);

    const refrescar = useCallback(async () => {
        try {
            setUsuario(await api.yo());
        } catch {
            // Un 401 aquí es lo normal cuando no hay sesión abierta.
            setUsuario(null);
        } finally {
            setCargando(false);
        }
    }, []);

    useEffect(() => {
        refrescar();
    }, [refrescar]);

    const entrar = useCallback(datos => {
        setUsuario(datos.usuario);
    }, []);

    const salir = useCallback(async () => {
        // La cookie sólo puede borrarla el servidor: el navegador no deja que
        // el JavaScript de la página toque una cookie httpOnly.
        try {
            await api.logout();
        } finally {
            setUsuario(null);
        }
    }, []);

    return (
        <ContextoSesion.Provider
            value={{ usuario, cargando, entrar, salir, refrescar }}
        >
            {children}
        </ContextoSesion.Provider>
    );
}

export function useSesion() {
    const contexto = useContext(ContextoSesion);
    if (contexto === null) {
        throw new Error('useSesion debe usarse dentro de <ProveedorSesion>.');
    }
    return contexto;
}
