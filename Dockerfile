# La aplicación necesita Python para la API y Node para compilar el cliente.
# El detector de la plataforma instala un solo lenguaje, así que la imagen se
# describe aquí y deja de depender de lo que adivine.

FROM python:3.12-slim

# Node se instala desde el repositorio oficial de Debian: el cliente sólo lo
# necesita para compilar, no para ejecutarse.
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Las dependencias se copian antes que el código para que su capa se reutilice
# mientras no cambien.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY cliente/package.json cliente/package-lock.json ./cliente/
RUN npm ci --prefix cliente

COPY . .

# El cliente se compila antes de recoger los archivos estáticos: Django sólo
# los busca en static_build/ si ese directorio ya existe.
RUN npm run build --prefix cliente

# collectstatic necesita leer la configuración, que exige estas variables. Los
# valores reales llegan del entorno al arrancar; aquí sólo permiten que el
# comando se ejecute durante la construcción de la imagen.
ENV DJANGO_SECRET_KEY=solo-para-construir \
    JWT_SECRETO=solo-para-construir \
    DATABASE_URL=postgresql+psycopg://usuario:clave@localhost:5432/postgres \
    DJANGO_DEBUG=false \
    DJANGO_HOSTS_PERMITIDOS=localhost

RUN python manage.py collectstatic --noinput

CMD gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers 2
