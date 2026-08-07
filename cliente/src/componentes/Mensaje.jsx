/* Aviso al usuario: éxito, error o advertencia.

   React escapa el contenido por defecto, así que el correo o cualquier otro
   dato que venga del servidor se pinta como texto y nunca como HTML. */

export default function Mensaje({ tipo, texto, detalles = [] }) {
    if (!texto) return null;

    return (
        <div className={`mensaje ${tipo}`} role={tipo === 'error' ? 'alert' : 'status'}>
            {texto}
            {detalles.length > 0 && (
                <ul>
                    {detalles.map((detalle, indice) => (
                        <li key={indice}>{detalle}</li>
                    ))}
                </ul>
            )}
        </div>
    );
}
