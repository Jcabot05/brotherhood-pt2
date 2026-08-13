-- Retira del esquema daw los datos que dejaron las corridas de prueba.
--
-- Las filas se eligen por su patrón, no por rango de identificadores: los ids
-- cambian entre entornos y una lista fija borraría lo que no toca.
--
-- Quedan fuera del borrado:
--   - Los clientes 1 a 3, que son los datos de ejemplo del proyecto.
--   - Las cuentas reales, que no usan el dominio example.com.
--
-- El orden respeta las claves foráneas: primero las citas, después el
-- catálogo, y al final las cuentas. Todo va en una transacción, de modo que
-- un fallo a medio camino no deje la base en un estado intermedio.
--
-- Antes de ejecutar conviene tener a mano db/respaldo_datos_prueba.sql, que
-- reinserta exactamente estas filas.

BEGIN;

-- Citas que apuntan a cualquier dato de prueba.
DELETE FROM daw.cita
WHERE id_barbero IN (
        SELECT id_barbero FROM daw.barbero WHERE nombre = 'Barbero de Prueba'
    )
   OR id_servicio IN (
        SELECT id_servicio FROM daw.servicio WHERE nombre = 'Servicio de Prueba'
    )
   OR id_cliente IN (
        SELECT id_cliente
        FROM daw.cliente
        WHERE correo LIKE '%@example.com'
          AND id_cliente NOT IN (1, 2, 3)
    );

DELETE FROM daw.barbero WHERE nombre = 'Barbero de Prueba';

DELETE FROM daw.servicio WHERE nombre = 'Servicio de Prueba';

DELETE FROM daw.cliente
WHERE correo LIKE '%@example.com'
  AND id_cliente NOT IN (1, 2, 3);

-- Las cuentas van al final: el cliente las referencia.
DELETE FROM daw.usuario WHERE correo LIKE '%@example.com';

COMMIT;
