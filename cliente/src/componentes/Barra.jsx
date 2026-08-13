import { Link, NavLink, useNavigate } from 'react-router-dom';

import { useSesion } from '../api/sesion';

export default function Barra() {
    const { usuario, salir } = useSesion();
    const navegar = useNavigate();

    async function cerrarSesion() {
        await salir();
        navegar('/');
    }

    return (
        <header className="barra">
            <div className="barra-contenido">
                <Link className="marca" to="/">
                    TheBrotherhood
                </Link>

                <nav className="navegacion">
                    <NavLink to="/" end>
                        Servicios
                    </NavLink>
                    <NavLink to="/agendar">Agendar</NavLink>
                </nav>

                <span className="estado-sesion">
                    {usuario ? (
                        <>
                            <span className="sesion">
                                <strong>{usuario.correo}</strong>
                            </span>
                            <button
                                type="button"
                                className="enlace-accion"
                                onClick={cerrarSesion}
                            >
                                Cerrar sesión
                            </button>
                        </>
                    ) : (
                        <Link className="boton boton-compacto" to="/login">
                            Iniciar sesión
                        </Link>
                    )}
                </span>
            </div>
        </header>
    );
}
