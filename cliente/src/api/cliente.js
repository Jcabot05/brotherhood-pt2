/* Capa de acceso a la API.

   La sesión ya no se guarda aquí: viaja en una cookie httpOnly que el
   navegador adjunta sola y que este código no puede leer. Por eso no hay
   token que almacenar, ni cabecera Authorization que construir, ni forma de
   que una inyección de script se lleve la sesión. */

class ErrorApi extends Error {
    constructor(codigo, cuerpo) {
        super(`HTTP ${codigo}`);
        this.codigo = codigo;
        this.cuerpo = cuerpo;
    }

    /* Mensaje principal, legible para una persona. */
    get mensaje() {
        switch (this.codigo) {
            case 401:
                return 'Necesita iniciar sesión para realizar esta acción.';
            case 403:
                return this.detalle() || 'No tiene permisos para realizar esta acción.';
            case 404:
                return (
                    this.detalle() ||
                    'No encontramos lo que busca. Puede que ya no esté disponible.'
                );
            case 409:
                return this.detalle() || 'Ese horario ya no está disponible. Elija otro.';
            case 422:
                // El servidor explica el motivo cuando puede; si no, se orienta
                // a revisar el formulario.
                return (
                    this.detalle() ||
                    'Revise los datos del formulario: hay campos incompletos o inválidos.'
                );
            default:
                return this.detalle() || 'No pudimos completar la operación. Intente de nuevo.';
        }
    }

    /* Detalle textual cuando la API lo entrega como cadena. */
    detalle() {
        const d = this.cuerpo && this.cuerpo.detail;
        return typeof d === 'string' ? d : null;
    }

    /* Errores de validación campo por campo.
       El servidor los entrega con el nombre técnico del campo, así que aquí
       se traducen a lo que el formulario muestra. */
    get camposInvalidos() {
        const d = this.cuerpo && this.cuerpo.detail;
        if (!Array.isArray(d)) return [];

        const nombres = {
            correo: 'Correo',
            contrasena: 'Contraseña',
            nombre: 'Nombre',
            telefono: 'Teléfono',
            fecha_hora: 'Fecha y hora',
            id_barbero: 'Barbero',
            id_servicio: 'Servicio',
        };

        return d.map(item => {
            const ubicacion = Array.isArray(item.loc) ? item.loc : [];
            const clave = ubicacion.filter(p => p !== 'body').join('.');
            // `non_field_errors` agrupa lo que no pertenece a un campo
            // concreto: ahí el mensaje del servidor ya se explica solo.
            if (clave === 'non_field_errors') return item.msg;
            const campo = nombres[clave] || 'Dato';
            return `${campo}: ${traducirMotivo(item.msg, item.type, item.ctx)}`;
        });
    }
}

function traducirMotivo(mensaje, tipo, contexto) {
    // El texto original es más específico que el tipo en algunos casos, así
    // que se revisa primero.
    if (typeof mensaje === 'string') {
        if (/valid email/i.test(mensaje)) return 'no es un correo válido';
    }

    if (tipo === 'string_too_short' && contexto && contexto.min_length) {
        const minimo = contexto.min_length;
        return minimo === 1
            ? 'no puede quedar vacío'
            : `debe tener al menos ${minimo} caracteres`;
    }

    const porTipo = {
        missing: 'este campo es obligatorio',
        string_too_short: 'es demasiado corto',
        string_too_long: 'es demasiado largo',
        value_error: 'el formato no es válido',
        datetime_parsing: 'la fecha no tiene un formato válido',
        int_parsing: 'debe ser un número',
        greater_than: 'debe ser mayor',
        greater_than_equal: 'no puede ser menor',
        less_than: 'debe ser menor',
        less_than_equal: 'no puede ser mayor',
    };

    return (tipo && porTipo[tipo]) || 'no es válido';
}

async function pedir(metodo, ruta, cuerpo = null) {
    const opciones = {
        method: metodo,
        headers: {},
        // Manda la cookie de sesión. En desarrollo el frontend corre en otro
        // puerto, así que hace falta declararlo expresamente.
        credentials: 'include',
    };

    if (cuerpo !== null) {
        opciones.headers['Content-Type'] = 'application/json';
        opciones.body = JSON.stringify(cuerpo);
    }

    const respuesta = await fetch(ruta, opciones);

    if (respuesta.status === 204) return null;

    const texto = await respuesta.text();
    let datos;
    try {
        datos = texto ? JSON.parse(texto) : null;
    } catch {
        datos = texto;
    }

    if (!respuesta.ok) throw new ErrorApi(respuesta.status, datos);
    return datos;
}

/* --- Operaciones ------------------------------------------------------ */

export const api = {
    // Sesión
    registro: datos => pedir('POST', '/auth/registro', datos),
    login: datos => pedir('POST', '/auth/login', datos),
    logout: () => pedir('POST', '/auth/logout'),
    yo: () => pedir('GET', '/auth/yo'),

    // Catálogo
    servicios: () => pedir('GET', '/servicios/'),
    barberos: () => pedir('GET', '/barberos/'),

    // Citas
    misCitas: () => pedir('GET', '/citas/'),
    agendar: datos => pedir('POST', '/citas/', datos),
    cancelar: id => pedir('DELETE', `/citas/${id}`),
    disponibilidad: (idBarbero, idServicio, fecha) =>
        pedir(
            'GET',
            `/citas/disponibilidad?id_barbero=${idBarbero}` +
                `&id_servicio=${idServicio}&fecha=${fecha}`
        ),
};

export { ErrorApi };

/* --- Formato ---------------------------------------------------------- */

export function formatearPrecio(precio) {
    return `$${Number(precio).toFixed(2)}`;
}

export function formatearFecha(iso) {
    // La API almacena en UTC (RN-17); la conversión a hora local ocurre aquí.
    return new Date(iso).toLocaleString('es-EC', {
        dateStyle: 'medium',
        timeStyle: 'short',
    });
}

export function hoyLocal() {
    const ahora = new Date();
    const desfase = ahora.getTimezoneOffset() * 60000;
    return new Date(ahora - desfase).toISOString().slice(0, 10);
}
