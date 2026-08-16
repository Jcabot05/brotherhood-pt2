import { useEffect, useRef } from 'react';

export default function Dialogo({
    abierto,
    titulo,
    descripcion,
    detalle,
    textoConfirmar = 'Confirmar',
    textoCancelar = 'Volver',
    peligroso = false,
    onConfirmar,
    onCerrar,
}) {
    const referencia = useRef(null);

    useEffect(() => {
        const dialogo = referencia.current;
        if (!dialogo) return;

        if (abierto && !dialogo.open) {
            dialogo.showModal();
        } else if (!abierto && dialogo.open) {
            dialogo.close();
        }
    }, [abierto]);

    useEffect(() => {
        const dialogo = referencia.current;
        if (!dialogo) return;

        const alCerrar = () => onCerrar();
        dialogo.addEventListener('close', alCerrar);
        return () => dialogo.removeEventListener('close', alCerrar);
    }, [onCerrar]);

    return (
        <dialog className="dialogo" ref={referencia} aria-labelledby="dialogo-titulo">
            <div className="dialogo-cuerpo">
                <h2 id="dialogo-titulo">{titulo}</h2>
                {descripcion && <p>{descripcion}</p>}

                {detalle && (
                    <div className="dialogo-detalle">
                        <dl>
                            {detalle.map(({ etiqueta, valor }) => (
                                <div key={etiqueta} style={{ display: 'contents' }}>
                                    <dt>{etiqueta}</dt>
                                    <dd>{valor}</dd>
                                </div>
                            ))}
                        </dl>
                    </div>
                )}
            </div>

            <div className="dialogo-acciones">
                <button
                    type="button"
                    className="boton boton-secundario"
                    onClick={onCerrar}
                >
                    {textoCancelar}
                </button>
                <button
                    type="button"
                    className={`boton ${peligroso ? 'boton-peligro-solido' : ''}`}
                    onClick={onConfirmar}
                >
                    {textoConfirmar}
                </button>
            </div>
        </dialog>
    );
}
