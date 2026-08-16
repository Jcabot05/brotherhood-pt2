import { useCallback, useState } from 'react';

import { ErrorApi } from './cliente';

export function useFalloApi(refrescarSesion = null) {
    const [error, setError] = useState(null);
    const [detalles, setDetalles] = useState([]);

    const limpiar = useCallback(() => {
        setError(null);
        setDetalles([]);
    }, []);

    const manejarFallo = useCallback(
        async fallo => {
            setDetalles([]);

            if (fallo instanceof ErrorApi && fallo.codigo === 401 && refrescarSesion) {
                setError('Su sesión expiró. Vuelva a iniciar sesión para continuar.');
                await refrescarSesion();
                return;
            }
            if (fallo instanceof ErrorApi) {
                setError(fallo.mensaje);
                setDetalles(fallo.camposInvalidos);
                return;
            }
            setError('No pudimos completar la operación. Intente de nuevo.');
        },
        [refrescarSesion]
    );

    return { error, detalles, manejarFallo, limpiar, setError };
}
