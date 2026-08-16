import { Route, Routes } from 'react-router-dom';

import { ProveedorSesion } from './api/sesion';
import Barra from './componentes/Barra';
import Acceso from './paginas/Acceso';
import Agendar from './paginas/Agendar';
import Servicios from './paginas/Servicios';

export default function App() {
    return (
        <ProveedorSesion>
            <Barra />
            <Routes>
                {/* HU-01: catálogo público */}
                <Route path="/" element={<Servicios />} />
                <Route path="/login" element={<Acceso />} />
                {/* HU-02: agenda, exige sesión */}
                <Route path="/agendar" element={<Agendar />} />
            </Routes>
        </ProveedorSesion>
    );
}
