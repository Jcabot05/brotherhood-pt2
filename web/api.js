/* Cliente de la API y manejo de la sesión.
   Compartido por las tres páginas del sitio. */

const API = window.location.origin;

/* --- Sesión ----------------------------------------------------------
   El token se guarda en sessionStorage: se borra al cerrar la pestaña y no
   viaja a otros orígenes. No es almacenamiento seguro frente a XSS, pero para
   el alcance de este proyecto es preferible a dejarlo en localStorage, donde
   sobreviviría indefinidamente. */

const Sesion = {
    guardar(datos) {
        sessionStorage.setItem('brotherhood_token', datos.token_acceso);
        sessionStorage.setItem('brotherhood_usuario', JSON.stringify(datos.usuario));
    },

    token() {
        return sessionStorage.getItem('brotherhood_token');
    },

    usuario() {
        const crudo = sessionStorage.getItem('brotherhood_usuario');
        return crudo ? JSON.parse(crudo) : null;
    },

    activa() {
        return Boolean(this.token());
    },

    cerrar() {
        sessionStorage.removeItem('brotherhood_token');
        sessionStorage.removeItem('brotherhood_usuario');
    }
};

/* --- Peticiones ------------------------------------------------------ */

async function pedir(metodo, ruta, cuerpo = null, conToken = false) {
    const opciones = { method: metodo, headers: {} };

    if (cuerpo !== null) {
        opciones.headers['Content-Type'] = 'application/json';
        opciones.body = JSON.stringify(cuerpo);
    }

    if (conToken) {
        const token = Sesion.token();
        if (token) opciones.headers['Authorization'] = `Bearer ${token}`;
    }

    const respuesta = await fetch(API + ruta, opciones);
    const texto = await respuesta.text();
    let datos = null;

    try {
        datos = texto ? JSON.parse(texto) : null;
    } catch {
        datos = texto;
    }

    if (!respuesta.ok) {
        throw new ErrorApi(respuesta.status, datos);
    }
    return datos;
}

/* --- Errores ---------------------------------------------------------
   Traduce cada código HTTP al mensaje que corresponde a su causa, siguiendo
   RN-19, sin exponer detalles internos del servidor (RN-20). */

/* Traduce el motivo de una validación fallida.
   Se resuelve por el tipo de error, que es estable, y solo se recurre al texto
   original cuando el tipo no está contemplado. */
function traducirMotivo(mensaje, tipo, contexto) {
    // El texto original es más específico que el tipo en algunos casos, así que
    // se revisa primero.
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
        less_than_equal: 'no puede ser mayor'
    };

    return (tipo && porTipo[tipo]) || 'no es válido';
}


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
                return Sesion.activa()
                    ? 'Su sesión expiró. Vuelva a iniciar sesión para continuar.'
                    : 'Necesita iniciar sesión para realizar esta acción.';
            case 403:
                return this.detalle() || 'No tiene permisos para realizar esta acción.';
            case 404:
                return this.detalle() || 'No encontramos lo que busca. Puede que ya no esté disponible.';
            case 409:
                return this.detalle() || 'Ese horario ya no está disponible. Elija otro.';
            case 422:
                // El servidor explica el motivo cuando puede; si no, se orienta
                // a revisar el formulario.
                return this.detalle() || 'Revise los datos del formulario: hay campos incompletos o inválidos.';
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
       El servidor los entrega con el nombre técnico del campo y el motivo en
       inglés, así que aquí se traducen a lo que el formulario muestra. */
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
            id_servicio: 'Servicio'
        };

        return d.map(item => {
            const ubicacion = Array.isArray(item.loc) ? item.loc : [];
            const clave = ubicacion.filter(p => p !== 'body').join('.');
            const campo = nombres[clave] || 'Dato';
            return `${campo}: ${traducirMotivo(item.msg, item.type, item.ctx)}`;
        });
    }
}

/* --- Presentación ---------------------------------------------------- */

function mostrarMensaje(elemento, tipo, texto, detalles = []) {
    elemento.className = `mensaje ${tipo}`;
    elemento.innerHTML = '';

    const parrafo = document.createElement('div');
    parrafo.textContent = texto;
    elemento.appendChild(parrafo);

    if (detalles.length) {
        const lista = document.createElement('ul');
        for (const detalle of detalles) {
            const item = document.createElement('li');
            item.textContent = detalle;
            lista.appendChild(item);
        }
        elemento.appendChild(lista);
    }

    elemento.classList.remove('oculto');
}

function mostrarError(elemento, error) {
    /* El código HTTP queda fuera del mensaje: a quien reserva le importa qué
       pasó y qué hacer, no el número con el que el servidor lo expresó. */
    if (error instanceof ErrorApi) {
        mostrarMensaje(elemento, 'error', error.mensaje, error.camposInvalidos);
    } else {
        mostrarMensaje(
            elemento,
            'error',
            'No pudimos conectarnos en este momento. Revise su conexión e intente de nuevo.'
        );
    }
}

function ocultarMensaje(elemento) {
    elemento.classList.add('oculto');
    elemento.textContent = '';
}

/* --- Formato --------------------------------------------------------- */

function formatearPrecio(valor) {
    return `$${Number(valor).toFixed(2)}`;
}

/* RN-17: la API almacena en UTC; la conversión a hora local ocurre aquí. */
function formatearFecha(iso) {
    const fecha = new Date(iso);
    return fecha.toLocaleString('es-EC', {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/* --- Barra de navegación --------------------------------------------- */

function pintarSesionEnBarra() {
    const contenedor = document.getElementById('estado-sesion');
    if (!contenedor) return;

    const usuario = Sesion.usuario();

    if (!usuario) {
        contenedor.innerHTML = '<a href="/app/login.html">Iniciar sesión</a>';
        return;
    }

    contenedor.innerHTML = '';

    const etiqueta = document.createElement('span');
    etiqueta.className = 'sesion';
    etiqueta.innerHTML = `<strong>${usuario.correo}</strong>`;

    const salir = document.createElement('a');
    salir.href = '#';
    salir.textContent = 'Cerrar sesión';
    salir.addEventListener('click', evento => {
        evento.preventDefault();
        Sesion.cerrar();
        window.location.href = '/app/';
    });

    contenedor.append(etiqueta, salir);
}

document.addEventListener('DOMContentLoaded', pintarSesionEnBarra);
