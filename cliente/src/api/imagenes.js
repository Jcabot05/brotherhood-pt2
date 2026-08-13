/* Fotografía de cada servicio.

   El catálogo de la base no guarda imágenes, así que se asocian aquí por
   palabra clave del nombre. Un servicio nuevo cae en la imagen genérica en
   lugar de quedarse sin fotografía. */

const POR_PALABRA = [
    [/combo|barba.*corte|corte.*barba/i, 'combo'],
    [/infantil|niño|nino|kids/i, 'infantil'],
    [/barba|afeitad/i, 'barba'],
    [/corte|cabello|pelo/i, 'corte'],
];

export function imagenDeServicio(nombre = '') {
    const encontrada = POR_PALABRA.find(([patron]) => patron.test(nombre));
    return `/servicios/${encontrada ? encontrada[1] : 'generico'}.jpg`;
}
