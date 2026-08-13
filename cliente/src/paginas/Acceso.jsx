/* Inicio de sesión y registro.

   Al entrar, el servidor devuelve la sesión en una cookie httpOnly. Este
   componente nunca ve el token: sólo guarda en memoria los datos del usuario
   que vienen en el cuerpo de la respuesta. */

import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { api } from '../api/cliente';
import { useSesion } from '../api/sesion';
import { useFalloApi } from '../api/useFalloApi';
import Mensaje from '../componentes/Mensaje';

export default function Acceso() {
    const [vista, setVista] = useState('login');
    const [enviando, setEnviando] = useState(false);
    const [exito, setExito] = useState(null);
    const { error, detalles, manejarFallo, limpiar } = useFalloApi();

    const { usuario, entrar } = useSesion();
    const navegar = useNavigate();
    const ubicacion = useLocation();

    // A dónde volver tras identificarse. Se acepta sólo una ruta interna:
    // un destino externo convertiría el enlace en un salto a otro sitio.
    const destinoCrudo = new URLSearchParams(ubicacion.search).get('destino');
    const destino =
        destinoCrudo && destinoCrudo.startsWith('/') && !destinoCrudo.startsWith('//')
            ? destinoCrudo
            : '/agendar';

    function cambiarVista(nueva) {
        setVista(nueva);
        limpiar();
    }

    async function enviar(evento, accion) {
        evento.preventDefault();
        setEnviando(true);
        limpiar();

        const campos = Object.fromEntries(new FormData(evento.target));

        try {
            const datos = await accion(campos);
            entrar(datos);
            setExito('Acceso correcto. Redirigiendo…');
            navegar(destino, { replace: true });
        } catch (fallo) {
            await manejarFallo(fallo);
        } finally {
            setEnviando(false);
        }
    }

    return (
        <main className="contenido contenido-estrecho">
            <div className="encabezado">
                <h1>Acceder</h1>
                <p>Identifíquese para agendar y consultar sus citas.</p>
            </div>

            {usuario && (
                <Mensaje
                    tipo="aviso"
                    texto={`Ya hay una sesión abierta como ${usuario.correo}.`}
                />
            )}

            <div className="pestanas">
                <button
                    className={`pestana ${vista === 'login' ? 'activa' : ''}`}
                    onClick={() => cambiarVista('login')}
                    type="button"
                >
                    Iniciar sesión
                </button>
                <button
                    className={`pestana ${vista === 'registro' ? 'activa' : ''}`}
                    onClick={() => cambiarVista('registro')}
                    type="button"
                >
                    Crear cuenta
                </button>
            </div>

            <Mensaje tipo="error" texto={error} detalles={detalles} />
            <Mensaje tipo="exito" texto={exito} />

            {vista === 'login' ? (
                <form className="formulario" onSubmit={e => enviar(e, api.login)}>
                    <div className="campo">
                        <label htmlFor="correo">Correo</label>
                        <input
                            id="correo"
                            name="correo"
                            type="email"
                            autoComplete="email"
                            required
                        />
                    </div>
                    <div className="campo">
                        <label htmlFor="contrasena">Contraseña</label>
                        <input
                            id="contrasena"
                            name="contrasena"
                            type="password"
                            autoComplete="current-password"
                            required
                        />
                    </div>
                    <button className="boton" disabled={enviando}>
                        {enviando ? 'Entrando…' : 'Iniciar sesión'}
                    </button>
                </form>
            ) : (
                <form className="formulario" onSubmit={e => enviar(e, api.registro)}>
                    <div className="campo">
                        <label htmlFor="nombre">Nombre</label>
                        <input id="nombre" name="nombre" type="text" required />
                    </div>
                    <div className="campo">
                        <label htmlFor="telefono">Teléfono</label>
                        <input
                            id="telefono"
                            name="telefono"
                            type="tel"
                            minLength="7"
                            required
                        />
                    </div>
                    <div className="campo">
                        <label htmlFor="reg-correo">Correo</label>
                        <input
                            id="reg-correo"
                            name="correo"
                            type="email"
                            autoComplete="email"
                            required
                        />
                    </div>
                    <div className="campo">
                        <label htmlFor="reg-contrasena">Contraseña</label>
                        <input
                            id="reg-contrasena"
                            name="contrasena"
                            type="password"
                            autoComplete="new-password"
                            minLength="8"
                            required
                        />
                        <p className="ayuda">
                            Mínimo 8 caracteres. Se almacena cifrada, nunca en texto
                            plano.
                        </p>
                    </div>
                    <button className="boton" disabled={enviando}>
                        {enviando ? 'Creando…' : 'Crear cuenta'}
                    </button>
                </form>
            )}

            <p className="nota">
                Por seguridad, la sesión se cierra tras un tiempo de inactividad.{' '}
                <Link className="enlace" to="/">
                    Volver al catálogo
                </Link>
            </p>
        </main>
    );
}
